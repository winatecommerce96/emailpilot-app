"""
AI Wrapper Generator

Automatically generates intelligent wrappers for any MCP tool.
"""
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPWrapper:
    """Base class for generated MCP wrappers"""
    
    def __init__(self, mcp_id: str, config: Dict[str, Any], llm_selector):
        self.mcp_id = mcp_id
        self.config = config
        self.llm_selector = llm_selector
        self.llm_model = None
        self.base_url = config.get('base_url', '')
        self.auth_type = config.get('auth_type', 'api_key')
        self.learning_enabled = True
        self.cache = {}
    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process natural language query"""
        raise NotImplementedError
    
    async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke specific tool"""
        raise NotImplementedError


class AIWrapperGenerator:
    """
    Automatically generates AI wrappers for any MCP tool
    """
    
    def __init__(self, llm_selector):
        self.llm_selector = llm_selector
        self.generated_wrappers = {}
    
    async def generate_wrapper(self, mcp_config: Dict[str, Any]) -> MCPWrapper:
        """
        Generate a complete AI wrapper for any MCP
        
        Args:
            mcp_config: Configuration for the MCP
            
        Returns:
            Generated wrapper instance
        """
        try:
            mcp_id = mcp_config.get('id') or self._generate_id(mcp_config['name'])
            
            logger.info(f"Generating AI wrapper for {mcp_id}")
            
            # 1. Select appropriate LLM for this MCP
            llm_model = self.llm_selector.select_for_mcp(mcp_id)
            
            # 2. Analyze MCP structure
            structure = await self._analyze_mcp_structure(mcp_config)
            
            # 3. Create wrapper class dynamically
            wrapper_class = self._create_wrapper_class(mcp_id, mcp_config, structure)
            
            # 4. Instantiate wrapper
            wrapper = wrapper_class(mcp_id, mcp_config, self.llm_selector)
            wrapper.llm_model = llm_model
            
            # 5. Cache wrapper
            self.generated_wrappers[mcp_id] = wrapper
            
            logger.info(f"Successfully generated wrapper for {mcp_id} using {llm_model}")
            
            return wrapper
            
        except Exception as e:
            logger.error(f"Failed to generate wrapper: {e}")
            raise
    
    async def _analyze_mcp_structure(self, mcp_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the MCP structure to understand its capabilities
        """
        structure = {
            'endpoints': [],
            'auth_method': mcp_config.get('auth_type', 'api_key'),
            'base_url': mcp_config.get('base_url', ''),
            'discovered_patterns': [],
            'parameter_types': {}
        }
        
        # If endpoints are provided, analyze them
        if 'endpoints' in mcp_config:
            for endpoint in mcp_config['endpoints']:
                structure['endpoints'].append({
                    'name': endpoint['name'],
                    'path': endpoint['path'],
                    'method': endpoint.get('method', 'GET'),
                    'parameters': endpoint.get('parameters', {}),
                    'description': endpoint.get('description', '')
                })
        
        # Use LLM to suggest additional endpoints based on service type
        if mcp_config.get('service_type'):
            llm = self.llm_selector.select_for_task('discovery')
            # In a real implementation, would call LLM here
            # suggestions = await llm.suggest_endpoints(mcp_config['service_type'])
            
        return structure
    
    def _create_wrapper_class(self, mcp_id: str, mcp_config: Dict[str, Any], 
                             structure: Dict[str, Any]) -> type:
        """
        Create a wrapper class dynamically for the MCP
        """
        
        async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
            """Process natural language query with AI"""
            try:
                # 1. Analyze query intent
                intent = await self._analyze_query_intent(query)
                
                # 2. Find matching tools
                tools = await self._find_matching_tools(intent)
                
                # 3. Execute with retry logic
                for tool in tools:
                    try:
                        result = await self.invoke_tool(tool['name'], tool['params'])
                        if result.get('success'):
                            # Learn from success
                            await self._record_success(query, tool, result)
                            return result
                    except Exception as e:
                        logger.warning(f"Tool {tool['name']} failed: {e}")
                        continue
                
                # 4. Try discovery if all tools fail
                return await self._discover_new_approach(query, context)
                
            except Exception as e:
                logger.error(f"Query processing failed: {e}")
                return {'success': False, 'error': str(e)}
        
        async def invoke_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Invoke specific tool with the MCP"""
            import httpx
            
            try:
                # Find tool endpoint
                endpoint = None
                for ep in structure['endpoints']:
                    if ep['name'] == tool_name:
                        endpoint = ep
                        break
                
                if not endpoint:
                    # Try to discover endpoint
                    endpoint = await self._discover_endpoint(tool_name)
                
                if not endpoint:
                    return {'success': False, 'error': f'Tool {tool_name} not found'}
                
                # Make API call
                url = f"{self.base_url}{endpoint['path']}"
                
                # Add authentication
                headers = {}
                if self.auth_type == 'api_key':
                    headers['Authorization'] = f"Bearer {params.get('api_key', '')}"
                
                async with httpx.AsyncClient() as client:
                    if endpoint['method'] == 'GET':
                        response = await client.get(url, headers=headers, params=params)
                    else:
                        response = await client.post(url, headers=headers, json=params)
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'data': response.json(),
                        'tool': tool_name
                    }
                else:
                    return {
                        'success': False,
                        'error': f"API returned {response.status_code}",
                        'details': response.text
                    }
                    
            except Exception as e:
                logger.error(f"Tool invocation failed: {e}")
                return {'success': False, 'error': str(e)}
        
        async def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
            """Analyze query intent using AI"""
            # Simplified - would use actual LLM in production
            intent = {
                'action': 'unknown',
                'entities': [],
                'parameters': {}
            }
            
            # Basic pattern matching
            lower_query = query.lower()
            if 'list' in lower_query or 'get all' in lower_query:
                intent['action'] = 'list'
            elif 'get' in lower_query or 'show' in lower_query:
                intent['action'] = 'get'
            elif 'create' in lower_query or 'add' in lower_query:
                intent['action'] = 'create'
            
            return intent
        
        async def _find_matching_tools(self, intent: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Find tools matching the intent"""
            tools = []
            
            for endpoint in structure['endpoints']:
                # Match based on action
                if intent['action'] in endpoint['name'].lower():
                    tools.append({
                        'name': endpoint['name'],
                        'params': self._map_intent_to_params(intent, endpoint)
                    })
            
            return tools
        
        def _map_intent_to_params(self, intent: Dict[str, Any], endpoint: Dict[str, Any]) -> Dict[str, Any]:
            """Map intent to endpoint parameters"""
            params = {}
            
            # Map from intent parameters to endpoint parameters
            for param_name, param_config in endpoint.get('parameters', {}).items():
                if param_name in intent.get('parameters', {}):
                    params[param_name] = intent['parameters'][param_name]
                elif param_config.get('required'):
                    # Try to infer required parameter
                    params[param_name] = None  # Would use AI to infer
            
            return params
        
        async def _discover_endpoint(self, tool_name: str) -> Optional[Dict[str, Any]]:
            """Try to discover endpoint for tool"""
            # Would use AI to suggest endpoint based on tool name
            return None
        
        async def _discover_new_approach(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
            """Discover new approach when standard tools fail"""
            return {
                'success': False,
                'error': 'Could not find suitable approach',
                'suggestion': 'Try rephrasing the query'
            }
        
        async def _record_success(self, query: str, tool: Dict[str, Any], result: Dict[str, Any]):
            """Record successful pattern for learning"""
            # Would store in Firebase for learning
            pass
        
        # Create the wrapper class dynamically
        wrapper_class = type(
            f'{mcp_id.title()}Wrapper',
            (MCPWrapper,),
            {
                'process_query': process_query,
                'invoke_tool': invoke_tool,
                '_analyze_query_intent': _analyze_query_intent,
                '_find_matching_tools': _find_matching_tools,
                '_map_intent_to_params': _map_intent_to_params,
                '_discover_endpoint': _discover_endpoint,
                '_discover_new_approach': _discover_new_approach,
                '_record_success': _record_success
            }
        )
        
        return wrapper_class
    
    def _generate_id(self, name: str) -> str:
        """Generate valid ID from name"""
        return name.lower().replace(' ', '_').replace('-', '_')