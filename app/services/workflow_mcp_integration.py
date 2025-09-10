"""
Universal Workflow MCP Integration Service
Ensures ALL future workflows automatically inherit intelligent MCP integration
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from pathlib import Path
import importlib
import inspect
import sys

# Import our core services
from .mcp_server_manager import get_mcp_manager, ensure_mcp_servers_ready
from .mcp_registry import get_mcp_registry
from .agent_data_requirements import get_requirements_analyzer
from .intelligent_query_service import IntelligentQueryService, QueryMode

logger = logging.getLogger(__name__)

class WorkflowMCPIntegration:
    """
    Universal service that automatically enhances ANY workflow with MCP capabilities
    This ensures future-compatibility and consistent behavior across all workflows
    """
    
    def __init__(self):
        self.registry = get_mcp_registry()
        self.mcp_manager = get_mcp_manager()
        self.requirements_analyzer = get_requirements_analyzer()
        self.query_service = IntelligentQueryService()
        self._workflow_configs = {}
        
    async def auto_enhance_workflow(self, workflow_module: Any, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically enhance any workflow with MCP integration
        This is the key future-proofing function that works with ANY workflow
        """
        workflow_name = getattr(workflow_module, '__name__', 'unknown_workflow')
        logger.info(f"Auto-enhancing workflow: {workflow_name}")
        
        try:
            # Step 1: Ensure MCP servers are ready
            servers_ready = await ensure_mcp_servers_ready()
            if not servers_ready:
                logger.warning(f"MCP servers not ready for {workflow_name}, using fallback")
                return {"mcp_enhanced": False, "fallback_reason": "servers_not_ready"}
            
            # Step 2: Auto-discover agents in the workflow
            agents = await self._discover_workflow_agents(workflow_module)
            logger.info(f"Discovered {len(agents)} agents in {workflow_name}")
            
            # Step 3: Analyze data requirements for all agents
            requirements = await self._analyze_workflow_requirements(workflow_name, agents)
            
            # Step 4: Auto-assign optimal MCP servers
            server_assignments = await self._auto_assign_mcp_servers(requirements)
            
            # Step 5: Pre-fetch critical data
            prefetch_data = await self._execute_intelligent_prefetch(
                workflow_state.get("client_id"),
                requirements,
                server_assignments
            )
            
            # Step 6: Create enhanced workflow context
            enhanced_context = {
                "mcp_enhanced": True,
                "workflow_name": workflow_name,
                "discovered_agents": [agent["name"] for agent in agents],
                "mcp_servers_assigned": server_assignments,
                "prefetch_data": prefetch_data,
                "requirements_analysis": requirements,
                "enhancement_timestamp": datetime.now().isoformat(),
                "auto_enhancement_version": "1.0.0"
            }
            
            # Step 7: Store configuration for future reference
            self._workflow_configs[workflow_name] = enhanced_context
            
            logger.info(f"Successfully auto-enhanced {workflow_name} with {len(server_assignments)} MCP integrations")
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Failed to auto-enhance workflow {workflow_name}: {e}")
            return {
                "mcp_enhanced": False,
                "error": str(e),
                "fallback_reason": "enhancement_failed"
            }
    
    async def _discover_workflow_agents(self, workflow_module: Any) -> List[Dict[str, Any]]:
        """
        Automatically discover all agents in a workflow module
        Works with any LangGraph workflow structure
        """
        agents = []
        
        try:
            # Method 1: Look for common agent patterns
            for attr_name in dir(workflow_module):
                attr = getattr(workflow_module, attr_name)
                
                # Look for agent dictionaries (common pattern)
                if isinstance(attr, dict) and attr_name.endswith('_AGENT'):
                    agents.append({
                        "name": attr_name.replace('_AGENT', '').lower(),
                        "config": attr,
                        "type": "dict_agent",
                        "source": "module_attribute"
                    })
                
                # Look for agent classes
                elif inspect.isclass(attr) and 'agent' in attr_name.lower():
                    agents.append({
                        "name": attr_name.lower(),
                        "config": {"class": attr},
                        "type": "class_agent", 
                        "source": "class_definition"
                    })
            
            # Method 2: Look for LangGraph node functions
            if hasattr(workflow_module, '__dict__'):
                for name, func in workflow_module.__dict__.items():
                    if callable(func) and any(keyword in name.lower() for keyword in ['agent', 'analyze', 'process', 'generate']):
                        # Skip private and utility functions
                        if not name.startswith('_') and name not in ['run_calendar_workflow', 'get_requirements_analyzer']:
                            agents.append({
                                "name": name,
                                "config": {"function": func},
                                "type": "function_agent",
                                "source": "workflow_function"
                            })
            
            # Method 3: Import and check for multi-agent patterns
            try:
                # Check if this workflow imports from our multi-agent system
                module_file = inspect.getfile(workflow_module)
                with open(module_file, 'r') as f:
                    content = f.read()
                
                # Look for agent imports
                import_lines = [line for line in content.split('\n') if 'import' in line and 'agent' in line.lower()]
                for line in import_lines:
                    if 'from integrations.langchain_core.agents' in line:
                        # Extract agent name from import
                        if 'import' in line:
                            agent_name = line.split('import')[-1].strip()
                            if agent_name not in [a["name"] for a in agents]:
                                agents.append({
                                    "name": agent_name.replace('_AGENT', '').lower(),
                                    "config": {"imported": True},
                                    "type": "imported_agent",
                                    "source": "import_statement"
                                })
            except Exception as e:
                logger.debug(f"Could not analyze imports: {e}")
            
        except Exception as e:
            logger.warning(f"Error discovering agents: {e}")
        
        return agents
    
    async def _analyze_workflow_requirements(self, workflow_name: str, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze data requirements for all discovered agents
        """
        all_requirements = {
            "workflow_name": workflow_name,
            "total_agents": len(agents),
            "agent_specs": [],
            "combined_data_sources": set(),
            "total_queries": 0
        }
        
        for agent in agents:
            try:
                # Try to get requirements using our analyzer
                if agent["type"] == "dict_agent" and "config" in agent:
                    prompt_template = agent["config"].get("prompt_template", "")
                    if prompt_template:
                        spec = self.requirements_analyzer.analyze_agent_prompt(
                            agent["name"],
                            prompt_template
                        )
                        all_requirements["agent_specs"].append(spec)
                        all_requirements["combined_data_sources"].update(spec.data_requirements)
                        all_requirements["total_queries"] += len(spec.custom_queries)
                
                # For other agent types, create basic requirements
                else:
                    basic_spec = self.requirements_analyzer.create_basic_agent_spec(
                        agent["name"],
                        agent.get("config", {})
                    )
                    all_requirements["agent_specs"].append(basic_spec)
                    
            except Exception as e:
                logger.warning(f"Could not analyze requirements for agent {agent['name']}: {e}")
        
        # Convert set to list for JSON serialization
        all_requirements["combined_data_sources"] = list(all_requirements["combined_data_sources"])
        
        return all_requirements
    
    async def _auto_assign_mcp_servers(self, requirements: Dict[str, Any]) -> Dict[str, str]:
        """
        Automatically assign optimal MCP servers to agents based on their requirements
        """
        assignments = {}
        
        try:
            # Get all online servers
            online_servers = self.registry.get_online_servers()
            
            if not online_servers:
                logger.warning("No online MCP servers available for assignment")
                return assignments
            
            # Create a capability map
            capability_map = {}
            for server in online_servers:
                for capability in server.capabilities:
                    if capability not in capability_map:
                        capability_map[capability] = []
                    capability_map[capability].append(server)
            
            # Assign servers to agents based on data requirements
            for agent_spec in requirements.get("agent_specs", []):
                agent_name = agent_spec.agent_name
                
                # Find best server for this agent's requirements
                best_server = None
                best_score = 0
                
                for server in online_servers:
                    score = 0
                    
                    # Score based on capability overlap
                    for data_req in agent_spec.data_requirements:
                        if any(cap in data_req.lower() for cap in server.capabilities):
                            score += 1
                    
                    # Prefer Klaviyo for marketing data
                    if "klaviyo" in server.name.lower() and any("campaign" in req.lower() or "metric" in req.lower() 
                                                                for req in agent_spec.data_requirements):
                        score += 2
                    
                    if score > best_score:
                        best_score = score
                        best_server = server
                
                if best_server:
                    assignments[agent_name] = best_server.id
                    logger.info(f"Assigned {best_server.name} to agent {agent_name} (score: {best_score})")
                else:
                    # Default to first available server
                    assignments[agent_name] = online_servers[0].id
                    logger.info(f"Default assignment: {online_servers[0].name} to agent {agent_name}")
        
        except Exception as e:
            logger.error(f"Error in auto-assignment: {e}")
        
        return assignments
    
    async def _execute_intelligent_prefetch(
        self, 
        client_id: Optional[str], 
        requirements: Dict[str, Any],
        server_assignments: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Execute intelligent prefetch of data based on workflow requirements
        """
        prefetch_results = {}
        
        if not client_id:
            logger.warning("No client_id provided, skipping prefetch")
            return prefetch_results
        
        try:
            # Execute top priority queries for each agent
            for agent_spec in requirements.get("agent_specs", []):
                agent_name = agent_spec.agent_name
                
                if not agent_spec.custom_queries:
                    continue
                
                # Execute the most important queries (limit to 2 per agent for performance)
                agent_results = []
                for query in agent_spec.custom_queries[:2]:
                    try:
                        result = await self.query_service.query(
                            natural_query=query,
                            client_id=client_id,
                            mode=QueryMode.AUTO
                        )
                        
                        if result.get("success"):
                            agent_results.append({
                                "query": query,
                                "status": "success",
                                "data_preview": str(result.get("results", ""))[:200] + "..." if len(str(result.get("results", ""))) > 200 else str(result.get("results", "")),
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            agent_results.append({
                                "query": query,
                                "status": "failed",
                                "error": result.get("error", "Unknown error"),
                                "timestamp": datetime.now().isoformat()
                            })
                            
                    except Exception as e:
                        agent_results.append({
                            "query": query,
                            "status": "error",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
                
                if agent_results:
                    prefetch_results[agent_name] = {
                        "queries_executed": len(agent_results),
                        "successful_queries": len([r for r in agent_results if r["status"] == "success"]),
                        "results": agent_results,
                        "assigned_server": server_assignments.get(agent_name, "unknown")
                    }
        
        except Exception as e:
            logger.error(f"Error in intelligent prefetch: {e}")
            prefetch_results["error"] = str(e)
        
        return prefetch_results
    
    def get_workflow_enhancement(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get the enhancement context for a specific workflow"""
        return self._workflow_configs.get(workflow_name)
    
    def list_enhanced_workflows(self) -> List[str]:
        """List all workflows that have been enhanced"""
        return list(self._workflow_configs.keys())
    
    async def refresh_workflow_enhancements(self) -> Dict[str, Any]:
        """Refresh all workflow enhancements (useful after adding new MCP servers)"""
        results = {}
        
        for workflow_name in self._workflow_configs.keys():
            try:
                # Re-analyze and update the enhancement
                logger.info(f"Refreshing enhancement for {workflow_name}")
                # This would require re-importing the workflow module, which is complex
                # For now, just refresh the server assignments
                requirements = self._workflow_configs[workflow_name]["requirements_analysis"]
                new_assignments = await self._auto_assign_mcp_servers(requirements)
                
                self._workflow_configs[workflow_name]["mcp_servers_assigned"] = new_assignments
                self._workflow_configs[workflow_name]["last_refreshed"] = datetime.now().isoformat()
                
                results[workflow_name] = "refreshed"
                
            except Exception as e:
                logger.error(f"Failed to refresh {workflow_name}: {e}")
                results[workflow_name] = f"failed: {e}"
        
        return results

# Global instance
_workflow_integration: Optional[WorkflowMCPIntegration] = None

def get_workflow_mcp_integration() -> WorkflowMCPIntegration:
    """Get the global workflow MCP integration service"""
    global _workflow_integration
    if _workflow_integration is None:
        _workflow_integration = WorkflowMCPIntegration()
    return _workflow_integration

async def auto_enhance_any_workflow(workflow_module: Any, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to automatically enhance any workflow with MCP capabilities
    
    Usage in any workflow:
    ```python
    from app.services.workflow_mcp_integration import auto_enhance_any_workflow
    
    # At the start of your workflow
    enhancement = await auto_enhance_any_workflow(sys.modules[__name__], state)
    if enhancement["mcp_enhanced"]:
        # Workflow now has intelligent MCP integration!
        # Use enhancement["prefetch_data"] for pre-loaded data
    ```
    """
    integration = get_workflow_mcp_integration()
    return await integration.auto_enhance_workflow(workflow_module, workflow_state)

# Future-proofing decorator for workflow functions
def mcp_enhanced_workflow(func):
    """
    Decorator that automatically adds MCP enhancement to any workflow function
    
    Usage:
    ```python
    from app.services.workflow_mcp_integration import mcp_enhanced_workflow
    
    @mcp_enhanced_workflow
    async def my_new_workflow(state):
        # This workflow automatically gets MCP integration!
        return final_result
    ```
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract state from arguments
        state = args[0] if args and isinstance(args[0], dict) else kwargs.get('state', {})
        
        # Auto-enhance the workflow
        enhancement = await auto_enhance_any_workflow(
            sys.modules[func.__module__],
            state
        )
        
        # Add enhancement to state
        if isinstance(state, dict):
            state['mcp_enhancement'] = enhancement
        
        # Call the original function
        result = await func(*args, **kwargs)
        
        # Log the enhancement results
        logger.info(f"Workflow {func.__name__} executed with MCP enhancement: {enhancement.get('mcp_enhanced', False)}")
        
        return result
    
    return wrapper