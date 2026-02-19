from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_negotiation_accepts_extraction_tasks():
    payload = {
        "task_summary": "Extract tables from PDF invoices",
        "task_details": "Process invoice PDFs and extract structured data",
        "input_mime_types": ["application/pdf"],
        "output_mime_types": ["application/json"],
        "max_latency_ms": 5000,
        "max_cost_amount": "0.001",
        "min_score": 0.7,
        "weights": {
            "skill_match": 0.6,
            "io_compatibility": 0.2,
            "performance": 0.1,
            "load": 0.05,
            "cost": 0.05
        }
    }
    
    response = client.post("/agent/negotiation", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["accepted"] is True
    assert data["score"] >= 0.7
    assert data["confidence"] == 0.95
    assert isinstance(data["skill_matches"], list)
    assert data["skill_matches"][0]["skill_id"] == "data-extraction-v1"

def test_negotiation_rejects_unrelated_tasks():
    payload = {
        "task_summary": "Write a creative fiction story about a magical forest.",
        "min_score": 0.7,
        "weights": {
            "skill_match": 0.6,
            "io_compatibility": 0.2,
            "performance": 0.1,
            "load": 0.05,
            "cost": 0.05
        }
    }
    
    response = client.post("/agent/negotiation", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["accepted"] is False
    assert data["score"] < 0.7
