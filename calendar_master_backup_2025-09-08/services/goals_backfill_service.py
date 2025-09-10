"""
Goals Backfill Service - Uses Natural Language MCP to fetch and store historical data
Handles comprehensive data backfill for all metrics from Klaviyo
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from app.services.client_key_resolver import ClientKeyResolver
from app.services.goal_predictor import GoalPredictor

logger = logging.getLogger(__name__)

class GoalsBackfillService:
    """
    Service for backfilling historical data and goals using Natural Language MCP
    """
    
    def __init__(self, db: firestore.Client, key_resolver: ClientKeyResolver):
        self.db = db
        self.key_resolver = key_resolver
        self.nl_mcp_url = "http://localhost:8000/api/mcp/nl"
        self.predictor = GoalPredictor()
    
    async def backfill_client_data(
        self, 
        client_id: str, 
        metrics: List[str] = None,
        years: int = 2
    ) -> Dict[str, Any]:
        """
        Backfill historical data for a client using natural language queries
        
        Args:
            client_id: Client identifier
            metrics: List of metrics to backfill (default: all key metrics)
            years: Number of years of historical data to fetch
        
        Returns:
            Summary of backfilled data
        """
        if not metrics:
            metrics = ["revenue", "open_rate", "click_rate", "bounce_rate", "delivered"]
        
        logger.info(f"Starting backfill for client {client_id} - Metrics: {metrics}, Years: {years}")
        
        results = {
            "client_id": client_id,
            "metrics_processed": [],
            "errors": [],
            "data_points": 0,
            "goals_generated": 0
        }
        
        # Process each metric
        for metric in metrics:
            try:
                logger.info(f"Backfilling {metric} for {client_id}")
                metric_result = await self._backfill_metric(client_id, metric, years)
                results["metrics_processed"].append({
                    "metric": metric,
                    "status": "success",
                    "data_points": metric_result.get("data_points", 0)
                })
                results["data_points"] += metric_result.get("data_points", 0)
            except Exception as e:
                logger.error(f"Error backfilling {metric}: {e}")
                results["errors"].append({
                    "metric": metric,
                    "error": str(e)
                })
        
        # Generate goals based on backfilled data
        try:
            goals_result = await self._generate_goals_from_backfill(client_id)
            results["goals_generated"] = goals_result.get("goals_created", 0)
        except Exception as e:
            logger.error(f"Error generating goals: {e}")
            results["errors"].append({
                "action": "generate_goals",
                "error": str(e)
            })
        
        return results
    
    async def _backfill_metric(
        self, 
        client_id: str, 
        metric: str, 
        years: int
    ) -> Dict[str, Any]:
        """
        Backfill a specific metric using natural language queries
        """
        # Craft specific queries for different metrics
        queries = self._generate_backfill_queries(metric, years)
        
        all_data = []
        for query in queries:
            try:
                # Use natural language API to fetch data
                response_data = await self._execute_nl_query(client_id, query)
                
                if response_data and response_data.get("success"):
                    # Extract and store the data
                    extracted_data = self._extract_metric_data(response_data, metric)
                    if extracted_data:
                        all_data.extend(extracted_data)
            except Exception as e:
                logger.warning(f"Query failed: {query} - Error: {e}")
                continue
        
        # Store in Firestore
        if all_data:
            await self._store_historical_data(client_id, metric, all_data)
        
        return {
            "metric": metric,
            "data_points": len(all_data),
            "date_range": self._get_date_range(all_data)
        }
    
    def _generate_backfill_queries(self, metric: str, years: int) -> List[str]:
        """
        Generate natural language queries for backfilling specific metrics
        """
        queries = []
        
        # Build time-based queries for comprehensive data fetching
        current_year = datetime.now().year
        
        if metric == "revenue":
            # Monthly revenue queries for each year
            for year_offset in range(years):
                year = current_year - year_offset
                queries.extend([
                    f"Get total revenue by month for {year}",
                    f"Show revenue for all campaigns in {year}",
                    f"Calculate placed orders value for each month of {year}"
                ])
        
        elif metric in ["open_rate", "click_rate"]:
            # Campaign performance metrics
            for year_offset in range(years):
                year = current_year - year_offset
                queries.extend([
                    f"Show {metric.replace('_', ' ')} for all campaigns in {year}",
                    f"Get monthly average {metric.replace('_', ' ')} for {year}",
                    f"List campaign {metric.replace('_', ' ')}s by month in {year}"
                ])
        
        elif metric == "bounce_rate":
            for year_offset in range(years):
                year = current_year - year_offset
                queries.append(f"Get bounce rates for all email campaigns in {year}")
        
        elif metric == "delivered":
            for year_offset in range(years):
                year = current_year - year_offset
                queries.append(f"Show total delivered emails by month for {year}")
        
        # Add comprehensive catch-all queries
        queries.append(f"Get all {metric.replace('_', ' ')} data for the last {years} years")
        queries.append(f"Show historical {metric.replace('_', ' ')} trends")
        
        return queries
    
    async def _execute_nl_query(self, client_id: str, query: str) -> Dict[str, Any]:
        """
        Execute a natural language query via the NL MCP endpoint
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.nl_mcp_url}/query",
                    json={
                        "query": query,
                        "client_id": client_id,
                        "context": {
                            "purpose": "backfill",
                            "return_raw_data": True
                        }
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"NL query failed with status {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error executing NL query: {e}")
            return None
    
    def _extract_metric_data(
        self, 
        response_data: Dict[str, Any], 
        metric: str
    ) -> List[Dict[str, Any]]:
        """
        Extract metric data from NL query response
        """
        extracted = []
        
        # Check different response structures
        result = response_data.get("result", {})
        raw_results = response_data.get("raw_results", [])
        
        # Try to extract from aggregated results
        if "metrics_data" in result:
            for data_point in result["metrics_data"]:
                extracted.append(self._normalize_data_point(data_point, metric))
        
        # Try to extract from raw results
        for raw_result in raw_results:
            if raw_result.get("success") and raw_result.get("data"):
                data = raw_result["data"]
                
                # Handle different data structures
                if isinstance(data, dict):
                    if "data" in data:
                        for item in data["data"]:
                            extracted.append(self._normalize_data_point(item, metric))
                    else:
                        extracted.append(self._normalize_data_point(data, metric))
                elif isinstance(data, list):
                    for item in data:
                        extracted.append(self._normalize_data_point(item, metric))
        
        return extracted
    
    def _normalize_data_point(
        self, 
        data_point: Dict[str, Any], 
        metric: str
    ) -> Dict[str, Any]:
        """
        Normalize a data point to a consistent structure
        """
        normalized = {
            "metric": metric,
            "timestamp": None,
            "value": None,
            "dimensions": {}
        }
        
        # Extract timestamp
        if "datetime" in data_point:
            normalized["timestamp"] = data_point["datetime"]
        elif "timestamp" in data_point:
            normalized["timestamp"] = data_point["timestamp"]
        elif "date" in data_point:
            normalized["timestamp"] = data_point["date"]
        
        # Extract value based on metric type
        if metric == "revenue":
            if "measurements" in data_point:
                measurements = data_point["measurements"]
                if isinstance(measurements, dict):
                    if "sum" in measurements:
                        normalized["value"] = measurements["sum"][0] if isinstance(measurements["sum"], list) else measurements["sum"]
                    elif "value" in measurements:
                        normalized["value"] = measurements["value"]
            elif "value" in data_point:
                normalized["value"] = data_point["value"]
            elif "revenue" in data_point:
                normalized["value"] = data_point["revenue"]
        else:
            # For rate metrics (open_rate, click_rate, etc.)
            if "rate" in data_point:
                normalized["value"] = data_point["rate"]
            elif metric in data_point:
                normalized["value"] = data_point[metric]
            elif "value" in data_point:
                normalized["value"] = data_point["value"]
            elif "measurements" in data_point:
                measurements = data_point["measurements"]
                if isinstance(measurements, dict) and "values" in measurements:
                    normalized["value"] = measurements["values"][0] if measurements["values"] else 0
        
        # Extract dimensions (campaign, flow, etc.)
        if "dimensions" in data_point:
            normalized["dimensions"] = data_point["dimensions"]
        elif "$attributed_message" in data_point:
            normalized["dimensions"]["campaign"] = data_point["$attributed_message"]
        
        return normalized
    
    async def _store_historical_data(
        self, 
        client_id: str, 
        metric: str, 
        data_points: List[Dict[str, Any]]
    ):
        """
        Store historical data in Firestore
        """
        collection_name = f"historical_metrics"
        
        # Group by month for efficient storage
        monthly_data = {}
        for point in data_points:
            if point["timestamp"] and point["value"] is not None:
                # Parse timestamp and group by year-month
                try:
                    dt = datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00"))
                    key = f"{dt.year}-{dt.month:02d}"
                    
                    if key not in monthly_data:
                        monthly_data[key] = {
                            "client_id": client_id,
                            "metric": metric,
                            "year": dt.year,
                            "month": dt.month,
                            "values": [],
                            "average": 0,
                            "total": 0,
                            "count": 0
                        }
                    
                    monthly_data[key]["values"].append(point["value"])
                    monthly_data[key]["count"] += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp {point['timestamp']}: {e}")
        
        # Calculate aggregates and store
        for key, data in monthly_data.items():
            if data["values"]:
                data["average"] = sum(data["values"]) / len(data["values"])
                data["total"] = sum(data["values"])
                
                # Store in Firestore
                doc_id = f"{client_id}_{metric}_{key}"
                self.db.collection(collection_name).document(doc_id).set(data)
                
                logger.info(f"Stored {data['count']} data points for {client_id}/{metric}/{key}")
    
    async def _generate_goals_from_backfill(self, client_id: str) -> Dict[str, Any]:
        """
        Generate goals based on backfilled historical data
        """
        current_year = datetime.now().year
        goals_created = 0
        
        # Fetch stored historical data
        historical_ref = self.db.collection("historical_metrics")\
            .where("client_id", "==", client_id)\
            .where("year", "==", current_year - 1)
        
        historical_docs = historical_ref.stream()
        
        # Group by month
        monthly_historicals = {}
        for doc in historical_docs:
            data = doc.to_dict()
            month = data.get("month")
            metric = data.get("metric")
            
            if month not in monthly_historicals:
                monthly_historicals[month] = {}
            
            monthly_historicals[month][metric] = {
                "value": data.get("average", 0),
                "total": data.get("total", 0)
            }
        
        # Generate goals for current year based on historical data
        for month, metrics_data in monthly_historicals.items():
            # Check if goal already exists
            existing_goal = self.db.collection("goals")\
                .where("client_id", "==", client_id)\
                .where("year", "==", current_year)\
                .where("month", "==", month)\
                .limit(1).stream()
            
            goal_exists = False
            for _ in existing_goal:
                goal_exists = True
                break
            
            if not goal_exists:
                # Create new goal with multi-metric support
                goal_data = {
                    "client_id": client_id,
                    "year": current_year,
                    "month": month,
                    "calculation_method": "ai_suggested",
                    "confidence": "high" if len(metrics_data) > 2 else "medium",
                    "human_override": False,
                    "metrics": {},
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                    "source": "backfill"
                }
                
                # Add each metric
                for metric, values in metrics_data.items():
                    # Apply YoY growth factor
                    growth_factor = 1.05  # 5% default growth
                    
                    goal_data["metrics"][metric] = {
                        "goal": values["value"] * growth_factor,
                        "historical_basis": values["value"],
                        "growth_factor": growth_factor
                    }
                    
                    # Backward compatibility for revenue
                    if metric == "revenue":
                        goal_data["revenue_goal"] = values["total"] * growth_factor
                
                # Store goal
                self.db.collection("goals").add(goal_data)
                goals_created += 1
                logger.info(f"Created goal for {client_id}/{current_year}/{month}")
        
        return {"goals_created": goals_created}
    
    def _get_date_range(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get the date range from data points
        """
        if not data_points:
            return {"start": None, "end": None}
        
        timestamps = [p["timestamp"] for p in data_points if p.get("timestamp")]
        if timestamps:
            return {
                "start": min(timestamps),
                "end": max(timestamps)
            }
        
        return {"start": None, "end": None}
    
    async def backfill_all_clients(
        self, 
        metrics: List[str] = None,
        years: int = 2
    ) -> Dict[str, Any]:
        """
        Backfill data for all active clients with API keys
        """
        results = {
            "clients_processed": [],
            "total_data_points": 0,
            "total_goals_generated": 0,
            "errors": []
        }
        
        # Get all active clients with API keys
        clients_ref = self.db.collection("clients")\
            .where("is_active", "==", True)
        
        for client_doc in clients_ref.stream():
            client_data = client_doc.to_dict()
            client_id = client_doc.id
            
            # Check if client has API key
            try:
                api_key = await self.key_resolver.get_client_klaviyo_key(client_id)
                if api_key:
                    logger.info(f"Backfilling client: {client_data.get('name', client_id)}")
                    
                    client_result = await self.backfill_client_data(client_id, metrics, years)
                    
                    results["clients_processed"].append({
                        "client_id": client_id,
                        "name": client_data.get("name"),
                        "data_points": client_result["data_points"],
                        "goals_generated": client_result["goals_generated"]
                    })
                    
                    results["total_data_points"] += client_result["data_points"]
                    results["total_goals_generated"] += client_result["goals_generated"]
                else:
                    logger.warning(f"No API key for client {client_id}")
                    
            except Exception as e:
                logger.error(f"Error backfilling client {client_id}: {e}")
                results["errors"].append({
                    "client_id": client_id,
                    "error": str(e)
                })
        
        return results