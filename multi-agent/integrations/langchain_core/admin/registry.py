"""
Agent Registry for CRUD operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from google.cloud import firestore

from ..config import get_config

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for managing agent definitions.
    """
    
    def __init__(self, db=None):
        """
        Initialize registry.
        
        Args:
            db: Firestore client (optional)
        """
        self.config = get_config()
        self.db = db
        
        if not self.db and self.config.firestore_project:
            self.db = firestore.Client(project=self.config.firestore_project)
        
        # In-memory cache
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default agents."""
        # Default RAG agent
        self.register_agent({
            "name": "rag",
            "description": "RAG-based question answering agent",
            "version": "1.0",
            "status": "active",
            "default_task": "Answer the question: {question}",
            "policy": {
                "max_tool_calls": 5,
                "timeout_seconds": 30,
                "allowed_tools": ["search", "retrieve"]
            },
            "variables": [
                {
                    "name": "question",
                    "type": "string",
                    "required": True,
                    "description": "Question to answer"
                },
                {
                    "name": "k",
                    "type": "integer",
                    "default": 5,
                    "description": "Number of documents to retrieve"
                }
            ],
            "prompt_template": """You are a helpful assistant that answers questions based on retrieved documents.
            
Use the provided context to answer the question accurately.
If you cannot answer based on the context, say so clearly.

Context: {context}
Question: {question}

Answer:"""
        })
        
        # Default task agent
        self.register_agent({
            "name": "default",
            "description": "General-purpose task execution agent",
            "version": "1.0",
            "status": "active",
            "default_task": "{task}",
            "policy": {
                "max_tool_calls": 15,
                "timeout_seconds": 60
            },
            "variables": [
                {
                    "name": "task",
                    "type": "string",
                    "required": True,
                    "description": "Task to execute"
                }
            ],
            "prompt_template": """You are a helpful AI assistant with access to various tools.

Complete the given task using the available tools.
Be efficient and provide clear, actionable answers.

Task: {task}
Context: {context}"""
        })
        
        # Revenue analysis agent
        self.register_agent({
            "name": "revenue_analyst",
            "description": "Analyzes revenue data and provides insights",
            "version": "1.0",
            "status": "active",
            "default_task": "Analyze revenue for {brand} in {month}",
            "policy": {
                "max_tool_calls": 10,
                "timeout_seconds": 45,
                "allowed_tools": ["klaviyo_revenue", "firestore_ro", "calculate"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand to analyze"
                },
                {
                    "name": "month",
                    "type": "string",
                    "required": True,
                    "pattern": "^\\d{4}-\\d{2}$",
                    "description": "Month to analyze (YYYY-MM)"
                },
                {
                    "name": "comparison_period",
                    "type": "string",
                    "default": "previous_month",
                    "allowed_values": ["previous_month", "previous_year", "ytd"],
                    "description": "Period to compare against"
                }
            ],
            "prompt_template": """You are Revenue Analyst, a specialist in analyzing email marketing revenue performance and providing actionable insights.

Analyze revenue performance for {brand} in {month} compared to {comparison_period}.

Your analysis should include:

1. **Revenue Metrics Analysis**:
   - Total revenue generated from email campaigns
   - Revenue per recipient and per email sent
   - Average order value trends
   - Conversion rate analysis
   - Click-to-purchase rates

2. **Comparative Performance**:
   - Month-over-month or year-over-year comparisons
   - Performance vs industry benchmarks
   - Trend identification and pattern analysis
   - Seasonal impact assessment

3. **Segment & Campaign Analysis**:
   - Top performing email campaigns by revenue
   - Best converting audience segments
   - Product category performance
   - Flow vs campaign revenue attribution

4. **Actionable Insights**:
   - Revenue optimization opportunities
   - Underperforming areas requiring attention
   - Recommended A/B tests for revenue growth
   - Budget allocation recommendations

5. **Key Metrics Dashboard**:
   - Revenue attribution by email type
   - Customer lifetime value impact
   - Revenue per subscriber trends
   - ROI calculations for email programs

Use available Klaviyo revenue tools to extract accurate data. Present findings with clear metrics, percentages, and dollar amounts. Highlight the top 3 revenue opportunities and provide specific, measurable recommendations.

