from fastapi import APIRouter, HTTPException, Body
from typing import List
import os
from dotenv import load_dotenv
from database import vendor_collection
from schemas import VendorSchema, RecommendationRequest
from services.vector_service import generate_embedding, compute_similarity
from services.llama_service import generate_vendor_recommendation

load_dotenv()

DEFAULT_MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY_THRESHOLD"))
DEFAULT_MAX_RESULTS = int(os.getenv("MAX_RESULTS"))

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.post("/add")
def add_vendor(vendor: VendorSchema):
    """
    Add or update a vendor in the database with vector embedding
    """
    vendor_dict = vendor.model_dump()
    # Generate embedding for vendor description
    vendor_dict['vectorEmbedding'] = generate_embedding(vendor.description)
    result = vendor_collection.update_one(
        {"vendorName": vendor.vendorName},
        {"$set": vendor_dict},
        upsert=True
    )
    return {"message": "Vendor added/updated successfully."}


@router.get("/")
def get_vendors():
    """
    Retrieve all vendors from database
    """
    vendors = list(vendor_collection.find({}, {"_id": 0}))
    return vendors


@router.post("/recommend")
def recommend_vendors(request: RecommendationRequest = Body(...)):
    """
    Recommend vendors based on natural language user prompt using RAG.
    Optimized for accuracy, efficiency, and speed.
    
    Args:
        request: RecommendationRequest containing user_prompt, min_similarity, max_results
    
    Returns:
        Intelligent recommendation with reasoning from LLaMA model
    """
    
    user_prompt = request.user_prompt
    min_similarity = request.min_similarity if request.min_similarity is not None else DEFAULT_MIN_SIMILARITY
    max_results = request.max_results if request.max_results is not None else DEFAULT_MAX_RESULTS
    
    # Validate input
    if not user_prompt or not user_prompt.strip():
        raise HTTPException(status_code=400, detail="User prompt cannot be empty.")
    
    # Validate max_results
    if max_results < 1 or max_results > 5:
        max_results = 3
    
    # Retrieve all vendors from database (only necessary fields)
    vendors = list(vendor_collection.find(
        {},
        {
            "_id": 0,
            "vendorName": 1,
            "vendorType": 1,
            "description": 1,
            "location": 1,
            "rating": 1,
            "pricing": 1,
            "tags": 1,
            "contact": 1,
            "vectorEmbedding": 1
        }
    ))
    
    if not vendors:
        raise HTTPException(status_code=404, detail="No vendors available in the database.")

    # Generate semantic embedding 
    try:
        prompt_embedding = generate_embedding(user_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")
    
    # Compute similarity scores for all vendors (optimized)
    vendors_with_scores = []
    for vendor in vendors:
        if 'vectorEmbedding' in vendor and vendor['vectorEmbedding']:
            similarity = compute_similarity(prompt_embedding, vendor['vectorEmbedding'])
            vendor['similarity'] = similarity
            vendors_with_scores.append(vendor)
    
    if not vendors_with_scores:
        raise HTTPException(status_code=404, detail="No vendors have embeddings. Please re-index vendors.")

    # Sort vendors by similarity (highest first) and apply limit
    vendors_sorted = sorted(vendors_with_scores, key=lambda x: x['similarity'], reverse=True)[:max_results]

    # Generate intelligent recommendation using LLaMA
    result = generate_vendor_recommendation(user_prompt, vendors_sorted, min_similarity)
    
    # Structure the response
    if result['status'] == 'no_match':
        return {
            "status": "no_match",
            "message": result['message'],
            "user_prompt": user_prompt,
            "vendors_found": 0,
            "top_vendors": []
        }
    else:
        # Clean vendor data  
        clean_vendors = []
        for vendor in result['vendors']:
            vendor_copy = vendor.copy()
            if 'vectorEmbedding' in vendor_copy:
                del vendor_copy['vectorEmbedding']
            clean_vendors.append(vendor_copy)
        
        return {
            "status": "success",
            "user_prompt": user_prompt,
            "recommendation": result['message'],
            "vendors_found": len(clean_vendors),
            "top_vendors": clean_vendors
        }
