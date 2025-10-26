from fastapi import APIRouter, HTTPException, Body
from schemas import LocationSearchRequest, LocationResponse
from services.places_service import search_places, parse_location_query
from typing import List
import os

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.post("/search")
def search_locations(request: LocationSearchRequest = Body(...)):
    """
    Search for event venues/locations based on natural language query.
    Uses Google Places API to find suitable locations.
    
    Args:
        request: LocationSearchRequest with query and filters
    
    Returns:
        List of location recommendations with details
    """
    
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # Parse the query to extract location details
        parsed_query = parse_location_query(request.query)
        
        # Search for places using Google Places API
        places = search_places(
            query=parsed_query['search_query'],
            location=parsed_query.get('city'),
            radius=request.radius,
            max_results=request.max_results,
            location_type=request.location_type or parsed_query.get('venue_type')
        )
        
        if not places:
            return {
                "status": "no_match",
                "message": "No suitable venues found for your search. Try:\n- Expanding the search radius\n- Being more flexible with location requirements\n- Checking nearby cities",
                "query": request.query,
                "locations_found": 0,
                "locations": []
            }
        
        return {
            "status": "success",
            "query": request.query,
            "locations_found": len(places),
            "locations": places,
            "message": f"Found {len(places)} suitable venue(s) for your event"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching for locations: {str(e)}"
        )


@router.get("/details/{place_id}")
def get_location_details(place_id: str):
    """
    Get detailed information about a specific location/venue
    """
    from services.places_service import get_place_details
    
    try:
        details = get_place_details(place_id)
        
        if not details:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return details
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching location details: {str(e)}"
        )
