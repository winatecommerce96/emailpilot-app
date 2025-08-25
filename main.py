"""
Main entry point for LangGraph Calendar Workflow
"""
import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.graph import calendar_graph
from langsmith import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_calendar_workflow(brand: str, month: str, instructions: str = None) -> Dict[str, Any]:
    """
    Run the calendar workflow with given inputs
    
    Args:
        brand: Brand name
        month: Target month
        instructions: Optional specific instructions
    
    Returns:
        Workflow results
    """
    # Prepare initial state
    initial_message = instructions or f"Plan a campaign calendar for {brand} in {month}"
    
    initial_state = {
        "messages": [{"role": "user", "content": initial_message}],
        "tasks": [],
        "current_task": None,
        "artifacts": [],
        "brand": brand,
        "month": month,
        "run_context": {
            "started_at": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        "error": None,
        "completed": False
    }
    
    logger.info(f"Starting calendar workflow for {brand} - {month}")
    logger.info(f"Initial state: {initial_state}")
    
    try:
        # Run the graph
        config = {
            "configurable": {
                "thread_id": f"calendar_{brand}_{month}_{datetime.now().timestamp()}"
            }
        }
        
        result = calendar_graph.invoke(initial_state, config={
            **config,
            "recursion_limit": 50  # Increase limit to handle all tasks
        })
        
        logger.info(f"Workflow completed. Artifacts: {len(result.get('artifacts', []))}")
        
        # Check LangSmith trace
        if os.getenv("LANGSMITH_API_KEY"):
            logger.info("✓ LangSmith tracing enabled")
            client = Client()
            project_name = os.getenv("LANGSMITH_PROJECT", "emailpilot-calendar")
            logger.info(f"View traces at: https://smith.langchain.com/o/{client.tenant_id}/projects/p/{project_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return {
            **initial_state,
            "error": str(e),
            "completed": True
        }


def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Calendar Workflow")
    parser.add_argument("--brand", default="TestBrand", help="Brand name")
    parser.add_argument("--month", default="March 2025", help="Target month")
    parser.add_argument("--instructions", help="Custom instructions")
    
    args = parser.parse_args()
    
    # Run workflow
    result = run_calendar_workflow(
        brand=args.brand,
        month=args.month,
        instructions=args.instructions
    )
    
    # Display results
    print("\n" + "="*50)
    print("WORKFLOW RESULTS")
    print("="*50)
    
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✓ Completed: {result.get('completed', False)}")
        print(f"✓ Tasks processed: {len(result.get('tasks', []))}")
        print(f"✓ Artifacts created: {len(result.get('artifacts', []))}")
        
        if result.get("artifacts"):
            print("\nArtifacts:")
            for artifact in result["artifacts"]:
                print(f"  - {artifact.get('task_type')}: {artifact.get('status')}")
    
    print("\n" + "="*50)
    
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    sys.exit(main())