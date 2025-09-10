"""
MCP Agent Factory

Factory for creating LangChain agents for any MCP tool.
"""
from typing import Dict, Any, List, Optional, Type
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPAgent:
    """Base class for MCP agents"""
    
    def __init__(self, name: str, description: str, system_prompt: str, llm_model: str):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.llm_model = llm_model
        self.tools = []
        self.examples = []
    
    async def process(self, input_text: str) -> str:
        """Process input using the agent"""
        # This would integrate with actual LangChain in production
        return f"Processed by {self.name}: {input_text}"
    
    def add_tool(self, tool):
        """Add a tool to the agent"""
        self.tools.append(tool)
    
    def update_prompt(self, new_prompt: str):
        """Update the system prompt"""
        self.system_prompt = new_prompt


class MCPAgentFactory:
    """
    Factory for creating LangChain agents for any MCP tool
    """
    
    def __init__(self, llm_selector):
        self.llm_selector = llm_selector
        self.created_agents = {}
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load prompt templates for different MCP types"""
        return {
            'default': """You are an intelligent assistant for {mcp_name}.

Your capabilities include:
{capabilities}

You can help users by:
1. Understanding natural language queries about {service_type}
2. Finding the right API endpoints to answer questions
3. Handling errors gracefully and retrying with alternatives
4. Learning from successful interactions

Always aim to provide accurate, helpful responses based on the data available.""",
            
            'marketing': """You are a marketing data specialist for {mcp_name}.

You excel at:
- Analyzing campaign performance metrics
- Segmenting audiences effectively  
- Tracking customer engagement
- Providing actionable insights

{capabilities}

Help users understand their marketing data and make data-driven decisions.""",
            
            'financial': """You are a financial data analyst for {mcp_name}.

You specialize in:
- Processing transaction data
- Generating financial reports
- Tracking revenue and expenses
- Ensuring data accuracy

{capabilities}

Provide precise financial insights while maintaining data security.""",
            
            'ecommerce': """You are an e-commerce assistant for {mcp_name}.

You help with:
- Product catalog management
- Order processing and tracking
- Inventory management
- Customer data analysis

{capabilities}

Support users in managing their online store effectively."""
        }
    
    async def create_agent(self, mcp_config: Dict[str, Any]) -> MCPAgent:
        """
        Create a LangChain agent for any MCP
        
        Args:
            mcp_config: Configuration for the MCP
            
        Returns:
            Created agent instance
        """
        try:
            mcp_id = mcp_config.get('id') or self._generate_id(mcp_config['name'])
            
            logger.info(f"Creating agent for MCP: {mcp_id}")
            
            # 1. Select appropriate LLM
            llm_model = self.llm_selector.select_for_mcp(mcp_id)
            
            # 2. Generate system prompt
            system_prompt = self._generate_system_prompt(mcp_config)
            
            # 3. Create agent
            agent = self._create_agent_class(
                mcp_id=mcp_id,
                mcp_config=mcp_config,
                system_prompt=system_prompt,
                llm_model=llm_model
            )
            
            # 4. Add tools
            tools = self._create_tools(mcp_config)
            for tool in tools:
                agent.add_tool(tool)
            
            # 5. Cache agent
            self.created_agents[mcp_id] = agent
            
            logger.info(f"Successfully created agent {agent.name} using {llm_model}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    def _generate_system_prompt(self, mcp_config: Dict[str, Any]) -> str:
        """Generate system prompt for the agent"""
        
        # Determine service type
        service_type = mcp_config.get('service_type', 'general')
        
        # Select appropriate template
        template_key = 'default'
        if service_type in ['marketing', 'email', 'customer_engagement']:
            template_key = 'marketing'
        elif service_type in ['payments', 'billing', 'financial']:
            template_key = 'financial'
        elif service_type in ['ecommerce', 'store', 'catalog']:
            template_key = 'ecommerce'
        
        template = self.prompt_templates[template_key]
        
        # Generate capabilities list
        capabilities = self._generate_capabilities_text(mcp_config)
        
        # Format prompt
        prompt = template.format(
            mcp_name=mcp_config.get('name', 'Unknown MCP'),
            service_type=service_type,
            capabilities=capabilities
        )
        
        # Add examples if provided
        if 'example_queries' in mcp_config:
            prompt += "\n\nExample queries you can handle:\n"
            for example in mcp_config['example_queries']:
                prompt += f"- {example}\n"
        
        return prompt
    
    def _generate_capabilities_text(self, mcp_config: Dict[str, Any]) -> str:
        """Generate text describing MCP capabilities"""
        capabilities = []
        
        if 'endpoints' in mcp_config:
            for endpoint in mcp_config['endpoints']:
                capabilities.append(f"- {endpoint.get('description', endpoint['name'])}")
        else:
            # Default capabilities
            capabilities = [
                "- List and retrieve data",
                "- Create and update records",
                "- Generate reports and analytics",
                "- Search and filter information"
            ]
        
        return "\n".join(capabilities)
    
    def _create_agent_class(self, mcp_id: str, mcp_config: Dict[str, Any],
                           system_prompt: str, llm_model: str) -> MCPAgent:
        """Create agent class for the MCP"""
        
        # Create agent instance
        agent_name = f"{mcp_id}_agent"
        agent_description = f"Intelligent agent for {mcp_config.get('name', mcp_id)}"
        
        agent = MCPAgent(
            name=agent_name,
            description=agent_description,
            system_prompt=system_prompt,
            llm_model=llm_model
        )
        
        # Add example queries if provided
        if 'example_queries' in mcp_config:
            agent.examples = mcp_config['example_queries']
        
        return agent
    
    def _create_tools(self, mcp_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create tools for the agent"""
        tools = []
        
        # Create a query tool
        tools.append({
            'name': f"{mcp_config.get('id', 'mcp')}_query",
            'description': f"Query {mcp_config.get('name', 'MCP')} using natural language",
            'parameters': {
                'query': {'type': 'string', 'description': 'Natural language query'},
                'context': {'type': 'object', 'description': 'Optional context'}
            }
        })
        
        # Create specific tools for each endpoint
        if 'endpoints' in mcp_config:
            for endpoint in mcp_config['endpoints']:
                tools.append({
                    'name': endpoint['name'],
                    'description': endpoint.get('description', f"Call {endpoint['name']}"),
                    'parameters': endpoint.get('parameters', {})
                })
        
        return tools
    
    async def get_agent(self, mcp_id: str) -> Optional[MCPAgent]:
        """Get an existing agent"""
        return self.created_agents.get(mcp_id)
    
    async def update_agent_prompt(self, mcp_id: str, new_prompt: str):
        """Update an agent's system prompt"""
        agent = self.created_agents.get(mcp_id)
        if agent:
            agent.update_prompt(new_prompt)
            logger.info(f"Updated prompt for agent {mcp_id}")
        else:
            logger.warning(f"Agent {mcp_id} not found")
    
    async def list_agents(self) -> List[Dict[str, str]]:
        """List all created agents"""
        return [
            {
                'id': agent_id,
                'name': agent.name,
                'description': agent.description,
                'llm_model': agent.llm_model
            }
            for agent_id, agent in self.created_agents.items()
        ]
    
    def _generate_id(self, name: str) -> str:
        """Generate valid ID from name"""
        return name.lower().replace(' ', '_').replace('-', '_')