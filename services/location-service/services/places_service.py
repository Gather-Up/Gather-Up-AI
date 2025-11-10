import requests
import os
import re
from dotenv import load_dotenv
from typing import Dict, List, Optional

load_dotenv()

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACES_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACES_PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

# Default location (Colombo, Sri Lanka) as fallback
DEFAULT_LOCATION = {
    "lat": 6.9271,
    "lng": 79.8612
}

# Mapping of event types to Google Places types
EVENT_VENUE_TYPES = {
    "conference": "conference_center",
    "meeting": "conference_center",
    "hackathon": "university|coworking_space",
    "workshop": "conference_center|coworking_space",
    "seminar": "conference_center",
    "wedding": "wedding_venue|banquet_hall",
    "party": "banquet_hall|night_club",
    "corporate": "conference_center|event_venue",
    "concert": "stadium|event_venue",
    "exhibition": "convention_center|event_venue",
    "gala": "banquet_hall|event_venue",
    "funeral": "funeral_home|church|place_of_worship",
    "memorial": "funeral_home|church|place_of_worship",
    "birthday": "banquet_hall|restaurant|event_venue",
    "anniversary": "banquet_hall|restaurant|event_venue"
}


def parse_location_query(query: str) -> Dict:
    '''
    Parse natural language query to extract location details.
    
    Examples:
    - "hackathon venue in Colombo" -> {city: "Colombo", venue_type: "coworking_space"}
    - "place like Hatchworks" -> {specific_name: "Hatchworks"}
    - "conference center for 100 people in Kandy" -> {city: "Kandy", venue_type: "conference_center"}
    '''
    query_lower = query.lower()
    parsed = {
        "search_query": query,
        "city": None,
        "venue_type": None,
        "specific_name": None
    }
    
    # Extract city names (Sri Lankan cities)
    sri_lankan_cities = [
        "colombo", "kandy", "galle", "jaffna", "negombo", "batticaloa",
        "trincomalee", "kurunegala", "ratnapura", "badulla", "matara",
        "anuradhapura", "polonnaruwa", "hambantota", "kegalle", "ampara"
    ]
    
    for city in sri_lankan_cities:
        if city in query_lower:
            parsed["city"] = city.capitalize()
            break
    
    # Extract venue type based on event type
    for event_type, places_type in EVENT_VENUE_TYPES.items():
        if event_type in query_lower:
            parsed["venue_type"] = places_type
            break
    
    # Check for specific venue names (e.g., "like Hatchworks")
    specific_venue_pattern = r"(?:like|similar to|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
    match = re.search(specific_venue_pattern, query)
    if match:
        parsed["specific_name"] = match.group(1)
        parsed["search_query"] = f"{match.group(1)} {parsed['city'] or 'Colombo'}"
    
    return parsed


