"""
Bridge between LangGraph Calendar Workflow and LangChain Multi-Agent System
Enables calendar to use existing agents for enhanced functionality
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add multi-agent path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'multi-agent'))

try:
    # Try direct import first
    from integrations.langchain_core.config import get_config
    from integrations.langchain_core.engine import MultiAgentEngine
    from integrations.langchain_core.vars.registry import VarRegistry
except ImportError:
    # Fallback to multi-agent path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'multi-agent'))
    from integrations.langchain_core.config import get_config
    from integrations.langchain_core.engine import MultiAgentEngine
    from integrations.langchain_core.vars.registry import VarRegistry
from graph.graph import calendar_graph
from main import run_calendar_workflow

logger = logging.getLogger(__name__)


class CalendarLangChainBridge:
    """
    Bridges LangGraph calendar with LangChain agents
    """
    
    def __init__(self):
        self.config = get_config()
        self.engine = MultiAgentEngine(config=self.config)
        self.var_registry = VarRegistry()
        
        # Available agent types for calendar operations
        self.calendar_agents = {
            "copy_smith": "Create compelling email copy",
            "layout_lab": "Design mobile-first layouts",
            "calendar_strategist": "Optimize campaign timing",
            "brand_brain": "Ensure brand consistency",
            "gatekeeper": "Check compliance and regulations",
            "truth_teller": "Analyze performance metrics",
            "audience_architect": "Design segmentation strategies",
            "campaign_planner": "Plan comprehensive campaigns",
            "revenue_analyst": "Analyze revenue metrics"
        }
    
    async def process_with_agent(
        self,
        agent_name: str,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a task using a specific LangChain agent
        
        Args:
            agent_name: Name of the agent to use
            task: Task description
            context: Context including brand, month, etc.
        
        Returns:
            Agent response
        """
        logger.info(f"Processing with agent {agent_name}: {task}")
        
        # Prepare variables for agent
        variables = {
            "brand": context.get("brand", ""),
            "month": context.get("month", ""),
            "campaign_type": context.get("campaign_type", "email"),
            "task": task,
            **self.var_registry.get_all()  # Include all system variables
        }
        
        # Run agent
        try:
            result = await self.engine.run(
                agent_name=agent_name,
                task=task,
                context=variables
            )
            
            logger.info(f"Agent {agent_name} completed successfully")
            return {
                "status": "success",
                "agent": agent_name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            return {
                "status": "error",
                "agent": agent_name,
                "error": str(e)
            }
    
    async def enhance_calendar_workflow(
        self,
        brand: str,
        month: str,
        campaign_goals: List[str] = None,
        use_agents: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run calendar workflow enhanced with LangChain agents
        
        Args:
            brand: Brand name
            month: Target month
            campaign_goals: List of campaign goals
            use_agents: Specific agents to use (or None for auto)
        
        Returns:
            Enhanced workflow results
        """
        logger.info(f"Starting enhanced calendar workflow for {brand} - {month}")
        
        # Run base calendar workflow
        base_result = run_calendar_workflow(brand, month)
        
        # If no specific agents requested, auto-select based on goals
        if not use_agents:
            use_agents = self._select_agents_for_goals(campaign_goals)
        
        # Enhance with agents
        agent_results = []
        context = {
            "brand": brand,
            "month": month,
            "calendar_artifacts": base_result.get("artifacts", []),
            "goals": campaign_goals
        }
        
        for agent_name in use_agents:
            if agent_name in self.calendar_agents:
                task = self._create_agent_task(agent_name, context)
                result = await self.process_with_agent(
                    agent_name,
                    task,
                    context
                )
                agent_results.append(result)
        
        # Combine results
        return {
            "brand": brand,
            "month": month,
            "calendar": base_result,
            "agent_enhancements": agent_results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _select_agents_for_goals(self, goals: List[str]) -> List[str]:
        """
        Auto-select agents based on campaign goals
        """
        if not goals:
            # Default agents for basic calendar
            return ["campaign_planner", "calendar_strategist", "copy_smith"]
        
        selected = []
        
        # Map goals to agents
        for goal in goals:
            goal_lower = goal.lower()
            
            if "revenue" in goal_lower or "sales" in goal_lower:
                selected.append("revenue_analyst")
            
            if "copy" in goal_lower or "content" in goal_lower:
                selected.append("copy_smith")
            
            if "brand" in goal_lower:
                selected.append("brand_brain")
            
            if "compliance" in goal_lower or "legal" in goal_lower:
                selected.append("gatekeeper")
            
            if "segment" in goal_lower or "audience" in goal_lower:
                selected.append("audience_architect")
            
            if "performance" in goal_lower or "metrics" in goal_lower:
                selected.append("truth_teller")
        
        # Always include campaign planner
        if "campaign_planner" not in selected:
            selected.insert(0, "campaign_planner")
        
        return selected
    
    def _create_agent_task(self, agent_name: str, context: Dict[str, Any]) -> str:
        """
        Create appropriate task for each agent type
        """
        brand = context.get("brand", "the brand")
        month = context.get("month", "the target month")
        
        tasks = {
            "copy_smith": f"Create compelling email copy for {brand}'s {month} campaigns. Focus on engagement and conversion.",
            "layout_lab": f"Design mobile-first email layouts for {brand}'s {month} campaigns. Ensure responsive design.",
            "calendar_strategist": f"Optimize send times and frequency for {brand}'s {month} campaign calendar.",
            "brand_brain": f"Review {brand}'s {month} campaign plan for brand consistency and voice alignment.",
            "gatekeeper": f"Check {brand}'s {month} campaigns for compliance with email regulations and best practices.",
            "truth_teller": f"Analyze expected performance metrics for {brand}'s {month} campaign strategy.",
            "audience_architect": f"Design segmentation strategy for {brand}'s {month} campaigns to maximize relevance.",
            "campaign_planner": f"Create comprehensive campaign plan for {brand} in {month} with clear objectives.",
            "revenue_analyst": f"Project revenue impact of {brand}'s {month} campaign calendar."
        }
        
        return tasks.get(agent_name, f"Process {brand}'s {month} campaign with {agent_name}")


# Quick test function
async def test_bridge():
    """Test the calendar-langchain bridge"""
    bridge = CalendarLangChainBridge()
    
    # Test single agent
    result = await bridge.process_with_agent(
        "campaign_planner",
        "Create a March 2025 campaign plan for TestBrand",
        {"brand": "TestBrand", "month": "March 2025"}
    )
    print(f"Agent result: {result}")
    
    # Test enhanced workflow
    enhanced = await bridge.enhance_calendar_workflow(
        brand="TestBrand",
        month="March 2025",
        campaign_goals=["Increase revenue", "Improve brand awareness"],
        use_agents=["campaign_planner", "revenue_analyst", "copy_smith"]
    )
    print(f"Enhanced workflow: {enhanced}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_bridge())