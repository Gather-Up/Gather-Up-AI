from pydantic import BaseModel, Field
from pydantic import EmailStr
from typing import List, Optional, Dict

class AvailabilityItem(BaseModel):
    date: str
    status: str

class PricingItem(BaseModel):
    currency: str
    averageCost: float
    pricingModel: str

class ContactItem(BaseModel):
    phone: str
    email: EmailStr

class VendorSchema(BaseModel):
    vendorName: str
    vendorType: str
    description: str
    location: str
    rating: float
    pricing: PricingItem
    availability: List[AvailabilityItem]
    contact: ContactItem
    tags: List[str]
    previousClients: Optional[List[str]] = []
    vendorDocuments: Optional[Dict[str, str]] = {}
    vectorEmbedding: Optional[List[float]] = []

class RecommendationRequest(BaseModel):
    user_prompt: str = Field(..., description="Natural language description of what the user needs")
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity threshold (0-1)")
    max_results: Optional[int] = Field(3, ge=1, le=5, description="Maximum number of vendors to return")