Brand: {brand}
Month: {month}
Comparison Period: {comparison_period}
Context: {context}"""
        })
        
        # Campaign planner agent
        self.register_agent({
            "name": "campaign_planner",
            "description": "Plans email campaigns based on data",
            "version": "1.0",
            "status": "active",
            "default_task": "Create a {num_emails}-email campaign plan for {brand}",
            "policy": {
                "max_tool_calls": 20,
                "timeout_seconds": 90,
                "denied_tools": ["write", "delete", "update"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True
                },
                {
                    "name": "num_emails",
                    "type": "integer",
                    "default": 3,
                    "min_value": 1,
                    "max_value": 10
                },
                {
                    "name": "objective",
                    "type": "string",
                    "default": "increase engagement",
                    "allowed_values": [
                        "increase engagement",
                        "drive sales",
                        "build awareness",
                        "retain customers"
                    ]
                }
            ],
            "prompt_template": """You are Campaign Planner, a specialist in creating comprehensive, data-driven email campaign strategies.

Create a strategic {num_emails}-email campaign plan for {brand} with the objective to {objective}.

Your campaign plan should include:

1. **Campaign Strategy Overview**:
   - Campaign theme and positioning
   - Target audience analysis and segmentation
   - Timeline and send schedule optimization
   - Success metrics and KPI framework

2. **Individual Email Planning**:
   For each of the {num_emails} emails:
   - Email purpose and primary call-to-action
   - Subject line and preview text strategy
   - Content outline and key messaging
   - Design direction and template recommendations
   - Timing and send optimization

3. **Audience & Segmentation Strategy**:
   - Primary target segments and criteria
   - Exclusion rules and suppression lists
   - Personalization opportunities
   - A/B testing recommendations for segments

4. **Content & Creative Direction**:
   - Brand voice and tone guidelines
   - Visual hierarchy and design principles
   - Product/service positioning
   - Storytelling arc across the email sequence

5. **Performance Optimization**:
   - Deliverability best practices
   - Mobile optimization requirements
   - Send time optimization recommendations
   - A/B testing plan for subject lines and content

6. **Measurement & Analytics**:
   - Primary and secondary KPIs
   - Attribution model and tracking setup
   - Post-send analysis framework
   - Conversion funnel optimization

7. **Risk Mitigation**:
   - Compliance considerations (CAN-SPAM, GDPR)
   - Brand safety and reputation management
   - Technical delivery contingencies
   - Fallback strategies for underperformance

Use historical performance data to inform recommendations. Provide specific, actionable guidance for each email while maintaining consistency across the campaign sequence.

Brand: {brand}
Number of Emails: {num_emails}
Objective: {objective}
Context: {context}"""
        })
        
        # Calendar Planner agent - comprehensive monthly campaign planning
        try:
            from ..agents.calendar_planner import CALENDAR_PLANNER_AGENT
            self.register_agent(CALENDAR_PLANNER_AGENT)
            logger.info("Registered calendar_planner agent")
        except ImportError as e:
            logger.warning(f"Could not import calendar_planner agent: {e}")
        
        # Specialized Email/SMS Agents
        
        # Copy Smith - Copywriting with AIDA/PAS/FOMO frameworks
        self.register_agent({
            "name": "copy_smith",
            "description": "Generates copy variants using AIDA, PAS, FOMO, and Story frameworks for A/B testing",
            "version": "1.0",
            "status": "active",
            "default_task": "Create email copy variants for {brand} using {framework} framework with {tone} tone",
            "policy": {
                "max_tool_calls": 12,
                "timeout_seconds": 60,
                "allowed_tools": ["klaviyo_data", "brand_guidelines", "personalization"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for copy creation"
                },
                {
                    "name": "framework",
                    "type": "string",
                    "default": "AIDA",
                    "allowed_values": ["AIDA", "PAS", "FOMO", "Story", "Problem-Solution"],
                    "description": "Copywriting framework to use"
                },
                {
                    "name": "tone",
                    "type": "string",
                    "default": "professional",
                    "allowed_values": ["professional", "casual", "luxury", "urgent", "grateful"],
                    "description": "Tone of voice for the copy"
                },
                {
                    "name": "target_segment",
                    "type": "string",
                    "default": "engaged_subscribers",
                    "description": "Target audience segment"
                }
            ],
            "prompt_template": """You are Copy Smith, a specialist in creating high-converting email copy using proven frameworks.

Create email copy variants for {brand} using the {framework} framework with a {tone} tone.
Target audience: {target_segment}

Requirements:
- Generate 3-5 copy variants for A/B testing
- Include subject lines, preview text, headlines, and body copy
- Add personalization tokens where appropriate
- Optimize for deliverability and engagement
- Provide rationale for each variant

