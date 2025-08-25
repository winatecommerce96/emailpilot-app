"""
LangChain Orchestration API
Handles dynamic variable discovery and MCP-to-Agent orchestration
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from google.cloud import firestore
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/langchain/orchestration", tags=["LangChain Orchestration"])


class OrchestrationConfig(BaseModel):
    """Configuration for MCP to Agent orchestration."""
    name: str = Field(..., description="Orchestration name")
    description: str = Field(..., description="What this orchestration does")
    mcp_server: str = Field(..., description="MCP server ID (e.g., klaviyo_revenue)")
    agent_id: str = Field(..., description="Target agent ID (e.g., revenue_analyst)")
    trigger_type: str = Field(..., description="Trigger type: webhook, schedule, event, manual")
    trigger_config: Dict[str, Any] = Field(default_factory=dict, description="Trigger configuration")
    data_mapping: Dict[str, str] = Field(default_factory=dict, description="Map MCP data to agent variables")
    filters: List[Dict[str, Any]] = Field(default_factory=list, description="Data filters")
    transformations: List[Dict[str, Any]] = Field(default_factory=list, description="Data transformations")
    enabled: bool = Field(default=True, description="Whether orchestration is active")


class VariableSource(BaseModel):
    """Represents a source of variables."""
    source_type: str  # firestore, mcp, static, api
    source_name: str  # e.g., clients, klaviyo_revenue
    fields: List[Dict[str, Any]]  # Available fields with metadata


# In-memory orchestration storage (use Firestore in production)
orchestrations = {}


@router.get("/variables/{context}")
async def discover_variables(
    context: str,
    client_id: Optional[str] = Query(None, description="Client ID for context-specific variables"),
    include_mcp: bool = Query(True, description="Include MCP server variables"),
    include_firestore: bool = Query(True, description="Include Firestore collections")
) -> Dict[str, Any]:
    """
    Discover available variables from multiple sources.
    
    Args:
        context: Context for variable discovery (e.g., 'agent', 'prompt', 'all')
        client_id: Optional client ID for client-specific variables
        include_mcp: Whether to include MCP server variables
        include_firestore: Whether to include Firestore variables
    
    Returns:
        Dictionary of variable sources and their available fields
    """
    sources = []
    
    # 1. Firestore Client Variables
    if include_firestore:
        try:
            db = firestore.Client()
            
            # Get client-specific variables
            if client_id:
                client_ref = db.collection('clients').document(client_id)
                client_doc = client_ref.get()
                
                if client_doc.exists:
                    client_data = client_doc.to_dict()
                    client_fields = []
                    
                    # Enhanced field descriptions for client-specific variables
                    field_descriptions = {
                        "name": "Client company name",
                        "client_slug": "URL-safe client identifier",
                        "description": "Client business description",
                        "contact_email": "Primary contact email",
                        "contact_name": "Primary contact person",
                        "website": "Client website URL",
                        "is_active": "Whether client is currently active",
                        "klaviyo_api_key_secret": "Secret Manager reference to Klaviyo API key (DO NOT expose actual key)",
                        "metric_id": "Klaviyo metric ID for revenue tracking",
                        "klaviyo_account_id": "Klaviyo account identifier",
                        "client_voice": "Brand voice and communication style guidelines",
                        "client_background": "Company background, history, and values",
                        "asana_project_link": "Link to Asana project for this client",
                        "affinity_segment_1_name": "First customer affinity segment name",
                        "affinity_segment_1_definition": "Definition and criteria for first affinity segment",
                        "affinity_segment_2_name": "Second customer affinity segment name",
                        "affinity_segment_2_definition": "Definition and criteria for second affinity segment",
                        "affinity_segment_3_name": "Third customer affinity segment name",
                        "affinity_segment_3_definition": "Definition and criteria for third affinity segment",
                        "key_growth_objective": "Primary growth objective for this client",
                        "timezone": "Client timezone for campaign scheduling",
                        "created_at": "When client record was created",
                        "updated_at": "When client record was last updated",
                        "created_by": "User who created the client record",
                        "updated_by": "User who last updated the client record"
                    }
                    
                    # Extract all fields from client document
                    for key, value in client_data.items():
                        field_type = type(value).__name__
                        description = field_descriptions.get(key, f"Client {key.replace('_', ' ').title()}")
                        
                        # Determine category based on field name
                        if key in ["name", "client_slug", "description", "contact_email", "contact_name", "website", "is_active"]:
                            category = "basic"
                        elif key in ["klaviyo_api_key_secret", "metric_id", "klaviyo_account_id"]:
                            category = "api"
                        elif key in ["client_voice", "client_background"]:
                            category = "brand"
                        elif key in ["asana_project_link"]:
                            category = "pm"
                        elif "affinity_segment" in key:
                            category = "segmentation"
                        elif key in ["key_growth_objective", "timezone"]:
                            category = "growth"
                        elif key in ["created_at", "updated_at", "created_by", "updated_by"]:
                            category = "metadata"
                        else:
                            category = "other"
                            
                        client_fields.append({
                            "name": f"client.{key}",
                            "type": field_type,
                            "category": category,
                            "description": description,
                            "sample_value": str(value)[:100] if value and key != "klaviyo_api_key_secret" else "[SECURE_REFERENCE]" if key == "klaviyo_api_key_secret" else None,
                            "source": "firestore.clients",
                            "is_secure": key == "klaviyo_api_key_secret"
                        })
                    
                    sources.append(VariableSource(
                        source_type="firestore",
                        source_name="clients",
                        fields=client_fields
                    ))
            
            # Get general client schema (from any client)
            else:
                clients_ref = db.collection('clients').limit(1)
                sample_client = list(clients_ref.stream())
                
                if sample_client:
                    sample_data = sample_client[0].to_dict()
                    schema_fields = []
                    
                    # Updated client fields schema - matches unified Firestore structure
                    standard_fields = {
                        # Basic Info
                        "name": {"type": "string", "category": "basic", "description": "Client company name"},
                        "client_slug": {"type": "string", "category": "basic", "description": "URL-safe client identifier"},
                        "description": {"type": "string", "category": "basic", "description": "Client business description"},
                        "contact_email": {"type": "string", "category": "basic", "description": "Primary contact email"},
                        "contact_name": {"type": "string", "category": "basic", "description": "Primary contact person"},
                        "website": {"type": "string", "category": "basic", "description": "Client website URL"},
                        "is_active": {"type": "boolean", "category": "basic", "description": "Whether client is currently active"},
                        
                        # API Integration
                        "klaviyo_api_key_secret": {"type": "string", "category": "api", "description": "Secret Manager reference to Klaviyo API key (not the actual key)"},
                        "metric_id": {"type": "string", "category": "api", "description": "Klaviyo metric ID for revenue tracking"},
                        "klaviyo_account_id": {"type": "string", "category": "api", "description": "Klaviyo account identifier"},
                        
                        # Brand Manager Context
                        "client_voice": {"type": "string", "category": "brand", "description": "Brand voice and communication style guidelines"},
                        "client_background": {"type": "string", "category": "brand", "description": "Company background, history, and values"},
                        
                        # Project Management
                        "asana_project_link": {"type": "string", "category": "pm", "description": "Link to Asana project for this client"},
                        
                        # Affinity Segments (Customer Segmentation)
                        "affinity_segment_1_name": {"type": "string", "category": "segmentation", "description": "First customer affinity segment name"},
                        "affinity_segment_1_definition": {"type": "string", "category": "segmentation", "description": "Definition and criteria for first affinity segment"},
                        "affinity_segment_2_name": {"type": "string", "category": "segmentation", "description": "Second customer affinity segment name"},
                        "affinity_segment_2_definition": {"type": "string", "category": "segmentation", "description": "Definition and criteria for second affinity segment"},
                        "affinity_segment_3_name": {"type": "string", "category": "segmentation", "description": "Third customer affinity segment name"},
                        "affinity_segment_3_definition": {"type": "string", "category": "segmentation", "description": "Definition and criteria for third affinity segment"},
                        
                        # Growth Strategy
                        "key_growth_objective": {"type": "string", "category": "growth", "description": "Primary growth objective for this client"},
                        "timezone": {"type": "string", "category": "growth", "description": "Client timezone for campaign scheduling"},
                        
                        # Metadata (auto-managed)
                        "created_at": {"type": "timestamp", "category": "metadata", "description": "When client record was created"},
                        "updated_at": {"type": "timestamp", "category": "metadata", "description": "When client record was last updated"},
                        "created_by": {"type": "string", "category": "metadata", "description": "User who created the client record"},
                        "updated_by": {"type": "string", "category": "metadata", "description": "User who last updated the client record"}
                    }
                    
                    for field_name, field_info in standard_fields.items():
                        schema_fields.append({
                            "name": f"client.{field_name}",
                            "type": field_info["type"],
                            "category": field_info["category"],
                            "description": field_info["description"],
                            "source": "firestore.clients"
                        })
                    
                    sources.append(VariableSource(
                        source_type="firestore",
                        source_name="clients_schema",
                        fields=schema_fields
                    ))
            
            # Get goals collection variables
            goals_fields = [
                {"name": "goals.revenue_goal", "type": "number", "description": "Monthly revenue goal"},
                {"name": "goals.email_goal", "type": "number", "description": "Monthly email send goal"},
                {"name": "goals.open_rate_goal", "type": "number", "description": "Target open rate"},
                {"name": "goals.click_rate_goal", "type": "number", "description": "Target click rate"},
                {"name": "goals.conversion_rate_goal", "type": "number", "description": "Target conversion rate"}
            ]
            
            sources.append(VariableSource(
                source_type="firestore",
                source_name="goals",
                fields=goals_fields
            ))
            
            # Get performance metrics variables
            performance_fields = [
                {"name": "performance.mtd_revenue", "type": "number", "description": "Month-to-date revenue"},
                {"name": "performance.mtd_orders", "type": "number", "description": "Month-to-date orders"},
                {"name": "performance.mtd_emails_sent", "type": "number", "description": "Month-to-date emails sent"},
                {"name": "performance.avg_order_value", "type": "number", "description": "Average order value"},
                {"name": "performance.open_rate", "type": "number", "description": "Current open rate"},
                {"name": "performance.click_rate", "type": "number", "description": "Current click rate"}
            ]
            
            sources.append(VariableSource(
                source_type="firestore",
                source_name="performance",
                fields=performance_fields
            ))
            
        except Exception as e:
            logger.error(f"Error discovering Firestore variables: {e}")
    
    # 2. MCP Server Variables
    if include_mcp:
        mcp_sources = {
            "klaviyo_revenue": {
                "name": "Klaviyo Revenue API",
                "fields": [
                    {"name": "mcp.revenue_7d", "type": "number", "description": "7-day revenue"},
                    {"name": "mcp.revenue_30d", "type": "number", "description": "30-day revenue"},
                    {"name": "mcp.orders_7d", "type": "number", "description": "7-day order count"},
                    {"name": "mcp.orders_30d", "type": "number", "description": "30-day order count"},
                    {"name": "mcp.aov_7d", "type": "number", "description": "7-day average order value"},
                    {"name": "mcp.top_campaigns", "type": "array", "description": "Top performing campaigns"},
                    {"name": "mcp.top_flows", "type": "array", "description": "Top performing flows"}
                ]
            },
            "performance_api": {
                "name": "Performance Metrics API",
                "fields": [
                    {"name": "mcp.email_performance", "type": "object", "description": "Email performance metrics"},
                    {"name": "mcp.segment_performance", "type": "object", "description": "Segment performance data"},
                    {"name": "mcp.campaign_roi", "type": "number", "description": "Campaign ROI"},
                    {"name": "mcp.list_growth_rate", "type": "number", "description": "List growth rate"}
                ]
            },
            "email_sms": {
                "name": "Email/SMS MCP",
                "fields": [
                    {"name": "mcp.scheduled_campaigns", "type": "array", "description": "Scheduled campaigns"},
                    {"name": "mcp.draft_templates", "type": "array", "description": "Draft email templates"},
                    {"name": "mcp.sms_credits", "type": "number", "description": "SMS credits remaining"},
                    {"name": "mcp.campaign_calendar", "type": "object", "description": "Campaign calendar data"}
                ]
            }
        }
        
        for server_id, server_info in mcp_sources.items():
            sources.append(VariableSource(
                source_type="mcp",
                source_name=server_id,
                fields=server_info["fields"]
            ))
    
    # 3. System Variables
    system_fields = [
        {"name": "system.current_date", "type": "string", "description": "Current date (YYYY-MM-DD)"},
        {"name": "system.current_month", "type": "string", "description": "Current month (YYYY-MM)"},
        {"name": "system.current_year", "type": "number", "description": "Current year"},
        {"name": "system.user_email", "type": "string", "description": "Current user email"},
        {"name": "system.user_name", "type": "string", "description": "Current user name"}
    ]
    
    sources.append(VariableSource(
        source_type="system",
        source_name="system",
        fields=system_fields
    ))
    
    # Compile all variables
    all_variables = []
    categories = {}
    
    for source in sources:
        all_variables.extend(source.fields)
        # Group variables by category for easier navigation
        for field in source.fields:
            category = field.get("category", "uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(field)
    
    return {
        "context": context,
        "client_id": client_id,
        "sources": [s.dict() for s in sources],
        "total_variables": len(all_variables),
        "variables": all_variables,
        "categories": categories,
        "client_schema_version": "2025-08-20",  # Track schema updates
        "notes": {
            "klaviyo_api_key_secret": "This field contains a Secret Manager reference, not the actual API key",
            "affinity_segments": "Customer segmentation data for targeted campaigns",
            "brand_context": "Use client_voice and client_background for brand-appropriate content generation",
            "security": "Never expose actual API keys or secret references in responses"
        }
    }


@router.post("/orchestrations")
async def create_orchestration(config: OrchestrationConfig) -> Dict[str, Any]:
    """
    Create a new MCP-to-Agent orchestration.
    
    Example orchestration:
    - MCP server ingests Klaviyo revenue data
    - Filters for specific conditions (e.g., revenue drop > 20%)
    - Triggers revenue_analyst agent with context
    - Agent analyzes and generates insights
    """
    try:
        # Generate ID
        orch_id = f"orch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Store orchestration
        orchestrations[orch_id] = {
            "id": orch_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            **config.dict()
        }
        
        # In production, save to Firestore
        try:
            db = firestore.Client()
            db.collection("orchestrations").document(orch_id).set(orchestrations[orch_id])
        except Exception as e:
            logger.warning(f"Could not save to Firestore: {e}")
        
        return {
            "success": True,
            "orchestration_id": orch_id,
            "message": f"Orchestration '{config.name}' created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orchestrations")
async def list_orchestrations(
    mcp_server: Optional[str] = Query(None, description="Filter by MCP server"),
    agent_id: Optional[str] = Query(None, description="Filter by agent"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status")
) -> List[Dict[str, Any]]:
    """List all orchestrations with optional filters."""
    try:
        # Try to load from Firestore first
        try:
            db = firestore.Client()
            query = db.collection("orchestrations")
            
            if mcp_server:
                query = query.where("mcp_server", "==", mcp_server)
            if agent_id:
                query = query.where("agent_id", "==", agent_id)
            if enabled is not None:
                query = query.where("enabled", "==", enabled)
            
            docs = query.stream()
            result = []
            for doc in docs:
                orch_data = doc.to_dict()
                orch_data["id"] = doc.id
                result.append(orch_data)
            
            return result
        except:
            # Fallback to in-memory
            result = list(orchestrations.values())
            
            if mcp_server:
                result = [o for o in result if o.get("mcp_server") == mcp_server]
            if agent_id:
                result = [o for o in result if o.get("agent_id") == agent_id]
            if enabled is not None:
                result = [o for o in result if o.get("enabled") == enabled]
            
            return result
    except Exception as e:
        logger.error(f"Error listing orchestrations: {e}")
        return []


@router.get("/orchestrations/{orchestration_id}")
async def get_orchestration(orchestration_id: str) -> Dict[str, Any]:
    """Get details of a specific orchestration."""
    try:
        # Try Firestore first
        try:
            db = firestore.Client()
            doc = db.collection("orchestrations").document(orchestration_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
        except:
            pass
        
        # Fallback to in-memory
        if orchestration_id in orchestrations:
            return orchestrations[orchestration_id]
        
        raise HTTPException(status_code=404, detail=f"Orchestration {orchestration_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/orchestrations/{orchestration_id}")
async def update_orchestration(
    orchestration_id: str,
    config: OrchestrationConfig
) -> Dict[str, Any]:
    """Update an existing orchestration."""
    try:
        # Update in-memory
        if orchestration_id in orchestrations:
            orchestrations[orchestration_id].update({
                **config.dict(),
                "updated_at": datetime.utcnow().isoformat()
            })
        
        # Update in Firestore
        try:
            db = firestore.Client()
            db.collection("orchestrations").document(orchestration_id).update({
                **config.dict(),
                "updated_at": datetime.utcnow()
            })
        except Exception as e:
            logger.warning(f"Could not update in Firestore: {e}")
        
        return {
            "success": True,
            "message": f"Orchestration {orchestration_id} updated"
        }
    except Exception as e:
        logger.error(f"Error updating orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orchestrations/{orchestration_id}")
async def delete_orchestration(orchestration_id: str) -> Dict[str, Any]:
    """Delete an orchestration."""
    try:
        # Delete from in-memory
        if orchestration_id in orchestrations:
            del orchestrations[orchestration_id]
        
        # Delete from Firestore
        try:
            db = firestore.Client()
            db.collection("orchestrations").document(orchestration_id).delete()
        except Exception as e:
            logger.warning(f"Could not delete from Firestore: {e}")
        
        return {
            "success": True,
            "message": f"Orchestration {orchestration_id} deleted"
        }
    except Exception as e:
        logger.error(f"Error deleting orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orchestrations/{orchestration_id}/test")
async def test_orchestration(
    orchestration_id: str,
    test_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Test an orchestration with sample data.
    
    This simulates the data flow from MCP to Agent.
    """
    try:
        # Get orchestration
        orch = await get_orchestration(orchestration_id)
        
        # Simulate MCP data
        if not test_data:
            test_data = {
                "revenue_7d": 14138.83,
                "orders_7d": 127,
                "aov_7d": 111.32,
                "brand": "rogue-creamery"
            }
        
        # Apply data mapping
        mapped_data = {}
        for agent_var, mcp_var in orch.get("data_mapping", {}).items():
            if mcp_var in test_data:
                mapped_data[agent_var] = test_data[mcp_var]
        
        # Apply transformations
        for transform in orch.get("transformations", []):
            if transform["type"] == "calculate":
                # Example: Calculate percentage change
                if transform["operation"] == "percentage_change":
                    old_val = test_data.get(transform["old_field"], 0)
                    new_val = test_data.get(transform["new_field"], 0)
                    if old_val > 0:
                        mapped_data[transform["output_field"]] = ((new_val - old_val) / old_val) * 100
        
        return {
            "orchestration_id": orchestration_id,
            "test_status": "success",
            "input_data": test_data,
            "mapped_data": mapped_data,
            "would_trigger": True,
            "agent_id": orch.get("agent_id"),
            "mcp_server": orch.get("mcp_server")
        }
    except Exception as e:
        logger.error(f"Error testing orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example orchestration templates
ORCHESTRATION_TEMPLATES = {
    "revenue_alert": {
        "name": "Revenue Drop Alert",
        "description": "Triggers revenue analysis when daily revenue drops significantly",
        "mcp_server": "klaviyo_revenue",
        "agent_id": "revenue_analyst",
        "trigger_type": "event",
        "trigger_config": {
            "event": "revenue_check",
            "frequency": "daily",
            "condition": "revenue_change < -20"
        },
        "data_mapping": {
            "brand": "brand",
            "month": "current_month",
            "comparison_period": "previous_day"
        },
        "filters": [
            {"field": "revenue_7d", "operator": ">", "value": 0}
        ],
        "transformations": [
            {
                "type": "calculate",
                "operation": "percentage_change",
                "old_field": "revenue_yesterday",
                "new_field": "revenue_today",
                "output_field": "revenue_change"
            }
        ]
    },
    "campaign_performance": {
        "name": "Campaign Performance Review",
        "description": "Analyze campaign performance after completion",
        "mcp_server": "performance_api",
        "agent_id": "campaign_planner",
        "trigger_type": "webhook",
        "trigger_config": {
            "endpoint": "/webhooks/campaign-complete",
            "method": "POST"
        },
        "data_mapping": {
            "brand": "brand",
            "campaign_id": "campaign_id",
            "objective": "analyze_performance"
        }
    }
}


@router.get("/orchestrations/templates")
async def get_orchestration_templates() -> Dict[str, Any]:
    """Get pre-built orchestration templates."""
    return {
        "templates": ORCHESTRATION_TEMPLATES,
        "description": "Pre-configured orchestration templates for common use cases"
    }