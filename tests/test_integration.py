import pytest
import asyncio
import requests
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.database import SessionLocal
from app import models, crud, schemas

class TestIntegration:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def db_session(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def test_device_lifecycle(self, client, db_session):
        """Test complete device lifecycle: create, read, update, delete"""
        
        # Create device
        device_data = {
            "ip_address": "192.168.1.100",
            "description": "Test Router",
            "tags": ["router", "gateway"],
            "snmp_community": "public"
        }
        
        response = client.post("/devices", json=device_data)
        assert response.status_code == 200
        device = response.json()
        device_id = device["id"]
        
        assert device["ip_address"] == "192.168.1.100"
        assert device["description"] == "Test Router"
        assert device["is_active"] is True
        
        # Get device
        response = client.get(f"/devices/{device_id}")
        assert response.status_code == 200
        device_info = response.json()
        
        assert device_info["ip_address"] == "192.168.1.100"
        assert device_info["availability_percentage"] == 0.0  # No ping history yet
        
        # Update device
        update_data = {
            "description": "Updated Test Router",
            "tags": ["router", "gateway", "updated"]
        }
        
        response = client.put(f"/devices/{device_id}", json=update_data)
        assert response.status_code == 200
        updated_device = response.json()
        
        assert updated_device["description"] == "Updated Test Router"
        
        # List devices
        response = client.get("/devices")
        assert response.status_code == 200
        devices = response.json()
        
        assert len(devices) >= 1
        device_found = any(d["id"] == device_id for d in devices)
        assert device_found
        
        # Delete device
        response = client.delete(f"/devices/{device_id}")
        assert response.status_code == 200
        
        # Verify device is deactivated
        response = client.get(f"/devices/{device_id}")
        assert response.status_code == 200
        device_info = response.json()
        assert device_info["is_active"] is False
    
    @pytest.mark.asyncio
    async def test_ping_integration(self, client, db_session):
        """Test ping functionality with mocked ping service"""
        
        # Create a test device
        device_data = {
            "ip_address": "8.8.8.8",
            "description": "Google DNS",
            "tags": ["dns", "google"]
        }
        
        response = client.post("/devices", json=device_data)
        assert response.status_code == 200
        device_id = response.json()["id"]
        
        # Mock ping service to return success
        with patch('app.ping_service.PingService.ping_device') as mock_ping:
            mock_ping.return_value = {
                "is_alive": True,
                "response_time": 15.5,
                "packet_loss": 0.0,
                "error_message": None
            }
            
            # Manual ping
            response = client.post(f"/devices/{device_id}/ping")
            assert response.status_code == 200
            ping_result = response.json()
            
            assert ping_result["device_id"] == device_id
            assert ping_result["ping_result"]["is_alive"] is True
            assert ping_result["ping_result"]["response_time"] == 15.5
        
        # Check ping history
        response = client.get(f"/devices/{device_id}/ping-history")
        assert response.status_code == 200
        history = response.json()
        
        assert len(history["ping_history"]) >= 1
        assert history["ping_history"][0]["is_alive"] is True
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        metrics_content = response.text
        assert "netmon_ping_requests_total" in metrics_content
        assert "netmon_device_availability" in metrics_content
        assert "netmon_ping_response_time_seconds" in metrics_content
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        health = response.json()
        
        assert health["status"] == "healthy"
        assert "monitoring_active" in health
        assert health["service"] == "NetMon Box"
    
    def test_api_documentation(self, client):
        """Test that API documentation is accessible"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_root_endpoint(self, client):
        """Test root endpoint with HTML interface"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        html_content = response.text
        assert "NetMon Box" in html_content
        assert "API Endpoints" in html_content 