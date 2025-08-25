#!/usr/bin/env python
"""
LangChain Core CLI - Production-grade interface with Typer.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize Typer app
app = typer.Typer(
    name="langchain",
    help="LangChain/LangGraph CLI for EmailPilot",
    add_completion=False
)

# Sub-apps
rag_app = typer.Typer(help="RAG operations")
agent_app = typer.Typer(help="Agent operations")
admin_app = typer.Typer(help="Admin operations")

app.add_typer(rag_app, name="rag")
app.add_typer(agent_app, name="agent")
app.add_typer(admin_app, name="admin")

console = Console()
logger = logging.getLogger(__name__)


@app.command()
def check():
    """
    Verify installation, dependencies, and connectivity.
    """
    console.print("[bold blue]LangChain Core Health Check[/bold blue]")
    console.print("=" * 50)
    
    checks = []
    
    # Check Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python Version", py_version, py_version >= "3.12"))
    
    # Check dependencies
    try:
        import langchain
        import langgraph
        import langchain_core
        checks.append(("LangChain", getattr(langchain, "__version__", "installed"), True))
        checks.append(("LangGraph", "installed", True))  # LangGraph doesn't expose __version__
        checks.append(("LangChain Core", getattr(langchain_core, "__version__", "installed"), True))
    except ImportError as e:
        checks.append(("Dependencies", str(e), False))
    
    # Check Firestore
    try:
        from google.cloud import firestore
        db = firestore.Client()
        # Try a simple read
        db.collection("_health").document("check").get()
        checks.append(("Firestore", "Connected", True))
    except Exception as e:
        checks.append(("Firestore", f"Error: {str(e)[:50]}", False))
    
    # Check Secret Manager
    try:
        from .secrets import get_secret
        # Try to fetch a test secret
        get_secret("test-secret")
        checks.append(("Secret Manager", "Available", True))
    except Exception:
        checks.append(("Secret Manager", "Not configured", False))
    
    # Check MCP servers
    mcp_status = []
    for name, port in [("Klaviyo Revenue", 9090), ("Performance", 9091)]:
        try:
            import httpx
            resp = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if resp.status_code == 200:
                mcp_status.append(f"{name}: ✓")
            else:
                mcp_status.append(f"{name}: ✗")
        except:
            mcp_status.append(f"{name}: ✗")
    
    checks.append(("MCP Servers", " | ".join(mcp_status), all("✓" in s for s in mcp_status)))
    
    # Check importability
    try:
        from emailpilot_multiagent.shim import get_langchain_core
        get_langchain_core()
        checks.append(("Import Alias", "Working", True))
    except:
        checks.append(("Import Alias", "Not working", False))
    
    # Display results
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Health", style="green")
    
    all_ok = True
    for component, status, ok in checks:
        health = "✅" if ok else "❌"
        table.add_row(component, status, health)
        if not ok:
            all_ok = False
    
    console.print(table)
    
    if all_ok:
        console.print("\n[green]✓ All systems operational[/green]")
    else:
        console.print("\n[red]⚠ Some systems need attention[/red]")
    
    return 0 if all_ok else 1


@rag_app.command("ingest")
def rag_ingest(
    rebuild: bool = typer.Option(False, "--rebuild", help="Rebuild index from scratch"),
    source: Optional[Path] = typer.Option(None, "--source", help="Additional source directory")
):
    """
    Build or update the RAG index.
    """
    console.print("[bold]Building RAG Index[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Loading documents...", total=None)
        
        try:
            from .rag.ingest import DocumentIngester
            
            ingester = DocumentIngester(rebuild=rebuild)
            
            # Add default sources
            progress.update(task, description="Scanning project docs...")
            stats = ingester.ingest_directory(Path(__file__).parent.parent.parent.parent / "docs")
            
            # Add custom source if provided
            if source:
                progress.update(task, description=f"Scanning {source}...")
                custom_stats = ingester.ingest_directory(source)
                stats["documents"] += custom_stats.get("documents", 0)
                stats["chunks"] += custom_stats.get("chunks", 0)
            
            progress.update(task, description="Persisting index...")
            ingester.persist()
            
            console.print(f"\n[green]✓ Indexed {stats['documents']} documents ({stats['chunks']} chunks)[/green]")
            
        except Exception as e:
            console.print(f"[red]✗ Failed to build index: {e}[/red]")
            raise typer.Exit(1)


@rag_app.command("ask")
def rag_ask(
    question: str = typer.Option(..., "-q", "--question", help="Question to ask"),
    k: int = typer.Option(5, "-k", help="Number of sources to retrieve")
):
    """
    Ask a question using RAG.
    """
    console.print(f"[bold]Question:[/bold] {question}\n")
    
    try:
        from .rag.chain import ask_rag_question
        result = ask_rag_question(question, k=k)
        
        console.print(f"[bold green]Answer:[/bold green]\n{result['answer']}\n")
        
        if result.get("sources"):
            console.print("[bold]Sources:[/bold]")
            for i, source in enumerate(result.get("sources", [])[:3], 1):
                console.print(f"  {i}. {source.get('title', 'Unknown')}")
                
    except Exception as e:
        console.print(f"[red]✗ Failed to answer: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("run")
def agent_run(
    task: str = typer.Option(..., "-t", "--task", help="Task description"),
    brand: Optional[str] = typer.Option(None, "--brand", help="Brand context"),
    month: Optional[str] = typer.Option(None, "--month", help="Month context (YYYY-MM)"),
    user_id: Optional[str] = typer.Option(None, "--user-id", help="User ID for policy resolution"),
    overrides_json: Optional[str] = typer.Option(None, "--overrides-json", help="JSON overrides")
):
    """
    Run an agent task.
    """
    console.print(f"[bold]Running Agent Task[/bold]")
    console.print(f"Task: {task}")
    
    # Parse overrides
    overrides = {}
    if overrides_json:
        try:
            overrides = json.loads(overrides_json)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON overrides: {e}[/red]")
            raise typer.Exit(1)
    
    # Build context
    context = {
        "brand": brand,
        "month": month,
        "user_id": user_id,
        **overrides
    }
    
    # Remove None values
    context = {k: v for k, v in context.items() if v is not None}
    
    try:
        from .agents import run_agent_task
        result = run_agent_task(task=task, context=context)
        
        console.print("\n[bold green]✓ Task completed[/bold green]\n")
        
        if result.get("final_answer"):
            console.print("[bold]Answer:[/bold]")
            console.print(result["final_answer"])
            
    except Exception as e:
        console.print(f"[red]✗ Task failed: {e}[/red]")
        raise typer.Exit(1)


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
