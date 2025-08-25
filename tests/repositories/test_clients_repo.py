"""
Unit tests for clients repository
"""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from google.cloud import firestore

from app.repositories.clients_repo import Client, ClientsRepository
from app.services.klaviyo_oauth_service import KlaviyoAccount, OAuthToken


@pytest.fixture
def mock_firestore():
    """Mock Firestore client"""
    return MagicMock(spec=firestore.Client)


@pytest.fixture
def clients_repo(mock_firestore):
    """Clients repository with mocked Firestore"""
    return ClientsRepository(mock_firestore)


@pytest.fixture
def sample_client_data():
    """Sample client data"""
    return {
        "client_id": str(uuid.uuid4()),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "owner_user_id": "test@example.com",
        "source": "klaviyo",
        "display_name": "Test Client",
        "status": "active",
        "tags": ["new", "oauth"],
        "klaviyo": {
            "account_id": "kl_123",
            "account_name": "Test Account",
            "email_domain": "test.com",
            "lists_count": 10,
            "segments_count": 5
        },
        "oauth": {
            "provider": "klaviyo",
            "access_token": "encrypted_token",
            "refresh_token": "encrypted_refresh",
            "expires_at": datetime.utcnow(),
            "scopes": ["accounts:read", "lists:read"]
        },
        "name": "Test Client",
        "description": "Test client description",
        "is_active": True,
        "contact_email": "contact@test.com",
        "contact_name": "Test Contact",
        "website": "https://test.com",
        "metric_id": "metric_123",
        "klaviyo_api_key": ""
    }


class TestClient:
    """Test Client model"""
    
    def test_client_initialization(self, sample_client_data):
        """Test client initialization with data"""
        client = Client(**sample_client_data)
        
        assert client.client_id == sample_client_data["client_id"]
        assert client.owner_user_id == sample_client_data["owner_user_id"]
        assert client.source == "klaviyo"
        assert client.display_name == "Test Client"
        assert client.status == "active"
        assert "oauth" in client.tags
        assert client.klaviyo["account_id"] == "kl_123"
    
    def test_client_to_dict(self, sample_client_data):
        """Test converting client to dictionary"""
        client = Client(**sample_client_data)
        client_dict = client.to_dict()
        
        assert client_dict["client_id"] == sample_client_data["client_id"]
        assert client_dict["owner_user_id"] == sample_client_data["owner_user_id"]
        assert client_dict["klaviyo"] == sample_client_data["klaviyo"]
        assert client_dict["oauth"] == sample_client_data["oauth"]
        assert client_dict["is_active"] is True
    
    def test_client_from_dict(self, sample_client_data):
        """Test creating client from dictionary"""
        client = Client.from_dict(sample_client_data)
        
        assert client.client_id == sample_client_data["client_id"]
        assert client.owner_user_id == sample_client_data["owner_user_id"]
        assert client.klaviyo == sample_client_data["klaviyo"]
    
    def test_client_defaults(self):
        """Test client with minimal data uses defaults"""
        client = Client(owner_user_id="user@example.com")
        
        assert client.client_id is not None  # UUID generated
        assert client.source == "klaviyo"
        assert client.status == "active"
        assert client.tags == []
        assert client.display_name == ""
        assert client.is_active is True


