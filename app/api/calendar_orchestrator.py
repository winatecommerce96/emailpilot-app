"""
Calendar Orchestrator API - LangChain-powered automated calendar generation
Implements the full calendar automation pipeline with MCP integration
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import logging
import asyncio
import uuid
from google.cloud import firestore

from app.deps import get_db
from app.services.secret_manager import SecretManagerService
from app.deps import get_secret_manager_service
from app.services.mcp_calendar_service import MCPCalendarService

logger = logging.getLogger(__name__)
router = APIRouter()

# Event retrieval endpoint for orchestrator-generated calendars
@router.get("/events/{client_id}")
async def get_orchestrator_events(
    client_id: str,
    year: int,
    month: int,
    version: Optional[int] = None
):
    """Get orchestrator-generated calendar events for a specific client and month"""
    try:
        db = firestore.client()
        
        # Build calendar_id for the specific month
        calendar_id = f"{client_id}_{year}{month:02d}"
        
        logger.info(f"Fetching orchestrator events for calendar_id: {calendar_id}")
        
        # Query for events
        events_ref = db.collection('calendar_events')
        query = events_ref.where('calendar_id', '==', calendar_id)
        
        # Filter by version if specified, otherwise get latest
        if version:
            query = query.where('version', '==', version)
        else:
            query = query.where('latest', '==', True)
        
        # Execute query
        events = []
        for doc in query.stream():
            event_data = doc.to_dict()
            event_data['id'] = doc.id
            
            # Ensure datetime fields are serializable
            if 'planned_send_datetime' in event_data:
                if hasattr(event_data['planned_send_datetime'], 'isoformat'):
                    event_data['planned_send_datetime'] = event_data['planned_send_datetime'].isoformat()
            
            if 'created_at' in event_data:
                if hasattr(event_data['created_at'], 'isoformat'):
                    event_data['created_at'] = event_data['created_at'].isoformat()
            
            events.append(event_data)
        
        # Get the latest import log for metadata
        import_logs = db.collection('calendar_import_logs').where(
            'client_firestore_id', '==', client_id
        ).where(
            'target_year', '==', year
        ).where(
            'target_month', '==', month
        ).order_by('completed_at', direction=firestore.Query.DESCENDING).limit(1).stream()
        
        import_log = None
        for doc in import_logs:
            import_log = doc.to_dict()
            import_log['id'] = doc.id
            # Make dates serializable
            for date_field in ['started_at', 'completed_at']:
                if date_field in import_log and hasattr(import_log[date_field], 'isoformat'):
                    import_log[date_field] = import_log[date_field].isoformat()
        
        # Sort events by planned send datetime
        events.sort(key=lambda x: x.get('planned_send_datetime', ''))
        
        logger.info(f"Retrieved {len(events)} orchestrator events for {calendar_id}")
        
        return {
            "events": events,
            "calendar_id": calendar_id,
            "version": events[0].get('version') if events else None,
            "correlation_id": import_log.get('correlation_id') if import_log else None,
            "import_log": import_log,
            "total_events": len(events)
        }
        
    except Exception as e:
        logger.error(f"Error fetching orchestrator events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Request/Response Models
class CalendarBuildRequest(BaseModel):
    client_display_name: str
    client_firestore_id: str
    klaviyo_account_id: str
    target_month: int  # 1-12
    target_year: int   # YYYY
    dry_run: Optional[bool] = False

class CalendarBuildStatus(BaseModel):
    status: str
    progress: float
    message: str
    current_step: str
    correlation_id: str
    started_at: datetime
    updated_at: datetime

# LangChain Orchestrator Graph Implementation
class CalendarOrchestrator:
    """LangChain-powered calendar automation orchestrator"""
    
    def __init__(self, db: firestore.Client, secret_manager: SecretManagerService):
        self.db = db
        self.secret_manager = secret_manager
        self.status_updates = {}
        self.mcp_service = MCPCalendarService(secret_manager)
        
    async def build_calendar(self, request: CalendarBuildRequest) -> str:
        """Execute the complete calendar automation pipeline"""
        correlation_id = str(uuid.uuid4())
        
        try:
            # Initialize status tracking
            await self._update_status(correlation_id, "initializing", 0.0, "Starting calendar automation pipeline")
            
            # Execute orchestrator graph
            context = await self._execute_orchestrator_graph(request, correlation_id)
            
            # Mark as complete
            await self._update_status(correlation_id, "completed", 100.0, f"Calendar automation complete. Generated {context.get('total_events', 0)} events.")
            
            return correlation_id
            
        except Exception as e:
            logger.error(f"Calendar orchestration failed: {e}")
            await self._update_status(correlation_id, "failed", 0.0, f"Pipeline failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _execute_orchestrator_graph(self, request: CalendarBuildRequest, correlation_id: str) -> Dict[str, Any]:
        """Execute the LangChain orchestrator graph with all nodes"""
        context = {
            "client_display_name": request.client_display_name,
            "client_firestore_id": request.client_firestore_id,
            "klaviyo_account_id": request.klaviyo_account_id,
            "target_month": request.target_month,
            "target_year": request.target_year,
            "dry_run": request.dry_run,
            "correlation_id": correlation_id,
            "started_at": datetime.utcnow()
        }
        
        # Node 1: MCP Selector
        await self._update_status(correlation_id, "mcp_selection", 10.0, "Selecting MCP tools and establishing connections")
        context = await self._node_mcp_selector(context)
        
        # Node 2: Data Fetcher
        await self._update_status(correlation_id, "data_fetching", 25.0, "Fetching historical campaign data from Klaviyo")
        context = await self._node_data_fetcher(context)
        
        # Node 3: Feature Engineer
        await self._update_status(correlation_id, "feature_engineering", 40.0, "Engineering campaign performance features")
        context = await self._node_feature_engineer(context)
        
        # Node 4: Scorer
        await self._update_status(correlation_id, "scoring", 55.0, "Computing performance scores and rankings")
        context = await self._node_scorer(context)
        
        # Node 5: Calendar Strategist (Agent)
        await self._update_status(correlation_id, "strategy_planning", 70.0, "AI strategist planning optimal calendar")
        context = await self._node_calendar_strategist(context)
        
        # Node 6: Calendar Builder
        await self._update_status(correlation_id, "calendar_building", 80.0, "Building concrete calendar events")
        context = await self._node_calendar_builder(context)
        
        # Node 7: Firestore Writer
        await self._update_status(correlation_id, "firestore_writing", 90.0, "Persisting calendar data to Firestore")
        context = await self._node_firestore_writer(context)
        
        # Node 8: Verifier
        await self._update_status(correlation_id, "verification", 95.0, "Verifying calendar data integrity")
        context = await self._node_verifier(context)
        
        return context
    
    async def _node_mcp_selector(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Select and test MCP tools with failover logic"""
        connection_result = await self.mcp_service.select_mcp_with_failover(context["klaviyo_account_id"])
        
        if not connection_result.success:
            raise HTTPException(status_code=500, detail=connection_result.error)
        
        context["selected_mcp"] = connection_result.mcp_name
        context["mcp_auth_context"] = connection_result.auth_context
        context["mcp_response_time"] = connection_result.response_time_ms
        
        logger.info(f"Selected MCP: {connection_result.mcp_name} (response time: {connection_result.response_time_ms}ms)")
        
        return context
    
    async def _node_data_fetcher(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Fetch campaign data for target windows with consistent timezone handling"""
        target_year = context["target_year"]
        target_month = context["target_month"]
        
        # Define time windows
        windows = {
            "current_year": {"year": target_year, "month": target_month},
            "prior_year": {"year": target_year - 1, "month": target_month},
            "prior_2_year": {"year": target_year - 2, "month": target_month},
            "last_30_days": {"days_back": 30}
        }
        
        # Fetch data for each window using enhanced MCP service
        campaign_data = {}
        normalization_map = {}
        fetch_stats = {}
        
        for window_name, window_config in windows.items():
            try:
                fetch_result = await self.mcp_service.fetch_campaign_data(
                    context["selected_mcp"],
                    context["mcp_auth_context"],
                    window_config,
                    context["klaviyo_account_id"]
                )
                
                if fetch_result.success:
                    campaign_data[window_name] = fetch_result.data
                    normalization_map[window_name] = fetch_result.normalization_map
                    fetch_stats[window_name] = {
                        "records_fetched": len(fetch_result.data),
                        "fetch_time_ms": fetch_result.fetch_time_ms
                    }
                    logger.info(f"Fetched {len(fetch_result.data)} campaigns for {window_name}")
                else:
                    logger.warning(f"Failed to fetch {window_name} data: {fetch_result.error}")
                    campaign_data[window_name] = []
                    normalization_map[window_name] = {}
                    fetch_stats[window_name] = {"error": fetch_result.error}
                
            except Exception as e:
                logger.warning(f"Unexpected error fetching {window_name} data: {e}")
                campaign_data[window_name] = []
                normalization_map[window_name] = {}
                fetch_stats[window_name] = {"error": str(e)}
        
        context["campaign_data"] = campaign_data
        context["normalization_map"] = normalization_map
        context["time_windows"] = windows
        context["fetch_stats"] = fetch_stats
        
        return context
    
    async def _node_feature_engineer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Engineer features from campaign data"""
        engineered_features = {}
        
        for window_name, campaigns in context["campaign_data"].items():
            features = []
            
            for campaign in campaigns:
                try:
                    feature_set = {
                        "campaign_id": campaign.get("campaign_id"),
                        "campaign_name": campaign.get("campaign_name"),
                        "send_datetime": campaign.get("send_datetime"),
                        "channel": campaign.get("channel", "email"),
                        
                        # Performance metrics
                        "sends": campaign.get("sends", 0),
                        "delivered": campaign.get("delivered", 0),
                        "open_rate": campaign.get("open_rate", 0.0),
                        "click_rate": campaign.get("click_rate", 0.0),
                        "placed_order_count": campaign.get("placed_order_count", 0),
                        "placed_order_revenue": campaign.get("placed_order_revenue", 0.0),
                        "revenue_per_recipient": campaign.get("revenue_per_recipient", 0.0),
                        "unsubscribes": campaign.get("unsubscribes", 0),
                        "spam_complaints": campaign.get("spam_complaints", 0),
                        
                        # Engineered features
                        "weekday": self._extract_weekday(campaign.get("send_datetime")),
                        "hour_bucket": self._extract_hour_bucket(campaign.get("send_datetime")),
                        "offer_type": self._extract_offer_type(campaign.get("campaign_name", "")),
                        "subject_patterns": self._extract_subject_patterns(campaign.get("campaign_name", "")),
                        "window": window_name
                    }
                    
                    features.append(feature_set)
                    
                except Exception as e:
                    logger.warning(f"Feature engineering failed for campaign: {e}")
                    continue
            
            engineered_features[window_name] = features
        
        context["engineered_features"] = engineered_features
        return context
    
    async def _node_scorer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Compute composite performance scores"""
        all_campaigns = []
        for window_features in context["engineered_features"].values():
            all_campaigns.extend(window_features)
        
        # Compute performance distributions
        if all_campaigns:
            revenue_scores = [c["revenue_per_recipient"] for c in all_campaigns if c["revenue_per_recipient"] > 0]
            order_scores = [c["placed_order_count"] for c in all_campaigns if c["placed_order_count"] > 0]
            
            # Calculate percentiles for scoring
            import statistics
            revenue_p90 = statistics.quantiles(revenue_scores, n=10)[-1] if revenue_scores else 1.0
            order_p90 = statistics.quantiles(order_scores, n=10)[-1] if order_scores else 1.0
            
            # Score each campaign
            for campaign in all_campaigns:
                composite_score = (
                    (campaign["revenue_per_recipient"] / revenue_p90) * 0.6 +
                    (campaign["placed_order_count"] / order_p90) * 0.4
                )
                campaign["composite_score"] = min(composite_score, 2.0)  # Cap at 2x
                campaign["performance_tier"] = self._determine_performance_tier(composite_score)
        
        # Separate email vs SMS performance
        email_campaigns = [c for c in all_campaigns if c["channel"] == "email"]
        sms_campaigns = [c for c in all_campaigns if c["channel"] == "sms"]
        
        context["scored_campaigns"] = {
            "all": all_campaigns,
            "email": email_campaigns,
            "sms": sms_campaigns
        }
        
        # Compute insights
        context["performance_insights"] = await self._compute_performance_insights(all_campaigns)
        
        return context
    
    async def _node_calendar_strategist(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: AI agent for calendar strategy decisions"""
        # Get client profile for context
        client_profile = await self._get_client_profile(context["client_firestore_id"])
        
        # Prepare context for strategist agent
        strategist_context = {
            "client_profile": client_profile,
            "performance_insights": context["performance_insights"],
            "target_month": context["target_month"],
            "target_year": context["target_year"],
            "historical_data_available": len(context["scored_campaigns"]["all"]) > 0
        }
        
        # Apply default strategy (20 email / 5 SMS) with adjustments
        if not strategist_context["historical_data_available"]:
            # Conservative plan for new clients
            strategy = {
                "total_emails": 12,
                "total_sms": 3,
                "send_cap_per_day": 1,
                "cooldown_hours": 24,
                "preferred_days": ["Tuesday", "Wednesday", "Thursday"],
                "preferred_hours": [10, 14, 16],
                "channel_mix": {"email": 0.8, "sms": 0.2},
                "themes": ["nurturing", "education", "community"],
                "reason": "Conservative plan - limited historical data"
            }
        else:
            # Data-driven strategy
            insights = context["performance_insights"]
            strategy = {
                "total_emails": 20,
                "total_sms": 5,
                "send_cap_per_day": 1,
                "cooldown_hours": 24,
                "preferred_days": insights.get("best_weekdays", ["Tuesday", "Wednesday", "Thursday"]),
                "preferred_hours": insights.get("best_hours", [10, 14, 16]),
                "channel_mix": {"email": 0.8, "sms": 0.2},
                "themes": insights.get("top_themes", ["cheese_club", "rrb", "sms_alert"]),
                "reason": "Data-driven strategy based on historical performance"
            }
        
        context["calendar_strategy"] = strategy
        return context
    
    async def _node_calendar_builder(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Build concrete calendar events"""
        strategy = context["calendar_strategy"]
        target_month = context["target_month"]
        target_year = context["target_year"]
        
        # Calculate days in target month
        if target_month == 12:
            next_month = datetime(target_year + 1, 1, 1)
        else:
            next_month = datetime(target_year, target_month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        
        events = []
        
        # Build email events
        email_dates = self._distribute_events(
            strategy["total_emails"],
            last_day,
            strategy["preferred_days"],
            strategy["send_cap_per_day"]
        )
        
        for i, date in enumerate(email_dates):
            event = {
                "title": self._generate_email_title(strategy["themes"], i),
                "description": self._generate_email_description(strategy["themes"], i),
                "planned_send_datetime": datetime(target_year, target_month, date, 
                                                strategy["preferred_hours"][i % len(strategy["preferred_hours"])]).isoformat(),
                "channel": "email",
                "event_type": "email",
                "audience_segment": "all_subscribers",
                "expected_kpi_band": self._predict_kpi_band(context["performance_insights"], "email"),
                "source": "EmailPilot AI Calendar",
                "color": "bg-blue-200 text-blue-800"
            }
            events.append(event)
        
        # Build SMS events
        sms_dates = self._distribute_events(
            strategy["total_sms"],
            last_day,
            strategy["preferred_days"],
            1,  # Max 1 SMS per day
            offset_from_email=True
        )
        
        for i, date in enumerate(sms_dates):
            event = {
                "title": self._generate_sms_title(strategy["themes"], i),
                "description": self._generate_sms_description(strategy["themes"], i),
                "planned_send_datetime": datetime(target_year, target_month, date, 
                                                strategy["preferred_hours"][i % len(strategy["preferred_hours"])]).isoformat(),
                "channel": "sms",
                "event_type": "sms",
                "audience_segment": "sms_subscribers",
                "expected_kpi_band": self._predict_kpi_band(context["performance_insights"], "sms"),
                "source": "EmailPilot AI Calendar",
                "color": "bg-orange-300 text-orange-800"
            }
            events.append(event)
        
        context["generated_events"] = events
        context["total_events"] = len(events)
        
        return context
    
    async def _node_firestore_writer(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Write calendar data to Firestore with versioning"""
        if context["dry_run"]:
            logger.info("DRY RUN: Skipping Firestore writes")
            context["write_results"] = {"dry_run": True, "events_written": 0, "logs_written": 0}
            return context
        
        # Generate idempotent calendar_id
        calendar_id = f"{context['client_firestore_id']}_{context['target_year']}{context['target_month']:02d}"
        
        # Check for existing calendar and increment version
        existing_calendars = self.db.collection('calendar_events').where('calendar_id', '==', calendar_id).stream()
        version = 1
        for doc in existing_calendars:
            data = doc.to_dict()
            if data and 'version' in data:
                version = max(version, data['version'] + 1)
        
        # Write import logs
        import_log = {
            "client_firestore_id": context["client_firestore_id"],
            "klaviyo_account_id": context["klaviyo_account_id"],
            "target_month": context["target_month"],
            "target_year": context["target_year"],
            "time_windows": context["time_windows"],
            "source_mcp_used": context["selected_mcp"],
            "normalization_map": context["normalization_map"],
            "stats_summary": {
                "total_historical_campaigns": len(context["scored_campaigns"]["all"]),
                "generated_events": context["total_events"],
                "strategy_reason": context["calendar_strategy"]["reason"]
            },
            "started_at": context["started_at"],
            "completed_at": datetime.utcnow(),
            "status": "completed",
            "correlation_id": context["correlation_id"],
            "version": version
        }
        
        log_ref = self.db.collection('calendar_import_logs').add(import_log)
        
        # Write calendar events
        events_written = 0
        for i, event in enumerate(context["generated_events"]):
            event_data = {
                **event,
                "client_firestore_id": context["client_firestore_id"],
                "calendar_id": calendar_id,
                "event_id": f"{calendar_id}_event_{i+1:03d}",
                "version": version,
                "latest": True,
                "created_at": datetime.utcnow()
            }
            
            self.db.collection('calendar_events').add(event_data)
            events_written += 1
        
        # Mark previous versions as not latest
        if version > 1:
            old_events = self.db.collection('calendar_events').where('calendar_id', '==', calendar_id).where('version', '<', version).stream()
            for doc in old_events:
                doc.reference.update({"latest": False})
        
        context["write_results"] = {
            "events_written": events_written,
            "logs_written": 1,
            "calendar_id": calendar_id,
            "version": version,
            "import_log_id": log_ref[1].id
        }
        
        return context
    
    async def _node_verifier(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Node: Verify written data integrity"""
        if context["dry_run"]:
            context["verification_results"] = {"dry_run": True, "verified": True}
            return context
        
        write_results = context["write_results"]
        calendar_id = write_results["calendar_id"]
        version = write_results["version"]
        
        # Verify events written
        written_events = list(self.db.collection('calendar_events')
                            .where('calendar_id', '==', calendar_id)
                            .where('version', '==', version)
                            .stream())
        
        events_count = len(written_events)
        expected_count = context["total_events"]
        
        # Verify import log
        log_doc = self.db.collection('calendar_import_logs').document(write_results["import_log_id"]).get()
        log_exists = log_doc.exists
        
        # Schema compatibility check
        schema_compatible = True
        for doc in written_events[:3]:  # Sample check
            data = doc.to_dict()
            required_fields = ["title", "planned_send_datetime", "channel", "source"]
            if not all(field in data for field in required_fields):
                schema_compatible = False
                break
        
        verification_results = {
            "events_verified": events_count == expected_count,
            "events_count": events_count,
            "expected_count": expected_count,
            "log_verified": log_exists,
            "schema_compatible": schema_compatible,
            "verified": events_count == expected_count and log_exists and schema_compatible
        }
        
        context["verification_results"] = verification_results
        
        if not verification_results["verified"]:
            raise HTTPException(status_code=500, detail=f"Verification failed: {verification_results}")
        
        return context
    
    # Helper methods
    async def _update_status(self, correlation_id: str, status: str, progress: float, message: str):
        """Update pipeline status for streaming"""
        status_update = CalendarBuildStatus(
            status=status,
            progress=progress,
            message=message,
            current_step=status,
            correlation_id=correlation_id,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.status_updates[correlation_id] = status_update
        logger.info(f"[{correlation_id}] {status}: {message} ({progress}%)")
    
    async def _test_mcp_connection(self, mcp_name: str, klaviyo_account_id: str) -> bool:
        """Test MCP connection with exponential backoff"""
        # Implementation would test actual MCP endpoints
        # For now, simulate success for known MCPs
        known_mcps = ["klaviyo_mcp", "openapi_mcp", "firestore_mcp"]
        return mcp_name in known_mcps
    
    async def _get_mcp_auth_context(self, mcp_name: str, klaviyo_account_id: str) -> Dict[str, Any]:
        """Get authentication context for selected MCP"""
        return {
            "mcp_name": mcp_name,
            "klaviyo_account_id": klaviyo_account_id,
            "authenticated": True
        }
    
    async def _fetch_window_data(self, mcp_name: str, auth_context: Dict[str, Any], 
                                window_config: Dict[str, Any], klaviyo_account_id: str) -> List[Dict[str, Any]]:
        """Fetch campaign data for a specific time window"""
        # Placeholder implementation - would integrate with actual MCP tools
        # Return sample data structure
        return [
            {
                "campaign_id": f"camp_{i}",
                "campaign_name": f"Sample Campaign {i}",
                "send_datetime": "2024-01-15T10:00:00Z",
                "channel": "email",
                "sends": 1000,
                "delivered": 980,
                "open_rate": 0.25,
                "click_rate": 0.05,
                "placed_order_count": 15,
                "placed_order_revenue": 750.0,
                "revenue_per_recipient": 0.75,
                "unsubscribes": 2,
                "spam_complaints": 0
            }
            for i in range(5)  # Sample data
        ]
    
    async def _normalize_campaign_data(self, raw_data: List[Dict[str, Any]]) -> tuple:
        """Normalize field names across different MCP responses"""
        # Define field mappings
        field_mappings = {
            "revenue_per_recipient": ["revenue_per_recipient", "rpr", "avg_revenue"],
            "placed_order_count": ["placed_order_count", "orders", "conversions"],
            "placed_order_revenue": ["placed_order_revenue", "revenue", "total_revenue"]
        }
        
        normalized_data = []
        normalization_map = {}
        
        for record in raw_data:
            normalized_record = {}
            for standard_field, possible_fields in field_mappings.items():
                for field in possible_fields:
                    if field in record:
                        normalized_record[standard_field] = record[field]
                        normalization_map[standard_field] = field
                        break
                else:
                    normalized_record[standard_field] = 0  # Default value
            
            # Copy other fields as-is
            for field, value in record.items():
                if field not in [f for fields in field_mappings.values() for f in fields]:
                    normalized_record[field] = value
            
            normalized_data.append(normalized_record)
        
        return normalized_data, normalization_map
    
    def _extract_weekday(self, send_datetime: str) -> int:
        """Extract weekday from datetime string"""
        try:
            dt = datetime.fromisoformat(send_datetime.replace('Z', '+00:00'))
            return dt.weekday()  # 0=Monday, 6=Sunday
        except:
            return 1  # Default to Tuesday
    
    def _extract_hour_bucket(self, send_datetime: str) -> str:
        """Extract hour bucket from datetime"""
        try:
            dt = datetime.fromisoformat(send_datetime.replace('Z', '+00:00'))
            hour = dt.hour
            if 6 <= hour < 12:
                return "morning"
            elif 12 <= hour < 18:
                return "afternoon"
            elif 18 <= hour < 22:
                return "evening"
            else:
                return "night"
        except:
            return "morning"
    
    def _extract_offer_type(self, campaign_name: str) -> str:
        """Extract offer type from campaign name"""
        name_lower = campaign_name.lower()
        if "cheese club" in name_lower:
            return "cheese_club"
        elif "rrb" in name_lower or "red ribbon" in name_lower:
            return "rrb"
        elif "flash" in name_lower or "sale" in name_lower:
            return "flash_sale"
        elif "nurtur" in name_lower:
            return "nurturing"
        else:
            return "general"
    
    def _extract_subject_patterns(self, campaign_name: str) -> List[str]:
        """Extract subject line patterns"""
        patterns = []
        name_lower = campaign_name.lower()
        
        if "%" in name_lower or "off" in name_lower:
            patterns.append("discount")
        if "limited" in name_lower or "exclusive" in name_lower:
            patterns.append("urgency")
        if "new" in name_lower:
            patterns.append("newness")
        if "free" in name_lower:
            patterns.append("free_offer")
        
        return patterns or ["general"]
    
    def _determine_performance_tier(self, composite_score: float) -> str:
        """Determine performance tier based on composite score"""
        if composite_score >= 1.5:
            return "high"
        elif composite_score >= 0.8:
            return "medium"
        else:
            return "low"
    
    async def _compute_performance_insights(self, campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute performance insights from campaign data"""
        if not campaigns:
            return {
                "best_weekdays": ["Tuesday", "Wednesday", "Thursday"],
                "best_hours": [10, 14, 16],
                "top_themes": ["nurturing", "education"]
            }
        
        # Analyze weekday performance
        weekday_performance = {}
        for campaign in campaigns:
            weekday = campaign.get("weekday", 1)
            score = campaign.get("composite_score", 0)
            if weekday not in weekday_performance:
                weekday_performance[weekday] = []
            weekday_performance[weekday].append(score)
        
        # Find best weekdays
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        best_weekdays = []
        for weekday, scores in weekday_performance.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score > 0.8:  # Threshold for "good" performance
                best_weekdays.append(weekday_names[weekday])
        
        if not best_weekdays:
            best_weekdays = ["Tuesday", "Wednesday", "Thursday"]
        
        return {
            "best_weekdays": best_weekdays,
            "best_hours": [10, 14, 16],  # Default for now
            "top_themes": ["cheese_club", "rrb", "nurturing"]
        }
    
    async def _get_client_profile(self, client_firestore_id: str) -> Dict[str, Any]:
        """Get client profile from Firestore"""
        try:
            doc = self.db.collection('clients').document(client_firestore_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.warning(f"Failed to get client profile: {e}")
        
        return {"name": "Unknown Client", "client_voice": "professional", "timezone": "UTC"}
    
    def _distribute_events(self, total_events: int, days_in_month: int, 
                          preferred_days: List[str], max_per_day: int, 
                          offset_from_email: bool = False) -> List[int]:
        """Distribute events across month respecting constraints"""
        weekday_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        preferred_weekdays = [weekday_map.get(day, 1) for day in preferred_days]
        selected_dates = []
        
        # Generate candidate dates
        candidates = []
        for day in range(1, days_in_month + 1):
            weekday = datetime(2024, 1, day).weekday()  # Use any year for weekday calc
            if weekday in preferred_weekdays:
                candidates.append(day)
        
        # Distribute events evenly
        if candidates:
            interval = len(candidates) // total_events if total_events > 0 else 1
            interval = max(1, interval)
            
            for i in range(total_events):
                if i * interval < len(candidates):
                    selected_dates.append(candidates[i * interval])
                elif candidates:
                    selected_dates.append(candidates[i % len(candidates)])
        
        return selected_dates[:total_events]
    
    def _generate_email_title(self, themes: List[str], index: int) -> str:
        """Generate email campaign title"""
        templates = {
            "cheese_club": ["Monthly Cheese Club Selection", "Artisan Cheese Discovery", "Premium Cheese Collection"],
            "rrb": ["Red Ribbon Box Special", "RRB Monthly Favorites", "Curated RRB Selection"],
            "nurturing": ["Gourmet Tips & Recipes", "Cheese Pairing Guide", "Artisan Spotlight"],
            "education": ["Cheese Making Insights", "From Farm to Table", "Seasonal Selections"]
        }
        
        theme = themes[index % len(themes)] if themes else "nurturing"
        template_list = templates.get(theme, templates["nurturing"])
        
        return template_list[index % len(template_list)]
    
    def _generate_email_description(self, themes: List[str], index: int) -> str:
        """Generate email campaign description"""
        return f"Email campaign focusing on {themes[index % len(themes)] if themes else 'customer engagement'}"
    
    def _generate_sms_title(self, themes: List[str], index: int) -> str:
        """Generate SMS campaign title"""
        sms_templates = [
            "Flash Sale Alert", "Limited Time Offer", "New Arrival Notice", 
            "Member Exclusive", "Quick Reminder"
        ]
        return sms_templates[index % len(sms_templates)]
    
    def _generate_sms_description(self, themes: List[str], index: int) -> str:
        """Generate SMS campaign description"""
        return f"SMS alert for {themes[index % len(themes)] if themes else 'special promotion'}"
    
    def _predict_kpi_band(self, insights: Dict[str, Any], channel: str) -> str:
        """Predict KPI performance band"""
        # Simple prediction logic - could be enhanced with ML
        if channel == "sms":
            return "medium"  # SMS generally performs well
        return "low"  # Conservative estimate for email

# Global orchestrator instance
orchestrator_instance = None

def get_orchestrator(
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> CalendarOrchestrator:
    """Get orchestrator instance"""
    global orchestrator_instance
    if orchestrator_instance is None:
        orchestrator_instance = CalendarOrchestrator(db, secret_manager)
    return orchestrator_instance

# API Endpoints
@router.post("/build")
async def build_calendar(
    request: CalendarBuildRequest,
    background_tasks: BackgroundTasks,
    orchestrator: CalendarOrchestrator = Depends(get_orchestrator)
):
    """
    Build automated calendar using LangChain orchestrator
    Returns correlation_id for tracking progress
    """
    try:
        correlation_id = await orchestrator.build_calendar(request)
        
        return {
            "success": True,
            "correlation_id": correlation_id,
            "message": "Calendar automation started",
            "status_endpoint": f"/api/calendar/build/status/{correlation_id}"
        }
        
    except Exception as e:
        logger.error(f"Calendar build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/build/status/{correlation_id}")
async def get_build_status(
    correlation_id: str,
    orchestrator: CalendarOrchestrator = Depends(get_orchestrator)
):
    """Get calendar build status"""
    status = orchestrator.status_updates.get(correlation_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    
    return status.dict()

@router.get("/build/stream/{correlation_id}")
async def stream_build_status(
    correlation_id: str,
    orchestrator: CalendarOrchestrator = Depends(get_orchestrator)
):
    """Stream calendar build status updates"""
    async def generate_status_stream():
        while True:
            status = orchestrator.status_updates.get(correlation_id)
            if status:
                yield f"data: {status.json()}\n\n"
                
                if status.status in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(generate_status_stream(), media_type="text/plain")

@router.get("/health")
async def calendar_orchestrator_health():
    """Health check for calendar orchestrator"""
    return {
        "status": "healthy",
        "service": "calendar_orchestrator",
        "timestamp": datetime.utcnow().isoformat()
    }