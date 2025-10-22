from pydantic import BaseModel, Field, EmailStr
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
