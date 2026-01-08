"""
Test script to verify MongoDB and Cloudinary configuration
Run this before starting the main application
"""

import sys
import os

print("=" * 60)
print("GatherUp - Configuration Verification")
print("=" * 60)
print()

# Test 1: Import check
print("[1/5] Checking required packages...")
try:
    import pymongo
    import cloudinary
    import httpx
    from fastapi import FastAPI
    print("✅ All required packages installed")
except ImportError as e:
    print(f"❌ Missing package: {e}")
    print("Run: pip install pymongo cloudinary")
    sys.exit(1)

# Test 2: Environment variables
print("\n[2/5] Checking environment variables...")
from dotenv import load_dotenv
load_dotenv()

required_vars = [
    "MONGODB_URI",
    "CLOUDINARY_CLOUD_NAME", 
    "CLOUDINARY_API_KEY",
    "CLOUDINARY_API_SECRET"
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if not value or value.startswith("your_"):
        missing_vars.append(var)
        print(f"❌ {var} not configured")
    else:
        # Mask sensitive data
        if "SECRET" in var or "URI" in var:
            display = value[:10] + "***"
        else:
            display = value
        print(f"✅ {var} = {display}")

if missing_vars:
    print(f"\n⚠️  Please configure these variables in .env file:")
    for var in missing_vars:
        print(f"   - {var}")
    print()

# Test 3: MongoDB connection
print("\n[3/5] Testing MongoDB connection...")
try:
    from database import verify_connection, db
    if verify_connection():
        print("✅ MongoDB connected successfully")
        print(f"   Database: {db.name}")
        collections = db.list_collection_names()
        print(f"   Collections: {', '.join(collections[:5])}...")
    else:
        print("❌ MongoDB connection failed")
except Exception as e:
    print(f"❌ MongoDB error: {e}")

# Test 4: Cloudinary configuration
print("\n[4/5] Testing Cloudinary configuration...")
try:
    import cloudinary
    config = cloudinary.config()
    if config.cloud_name and not config.cloud_name.startswith("your_"):
        print("✅ Cloudinary configured")
        print(f"   Cloud Name: {config.cloud_name}")
        print(f"   API Key: {str(config.api_key)[:5]}***")
    else:
        print("❌ Cloudinary not configured properly")
        print("   Please set CLOUDINARY_* variables in .env")
except Exception as e:
    print(f"❌ Cloudinary error: {e}")

# Test 5: Collections check
print("\n[5/5] Checking MongoDB collections...")
try:
    from database import (
        email_templates_collection, 
        generated_events_collection,
        events_collection
    )
    
    collections = {
        "email_templates": email_templates_collection,
        "generated_events": generated_events_collection,
        "Events": events_collection
    }
    
    for name, collection in collections.items():
        count = collection.count_documents({})
        print(f"✅ {name}: {count} documents")
        
except Exception as e:
    print(f"❌ Collection error: {e}")

# Summary
print("\n" + "=" * 60)
print("Configuration Summary")
print("=" * 60)

if not missing_vars:
    print("✅ All configurations complete!")
    print("\nYou can now start the application:")
    print("   python main.py")
else:
    print("⚠️  Some configurations are missing.")
    print("\nPlease complete the setup in .env file:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nFor Cloudinary setup:")
    print("   1. Visit: https://cloudinary.com/users/register_free")
    print("   2. Get credentials from dashboard")
    print("   3. Add to .env file")

print("\n" + "=" * 60)