Framework: {framework}
Brand: {brand}
Tone: {tone}
Context: {context}"""
        })
        
        # Layout Lab - Mobile-first responsive design specifications
        self.register_agent({
            "name": "layout_lab",
            "description": "Creates mobile-first responsive design specifications and asset requirements",
            "version": "1.0",
            "status": "active",
            "default_task": "Create responsive email design specs for {brand} with {layout_type} layout",
            "policy": {
                "max_tool_calls": 10,
                "timeout_seconds": 45,
                "allowed_tools": ["brand_assets", "design_system", "accessibility_check"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for design specifications"
                },
                {
                    "name": "layout_type",
                    "type": "string",
                    "default": "single_column_responsive",
                    "allowed_values": ["single_column_responsive", "two_column", "grid_layout", "hero_focus"],
                    "description": "Email layout structure"
                },
                {
                    "name": "device_priority",
                    "type": "string",
                    "default": "mobile_first",
                    "allowed_values": ["mobile_first", "desktop_first", "tablet_optimized"],
                    "description": "Primary device target"
                }
            ],
            "prompt_template": """You are Layout Lab, a specialist in mobile-first email design and responsive layouts.

Create comprehensive design specifications for {brand} using {layout_type} layout.
Priority: {device_priority}

Requirements:
- Define responsive breakpoints and sections
- Specify asset requirements and dimensions
- Set accessibility standards and color schemes
- Provide typography specifications
- Include fallback strategies for email clients

Brand: {brand}
Layout: {layout_type}
Priority: {device_priority}
Context: {context}"""
        })
        
        # Calendar Strategist - Campaign timing optimization
        self.register_agent({
            "name": "calendar_strategist",
            "description": "Optimizes campaign timing and creates strategic email calendar based on performance data",
            "version": "1.0",
            "status": "active",
            "default_task": "Create email calendar strategy for {brand} for {month} with {campaign_count} campaigns",
            "policy": {
                "max_tool_calls": 15,
                "timeout_seconds": 75,
                "allowed_tools": ["klaviyo_analytics", "calendar_data", "performance_data"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for calendar planning"
                },
                {
                    "name": "month",
                    "type": "string",
                    "required": True,
                    "pattern": "^\\d{4}-\\d{2}$",
                    "description": "Target month (YYYY-MM)"
                },
                {
                    "name": "campaign_count",
                    "type": "integer",
                    "default": 4,
                    "min_value": 1,
                    "max_value": 12,
                    "description": "Number of campaigns to plan"
                },
                {
                    "name": "focus",
                    "type": "string",
                    "default": "revenue",
                    "allowed_values": ["revenue", "engagement", "retention", "acquisition"],
                    "description": "Primary campaign focus"
                }
            ],
            "prompt_template": """You are Calendar Strategist, a specialist in optimizing email campaign timing and strategic planning.

Create a strategic email calendar for {brand} for {month} with {campaign_count} campaigns.
Focus: {focus}

Requirements:
- Analyze historical performance patterns
- Identify optimal send times and segments
- Create campaign hypotheses with confidence scores
- Estimate revenue impact and engagement
- Consider seasonality and competitive factors

Brand: {brand}
Month: {month}
Campaigns: {campaign_count}
Focus: {focus}
Context: {context}"""
        })
        
        # Brand Brain - Brand consistency and voice
        self.register_agent({
            "name": "brand_brain",
            "description": "Ensures brand consistency, voice alignment, and creates compliant campaign briefs",
            "version": "1.0",
            "status": "active",
            "default_task": "Create brand-compliant campaign brief for {brand} with {objective} objective",
            "policy": {
                "max_tool_calls": 12,
                "timeout_seconds": 50,
                "allowed_tools": ["brand_guidelines", "compliance_check", "voice_analysis"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for compliance checking"
                },
                {
                    "name": "objective",
                    "type": "string",
                    "required": True,
                    "allowed_values": ["drive_sales", "build_awareness", "increase_engagement", "customer_retention"],
                    "description": "Campaign objective"
                },
                {
                    "name": "audience_segment",
                    "type": "string",
                    "default": "general",
                    "description": "Target audience segment"
                },
                {
                    "name": "compliance_level",
                    "type": "string",
                    "default": "standard",
                    "allowed_values": ["standard", "strict", "regulatory"],
                    "description": "Brand compliance requirements"
                }
            ],
            "prompt_template": """You are Brand Brain, a specialist in brand consistency, voice alignment, and compliance.

Create a comprehensive campaign brief for {brand} with {objective} objective.
Audience: {audience_segment}
Compliance Level: {compliance_level}

Requirements:
- Ensure brand voice and tone consistency
- Define target audience and key messages
- Set creative direction and channel strategy
- Perform brand compliance checks
- Establish performance targets and success metrics

