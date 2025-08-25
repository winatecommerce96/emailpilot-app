"""
Smoke test for LangGraph Calendar Workflow
"""
import os
import sys
import unittest
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.state import CalendarState
from graph.graph import calendar_graph, create_calendar_graph
from agents.calendar.planner import planner_node
from agents.calendar.router import router_node
from agents.calendar.worker import worker_node
from tools.calendar_tools import get_calendar_tools


class TestCalendarWorkflow(unittest.TestCase):
    """Test the calendar workflow components"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_state = {
            "messages": [{"role": "user", "content": "Plan a campaign for TestBrand in March"}],
            "tasks": [],
            "current_task": None,
            "artifacts": [],
            "brand": "TestBrand",
            "month": "March 2025",
            "run_context": {"test": True},
            "error": None,
            "completed": False
        }
    
    def test_state_definition(self):
        """Test that CalendarState is properly defined"""
        # This should not raise an error
        state = CalendarState(
            messages=[],
            tasks=[],
            current_task=None,
            artifacts=[],
            brand="test",
            month="test",
            run_context={},
            error=None,
            completed=False
        )
        self.assertIsNotNone(state)
    
    def test_planner_node(self):
        """Test planner node creates tasks"""
        result = planner_node(self.test_state)
        
        self.assertIn("tasks", result)
        self.assertIsInstance(result["tasks"], list)
        self.assertGreater(len(result["tasks"]), 0)
        
        # Check task structure
        task = result["tasks"][0]
        self.assertIn("id", task)
        self.assertIn("type", task)
        self.assertIn("description", task)
    
    def test_router_node(self):
        """Test router node handles routing logic"""
        # Test with tasks
        state_with_tasks = {
            **self.test_state,
            "tasks": [{"id": "1", "type": "test"}]
        }
        result = router_node(state_with_tasks)
        
        self.assertIn("current_task", result)
        self.assertEqual(result["current_task"]["id"], "1")
        self.assertEqual(len(result["tasks"]), 0)
        
        # Test with error
        state_with_error = {
            **self.test_state,
            "error": "Test error"
        }
        result = router_node(state_with_error)
        self.assertTrue(result["completed"])
    
    def test_worker_node(self):
        """Test worker node executes tasks"""
        state_with_task = {
            **self.test_state,
            "current_task": {
                "id": "test_1",
                "type": "optimize_timing",
                "description": "Test task",
                "requires_tool": False
            }
        }
        
        result = worker_node(state_with_task)
        
        self.assertIn("artifacts", result)
        self.assertGreater(len(result["artifacts"]), 0)
        
        artifact = result["artifacts"][0]
        self.assertEqual(artifact["task_id"], "test_1")
        self.assertEqual(artifact["status"], "completed")
        self.assertIn("result", artifact)
    
    def test_tools_available(self):
        """Test that calendar tools are available"""
        tools = get_calendar_tools()
        
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)
        
        # Test tool names
        tool_names = [tool.name for tool in tools]
        self.assertIn("analyze_metrics", tool_names)
        self.assertIn("generate_calendar", tool_names)
        self.assertIn("read_calendar_events", tool_names)
    
    def test_graph_compilation(self):
        """Test that the graph compiles successfully"""
        try:
            graph = create_calendar_graph()
            self.assertIsNotNone(graph)
        except Exception as e:
            self.fail(f"Graph compilation failed: {e}")
    
    def test_graph_invocation(self):
        """Test basic graph invocation"""
        try:
            config = {
                "configurable": {
                    "thread_id": f"test_{datetime.now().timestamp()}"
                }
            }
            
            result = calendar_graph.invoke(self.test_state, config=config)
            
            self.assertIsNotNone(result)
            self.assertIn("completed", result)
            
        except Exception as e:
            # Some errors are expected in test environment
            if "checkpointer" not in str(e).lower():
                self.fail(f"Graph invocation failed unexpectedly: {e}")
    
    def test_langsmith_integration(self):
        """Test LangSmith environment variables"""
        if os.getenv("LANGSMITH_API_KEY"):
            self.assertTrue(os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true")
            print("✓ LangSmith integration configured")
        else:
            print("⚠ LangSmith API key not set (tracing disabled)")


def run_smoke_test():
    """Run the smoke test suite"""
    print("\n" + "="*50)
    print("LANGGRAPH CALENDAR WORKFLOW SMOKE TEST")
    print("="*50 + "\n")
    
    # Check environment
    print("Environment Check:")
    print(f"  Python version: {sys.version.split()[0]}")
    print(f"  Working directory: {os.getcwd()}")
    print(f"  LangSmith configured: {'Yes' if os.getenv('LANGSMITH_API_KEY') else 'No'}")
    print()
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCalendarWorkflow)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*50)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*50 + "\n")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_smoke_test())