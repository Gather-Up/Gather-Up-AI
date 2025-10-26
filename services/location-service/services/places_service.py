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
    "gala": "banquet_hall|event_venue"
}


def parse_location_query(query: str) -> Dict:
    """
    Parse natural language query to extract location details.
    
    Examples:
    - "hackathon venue in Colombo" -> {city: "Colombo", venue_type: "coworking_space"}
    - "place like Hatchworks" -> {specific_name: "Hatchworks"}
    - "conference center for 100 people in Kandy" -> {city: "Kandy", venue_type: "conference_center"}
    """
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
    """
    Search for places using Google Places API Text Search.
    
    Args:
        query: Search query
        location: City or area name
        radius: Search radius in meters
        max_results: Maximum number of results to return
        location_type: Google Places type filter
    
    Returns:
        List of place details
    """
    
    if not GOOGLE_PLACES_API_KEY:
        # Fallback mode without API key - return mock data
        print("Warning: GOOGLE_PLACES_API_KEY not found. Using mock data.")
        return get_mock_locations(query, max_results)
    
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
            print(f"Google Places API error: {response.status_code}")
            return get_mock_locations(query, max_results)
        
        data = response.json()
        
        if data.get("status") != "OK":
            print(f"Google Places API status: {data.get('status')}")
            return get_mock_locations(query, max_results)
        
        places = data.get("results", [])[:max_results]
        
        # Format the results
        formatted_places = []
        for place in places:
            formatted_place = {
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": place.get("geometry", {}).get("location", {}),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "types": place.get("types", []),
                "vicinity": place.get("vicinity"),
                "business_status": place.get("business_status"),
                "price_level": place.get("price_level")
            }
            
            # Add photo references if available
            if "photos" in place:
                formatted_place["photos"] = [
                    photo.get("photo_reference") for photo in place["photos"][:3]
                ]
            
            formatted_places.append(formatted_place)
        
        return formatted_places
        
    except Exception as e:
        print(f"Error calling Google Places API: {str(e)}")
        return get_mock_locations(query, max_results)


def get_place_details(place_id: str) -> Dict:
    """
    Get detailed information about a specific place.
    """
    
    if not GOOGLE_PLACES_API_KEY:
        return {"error": "API key not configured"}
    
    params = {
        "place_id": place_id,
        "key": GOOGLE_PLACES_API_KEY,
        "fields": "name,formatted_address,geometry,rating,opening_hours,photos,price_level,website,formatted_phone_number,reviews"
    }
    
    try:
        response = requests.get(PLACES_DETAILS_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "OK":
                return data.get("result", {})
        
        return {}
        
    except Exception as e:
        print(f"Error fetching place details: {str(e)}")
        return {}


def get_mock_locations(query: str, max_results: int = 3) -> List[Dict]:
    """
    Return mock location data when Google Places API is unavailable.
    This is for development/testing purposes.
    """
    mock_venues = [
        {
            "place_id": "mock_1",
            "name": "Hatchworks Colombo",
            "address": "371/A Galle Rd, Colombo 00300, Sri Lanka",
            "location": {"lat": 6.9018, "lng": 79.8509},
            "rating": 4.5,
            "user_ratings_total": 150,
            "types": ["coworking_space", "event_venue"],
            "vicinity": "Colombo 3",
            "business_status": "OPERATIONAL",
            "price_level": 3
        },
        {
            "place_id": "mock_2",
            "name": "Cinnamon Grand Colombo",
            "address": "77 Galle Rd, Colombo 00300, Sri Lanka",
            "location": {"lat": 6.9147, "lng": 79.8501},
            "rating": 4.6,
            "user_ratings_total": 3500,
            "types": ["hotel", "conference_center", "banquet_hall"],
            "vicinity": "Colombo 3",
            "business_status": "OPERATIONAL",
            "price_level": 4
        },
        {
            "place_id": "mock_3",
            "name": "BMICH - Bandaranaike Memorial International Conference Hall",
            "address": "Bauddhaloka Mawatha, Colombo 00700, Sri Lanka",
            "location": {"lat": 6.9175, "lng": 79.8653},
            "rating": 4.3,
            "user_ratings_total": 1200,
            "types": ["conference_center", "event_venue"],
            "vicinity": "Colombo 7",
            "business_status": "OPERATIONAL",
            "price_level": 3
        },
        {
            "place_id": "mock_4",
            "name": "Trace Expert City",
            "address": "No 200, Union Place, Colombo 00200, Sri Lanka",
            "location": {"lat": 6.9147, "lng": 79.8612},
            "rating": 4.4,
            "user_ratings_total": 500,
            "types": ["coworking_space", "event_venue"],
            "vicinity": "Colombo 2",
            "business_status": "OPERATIONAL",
            "price_level": 2
        }
    ]
    
    # Simple filtering based on query
    query_lower = query.lower()
    filtered_venues = []
    
    for venue in mock_venues:
        if (query_lower in venue["name"].lower() or 
            any(t in query_lower for t in ["hackathon", "coworking", "tech"]) and "coworking_space" in venue["types"] or
            any(t in query_lower for t in ["conference", "meeting", "seminar"]) and "conference_center" in venue["types"]):
            filtered_venues.append(venue)
    
    # If no specific matches, return all
    if not filtered_venues:
        filtered_venues = mock_venues
    
    return filtered_venues[:max_results]
