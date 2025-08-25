"""
Enhanced Agent Service with AI Models Integration
This service seamlessly integrates the AI Models Admin with the Multi-Agent System
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from google.cloud import firestore
from app.deps import get_db
from app.deps.secrets import get_secret_manager_service
# Import AI Orchestrator as primary interface
try:
    from app.core.ai_orchestrator import get_ai_orchestrator, ai_complete
    AI_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    AI_ORCHESTRATOR_AVAILABLE = False
    logger.warning("AI Orchestrator not available, using legacy AI Models Service")

# Fallback to legacy AI Models Service - runtime import only
from app.services.ai_models_service import get_ai_models_service

if TYPE_CHECKING:
    from app.services.ai_models_service import AIModelsService

logger = logging.getLogger(__name__)

# Path to agent configuration files
AGENT_CONFIG_PATH = Path(__file__).parent.parent.parent / "email-sms-mcp-server"
INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "agents_config.json"
CUSTOM_INSTRUCTIONS_FILE = AGENT_CONFIG_PATH / "custom_instructions.json"

class EnhancedEmailSMSAgent:
    """Enhanced agent that uses AI Models Admin for dynamic prompt execution"""
    
    def __init__(self, name: str, config: Dict[str, Any], ai_service: "AIModelsService" = None):
        self.name = name
        self.role = config.get("role", "No role defined")
        self.expertise = config.get("expertise", [])
        self.responsibilities = config.get("responsibilities", [])
        self.context = config
        self.ai_service = ai_service
        self.use_orchestrator = AI_ORCHESTRATOR_AVAILABLE
        
        # Prompt configuration from Firestore
        self.prompt_id = config.get("prompt_id")  # Can be set in custom_instructions.json
        self.preferred_provider = config.get("preferred_provider", "gemini")
        self.preferred_model = config.get("preferred_model")
        self.fallback_providers = config.get("fallback_providers", ["openai", "claude"])
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request using AI Orchestrator or AI Models Admin for actual LLM execution"""
        
        logger.info(f"Agent '{self.name}' processing request with {'AI Orchestrator' if self.use_orchestrator else 'AI Models'} integration")
        
        try:
            # Build context for the AI prompt
            prompt_context = {
                "agent_name": self.name,
                "agent_role": self.role,
                "agent_expertise": ", ".join(self.expertise),
                "agent_responsibilities": "\n".join(self.responsibilities),
                "request_data": json.dumps(request, indent=2),
                "timestamp": datetime.utcnow().isoformat(),
                "collaboration_with": ", ".join(self.context.get("collaboration_with", []))
            }
            # Try to pass through user/client identifiers for logging/stats
            try:
                if isinstance(request, dict):
                    if request.get("user_id"):
                        prompt_context["user_id"] = request.get("user_id")
                    if request.get("client_id") or request.get("account_id") or request.get("metric_id"):
                        prompt_context["client_id"] = request.get("client_id") or request.get("account_id") or request.get("metric_id")
            except Exception:
                pass
            
            # Use AI Orchestrator if available
            if self.use_orchestrator:
                # Build messages for orchestrator
                prompt_text = self._create_generic_prompt(prompt_context)
                messages = [{"role": "user", "content": prompt_text}]
                
                try:
                    response = await ai_complete(
                        messages=messages,
                        provider=self.preferred_provider,
                        model=self.preferred_model,
                        temperature=0.7,
                        max_tokens=2000
                    )
                    result = {
                        "success": True,
                        "response": response,
                        "provider": self.preferred_provider,
                        "model": self.preferred_model or "auto"
                    }
                except Exception as e:
                    logger.error(f"Orchestrator failed: {e}")
                    result = {"success": False, "error": str(e)}
            else:
                # Fallback to legacy AI service
                if self.prompt_id:
                    # Use the configured prompt
                    result = await self.ai_service.execute_prompt(
                        prompt_id=self.prompt_id,
                        variables=prompt_context,
                        override_provider=self.preferred_provider,
                        override_model=self.preferred_model
                    )
                else:
                    # Try to find an agent-specific prompt by category
                    result = await self.ai_service.execute_agent_prompt(
                        agent_type=self.name,
                        context=prompt_context
                    )
            
            # If primary provider fails, try fallbacks
            if not result.get("success") and self.fallback_providers:
                for fallback in self.fallback_providers:
                    logger.warning(f"Primary provider failed, trying fallback: {fallback}")
                    
                    if self.use_orchestrator:
                        # Use orchestrator with fallback provider
                        try:
                            prompt_text = self._create_generic_prompt(prompt_context)
                            messages = [{"role": "user", "content": prompt_text}]
                            response = await ai_complete(
                                messages=messages,
                                provider=fallback,
                                temperature=0.7,
                                max_tokens=2000
                            )
                            result = {
                                "success": True,
                                "response": response,
                                "provider": fallback,
                                "model": "auto"
                            }
                        except Exception as e:
                            logger.error(f"Orchestrator fallback {fallback} failed: {e}")
                            result = {"success": False, "error": str(e)}
                    else:
                        # Legacy fallback
                        if self.prompt_id:
                            result = await self.ai_service.execute_prompt(
                                prompt_id=self.prompt_id,
                                variables=prompt_context,
                                override_provider=fallback
                            )
                        else:
                            # Create a generic prompt if no specific one exists
                            generic_prompt = self._create_generic_prompt(prompt_context)
                            result = await self._execute_generic_prompt(generic_prompt, fallback)
                    
                    if result.get("success"):
                        break
            
            if result.get("success"):
                # Parse the AI response and structure it
                ai_response = result.get("response", "")
                
                # Try to parse JSON if the AI returned structured data
                try:
                    if ai_response.strip().startswith("{"):
                        structured_response = json.loads(ai_response)
                    else:
                        structured_response = {"content": ai_response}
                except:
                    structured_response = {"content": ai_response}
                
                return {
                    "agent_name": self.name,
                    "role": self.role,
                    "status": "success",
                    "output": structured_response,
                    "ai_provider": result.get("provider"),
                    "ai_model": result.get("model"),
                    "next_steps": self.context.get("collaboration_with", []),
                    "metadata": {
                        "prompt_id": result.get("prompt_id"),
                        "execution_time": datetime.utcnow().isoformat()
                    }
                }
            else:
                # Fallback to simulated response if all AI providers fail
                logger.error(f"All AI providers failed for agent {self.name}, using fallback")
                return self._create_fallback_response(request)
                
        except Exception as e:
            logger.error(f"Error in agent {self.name}: {e}")
            return self._create_fallback_response(request)
    
    def _create_generic_prompt(self, context: Dict[str, Any]) -> str:
        """Create a generic prompt when no specific prompt exists"""
        return f"""
You are {context['agent_name']}, an AI agent with the following role: {context['agent_role']}

Your expertise includes: {context['agent_expertise']}

Your responsibilities are:
{context['agent_responsibilities']}

Based on the following request, provide a detailed response that fulfills your role:

Request Data:
{context['request_data']}

Please provide a structured response that includes:
1. Your analysis of the request
2. Your recommendations based on your expertise
3. Specific actions or outputs related to your responsibilities
4. Suggestions for the next agents to involve: {context['collaboration_with']}

Format your response as JSON if possible.
"""
    
    async def _execute_generic_prompt(self, prompt: str, provider: str) -> Dict[str, Any]:
        """Execute a generic prompt directly with a provider"""
        try:
            if provider == "gemini":
                model = "gemini-1.5-pro-latest"
                text = await self.ai_service._execute_gemini(prompt, model)
                return {"success": True, "response": text, "provider": provider, "model": model}
            elif provider == "openai":
                model = "gpt-4"
                text = await self.ai_service._execute_openai(prompt, model)
                return {"success": True, "response": text, "provider": provider, "model": model}
            elif provider == "claude":
                model = "claude-3-sonnet"
                text = await self.ai_service._execute_claude(prompt, model)
                return {"success": True, "response": text, "provider": provider, "model": model}
            else:
                return {"success": False, "error": f"Unknown provider: {provider}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_fallback_response(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback response when AI execution fails"""
        return {
            "agent_name": self.name,
            "role": self.role,
            "status": "fallback",
            "output": {
                "message": f"AI execution failed. This is a fallback response from {self.name}.",
                "request_received": request,
                "suggested_actions": self.responsibilities[:3] if self.responsibilities else []
            },
            "next_steps": self.context.get("collaboration_with", []),
            "metadata": {
                "fallback_reason": "AI providers unavailable",
                "execution_time": datetime.utcnow().isoformat()
            }
        }

class EnhancedMultiAgentOrchestrator:
    """Enhanced orchestrator that uses AI Models Admin for agent coordination"""
    
    def __init__(self, db: firestore.Client = None, secret_manager = None):
        self.agents: Dict[str, EnhancedEmailSMSAgent] = {}
        self.db = db or get_db()
        self.secret_manager = secret_manager or get_secret_manager_service()
        # Use AI Orchestrator if available, otherwise fall back to legacy service
        if AI_ORCHESTRATOR_AVAILABLE:
            self.orchestrator = get_ai_orchestrator()
            self.ai_service = None  # Will pass None to agents
        else:
            self.orchestrator = None
            self.ai_service = get_ai_models_service(self.db, self.secret_manager)
        self._load_agents()
    
    def _load_agents(self):
        """Load agent configurations and create enhanced agent instances"""
        
        # Load default configuration
        if not INSTRUCTIONS_FILE.exists():
            logger.error(f"Default agent configuration file not found at {INSTRUCTIONS_FILE}")
            return
            
        with open(INSTRUCTIONS_FILE, 'r') as f:
            default_config = json.load(f)
        
        # Load custom instructions if they exist
        custom_config = {}
        if CUSTOM_INSTRUCTIONS_FILE.exists():
            with open(CUSTOM_INSTRUCTIONS_FILE, 'r') as f:
                custom_config = json.load(f)
        
        # Check Firestore for agent-specific prompt configurations
        firestore_config = self._load_firestore_agent_config()
        
        # Merge configurations: defaults < custom file < Firestore
        agents_config = default_config.get("agents", {})
        
        # Apply custom file overrides
        for agent_name, config in custom_config.get("agents", {}).items():
            if agent_name in agents_config:
                agents_config[agent_name].update(config)
            else:
                agents_config[agent_name] = config
        
        # Apply Firestore overrides (highest priority)
        for agent_name, config in firestore_config.items():
            if agent_name in agents_config:
                agents_config[agent_name].update(config)
        
        # Create enhanced agent instances
        for agent_name, agent_config in agents_config.items():
            self.agents[agent_name] = EnhancedEmailSMSAgent(
                agent_name, 
                agent_config,
                self.ai_service
            )
            logger.info(f"Loaded enhanced agent: {agent_name} with AI Models integration")
    
    def _load_firestore_agent_config(self) -> Dict[str, Dict[str, Any]]:
        """Load agent-specific configurations from Firestore.

        Sources of truth (highest priority last):
        - ai_prompts (category == 'agent') for mapping prompt -> agent via metadata.agent_type
        - agent_configurations collection for per-agent preferences (provider, model, fallbacks, custom_instructions)
        """
        agent_configs: Dict[str, Dict[str, Any]] = {}

        # 1) Map prompts to agents from ai_prompts
        try:
            prompts = self.db.collection("ai_prompts").where("category", "==", "agent").stream()
            for doc in prompts:
                prompt_data = doc.to_dict()
                agent_type = prompt_data.get("metadata", {}).get("agent_type")
                if not agent_type:
                    continue
                agent_configs.setdefault(agent_type, {})
                agent_configs[agent_type].update({
                    "prompt_id": doc.id,
                    "preferred_provider": prompt_data.get("model_provider", "gemini"),
                    "preferred_model": prompt_data.get("model_name")
                })
                logger.info(f"Loaded Firestore prompt config for agent: {agent_type}")
        except Exception as e:
            logger.warning(f"Could not load Firestore ai_prompts configs: {e}")

        # 2) Overlay agent_configurations (preferred/fallback providers, custom instructions)
        try:
            config_docs = self.db.collection("agent_configurations").stream()
            for doc in config_docs:
                data = doc.to_dict() or {}
                agent_name = data.get("agent_name") or doc.id
                if not agent_name:
                    continue
                agent_configs.setdefault(agent_name, {})
                # Only set keys if present in config
                if "prompt_id" in data and data["prompt_id"]:
                    agent_configs[agent_name]["prompt_id"] = data["prompt_id"]
                if "preferred_provider" in data and data["preferred_provider"]:
                    agent_configs[agent_name]["preferred_provider"] = data["preferred_provider"]
                if "preferred_model" in data and data["preferred_model"]:
                    agent_configs[agent_name]["preferred_model"] = data["preferred_model"]
                if "fallback_providers" in data and data["fallback_providers"]:
                    agent_configs[agent_name]["fallback_providers"] = data["fallback_providers"]
                if "custom_instructions" in data and data["custom_instructions"]:
                    agent_configs[agent_name]["custom_instructions"] = data["custom_instructions"]
                logger.info(f"Loaded Firestore agent_configurations for agent: {agent_name}")
        except Exception as e:
            logger.warning(f"Could not load Firestore agent_configurations: {e}")

        return agent_configs
    
    async def orchestrate_campaign_creation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate the multi-agent campaign creation process with AI-powered agents"""
        
        workflow_results = {}
        self.workflow_context = request.copy()
        
        # Determine workflow type and agent selection
        workflow_type = request.get("workflow_type", "sequential")
        selected_agents = request.get("agents") or request.get("selected_agents") or []
        sequence = request.get("sequence") or []
        start_agent = request.get("start_agent", "content_strategist")
        max_iterations = request.get("max_iterations", 10)  # Prevent infinite loops
        
        # Coordinated execution: selected agents provided
        if workflow_type == "parallel":
            results = await self._execute_parallel_workflow(request, selected_agents or None)
            return results
        # Explicit fixed sequence takes precedence in sequential mode
        if sequence:
            results = await self._execute_sequence_workflow(request, sequence)
            return results
        if selected_agents and len(selected_agents) > 0:
            # Sequential over provided list
            results = await self._execute_sequence_workflow(request, selected_agents)
            return results
        else:
            # Sequential workflow (default)
            current_agent_name = start_agent
            iterations = 0
            
            while current_agent_name and iterations < max_iterations:
                if current_agent_name not in self.agents:
                    logger.error(f"Agent '{current_agent_name}' not found in configuration.")
                    break
                
                agent = self.agents[current_agent_name]
                logger.info(f"Invoking enhanced agent: {current_agent_name}")
                
                # Pass the current workflow context to the agent
                result = await agent.process_request(self.workflow_context)
                
                # Store the result and update the context
                workflow_results[current_agent_name] = result
                self.workflow_context[current_agent_name] = result
                
                # Determine the next agent based on the result
                if result.get("status") == "success":
                    next_agents = result.get("next_steps", [])
                    current_agent_name = next_agents[0] if next_agents else None
                else:
                    # Handle failure - could retry or skip
                    logger.warning(f"Agent {current_agent_name} failed, checking for alternatives")
                    current_agent_name = None
                
                iterations += 1
            
            return {
                "campaign_creation_complete": True,
                "workflow_type": workflow_type,
                "workflow_results": workflow_results,
                "iterations": iterations,
                "final_recommendations": self._generate_ai_powered_recommendations(workflow_results)
            }
    
    async def _execute_parallel_workflow(self, request: Dict[str, Any], only_agents: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute agents in parallel, optionally restricted to a subset"""
        tasks = []
        
        agent_items = self.agents.items()
        if only_agents:
            agent_items = [(n, a) for n, a in self.agents.items() if n in set(only_agents)]
        for agent_name, agent in agent_items:
            task = asyncio.create_task(agent.process_request(request))
            tasks.append((agent_name, task))
        
        workflow_results = {}
        for agent_name, task in tasks:
            try:
                result = await task
                workflow_results[agent_name] = result
            except Exception as e:
                logger.error(f"Error in parallel execution of {agent_name}: {e}")
                workflow_results[agent_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "campaign_creation_complete": True,
            "workflow_type": "parallel",
            "workflow_results": workflow_results,
            "final_recommendations": self._generate_ai_powered_recommendations(workflow_results)
        }

    async def _execute_sequence_workflow(self, request: Dict[str, Any], agents_list: List[str]) -> Dict[str, Any]:
        """Execute a fixed list of agents sequentially, ignoring next_steps chaining"""
        workflow_results = {}
        self.workflow_context = request.copy()
        iterations = 0
        for name in agents_list:
            if name not in self.agents:
                workflow_results[name] = {
                    "status": "error",
                    "error": "Agent not found"
                }
                continue
            agent = self.agents[name]
            result = await agent.process_request(self.workflow_context)
            workflow_results[name] = result
            self.workflow_context[name] = result
            iterations += 1
            if iterations >= request.get("max_iterations", 50):
                break
        return {
            "campaign_creation_complete": True,
            "workflow_type": "sequential_fixed",
            "workflow_results": workflow_results,
            "iterations": iterations,
            "final_recommendations": self._generate_ai_powered_recommendations(workflow_results)
        }
    
    def _generate_ai_powered_recommendations(self, workflow_results: Dict) -> List[str]:
        """Generate intelligent recommendations based on all agent outputs"""
        recommendations = []
        
        # Analyze agent outputs for common themes
        successful_agents = [
            name for name, result in workflow_results.items() 
            if result.get("status") == "success"
        ]
        
        if len(successful_agents) > 0:
            recommendations.append(f"Successfully executed {len(successful_agents)} agents with AI-powered responses")
        
        # Add specific recommendations based on agent outputs
        if "content_strategist" in successful_agents:
            recommendations.append("Review content strategy for brand alignment")
        
        if "copywriter" in successful_agents:
            recommendations.append("A/B test the generated copy variations")
        
        if "designer" in successful_agents:
            recommendations.append("Ensure visual assets match brand guidelines")
        
        if "compliance_officer" in successful_agents:
            recommendations.append("Compliance check completed - review any flagged items")
        
        recommendations.extend([
            "Monitor initial performance metrics closely",
            "Prepare iteration plan based on early engagement data",
            "Document learnings for future campaign optimization"
        ])
        
        return recommendations
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get the status of all agents and their AI configurations"""
        status = {
            "total_agents": len(self.agents),
            "agents": {}
        }
        
        for name, agent in self.agents.items():
            status["agents"][name] = {
                "name": name,
                "role": agent.role,
                "prompt_configured": bool(agent.prompt_id),
                "prompt_id": agent.prompt_id,
                "preferred_provider": agent.preferred_provider,
                "preferred_model": agent.preferred_model,
                "fallback_providers": agent.fallback_providers
            }
        
        return status

class EnhancedAgentService:
    """Enhanced Agent Service that integrates with AI Models Admin"""
    
    def __init__(self, db: firestore.Client = None, secret_manager = None):
        self.orchestrator = EnhancedMultiAgentOrchestrator(db, secret_manager)
    
    async def invoke_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the enhanced agent orchestrator"""
        try:
            result = await self.orchestrator.orchestrate_campaign_creation(data)
            return {
                "status": "success",
                "result": result,
                "agents_used": list(self.orchestrator.agents.keys()),
                "ai_powered": True
            }
        except Exception as e:
            logger.error(f"Error invoking enhanced agent orchestrator: {e}")
            return {
                "status": "error",
                "message": str(e),
                "ai_powered": True
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the status of the agent system"""
        return await self.orchestrator.get_agent_status()
    
    async def reload_agents(self) -> Dict[str, Any]:
        """Reload agent configurations from files and Firestore"""
        try:
            self.orchestrator._load_agents()
            return {
                "status": "success",
                "message": "Agents reloaded successfully",
                "agent_count": len(self.orchestrator.agents)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

def get_enhanced_agent_service(
    db: firestore.Client = None,
    secret_manager = None
) -> EnhancedAgentService:
    """Factory function to get enhanced agent service instance"""
    if not db:
        db = get_db()
    if not secret_manager:
        secret_manager = get_secret_manager_service()
    return EnhancedAgentService(db, secret_manager)
