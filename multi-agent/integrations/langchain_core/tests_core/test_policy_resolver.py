"""Tests for ModelPolicyResolver cascade and enforcement."""

import pytest
from unittest.mock import Mock, patch
from datetime import date
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deps import ModelPolicyResolver


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    mock_db = Mock()
    return mock_db


@pytest.fixture
def mock_config():
    """Mock config with defaults."""
    config = Mock()
    config.firestore_project = 'test-project'
    config.lc_provider = 'gemini'
    config.lc_model = 'gemini-1.5-flash'
    config.lc_temperature = 0.7
    config.lc_max_tokens = 2048
    return config


def test_policy_cascade_priority(mock_firestore, mock_config):
    """Test that user policy overrides brand which overrides global."""
    resolver = ModelPolicyResolver(mock_config)
    resolver._db = mock_firestore
    
    # Mock policies at different levels
    global_doc = Mock()
    global_doc.exists = True
    global_doc.to_dict.return_value = {
        'provider': 'gemini',
        'model': 'gemini-1.5-flash',
        'temperature': 0.7
    }
    
    brand_doc = Mock()
    brand_doc.exists = True
    brand_doc.to_dict.return_value = {
        'provider': 'openai',
        'model': 'gpt-4',
        'temperature': 0.5
    }
    
    user_doc = Mock()
    user_doc.exists = True  
    user_doc.to_dict.return_value = {
        'provider': 'anthropic',
        'model': 'claude-3-opus',
        'temperature': 0.3
    }
    
    def mock_get_doc(doc_id):
        doc_ref = Mock()
        if 'global' in doc_id:
            doc_ref.get.return_value = global_doc
        elif 'brand' in doc_id:
            doc_ref.get.return_value = brand_doc
        elif 'user' in doc_id:
            doc_ref.get.return_value = user_doc
        return doc_ref
    
    mock_firestore.collection.return_value.document.side_effect = mock_get_doc
    
    # Test cascade
    result = resolver.resolve(user_id='test_user', brand='test_brand')
    
    # User settings should win
    assert result['provider'] == 'anthropic'
    assert result['model'] == 'claude-3-opus'
    assert result['temperature'] == 0.3
    assert result['cascade_level'] == 'user'


def test_allowlist_enforcement(mock_firestore, mock_config):
    """Test that allowlist restricts available models."""
    resolver = ModelPolicyResolver(mock_config)
    resolver._db = mock_firestore
    
    # Mock policy with allowlist
    policy_doc = Mock()
    policy_doc.exists = True
    policy_doc.to_dict.return_value = {
        'provider': 'openai',
        'model': 'gpt-4-turbo',  # Not in allowlist
        'allowlist': ['openai:gpt-4', 'anthropic:claude-3-opus']
    }
    
    mock_doc_ref = Mock()
    mock_doc_ref.get.return_value = policy_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Resolve with enforcement
    result = resolver.resolve(user_id='test_user', enforce_limits=True)
    
    # Should downgrade to first allowed model
    assert result['provider'] == 'openai'
    assert result['model'] == 'gpt-4'
    assert result['tier'] == 'downgraded'


def test_blocklist_enforcement(mock_firestore, mock_config):
    """Test that blocklist prevents specific models."""
    resolver = ModelPolicyResolver(mock_config)
    resolver._db = mock_firestore
    
    # Mock policy with blocklist
    policy_doc = Mock()
    policy_doc.exists = True
    policy_doc.to_dict.return_value = {
        'provider': 'openai',
        'model': 'gpt-4',
        'blocklist': ['openai:gpt-4', 'openai:gpt-3.5-turbo']
    }
    
    mock_doc_ref = Mock()
    mock_doc_ref.get.return_value = policy_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Resolve with enforcement
    result = resolver.resolve(user_id='test_user', enforce_limits=True)
    
    # Should fallback to gemini
    assert result['provider'] == 'gemini'
    assert result['model'] == 'gemini-1.5-flash'
    assert result['tier'] == 'blocked_fallback'


def test_daily_limit_enforcement(mock_firestore, mock_config):
    """Test that exceeding daily limit downgrades model."""
    resolver = ModelPolicyResolver(mock_config)
    resolver._db = mock_firestore
    
    # Mock policy with limits
    policy_doc = Mock()
    policy_doc.exists = True
    policy_doc.to_dict.return_value = {
        'provider': 'openai',
        'model': 'gpt-4',
        'limits': {'daily_tokens': 10000}
    }
    
    # Mock usage exceeding limit
    usage_doc = Mock()
    usage_doc.exists = True
    usage_doc.to_dict.return_value = {
        'totals': {'total_tokens': 15000}  # Over limit
    }
    
    def mock_get_doc(doc_id):
        doc_ref = Mock()
        if 'model_policies' in str(mock_firestore.collection.call_args):
            doc_ref.get.return_value = policy_doc
        else:  # token_usage_daily
            doc_ref.get.return_value = usage_doc
        return doc_ref
    
    mock_firestore.collection.return_value.document.side_effect = mock_get_doc
    
    # Resolve with enforcement
    result = resolver.resolve(user_id='test_user', enforce_limits=True)
    
    # Should downgrade due to limit
    assert result['provider'] == 'gemini'
    assert result['model'] == 'gemini-1.5-flash'
    assert result['tier'] == 'limit_exceeded'


def test_get_available_models_with_filters(mock_firestore, mock_config):
    """Test getting available models with allowlist/blocklist filters."""
    resolver = ModelPolicyResolver(mock_config)
    resolver._db = mock_firestore
    
    # Mock policy with both lists
    policy_doc = Mock()
    policy_doc.exists = True
    policy_doc.to_dict.return_value = {
        'provider': 'openai',
        'model': 'gpt-4',
        'allowlist': [
            'openai:gpt-4',
            'anthropic:claude-3-opus',
            'gemini:gemini-1.5-pro'
        ],
        'blocklist': ['openai:gpt-3.5-turbo']
    }
    
    mock_doc_ref = Mock()
    mock_doc_ref.get.return_value = policy_doc
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Get available models
    models = resolver.get_available_models(user_id='test_user')
    
    # Should only include allowed models
    model_keys = [f"{m['provider']}:{m['model']}" for m in models]
    assert 'openai:gpt-4' in model_keys
    assert 'anthropic:claude-3-opus' in model_keys
    assert 'gemini:gemini-1.5-pro' in model_keys
    assert 'openai:gpt-3.5-turbo' not in model_keys  # Blocked
    
    # Check selected flag
    selected = [m for m in models if m.get('selected')]
    assert len(selected) == 1
    assert selected[0]['model'] == 'gpt-4'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])