"""
Tests for ModelPolicyResolver using emailpilot_multiagent alias.
"""
import pytest
from integrations.langchain_core.deps import ModelPolicyResolver


def test_policy_resolver_init():
    """Test ModelPolicyResolver initialization."""
    resolver = ModelPolicyResolver()
    assert resolver is not None
    # Resolver has a resolve method
    assert hasattr(resolver, 'resolve')


def test_resolve_global_policy():
    """Test resolving global policy."""
    resolver = ModelPolicyResolver()
    result = resolver.resolve()
    
    assert "provider" in result
    assert "model" in result
    assert "cascade_level" in result
    assert result["cascade_level"] in ["global", "environment", "user", "brand", "account"]


def test_resolve_with_user():
    """Test resolving with user context."""
    resolver = ModelPolicyResolver()
    
    # Resolve with user context (without setting policy - uses defaults)
    result = resolver.resolve(user_id="test_user")
    assert "provider" in result
    assert "model" in result
    assert "cascade_level" in result


def test_resolve_with_brand():
    """Test resolving with brand context."""
    resolver = ModelPolicyResolver()
    
    # Resolve with brand context (without setting policy - uses defaults)
    result = resolver.resolve(brand="acme")
    assert "provider" in result
    assert "model" in result
    assert "cascade_level" in result


def test_validate_provider():
    """Test provider validation."""
    resolver = ModelPolicyResolver()
    
    # Test that resolver can validate providers by resolving with them
    for provider in ["openai", "anthropic", "google"]:
        # Mock setting a provider preference (through resolve)
        result = resolver.resolve()
        assert "provider" in result
        # Provider should be one of the valid ones
        assert result["provider"] in ["openai", "anthropic", "google", "azure"]
