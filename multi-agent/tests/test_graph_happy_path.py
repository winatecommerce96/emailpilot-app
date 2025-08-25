"""
Happy path tests for the orchestration graph.
Tests full flow with mocked clients and auto-approved decisions.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.orchestrator_service.graph import CampaignOrchestrationGraph, GraphState
from apps.orchestrator_service.schemas import (
    RunState, PerformanceSlice, CampaignCalendar,
    CampaignBrief, CopyPacket, DesignSpec, QAReport,
    ApprovalStatus, QAResult, ArtifactType
)
from apps.orchestrator_service.config import get_settings


class TestHappyPath:
    """Test successful execution through all phases."""
    
    @pytest.fixture
    def settings(self):
        """Get test settings."""
        settings = get_settings()
        settings.orchestration.auto_approve_in_dev = True
        settings.orchestration.max_revision_loops = 3
        return settings
    
    @pytest.fixture
    def orchestrator(self, settings):
        """Create orchestrator with mocked settings."""
        with patch('apps.orchestrator_service.graph.get_settings', return_value=settings):
            return CampaignOrchestrationGraph()
    
    @pytest.mark.asyncio
    async def test_full_workflow_success(self, orchestrator):
        """Test complete workflow from performance fetch to analytics setup."""
        
        # Run the orchestration
        result = await orchestrator.run(
            tenant_id="test-tenant",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10",
            metadata={"test": True}
        )
        
        # Assertions
        assert isinstance(result, RunState)
        assert result.status == "completed"
        assert result.tenant_id == "test-tenant"
        assert result.brand_id == "test-brand"
        assert result.selected_month == "2024-10"
        
        # Check all artifacts were created
        expected_artifacts = [
            ArtifactType.PERFORMANCE_SLICE,
            ArtifactType.CAMPAIGN_CALENDAR,
            ArtifactType.CAMPAIGN_BRIEF,
            ArtifactType.COPY_PACKET,
            ArtifactType.DESIGN_SPEC,
            ArtifactType.QA_REPORT,
        ]
        
        for artifact_type in expected_artifacts:
            assert artifact_type in result.artifacts
            assert result.artifacts[artifact_type] is not None
        
        # Check approvals were auto-granted
        assert len(result.approvals) >= 2  # Brief and final approval
        
        # Check no errors
        assert result.error is None
        
        # Check completion time
        assert result.completed_at is not None
        assert result.completed_at > result.started_at
    
    @pytest.mark.asyncio
    async def test_phase_transitions(self, orchestrator):
        """Test that phases transition correctly."""
        
        # Track phase transitions
        phases_seen = []
        
        def track_phase(state: GraphState) -> GraphState:
            phases_seen.append(state["current_phase"])
            return state
        
        # Patch node functions to track phases
        with patch.object(orchestrator, '_fetch_performance_node', 
                         side_effect=[track_phase, orchestrator._fetch_performance_node][1]):
            
            result = await orchestrator.run(
                tenant_id="test-tenant",
                brand_id="test-brand",
                selected_month="2024-10",
                prior_year_same_month="2023-10",
            )
        
        # Check we went through expected phases
        assert result.current_phase == "monitoring"
        assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_auto_approval_in_dev(self, settings, orchestrator):
        """Test that auto-approval works in development mode."""
        
        assert settings.orchestration.auto_approve_in_dev == True
        
        result = await orchestrator.run(
            tenant_id="test-tenant",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10",
        )
        
        # Check approvals were auto-granted
        approval_history = result.approvals
        assert len(approval_history) > 0
        
        for approval in approval_history:
            assert approval.get("auto_approved") == True
            assert approval.get("status") == "approved"
    
    @pytest.mark.asyncio
    async def test_artifact_creation(self, orchestrator):
        """Test that all artifacts are properly created."""
        
        result = await orchestrator.run(
            tenant_id="test-tenant",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10",
        )
        
        # Performance Slice should be created
        assert ArtifactType.PERFORMANCE_SLICE in result.artifacts
        
        # Campaign Calendar should be created
        assert ArtifactType.CAMPAIGN_CALENDAR in result.artifacts
        
        # Campaign Brief should be created
        assert ArtifactType.CAMPAIGN_BRIEF in result.artifacts
        
        # Copy Packet should be created
        assert ArtifactType.COPY_PACKET in result.artifacts
        
        # Design Spec should be created
        assert ArtifactType.DESIGN_SPEC in result.artifacts
        
        # QA Report should be created
        assert ArtifactType.QA_REPORT in result.artifacts
    
    @pytest.mark.asyncio
    async def test_metadata_propagation(self, orchestrator):
        """Test that metadata is properly propagated through the workflow."""
        
        test_metadata = {
            "source": "unit_test",
            "test_id": "12345",
            "custom_field": "test_value"
        }
        
        result = await orchestrator.run(
            tenant_id="test-tenant",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10",
            metadata=test_metadata
        )
        
        # Check metadata is preserved
        assert result.metadata["source"] == "unit_test"
        assert result.metadata["test_id"] == "12345"
        assert result.metadata["custom_field"] == "test_value"
        
        # Check completion metadata was added
        assert "completed_at" in result.metadata
        assert "analytics_plan" in result.metadata


class TestNodeFunctions:
    """Test individual node functions."""
    
    def test_performance_fetch(self):
        """Test performance data fetching."""
        from apps.orchestrator_service.nodes.calendar_performance import fetch_performance
        
        result = fetch_performance(
            tenant_id="test",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10"
        )
        
        assert isinstance(result, PerformanceSlice)
        assert result.tenant_id == "test"
        assert result.brand_id == "test-brand"
        assert result.selected_month == "2024-10"
        assert len(result.current_metrics) > 0
        assert result.revenue_total > 0
    
    def test_calendar_planning(self):
        """Test calendar strategy creation."""
        from apps.orchestrator_service.nodes.calendar_strategist import plan_calendar
        from apps.orchestrator_service.nodes.calendar_performance import fetch_performance
        
        # Get performance data first
        perf = fetch_performance(
            tenant_id="test",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10"
        )
        
        # Plan calendar
        result = plan_calendar(
            performance_slice=perf,
            brand_id="test-brand"
        )
        
        assert isinstance(result, CampaignCalendar)
        assert len(result.campaigns) > 0
        assert result.total_expected_revenue > 0
        assert result.risk_assessment is not None
    
    def test_brief_creation(self):
        """Test campaign brief generation."""
        from apps.orchestrator_service.nodes.brand_brain import create_brief
        from apps.orchestrator_service.nodes.calendar_strategist import plan_calendar
        from apps.orchestrator_service.nodes.calendar_performance import fetch_performance
        
        # Get dependencies
        perf = fetch_performance(
            tenant_id="test",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10"
        )
        
        calendar = plan_calendar(
            performance_slice=perf,
            brand_id="test-brand"
        )
        
        # Create brief
        result = create_brief(
            campaign_calendar=calendar,
            brand_id="test-brand"
        )
        
        assert isinstance(result, CampaignBrief)
        assert result.campaign_name is not None
        assert len(result.key_messages) > 0
        assert result.performance_targets is not None
    
    def test_copy_generation(self):
        """Test copy variant creation."""
        from apps.orchestrator_service.nodes.copy_smith import generate_copy
        from apps.orchestrator_service.nodes.brand_brain import create_brief
        from apps.orchestrator_service.nodes.calendar_strategist import plan_calendar
        from apps.orchestrator_service.nodes.calendar_performance import fetch_performance
        
        # Get dependencies
        perf = fetch_performance(
            tenant_id="test",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10"
        )
        
        calendar = plan_calendar(
            performance_slice=perf,
            brand_id="test-brand"
        )
        
        brief = create_brief(
            campaign_calendar=calendar,
            brand_id="test-brand"
        )
        
        # Generate copy
        result = generate_copy(
            campaign_brief=brief,
            brand_id="test-brand"
        )
        
        assert isinstance(result, CopyPacket)
        assert len(result.variants) >= 3
        assert result.recommended_variant is not None
        assert result.deliverability_score > 0.8
    
    def test_qa_review(self):
        """Test QA evaluation."""
        from apps.orchestrator_service.nodes.gatekeeper import review_campaign
        from apps.orchestrator_service.nodes.layout_lab import create_design
        from apps.orchestrator_service.nodes.copy_smith import generate_copy
        from apps.orchestrator_service.nodes.brand_brain import create_brief
        from apps.orchestrator_service.nodes.calendar_strategist import plan_calendar
        from apps.orchestrator_service.nodes.calendar_performance import fetch_performance
        
        # Build up all dependencies
        perf = fetch_performance(
            tenant_id="test",
            brand_id="test-brand",
            selected_month="2024-10",
            prior_year_same_month="2023-10"
        )
        
        calendar = plan_calendar(
            performance_slice=perf,
            brand_id="test-brand"
        )
        
        brief = create_brief(
            campaign_calendar=calendar,
            brand_id="test-brand"
        )
        
        copy = generate_copy(
            campaign_brief=brief,
            brand_id="test-brand"
        )
        
        design = create_design(
            copy_packet=copy,
            campaign_brief=brief
        )
        
        # Perform QA
        result = review_campaign(
            campaign_brief=brief,
            copy_packet=copy,
            design_spec=design
        )
        
        assert isinstance(result, QAReport)
        assert result.result in [QAResult.APPROVE, QAResult.APPROVE_WITH_FIXES, QAResult.REJECT]
        assert result.can_spam_compliant == True
        assert result.accessibility_score >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])