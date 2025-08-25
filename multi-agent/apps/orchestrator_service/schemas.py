"""
Core schemas for multi-agent orchestration system.
All models include tenant/brand context and versioning.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum


class SchemaVersion(str, Enum):
    V1_0_0 = "1.0.0"
    

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPROVED_WITH_FIXES = "approved_with_fixes"


class QAResult(str, Enum):
    APPROVE = "approve"
    APPROVE_WITH_FIXES = "approve_with_fixes"
    REJECT = "reject"


class ArtifactType(str, Enum):
    PERFORMANCE_SLICE = "performance_slice"
    CAMPAIGN_CALENDAR = "campaign_calendar"
    CAMPAIGN_BRIEF = "campaign_brief"
    COPY_PACKET = "copy_packet"
    DESIGN_SPEC = "design_spec"
    QA_REPORT = "qa_report"
    ANALYTICS_REPORT = "analytics_report"


class BaseArtifact(BaseModel):
    """Base model for all artifacts."""
    tenant_id: str = Field(..., description="Tenant identifier")
    brand_id: str = Field(..., description="Brand identifier")
    schema_version: SchemaVersion = Field(default=SchemaVersion.V1_0_0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    provenance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model, prompt version, and other metadata"
    )
    
    class Config:
        use_enum_values = True


class MetricSnapshot(BaseModel):
    """Point-in-time metric data."""
    metric_name: str
    value: float
    unit: str
    period_start: datetime
    period_end: datetime
    comparison_value: Optional[float] = None
    comparison_period: Optional[str] = None
    

class PerformanceSlice(BaseArtifact):
    """Performance metrics for a specific time period."""
    artifact_type: Literal[ArtifactType.PERFORMANCE_SLICE] = ArtifactType.PERFORMANCE_SLICE
    selected_month: str  # YYYY-MM
    prior_year_same_month: str  # YYYY-MM
    
    current_metrics: List[MetricSnapshot]
    prior_year_metrics: List[MetricSnapshot]
    
    revenue_total: float
    conversion_rate: float
    engagement_rate: float
    
    top_campaigns: List[Dict[str, Any]]
    segment_performance: Dict[str, Any]
    
    insights: List[str] = Field(default_factory=list)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)


class CampaignHypothesis(BaseModel):
    """Campaign hypothesis with expected outcomes."""
    campaign_name: str
    scheduled_date: datetime
    target_segment: str
    hypothesis: str
    expected_revenue: float
    expected_engagement: float
    confidence_score: float = Field(ge=0.0, le=1.0)
    rationale: str


class CampaignCalendar(BaseArtifact):
    """Strategic campaign calendar."""
    artifact_type: Literal[ArtifactType.CAMPAIGN_CALENDAR] = ArtifactType.CAMPAIGN_CALENDAR
    month: str  # YYYY-MM
    
    campaigns: List[CampaignHypothesis]
    total_expected_revenue: float
    risk_assessment: Dict[str, Any]
    
    seasonality_factors: List[str]
    competitive_considerations: List[str]
    resource_requirements: Dict[str, Any]
    
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approver_notes: Optional[str] = None


class BrandProfile(BaseModel):
    """Brand identity and guidelines."""
    brand_id: str
    brand_name: str
    
    voice_attributes: List[str]
    tone_guidelines: Dict[str, str]
    
    visual_identity: Dict[str, Any]
    color_palette: List[str]
    typography: Dict[str, str]
    
    compliance_requirements: List[str]
    restricted_terms: List[str]
    mandatory_disclaimers: List[str]
    
    target_demographics: Dict[str, Any]
    value_propositions: List[str]


class CampaignBrief(BaseArtifact):
    """Campaign creative brief."""
    artifact_type: Literal[ArtifactType.CAMPAIGN_BRIEF] = ArtifactType.CAMPAIGN_BRIEF
    campaign_id: str
    campaign_name: str
    
    objective: str
    target_audience: Dict[str, Any]
    key_messages: List[str]
    
    creative_direction: str
    channel_strategy: Dict[str, Any]
    
    brand_violations: List[str] = Field(default_factory=list)
    compliance_checks: Dict[str, bool] = Field(default_factory=dict)
    
    performance_targets: Dict[str, float]
    success_metrics: List[str]
    
    approval_status: ApprovalStatus = ApprovalStatus.PENDING


class CopyVariant(BaseModel):
    """Individual copy variant."""
    variant_id: str
    framework: Literal["AIDA", "PAS", "FOMO", "Story", "Problem-Solution", "Educational"]
    
    subject_line: str
    preview_text: str
    headline: str
    body_copy: str
    cta_text: str
    
    personalization_tokens: List[str]
    dynamic_content_blocks: Dict[str, str]
    
    tone_score: float = Field(ge=0.0, le=1.0)
    readability_score: float = Field(ge=0.0, le=100.0)
    estimated_engagement: float = Field(ge=0.0, le=1.0)
    
    rationale: str


class CopyPacket(BaseArtifact):
    """Collection of copy variants for testing."""
    artifact_type: Literal[ArtifactType.COPY_PACKET] = ArtifactType.COPY_PACKET
    campaign_brief_id: str
    
    variants: List[CopyVariant]
    recommended_variant: str
    
    a_b_test_plan: Dict[str, Any]
    personalization_strategy: Dict[str, Any]
    
    brand_compliance_score: float = Field(ge=0.0, le=1.0)
    deliverability_score: float = Field(ge=0.0, le=1.0)


class DesignSpec(BaseArtifact):
    """Design specifications and requirements."""
    artifact_type: Literal[ArtifactType.DESIGN_SPEC] = ArtifactType.DESIGN_SPEC
    copy_packet_id: str
    
    layout_type: str
    mobile_first: bool = True
    
    sections: List[Dict[str, Any]]
    asset_requirements: List[Dict[str, Any]]
    
    color_scheme: List[str]
    typography_specs: Dict[str, Any]
    
    responsive_breakpoints: Dict[str, int]
    accessibility_requirements: List[str]
    
    interactive_elements: List[Dict[str, Any]]
    fallback_strategies: Dict[str, str]
    
    production_notes: str


class QAReport(BaseArtifact):
    """Quality assurance evaluation."""
    artifact_type: Literal[ArtifactType.QA_REPORT] = ArtifactType.QA_REPORT
    evaluated_artifact_id: str
    evaluated_artifact_type: ArtifactType
    
    result: QAResult
    
    brand_compliance: Dict[str, Any]
    accessibility_score: float = Field(ge=0.0, le=1.0)
    
    can_spam_compliant: bool
    tcpa_compliant: bool
    gdpr_compliant: bool
    
    deliverability_checks: Dict[str, bool]
    content_warnings: List[str]
    
    required_fixes: List[str]
    recommendations: List[str]
    
    risk_level: Literal["low", "medium", "high"]


class AnalyticsReport(BaseArtifact):
    """Post-send analytics and insights."""
    artifact_type: Literal[ArtifactType.ANALYTICS_REPORT] = ArtifactType.ANALYTICS_REPORT
    campaign_id: str
    
    send_date: datetime
    recipient_count: int
    
    open_rate: float
    click_rate: float
    conversion_rate: float
    revenue_generated: float
    
    segment_performance: Dict[str, Dict[str, float]]
    variant_performance: Dict[str, Dict[str, float]]
    
    kpi_achievement: Dict[str, float]
    insights: List[str]
    recommendations: List[str]


class RunState(BaseModel):
    """Orchestration run state."""
    run_id: str
    tenant_id: str
    brand_id: str
    
    selected_month: str
    prior_year_same_month: str
    
    current_phase: str
    current_node: str
    
    artifacts: Dict[ArtifactType, str] = Field(
        default_factory=dict,
        description="Map of artifact type to artifact ID"
    )
    
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    revision_count: int = 0
    
    status: Literal["running", "paused", "completed", "failed"]
    error: Optional[str] = None
    
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)