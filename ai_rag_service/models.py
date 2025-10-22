from typing import List, Optional, Dict
from pydantic import BaseModel

class VendorModel(BaseModel):
    vendorName: str
    vendorType: str
    description: str
    location: str
    rating: float
    pricing: Dict
    availability: List[Dict]
    contact: Dict
    tags: List[str]
    previousClients: Optional[List[str]] = []
    vendorDocuments: Optional[Dict[str, str]] = {}
    vectorEmbedding: Optional[List[float]] = []

    class Config:
        arbitrary_types_allowed = True
