"""
Tool Registry for Klaviyo MCP Service

Maps and documents all available MCP tools from the Enhanced server.
"""

from typing import List, Dict, Any, Optional
from .models import ToolInfo


class MCPToolRegistry:
    """Registry of all available Klaviyo MCP tools."""
    
    def __init__(self):
        """Initialize the tool registry with all available tools."""
        self.tools = self._initialize_tools()
        self.categories = self._extract_categories()
        
    def _initialize_tools(self) -> List[ToolInfo]:
        """Initialize the complete list of MCP tools."""
        return [
            # Analytics & Reporting Tools
            ToolInfo(
                name="get_campaign_metrics",
                description="Get performance metrics for a specific campaign (open rates, click rates, etc.)",
                category="Analytics",
                input_schema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Campaign ID"},
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Metrics to retrieve"
                        },
                        "start_date": {"type": "string", "format": "date-time"},
                        "end_date": {"type": "string", "format": "date-time"},
                        "conversion_metric_id": {"type": "string"}
                    },
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="query_metric_aggregates",
                description="Query aggregated metric data for custom analytics reporting",
                category="Analytics",
                input_schema={
                    "type": "object",
                    "properties": {
                        "metric_id": {"type": "string"},
                        "measurement": {"type": "string", "enum": ["count", "sum", "unique"]},
                        "group_by": {"type": "array", "items": {"type": "string"}},
                        "timeframe": {"type": "string"},
                        "start_date": {"type": "string", "format": "date-time"},
                        "end_date": {"type": "string", "format": "date-time"}
                    },
                    "required": ["metric_id"]
                }
            ),
            ToolInfo(
                name="get_campaign_performance",
                description="Get comprehensive performance summary for a campaign",
                category="Analytics"
            ),
            
            # Campaign Tools
            ToolInfo(
                name="get_campaigns",
                description="Get campaigns from Klaviyo",
                category="Campaigns"
            ),
            ToolInfo(
                name="get_campaign",
                description="Get a specific campaign from Klaviyo",
                category="Campaigns",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="get_campaign_message",
                description="Get a specific campaign message with template details",
                category="Campaigns"
            ),
            ToolInfo(
                name="get_campaign_messages",
                description="Get all messages for a specific campaign",
                category="Campaigns"
            ),
            ToolInfo(
                name="get_campaign_recipient_estimation",
                description="Get estimated recipient count for a campaign",
                category="Campaigns"
            ),
            
            # Profile Tools
            ToolInfo(
                name="get_profiles",
                description="Get profiles from Klaviyo",
                category="Profiles"
            ),
            ToolInfo(
                name="get_profile",
                description="Get a specific profile from Klaviyo",
                category="Profiles",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="create_profile",
                description="Create a new profile in Klaviyo",
                category="Profiles"
            ),
            ToolInfo(
                name="update_profile",
                description="Update an existing profile in Klaviyo",
                category="Profiles"
            ),
            ToolInfo(
                name="delete_profile",
                description="Delete a profile from Klaviyo",
                category="Profiles"
            ),
            
            # List Tools
            ToolInfo(
                name="get_lists",
                description="Get lists from Klaviyo",
                category="Lists"
            ),
            ToolInfo(
                name="get_list",
                description="Get a specific list from Klaviyo",
                category="Lists",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="create_list",
                description="Create a new list in Klaviyo",
                category="Lists"
            ),
            ToolInfo(
                name="add_profiles_to_list",
                description="Add profiles to a list in Klaviyo",
                category="Lists"
            ),
            
            # Segment Tools
            ToolInfo(
                name="get_segments",
                description="Get segments from Klaviyo",
                category="Segments"
            ),
            ToolInfo(
                name="get_segment",
                description="Get a specific segment from Klaviyo",
                category="Segments",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            
            # Event Tools
            ToolInfo(
                name="get_events",
                description="Get events from Klaviyo",
                category="Events"
            ),
            ToolInfo(
                name="create_event",
                description="Create a new event in Klaviyo",
                category="Events"
            ),
            
            # Metric Tools
            ToolInfo(
                name="get_metrics",
                description="Get metrics from Klaviyo",
                category="Metrics"
            ),
            ToolInfo(
                name="get_metric",
                description="Get a specific metric from Klaviyo",
                category="Metrics",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            
            # Flow Tools
            ToolInfo(
                name="get_flows",
                description="Get flows from Klaviyo",
                category="Flows"
            ),
            ToolInfo(
                name="get_flow",
                description="Get a specific flow from Klaviyo",
                category="Flows",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="update_flow_status",
                description="Update the status of a flow in Klaviyo",
                category="Flows"
            ),
            
            # Template Tools
            ToolInfo(
                name="get_templates",
                description="Get templates from Klaviyo",
                category="Templates"
            ),
            ToolInfo(
                name="get_template",
                description="Get a specific template from Klaviyo",
                category="Templates",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            ToolInfo(
                name="create_template",
                description="Create a new template in Klaviyo",
                category="Templates"
            ),
            
            # Image Tools
            ToolInfo(
                name="get_images",
                description="Get images from Klaviyo",
                category="Images"
            ),
            ToolInfo(
                name="get_image",
                description="Get a specific image from Klaviyo",
                category="Images",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            
            # E-commerce Tools
            ToolInfo(
                name="get_catalogs",
                description="Get catalogs from Klaviyo",
                category="E-commerce"
            ),
            ToolInfo(
                name="get_catalog_items",
                description="Get items from a catalog in Klaviyo",
                category="E-commerce"
            ),
            ToolInfo(
                name="get_catalog_item",
                description="Get a specific item from a catalog in Klaviyo",
                category="E-commerce"
            ),
            ToolInfo(
                name="get_coupons",
                description="Get coupons from Klaviyo",
                category="E-commerce"
            ),
            ToolInfo(
                name="create_coupon_code",
                description="Create a new coupon code in Klaviyo",
                category="E-commerce"
            ),
            
            # Tag Tools
            ToolInfo(
                name="get_tags",
                description="Get tags from Klaviyo",
                category="Tags"
            ),
            ToolInfo(
                name="create_tag",
                description="Create a new tag in Klaviyo",
                category="Tags"
            ),
            ToolInfo(
                name="add_tag_to_resource",
                description="Add a tag to a resource in Klaviyo",
                category="Tags"
            ),
            
            # Webhook Tools
            ToolInfo(
                name="get_webhooks",
                description="Get webhooks from Klaviyo",
                category="Webhooks"
            ),
            ToolInfo(
                name="create_webhook",
                description="Create a new webhook in Klaviyo",
                category="Webhooks"
            ),
            ToolInfo(
                name="delete_webhook",
                description="Delete a webhook from Klaviyo",
                category="Webhooks"
            ),
            
            # Data Privacy Tools
            ToolInfo(
                name="request_profile_deletion",
                description="Request deletion of a profile for data privacy compliance",
                category="Privacy"
            ),
            
            # Form Tools
            ToolInfo(
                name="get_forms",
                description="Get forms from Klaviyo",
                category="Forms"
            ),
            ToolInfo(
                name="get_form",
                description="Get a specific form from Klaviyo",
                category="Forms",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
            
            # Product Review Tools
            ToolInfo(
                name="get_product_reviews",
                description="Get product reviews from Klaviyo",
                category="Reviews"
            ),
            ToolInfo(
                name="get_product_review",
                description="Get a specific product review from Klaviyo",
                category="Reviews",
                input_schema={
                    "type": "object",
                    "properties": {"id": {"type": "string"}},
                    "required": ["id"]
                }
            ),
        ]
        
    def _extract_categories(self) -> List[str]:
        """Extract unique categories from tools."""
        categories = set()
        for tool in self.tools:
            if tool.category:
                categories.add(tool.category)
        return sorted(list(categories))
        
    def get_tools(self, category: Optional[str] = None) -> List[ToolInfo]:
        """
        Get tools, optionally filtered by category.
        
        Args:
            category: Optional category to filter by
            
        Returns:
            List of tool information
        """
        if category:
            return [tool for tool in self.tools if tool.category == category]
        return self.tools
        
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool information or None if not found
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
        
    def get_categories(self) -> List[str]:
        """Get list of all tool categories."""
        return self.categories
        
    def get_tool_count(self) -> int:
        """Get total number of tools."""
        return len(self.tools)
        
    def get_tools_by_category(self) -> Dict[str, List[ToolInfo]]:
        """Get tools grouped by category."""
        result = {}
        for category in self.categories:
            result[category] = self.get_tools(category=category)
        return result