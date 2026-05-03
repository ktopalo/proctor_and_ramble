import pytest
import json
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from fastapi.testclient import TestClient
from backend.main import app, manager as session_manager


@pytest.fixture(autouse=True)
def reset_session():
    from backend.main import connection_manager
    connection_manager.active_connections.clear()
    yield


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_load_question_missing_url():
    response = client.post("/question/load", json={})
    assert response.status_code == 422


def test_start_session_missing_watch_path():
    response = client.post("/session/start", json={})
    assert response.status_code == 422


def test_start_session():
    response = client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    assert response.status_code == 200
    assert response.json()["status"] == "started"


def test_end_session():
    client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    response = client.post("/session/end")
    assert response.status_code == 200
    assert response.json()["status"] == "ended"


def test_get_snapshot():
    client.post("/session/start", json={"watch_path": "/tmp/test.py"})
    response = client.get("/session/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert "interjections" in data
