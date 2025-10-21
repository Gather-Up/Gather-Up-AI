from fastapi import APIRouter, HTTPException
from typing import List
from database import vendor_collection
from schemas import VendorSchema
from services.vector_service import generate_embedding, compute_similarity
from services.llama_service import generate_vendor_recommendation

router = APIRouter(prefix="/vendors", tags=["Vendors"])

# Add or update vendor
@router.post("/add")
def add_vendor(vendor: VendorSchema):
    vendor_dict = vendor.dict()
    # Generate embedding for vendor description
    vendor_dict['vectorEmbedding'] = generate_embedding(vendor.description)
    result = vendor_collection.update_one(
        {"vendorName": vendor.vendorName},
        {"$set": vendor_dict},
        upsert=True
    )
    return {"message": "Vendor added/updated successfully."}

# Retrieve all vendors
@router.get("/")
def get_vendors():
    vendors = list(vendor_collection.find({}, {"_id": 0}))
    return vendors

# Recommend vendors based on user prompt
@router.post("/recommend")
def recommend_vendors(user_prompt: str):
    vendors = list(vendor_collection.find({}))
    if not vendors:
        raise HTTPException(status_code=404, detail="No vendors available.")

    # Generate prompt embedding
    prompt_embedding = generate_embedding(user_prompt)
    # Compute similarity
    for v in vendors:
        if 'vectorEmbedding' in v and v['vectorEmbedding']:
            v['similarity'] = compute_similarity(prompt_embedding, v['vectorEmbedding'])
        else:
            v['similarity'] = 0.0

    # Sort vendors by similarity
    vendors_sorted = sorted(vendors, key=lambda x: x['similarity'], reverse=True)

    # Generate LLaMA recommendation
    recommendation = generate_vendor_recommendation(user_prompt, vendors_sorted)
    return {"recommendation": recommendation, "top_vendors": vendors_sorted[:5]}