def search_places(
    query: str,
    location: Optional[str] = None,
    radius: int = 5000,
    max_results: int = 3,
    location_type: Optional[str] = None
) -> List[Dict]:
    '''
    Search for places using Google Places API Text Search.
    
    Args:
        query: Search query
        location: City or area name
        radius: Search radius in meters
        max_results: Maximum number of results to return
        location_type: Google Places type filter
    
    Returns:
        List of place details with comprehensive information
    '''
    
    if not GOOGLE_PLACES_API_KEY:
        raise ValueError("GOOGLE_PLACES_API_KEY not configured. Please set the API key in your .env file.")
    
    # Build search query
    search_query = query
    if location:
        search_query = f"{query} in {location}"
    
    params = {
        "query": search_query,
        "key": GOOGLE_PLACES_API_KEY,
        "radius": radius
    }
    
    if location_type:
        params["type"] = location_type
    
    try:
        response = requests.get(PLACES_TEXT_SEARCH_URL, params=params, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Google Places API returned status code {response.status_code}: {response.text}")
        
        data = response.json()
        
        if data.get("status") == "ZERO_RESULTS":
            return []  # No results found, return empty list
        
        if data.get("status") != "OK":
            raise Exception(f"Google Places API error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
        
        places = data.get("results", [])[:max_results]
        
        # Format the results with enhanced details
        formatted_places = []
        for place in places:
            place_id = place.get("place_id")
            geometry = place.get("geometry", {})
            location_coords = geometry.get("location", {})
            
            # Get detailed information for this place
            details = get_place_details(place_id) if place_id else {}
            
            formatted_place = {
                # Basic Information
                "place_id": place_id,
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": {
                    "lat": location_coords.get("lat"),
                    "lng": location_coords.get("lng")
                },
                
                # Category/Type
                "category": place.get("types", [])[0] if place.get("types") else "unknown",
                "types": place.get("types", []),
                
                # Rating & Reviews
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "reviews": details.get("reviews", [])[:3] if details else [],  # Top 3 reviews
                
                # Contact Information
                "contact_info": {
                    "phone": details.get("formatted_phone_number"),
                    "website": details.get("website"),
                    "google_maps_url": details.get("url")
                },
                
                # Opening Hours
                "opening_hours": details.get("opening_hours"),
                
                # Business Details
                "business_status": place.get("business_status"),
                "price_level": place.get("price_level"),
                "vicinity": place.get("vicinity"),
                
                # Amenities/Facilities
                "amenities": {
                    "wheelchair_accessible": details.get("wheelchair_accessible_entrance")
                }
            }
            
            # Add photo references if available
            if "photos" in place:
                formatted_place["photos"] = [
                    {
                        "photo_reference": photo.get("photo_reference"),
                        "width": photo.get("width"),
                        "height": photo.get("height"),
                        "photo_url": f"{PLACES_PHOTO_URL}?maxwidth=400&photo_reference={photo.get('photo_reference')}&key={GOOGLE_PLACES_API_KEY}"
                    }
                    for photo in place["photos"][:3]  # Limit to 3 photos
                ]
            else:
                formatted_place["photos"] = []
            
            # Add nearby places for context
            if location_coords.get("lat") and location_coords.get("lng"):
                formatted_place["nearby_places"] = get_nearby_places(
                    location_coords.get("lat"),
                    location_coords.get("lng"),
                    radius=500
                )
            else:
                formatted_place["nearby_places"] = []
            
            formatted_places.append(formatted_place)
        
        return formatted_places
        
    except Exception as e:
        print(f"Error calling Google Places API: {str(e)}")
        raise


def get_place_details(place_id: str) -> Dict:
    '''
    Get detailed information about a specific place using Google Places Details API.
    
    Args:
        place_id: The unique identifier for a place
        
    Returns:
        Dictionary containing detailed place information
    '''
    
    if not GOOGLE_PLACES_API_KEY:
        return {}
    
    params = {
        "place_id": place_id,
        "key": GOOGLE_PLACES_API_KEY,
        "fields": "name,formatted_address,geometry,rating,opening_hours,photos,price_level,website,formatted_phone_number,reviews,wheelchair_accessible_entrance,business_status,types,url"
    }
    
    try:
        response = requests.get(PLACES_DETAILS_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return data.get("result", {})
        
        print(f"Warning: Could not fetch details for place {place_id}")
        return {}
        
    except Exception as e:
        print(f"Error fetching place details: {str(e)}")
        return {}


def get_nearby_places(lat: float, lng: float, radius: int = 1000, place_type: str = None) -> List[Dict]:
    '''
    Get nearby places for context and navigation using Google Places Nearby Search API.
    
    Args:
        lat: Latitude
        lng: Longitude
        radius: Search radius in meters (default: 1000)
        place_type: Type of places to search for (optional)
    
    Returns:
        List of nearby places with basic information
    '''
    
    if not GOOGLE_PLACES_API_KEY:
        return []
    
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "key": GOOGLE_PLACES_API_KEY
    }
    
    if place_type:
        params["type"] = place_type
    
    try:
        response = requests.get(PLACES_NEARBY_SEARCH_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                places = data.get("results", [])[:5]  # Limit to 5 nearby places
                return [
                    {
                        "name": place.get("name"),
                        "type": place.get("types", [])[0] if place.get("types") else "unknown",
                        "vicinity": place.get("vicinity"),
                        "distance": "nearby"  # Could calculate actual distance if needed
                    }
                    for place in places
                ]
        
        return []
        
    except Exception as e:
        print(f"Error fetching nearby places: {str(e)}")
        return []
