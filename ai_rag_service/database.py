import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from an .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_VENDOR_COLLECTION = os.getenv("MONGO_VENDOR_COLLECTION")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
vendor_collection = db[MONGO_VENDOR_COLLECTION]