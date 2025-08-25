"""
LangGraph orchestration graph for multi-agent campaign workflow.
Implements four phases with approval interrupts and QA loops.
"""

from typing import Dict, Any, List, TypedDict, Annotated, Optional
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
import os
import logging

logger = logging.getLogger(__name__)

from .schemas import (
    RunState, PerformanceSlice, CampaignCalendar, CampaignBrief,
    CopyPacket, DesignSpec, QAReport, ApprovalStatus, QAResult,
    ArtifactType
)
from .config import get_settings
from .approvals import ApprovalManager
from .nodes import (
    calendar_performance,
    calendar_strategist,
    brand_brain,
    copy_smith,
    layout_lab,
    gatekeeper,
    truth_teller,
)


# Graph state definition
class GraphState(TypedDict):
    """State passed between graph nodes."""
    
    # Core identifiers
    run_id: str
    tenant_id: str
    brand_id: str
    selected_month: str
    prior_year_same_month: str
    
    # Artifacts
    performance_slice: Optional[PerformanceSlice]
    campaign_calendar: Optional[CampaignCalendar]
    campaign_brief: Optional[CampaignBrief]
    copy_packet: Optional[CopyPacket]
    design_spec: Optional[DesignSpec]
    qa_report: Optional[QAReport]
    
    # Control flow
    current_phase: str
    current_node: str
    revision_count: int
    max_revisions: int
    
    # Approvals
    pending_approval: Optional[Dict[str, Any]]
    approval_history: List[Dict[str, Any]]
    
    # Error handling
    error: Optional[str]
    retry_count: int
    
    # Metadata
    started_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]


