"""
Main entry point for the multi-agent orchestration service.
Provides CLI and API interfaces for campaign workflow execution.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import click
import json
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .graph import CampaignOrchestrationGraph
from .schemas import RunState
from .approvals import ApprovalManager, ApprovalCLI
from .config import get_settings

# Log LangGraph version on startup
import importlib.metadata as m
try:
    _lg_ver = m.version("langgraph")
except Exception:
    _lg_ver = "UNKNOWN"

print(f"[orchestrator] LangGraph version: {_lg_ver}")


# FastAPI app for HTTP interface
app = FastAPI(
    title="Multi-Agent Orchestration Service",
    description="LangGraph-based campaign creation workflow",
    version="1.0.0",
)

# Configure CORS middleware to allow local file:// and http:// origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins including file:// (null origin)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Global instances
orchestrator = CampaignOrchestrationGraph()
approval_manager = ApprovalManager()
settings = get_settings()


# API Models
class RunRequest(BaseModel):
    """Request model for starting a run."""
    tenant_id: str = "pilot-tenant"
    brand_id: str
    selected_month: str
    prior_year_same_month: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    

class ApprovalRequest(BaseModel):
    """Request model for approval decisions."""
    request_id: str
    decision: str  # approve, reject, approve_with_fixes
    approver: str
    notes: Optional[str] = None


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Multi-Agent Orchestration",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "start_run": "/runs/start",
            "get_run": "/runs/{run_id}",
            "list_runs": "/runs",
            "pending_approvals": "/approvals/pending",
            "submit_approval": "/approvals/submit",
        }
    }


@app.post("/runs/start", response_model=RunState)
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    """Start a new orchestration run."""
    
    # Default prior year if not provided
    if not request.prior_year_same_month:
        year, month = request.selected_month.split("-")
        prior_year = str(int(year) - 1)
        request.prior_year_same_month = f"{prior_year}-{month}"
    
    # Execute the orchestration
    try:
        run_state = await orchestrator.run(
            tenant_id=request.tenant_id,
            brand_id=request.brand_id,
            selected_month=request.selected_month,
            prior_year_same_month=request.prior_year_same_month,
            metadata=request.metadata or {},
        )
        return run_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get status of a specific run."""
    # In production, this would query from storage
    return {
        "run_id": run_id,
        "status": "pending",
        "message": "Run status retrieval to be implemented",
    }


@app.get("/runs")
async def list_runs(limit: int = 10):
    """List recent runs."""
    # In production, this would query from storage
    return {
        "runs": [],
        "total": 0,
        "message": "Run listing to be implemented",
    }


@app.get("/approvals/pending")
async def get_pending_approvals(approver_role: Optional[str] = None):
    """Get pending approval requests."""
    
    pending = await approval_manager.get_pending_approvals(approver_role)
    
    return {
        "pending": [
            {
                "request_id": r.request_id,
                "artifact_type": r.artifact_type,
                "artifact_id": r.artifact_id,
                "requested_at": r.requested_at.isoformat(),
                "timeout_at": r.timeout_at.isoformat(),
                "approver_role": r.approver_role,
            }
            for r in pending
        ],
        "count": len(pending),
    }


@app.post("/approvals/submit")
async def submit_approval(request: ApprovalRequest):
    """Submit an approval decision."""
    
    try:
        if request.decision == "approve":
            result = await approval_manager.approve(
                request.request_id,
                request.approver,
                request.notes,
                with_fixes=False,
            )
        elif request.decision == "approve_with_fixes":
            result = await approval_manager.approve(
                request.request_id,
                request.approver,
                request.notes,
                with_fixes=True,
            )
        elif request.decision == "reject":
            if not request.notes:
                raise ValueError("Notes required for rejection")
            result = await approval_manager.reject(
                request.request_id,
                request.approver,
                request.notes,
            )
        else:
            raise ValueError(f"Invalid decision: {request.decision}")
        
        return {
            "success": True,
            "request_id": result.request_id,
            "status": result.status,
            "decided_at": result.decided_at.isoformat() if result.decided_at else None,
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.app.environment,
    }


# Optional LangChain Core API Routes
@app.post("/api/lc/rag")
async def api_langchain_rag(
    q: str,
    k: int = 5,
    max_tokens: int = 600
):
    """RAG endpoint for LangChain Core integration."""
    if not LANGCHAIN_CORE_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="LangChain Core not available. Install dependencies."
        )
    
    try:
        result = lc_rag(
            question=q,
            k=k,
            max_tokens=max_tokens
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "RAG query failed")
            )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lc/agent")
