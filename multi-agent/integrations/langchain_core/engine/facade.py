"""
High-level facade for agent engine operations.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from google.cloud import firestore

from ..config import get_config
from ..deps import ModelPolicyResolver
from ..vars.registry import get_variable_registry
from ..admin.registry import get_agent_registry
from .graph import create_agent_graph, AgentGraph

logger = logging.getLogger(__name__)


@dataclass
class PreparedRun:
    """Prepared run with validated inputs and resolved configuration."""
    run_id: str
    agent_name: str
    user_id: Optional[str]
    brand: Optional[str]
    context: Dict[str, Any]
    variables: Dict[str, Any]
    model_config: Dict[str, Any]
    policy: Dict[str, Any]
    graph: AgentGraph


# Global abort controller
_abort_signals: Dict[str, bool] = {}


def prepare_run(
    agent_name: str,
    user_id: Optional[str] = None,
    brand: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> PreparedRun:
    """
    Prepare an agent run with validation and configuration.
    
    Args:
        agent_name: Name of the agent to run
        user_id: User ID for policy resolution
        brand: Brand context
        context: Execution context
        overrides: Variable overrides
    
    Returns:
        PreparedRun with validated configuration
    
    Raises:
        ValueError: If validation fails
    """
    logger.info(f"Preparing run for agent: {agent_name}")
    
    # Get agent definition
    registry = get_agent_registry()
    agent_def = registry.get_agent(agent_name)
    
    if not agent_def:
        raise ValueError(f"Agent not found: {agent_name}")
    
    # Get variables
    var_registry = get_variable_registry()
    agent_vars = var_registry.get_agent_variables(agent_name)
    
    # Build context
    full_context = {
        **(context or {}),
        "user_id": user_id,
        "brand": brand,
        "agent_name": agent_name
    }
    
    # Apply overrides
    if overrides:
        full_context.update(overrides)
    
    # Validate variables
    validated_vars = var_registry.validate_inputs(
        agent_name,
        full_context
    )
    
    # Resolve model policy
    config = get_config()
    policy_resolver = ModelPolicyResolver(config)
    
    model_config = policy_resolver.resolve(
        user_id=user_id,
        brand=brand
    )
    
    # Get agent policy
    agent_policy = agent_def.get("policy", {})
    
    # Create graph
    from ..agents.policies import AgentPolicy
    
    policy = AgentPolicy(
        max_tool_calls=agent_policy.get("max_tool_calls", 15),
        timeout_seconds=agent_policy.get("timeout_seconds", 60),
        allowed_tools=agent_policy.get("allowed_tools"),
        denied_tools=agent_policy.get("denied_tools")
    )
    
    graph = create_agent_graph(
        policy=policy,
        config=config
    )
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    return PreparedRun(
        run_id=run_id,
        agent_name=agent_name,
        user_id=user_id,
        brand=brand,
        context=full_context,
        variables=validated_vars,
        model_config=model_config,
        policy=agent_policy,
        graph=graph
    )


def invoke_agent(
    prepared: PreparedRun,
    task: Optional[str] = None,
    checkpoint_id: Optional[str] = None,
    stream_callback=None
) -> Dict[str, Any]:
    """
    Invoke a prepared agent run.
    
    Args:
        prepared: PreparedRun from prepare_run()
        task: Task override (uses agent default if not provided)
        checkpoint_id: Resume from checkpoint
        stream_callback: Callback for streaming events
    
    Returns:
        Execution result
    """
    logger.info(f"Invoking agent {prepared.agent_name} - Run ID: {prepared.run_id}")
    
    # Get task
    if not task:
        registry = get_agent_registry()
        agent_def = registry.get_agent(prepared.agent_name)
        task = agent_def.get("default_task", "Process the provided context")
    
    # Format task with variables
    try:
        task = task.format(**prepared.variables)
    except KeyError as e:
        logger.warning(f"Failed to format task with variables: {e}")
    
    # Store run in Firestore
    if prepared.context.get("persist_runs", True):
        _store_run_start(prepared, task)
    
    # Set up abort signal
    _abort_signals[prepared.run_id] = False
    
    try:
        # Invoke graph
        result = prepared.graph.invoke(
            task=task,
            context=prepared.context,
            run_id=prepared.run_id,
            user_id=prepared.user_id,
            brand=prepared.brand,
            checkpoint_id=checkpoint_id
        )
        
        # Check for abort
        if _abort_signals.get(prepared.run_id):
            result["aborted"] = True
            result["error"] = "Run aborted by user"
        
        # Store completion
        if prepared.context.get("persist_runs", True):
            _store_run_completion(prepared.run_id, result)
        
        return result
        
    finally:
        # Clean up abort signal
        _abort_signals.pop(prepared.run_id, None)


def abort_controller(run_id: str) -> bool:
    """
    Abort a running agent.
    
    Args:
        run_id: Run ID to abort
    
    Returns:
        True if abort signal was set
    """
    if run_id in _abort_signals:
        _abort_signals[run_id] = True
        logger.info(f"Abort signal set for run: {run_id}")
        return True
    return False


def list_available_vars(agent_name: str) -> List[Dict[str, Any]]:
    """
    List available variables for an agent.
    
    Args:
        agent_name: Agent name
    
    Returns:
        List of variable definitions
    """
    var_registry = get_variable_registry()
    return var_registry.get_agent_variables(agent_name)


def dry_run(
    agent_name: str,
    user_id: Optional[str] = None,
    brand: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform a dry run to validate configuration without execution.
    
    Args:
        agent_name: Agent to test
        user_id: User ID
        brand: Brand
        context: Context
        overrides: Overrides
    
    Returns:
        Validation result with prepared configuration
    """
    try:
        prepared = prepare_run(
            agent_name=agent_name,
            user_id=user_id,
            brand=brand,
            context=context,
            overrides=overrides
        )
        
        return {
            "valid": True,
            "run_id": prepared.run_id,
            "variables": prepared.variables,
            "model_config": prepared.model_config,
            "policy": prepared.policy
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


def _store_run_start(prepared: PreparedRun, task: str):
    """Store run start in Firestore."""
    try:
        config = get_config()
        if not config.firestore_project:
            return
        
        db = firestore.Client(project=config.firestore_project)
        
        doc = {
            "run_id": prepared.run_id,
            "agent_name": prepared.agent_name,
            "user_id": prepared.user_id,
            "brand": prepared.brand,
            "task": task,
            "context": prepared.context,
            "variables": prepared.variables,
            "model_config": prepared.model_config,
            "policy": prepared.policy,
            "status": "running",
            "started_at": datetime.utcnow(),
            "events": []
        }
        
        db.collection("agent_runs").document(prepared.run_id).set(doc)
        
    except Exception as e:
        logger.error(f"Failed to store run start: {e}")


def _store_run_completion(run_id: str, result: Dict[str, Any]):
    """Store run completion in Firestore."""
    try:
        config = get_config()
        if not config.firestore_project:
            return
        
        db = firestore.Client(project=config.firestore_project)
        
        update = {
            "status": "completed" if result.get("success") else "failed",
            "completed_at": datetime.utcnow(),
            "duration_ms": result.get("metadata", {}).get("duration_ms"),
            "final_answer": result.get("final_answer"),
            "error": result.get("error"),
            "tool_calls": result.get("tool_calls", []),
            "aborted": result.get("aborted", False)
        }
        
        db.collection("agent_runs").document(run_id).update(update)
        
    except Exception as e:
        logger.error(f"Failed to store run completion: {e}")