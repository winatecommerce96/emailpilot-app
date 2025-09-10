"""
Comprehensive Query Handler for Complex Multi-Part Klaviyo Queries
Designed specifically for calendar workflow and complex analytical requests
With full LangSmith tracing integration
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import httpx
from dataclasses import dataclass
from collections import defaultdict

# LangSmith tracing
try:
    from langsmith import traceable
    TRACING_ENABLED = True
except ImportError:
    # Fallback decorator if LangSmith not available
    def traceable(name=None, tags=None, metadata=None):
        def decorator(func):
            return func
        return decorator
    TRACING_ENABLED = False

logger = logging.getLogger(__name__)
if TRACING_ENABLED:
    logger.info("🔍 LangSmith tracing enabled for Comprehensive Query Handler")
else:
    logger.info("LangSmith tracing not available")

@dataclass
class QueryRequest:
    """Represents a single query request"""
    query_type: str  # campaigns, segments, revenue, etc.
    metrics: List[str]  # specific metrics requested
    time_range: Optional[Dict[str, Any]]  # time period
    filters: Dict[str, Any]  # additional filters
    tool: str  # MCP tool to use
    params: Dict[str, Any]  # tool parameters
    description: str  # human-readable description

class ComprehensiveQueryHandler:
    """
    Handles complex, multi-part queries by:
    1. Parsing into individual requests
    2. Executing in parallel where possible
    3. Aggregating results
    4. Providing AI-ready analysis
    """
    
    def __init__(self, mcp_gateway_url: str = "http://localhost:8000/api/mcp/gateway"):
        self.mcp_gateway_url = mcp_gateway_url
        
    @traceable(
        name="process_comprehensive_query",
        tags=["comprehensive", "query", "orchestration"],
        metadata={"handler": "ComprehensiveQueryHandler"}
    )
    async def process_comprehensive_query(self, query: str, client_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a comprehensive multi-part query with full tracing
        
        Args:
            query: Natural language query (can be multi-line)
            client_id: Client identifier
            context: Additional context (metric IDs, etc.)
            
        Returns:
            Aggregated results with AI-ready analysis
        """
        logger.info(f"📊 Processing comprehensive query for {client_id}")
        
        # Parse the query into individual requests
        requests = self._parse_comprehensive_query(query, context)
        logger.info(f"📝 Parsed into {len(requests)} individual requests")
        
        # Execute requests (in parallel where possible)
        results = await self._execute_requests_parallel(requests, client_id)
        logger.info(f"✅ Executed {len(results)} requests successfully")
        
        # Aggregate and analyze results
        aggregated = self._aggregate_results(results)
        
        # Prepare for AI analysis
        ai_ready = self._prepare_for_ai_analysis(aggregated, query, client_id)
        
        return {
            'success': True,
            'query': query,
            'client_id': client_id,
            'total_requests': len(requests),
            'successful_requests': len(results),
            'raw_results': results,
            'aggregated_data': aggregated,
            'ai_ready_analysis': ai_ready,
            'timestamp': datetime.now().isoformat()
        }
    
    @traceable(name="parse_query", tags=["parsing", "nlp"])
    def _parse_comprehensive_query(self, query: str, context: Dict[str, Any] = None) -> List[QueryRequest]:
        """
        Parse complex query into individual executable requests with tracing
        """
        requests = []
        
        # Split by lines or periods to get individual requests
        query_lines = []
        if '\n' in query:
            query_lines = [line.strip() for line in query.split('\n') if line.strip()]
        else:
            # Split by periods but keep time ranges intact
            query_lines = re.split(r'(?<!\d)\.(?!\d)', query)
            query_lines = [line.strip() for line in query_lines if line.strip()]
        
        # Get default metric IDs from context
        revenue_metric_id = context.get('revenue_metric_id', 'TPWsCU') if context else 'TPWsCU'
        
        for line in query_lines:
            lower_line = line.lower()
            
            # Extract time range for this line
            time_range = self._extract_time_range(lower_line)
            
            # Parse different types of requests
            if 'campaign performance' in lower_line:
                metrics = self._extract_metrics(lower_line)
                if not metrics:
                    metrics = ['open_rate', 'click_rate', 'conversion_rate']
                
                requests.append(QueryRequest(
                    query_type='campaign_performance',
                    metrics=metrics,
                    time_range=time_range,
                    filters={},
                    tool='campaigns.list',
                    params={'limit': 100},
                    description=f"Campaign performance for {time_range.get('days', 'all')} days"
                ))
                
                # Also get campaign metrics if specific metrics requested
                if metrics:
                    requests.append(QueryRequest(
                        query_type='campaign_metrics',
                        metrics=metrics,
                        time_range=time_range,
                        filters={},
                        tool='metrics.aggregate',
                        params=self._build_metrics_params(metrics, time_range, revenue_metric_id),
                        description=f"Campaign metrics: {', '.join(metrics)}"
                    ))
            
            elif 'segment' in lower_line:
                segment_metrics = []
                if 'engagement' in lower_line:
                    segment_metrics.append('engagement_rate')
                if 'size' in lower_line:
                    segment_metrics.append('member_count')
                if 'value' in lower_line:
                    segment_metrics.append('value_metrics')
                if 'growth' in lower_line:
                    segment_metrics.append('growth_rate')
                
                requests.append(QueryRequest(
                    query_type='segments',
                    metrics=segment_metrics,
                    time_range=time_range,
                    filters={'active': True} if 'active' in lower_line else {},
                    tool='segments.list',
                    params={'limit': 100},
                    description=f"Segments with metrics: {', '.join(segment_metrics) if segment_metrics else 'all'}"
                ))
            
            elif 'revenue' in lower_line:
                revenue_breakdowns = []
                if 'per campaign' in lower_line:
                    revenue_breakdowns.append('campaign')
                if 'by segment' in lower_line:
                    revenue_breakdowns.append('segment')
                
                requests.append(QueryRequest(
                    query_type='revenue',
                    metrics=['total_revenue'] + revenue_breakdowns,
                    time_range=time_range,
                    filters={},
                    tool='metrics.aggregate',
                    params=self._build_revenue_params(time_range, revenue_metric_id, revenue_breakdowns),
                    description=f"Revenue analysis for {time_range.get('days', 'all')} days"
                ))
            
            elif 'optimal send time' in lower_line or 'send time' in lower_line:
                requests.append(QueryRequest(
                    query_type='send_time_analysis',
                    metrics=['engagement_by_hour', 'engagement_by_day'],
                    time_range=time_range,
                    filters={},
                    tool='campaigns.list',
                    params={'limit': 200},  # Get more campaigns for analysis
                    description="Optimal send time analysis"
                ))
            
            elif 'subject line' in lower_line or 'content theme' in lower_line or 'cta' in lower_line:
                requests.append(QueryRequest(
                    query_type='content_analysis',
                    metrics=['subject_lines', 'content_themes', 'ctas'],
                    time_range=time_range,
                    filters={},
                    tool='campaigns.list',
                    params={'limit': 100},
                    description="Content performance analysis"
                ))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_requests = []
        for req in requests:
            key = (req.tool, str(req.params))
            if key not in seen:
                seen.add(key)
                unique_requests.append(req)
        
        return unique_requests
    
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
                'end': end_date.isoformat(),
                'filter': [
                    f"greater-or-equal(datetime,{start_date.isoformat()})",
                    f"less-than(datetime,{end_date.isoformat()})"
                ]
            }
        elif 'last month' in query or 'past month' in query:
            time_range = {
                'days': 30,
                'start': (datetime.now() - timedelta(days=30)).isoformat(),
                'end': datetime.now().isoformat(),
                'filter': [
                    f"greater-or-equal(datetime,{(datetime.now() - timedelta(days=30)).isoformat()})",
                    f"less-than(datetime,{datetime.now().isoformat()})"
                ]
            }
        elif 'last year' in query or 'past year' in query:
            time_range = {
                'days': 365,
                'start': (datetime.now() - timedelta(days=365)).isoformat(),
                'end': datetime.now().isoformat(),
                'filter': [
                    f"greater-or-equal(datetime,{(datetime.now() - timedelta(days=365)).isoformat()})",
                    f"less-than(datetime,{datetime.now().isoformat()})"
                ]
            }
        
        return time_range
    
    def _extract_metrics(self, query: str) -> List[str]:
        """Extract specific metrics mentioned in query"""
        metrics = []
        
        metric_mapping = {
            'open_rate': ['open rate', 'open_rate', 'opens'],
            'click_rate': ['click rate', 'click_rate', 'clicks', 'ctr'],
            'conversion_rate': ['conversion', 'conversion_rate', 'conversions'],
            'bounce_rate': ['bounce', 'bounce_rate', 'bounces'],
            'unsubscribe_rate': ['unsubscribe', 'unsubscribe_rate'],
            'revenue': ['revenue', 'sales', 'income'],
            'engagement_rate': ['engagement', 'engagement_rate'],
            'growth_rate': ['growth', 'growth_rate']
        }
        
        for metric, keywords in metric_mapping.items():
            if any(keyword in query.lower() for keyword in keywords):
                metrics.append(metric)
        
        return metrics
    
    def _build_metrics_params(self, metrics: List[str], time_range: Dict, metric_id: str) -> Dict[str, Any]:
        """Build parameters for metrics.aggregate call"""
        params = {
            'metric_id': metric_id,
            'measurements': ['sum_value', 'count', 'unique'],
            'interval': 'day'
        }
        
        if time_range and 'filter' in time_range:
            params['filter'] = time_range['filter']
        
        return params
    
    def _build_revenue_params(self, time_range: Dict, metric_id: str, breakdowns: List[str]) -> Dict[str, Any]:
        """Build parameters for revenue metrics call"""
        params = {
            'metric_id': metric_id,
            'measurements': ['sum_value', 'count'],
            'interval': 'day',
            'timezone': 'UTC'
        }
        
        if time_range and 'filter' in time_range:
            params['filter'] = time_range['filter']
        
        # Add dimensions for breakdowns
        if 'campaign' in breakdowns:
            params['by'] = ['Campaign Name']
        elif 'segment' in breakdowns:
            params['by'] = ['$flow']
        
        return params
    
    @traceable(name="execute_parallel", tags=["execution", "parallel", "mcp"])
    async def _execute_requests_parallel(self, requests: List[QueryRequest], client_id: str) -> List[Dict[str, Any]]:
        """Execute multiple requests in parallel with tracing"""
        tasks = []
        
        for request in requests:
            task = self._execute_single_request(request, client_id)
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed requests
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Request {requests[i].description} failed: {result}")
            else:
                successful_results.append({
                    'request': requests[i],
                    'data': result
                })
        
        return successful_results
    
    @traceable(name="execute_mcp_request", tags=["mcp", "klaviyo"])
    async def _execute_single_request(self, request: QueryRequest, client_id: str) -> Dict[str, Any]:
        """Execute a single MCP request with tracing"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.mcp_gateway_url}/tool/{request.tool}"
            payload = {
                "tool": request.tool,
                "client_id": client_id,
                "params": request.params
            }
            
            logger.info(f"🔧 Executing: {request.description}")
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Request failed with status {response.status_code}: {response.text}")
    
    @traceable(name="aggregate_results", tags=["aggregation", "analysis"])
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple queries with tracing"""
        aggregated = {
            'campaigns': {},
            'segments': {},
            'revenue': {},
            'metrics': {},
            'send_times': {},
            'content': {}
        }
        
        for result_wrapper in results:
            request = result_wrapper['request']
            data = result_wrapper['data']
            
            if request.query_type == 'campaign_performance':
                aggregated['campaigns'] = self._extract_campaign_data(data)
            elif request.query_type == 'segments':
                aggregated['segments'] = self._extract_segment_data(data)
            elif request.query_type == 'revenue':
                aggregated['revenue'] = self._extract_revenue_data(data)
            elif request.query_type == 'send_time_analysis':
                aggregated['send_times'] = self._analyze_send_times(data)
            elif request.query_type == 'content_analysis':
                aggregated['content'] = self._analyze_content(data)
        
        return aggregated
    
    def _extract_campaign_data(self, data: Dict) -> Dict:
        """Extract campaign data from response"""
        campaigns = []
        
        if data.get('success') and 'data' in data:
            nested_data = data['data'].get('data', {}).get('data', [])
            for campaign in nested_data:
                attrs = campaign.get('attributes', {})
                campaigns.append({
                    'id': campaign.get('id'),
                    'name': attrs.get('name'),
                    'status': attrs.get('status'),
                    'send_time': attrs.get('send_time'),
                    'audiences': attrs.get('audiences', {})
                })
        
        return {
            'total': len(campaigns),
            'campaigns': campaigns[:10]  # Limit for summary
        }
    
    def _extract_segment_data(self, data: Dict) -> Dict:
        """Extract segment data from response"""
        segments = []
        
        if data.get('success') and 'data' in data:
            nested_data = data['data'].get('data', {}).get('data', [])
            for segment in nested_data:
                attrs = segment.get('attributes', {})
                segments.append({
                    'id': segment.get('id'),
                    'name': attrs.get('name'),
                    'is_active': attrs.get('is_active'),
                    'created': attrs.get('created'),
                    'updated': attrs.get('updated')
                })
        
        return {
            'total': len(segments),
            'active': sum(1 for s in segments if s.get('is_active')),
            'segments': segments[:10]  # Limit for summary
        }
    
    def _extract_revenue_data(self, data: Dict) -> Dict:
        """Extract revenue data from response"""
        if data.get('success') and 'data' in data:
            metrics_data = data['data'].get('data', {}).get('data', {})
            attributes = metrics_data.get('attributes', {})
            
            # Calculate total revenue
            measurements = attributes.get('data', [{}])[0].get('measurements', {})
            revenue_values = measurements.get('sum_value', [])
            total_revenue = sum(revenue_values) if revenue_values else 0
            
            return {
                'total_revenue': total_revenue,
                'daily_revenue': revenue_values,
                'transaction_count': sum(measurements.get('count', [])),
                'dates': attributes.get('dates', [])
            }
        
        return {}
    
    def _analyze_send_times(self, data: Dict) -> Dict:
        """Analyze optimal send times from campaign data"""
        send_times = defaultdict(lambda: {'count': 0, 'performance': []})
        
        if data.get('success') and 'data' in data:
            campaigns = data['data'].get('data', {}).get('data', [])
            
            for campaign in campaigns:
                attrs = campaign.get('attributes', {})
                send_time = attrs.get('send_time')
                
                if send_time:
                    dt = datetime.fromisoformat(send_time.replace('Z', '+00:00'))
                    hour = dt.hour
                    day = dt.strftime('%A')
                    
                    send_times[f"{day}_{hour:02d}"]["count"] += 1
        
        # Find optimal times
        optimal_times = sorted(send_times.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
        
        return {
            'optimal_times': [{'time': k, 'count': v['count']} for k, v in optimal_times],
            'total_analyzed': len(send_times)
        }
    
    def _analyze_content(self, data: Dict) -> Dict:
        """Analyze content performance from campaign data"""
        content_analysis = {
            'subject_lines': [],
            'top_performers': []
        }
        
        if data.get('success') and 'data' in data:
            campaigns = data['data'].get('data', {}).get('data', [])
            
            for campaign in campaigns[:20]:  # Analyze top 20
                attrs = campaign.get('attributes', {})
                content_analysis['subject_lines'].append({
                    'name': attrs.get('name', ''),
                    'status': attrs.get('status', '')
                })
        
        return content_analysis
    
    def _prepare_for_ai_analysis(self, aggregated: Dict, query: str, client_id: str) -> Dict[str, Any]:
        """Prepare data for AI analysis"""
        return {
            'client_id': client_id,
            'original_query': query,
            'summary': {
                'total_campaigns': aggregated['campaigns'].get('total', 0),
                'active_segments': aggregated['segments'].get('active', 0),
                'total_revenue': aggregated['revenue'].get('total_revenue', 0),
                'optimal_send_times': aggregated['send_times'].get('optimal_times', []),
                'content_insights': len(aggregated['content'].get('subject_lines', []))
            },
            'recommendations': self._generate_recommendations(aggregated),
            'data_quality': self._assess_data_quality(aggregated),
            'ready_for_calendar_workflow': True
        }
    
    def _generate_recommendations(self, aggregated: Dict) -> List[str]:
        """Generate recommendations based on aggregated data"""
        recommendations = []
        
        # Campaign recommendations
        if aggregated['campaigns'].get('total', 0) < 10:
            recommendations.append("Consider increasing campaign frequency to improve engagement")
        
        # Segment recommendations
        active_segments = aggregated['segments'].get('active', 0)
        if active_segments > 20:
            recommendations.append(f"You have {active_segments} active segments - consider consolidating similar segments")
        
        # Revenue recommendations
        if aggregated['revenue'].get('total_revenue', 0) > 0:
            daily_avg = aggregated['revenue']['total_revenue'] / max(len(aggregated['revenue'].get('daily_revenue', [1])), 1)
            recommendations.append(f"Average daily revenue: ${daily_avg:.2f}")
        
        # Send time recommendations
        if aggregated['send_times'].get('optimal_times'):
            best_time = aggregated['send_times']['optimal_times'][0]
            recommendations.append(f"Optimal send time: {best_time['time'].replace('_', ' at ')}:00")
        
        return recommendations
    
    def _assess_data_quality(self, aggregated: Dict) -> Dict[str, Any]:
        """Assess the quality and completeness of data"""
        quality = {
            'completeness': 0,
            'data_points': 0,
            'missing_data': []
        }
        
        # Check what data we have
        if aggregated['campaigns'].get('total', 0) > 0:
            quality['completeness'] += 25
            quality['data_points'] += aggregated['campaigns']['total']
        else:
            quality['missing_data'].append('campaigns')
        
        if aggregated['segments'].get('total', 0) > 0:
            quality['completeness'] += 25
            quality['data_points'] += aggregated['segments']['total']
        else:
            quality['missing_data'].append('segments')
        
        if aggregated['revenue'].get('total_revenue', 0) > 0:
            quality['completeness'] += 25
            quality['data_points'] += len(aggregated['revenue'].get('daily_revenue', []))
        else:
            quality['missing_data'].append('revenue')
        
        if aggregated['send_times'].get('optimal_times'):
            quality['completeness'] += 25
            quality['data_points'] += aggregated['send_times']['total_analyzed']
        else:
            quality['missing_data'].append('send_times')
        
        return quality