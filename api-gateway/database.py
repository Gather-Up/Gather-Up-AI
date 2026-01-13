"""
MongoDB Database Configuration and Models
"""
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

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
events_collection = db["Events"]  # Main events collection
tasks_collection = db["Tasks"]  # Tasks collection
generated_media_history_collection = db["GeneratedMediaHistory"]  # Media history collection

def get_next_sequence_value(sequence_name: str) -> int:
    """Get next sequence value for auto-increment fields"""
    counter = db.counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return counter["sequence_value"]


def verify_connection() -> bool:
    """Verify MongoDB connection"""
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        return False


class EventModel:
    """Main Event document model"""
    
    @staticmethod
    def create(
        user_id: str,
        user_prompt: str,
        event_type: str,
        event_date: datetime,
        guest_count: int,
        venue: Dict[str, Any],
        vendors: List[Dict[str, Any]],
        images: List[Dict[str, Any]],
        email_template: Dict[str, str],
        task_checklist: List[Dict[str, Any]],
        budget_estimate: Optional[float] = None
    ) -> str:
        """Create new event in main Events collection"""
        document = {
            "_id": ObjectId(),
            "user_id": user_id,
            "event_type": event_type,
            "status": "planned",
            "user_prompt": user_prompt,
            
            # Event Details
            "event_date": event_date,
            "guest_count": guest_count,
            "budget_estimate": budget_estimate,
            
            # Venue Information
            "venue": {
                "name": venue.get("name"),
                "address": venue.get("address"),
                "rating": venue.get("rating"),
                "place_id": venue.get("place_id"),
                "phone": venue.get("contact_info", {}).get("phone"),
                "website": venue.get("contact_info", {}).get("website"),
                "email": venue.get("contact_info", {}).get("email"),
                "google_maps_url": venue.get("contact_info", {}).get("google_maps_url"),
                "photos": venue.get("photos", [])[:3]  # First 3 photos
            },
            
            # Vendors Information
            "vendors": [
                {
                    "vendor_id": vendor.get("_id") if vendor.get("_id") else None,
                    "name": vendor.get("vendorName"),
                    "type": vendor.get("vendorType"),
                    "description": vendor.get("description"),
                    "location": vendor.get("location"),
                    "rating": vendor.get("rating"),
                    "pricing": vendor.get("pricing"),
                    "contact": vendor.get("contact"),
                }
                for vendor in vendors
            ],
            
            # Generated Images
            "images": images,
            
            # Email Template
            "email_template": {
                "subject": email_template.get("subject"),
                "body": email_template.get("body"),
                "generated_at": datetime.utcnow()
            },
            
            # Task Checklist for Organizer
            "task_checklist": task_checklist,
            
            # Timestamps
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "_class": "com.gatherup.entity.Event"
        }
        
        result = events_collection.insert_one(document)
        return str(result.inserted_id)


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


class TasksModel:
    """Tasks document model"""
    
    @staticmethod
    def create(
        title: str,
        description: str,
        priority: str,
        status: str,
        start_date: datetime,
        due_date: datetime,
        employee_acc: str,
        assigned_to_id: str,
        event_id: str
    ) -> str:
        """Create new task document"""
        document = {
            "_id": ObjectId(),
            "title": title,
            "description": description,
            "priority": priority,  # "low", "medium", "high"
            "status": status,  # "not started", "progress", "complete", "cancelled", "late"
            "createdDate": datetime.utcnow(),
            "startDate": start_date,
            "dueDate": due_date,
            "completedDate": None,
            "employeeAcc": employee_acc,  # Employee who will perform the task
            "assignedToID": assigned_to_id,  # User who created/assigned the task
            "eventID": event_id,  # Foreign key to Events collection
            "_class": "com.example.AdminBasic.Entity.Tasks"
        }
        result = tasks_collection.insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    def create_multiple(tasks: List[Dict[str, Any]], event_id: str, assigned_to_id: str) -> List[str]:
        """Create multiple tasks at once"""
        task_ids = []
        for task in tasks:
            task_id = TasksModel.create(
                title=task["title"],
                description=task["description"],
                priority=task.get("priority", "medium"),
                status=task.get("status", "not started"),
                start_date=task.get("startDate", datetime.utcnow()),
                due_date=task["dueDate"],
                employee_acc=task.get("employeeAcc", assigned_to_id),
                assigned_to_id=assigned_to_id,
                event_id=event_id
            )
            task_ids.append(task_id)
        return task_ids
    
    @staticmethod
    def get_by_event(event_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for an event"""
        tasks = tasks_collection.find({"eventID": event_id})
        return [task for task in tasks]


class GeneratedMediaHistoryModel:
    """Generated media history document model"""
    
    @staticmethod
    def create(media_link: str, event_id_string: str) -> str:
        """Create new media history document"""
        document = {
            "_id": ObjectId(),
            "mediaLink": media_link,  # Cloudinary URL
            "createdDate": datetime.utcnow(),
            "eventIDString": event_id_string,  # Foreign key to Events collection
            "_class": "com.example.AdminBasic.Entity.GeneratedMediaHistory"
        }
        result = generated_media_history_collection.insert_one(document)
        return str(result.inserted_id)
    
    @staticmethod
    def create_multiple(media_links: List[str], event_id_string: str) -> List[str]:
        """Create multiple media history documents"""
        media_ids = []
        for media_link in media_links:
            media_id = GeneratedMediaHistoryModel.create(media_link, event_id_string)
            media_ids.append(media_id)
        return media_ids
    
    @staticmethod
    def get_by_event(event_id_string: str) -> List[Dict[str, Any]]:
        """Get all media for an event"""
        media = generated_media_history_collection.find({"eventIDString": event_id_string})
        return [item for item in media]