async def api_langchain_agent(
    task: str,
    brand: Optional[str] = None,
    month: Optional[str] = None,
    timeout: int = 30,
    max_tools: int = 15
):
    """Agent endpoint for LangChain Core integration."""
    if not LANGCHAIN_CORE_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="LangChain Core not available. Install dependencies."
        )
    
    try:
        result = lc_agent(
            task=task,
            brand=brand,
            month=month,
            timeout=timeout,
            max_tools=max_tools
        )
        
        if not result.get("success", True):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Agent execution failed")
            )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# CLI Interface

@click.group()
def cli():
    """Multi-Agent Orchestration CLI."""
    pass


@cli.command()
@click.option("--month", required=True, help="Target month (YYYY-MM)")
@click.option("--brand", required=True, help="Brand ID")
@click.option("--tenant", default="pilot-tenant", help="Tenant ID")
@click.option("--prior-year-month", help="Prior year comparison month")
@click.option("--auto-approve", is_flag=True, help="Auto-approve all decisions")
def demo(month, brand, tenant, prior_year_month, auto_approve):
    """Run a demonstration workflow."""
    
    click.echo(f"Starting demo run for {brand} - {month}")
    
    # Set auto-approve if requested
    if auto_approve:
        settings.orchestration.auto_approve_in_dev = True
    
    # Calculate prior year if not provided
    if not prior_year_month:
        year, m = month.split("-")
        prior_year_month = f"{int(year)-1}-{m}"
    
    # Run the orchestration
    async def run():
        try:
            result = await orchestrator.run(
                tenant_id=tenant,
                brand_id=brand,
                selected_month=month,
                prior_year_same_month=prior_year_month,
                metadata={"source": "cli_demo"},
            )
            
            # Save artifacts
            output_dir = Path(f"multi-agent/.artifacts/{brand}/{month}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Write run state
            with open(output_dir / "run_state.json", "w") as f:
                json.dump(result.dict(), f, indent=2, default=str)
            
            click.echo(f"\n✓ Demo completed successfully!")
            click.echo(f"  Run ID: {result.run_id}")
            click.echo(f"  Status: {result.status}")
            click.echo(f"  Artifacts saved to: {output_dir}")
            
            # Summary
            click.echo("\nArtifacts created:")
            for artifact_type, artifact_id in result.artifacts.items():
                click.echo(f"  - {artifact_type}: {artifact_id}")
            
            if result.revision_count > 0:
                click.echo(f"\nRevisions: {result.revision_count}")
            
            return result
            
        except Exception as e:
            click.echo(f"\n✗ Demo failed: {str(e)}", err=True)
            raise
    
    result = asyncio.run(run())
    return result


@cli.command()
def approve():
    """Interactive approval session."""
    
    click.echo("Starting interactive approval session...")
    
    async def run():
        cli_approver = ApprovalCLI(approval_manager)
        await cli_approver.interactive_approve()
    
    asyncio.run(run())


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8100, type=int, help="Port to bind to")
def serve(host, port):
    """Start the HTTP API server."""
    
    click.echo(f"Starting API server on {host}:{port}")
    
    import uvicorn
    uvicorn.run(
        "apps.orchestrator_service.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )


@cli.command()
def validate():
    """Validate configuration and connections."""
    
    click.echo("Validating configuration...")
    
    # Check settings
    click.echo(f"  Environment: {settings.app.environment}")
    click.echo(f"  Primary Model: {settings.models.primary_provider}/{settings.models.primary_model}")
    click.echo(f"  EmailPilot URL: {settings.services.emailpilot_base_url}")
    
    # Check graph compilation
    try:
        test_graph = CampaignOrchestrationGraph()
        click.echo("  ✓ Graph compilation: OK")
    except Exception as e:
        click.echo(f"  ✗ Graph compilation: {str(e)}", err=True)
        return 1
    
    # Check approval manager
    try:
        test_manager = ApprovalManager()
        click.echo("  ✓ Approval manager: OK")
    except Exception as e:
        click.echo(f"  ✗ Approval manager: {str(e)}", err=True)
        return 1
    
    click.echo("\nValidation complete!")
    return 0


# LangChain Core Integration (Optional)
try:
    # Add parent directory to path for import
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from integrations.langchain_core.adapters.orchestrator_bridge import (
        lc_rag,
        lc_agent,
        check_langchain_available
    )
    LANGCHAIN_CORE_AVAILABLE = check_langchain_available()
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False
    import logging
    logging.getLogger(__name__).info("LangChain Core not available (optional feature)")


@cli.command("lc-rag")
@click.option("-q", "--question", required=True, help="Question for RAG system")
@click.option("--max-tokens", type=int, default=600, help="Maximum response tokens")
@click.option("-k", "--k-documents", type=int, default=5, help="Number of documents to retrieve")
def langchain_rag(question, max_tokens, k_documents):
    """Query LangChain Core RAG system (optional integration)."""
    if not LANGCHAIN_CORE_AVAILABLE:
        click.echo("❌ LangChain Core not available. Install with: pip install -r multi-agent/integrations/langchain_core/requirements.txt", err=True)
        return 1
    
    try:
        click.echo(f"🔍 Querying RAG system: {question}")
        click.echo("-" * 50)
        
        result = lc_rag(
            question=question,
            k=k_documents,
            max_tokens=max_tokens
        )
        
        if not result.get("success"):
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}", err=True)
            return 1
        
        # Display results
        click.echo("\n📝 Answer:")
        click.echo(result.get("answer", "No answer generated"))
        
        if result.get("citations"):
            click.echo("\n📚 Citations:")
            for citation in result["citations"]:
                click.echo(f"  - {citation.get('source', 'Unknown')}: {citation.get('text', '')[:100]}...")
        
        if result.get("source_documents"):
            click.echo(f"\n📄 Retrieved {len(result['source_documents'])} source documents")
        
        if result.get("diagnostics"):
            diag = result["diagnostics"]
            click.echo(f"\n⚡ Performance: {diag.get('duration_ms', 0)}ms | Model: {diag.get('model', 'unknown')}")
        
        click.echo(f"\n✓ Query completed successfully")
        return 0
        
    except Exception as e:
        click.echo(f"❌ RAG query failed: {str(e)}", err=True)
        return 1


