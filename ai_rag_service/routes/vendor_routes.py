from fastapi import APIRouter, HTTPException
from typing import List
import os
from dotenv import load_dotenv
from database import vendor_collection
from schemas import VendorSchema
from services.vector_service import generate_embedding, compute_similarity
from services.llama_service import generate_vendor_recommendation
load_dotenv()

DEFAULT_MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY_THRESHOLD"))
DEFAULT_MAX_RESULTS = int(os.getenv("MAX_RESULTS"))

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
def recommend_vendors(
    user_prompt: str, 
    min_similarity: float = None,  
    max_results: int = None      
):
    """
    Recommend vendors based on natural language user prompt using RAG.
    
    Args:
        user_prompt: Natural language description of what the user needs
        min_similarity: Minimum cosine similarity threshold (0.0 to 1.0, default from .env)
        max_results: Maximum number of vendors to return (1-3, default from .env)
    
    Returns:
        Intelligent recommendation with reasoning from LLaMA model
    """
    
    if min_similarity is None:
        min_similarity = DEFAULT_MIN_SIMILARITY
    if max_results is None:
        max_results = DEFAULT_MAX_RESULTS
    
    # Validate input
    if not user_prompt or not user_prompt.strip():
        raise HTTPException(status_code=400, detail="User prompt cannot be empty.")
    
    # Validate max_results
    if max_results < 1 or max_results > 3:
        max_results = 3
    
    # Retrieve all vendors from database
    vendors = list(vendor_collection.find({}, {"_id": 0}))
    
    if not vendors:
        raise HTTPException(status_code=404, detail="No vendors available in the database.")

    # Generate semantic embedding 
    try:
        prompt_embedding = generate_embedding(user_prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {str(e)}")
    
    # Compute similarity scores for all vendors
    for vendor in vendors:
        if 'vectorEmbedding' in vendor and vendor['vectorEmbedding']:
            vendor['similarity'] = compute_similarity(prompt_embedding, vendor['vectorEmbedding'])
        else:
            vendor['similarity'] = 0.0

    # Sort vendors by similarity (highest first)
    vendors_sorted = sorted(vendors, key=lambda x: x['similarity'], reverse=True)
    
    # Apply max_results limit
    vendors_sorted = vendors_sorted[:max_results]

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
