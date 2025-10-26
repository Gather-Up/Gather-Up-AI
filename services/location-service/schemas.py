from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class LocationSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language query for location/venue search")
    max_results: Optional[int] = Field(3, ge=1, le=10, description="Maximum number of locations to return")
    radius: Optional[int] = Field(5000, description="Search radius in meters (default 5km)")
    location_type: Optional[str] = Field(None, description="Specific type of location (e.g., 'event_venue', 'conference_center')")

class LocationResponse(BaseModel):
    place_id: str
    name: str
    address: str
    location: Dict[str, float]  # lat, lng
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    types: List[str] = []
    vicinity: Optional[str] = None
    opening_hours: Optional[Dict] = None
    photos: Optional[List[str]] = []
    price_level: Optional[int] = None
    business_status: Optional[str] = None
