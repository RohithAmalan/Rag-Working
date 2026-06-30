from unittest.mock import MagicMock, patch

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@patch("app.routes.audit_routes.get_database")
def test_audit_log(mock_get_database):
    mock_db = MagicMock()
    mock_collection = MagicMock()

    # AsyncMock for the awaitable insert_one
    async def mock_insert_one(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.inserted_id = "test-id"
        return mock_result

    mock_collection.insert_one = mock_insert_one
    mock_db.__getitem__.return_value = mock_collection
    mock_get_database.return_value = mock_db

    payload = {
        "event": "test_event",
        "severity": "info",
        "username": "test_user",
        "details": {"key": "value"},
        "source": "test_source",
    }

    response = client.post("/audit/log", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged"
    assert data["event"] == "test_event"


@patch("app.routes.audit_routes.get_database")
def test_audit_alert(mock_get_database):
    mock_db = MagicMock()
    mock_collection = MagicMock()

    async def mock_insert_one(*args, **kwargs):
        mock_result = MagicMock()
        mock_result.inserted_id = "alert-id"
        return mock_result

    mock_collection.insert_one = mock_insert_one
    mock_db.__getitem__.return_value = mock_collection
    mock_get_database.return_value = mock_db

    payload = {
        "alert_type": "security",
        "message": "test alert message",
        "event": "test_alert_event",
        "severity": "critical",
    }

    response = client.post("/audit/alert", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alert_logged"
    assert data["alert_type"] == "security"


@patch("app.routes.audit_routes.get_database")
def test_list_audit_events(mock_get_database):
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    async def mock_to_list(length):
        return [{"event": "event1"}, {"event": "event2"}]

    mock_cursor.to_list = mock_to_list
    mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor
    mock_db.__getitem__.return_value = mock_collection
    mock_get_database.return_value = mock_db

    response = client.get("/audit/events")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["events"]) == 2


@patch("app.routes.audit_routes.get_database")
def test_list_audit_alerts(mock_get_database):
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_cursor = MagicMock()

    async def mock_to_list(length):
        return [{"alert_type": "alert1"}]

    mock_cursor.to_list = mock_to_list
    mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor
    mock_db.__getitem__.return_value = mock_collection
    mock_get_database.return_value = mock_db

    response = client.get("/audit/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["alerts"]) == 1