@cli.command("lc-agent")
@click.option("-t", "--task", required=True, help="Task for agent to execute")
@click.option("--brand", help="Brand ID for context")
@click.option("--month", help="Month for context (YYYY-MM)")
@click.option("--timeout", type=int, default=30, help="Timeout in seconds")
@click.option("--max-tools", type=int, default=15, help="Maximum tool calls")
def langchain_agent(task, brand, month, timeout, max_tools):
    """Run LangChain Core agent task (optional integration)."""
    if not LANGCHAIN_CORE_AVAILABLE:
        click.echo("❌ LangChain Core not available. Install with: pip install -r multi-agent/integrations/langchain_core/requirements.txt", err=True)
        return 1
    
    try:
        click.echo(f"🤖 Running agent task: {task}")
        click.echo(f"⚙️  Limits: timeout={timeout}s, max_tools={max_tools}")
        if brand or month:
            click.echo(f"📌 Context: brand={brand}, month={month}")
        click.echo("-" * 50)
        
        result = lc_agent(
            task=task,
            brand=brand,
            month=month,
            timeout=timeout,
            max_tools=max_tools
        )
        
        if not result.get("success", True):
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}", err=True)
            return 1
        
        # Display results
        if result.get("plan"):
            click.echo("\n📋 Plan:")
            click.echo(result["plan"])
        
        if result.get("tool_calls"):
            click.echo(f"\n🔧 Made {len(result['tool_calls'])} tool calls:")
            for call in result["tool_calls"]:
                click.echo(f"  - {call['tool']}: {str(call.get('input', ''))[:50]}...")
        
        click.echo("\n💡 Final Answer:")
        click.echo(result.get("final_answer", "No answer generated"))
        
        if result.get("policy_summary"):
            summary = result["policy_summary"]
            click.echo(f"\n📊 Execution Summary:")
            click.echo(f"  Time: {summary.get('elapsed_seconds', 0)}s")
            click.echo(f"  Tool calls: {summary.get('tool_calls', 0)}")
            if summary.get("violations"):
                click.echo(f"  Policy violations: {len(summary['violations'])}")
        
        if result.get("diagnostics"):
            diag = result["diagnostics"]
            click.echo(f"\n⚡ Performance: {diag.get('duration_ms', 0)}ms | Model: {diag.get('model', 'unknown')}")
        
        click.echo(f"\n✓ Agent task completed successfully")
        return 0
        
    except Exception as e:
        click.echo(f"❌ Agent execution failed: {str(e)}", err=True)
        return 1


if __name__ == "__main__":
    cli()