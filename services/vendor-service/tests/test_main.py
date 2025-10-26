import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

mock_collection = Mock()
mock_db = Mock()
mock_client = Mock()

mock_client.__getitem__.return_value = mock_db
mock_db.__getitem__.return_value = mock_collection

# Set environment variables for testing
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB_NAME"] = "test_db"
os.environ["MONGO_VENDOR_COLLECTION"] = "test_vendors"

# Patch MongoClient before importing main
with patch("database.MongoClient", return_value=mock_client):
    from main import app

# Create a test client
client = TestClient(app)


def test_health_endpoint():
    """
    Test the /health endpoint
    This is a simple test that checks if the health check endpoint works
    """
    # Send a GET request to the /health endpoint
    response = client.get("/health")
    
    # Check if the response status code is 200 (OK)
    assert response.status_code == 200
    
    # Check if the response contains the expected data
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vendor-service"
    
    print("✅ Vendor Service health check test passed!")
