"""
Agent module for tool-using agents with policies.

Provides ReAct/Tool-Calling agents with native and MCP-backed tools.
"""

from .tools import (
    get_native_tools,
    get_mcp_tools,
    get_all_tools,
    firestore_ro_get,
    http_get_json,
    simple_cache_get,
    simple_cache_set
)
from .policies import AgentPolicy, PolicyEnforcer, PolicyViolation
from .agent_v2 import SimpleAgentExecutor as AgentExecutor, run_agent_task, AgentResult

__all__ = [
    "get_native_tools",
    "get_mcp_tools",
    "get_all_tools",
    "firestore_ro_get",
    "http_get_json",
    "simple_cache_get",
    "simple_cache_set",
    "AgentPolicy",
    "PolicyEnforcer",
    "PolicyViolation",
    "AgentExecutor",
    "run_agent_task",
    "AgentResult"
]