Brand: {brand}
Objective: {objective}
Audience: {audience_segment}
Context: {context}"""
        })
        
        # Gatekeeper - Compliance and regulations
        self.register_agent({
            "name": "gatekeeper",
            "description": "Performs QA review for brand, legal, accessibility, and deliverability compliance",
            "version": "1.0",
            "status": "active",
            "default_task": "Review {artifact_type} for {brand} and check {compliance_areas} compliance",
            "policy": {
                "max_tool_calls": 8,
                "timeout_seconds": 40,
                "allowed_tools": ["compliance_scanner", "accessibility_checker", "deliverability_analyzer"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for compliance review"
                },
                {
                    "name": "artifact_type",
                    "type": "string",
                    "default": "email_campaign",
                    "allowed_values": ["email_campaign", "copy_variants", "design_spec", "landing_page"],
                    "description": "Type of artifact to review"
                },
                {
                    "name": "compliance_areas",
                    "type": "string",
                    "default": "all",
                    "allowed_values": ["all", "legal", "brand", "accessibility", "deliverability"],
                    "description": "Specific compliance areas to check"
                },
                {
                    "name": "review_level",
                    "type": "string",
                    "default": "standard",
                    "allowed_values": ["basic", "standard", "strict"],
                    "description": "Depth of compliance review"
                }
            ],
            "prompt_template": """You are Gatekeeper, a specialist in quality assurance and compliance review.

Review {artifact_type} for {brand} focusing on {compliance_areas} compliance.
Review Level: {review_level}

Requirements:
- Check brand guideline compliance
- Validate legal requirements (CAN-SPAM, TCPA, GDPR)
- Assess accessibility standards
- Evaluate deliverability risks
- Provide actionable fix recommendations

Brand: {brand}
Artifact: {artifact_type}
Compliance Areas: {compliance_areas}
Context: {context}"""
        })
        
        # Truth Teller - Performance analytics
        self.register_agent({
            "name": "truth_teller",
            "description": "Sets up analytics, measurement frameworks, and defines success criteria for campaigns",
            "version": "1.0",
            "status": "active",
            "default_task": "Setup analytics and measurement plan for {brand} {campaign_type} campaign",
            "policy": {
                "max_tool_calls": 10,
                "timeout_seconds": 55,
                "allowed_tools": ["analytics_setup", "kpi_calculator", "dashboard_builder"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for analytics setup"
                },
                {
                    "name": "campaign_type",
                    "type": "string",
                    "default": "promotional",
                    "allowed_values": ["promotional", "educational", "lifecycle", "retention"],
                    "description": "Type of campaign for measurement"
                },
                {
                    "name": "primary_kpi",
                    "type": "string",
                    "default": "revenue",
                    "allowed_values": ["revenue", "conversion_rate", "engagement", "retention"],
                    "description": "Primary success metric"
                },
                {
                    "name": "measurement_window",
                    "type": "string",
                    "default": "7_days",
                    "allowed_values": ["24_hours", "7_days", "30_days", "90_days"],
                    "description": "Attribution window for measurement"
                }
            ],
            "prompt_template": """You are Truth Teller, a specialist in analytics setup and performance measurement.

Setup comprehensive measurement plan for {brand} {campaign_type} campaign.
Primary KPI: {primary_kpi}
Measurement Window: {measurement_window}

Requirements:
- Define KPI framework and tracking parameters
- Setup A/B testing measurement criteria
- Create dashboard and alerting requirements
- Establish post-send analysis timeline
- Set success criteria at multiple levels

Brand: {brand}
Campaign Type: {campaign_type}
Primary KPI: {primary_kpi}
Context: {context}"""
        })
        
        # Audience Architect - Segmentation strategies
        self.register_agent({
            "name": "audience_architect",
            "description": "Creates advanced audience segmentation and targeting strategies for optimal campaign performance",
            "version": "1.0",
            "status": "active",
            "default_task": "Create audience segmentation strategy for {brand} targeting {objective}",
            "policy": {
                "max_tool_calls": 15,
                "timeout_seconds": 70,
                "allowed_tools": ["segmentation_engine", "behavioral_data", "predictive_modeling"]
            },
            "variables": [
                {
                    "name": "brand",
                    "type": "string",
                    "required": True,
                    "description": "Brand name for segmentation analysis"
                },
                {
                    "name": "objective",
                    "type": "string",
                    "default": "increase_conversion",
                    "allowed_values": ["increase_conversion", "improve_retention", "cross_sell", "win_back"],
                    "description": "Segmentation objective"
                },
                {
                    "name": "segment_type",
                    "type": "string",
                    "default": "behavioral",
                    "allowed_values": ["behavioral", "demographic", "psychographic", "lifecycle", "rfm"],
                    "description": "Primary segmentation approach"
                },
                {
                    "name": "data_sources",
                    "type": "string",
                    "default": "klaviyo",
                    "allowed_values": ["klaviyo", "multi_source", "predictive", "lookalike"],
                    "description": "Data sources for segmentation"
                }
            ],
            "prompt_template": """You are Audience Architect, a specialist in advanced audience segmentation and targeting strategies.