class CampaignOrchestrationGraph:
    """Main orchestration graph for campaign creation workflow."""
    
    def __init__(self):
        self.settings = get_settings()
        self.approval_manager = ApprovalManager()
        self.graph = self._build_graph()
        
        # Configure Firestore checkpointing for state persistence
        # Get project ID from settings or environment
        project_id = getattr(self.settings.storage, 'gcp_project', None) or \
                    os.environ.get('GOOGLE_CLOUD_PROJECT', 'emailpilot-438321')
        
        try:
            # Try to use the original FirestoreSaver if available
            try:
                from langgraph_checkpoint_firestore import FirestoreSaver
                # Initialize Firestore checkpointer
                self.checkpointer = FirestoreSaver(
                    project_id=project_id,
                    checkpoints_collection='langgraph_checkpoints',
                    writes_collection='langgraph_writes'
                )
                logger.info(f"Initialized FirestoreSaver for project: {project_id}")
            except ImportError:
                # Use our robust version with auto-fallback
                logger.info("Using RobustFirestoreSaver with auto-transport detection")
                from .checkpoints.firestore_saver import get_robust_firestore_saver
                self.checkpointer = get_robust_firestore_saver(
                    project_id=project_id,
                    checkpoints_collection='langgraph_checkpoints',
                    writes_collection='langgraph_writes'
                )
                logger.info(f"Initialized RobustFirestoreSaver for project: {project_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize Firestore checkpointer: {e}. Falling back to in-memory.")
            # Fallback to in-memory if Firestore is not available
            from .compat.langgraph_checkpoint import resolve_memory_saver
            MemorySaver = resolve_memory_saver()
            self.checkpointer = MemorySaver()
        
        self.app = self.graph.compile(checkpointer=self.checkpointer)
    
    def _build_graph(self) -> StateGraph:
        """Build the orchestration graph."""
        
        # Initialize graph with state schema
        workflow = StateGraph(GraphState)
        
        # Phase 1: Calendar Creation
        workflow.add_node("fetch_performance", self._fetch_performance_node)
        workflow.add_node("plan_calendar", self._plan_calendar_node)
        
        # Phase 2: Brief Writing
        workflow.add_node("create_brief", self._create_brief_node)
        workflow.add_node("brief_approval", self._brief_approval_node)
        
        # Phase 3: Copywriting
        workflow.add_node("generate_copy", self._generate_copy_node)
        
        # Phase 4: Design & QA
        workflow.add_node("create_design", self._create_design_node)
        workflow.add_node("qa_review", self._qa_review_node)
        workflow.add_node("final_approval", self._final_approval_node)
        
        # Analytics & Monitoring
        workflow.add_node("setup_analytics", self._setup_analytics_node)
        
        # Set entry point
        workflow.set_entry_point("fetch_performance")
        
        # Define edges (transitions)
        workflow.add_edge("fetch_performance", "plan_calendar")
        workflow.add_edge("plan_calendar", "create_brief")
        workflow.add_edge("create_brief", "brief_approval")
        
        # Conditional routing based on approval
        workflow.add_conditional_edges(
            "brief_approval",
            self._route_brief_approval,
            {
                "approved": "generate_copy",
                "rejected": "create_brief",
                "pending": "brief_approval",
            }
        )
        
        workflow.add_edge("generate_copy", "create_design")
        workflow.add_edge("create_design", "qa_review")
        
        # QA loop routing
        workflow.add_conditional_edges(
            "qa_review",
            self._route_qa_review,
            {
                "approve": "final_approval",
                "approve_with_fixes": "final_approval",
                "create_brief": "create_brief",
                "generate_copy": "generate_copy", 
                "create_design": "create_design",
            }
        )
        
        # Final approval routing
        workflow.add_conditional_edges(
            "final_approval",
            self._route_final_approval,
            {
                "approved": "setup_analytics",
                "rejected": "generate_copy",
                "pending": "final_approval",
            }
        )
        
        workflow.add_edge("setup_analytics", END)
        
        return workflow
    
    # Node implementations
    
    def _fetch_performance_node(self, state: GraphState) -> GraphState:
        """Fetch performance metrics."""
        state["current_phase"] = "calendar_creation"
        state["current_node"] = "fetch_performance"
        state["updated_at"] = datetime.utcnow()
        
        # Call the calendar_performance node function
        performance_slice = calendar_performance.fetch_performance(
            tenant_id=state["tenant_id"],
            brand_id=state["brand_id"],
            selected_month=state["selected_month"],
            prior_year_same_month=state["prior_year_same_month"],
        )
        
        state["performance_slice"] = performance_slice
        return state
    
    def _plan_calendar_node(self, state: GraphState) -> GraphState:
        """Plan campaign calendar."""
        state["current_node"] = "plan_calendar"
        state["updated_at"] = datetime.utcnow()
        
        # Call the calendar_strategist node function
        campaign_calendar = calendar_strategist.plan_calendar(
            performance_slice=state["performance_slice"],
            brand_id=state["brand_id"],
        )
        
        state["campaign_calendar"] = campaign_calendar
        return state
    
    def _create_brief_node(self, state: GraphState) -> GraphState:
        """Create campaign brief."""
        state["current_phase"] = "brief_writing"
        state["current_node"] = "create_brief"
        state["updated_at"] = datetime.utcnow()
        
        # Call the brand_brain node function
        campaign_brief = brand_brain.create_brief(
            campaign_calendar=state["campaign_calendar"],
            brand_id=state["brand_id"],
        )
        
        state["campaign_brief"] = campaign_brief
        return state
    
    def _brief_approval_node(self, state: GraphState) -> GraphState:
        """Handle brief approval."""
        state["current_node"] = "brief_approval"
        state["updated_at"] = datetime.utcnow()
        
        if self.settings.orchestration.auto_approve_in_dev:
            # Auto-approve in development
            state["campaign_brief"].approval_status = ApprovalStatus.APPROVED
            state["approval_history"].append({
                "artifact_type": "campaign_brief",
                "status": "approved",
                "timestamp": datetime.utcnow(),
                "auto_approved": True,
            })
        else:
            # Create approval request
            state["pending_approval"] = {
                "artifact_type": "campaign_brief",
                "artifact_id": state["campaign_brief"].campaign_id,
                "requested_at": datetime.utcnow(),
            }
        
        return state
    
    def _generate_copy_node(self, state: GraphState) -> GraphState:
        """Generate copy variants."""
        state["current_phase"] = "copywriting"
        state["current_node"] = "generate_copy"
        state["updated_at"] = datetime.utcnow()
        
        # Call the copy_smith node function
        copy_packet = copy_smith.generate_copy(
            campaign_brief=state["campaign_brief"],
            brand_id=state["brand_id"],
        )
        
        state["copy_packet"] = copy_packet
        return state
    
    def _create_design_node(self, state: GraphState) -> GraphState:
        """Create design specifications."""
        state["current_phase"] = "design_qa"
        state["current_node"] = "create_design"
        state["updated_at"] = datetime.utcnow()
        
        # Call the layout_lab node function
        design_spec = layout_lab.create_design(
            copy_packet=state["copy_packet"],
            campaign_brief=state["campaign_brief"],
        )
        
        state["design_spec"] = design_spec
        return state
    
    def _qa_review_node(self, state: GraphState) -> GraphState:
        """Perform QA review."""
        state["current_node"] = "qa_review"
        state["updated_at"] = datetime.utcnow()
        
        # Call the gatekeeper node function
        qa_report = gatekeeper.review_campaign(
            campaign_brief=state["campaign_brief"],
            copy_packet=state["copy_packet"],
            design_spec=state["design_spec"],
        )
        
        state["qa_report"] = qa_report
        
        # Track revision if this is a re-review
        if qa_report.result == QAResult.REJECT:
            state["revision_count"] += 1
        
        return state
    
    def _final_approval_node(self, state: GraphState) -> GraphState:
        """Handle final approval before release."""
        state["current_node"] = "final_approval"
        state["updated_at"] = datetime.utcnow()
        
        if self.settings.orchestration.auto_approve_in_dev:
            # Auto-approve in development
            state["approval_history"].append({
                "artifact_type": "final_campaign",
                "status": "approved",
                "timestamp": datetime.utcnow(),
                "auto_approved": True,
            })
        else:
            # Create approval request
            state["pending_approval"] = {
                "artifact_type": "final_campaign",
                "requested_at": datetime.utcnow(),
                "qa_result": state["qa_report"].result,
            }
        
        return state
    
    def _setup_analytics_node(self, state: GraphState) -> GraphState:
        """Setup analytics and monitoring."""
        state["current_phase"] = "monitoring"
        state["current_node"] = "setup_analytics"
        state["updated_at"] = datetime.utcnow()
        
        # Call the truth_teller node function
        analytics_plan = truth_teller.setup_analytics(
            campaign_brief=state["campaign_brief"],
            copy_packet=state["copy_packet"],
        )
        
        state["metadata"]["analytics_plan"] = analytics_plan
        state["metadata"]["completed_at"] = datetime.utcnow()
        
        return state
    
    # Routing functions
    
    def _route_brief_approval(self, state: GraphState) -> str:
        """Route based on brief approval status."""
        if state.get("pending_approval"):
            return "pending"
        
        if state["campaign_brief"].approval_status == ApprovalStatus.APPROVED:
            return "approved"
        elif state["campaign_brief"].approval_status == ApprovalStatus.REJECTED:
            return "rejected"
        
        return "pending"
    
    def _route_qa_review(self, state: GraphState) -> str:
        """Route based on QA review result."""
        qa_result = state["qa_report"].result
        
        if qa_result == QAResult.APPROVE:
            return "approve"
        elif qa_result == QAResult.APPROVE_WITH_FIXES:
            return "approve_with_fixes"
        else:  # REJECT
            # Check revision limit
            if state["revision_count"] >= state["max_revisions"]:
                state["error"] = f"Max revisions ({state['max_revisions']}) exceeded"
                return "approve_with_fixes"  # Force through with warnings
            # Determine where to route for revision
            return self._determine_revision_target(state)
    
    def _route_final_approval(self, state: GraphState) -> str:
        """Route based on final approval status."""
        if state.get("pending_approval"):
            return "pending"
        
        # Check approval history for final approval
        final_approvals = [
            a for a in state["approval_history"]
            if a["artifact_type"] == "final_campaign"
        ]
        
        if final_approvals:
            latest = final_approvals[-1]
            if latest["status"] == "approved":
                return "approved"
            else:
                return "rejected"
        
        return "pending"
    
    def _determine_revision_target(self, state: GraphState) -> str:
        """Determine which node to return to for revision."""
        qa_report = state["qa_report"]
        
        # Analyze the QA report to determine the primary issue
        if qa_report.brand_compliance and \
           any(not v for v in qa_report.brand_compliance.values()):
            return "create_brief"  # Brand issues -> back to brief
        
        if qa_report.content_warnings:
            return "generate_copy"  # Content issues -> back to copy
        
        if qa_report.accessibility_score < 0.7:
            return "create_design"  # Design issues -> back to design
        
        # Default to copy revision
        return "generate_copy"
    
    # Public methods
    
    async def run(
        self,
        tenant_id: str,
        brand_id: str,
        selected_month: str,
        prior_year_same_month: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RunState:
        """Execute the orchestration graph."""
        
        # Initialize state
        initial_state: GraphState = {
            "run_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "brand_id": brand_id,
            "selected_month": selected_month,
            "prior_year_same_month": prior_year_same_month,
            
            "performance_slice": None,
            "campaign_calendar": None,
            "campaign_brief": None,
            "copy_packet": None,
            "design_spec": None,
            "qa_report": None,
            
            "current_phase": "initialization",
            "current_node": "start",
            "revision_count": 0,
            "max_revisions": self.settings.orchestration.max_revision_loops,
            
            "pending_approval": None,
            "approval_history": [],
            
            "error": None,
            "retry_count": 0,
            
            "started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": metadata or {},
        }
        
        # Configure for this run
        config = {
            "configurable": {
                "thread_id": initial_state["run_id"],
            }
        }
        
        # Execute the graph
        final_state = await self.app.ainvoke(initial_state, config)
        
        # Convert to RunState
        return self._state_to_run_state(final_state)
    
    def _state_to_run_state(self, state: GraphState) -> RunState:
        """Convert graph state to RunState schema."""
        
        # Collect artifact IDs
        artifacts = {}
        if state.get("performance_slice"):
            artifacts[ArtifactType.PERFORMANCE_SLICE] = str(uuid.uuid4())
        if state.get("campaign_calendar"):
            artifacts[ArtifactType.CAMPAIGN_CALENDAR] = str(uuid.uuid4())
        if state.get("campaign_brief"):
            artifacts[ArtifactType.CAMPAIGN_BRIEF] = state["campaign_brief"].campaign_id
        if state.get("copy_packet"):
            artifacts[ArtifactType.COPY_PACKET] = str(uuid.uuid4())
        if state.get("design_spec"):
            artifacts[ArtifactType.DESIGN_SPEC] = str(uuid.uuid4())
        if state.get("qa_report"):
            artifacts[ArtifactType.QA_REPORT] = str(uuid.uuid4())
        
        # Determine status
        if state.get("error"):
            status = "failed"
        elif state.get("pending_approval"):
            status = "paused"
        elif state["metadata"].get("completed_at"):
            status = "completed"
        else:
            status = "running"
        
        return RunState(
            run_id=state["run_id"],
            tenant_id=state["tenant_id"],
            brand_id=state["brand_id"],
            selected_month=state["selected_month"],
            prior_year_same_month=state["prior_year_same_month"],
            current_phase=state["current_phase"],
            current_node=state["current_node"],
            artifacts=artifacts,
            approvals=state["approval_history"],
            revision_count=state["revision_count"],
            status=status,
            error=state.get("error"),
            started_at=state["started_at"],
            completed_at=state["metadata"].get("completed_at"),
            metadata=state["metadata"],
        )