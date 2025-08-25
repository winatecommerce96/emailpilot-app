"""
Integration tests for Klaviyo OAuth flow and auto-client creation
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore

from app.repositories.clients_repo import ClientsRepository
from app.services.crypto_service import CryptoService
from app.services.klaviyo_oauth_service import (
    KlaviyoAccount,
    KlaviyoOAuthService,
    OAuthToken,
)


@pytest.fixture
def mock_firestore_client():
    """Mock Firestore client"""
    mock_db = MagicMock(spec=firestore.Client)
    return mock_db


@pytest.fixture
def mock_secret_manager():
    """Mock Secret Manager service"""
    mock_sm = MagicMock()
    mock_sm.create_or_update_secret = MagicMock(return_value=True)
    mock_sm.get_secret = MagicMock(return_value="test-secret")
    return mock_sm


@pytest.fixture
def crypto_service():
    """Real crypto service for testing"""
    return CryptoService()


@pytest.fixture
def klaviyo_oauth_service():
    """Klaviyo OAuth service with test configuration"""
    return KlaviyoOAuthService(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/api/integrations/klaviyo/oauth/callback",
        scopes=["accounts:read", "lists:read"]
    )


@pytest.fixture
def sample_oauth_token():
    """Sample OAuth token"""
    return OAuthToken(
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        expires_in=3600,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        scope="accounts:read lists:read",
        token_type="Bearer"
    )


@pytest.fixture
def sample_klaviyo_account():
    """Sample Klaviyo account"""
    return KlaviyoAccount(
        id="acc_123",
        name="Test Company",
        email_domain="test.com",
        company_id="comp_123",
        contact_email="admin@test.com",
        lists_count=5,
        segments_count=10,
        test_account=False,
        metadata={
            "timezone": "America/New_York",
            "preferred_currency": "USD"
        }
    )


class TestKlaviyoOAuthService:
    """Test Klaviyo OAuth service"""
    
    def test_generate_pkce_pair(self, klaviyo_oauth_service):
        """Test PKCE pair generation"""
        verifier, challenge = klaviyo_oauth_service.generate_pkce_pair()
        
        # Verify verifier length (43-128 characters)
        assert 43 <= len(verifier) <= 128
        
        # Verify challenge is base64url encoded
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in challenge)
        
        # Verify different pairs are generated
        verifier2, challenge2 = klaviyo_oauth_service.generate_pkce_pair()
        assert verifier != verifier2
        assert challenge != challenge2
    
    def test_build_auth_url(self, klaviyo_oauth_service):
        """Test authorization URL building"""
        state = "test-state-123"
        verifier, challenge = klaviyo_oauth_service.generate_pkce_pair()
        
        auth_url = klaviyo_oauth_service.build_auth_url(state, challenge)
        
        # Verify URL components
        assert "https://www.klaviyo.com/oauth/authorize" in auth_url
        assert f"client_id=test-client-id" in auth_url
        assert f"state={state}" in auth_url
        assert f"code_challenge={challenge}" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=accounts%3Aread+lists%3Aread" in auth_url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, klaviyo_oauth_service):
        """Test authorization code exchange"""
        with patch.object(klaviyo_oauth_service.http_client, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "scope": "accounts:read lists:read",
                "token_type": "Bearer"
            }
            mock_post.return_value = mock_response
            
            token = await klaviyo_oauth_service.exchange_code_for_token("auth-code-123", "verifier-123")
            
            assert token.access_token == "new-access-token"
            assert token.refresh_token == "new-refresh-token"
            assert token.expires_in == 3600
            assert token.scope == "accounts:read lists:read"
            
            # Verify the request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == klaviyo_oauth_service.TOKEN_ENDPOINT
            assert call_args[1]["data"]["code"] == "auth-code-123"
            assert call_args[1]["data"]["code_verifier"] == "verifier-123"
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, klaviyo_oauth_service):
        """Test token refresh"""
        with patch.object(klaviyo_oauth_service.http_client, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "refreshed-access-token",
                "refresh_token": "refreshed-refresh-token",
                "expires_in": 3600,
                "scope": "accounts:read lists:read",
                "token_type": "Bearer"
            }
            mock_post.return_value = mock_response
            
            new_token = await klaviyo_oauth_service.refresh_token("old-refresh-token")
            
            assert new_token.access_token == "refreshed-access-token"
            assert new_token.refresh_token == "refreshed-refresh-token"
            
            # Verify the request
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]["data"]["refresh_token"] == "old-refresh-token"
            assert call_args[1]["data"]["grant_type"] == "refresh_token"
    
    @pytest.mark.asyncio
    async def test_get_account_profile(self, klaviyo_oauth_service):
        """Test fetching account profile"""
        with patch.object(klaviyo_oauth_service.http_client, 'get') as mock_get:
            # Mock accounts response
            accounts_response = MagicMock()
            accounts_response.status_code = 200
            accounts_response.json.return_value = {
                "data": [{
                    "id": "acc_456",
                    "attributes": {
                        "account_name": "Test Account",
                        "email_domain": "example.com",
                        "company_id": "comp_456",
                        "contact_email": "contact@example.com",
                        "test_account": False,
                        "timezone": "UTC",
                        "preferred_currency": "EUR"
                    }
                }]
            }
            
            # Mock lists response
            lists_response = MagicMock()
            lists_response.status_code = 200
            lists_response.json.return_value = {
                "meta": {"total_count": 8}
            }
            
            # Mock segments response
            segments_response = MagicMock()
            segments_response.status_code = 200
            segments_response.json.return_value = {
                "meta": {"total_count": 15}
            }
            
            mock_get.side_effect = [accounts_response, lists_response, segments_response]
            
            account = await klaviyo_oauth_service.get_account_profile("test-token")
            
            assert account.id == "acc_456"
            assert account.name == "Test Account"
            assert account.email_domain == "example.com"
            assert account.lists_count == 8
            assert account.segments_count == 15
            assert account.metadata["timezone"] == "UTC"
            assert account.metadata["preferred_currency"] == "EUR"
    
    @pytest.mark.asyncio
    async def test_validate_token(self, klaviyo_oauth_service):
        """Test token validation"""
        with patch.object(klaviyo_oauth_service.http_client, 'get') as mock_get:
            # Valid token
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            is_valid = await klaviyo_oauth_service.validate_token("valid-token")
            assert is_valid is True
            
            # Invalid token
            mock_response.status_code = 401
            is_valid = await klaviyo_oauth_service.validate_token("invalid-token")
            assert is_valid is False


class TestClientsRepository:
    """Test clients repository"""
    
    @pytest.mark.asyncio
    async def test_find_by_owner_and_klaviyo_account(self, mock_firestore_client):
        """Test finding client by owner and Klaviyo account"""
        # Mock Firestore query
        mock_query = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "client_id": "client_123",
            "owner_user_id": "user@example.com",
            "klaviyo": {"account_id": "acc_123"},
            "display_name": "Test Client",
            "status": "active"
        }
        mock_query.stream.return_value = [mock_doc]
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_query
        
        repo = ClientsRepository(mock_firestore_client)
        client = await repo.find_by_owner_and_klaviyo_account("user@example.com", "acc_123")
        
        assert client is not None
        assert client.client_id == "client_123"
        assert client.owner_user_id == "user@example.com"
    
    @pytest.mark.asyncio
    async def test_upsert_client_from_klaviyo_new(
        self,
        mock_firestore_client,
        sample_klaviyo_account,
        sample_oauth_token,
        crypto_service
    ):
        """Test creating new client from Klaviyo OAuth"""
        # Mock no existing client
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_query
        
        # Mock document creation
        mock_doc_ref = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        repo = ClientsRepository(mock_firestore_client)
        
        encrypted_tokens = {
            "access_token": crypto_service.encrypt(sample_oauth_token.access_token),
            "refresh_token": crypto_service.encrypt(sample_oauth_token.refresh_token)
        }
        
        client = await repo.upsert_client_from_klaviyo(
            "user@example.com",
            sample_klaviyo_account,
            sample_oauth_token,
            encrypted_tokens
        )
        
        assert client.owner_user_id == "user@example.com"
        assert client.display_name == "Test Company"
        assert client.klaviyo["account_id"] == "acc_123"
        assert client.source == "klaviyo"
        assert "oauth" in client.tags
        assert "new" in client.tags
        
        # Verify document was created
        mock_doc_ref.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upsert_client_from_klaviyo_update(
        self,
        mock_firestore_client,
        sample_klaviyo_account,
        sample_oauth_token,
        crypto_service
    ):
        """Test updating existing client from Klaviyo OAuth"""
        # Mock existing client
        existing_client_data = {
            "client_id": "existing_123",
            "owner_user_id": "user@example.com",
            "klaviyo": {"account_id": "acc_123"},
            "display_name": "Old Name",
            "status": "active",
            "tags": ["existing"]
        }
        
        mock_query = MagicMock()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = existing_client_data
        mock_query.stream.return_value = [mock_doc]
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_firestore_client.collection.return_value = mock_query
        
        # Mock document update
        mock_doc_ref = MagicMock()
        mock_updated_doc = MagicMock()
        mock_updated_doc.to_dict.return_value = {
            **existing_client_data,
            "display_name": sample_klaviyo_account.name,
            "tags": ["existing", "oauth"]
        }
        mock_doc_ref.get.return_value = mock_updated_doc
        mock_firestore_client.collection.return_value.document.return_value = mock_doc_ref
        
        repo = ClientsRepository(mock_firestore_client)
        
        encrypted_tokens = {
            "access_token": crypto_service.encrypt(sample_oauth_token.access_token),
            "refresh_token": crypto_service.encrypt(sample_oauth_token.refresh_token)
        }
        
        client = await repo.upsert_client_from_klaviyo(
            "user@example.com",
            sample_klaviyo_account,
            sample_oauth_token,
            encrypted_tokens
        )
        
        assert client.client_id == "existing_123"
        assert client.display_name == "Test Company"
        assert "oauth" in client.tags
        
        # Verify document was updated
        mock_doc_ref.update.assert_called_once()


class TestCryptoService:
    """Test crypto service"""
    
    def test_encrypt_decrypt(self, crypto_service):
        """Test encryption and decryption"""
        plain_text = "secret-token-12345"
        
        encrypted = crypto_service.encrypt(plain_text)
        assert encrypted != plain_text
        assert len(encrypted) > 0
        
        decrypted = crypto_service.decrypt(encrypted)
        assert decrypted == plain_text
    
    def test_encrypt_decrypt_dict(self, crypto_service):
        """Test dictionary encryption and decryption"""
        data = {
            "access_token": "token-123",
            "refresh_token": "refresh-456",
            "api_key": None
        }
        
        encrypted_dict = crypto_service.encrypt_dict(data)
        assert encrypted_dict["access_token"] != "token-123"
        assert encrypted_dict["refresh_token"] != "refresh-456"
        assert encrypted_dict["api_key"] is None
        
        decrypted_dict = crypto_service.decrypt_dict(encrypted_dict)
        assert decrypted_dict["access_token"] == "token-123"
        assert decrypted_dict["refresh_token"] == "refresh-456"
        assert decrypted_dict["api_key"] is None
    
    def test_hash_value(self, crypto_service):
        """Test value hashing"""
        value = "test-value"
        hash1 = crypto_service.hash_value(value)
        hash2 = crypto_service.hash_value(value)
        
        # Same value should produce same hash
        assert hash1 == hash2
        
        # Different value should produce different hash
        hash3 = crypto_service.hash_value("different-value")
        assert hash3 != hash1
    
    def test_needs_refresh(self, crypto_service):
        """Test token refresh check"""
        # Token expires in 10 minutes - needs refresh
        expires_soon = datetime.utcnow() + timedelta(minutes=3)
        assert crypto_service.needs_refresh(expires_soon, buffer_minutes=5) is True
        
        # Token expires in 1 hour - doesn't need refresh
        expires_later = datetime.utcnow() + timedelta(hours=1)
        assert crypto_service.needs_refresh(expires_later, buffer_minutes=5) is False
        
        # No expiration - doesn't need refresh
        assert crypto_service.needs_refresh(None) is False


# Integration test for the full OAuth flow
@pytest.mark.integration
class TestFullOAuthFlow:
    """Test the complete OAuth flow end-to-end"""
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self):
        """Test complete OAuth flow from start to client creation"""
        # This would require a test instance of the FastAPI app
        # and mocked external services
        
        # TODO: Implement with TestClient when app is available
        pass