class TestClientsRepository:
    """Test ClientsRepository"""
    
    @pytest.mark.asyncio
    async def test_find_by_owner_and_klaviyo_account_found(self, clients_repo, mock_firestore, sample_client_data):
        """Test finding existing client"""
        # Mock query result
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = sample_client_data
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_firestore.collection.return_value = mock_query
        
        client = await clients_repo.find_by_owner_and_klaviyo_account(
            "test@example.com",
            "kl_123"
        )
        
        assert client is not None
        assert client.owner_user_id == "test@example.com"
        assert client.klaviyo["account_id"] == "kl_123"
    
    @pytest.mark.asyncio
    async def test_find_by_owner_and_klaviyo_account_not_found(self, clients_repo, mock_firestore):
        """Test finding non-existent client"""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_firestore.collection.return_value = mock_query
        
        client = await clients_repo.find_by_owner_and_klaviyo_account(
            "test@example.com",
            "kl_999"
        )
        
        assert client is None
    
    @pytest.mark.asyncio
    async def test_get_client(self, clients_repo, mock_firestore, sample_client_data):
        """Test getting client by ID"""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_client_data
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        client = await clients_repo.get_client(sample_client_data["client_id"])
        
        assert client is not None
        assert client.client_id == sample_client_data["client_id"]
    
    @pytest.mark.asyncio
    async def test_get_client_not_found(self, clients_repo, mock_firestore):
        """Test getting non-existent client"""
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        client = await clients_repo.get_client("nonexistent")
        
        assert client is None
    
    @pytest.mark.asyncio
    async def test_list_clients(self, clients_repo, mock_firestore, sample_client_data):
        """Test listing clients with filters"""
        mock_doc1 = MagicMock()
        mock_doc1.to_dict.return_value = sample_client_data
        
        mock_doc2 = MagicMock()
        client2_data = {**sample_client_data, "client_id": str(uuid.uuid4())}
        mock_doc2.to_dict.return_value = client2_data
        
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_firestore.collection.return_value = mock_query
        
        # Test with filters
        clients = await clients_repo.list_clients(
            user_id="test@example.com",
            source="klaviyo",
            status="active",
            limit=10
        )
        
        assert len(clients) == 2
        assert all(c.owner_user_id == "test@example.com" for c in clients)
        assert all(c.source == "klaviyo" for c in clients)
    
    @pytest.mark.asyncio
    async def test_update_oauth_tokens(self, clients_repo, mock_firestore):
        """Test updating OAuth tokens"""
        mock_doc_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref
        
        encrypted_tokens = {
            "access_token": "new_encrypted_token",
            "refresh_token": "new_encrypted_refresh"
        }
        expires_at = datetime.utcnow()
        
        success = await clients_repo.update_oauth_tokens(
            "client_123",
            encrypted_tokens,
            expires_at
        )
        
        assert success is True
        
        # Verify update was called with correct data
        mock_doc_ref.update.assert_called_once()
        update_data = mock_doc_ref.update.call_args[0][0]
        assert "oauth.access_token" in update_data
        assert "oauth.refresh_token" in update_data
        assert "oauth.expires_at" in update_data
        assert "oauth.last_refreshed" in update_data
    
    @pytest.mark.asyncio
    async def test_update_oauth_tokens_error(self, clients_repo, mock_firestore):
        """Test handling error when updating tokens"""
        mock_doc_ref = MagicMock()
        mock_doc_ref.update.side_effect = Exception("Firestore error")
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref
        
        encrypted_tokens = {
            "access_token": "new_encrypted_token",
            "refresh_token": "new_encrypted_refresh"
        }
        
        success = await clients_repo.update_oauth_tokens(
            "client_123",
            encrypted_tokens
        )
        
        assert success is False


class TestIdempotency:
    """Test idempotent operations"""
    
    @pytest.mark.asyncio
    async def test_upsert_idempotency(self, clients_repo, mock_firestore):
        """Test that upsert is idempotent"""
        # First call - create new client
        mock_query = MagicMock()
        mock_query.stream.return_value = []  # No existing client
        mock_query.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_firestore.collection.return_value = mock_query
        
        mock_doc_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref
        
        account = KlaviyoAccount(
            id="kl_456",
            name="Test Account",
            email_domain="test.com"
        )
        
        token = OAuthToken(
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.utcnow()
        )
        
        encrypted_tokens = {
            "access_token": "encrypted",
            "refresh_token": "encrypted_refresh"
        }
        
        # First upsert - creates new
        client1 = await clients_repo.upsert_client_from_klaviyo(
            "user@example.com",
            account,
            token,
            encrypted_tokens
        )
        
        assert client1.owner_user_id == "user@example.com"
        assert mock_doc_ref.set.called
        
        # Second call - update existing
        existing_data = client1.to_dict()
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = existing_data
        mock_query.stream.return_value = [mock_doc]  # Existing client found
        
        mock_updated_doc = MagicMock()
        mock_updated_doc.to_dict.return_value = {
            **existing_data,
            "updated_at": datetime.utcnow()
        }
        mock_doc_ref.get.return_value = mock_updated_doc
        
        # Second upsert - updates existing
        client2 = await clients_repo.upsert_client_from_klaviyo(
            "user@example.com",
            account,
            token,
            encrypted_tokens
        )
        
        assert client2.client_id == client1.client_id  # Same client
        assert mock_doc_ref.update.called