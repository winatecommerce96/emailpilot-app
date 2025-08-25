"""
Agent run management with SSE streaming.
"""

import uuid
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime, timedelta
from google.cloud import firestore

from ..config import get_config
from ..engine.facade import prepare_run, invoke_agent, abort_controller
from .registry import get_agent_registry

logger = logging.getLogger(__name__)


def start_run(
    agent_name: str,
    user_id: Optional[str] = None,
    brand: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    task: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start a new agent run.
    
    Args:
        agent_name: Agent to run
        user_id: User ID
        brand: Brand context
        context: Execution context
        overrides: Variable overrides
        task: Task override
    
    Returns:
        Run information including run_id
    """
    try:
        # Prepare run
        prepared = prepare_run(
            agent_name=agent_name,
            user_id=user_id,
            brand=brand,
            context=context,
            overrides=overrides
        )
        
        # Start async execution
        import threading
        
        def run_async():
            try:
                invoke_agent(prepared, task=task)
            except Exception as e:
                logger.error(f"Async run failed: {e}")
        
        thread = threading.Thread(target=run_async)
        thread.daemon = True
        thread.start()
        
        return {
            "run_id": prepared.run_id,
            "agent_name": agent_name,
            "status": "started",
            "started_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to start run: {e}")
        raise


def abort_run(run_id: str) -> bool:
    """
    Abort a running agent.
    
    Args:
        run_id: Run ID to abort
    
    Returns:
        Success flag
    """
    success = abort_controller(run_id)
    
    if success:
        # Update Firestore
        config = get_config()
        if config.firestore_project:
            try:
                db = firestore.Client(project=config.firestore_project)
                db.collection("agent_runs").document(run_id).update({
                    "status": "aborted",
                    "aborted_at": datetime.utcnow()
                })
            except Exception as e:
                logger.error(f"Failed to update abort status: {e}")
    
    return success


def replay_run(run_id: str, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Replay a run from a checkpoint.
    
    Args:
        run_id: Original run ID
        checkpoint_id: Checkpoint to resume from
    
    Returns:
        New run information
    """
    config = get_config()
    if not config.firestore_project:
        raise ValueError("Firestore required for replay")
    
    db = firestore.Client(project=config.firestore_project)
    
    # Get original run
    doc = db.collection("agent_runs").document(run_id).get()
    if not doc.exists:
        raise ValueError(f"Run not found: {run_id}")
    
    original = doc.to_dict()
    
    # Start new run with same parameters
    return start_run(
        agent_name=original["agent_name"],
        user_id=original.get("user_id"),
        brand=original.get("brand"),
        context=original.get("context"),
        overrides=original.get("variables"),
        task=original.get("task")
    )


def list_runs(
    limit: int = 100,
    agent_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    List agent runs.
    
    Args:
        limit: Maximum number to return
        agent_filter: Filter by agent name
        user_filter: Filter by user ID
        status_filter: Filter by status
        since: Filter by start time
    
    Returns:
        List of run summaries
    """
    config = get_config()
    if not config.firestore_project:
        return []
    
    db = firestore.Client(project=config.firestore_project)
    
    query = db.collection("agent_runs").order_by(
        "started_at", direction=firestore.Query.DESCENDING
    ).limit(limit)
    
    if agent_filter:
        query = query.where("agent_name", "==", agent_filter)
    if user_filter:
        query = query.where("user_id", "==", user_filter)
    if status_filter:
        query = query.where("status", "==", status_filter)
    if since:
        query = query.where("started_at", ">=", since)
    
    runs = []
    for doc in query.stream():
        run = doc.to_dict()
        runs.append({
            "run_id": run["run_id"],
            "agent_name": run["agent_name"],
            "status": run["status"],
            "started_at": run["started_at"].isoformat() if run.get("started_at") else None,
            "duration_ms": run.get("duration_ms"),
            "user_id": run.get("user_id"),
            "brand": run.get("brand")
        })
    
    return runs


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed run information.
    
    Args:
        run_id: Run ID
    
    Returns:
        Run details or None
    """
    config = get_config()
    if not config.firestore_project:
        return None
    
    db = firestore.Client(project=config.firestore_project)
    
    doc = db.collection("agent_runs").document(run_id).get()
    if not doc.exists:
        return None
    
    return doc.to_dict()


async def stream_run_events(run_id: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream run events via SSE.
    
    Args:
        run_id: Run ID to stream
    
    Yields:
        Event dictionaries
    """
    config = get_config()
    if not config.firestore_project:
        return
    
    db = firestore.Client(project=config.firestore_project)
    doc_ref = db.collection("agent_runs").document(run_id)
    
    # Watch for changes
    last_event_count = 0
    
    while True:
        try:
            doc = doc_ref.get()
            if not doc.exists:
                yield {
                    "event": "error",
                    "data": {"message": "Run not found"}
                }
                break
            
            run = doc.to_dict()
            
            # Check status
            if run["status"] in ["completed", "failed", "aborted"]:
                yield {
                    "event": "complete",
                    "data": {
                        "status": run["status"],
                        "final_answer": run.get("final_answer"),
                        "error": run.get("error")
                    }
                }
                break
            
            # Stream new events
            events = run.get("events", [])
            if len(events) > last_event_count:
                for event in events[last_event_count:]:
                    yield {
                        "event": "update",
                        "data": event
                    }
                last_event_count = len(events)
            
            # Wait before next check
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error streaming events: {e}")
            yield {
                "event": "error",
                "data": {"message": str(e)}
            }
            break


def get_run_artifacts(run_id: str) -> Dict[str, Any]:
    """
    Get artifacts from a run.
    
    Args:
        run_id: Run ID
    
    Returns:
        Artifacts dictionary
    """
    run = get_run(run_id)
    if not run:
        return {}
    
    return {
        "plan": run.get("plan"),
        "tool_calls": run.get("tool_calls", []),
        "final_answer": run.get("final_answer"),
        "checkpoints": run.get("checkpoints", [])
    }