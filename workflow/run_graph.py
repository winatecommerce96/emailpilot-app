#!/usr/bin/env python3
"""
CLI runner for LangGraph workflows
"""

import argparse
import json
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.util
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_schema(schema_path: str) -> Dict[str, Any]:
    """Load workflow schema from file"""
    path = Path(schema_path)
    
    if not path.exists():
        # Try workflow directory
        path = Path(__file__).parent / schema_path
    
    if not path.exists():
        # Try schemas directory
        path = Path(__file__).parent / "schemas" / schema_path
    
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    
    with open(path) as f:
        return json.load(f)


def compile_workflow(schema_path: str) -> Any:
    """Compile workflow from schema"""
    import subprocess
    
    # Run codegen
    codegen_path = Path(__file__).parent / "tools" / "codegen.py"
    result = subprocess.run(
        [sys.executable, str(codegen_path)],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent)
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Codegen failed: {result.stderr}")
    
    logger.info(f"Codegen output: {result.stdout}")
    
    # Import the compiled graph
    runtime_path = Path(__file__).parent / "runtime" / "graph_compiled.py"
    
    if not runtime_path.exists():
        raise RuntimeError("Compiled graph not found")
    
    spec = importlib.util.spec_from_file_location("graph_compiled", runtime_path)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load compiled graph")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, 'compile_graph'):
        raise RuntimeError("Compiled graph missing compile_graph function")
    
    return module.compile_graph()


def run_workflow(
    app: Any,
    inputs: Dict[str, Any],
    thread_id: Optional[str] = None,
    checkpoint_id: Optional[str] = None
) -> Dict[str, Any]:
    """Run the workflow"""
    
    # Create config for execution
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    if checkpoint_id:
        config["configurable"] = config.get("configurable", {})
        config["configurable"]["checkpoint_id"] = checkpoint_id
    
    # Create initial state
    initial_state = {
        "inputs": inputs,
        **inputs  # Also spread inputs at top level for convenience
    }
    
    logger.info("Starting workflow execution...")
    logger.info(f"Initial state: {json.dumps(initial_state, indent=2)}")
    
    # Run the graph
    if config:
        result = app.invoke(initial_state, config=config)
    else:
        result = app.invoke(initial_state)
    
    return result


def stream_workflow(
    app: Any,
    inputs: Dict[str, Any],
    thread_id: Optional[str] = None
) -> None:
    """Stream workflow execution"""
    
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    
    initial_state = {
        "inputs": inputs,
        **inputs
    }
    
    logger.info("Streaming workflow execution...")
    
    # Stream the graph execution
    for event in app.stream(initial_state, config=config if config else None):
        print(f"\n{'='*50}")
        print(f"Event: {json.dumps(event, indent=2, default=str)}")
        print(f"{'='*50}")


def interactive_mode(app: Any, thread_id: str) -> None:
    """Interactive execution with checkpoints"""
    
    print("\n" + "="*50)
    print("INTERACTIVE MODE")
    print("="*50)
    print("Commands:")
    print("  run <json>    - Run with given inputs")
    print("  continue      - Continue from last checkpoint")
    print("  history       - Show execution history")
    print("  state         - Show current state")
    print("  quit          - Exit")
    print("="*50 + "\n")
    
    config = {"configurable": {"thread_id": thread_id}}
    current_state = None
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if command.startswith("run "):
                json_str = command[4:].strip()
                inputs = json.loads(json_str)
                
                initial_state = {
                    "inputs": inputs,
                    **inputs
                }
                
                print("\nRunning workflow...")
                for event in app.stream(initial_state, config=config):
                    print(f"Event: {json.dumps(event, indent=2, default=str)}")
                    current_state = event
            
            elif command == "continue":
                if not current_state:
                    print("No previous execution to continue from")
                    continue
                
                print("\nContinuing workflow...")
                for event in app.stream(None, config=config):
                    print(f"Event: {json.dumps(event, indent=2, default=str)}")
                    current_state = event
            
            elif command == "history":
                # Get checkpoint history
                if hasattr(app, 'checkpointer') and app.checkpointer:
                    # This depends on checkpointer implementation
                    print("Checkpoint history:")
                    # Would need to implement based on specific checkpointer
                    print("(Feature not yet implemented)")
                else:
                    print("No checkpointer configured")
            
            elif command == "state":
                if current_state:
                    print(f"Current state: {json.dumps(current_state, indent=2, default=str)}")
                else:
                    print("No current state")
            
            elif command == "quit":
                break
            
            else:
                print(f"Unknown command: {command}")
        
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run LangGraph workflow")
    parser.add_argument(
        "schema",
        nargs="?",
        default="workflow.json",
        help="Path to workflow schema (default: workflow.json)"
    )
    parser.add_argument(
        "--inputs", "-i",
        help="Input data as JSON string or file path"
    )
    parser.add_argument(
        "--thread-id", "-t",
        help="Thread ID for checkpointing"
    )
    parser.add_argument(
        "--checkpoint-id", "-c",
        help="Checkpoint ID to resume from"
    )
    parser.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Stream execution events"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode with checkpoints"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file for results"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load and compile workflow
        logger.info(f"Loading schema: {args.schema}")
        schema = load_schema(args.schema)
        
        logger.info(f"Compiling workflow: {schema['name']}")
        app = compile_workflow(args.schema)
        
        # Interactive mode
        if args.interactive:
            thread_id = args.thread_id or f"interactive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            interactive_mode(app, thread_id)
            return 0
        
        # Parse inputs
        inputs = {}
        if args.inputs:
            if args.inputs.startswith("{"):
                # JSON string
                inputs = json.loads(args.inputs)
            elif Path(args.inputs).exists():
                # File path
                with open(args.inputs) as f:
                    inputs = json.load(f)
            else:
                # Try as JSON anyway
                inputs = json.loads(args.inputs)
        
        # Stream mode
        if args.stream:
            stream_workflow(app, inputs, args.thread_id)
            return 0
        
        # Regular execution
        result = run_workflow(app, inputs, args.thread_id, args.checkpoint_id)
        
        # Output results
        output_data = {
            "workflow": schema["name"],
            "execution_time": datetime.now().isoformat(),
            "inputs": inputs,
            "result": result
        }
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            logger.info(f"Results saved to: {args.output}")
        else:
            print("\n" + "="*50)
            print("WORKFLOW RESULT")
            print("="*50)
            print(json.dumps(result, indent=2, default=str))
        
        return 0
        
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())