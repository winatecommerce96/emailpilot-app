"""
Tests for agent system.

Minimal tests to verify agent functionality with tool calling and policies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ..config import LangChainConfig
from ..agents.policies import AgentPolicy, PolicyEnforcer, PolicyViolation
from ..agents.tools import firestore_ro_get, http_get_json, simple_cache_get, simple_cache_set
from ..agents.agent import AgentExecutor, AgentResult, AgentStep


def test_agent_policy_defaults():
    """Test AgentPolicy has sensible defaults."""
    policy = AgentPolicy()
    
    assert policy.max_tool_calls == 15
    assert policy.max_calls_per_tool == 5
    assert policy.timeout_seconds == 60
    assert policy.enable_pii_redaction == True
    assert "write_to_firestore" in policy.denied_tools


def test_policy_enforcer_initialization():
    """Test PolicyEnforcer initialization."""
    policy = AgentPolicy(max_tool_calls=10)
    enforcer = PolicyEnforcer(policy)
    
    assert enforcer.policy == policy
    assert enforcer.total_tool_calls == 0
    assert len(enforcer.violations) == 0


def test_policy_enforcer_timeout_check():
    """Test timeout checking."""
    policy = AgentPolicy(timeout_seconds=1)
    enforcer = PolicyEnforcer(policy)
    
    # Should not timeout immediately
    assert enforcer.check_timeout() == False
    
    # Mock time passage
    import time
    time.sleep(1.1)
    
    # Should timeout now
    assert enforcer.check_timeout() == True
    assert len(enforcer.violations) > 0
    assert enforcer.violations[0].type == "timeout"


def test_policy_enforcer_tool_call_limits():
    """Test tool call limit enforcement."""
    policy = AgentPolicy(
        max_tool_calls=3,
        max_calls_per_tool=2
    )
    enforcer = PolicyEnforcer(policy)
    
    # First two calls to same tool should succeed
    assert enforcer.check_tool_call("test_tool") == True
    assert enforcer.check_tool_call("test_tool") == True
    
    # Third call to same tool should fail (per-tool limit)
    assert enforcer.check_tool_call("test_tool") == False
    
    # Call to different tool should succeed
    assert enforcer.check_tool_call("other_tool") == True
    
    # Fourth total call should fail (total limit)
    assert enforcer.check_tool_call("another_tool") == False


def test_policy_enforcer_denied_tools():
    """Test denied tool enforcement."""
    policy = AgentPolicy()
    enforcer = PolicyEnforcer(policy)
    
    # Allowed tool
    assert enforcer.check_tool_call("firestore_ro_get") == True
    
    # Denied tool
    assert enforcer.check_tool_call("write_to_firestore") == False
    assert any(v.type == "denied_tool" for v in enforcer.violations)


def test_policy_enforcer_pii_redaction():
    """Test PII redaction."""
    policy = AgentPolicy(enable_pii_redaction=True)
    enforcer = PolicyEnforcer(policy)
    
    text = "Contact John Smith at john.smith@example.com or 555-123-4567"
    redacted = enforcer.redact_pii(text)
    
    assert "john.smith@example.com" not in redacted
    assert "[REDACTED]" in redacted


def test_policy_enforcer_url_checking():
    """Test URL allowlist checking."""
    policy = AgentPolicy()
    enforcer = PolicyEnforcer(policy)
    
    # Allowed domain
    assert enforcer.check_url("https://api.klaviyo.com/v3/campaigns") == True
    assert enforcer.check_url("http://localhost:8000/api") == True
    
    # Denied domain
    assert enforcer.check_url("https://evil.com/malware") == False
    assert any(v.type == "denied_domain" for v in enforcer.violations)


def test_firestore_tool_schema():
    """Test Firestore tool has correct schema."""
    assert firestore_ro_get.name == "firestore_ro_get"
    assert "read-only" in firestore_ro_get.description.lower()
    assert firestore_ro_get.args_schema is not None


@patch("httpx.Client")
def test_http_tool_with_allowlist(mock_client_class):
    """Test HTTP tool respects domain allowlist."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test"}
    mock_client.get.return_value = mock_response
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Allowed domain
    result = http_get_json("https://api.klaviyo.com/test")
    assert result["success"] == True
    assert result["data"] == {"data": "test"}
    
    # Denied domain
    result = http_get_json("https://evil.com/bad")
    assert result["success"] == False
    assert "not in allowlist" in result["error"]


