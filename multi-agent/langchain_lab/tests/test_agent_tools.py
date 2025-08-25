"""
Tests for agent tools and policies.

Tests tool functionality, policy enforcement, and agent execution.
"""

import unittest
from unittest.mock import MagicMock, patch, call
import json
import time


class TestAgentTools(unittest.TestCase):
    """Test agent tools."""
    
    def test_klaviyo_stub_tool(self):
        """Test Klaviyo API stub tool."""
        from ..agents.tools import http_klaviyo_stub
        
        # Mock config
        config = MagicMock()
        config.readonly_klaviyo_base_url = "http://localhost:9090"
        
        # Mock httpx
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"metrics": ["opens", "clicks"]}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            # Call tool
            result = http_klaviyo_stub("/metrics", "GET", None, config)
        
        self.assertIn("metrics", result)
        self.assertEqual(result["metrics"], ["opens", "clicks"])
    
    def test_firestore_ro_tool(self):
        """Test Firestore read-only tool."""
        from ..agents.tools import firestore_ro
        
        # Mock config and client
        config = MagicMock()
        config.firestore_project = "test-project"
        
        with patch('multi_agent.langchain_lab.deps.get_firestore_client') as mock_get_client:
            # Mock Firestore client
            mock_client = MagicMock()
            mock_collection = MagicMock()
            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {"name": "Test Client"}
            mock_doc.id = "client123"
            
            mock_collection.document.return_value.get.return_value = mock_doc
            mock_client.collection.return_value = mock_collection
            mock_get_client.return_value = mock_client
            
            # Test document read
            result = firestore_ro("clients", "client123", config=config)
        
        self.assertIn("document", result)
        self.assertEqual(result["document"]["name"], "Test Client")
        self.assertEqual(result["document"]["_id"], "client123")
    
    def test_calendar_ro_tool(self):
        """Test calendar read-only tool."""
        from ..agents.tools import calendar_ro
        
        # Mock config
        config = MagicMock()
        config.seed_docs_path.parent = MagicMock()
        
        # Test with auto-created sample data
        result = calendar_ro(month="2024-10", config=config)
        
        self.assertIn("events", result)
        self.assertIn("count", result)
        
        # If sample data was created, should have October events
        if result["count"] > 0:
            for event in result["events"]:
                if "date" in event:
                    self.assertTrue(event["date"].startswith("2024-10"))
    
    def test_web_fetch_tool(self):
        """Test web fetch tool with allowlist."""
        from ..agents.tools import web_fetch
        
        config = MagicMock()
        
        # Test blocked domain
        result = web_fetch("https://evil.com/data", config)
        self.assertIn("error", result)
        self.assertIn("allowlist", result["error"])
        
        # Test allowed domain
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "Klaviyo documentation content"
            mock_response.status_code = 200
            mock_response.url = "https://docs.klaviyo.com/api"
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status = MagicMock()
            
            mock_client_instance = MagicMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            result = web_fetch("https://docs.klaviyo.com/api", config)
        
        self.assertIn("content", result)
        self.assertIn("Klaviyo", result["content"])
        self.assertEqual(result["status_code"], 200)


