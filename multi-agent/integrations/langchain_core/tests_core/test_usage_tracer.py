"""Tests for UsageTracer token metering."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.usage_tracer import UsageTracer, TokenUsage


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    mock_db = Mock()
    mock_collection = Mock()
    mock_db.collection.return_value = mock_collection
    return mock_db


@pytest.fixture
def mock_config():
    """Mock config."""
    config = Mock()
    config.firestore_project = 'test-project'
    return config


def test_usage_tracer_extracts_openai_format():
    """Test extraction of token usage from OpenAI format."""
    tracer = UsageTracer(user_id='test_user', agent='test_agent')
    
    # Mock OpenAI response
    response = Mock()
    response.llm_output = {
        'token_usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    }
    response.generations = []
    
    usage = tracer._extract_usage(response)
    
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    assert not usage.estimated


def test_usage_tracer_extracts_anthropic_format():
    """Test extraction of token usage from Anthropic format."""
    tracer = UsageTracer(user_id='test_user', agent='test_agent')
    
    # Mock Anthropic response
    response = Mock()
    response.llm_output = {
        'usage': {
            'input_tokens': 200,
            'output_tokens': 75
        }
    }
    response.generations = []
    
    usage = tracer._extract_usage(response)
    
    assert usage.prompt_tokens == 200
    assert usage.completion_tokens == 75
    assert usage.total_tokens == 275
    assert not usage.estimated


def test_usage_tracer_estimates_when_no_usage_data():
    """Test token estimation using tiktoken when no usage data."""
    tracer = UsageTracer(user_id='test_user', agent='test_agent')
    
    # Mock response without usage data
    response = Mock()
    response.llm_output = {}
    
    # Mock generation with text
    generation = Mock()
    generation.text = "This is a test response with approximately twenty tokens or so to test the estimation logic properly."
    response.generations = [[generation]]
    
    with patch('tiktoken.get_encoding') as mock_encoding:
        mock_enc = Mock()
        mock_enc.encode.return_value = [1] * 20  # 20 tokens
        mock_encoding.return_value = mock_enc
        
        usage = tracer._estimate_usage(response)
        
        assert usage.completion_tokens == 20
        assert usage.prompt_tokens == 40  # 2:1 ratio estimate
        assert usage.total_tokens == 60
        assert usage.estimated


def test_usage_tracer_emits_event_on_llm_end(mock_firestore):
    """Test that usage event is emitted on LLM end."""
    tracer = UsageTracer(
        user_id='test_user',
        brand='test_brand',
        run_id='run_123',
        agent='test_agent',
        node='plan',
        db=mock_firestore
    )
    
    # Mock LLM response
    response = Mock()
    response.llm_output = {
        'token_usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        },
        'model_name': 'gpt-4'
    }
    response.generations = []
    
    # Track calls to collection.add
    mock_collection = mock_firestore.collection.return_value
    mock_collection.add = Mock()
    
    # Call on_llm_end
    tracer.on_llm_end(response)
    
    # Verify event was added
    mock_collection.add.assert_called_once()
    event = mock_collection.add.call_args[0][0]
    
    assert event['user_id'] == 'test_user'
    assert event['brand'] == 'test_brand'
    assert event['run_id'] == 'run_123'
    assert event['agent'] == 'test_agent'
    assert event['node'] == 'plan'
    assert event['prompt_tokens'] == 100
    assert event['completion_tokens'] == 50
    assert event['total_tokens'] == 150
    assert event['provider'] == 'openai'
    assert event['model'] == 'gpt-4'


def test_usage_tracer_updates_daily_aggregates(mock_firestore):
    """Test that flush() updates daily aggregates correctly."""
    tracer = UsageTracer(
        user_id='test_user',
        brand='test_brand',
        db=mock_firestore
    )
    
    # Add some events
    tracer.events = [
        {
            'ts': datetime.utcnow(),
            'user_id': 'test_user',
            'brand': 'test_brand',
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        },
        {
            'ts': datetime.utcnow(),
            'user_id': 'test_user',
            'brand': 'test_brand',
            'prompt_tokens': 200,
            'completion_tokens': 100,
            'total_tokens': 300
        }
    ]
    
    # Mock document reference
    mock_doc_ref = Mock()
    mock_firestore.collection.return_value.document.return_value = mock_doc_ref
    
    # Flush events
    tracer.flush()
    
    # Verify daily aggregate was updated
    mock_doc_ref.set.assert_called_once()
    update_data = mock_doc_ref.set.call_args[0][0]
    
    assert update_data['user_id'] == 'test_user'
    assert update_data['brand'] == 'test_brand'
    assert update_data['date'] == date.today()
    
    # Check increments (mocked, so we check structure)
    assert 'totals' in update_data
    
    # Events should be cleared
    assert len(tracer.events) == 0


def test_cost_calculation():
    """Test cost calculation for token usage."""
    usage = TokenUsage(
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500
    )
    
    # Default pricing (simplified)
    assert usage.input_cost_usd == 0.001  # 1000 * 0.000001
    assert usage.output_cost_usd == 0.001  # 500 * 0.000002


def test_provider_detection():
    """Test provider and model detection from response."""
    tracer = UsageTracer()
    
    # Test OpenAI detection
    response = Mock()
    response.llm_output = {'model_name': 'gpt-4-turbo'}
    provider, model = tracer._detect_provider_model(response)
    assert provider == 'openai'
    assert model == 'gpt-4-turbo'
    
    # Test Anthropic detection
    response.llm_output = {'model_name': 'claude-3-opus'}
    provider, model = tracer._detect_provider_model(response)
    assert provider == 'anthropic'
    assert model == 'claude-3-opus'
    
    # Test Gemini detection
    response.llm_output = {'model_name': 'gemini-1.5-pro'}
    provider, model = tracer._detect_provider_model(response)
    assert provider == 'gemini'
    assert model == 'gemini-1.5-pro'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])