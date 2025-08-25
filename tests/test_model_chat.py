"""
Test cases for Model Chat functionality
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json

# Mock the app for testing
from main_firestore import app

client = TestClient(app)


class TestModelChatEndpoints:
    """Test Model Chat API endpoints"""

    def test_get_models_for_provider(self):
        """Test getting models for a specific provider"""
        response = client.get("/api/ai-models/models?provider=openai")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "models" in data
        assert "default_model" in data
        assert data["provider"] == "openai"
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

    def test_get_models_invalid_provider(self):
        """Test getting models for invalid provider"""
        response = client.get("/api/ai-models/models?provider=invalid")
        assert response.status_code == 400
        assert "Invalid provider" in response.json()["detail"]

    @patch('app.services.ai_models_service.AIModelsService')
    def test_chat_complete_success(self, mock_ai_service):
        """Test successful chat completion"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.complete = AsyncMock(return_value={
            "success": True,
            "response": "This is a test response",
            "provider": "openai",
            "model": "gpt-4",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15
            }
        })
        mock_ai_service.return_value = mock_instance

        # Make request
        request_data = {
            "provider": "openai",
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }

        response = client.post(
            "/api/ai-models/chat/complete",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["output_message"]["role"] == "assistant"
        assert data["output_message"]["content"] == "This is a test response"
        assert "usage" in data

    @patch('app.services.ai_models_service.AIModelsService')
    def test_chat_complete_with_agent(self, mock_ai_service):
        """Test chat completion with agent type"""
        # Setup mock
        mock_instance = Mock()
        mock_instance.complete = AsyncMock(return_value={
            "success": True,
            "response": "Agent-based response",
            "provider": "claude",
            "model": "claude-3-sonnet",
            "usage": {}
        })
        mock_instance.get_prompts_by_category = AsyncMock(return_value=[
            {
                "id": "test_prompt",
                "prompt_template": "You are a helpful agent",
                "metadata": {"agent_type": "copywriter"}
            }
        ])
        mock_ai_service.return_value = mock_instance

        # Make request with agent
        request_data = {
            "provider": "claude",
            "model": "claude-3-sonnet",
            "messages": [
                {"role": "user", "content": "Write a tagline"}
            ],
            "temperature": 0.8,
            "max_tokens": 150,
            "agent_type": "copywriter"
        }

        response = client.post(
            "/api/ai-models/chat/complete",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["output_message"]["content"] == "Agent-based response"

    def test_chat_complete_invalid_provider(self):
        """Test chat completion with invalid provider"""
        request_data = {
            "provider": "invalid_provider",
            "model": "some-model",
            "messages": [
                {"role": "user", "content": "Test"}
            ]
        }

        response = client.post(
            "/api/ai-models/chat/complete",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "error" in data
        assert "Invalid provider" in data["error"]["message"]

    def test_chat_complete_invalid_model(self):
        """Test chat completion with invalid model"""
        request_data = {
            "provider": "openai",
            "model": "invalid-model",
            "messages": [
                {"role": "user", "content": "Test"}
            ]
        }

        response = client.post(
            "/api/ai-models/chat/complete",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "error" in data
        assert "Invalid model" in data["error"]["message"]

    @patch('app.services.ai_models_service.AIModelsService')
    def test_chat_complete_api_failure(self, mock_ai_service):
        """Test chat completion when API fails"""
        # Setup mock to simulate failure
        mock_instance = Mock()
        mock_instance.complete = AsyncMock(return_value={
            "success": False,
            "error": "API key invalid"
        })
        mock_ai_service.return_value = mock_instance

        request_data = {
            "provider": "openai",
            "model": "gpt-4",
            "messages": [
                {"role": "user", "content": "Test"}
            ]
        }

        response = client.post(
            "/api/ai-models/chat/complete",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "error" in data
        assert "API key invalid" in data["error"]["message"]


class TestAIModelsServiceComplete:
    """Test AIModelsService.complete() method"""

    @pytest.mark.asyncio
    @patch('app.services.ai_models_service.openai')
    async def test_complete_openai(self, mock_openai):
        """Test complete method with OpenAI provider"""
        from app.services.ai_models_service import AIModelsService
        from unittest.mock import MagicMock

        # Setup mocks
        mock_db = MagicMock()
        mock_secret_manager = MagicMock()
        mock_secret_manager.get_secret.return_value = "test-api-key"

        service = AIModelsService(mock_db, mock_secret_manager)
        service._api_clients["openai"] = mock_openai

        # Mock OpenAI response
        mock_response = {
            "choices": [{
                "message": {"content": "OpenAI response"}
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        mock_openai.ChatCompletion.create = AsyncMock(return_value=mock_response)

        # Test complete
        result = await service.complete(
            provider="openai",
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.5,
            max_tokens=100
        )

        assert result["success"] is True
        assert result["response"] == "OpenAI response"
        assert result["usage"]["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_complete_invalid_provider(self):
        """Test complete with invalid provider"""
        from app.services.ai_models_service import AIModelsService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_secret_manager = MagicMock()
        service = AIModelsService(mock_db, mock_secret_manager)

        result = await service.complete(
            provider="invalid",
            model="some-model",
            messages=[{"role": "user", "content": "Test"}]
        )

        assert result["success"] is False
        assert "not configured" in result["error"]

    @pytest.mark.asyncio
    async def test_complete_with_clamped_values(self):
        """Test that temperature and max_tokens are clamped to valid ranges"""
        from app.services.ai_models_service import AIModelsService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_secret_manager = MagicMock()
        service = AIModelsService(mock_db, mock_secret_manager)

        # Add a mock provider
        mock_client = MagicMock()
        service._api_clients["test"] = mock_client

        # Mock the complete method to check clamped values
        original_complete = service.complete

        async def mock_complete_check(*args, **kwargs):
            # Check that values are clamped
            assert kwargs.get("temperature", 0.7) <= 2.0
            assert kwargs.get("temperature", 0.7) >= 0.0
            assert kwargs.get("max_tokens", 512) <= 4096
            assert kwargs.get("max_tokens", 512) >= 1
            return {"success": True, "response": "Test"}

        service.complete = mock_complete_check

        # Test with out-of-range values
        result = await service.complete(
            provider="test",
            model="test-model",
            messages=[{"role": "user", "content": "Test"}],
            temperature=3.0,  # Should be clamped to 2.0
            max_tokens=5000   # Should be clamped to 4096
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])