class TestAgentPolicies(unittest.TestCase):
    """Test agent policy enforcement."""
    
    def test_policy_enforcer_limits(self):
        """Test policy enforcement for resource limits."""
        from ..agents.policies import PolicyEnforcer, AgentPolicy
        
        policy = AgentPolicy(
            max_tool_calls=3,
            max_iterations=2,
            timeout_seconds=1
        )
        
        enforcer = PolicyEnforcer(policy)
        enforcer.start_execution()
        
        # Test tool call budget
        self.assertTrue(enforcer.check_tool_call("tool1"))
        self.assertTrue(enforcer.check_tool_call("tool2"))
        self.assertTrue(enforcer.check_tool_call("tool3"))
        self.assertFalse(enforcer.check_tool_call("tool4"))  # Exceeds limit
        
        # Test iteration limit
        enforcer = PolicyEnforcer(policy)
        enforcer.start_execution()
        self.assertTrue(enforcer.check_iteration())
        self.assertTrue(enforcer.check_iteration())
        self.assertFalse(enforcer.check_iteration())  # Exceeds limit
        
        # Test timeout
        enforcer = PolicyEnforcer(policy)
        enforcer.start_execution()
        time.sleep(1.1)
        self.assertFalse(enforcer.check_timeout())
    
    def test_pii_redaction(self):
        """Test PII redaction in output."""
        from ..agents.policies import PolicyEnforcer, AgentPolicy
        
        policy = AgentPolicy(redact_pii=True)
        enforcer = PolicyEnforcer(policy)
        
        # Test various PII patterns
        text = "Contact john@example.com or call 555-123-4567"
        redacted = enforcer.redact_pii(text)
        
        self.assertNotIn("john@example.com", redacted)
        self.assertNotIn("555-123-4567", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
    
    def test_tool_blocking(self):
        """Test tool allowlist/blocklist."""
        from ..agents.policies import PolicyEnforcer, AgentPolicy
        
        # Test with blocklist
        policy = AgentPolicy(
            blocked_tools={"dangerous_tool", "write_tool"}
        )
        enforcer = PolicyEnforcer(policy)
        enforcer.start_execution()
        
        self.assertTrue(enforcer.check_tool_call("safe_tool"))
        self.assertFalse(enforcer.check_tool_call("dangerous_tool"))
        
        # Test with allowlist
        policy = AgentPolicy(
            allowed_tools={"tool1", "tool2"}
        )
        enforcer = PolicyEnforcer(policy)
        enforcer.start_execution()
        
        self.assertTrue(enforcer.check_tool_call("tool1"))
        self.assertFalse(enforcer.check_tool_call("tool3"))


class TestAgentExecution(unittest.TestCase):
    """Test agent execution."""
    
    @patch('langchain.agents.AgentExecutor')
    def test_agent_run(self, mock_executor_class):
        """Test agent task execution."""
        from ..agents.agent import TaskAgent
        
        # Mock LLM and tools
        mock_llm = MagicMock()
        mock_tools = [
            MagicMock(name="tool1", description="Tool 1"),
            MagicMock(name="tool2", description="Tool 2")
        ]
        
        # Mock executor
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {
            "output": "Task completed successfully",
            "intermediate_steps": [
                (MagicMock(tool="tool1", tool_input={"param": "value"}, log="Thinking..."),
                 "Tool 1 output"),
                (MagicMock(tool="tool2", tool_input={"data": "test"}, log="Processing..."),
                 "Tool 2 output")
            ]
        }
        mock_executor_class.return_value = mock_executor
        
        # Create and run agent
        agent = TaskAgent(mock_llm, mock_tools)
        result = agent.run("Test task")
        
        # Assertions
        self.assertEqual(result.final_answer, "Task completed successfully")
        self.assertEqual(len(result.tool_calls), 2)
        self.assertEqual(result.tool_calls[0]["tool"], "tool1")
        self.assertIsNotNone(result.time_ms)
        self.assertIsNone(result.error)
    
    def test_agent_with_policy(self):
        """Test agent with policy enforcement."""
        from ..agents.agent import create_agent
        from ..agents.policies import AgentPolicy
        
        # Mock dependencies
        with patch('multi_agent.langchain_lab.deps.get_llm') as mock_get_llm:
            with patch('multi_agent.langchain_lab.agents.tools.get_agent_tools') as mock_get_tools:
                mock_llm = MagicMock()
                mock_get_llm.return_value = mock_llm
                
                mock_tools = [MagicMock(name="test_tool")]
                mock_get_tools.return_value = mock_tools
                
                # Create agent with policy
                policy = AgentPolicy(max_tool_calls=5, timeout_seconds=10)
                agent = create_agent(policy=policy)
                
                self.assertIsNotNone(agent.policy_enforcer)
                self.assertEqual(agent.policy_enforcer.policy.max_tool_calls, 5)


if __name__ == "__main__":
    unittest.main()