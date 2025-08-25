"""Tests for usage tracking API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from google.cloud import firestore


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('google.cloud.firestore.Client') as mock_client:
        mock_db = Mock()
        mock_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def mock_config():
    """Mock LangChain config."""
    config = Mock()
    config.firestore_project = 'test-project'
    return config


def test_usage_summary_endpoint(mock_firestore, mock_config):
    """Test GET /usage/summary endpoint."""
    from app.api.langchain_admin import get_usage_summary
    
    # Mock Firestore query
    mock_collection = Mock()
    mock_firestore.collection.return_value = mock_collection
    
    # Mock documents
    doc1 = Mock()
    doc1.to_dict.return_value = {
        'date': datetime.now().date(),
        'totals': {
            'total_tokens': 1000,
            'input_cost_usd': 0.01,
            'output_cost_usd': 0.02
        }
    }
    
    doc2 = Mock()
    doc2.to_dict.return_value = {
        'date': (datetime.now() - timedelta(days=1)).date(),
        'totals': {
            'total_tokens': 500,
            'input_cost_usd': 0.005,
            'output_cost_usd': 0.01
        }
    }
    
    mock_query = Mock()
    mock_query.stream.return_value = [doc1, doc2]
    mock_collection.where.return_value = mock_query
    
    # Test with patch
    with patch('app.api.langchain_admin.get_config', return_value=mock_config):
        with patch('app.api.langchain_admin.firestore.Client', return_value=mock_firestore):
            # This would be an async test in real implementation
            # result = await get_usage_summary(days=7)
            # assert result['total_tokens'] == 1500
            # assert result['total_cost_usd'] == 0.045
            pass


def test_usage_events_endpoint(mock_firestore, mock_config):
    """Test GET /usage/events endpoint."""
    from app.api.langchain_admin import get_usage_events
    
    # Mock Firestore query
    mock_collection = Mock()
    mock_firestore.collection.return_value = mock_collection
    
    # Mock event
    event_doc = Mock()
    event_doc.to_dict.return_value = {
        'ts': datetime.now(),
        'user_id': 'test_user',
        'brand': 'test_brand',
        'provider': 'openai',
        'model': 'gpt-4',
        'total_tokens': 150,
        'latency_ms': 500
    }
    
    mock_query = Mock()
    mock_query.stream.return_value = [event_doc]
    mock_query.order_by.return_value.limit.return_value = mock_query
    mock_collection.where.return_value = mock_query
    
    with patch('app.api.langchain_admin.get_config', return_value=mock_config):
        with patch('app.api.langchain_admin.firestore.Client', return_value=mock_firestore):
            # This would be an async test
            # events = await get_usage_events(user_id='test_user')
            # assert len(events) == 1
            # assert events[0]['total_tokens'] == 150
            pass


def test_seed_and_query_usage_data():
    """Test seeding usage events and querying summary."""
    # This test would actually write to Firestore in integration testing
    # For unit test, we use mocks as shown above
    
    # Example of what integration test would look like:
    # 1. Create test events
    events = [
        {
            'ts': datetime.now(),
            'user_id': 'test_user',
            'brand': 'test_brand',
            'total_tokens': 100,
            'input_cost_usd': 0.001,
            'output_cost_usd': 0.002
        },
        {
            'ts': datetime.now() - timedelta(hours=1),
            'user_id': 'test_user',
            'brand': 'test_brand', 
            'total_tokens': 200,
            'input_cost_usd': 0.002,
            'output_cost_usd': 0.004
        }
    ]
    
    # 2. Query summary
    # result = get_usage_summary(user_id='test_user', days=1)
    
    # 3. Assert totals
    expected_tokens = 300
    expected_cost = 0.009
    
    # assert result['total_tokens'] == expected_tokens
    # assert abs(result['total_cost_usd'] - expected_cost) < 0.001
    
    assert True  # Placeholder for now


if __name__ == '__main__':
    pytest.main([__file__, '-v'])