import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.n8n_service import notify_n8n_event

@pytest.mark.asyncio
@patch("app.services.n8n_service.settings")
@patch("app.services.n8n_service.httpx.AsyncClient")
async def test_notify_n8n_event(mock_client_cls, mock_settings):
    mock_settings.n8n_webhook_url = "http://test-webhook"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response
    
    # AsyncClient context manager returns the mock client
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    await notify_n8n_event("test_event", "info", "test_user")
    
    mock_client.post.assert_called_once_with(
        "http://test-webhook",
        json={
            "event": "test_event",
            "severity": "info",
            "username": "test_user",
            "details": {}
        }
    )

@pytest.mark.asyncio
@patch("app.services.n8n_service.settings")
@patch("app.services.n8n_service.httpx.AsyncClient")
async def test_notify_n8n_event_empty_url(mock_client_cls, mock_settings):
    mock_settings.n8n_webhook_url = ""
    await notify_n8n_event("test_event", "info", "test_user")
    mock_client_cls.assert_not_called()

@pytest.mark.asyncio
@patch("app.services.n8n_service.settings")
@patch("app.services.n8n_service.logger")
@patch("app.services.n8n_service.httpx.AsyncClient")
async def test_notify_n8n_event_error(mock_client_cls, mock_logger, mock_settings):
    mock_settings.n8n_webhook_url = "http://test-webhook"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value.__aenter__.return_value = mock_client
    
    await notify_n8n_event("test_event", "error", "test_user")
    mock_logger.warning.assert_called_once()