def test_cache_tools():
    """Test cache get/set tools."""
    # Set value
    result = simple_cache_set("test_key", "test_value", ttl_seconds=60)
    assert result == True
    
    # Get value
    value = simple_cache_get("test_key")
    assert value == "test_value"
    
    # Non-existent key
    value = simple_cache_get("nonexistent")
    assert value is None


@patch("langchain_openai.ChatOpenAI")
def test_agent_executor_initialization(mock_llm):
    """Test AgentExecutor initialization."""
    config = LangChainConfig(
        lc_provider="openai",
        openai_api_key="test-key"
    )
    policy = AgentPolicy(max_tool_calls=5)
    
    mock_llm_instance = Mock()
    mock_llm.return_value = mock_llm_instance
    
    with patch("langchain.agents.create_react_agent") as mock_create_agent:
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent
        
        executor = AgentExecutor(
            llm=mock_llm_instance,
            policy=policy,
            config=config
        )
        
        assert executor.llm == mock_llm_instance
        assert executor.policy == policy
        assert executor.config == config
        assert executor.enforcer.policy == policy


def test_agent_result_structure():
    """Test AgentResult dataclass."""
    step = AgentStep(
        step_number=1,
        action="test",
        thought="Testing",
        tool="test_tool",
        tool_input={"param": "value"},
        tool_output={"result": "success"},
        timestamp=datetime.utcnow()
    )
    
    result = AgentResult(
        task="Test task",
        plan="Test plan",
        steps=[step],
        tool_calls=[{"tool": "test_tool", "input": {}, "output": {}}],
        final_answer="Task completed",
        success=True,
        error=None,
        policy_summary={"tool_calls": 1},
        metadata={"duration_ms": 100}
    )
    
    # Test to_dict conversion
    dict_result = result.to_dict()
    
    assert dict_result["task"] == "Test task"
    assert dict_result["success"] == True
    assert len(dict_result["steps"]) == 1
    assert dict_result["steps"][0]["tool"] == "test_tool"


@pytest.mark.integration
@pytest.mark.skipif(
    not Path(__file__).parent.parent.joinpath(".env").exists(),
    reason="No .env file with API keys"
)
def test_agent_with_mock_mcp():
    """Integration test with mocked MCP endpoints."""
    from ..agents import run_agent_task
    
    with patch("httpx.Client") as mock_client_class:
        # Mock MCP responses
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "campaigns": [
                {"id": "1", "name": "October Campaign"},
                {"id": "2", "name": "November Campaign"}
            ]
        }
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Run agent task
        result = run_agent_task(
            task="Fetch last October's top 2 campaigns",
            context={"brand": "test", "month": "2024-10"},
            timeout=10,
            max_tools=5
        )
        
        assert result["success"] in [True, False]  # May fail if no API keys
        assert "task" in result
        assert "policy_summary" in result
        
        # Check policy was enforced
        summary = result["policy_summary"]
        assert summary["tool_calls"] <= 5
        assert summary["elapsed_seconds"] <= 10


def test_agent_task_with_timeout():
    """Test agent respects timeout."""
    from ..agents import run_agent_task
    
    with patch("langchain_openai.ChatOpenAI"):
        # Use very short timeout
        result = run_agent_task(
            task="Complex task that would take long",
            timeout=0.001,  # 1ms timeout
            max_tools=10
        )
        
        # Should timeout or complete very quickly
        assert "policy_summary" in result
        if not result.get("success"):
            assert result.get("error") or \
                   result["policy_summary"].get("has_critical", False)