Create segmentation strategy for {brand} targeting {objective}.
Approach: {segment_type}
Data Sources: {data_sources}

Requirements:
- Analyze customer data for behavioral patterns
- Create predictive audience segments
- Design lookalike modeling strategies
- Build exclusion lists and suppression rules
- Optimize segments for campaign performance

Brand: {brand}
Objective: {objective}
Segment Type: {segment_type}
Context: {context}"""
        })
    
    def register_agent(self, agent_def: Dict[str, Any]) -> str:
        """
        Register or update an agent.
        
        Args:
            agent_def: Agent definition
        
        Returns:
            Agent name
        """
        name = agent_def.get("name")
        if not name:
            raise ValueError("Agent name is required")
        
        # Add metadata
        agent_def["updated_at"] = datetime.utcnow()
        if name not in self._agents:
            agent_def["created_at"] = datetime.utcnow()
        
        # Store in memory
        self._agents[name] = agent_def
        
        # Store in Firestore if available
        if self.db:
            try:
                self.db.collection("agent_registry").document(name).set(agent_def)
            except Exception as e:
                logger.error(f"Failed to store agent in Firestore: {e}")
        
        logger.info(f"Registered agent: {name}")
        return name
    
    def get_agent(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get an agent definition.
        
        Args:
            name: Agent name
        
        Returns:
            Agent definition or None
        """
        # Check memory cache
        if name in self._agents:
            return self._agents[name]
        
        # Try Firestore
        if self.db:
            try:
                doc = self.db.collection("agent_registry").document(name).get()
                if doc.exists:
                    agent_def = doc.to_dict()
                    self._agents[name] = agent_def
                    return agent_def
            except Exception as e:
                logger.error(f"Failed to get agent from Firestore: {e}")
        
        return None
    
    def list_agents(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List all agents.
        
        Args:
            status: Filter by status
            limit: Maximum number to return
        
        Returns:
            List of agent definitions
        """
        agents = []
        
        # Get from memory
        for agent in self._agents.values():
            if status and agent.get("status") != status:
                continue
            agents.append(agent)
        
        # Get from Firestore if needed
        if self.db and len(agents) < limit:
            try:
                query = self.db.collection("agent_registry").limit(limit)
                if status:
                    query = query.where("status", "==", status)
                
                for doc in query.stream():
                    agent_def = doc.to_dict()
                    if agent_def["name"] not in self._agents:
                        self._agents[agent_def["name"]] = agent_def
                        agents.append(agent_def)
            except Exception as e:
                logger.error(f"Failed to list agents from Firestore: {e}")
        
        return agents[:limit]
    
    def update_agent(self, name: str, updates: Dict[str, Any]) -> bool:
        """
        Update an agent.
        
        Args:
            name: Agent name
            updates: Fields to update
        
        Returns:
            Success flag
        """
        agent = self.get_agent(name)
        if not agent:
            return False
        
        # Apply updates
        agent.update(updates)
        agent["updated_at"] = datetime.utcnow()
        
        # Store
        self._agents[name] = agent
        
        if self.db:
            try:
                self.db.collection("agent_registry").document(name).update(updates)
            except Exception as e:
                logger.error(f"Failed to update agent in Firestore: {e}")
        
        return True
    
    def delete_agent(self, name: str) -> bool:
        """
        Delete an agent.
        
        Args:
            name: Agent name
        
        Returns:
            Success flag
        """
        # Protect system agents and specialized email/SMS agents
        protected_agents = [
            "default", "rag", "revenue_analyst", "campaign_planner", "calendar_planner",
            "copy_smith", "layout_lab", "calendar_strategist", "brand_brain",
            "gatekeeper", "truth_teller", "audience_architect"
        ]
        if name in protected_agents:
            logger.warning(f"Cannot delete protected agent: {name}")
            return False
        
        if name in self._agents:
            del self._agents[name]
        
        if self.db:
            try:
                self.db.collection("agent_registry").document(name).delete()
            except Exception as e:
                logger.error(f"Failed to delete agent from Firestore: {e}")
                return False
        
        return True


# Global registry instance
_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry