#!/usr/bin/env python3
"""
Test LangGraph tracing for calendar workflow
This will execute a simple workflow and verify tracing is sent to LangSmith
"""

import os
import asyncio
from datetime import datetime

# Set environment variables for LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "emailpilot-calendar"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"

# Import after setting env vars
from langgraph.graph import StateGraph, END
from typing import TypedDict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestState(TypedDict):
    """Simple test state"""
    message: str
    timestamp: str
    workflow: str

def node1(state: TestState) -> TestState:
    """First test node"""
    state["message"] = "Node 1 executed"
    state["timestamp"] = datetime.now().isoformat()
    logger.info(f"Node 1: {state['message']}")
    return state

def node2(state: TestState) -> TestState:
    """Second test node"""
    state["message"] += " -> Node 2 executed"
    logger.info(f"Node 2: {state['message']}")
    return state

def node3(state: TestState) -> TestState:
    """Final test node"""
    state["message"] += " -> Node 3 completed"
    logger.info(f"Node 3: {state['message']}")
    return state

async def test_workflow():
    """Create and run a test workflow"""
    
    # Create workflow
    workflow = StateGraph(TestState)
    
    # Add nodes
    workflow.add_node("node1", node1)
    workflow.add_node("node2", node2)
    workflow.add_node("node3", node3)
    
    # Add edges
    workflow.set_entry_point("node1")
    workflow.add_edge("node1", "node2")
    workflow.add_edge("node2", "node3")
    workflow.add_edge("node3", END)
    
    # Compile
    app = workflow.compile()
    
    # Run with tracing
    initial_state = {
        "message": "Starting",
        "timestamp": datetime.now().isoformat(),
        "workflow": "calendar_workflow_test"
    }
    
    logger.info(f"🚀 Starting workflow execution at {initial_state['timestamp']}")
    logger.info(f"📊 LangSmith project: {os.environ.get('LANGCHAIN_PROJECT')}")
    logger.info(f"🔗 Trace will appear at: https://smith.langchain.com/")
    
    try:
        result = await app.ainvoke(initial_state)
        logger.info(f"✅ Workflow completed: {result['message']}")
        logger.info(f"🔍 Check LangSmith for traces: https://smith.langchain.com/")
        return result
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        raise

if __name__ == "__main__":
    # Check for API key
    if not os.environ.get("LANGSMITH_API_KEY"):
        logger.warning("⚠️  LANGSMITH_API_KEY not set - loading from .env")
        from dotenv import load_dotenv
        load_dotenv()
    
    # Run the test
    asyncio.run(test_workflow())
    
    print("\n" + "="*50)
    print("✅ Test complete!")
    print(f"📊 Project: {os.environ.get('LANGCHAIN_PROJECT')}")
    print("🔍 View traces at: https://smith.langchain.com/")
    print("="*50)