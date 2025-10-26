"""
Simple test for Location Service
This test checks if the health endpoint returns the correct response
"""

from fastapi.testclient import TestClient
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
    assert data["service"] == "location-service"
    
    print("✅ Location Service health check test passed!")
