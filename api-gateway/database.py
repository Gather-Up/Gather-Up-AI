"""
MongoDB Database Configuration and Models
"""
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://developerofficial54_db_user:ciKqctDrfHK7gQ1m@cluster0.5weecdp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

DATABASE_NAME = "GatherUp_Official_DB"

# Initialize MongoDB client
client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

# Collections
email_templates_collection = db["email_templates"]
generated_events_collection = db["generated_events"]
events_collection = db["Events"]  # Existing events collection

def get_next_sequence_value(sequence_name: str) -> int:
    """Get next sequence value for auto-increment fields"""
    counter = db.counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]


class EmailTemplateModel:
    """Email template document model"""
    
    @staticmethod
    def create(event_id: str, subject: str, body: str, venue_info: dict, user_prompt: str):
        """Create new email template document"""
        document = {
            "_id": ObjectId(),
            "event_id": ObjectId(event_id) if event_id else None,
            "subject": subject,
            "body": body,
            "venue_info": venue_info,
            "user_prompt": user_prompt,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "_class": "com.gatherup.entity.EmailTemplate"
        }
        result = email_templates_collection.insert_one(document)
        return str(result.inserted_id)


class GeneratedEventModel:
    """Generated event document model with all recommendations"""
    
    @staticmethod
    def create(
        event_id: str,
        user_prompt: str,
        selected_venue: dict,
        selected_vendor: dict,  # FIRST vendor only
        generated_images: list,
        image_prompt: str
    ):
        """Create new generated event document"""
        document = {
            "_id": ObjectId(),
            "event_id": ObjectId(event_id) if event_id else None,
            "user_prompt": user_prompt,
            "venue": {
                "name": selected_venue.get("name"),
                "address": selected_venue.get("address"),
                "rating": selected_venue.get("rating"),
                "place_id": selected_venue.get("place_id"),
                "phone": selected_venue.get("contact_info", {}).get("phone"),
                "website": selected_venue.get("contact_info", {}).get("website"),
                "google_maps_url": selected_venue.get("contact_info", {}).get("google_maps_url"),
            },
            "vendor": {
                "name": selected_vendor.get("vendorName") if selected_vendor else None,
                "type": selected_vendor.get("vendorType") if selected_vendor else None,
                "description": selected_vendor.get("description") if selected_vendor else None,
                "location": selected_vendor.get("location") if selected_vendor else None,
                "rating": selected_vendor.get("rating") if selected_vendor else None,
                "pricing": selected_vendor.get("pricing") if selected_vendor else None,
                "contact": selected_vendor.get("contact") if selected_vendor else None,
            } if selected_vendor else None,
            "images": generated_images,  # Array of {url, prompt, cloudinary_id}
            "image_generation_prompt": image_prompt,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "_class": "com.gatherup.entity.GeneratedEvent"
        }
        result = generated_events_collection.insert_one(document)
        return str(result.inserted_id)


def verify_connection():
    """Verify MongoDB connection"""
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return False
