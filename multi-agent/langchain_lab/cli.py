"""
Command-line interface for LangChain Lab.

Provides commands for RAG ingestion/querying and agent task execution.
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

# Fix import path for the multi-agent directory
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Set up the argument parser."""
    parser = argparse.ArgumentParser(
        description="LangChain Lab CLI - RAG and Agent evaluation tools",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # RAG commands
    rag_parser = subparsers.add_parser("rag.ingest", help="Ingest documents into RAG system")
    rag_parser.add_argument("--rebuild", action="store_true", help="Rebuild index from scratch")
    rag_parser.add_argument("--source", nargs="+", help="Additional source paths")
    
    ask_parser = subparsers.add_parser("rag.ask", help="Ask a question using RAG")
    ask_parser.add_argument("-q", "--question", required=True, help="Question to ask")
    ask_parser.add_argument("-k", "--k-documents", type=int, default=5, help="Number of documents to retrieve")
    ask_parser.add_argument("--max-tokens", type=int, default=600, help="Maximum tokens in response")
    ask_parser.add_argument("--evaluate", action="store_true", help="Run evaluation on response")
    
    # Agent commands
    agent_parser = subparsers.add_parser("agent.run", help="Run an agent task")
    agent_parser.add_argument("-t", "--task", required=True, help="Task description")
    agent_parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    agent_parser.add_argument("--max-tools", type=int, default=15, help="Maximum tool calls")
    
    # Utility commands
    parser.add_subparsers().add_parser("check", help="Check dependencies")
    
    return parser


def save_artifact(data: Dict[str, Any], prefix: str) -> Path:
    """
    Save result to artifacts directory.
    
    Args:
        data: Data to save
        prefix: Filename prefix
    
    Returns:
        Path to saved file
    """
    from .config import get_config
    config = get_config()
    
    # Create artifacts directory
    artifacts_dir = config.artifacts_path
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.json"
    filepath = artifacts_dir / filename
    
    # Save data
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved artifact to {filepath}")
    return filepath


def cmd_check_dependencies() -> int:
    """Check if all dependencies are available."""
    from .deps import check_dependencies
    
    print("Checking LangChain Lab dependencies...")
    print("-" * 50)
    
    deps = check_dependencies()
    
    all_ok = True
    for package, available in deps.items():
        status = "✓" if available else "✗"
        print(f"{status} {package}: {'installed' if available else 'NOT INSTALLED'}")
        if not available:
            all_ok = False
    
    print("-" * 50)
    if all_ok:
        print("All dependencies are installed!")
        return 0
    else:
        print("Some dependencies are missing. Install with:")
        print("pip install -r requirements.txt")
        return 1


def cmd_rag_ingest(args: argparse.Namespace) -> int:
    """Run RAG document ingestion."""
    from .rag import ingest_documents
    from .config import get_config
    
    config = get_config()
    print(config.model_banner())
    print("-" * 50)
    
    print("Starting document ingestion...")
    
    result = ingest_documents(
        rebuild=args.rebuild,
        source_paths=args.source,
        config=config
    )
    
    if result["status"] == "success":
        stats = result["stats"]
        print(f"\n✓ Ingestion complete!")
        print(f"  Files: {stats['total_files']}")
        print(f"  Chunks: {stats['total_chunks']}")
        print(f"  Characters: {stats['total_chars']:,}")
        print(f"  File types: {stats['file_types']}")
        
        # Save stats
        save_artifact(result, "rag_ingest")
        return 0
    else:
        print(f"\n✗ Ingestion failed: {result.get('message', 'Unknown error')}")
        return 1


def cmd_rag_ask(args: argparse.Namespace) -> int:
    """Ask a question using RAG."""
    from .rag import create_rag_chain
    from .rag.evaluators import evaluate_response
    from .config import get_config
    
    config = get_config()
    
    # Update k_documents if specified
    if args.k_documents:
        config.rag_k_documents = args.k_documents
    
    print(config.model_banner())
    print("-" * 50)
    
    try:
        # Create RAG chain
        print("Loading RAG chain...")
        chain = create_rag_chain(config=config)
        
        # Ask question
        print(f"\nQuestion: {args.question}")
        print("-" * 50)
        
        response = chain.ask(
            args.question,
            max_tokens=args.max_tokens
        )
        
        # Print answer
        print("\nAnswer:")
        print(response.answer)
        
        # Print citations
        if response.citations:
            print("\nCitations:")
            for citation in response.citations:
                print(f"  {citation}")
        
        # Print source snippets
        if response.source_documents:
            print(f"\nRetrieved {len(response.source_documents)} source documents")
            for i, doc in enumerate(response.source_documents[:3]):  # Show first 3
                print(f"\nSource {i+1} ({doc['metadata'].get('source', 'unknown')}):")
                print(f"  {doc['content'][:200]}...")
        
        # Run evaluation if requested
        if args.evaluate:
            print("\nRunning evaluation...")
            scores = evaluate_response(
                args.question,
                response.answer,
                response.source_documents
            )
            print(f"\nEvaluation Scores:")
            print(f"  Faithfulness: {scores['faithfulness']:.2f}")
            print(f"  Relevance: {scores['relevance']:.2f}")
            print(f"  Overall: {scores['overall']:.2f}")
        
        # Save result
        result = {
            "question": args.question,
            "response": response.to_dict(),
            "evaluation": scores if args.evaluate else None
        }
        save_artifact(result, "rag_ask")
        
        return 0
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        print(f"\n✗ Error: {str(e)}")
        return 1


def cmd_agent_run(args: argparse.Namespace) -> int:
    """Run an agent task."""
    from .agents import run_agent_task
    from .agents.policies import AgentPolicy
    from .config import get_config
    
    config = get_config()
    print(config.model_banner())
    print("-" * 50)
    
    # Create policy with user settings
    policy = AgentPolicy(
        max_tool_calls=args.max_tools,
        timeout_seconds=args.timeout
    )
    
    print(f"Running agent task: {args.task}")
    print(f"Policy: max_tools={policy.max_tool_calls}, timeout={policy.timeout_seconds}s")
    print("-" * 50)
    
    try:
        result = run_agent_task(
            task=args.task,
            policy=policy,
            config=config
        )
        
        # Print plan
        if result.get("plan"):
            print("\nPlan:")
            print(result["plan"])
        
        # Print steps
        if result.get("steps"):
            print(f"\nExecuted {len(result['steps'])} steps:")
            for step in result["steps"]:
                print(f"\n  Step {step['step_number']}: {step.get('action', 'N/A')}")
                if step.get("thought"):
                    print(f"    Thought: {step['thought'][:100]}...")
        
        # Print tool calls
        if result.get("tool_calls"):
            print(f"\nMade {len(result['tool_calls'])} tool calls:")
            for call in result["tool_calls"]:
                print(f"  - {call['tool']}: {json.dumps(call['input'], indent=4)[:100]}...")
        
        # Print final answer
        print("\nFinal Answer:")
        print(result.get("final_answer", "No answer generated"))
        
        # Print policy summary
        if result.get("policy_summary"):
            summary = result["policy_summary"]
            print(f"\nPolicy Summary:")
            print(f"  Tool calls: {summary['tool_calls']}/{summary['limits']['max_tool_calls']}")
            print(f"  Time: {summary['elapsed_seconds']}s")
            if summary.get("violations"):
                print(f"  Violations: {len(summary['violations'])}")
        
        # Save result
        save_artifact(result, "agent_run")
        
        return 0 if not result.get("error") else 1
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        print(f"\n✗ Error: {str(e)}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = setup_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Route to appropriate command
    if args.command == "check":
        return cmd_check_dependencies()
    elif args.command == "rag.ingest":
        return cmd_rag_ingest(args)
    elif args.command == "rag.ask":
        return cmd_rag_ask(args)
    elif args.command == "agent.run":
        return cmd_agent_run(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


# Entry points for orchestrator integration
def rag_ask_entrypoint(question: str, **kwargs) -> Dict[str, Any]:
    """Entry point for orchestrator to call RAG."""
    from .rag import create_rag_chain
    
    chain = create_rag_chain()
    response = chain.ask(question, **kwargs)
    return response.to_dict()


def agent_run_entrypoint(task: str, **kwargs) -> Dict[str, Any]:
    """Entry point for orchestrator to run agent."""
    from .agents import run_agent_task
    
    return run_agent_task(task, **kwargs)


if __name__ == "__main__":
    sys.exit(main())