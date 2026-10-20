import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "scanner_engine" in data
    assert "docker_connected" in data


def test_list_used_ports():
    res = client.get("/api/v1/ports/used")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert isinstance(data["ports"], list)


def test_get_random_port():
    res = client.get("/api/v1/ports/random?min=50000&max=50100&protocol=tcp")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "free"
    assert 50000 <= data["port"] <= 50100
    assert data["protocol"] == "tcp"


def test_get_random_port_invalid_proto():
    res = client.get("/api/v1/ports/random?min=8000&max=9000&protocol=invalid")
    assert res.status_code == 400


def test_check_port():
    res = client.get("/api/v1/ports/check/52345?protocol=tcp")
    assert res.status_code == 200
    data = res.json()
    assert data["port"] == 52345
    assert "free" in data
    assert "status" in data
