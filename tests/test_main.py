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


@pytest.mark.asyncio
async def test_on_interjection_enqueues_tts():
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime, timezone
    import backend.main as main_module
    from backend.session.models import Interjection

    mock_player = MagicMock()
    mock_player.enqueue = AsyncMock()
    original = main_module.tts_player
    main_module.tts_player = mock_player
    try:
        interjection = Interjection(
            text="Can you walk me through your approach?",
            timestamp=datetime.now(timezone.utc),
            trigger="speech_pause",
        )
        await main_module._on_interjection(interjection)
        mock_player.enqueue.assert_called_once_with(
            "Can you walk me through your approach?"
        )
    finally:
        main_module.tts_player = original
