"""
Universal MCP Registry

Central registry for all MCP tools with automatic AI enhancement.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
from google.cloud import firestore
from .wrapper_generator import AIWrapperGenerator
from .agent_factory import MCPAgentFactory
from ..llm_selector import LLMSelector

logger = logging.getLogger(__name__)


class UniversalMCPRegistry:
    """
    Registry for ALL MCP tools with automatic AI enhancement
    """
    
    def __init__(self, db: firestore.Client):
        self.db = db
        self.registered_mcps: Dict[str, Any] = {}
        self.llm_selector = LLMSelector()
        self.wrapper_generator = AIWrapperGenerator(self.llm_selector)
        self.agent_factory = MCPAgentFactory(self.llm_selector)
        self._mcps_loaded = False
    
    async def _ensure_mcps_loaded(self):
        """Load MCPs from Firestore if not already loaded (lazy loading)"""
        if self._mcps_loaded:
            return
        
        try:
            # Use get() instead of stream() to avoid blocking
            mcp_docs = self.db.collection('mcp_registry').get()
            for doc in mcp_docs:
                if doc.exists:
                    mcp_data = doc.to_dict()
                    self.registered_mcps[doc.id] = mcp_data
                    logger.info(f"Loaded MCP: {doc.id}")
            self._mcps_loaded = True
        except Exception as e:
            logger.warning(f"Could not load existing MCPs: {e}")
            self._mcps_loaded = True  # Mark as loaded even on error to prevent retries
    
    async def register_new_mcp(self, mcp_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register any new MCP tool with automatic AI wrapper generation
        
        Args:
            mcp_config: Configuration for the new MCP tool
            
        Returns:
            Registration result with endpoints and agent info
        """
        try:
            mcp_id = mcp_config.get('id') or self._generate_mcp_id(mcp_config['name'])
            
            logger.info(f"Registering new MCP: {mcp_id}")
            
            # 1. Create tool registry entry
            tool_registry = await self._create_tool_registry(mcp_id, mcp_config)
            
            # 2. Generate AI wrapper
            wrapper = await self.wrapper_generator.generate_wrapper(mcp_config)
            
            # 3. Create LangChain agent
            agent = await self.agent_factory.create_agent(mcp_config)
            
            # 4. Store in Firestore
            registration_data = {
                'id': mcp_id,
                'name': mcp_config['name'],
                'description': mcp_config.get('description', ''),
                'base_url': mcp_config.get('base_url', ''),
                'auth_type': mcp_config.get('auth_type', 'api_key'),
                'config': mcp_config,
                'tool_registry': tool_registry,
                'wrapper': {
                    'endpoint': f'/api/mcp/{mcp_id}/invoke',
                    'class_name': wrapper.__class__.__name__,
                    'llm_model': wrapper.llm_model,
                    'learning_enabled': True
                },
                'agent': {
                    'name': agent.name,
                    'description': agent.description,
                    'llm_model': agent.llm_model  # Fixed: MCPAgent has llm_model, not llm
                },
                'created_at': datetime.now(),
                'status': 'active',
                'metrics': {
                    'total_queries': 0,
                    'success_rate': 0.0,
                    'avg_response_time': 0,
                    'patterns_learned': 0
                }
            }
            
            await self.db.collection('mcp_registry').document(mcp_id).set(registration_data)
            
            # 5. Cache locally
            self.registered_mcps[mcp_id] = registration_data
            
            logger.info(f"Successfully registered MCP: {mcp_id}")
            
            return {
                'mcp_id': mcp_id,
                'name': mcp_config['name'],
                'wrapper_endpoint': f'/api/mcp/{mcp_id}/invoke',
                'agent_name': agent.name,
                'status': 'active',
                'message': f'MCP {mcp_id} registered successfully with AI capabilities'
            }
            
        except Exception as e:
            logger.error(f"Failed to register MCP: {e}")
            raise
    
    async def _create_tool_registry(self, mcp_id: str, mcp_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create tool registry for the MCP with discovered endpoints
        """
        tools = {}
        
        # If endpoints are provided, use them
        if 'endpoints' in mcp_config:
            for endpoint in mcp_config['endpoints']:
                tool_id = self._generate_tool_id(endpoint['name'])
                tools[tool_id] = {
                    'name': endpoint['name'],
                    'description': endpoint.get('description', ''),
                    'endpoint': endpoint['path'],
                    'method': endpoint.get('method', 'GET'),
                    'parameters': endpoint.get('parameters', {}),
                    'intents': [],  # Will be learned
                    'success_rate': 0.0,
                    'patterns_learned': []
                }
        else:
            # Start with generic tools that will be discovered
            tools = {
                'list': {
                    'name': f'{mcp_id}.list',
                    'description': f'List items from {mcp_id}',
                    'endpoint': '/',
                    'method': 'GET',
                    'intents': ['list', 'get all', 'show'],
                    'success_rate': 0.0
                },
                'get': {
                    'name': f'{mcp_id}.get',
                    'description': f'Get specific item from {mcp_id}',
                    'endpoint': '/{id}',
                    'method': 'GET',
                    'intents': ['get', 'show', 'find'],
                    'success_rate': 0.0
                }
            }
        
        # Store tools in separate collection for querying
        for tool_id, tool_data in tools.items():
            await self.db.collection('mcp_tools').document(f'{mcp_id}_{tool_id}').set({
                'mcp_id': mcp_id,
                'tool_id': tool_id,
                **tool_data,
                'created_at': datetime.now()
            })
        
        return tools
    
    async def get_mcp(self, mcp_id: str) -> Optional[Dict[str, Any]]:
        """Get MCP configuration and status"""
        # Ensure MCPs are loaded
        await self._ensure_mcps_loaded()
        
        if mcp_id in self.registered_mcps:
            return self.registered_mcps[mcp_id]
        
        doc = await self.db.collection('mcp_registry').document(mcp_id).get()
        if doc.exists:
            return doc.to_dict()
        
        return None
    
    async def list_mcps(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered MCPs"""
        # Ensure MCPs are loaded
        await self._ensure_mcps_loaded()
        
        mcps = []
        
        query = self.db.collection('mcp_registry')
        if status:
            query = query.where('status', '==', status)
        
        docs = query.get()
        for doc in docs:
            mcps.append(doc.to_dict())
        
        return mcps
    
    async def update_mcp_metrics(self, mcp_id: str, metrics: Dict[str, Any]):
        """Update MCP performance metrics"""
        await self.db.collection('mcp_registry').document(mcp_id).update({
            f'metrics.{k}': v for k, v in metrics.items()
        })
    
    async def deactivate_mcp(self, mcp_id: str):
        """Deactivate an MCP"""
        await self.db.collection('mcp_registry').document(mcp_id).update({
            'status': 'inactive',
            'deactivated_at': datetime.now()
        })
        
        if mcp_id in self.registered_mcps:
            self.registered_mcps[mcp_id]['status'] = 'inactive'
    
    async def get_mcp_tools(self, mcp_id: str) -> List[Dict[str, Any]]:
        """Get all tools for an MCP"""
        tools = []
        tool_docs = self.db.collection('mcp_tools').where('mcp_id', '==', mcp_id).get()
        
        for doc in tool_docs:
            tools.append(doc.to_dict())
        
        return tools
    
    async def update_tool_learning(self, mcp_id: str, tool_id: str, pattern: Dict[str, Any]):
        """Update learned patterns for a tool"""
        doc_id = f'{mcp_id}_{tool_id}'
        tool_ref = self.db.collection('mcp_tools').document(doc_id)
        
        # Add to patterns_learned array
        tool_ref.update({
            'patterns_learned': firestore.ArrayUnion([pattern]),
            'last_updated': datetime.now()
        })
    
    def _generate_mcp_id(self, name: str) -> str:
        """Generate a valid MCP ID from name"""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    def _generate_tool_id(self, name: str) -> str:
        """Generate a valid tool ID from name"""
        return name.lower().replace(' ', '_').replace('.', '_')