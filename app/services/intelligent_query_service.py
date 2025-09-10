"""
Intelligent Query Service for Natural Language Klaviyo Data Retrieval

This service provides intelligent parsing of natural language queries to fetch Klaviyo data,
with fallback to direct MCP tool invocation for reliability.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import httpx
from enum import Enum

logger = logging.getLogger(__name__)


class QueryMode(Enum):
    """Query execution modes"""
    INTELLIGENT = "intelligent"
    DIRECT = "direct"
    AUTO = "auto"


class QueryStrategy:
    """Represents a single query strategy"""
    def __init__(self, tool: str, params: Dict[str, Any], description: str, 
                 fallback_tool: Optional[str] = None, fallback_params: Optional[Dict] = None):
        self.tool = tool
        self.params = params or {}
        self.description = description
        self.fallback_tool = fallback_tool or tool
        self.fallback_params = fallback_params or params
        self.process_next = None  # Optional function to process results and generate follow-up queries


class IntelligentQueryService:
    """
    Service for intelligent natural language query processing with fallback to direct MCP calls
    """
    
    def __init__(self, mcp_gateway_url: str = "http://localhost:8000/api/mcp/gateway", db = None):
        """
        Initialize the service
        
        Args:
            mcp_gateway_url: URL of the MCP gateway service
            db: Firestore database client for looking up client-specific data
        """
        self.mcp_gateway_url = mcp_gateway_url
        self.db = db
        self.strategy_builder = QueryStrategyBuilder()
        self.executor = QueryExecutor(mcp_gateway_url)
    
    async def query(self, natural_query: str, client_id: str, 
                   mode: QueryMode = QueryMode.AUTO,
                   fallback_tool: Optional[str] = None,
                   fallback_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Query Klaviyo with intelligent parsing or direct tool call
        
        Args:
            natural_query: Natural language query or direct tool name
            client_id: Client identifier
            mode: Query execution mode (intelligent, direct, or auto)
            fallback_tool: Tool to use if intelligent mode fails
            fallback_params: Parameters for fallback tool
            
        Returns:
            Query results with metadata
        """
        # Enrich context with client-specific data (e.g., revenue metric ID)
        context = await self._get_client_context(client_id)
        
        if mode == QueryMode.DIRECT:
            # Direct MCP call
            return await self.direct_mcp_call(natural_query, client_id, fallback_params)
        
        if mode == QueryMode.INTELLIGENT:
            # Intelligent parsing only
            strategies = self.strategy_builder.build(natural_query, context)
            return await self.executor.execute_with_retry(strategies, client_id)
        
        # AUTO mode - try intelligent first, then fallback
        try:
            strategies = self.strategy_builder.build(natural_query, context)
            logger.info(f"🏗️ Built {len(strategies)} strategies for query: '{natural_query}'")
            for i, strategy in enumerate(strategies):
                logger.info(f"🏗️ Strategy {i+1}: {strategy.description} (tool: {strategy.tool}, params: {strategy.params})")
            
            result = await self.executor.execute_with_retry(strategies, client_id)
            
            if result.get('success'):
                return result
            else:
                raise Exception("No useful results from intelligent query")
                
        except Exception as e:
            logger.warning(f"Intelligent query failed: {e}, falling back to direct mode")
            
            # Try fallback if provided
            if fallback_tool:
                return await self.direct_mcp_call(fallback_tool, client_id, fallback_params)
            
            # Try to guess a direct tool from the query
            guessed_tool = self.strategy_builder.guess_direct_tool(natural_query)
            if guessed_tool:
                return await self.direct_mcp_call(
                    guessed_tool['tool'], 
                    client_id, 
                    guessed_tool.get('params', {})
                )
            
            return {
                'success': False,
                'error': 'Failed to process query in both intelligent and direct modes',
                'original_error': str(e)
            }
    
    async def direct_mcp_call(self, tool_name: str, client_id: str, 
                             params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Direct MCP tool invocation (original method)
        
        Args:
            tool_name: Name of the MCP tool
            client_id: Client identifier
            params: Tool parameters
            
        Returns:
            Tool execution results
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_gateway_url}/tool/{tool_name}",
                    json={
                        "tool": tool_name,
                        "client_id": client_id,
                        "params": params or {}
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Check if the MCP gateway returned success
                    if result.get('success'):
                        return {
                            'success': True,
                            'data': result.get('data'),
                            'tool': tool_name,
                            'mode': 'direct'
                        }
                    else:
                        return {
                            'success': False,
                            'error': result.get('error', 'Unknown MCP error'),
                            'details': result,
                            'tool': tool_name,
                            'mode': 'direct'
                        }
                else:
                    return {
                        'success': False,
                        'error': f"MCP call failed with status {response.status_code}",
                        'details': response.text,
                        'tool': tool_name,
                        'mode': 'direct'
                    }
                    
        except Exception as e:
            logger.error(f"Direct MCP call failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'tool': tool_name,
                'mode': 'direct'
            }
    
    async def _get_client_context(self, client_id: str) -> Dict[str, Any]:
        """
        Get client-specific context from Firestore
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client context including revenue metric ID
        """
        context = {'client_id': client_id}
        
        if self.db:
            try:
                # Look up client's placed_order_metric_id from Firestore
                from google.cloud import firestore
                if isinstance(self.db, firestore.Client):
                    client_ref = self.db.collection('clients').document(client_id)
                    client_doc = client_ref.get()
                    
                    if client_doc.exists:
                        client_data = client_doc.to_dict()
                        context['revenue_metric_id'] = client_data.get('placed_order_metric_id')
                        context['client_name'] = client_data.get('name')
                        context['klaviyo_account_id'] = client_data.get('klaviyo_account_id')
                        logger.info(f"Found revenue metric ID for {client_id}: {context.get('revenue_metric_id')}")
            except Exception as e:
                logger.warning(f"Failed to get client context: {e}")
        
        return context


class QueryStrategyBuilder:
    """Builds query strategies from natural language"""
    
    # Complete mapping of all 48 Klaviyo MCP Enhanced tools
    TOOL_MAPPINGS = {
        # Campaigns (5 tools)
        'campaigns.list': ['campaigns', 'campaign list', 'all campaigns', 'show campaigns'],
        'campaigns.get': ['campaign details', 'specific campaign', 'campaign info'],
        'campaigns.get_message': ['campaign message', 'email content', 'campaign template'],
        'campaigns.get_messages': ['campaign messages', 'all messages', 'campaign emails'],
        'campaigns.get_recipient_estimation': ['recipient count', 'audience size', 'campaign reach'],
        
        # Profiles (5 tools)
        'profiles.list': ['profiles', 'customers', 'subscribers', 'contacts', 'people'],
        'profiles.get': ['profile details', 'customer info', 'subscriber details'],
        'profiles.create': ['create profile', 'add customer', 'new subscriber'],
        'profiles.update': ['update profile', 'edit customer', 'modify subscriber'],
        'profiles.delete': ['delete profile', 'remove customer', 'delete subscriber'],
        
        # Lists (4 tools)
        'lists.list': ['lists', 'mailing lists', 'all lists'],
        'lists.get': ['list details', 'list info', 'specific list'],
        'lists.create': ['create list', 'new list', 'add list'],
        'lists.add_profiles': ['add to list', 'subscribe to list', 'add profiles'],
        
        # Segments (2 tools)
        'segments.list': ['segments', 'audiences', 'groups', 'all segments'],
        'segments.get': ['segment details', 'audience info', 'segment info'],
        
        # Events (2 tools)
        'events.list': ['events', 'activities', 'customer actions'],
        'events.create': ['track event', 'create event', 'log activity'],
        
        # Metrics (2 tools)
        'metrics.list': ['metrics', 'all metrics', 'metric types'],
        'metrics.get': ['metric details', 'metric info', 'specific metric'],
        
        # Reporting/Analytics (3 tools)
        'campaigns.get_metrics': ['campaign performance', 'campaign metrics', 'campaign stats'],
        'metrics.aggregate': ['aggregate metrics', 'metric totals', 'analytics', 'revenue', 'sales'],
        'metrics.timeline': ['metric timeline', 'metric history', 'performance over time'],
        
        # Flows (3 tools)
        'flows.list': ['flows', 'automations', 'workflows'],
        'flows.get': ['flow details', 'automation info', 'workflow details'],
        'flows.update_status': ['activate flow', 'deactivate flow', 'flow status'],
        
        # Templates (3 tools)
        'templates.list': ['templates', 'email templates', 'all templates'],
        'templates.get': ['template details', 'template info'],
        'templates.create': ['create template', 'new template'],
        
        # Catalogs (3 tools)
        'catalogs.list': ['catalogs', 'product catalogs'],
        'catalogs.get_items': ['catalog items', 'products', 'catalog products'],
        'catalogs.get_item': ['product details', 'item info'],
        
        # Tags (3 tools)
        'tags.list': ['tags', 'all tags', 'labels'],
        'tags.create': ['create tag', 'new tag', 'add tag'],
        'tags.add_to_resource': ['tag resource', 'apply tag', 'add tag to'],
        
        # Webhooks (3 tools)
        'webhooks.list': ['webhooks', 'all webhooks'],
        'webhooks.create': ['create webhook', 'new webhook'],
        'webhooks.delete': ['delete webhook', 'remove webhook'],
        
        # Coupons (2 tools)
        'coupons.list': ['coupons', 'discount codes', 'promotions'],
        'coupons.create_code': ['create coupon', 'new discount', 'generate code'],
        
        # Forms (2 tools)
        'forms.list': ['forms', 'signup forms', 'all forms'],
        'forms.get': ['form details', 'form info'],
        
        # Reviews (2 tools)
        'reviews.list': ['reviews', 'product reviews'],
        'reviews.get': ['review details', 'review info'],
        
        # Images (2 tools)
        'images.list': ['images', 'all images', 'media'],
        'images.get': ['image details', 'image info'],
        
        # Data Privacy (1 tool)
        'data_privacy.request_deletion': ['delete data', 'privacy request', 'GDPR deletion']
    }
    
    def build(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """
        Parse natural language query and build execution strategies
        Enhanced to handle complex, multi-part queries including multi-line requests
        
        Args:
            query: Natural language query (can be multi-line)
            context: Client context including revenue_metric_id
            
        Returns:
            List of query strategies to try
        """
        lower_query = query.lower()
        strategies = []
        
        # Split query into separate requests if it contains line breaks or sentence endings
        query_parts = []
        if '\n' in query:
            # Multi-line query - treat each line as a separate request
            query_parts = [line.strip() for line in query.split('\n') if line.strip()]
        elif '. ' in query:
            # Multiple sentences - treat each as a separate request
            query_parts = [sent.strip() for sent in query.split('. ') if sent.strip()]
        else:
            query_parts = [query]
        
        # Process each part of the query
        for part in query_parts:
            lower_part = part.lower()
            
            # Check for time ranges in this part
            time_range = self._extract_time_range(lower_part)
            
            # Check query characteristics
            is_compound = any(word in lower_part for word in [' and ', ' also ', ' plus ', ' with ', ' as well as '])
            is_comparative = any(word in lower_part for word in ['compare', 'versus', 'vs', 'better', 'worse'])
            is_analytical = any(phrase in lower_part for phrase in [
                'analyze', 'analysis', 'breakdown', 'insights', 'trends', 'patterns'
            ])
            
            # Parse this part of the query and add strategies
            strategies.extend(self._build_strategies_for_part(lower_part, context, time_range))
        
        # Remove duplicate strategies
        seen = set()
        unique_strategies = []
        for strategy in strategies:
            key = (strategy.tool, str(strategy.params))
            if key not in seen:
                seen.add(key)
                unique_strategies.append(strategy)
        
        # Log what strategies we're building for debugging
        logger.info(f"🎯 Query interpretation for '{query[:100]}...':")
        logger.info(f"  - Query parts: {len(query_parts)}")
        logger.info(f"  - Total strategies: {len(unique_strategies)}")
        
        return unique_strategies
    
    def _extract_time_range(self, query: str) -> Dict[str, Any]:
        """Extract time range from query text"""
        import re
        from datetime import datetime, timedelta
        
        time_range = {}
        
        # Check for specific day counts
        day_match = re.search(r'last (\d+) days?', query)
        if day_match:
            days = int(day_match.group(1))
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            time_range = {
                'days': days,
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        elif 'last month' in query or 'past month' in query:
            time_range = {
                'days': 30,
                'start': (datetime.now() - timedelta(days=30)).isoformat(),
                'end': datetime.now().isoformat()
            }
        elif 'last year' in query or 'past year' in query:
            time_range = {
                'days': 365,
                'start': (datetime.now() - timedelta(days=365)).isoformat(),
                'end': datetime.now().isoformat()
            }
        
        return time_range
    
    def _build_strategies_for_part(self, lower_query: str, context: Dict[str, Any] = None, time_range: Dict = None) -> List[QueryStrategy]:
        """Build strategies for a single part of the query"""
        strategies = []
        
        # Check for compound queries with "and", "also", "plus", "with"
        is_compound = any(word in lower_query for word in [' and ', ' also ', ' plus ', ' with ', ' as well as '])
        
        # Check for comparative queries
        is_comparative = any(word in lower_query for word in ['compare', 'versus', 'vs', 'better', 'worse'])
        
        # Check for analytical queries
        is_analytical = any(phrase in lower_query for phrase in [
            'analyze', 'analysis', 'breakdown', 'insights', 'trends', 'patterns'
        ])
        
        # Build strategies for each component of the query
        # Comprehensive campaign performance queries (check first for most specific)
        if any(phrase in lower_query for phrase in [
            'campaign data', 'campaign performance', 'sends for campaigns',
            'deliveries', 'open percent', 'click percent', 'campaign metrics'
        ]) or ('campaign' in lower_query and is_analytical):
            strategies.extend(self._build_comprehensive_campaign_strategies(lower_query, context))
        
        # Revenue/Sales queries - use client's placed_order_metric_id
        if any(word in lower_query for word in ['revenue', 'sales', 'orders', 'income', 'earnings', 'money']):
            strategies.extend(self._build_revenue_strategies(lower_query, context))
            
            # Also get flow revenue if requested
            if 'flow' in lower_query:
                strategies.extend(self._build_flow_revenue_strategies(lower_query, context))
        
        # Performance/metrics queries
        if any(word in lower_query for word in ['performance', 'metric', 'statistic', 'analytics']):
            strategies.extend(self._build_performance_strategies(lower_query, context))
        
        # Campaign queries (if not already handled above)
        if 'campaign' in lower_query and not any(s.tool.startswith('campaigns.') for s in strategies):
            strategies.extend(self._build_campaign_strategies(lower_query, context))
        
        # Flow queries
        if any(word in lower_query for word in ['flow', 'automation', 'workflow']):
            strategies.extend(self._build_flow_strategies(lower_query))
        
        # Segment queries
        if any(word in lower_query for word in ['segment', 'audience', 'group', 'segments']):
            strategies.extend(self._build_segment_strategies(lower_query))
        
        # Profile queries
        if any(word in lower_query for word in ['customer', 'profile', 'subscriber', 'contact', 'people']):
            strategies.extend(self._build_profile_strategies(lower_query))
        
        # Template queries
        if any(word in lower_query for word in ['template', 'templates', 'email design']):
            strategies.append(QueryStrategy(
                tool='templates.list',
                params={'limit': 20},
                description='List email templates'
            ))
        
        # List queries
        if any(word in lower_query for word in ['list', 'lists', 'mailing list']):
            strategies.append(QueryStrategy(
                tool='lists.list',
                params={'limit': 20},
                description='List all mailing lists'
            ))
        
        # Tag queries
        if any(word in lower_query for word in ['tag', 'tags', 'label', 'labels']):
            strategies.append(QueryStrategy(
                tool='tags.list',
                params={'limit': 50},
                description='List all tags'
            ))
        
        # Event queries
        if any(word in lower_query for word in ['event', 'events', 'tracking']):
            strategies.append(QueryStrategy(
                tool='events.list',
                params={'limit': 50},
                description='List tracked events'
            ))
        
        # For comparative queries, ensure we get both datasets
        if is_comparative and len(strategies) < 2:
            # Add campaigns and segments for comparison
            if not any(s.tool == 'campaigns.list' for s in strategies):
                strategies.append(QueryStrategy(
                    tool='campaigns.list',
                    params={'limit': 50},
                    description='Get campaigns for comparison'
                ))
            if not any(s.tool == 'segments.list' for s in strategies):
                strategies.append(QueryStrategy(
                    tool='segments.list',
                    params={'limit': 50},
                    description='Get segments for comparison'
                ))
        
        # Default fallback strategies if nothing matched
        if not strategies:
            strategies.extend(self._build_default_strategies(lower_query))
        
        return strategies
    
    def guess_direct_tool(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Guess the most likely direct tool from a natural language query
        
        Args:
            query: Natural language query
            
        Returns:
            Tool name and parameters, or None
        """
        lower_query = query.lower()
        
        # Simple keyword mapping
        if 'campaign' in lower_query:
            return {'tool': 'campaigns.list', 'params': {'limit': 20}}
        elif 'metric' in lower_query or 'performance' in lower_query:
            return {'tool': 'metrics.list', 'params': {'limit': 50}}
        elif 'segment' in lower_query:
            return {'tool': 'segments.list', 'params': {'limit': 20}}
        elif 'flow' in lower_query:
            return {'tool': 'flows.list', 'params': {'limit': 20}}
        elif 'profile' in lower_query or 'customer' in lower_query:
            return {'tool': 'profiles.list', 'params': {'limit': 20}}
        elif 'template' in lower_query:
            return {'tool': 'templates.list', 'params': {'limit': 20}}
        
        # Default to campaigns
        return {'tool': 'campaigns.list', 'params': {'limit': 10}}
    
    def _build_revenue_strategies(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """Build strategies for revenue/sales queries using client's placed_order_metric_id"""
        strategies = []
        date_range = self._extract_date_range(query)
        revenue_metric_id = context.get('revenue_metric_id') if context else None
        
        if revenue_metric_id:
            # Use the client's specific revenue metric ID
            # Build filter array for date range
            filter_array = []
            if date_range.get('start') and date_range.get('end'):
                filter_array = [
                    f"greater-or-equal(datetime,{date_range['start']})",
                    f"less-than(datetime,{date_range['end']})"
                ]
            else:
                # Default to last 30 days
                from datetime import datetime, timedelta
                end = datetime.now()
                start = end - timedelta(days=30)
                filter_array = [
                    f"greater-or-equal(datetime,{start.isoformat()}Z)",
                    f"less-than(datetime,{end.isoformat()}Z)"
                ]
            
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params={
                    'metric_id': revenue_metric_id,
                    'measurements': ['sum_value', 'count'],  # Use plural and correct measurement names
                    'interval': 'day',
                    'filter': filter_array,
                    'timezone': 'UTC'
                },
                description=f"Get revenue data using client's metric {revenue_metric_id}"
            ))
        else:
            # Fallback: Try to find the Placed Order metric
            strategies.append(QueryStrategy(
                tool='metrics.list',
                params={'limit': 100},
                description="Find revenue metrics"
            ))
            # Then aggregate the found metric
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params={
                    'metric_id': 'VevE7N',  # Common Placed Order metric ID
                    'measurement': 'sum',
                    'group_by': ['day'],
                    'timeframe': date_range.get('timeframe', 'last_30_days')
                },
                description="Aggregate revenue metrics"
            ))
        
        return strategies
    
    def _build_comprehensive_campaign_strategies(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """Build strategies for comprehensive campaign performance queries"""
        strategies = []
        date_range = self._extract_date_range(query)
        
        # Strategy 1: Get list of campaigns first
        list_campaigns = QueryStrategy(
            tool='campaigns.list',
            params={'limit': 50},
            description='Get campaigns list'
        )
        
        # Process campaigns to get detailed metrics for each
        def process_campaigns_for_metrics(result):
            follow_up = []
            if result and 'data' in result:
                campaigns_data = result.get('data', {})
                if isinstance(campaigns_data, dict) and 'data' in campaigns_data:
                    campaigns = campaigns_data.get('data', [])
                elif isinstance(campaigns_data, dict) and 'success' in campaigns_data:
                    # Handle nested response from MCP gateway
                    inner_data = campaigns_data.get('data', {})
                    if isinstance(inner_data, dict) and 'data' in inner_data:
                        campaigns = inner_data.get('data', [])
                    else:
                        campaigns = []
                else:
                    campaigns = []
                
                # Get metrics for each campaign (limit to recent campaigns)
                for campaign in campaigns[:10]:  # Process first 10 campaigns
                    campaign_id = campaign.get('id')
                    campaign_name = campaign.get('attributes', {}).get('name', campaign_id)
                    
                    # Use the correct tool name for campaign metrics
                    follow_up.append(QueryStrategy(
                        tool='get_campaign_metrics',  # This is the actual MCP tool name
                        params={
                            'id': campaign_id,
                            'metrics': [
                                'sent', 'delivered', 'bounced',
                                'open_rate', 'click_rate', 'conversion_rate',
                                'revenue', 'revenue_per_recipient',
                                'unsubscribe_rate', 'spam_complaint_rate'
                            ],
                            'start_date': date_range['start'],
                            'end_date': date_range['end'],
                            'conversion_metric_id': context.get('revenue_metric_id') if context else None
                        },
                        description=f'Get detailed metrics for campaign: {campaign_name}'
                    ))
            
            return follow_up
        
        list_campaigns.process_next = process_campaigns_for_metrics
        strategies.append(list_campaigns)
        
        # Also add overall revenue metrics if revenue is mentioned
        if any(word in query.lower() for word in ['revenue', 'order', 'sales']):
            revenue_metric_id = context.get('revenue_metric_id') if context else None
            if revenue_metric_id:
                filter_array = [
                    f"greater-or-equal(datetime,{date_range['start']})",
                    f"less-than(datetime,{date_range['end']})"
                ]
                
                strategies.append(QueryStrategy(
                    tool='metrics.aggregate',
                    params={
                        'metric_id': revenue_metric_id,
                        'measurements': ['sum_value', 'count'],
                        'interval': 'day',
                        'filter': filter_array,
                        'timezone': 'UTC'
                    },
                    description='Get overall revenue metrics'
                ))
        
        return strategies
    
    def _build_flow_revenue_strategies(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """Build strategies for flow revenue queries"""
        strategies = []
        date_range = self._extract_date_range(query)
        revenue_metric_id = context.get('revenue_metric_id') if context else None
        
        if revenue_metric_id:
            # Get flow-triggered revenue
            # Flows don't have direct revenue, but we can filter metrics by flow trigger
            filter_array = [
                f"greater-or-equal(datetime,{date_range['start']})",
                f"less-than(datetime,{date_range['end']})"
            ]
            
            strategies.append(QueryStrategy(
                tool='flows.list',
                params={'limit': 50},
                description='List flows for revenue attribution'
            ))
            
            # Get metrics for flow-triggered events
            strategies.append(QueryStrategy(
                tool='metrics.aggregate',
                params={
                    'metric_id': revenue_metric_id,
                    'measurements': ['sum_value', 'count'],
                    'interval': 'day',
                    'filter': filter_array,
                    'group_by': ['flow'],  # Group by flow if possible
                    'timezone': 'UTC'
                },
                description=f"Get flow revenue using metric {revenue_metric_id}"
            ))
        
        return strategies
    
    def _build_performance_strategies(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """Build strategies for performance queries"""
        strategies = []
        date_range = self._extract_date_range(query)
        
        # First, get available metrics
        list_strategy = QueryStrategy(
            tool='metrics.list',
            params={'limit': 100},
            description='Get available metrics'
        )
        
        # Add processing function to aggregate key metrics
        def process_metrics(result):
            if not result.get('success') or not result.get('data'):
                return []
            
            metrics_data = result['data'].get('data', {}).get('data', [])
            follow_up = []
            
            # Find key email metrics
            priority_metrics = ['Opened Email', 'Clicked Email', 'Received Email', 'Sent Email']
            for metric in metrics_data:
                if metric.get('attributes', {}).get('name') in priority_metrics:
                    follow_up.append(QueryStrategy(
                        tool='metrics.aggregate',
                        params={
                            'metric_id': metric['id'],
                            'by': ['day'],
                            'measurements': ['sum_value', 'count'],
                            'filter': f"greater-or-equal(datetime,{date_range['start']}),less-than(datetime,{date_range['end']})"
                        },
                        description=f"Aggregate {metric['attributes']['name']}"
                    ))
            
            return follow_up
        
        list_strategy.process_next = process_metrics
        strategies.append(list_strategy)
        
        return strategies
    
    def _build_campaign_strategies(self, query: str, context: Dict[str, Any] = None) -> List[QueryStrategy]:
        """Build strategies for campaign queries"""
        strategies = []
        date_range = self._extract_date_range(query)
        lower_query = query.lower()
        
        # Check if detailed metrics are requested
        needs_metrics = any(word in lower_query for word in [
            'sends', 'deliveries', 'open', 'click', 'revenue', 'unsubscribe', 'spam',
            'performance', 'metrics', 'statistics', 'average order', 'utm', 'mobile', 'desktop'
        ])
        
        if needs_metrics:
            # Get campaigns first to get their IDs
            campaigns_strategy = QueryStrategy(
                tool='campaigns.list',
                params={'limit': 50},
                description='List campaigns for metrics'
            )
            
            # Process campaign list to get metrics for each
            def process_campaigns(result):
                follow_up = []
                if result and 'data' in result:
                    campaigns = result.get('data', {}).get('data', [])
                    for campaign in campaigns[:10]:  # Limit to first 10 campaigns
                        # Get detailed metrics for each campaign
                        follow_up.append(QueryStrategy(
                            tool='campaigns.get_metrics',
                            params={
                                'id': campaign['id'],
                                'metrics': [
                                    'sent', 'delivered', 'bounced',
                                    'open_rate', 'click_rate', 'conversion_rate',
                                    'unsubscribe_rate', 'spam_complaint_rate',
                                    'revenue', 'revenue_per_recipient'
                                ]
                            },
                            description=f"Get metrics for campaign {campaign.get('attributes', {}).get('name', campaign['id'])}"
                        ))
                return follow_up
            
            campaigns_strategy.process_next = process_campaigns
            strategies.append(campaigns_strategy)
        else:
            # Simple campaign list
            strategies.append(QueryStrategy(
                tool='campaigns.list',
                params={'limit': 20},
                description='List campaigns'
            ))
        
        return strategies
    
    def _build_flow_strategies(self, query: str) -> List[QueryStrategy]:
        """Build strategies for flow queries"""
        return [
            QueryStrategy(
                tool='flows.list',
                params={'limit': 20},
                description='List flows'
            )
        ]
    
    def _build_segment_strategies(self, query: str) -> List[QueryStrategy]:
        """Build strategies for segment queries"""
        return [
            QueryStrategy(
                tool='segments.list',
                params={'limit': 20},
                description='List segments'
            )
        ]
    
    def _build_profile_strategies(self, query: str) -> List[QueryStrategy]:
        """Build strategies for profile queries"""
        return [
            QueryStrategy(
                tool='profiles.list',
                params={'limit': 20},
                description='List profiles'
            )
        ]
    
    def _build_default_strategies(self, query: str) -> List[QueryStrategy]:
        """Build default fallback strategies"""
        date_range = self._extract_date_range(query) if self._has_time_reference(query) else None
        
        strategies = [
            QueryStrategy(
                tool='campaigns.list',
                params={'limit': 10},
                description='List recent campaigns (fallback)'
            )
        ]
        
        if date_range:
            strategies.append(QueryStrategy(
                tool='metrics.list',
                params={'limit': 50},
                description='List available metrics (fallback)'
            ))
        
        return strategies
    
    def _extract_date_range(self, query: str) -> Dict[str, str]:
        """Extract date range from query"""
        import re
        import calendar
        
        now = datetime.now()
        end = now.isoformat()
        lower_query = query.lower()
        
        # Check for specific month/year (e.g., "October 2024", "October of 2024")
        month_pattern = r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(?:of\s+)?(\d{4})'
        month_match = re.search(month_pattern, lower_query, re.IGNORECASE)
        if month_match:
            month_name = month_match.group(1).lower()
            year = int(month_match.group(2))
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12
            }
            month = month_map[month_name]
            
            # Calculate first and last day of the month
            first_day = datetime(year, month, 1)
            last_day = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)
            
            return {
                'start': first_day.isoformat() + 'Z',
                'end': last_day.isoformat() + 'Z',
                'timeframe': f'{month_name}_{year}'
            }
        
        # Check for relative time periods
        if 'last 30 days' in lower_query or 'past month' in lower_query or 'last thirty days' in lower_query:
            start = (now - timedelta(days=30)).isoformat()
        elif 'last 7 days' in lower_query or 'past week' in lower_query:
            start = (now - timedelta(days=7)).isoformat()
        elif 'last 90 days' in lower_query or 'last 3 months' in lower_query:
            start = (now - timedelta(days=90)).isoformat()
        elif 'last year' in lower_query or 'past year' in lower_query:
            start = (now - timedelta(days=365)).isoformat()
        elif 'today' in lower_query:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif 'yesterday' in lower_query:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            end = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            # Default to last 30 days
            start = (now - timedelta(days=30)).isoformat()
        
        return {'start': start, 'end': end}
    
    def _has_time_reference(self, query: str) -> bool:
        """Check if query contains time references"""
        time_words = ['last', 'past', 'today', 'yesterday', 'week', 'month', 'year', 'days']
        return any(word in query.lower() for word in time_words)


class QueryExecutor:
    """Executes query strategies with retry and fallback logic"""
    
    def __init__(self, mcp_gateway_url: str):
        self.mcp_gateway_url = mcp_gateway_url
    
    async def execute_with_retry(self, strategies: List[QueryStrategy], 
                                 client_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Execute strategies with retry logic
        
        Args:
            strategies: List of strategies to try
            client_id: Client identifier
            max_retries: Maximum number of retries
            
        Returns:
            Combined results from successful strategies
        """
        all_results = []
        successful_results = []
        
        for strategy in strategies:
            try:
                result = await self._execute_strategy(strategy, client_id)
                
                if result.get('success'):
                    all_results.append({
                        'strategy': strategy.description,
                        'tool': strategy.tool,
                        'data': result.get('data')
                    })
                    
                    # Process follow-up queries if defined
                    if strategy.process_next and result.get('data'):
                        follow_up_queries = strategy.process_next(result)
                        for follow_up in follow_up_queries:
                            try:
                                follow_up_result = await self._execute_strategy(follow_up, client_id)
                                if follow_up_result.get('success'):
                                    successful_results.append({
                                        'strategy': follow_up.description,
                                        'tool': follow_up.tool,
                                        'data': follow_up_result.get('data')
                                    })
                            except Exception as e:
                                logger.debug(f"Follow-up query failed: {e}")
                    else:
                        successful_results.append({
                            'strategy': strategy.description,
                            'tool': strategy.tool,
                            'data': result.get('data')
                        })
                    
                    # If we have useful results, we can stop
                    if successful_results and self._has_useful_data(result.get('data')):
                        break
                        
            except Exception as e:
                logger.warning(f"Strategy '{strategy.description}' failed: {e}")
                
                # Try fallback tool if available
                if strategy.fallback_tool:
                    try:
                        fallback_result = await self._execute_strategy(
                            QueryStrategy(
                                tool=strategy.fallback_tool,
                                params=strategy.fallback_params,
                                description=f"{strategy.description} (fallback)"
                            ),
                            client_id
                        )
                        if fallback_result.get('success'):
                            all_results.append(fallback_result)
                    except Exception as fallback_error:
                        logger.debug(f"Fallback also failed: {fallback_error}")
        
        # Return results with aggregated insights
        if successful_results:
            # Generate insights from the collected data
            insights = self._generate_insights(successful_results)
            
            return {
                'success': True,
                'results': successful_results,
                'total_strategies': len(strategies),
                'successful_strategies': len(successful_results),
                'mode': 'intelligent',
                'insights': insights
            }
        elif all_results:
            return {
                'success': True,
                'results': all_results,
                'total_strategies': len(strategies),
                'successful_strategies': len(all_results),
                'mode': 'intelligent',
                'partial': True
            }
        else:
            return {
                'success': False,
                'error': 'No strategies succeeded',
                'strategies_attempted': [s.description for s in strategies],
                'mode': 'intelligent'
            }
    
    def _generate_insights(self, results: List[Dict]) -> Dict[str, Any]:
        """
        Generate insights from multiple query results
        
        Args:
            results: List of successful query results
            
        Returns:
            Dictionary of insights and correlations
        """
        insights = {
            'data_summary': {},
            'correlations': [],
            'recommendations': []
        }
        
        # Analyze each result type
        for result in results:
            tool = result.get('tool', '')
            data = result.get('data', {})
            
            # Extract key metrics based on tool type
            if 'campaigns' in tool:
                campaigns_data = self._extract_nested_data(data)
                if campaigns_data:
                    insights['data_summary']['campaigns'] = {
                        'total': len(campaigns_data),
                        'sent': sum(1 for c in campaigns_data if self._get_attr(c, 'status') == 'Sent'),
                        'scheduled': sum(1 for c in campaigns_data if self._get_attr(c, 'status') == 'Scheduled')
                    }
            
            elif 'segments' in tool:
                segments_data = self._extract_nested_data(data)
                if segments_data:
                    insights['data_summary']['segments'] = {
                        'total': len(segments_data),
                        'active': sum(1 for s in segments_data if self._get_attr(s, 'is_active')),
                        'processing': sum(1 for s in segments_data if self._get_attr(s, 'is_processing'))
                    }
            
            elif 'metrics' in tool or 'revenue' in tool:
                # Extract revenue/metrics data
                if isinstance(data, dict) and 'data' in data:
                    metrics_data = data.get('data', {})
                    if 'attributes' in metrics_data:
                        insights['data_summary']['metrics'] = metrics_data['attributes']
        
        # Generate recommendations based on the data
        if 'campaigns' in insights['data_summary'] and 'segments' in insights['data_summary']:
            campaign_count = insights['data_summary']['campaigns']['total']
            segment_count = insights['data_summary']['segments']['total']
            
            if segment_count > campaign_count * 2:
                insights['recommendations'].append(
                    f"You have {segment_count} segments but only {campaign_count} campaigns. "
                    "Consider creating more targeted campaigns for underutilized segments."
                )
        
        return insights
    
    def _extract_nested_data(self, data: Any) -> List:
        """Extract nested data array from various response formats"""
        if isinstance(data, dict):
            if 'data' in data:
                inner = data['data']
                if isinstance(inner, dict) and 'data' in inner:
                    result = inner['data']
                    if isinstance(result, list):
                        return result
                elif isinstance(inner, list):
                    return inner
        return []
    
    def _get_attr(self, item: Dict, attr_name: str) -> Any:
        """Safely get attribute from item"""
        if 'attributes' in item:
            return item['attributes'].get(attr_name)
        return item.get(attr_name)
    
    async def _execute_strategy(self, strategy: QueryStrategy, client_id: str) -> Dict[str, Any]:
        """Execute a single strategy"""
        logger.info(f"🔧 Executing strategy: {strategy.description} with tool: {strategy.tool}")
        logger.info(f"🔧 Strategy params: {strategy.params}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.mcp_gateway_url}/tool/{strategy.tool}"
                payload = {
                    "tool": strategy.tool,
                    "client_id": client_id,
                    "params": strategy.params
                }
                
                logger.info(f"🌐 Making request to: {url}")
                logger.info(f"🌐 Payload: {payload}")
                
                # Use the specific tool endpoint which works correctly
                response = await client.post(url, json=payload)
                
                logger.info(f"📡 Response status: {response.status_code}")
                logger.info(f"📡 Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    logger.info(f"✅ Strategy succeeded: {strategy.description}")
                    logger.debug(f"📋 Response data: {response_data}")
                    return {
                        'success': True,
                        'data': response_data
                    }
                else:
                    error_text = response.text
                    logger.error(f"❌ Strategy failed: {strategy.description} - Status {response.status_code}")
                    logger.error(f"❌ Error details: {error_text}")
                    return {
                        'success': False,
                        'error': f"Status {response.status_code}",
                        'details': error_text
                    }
        except Exception as e:
            logger.error(f"🚨 Strategy execution exception: {strategy.description} - {e}")
            return {
                'success': False,
                'error': f"Exception: {str(e)}",
                'details': str(e)
            }
    
    def _has_useful_data(self, data: Any) -> bool:
        """Check if data contains useful information"""
        logger.debug(f"🔍 Checking data usefulness: {type(data)}")
        
        if not data:
            logger.debug("❌ Data is empty/None")
            return False
        
        # More permissive check - if we have any data structure with content, it's useful
        if isinstance(data, dict):
            # Check if it has a success field and it's True
            if data.get('success') is True:
                logger.debug("✅ Data has success=True, considering it useful")
                return True
                
            # Check for nested data structures
            if 'data' in data:
                inner_data = data['data']
                if isinstance(inner_data, dict) and inner_data.get('success'):
                    # Check for actual content in nested data
                    nested_data = inner_data.get('data', {})
                    if isinstance(nested_data, dict) and nested_data.get('data'):
                        content = nested_data['data']
                        if isinstance(content, list) and len(content) > 0:
                            logger.debug(f"✅ Found {len(content)} items in nested data")
                            return True
                    elif isinstance(nested_data, list) and len(nested_data) > 0:
                        logger.debug(f"✅ Found {len(nested_data)} items in data list")
                        return True
        
        logger.debug("❌ Data doesn't contain useful content")
        return False