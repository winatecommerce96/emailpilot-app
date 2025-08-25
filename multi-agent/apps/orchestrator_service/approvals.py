"""
Approval management for human-in-the-loop controls.
Handles approval requests, timeouts, and persistence.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import uuid
from enum import Enum

from .schemas import ApprovalStatus, ArtifactType
from .config import get_settings


class ApprovalRequest:
    """Represents an approval request."""
    
    def __init__(
        self,
        request_id: str,
        artifact_type: ArtifactType,
        artifact_id: str,
        artifact_data: Dict[str, Any],
        approver_role: str,
        requested_at: datetime,
        timeout_hours: int = 24,
    ):
        self.request_id = request_id
        self.artifact_type = artifact_type
        self.artifact_id = artifact_id
        self.artifact_data = artifact_data
        self.approver_role = approver_role
        self.requested_at = requested_at
        self.timeout_at = requested_at + timedelta(hours=timeout_hours)
        self.status = ApprovalStatus.PENDING
        self.decision: Optional[ApprovalStatus] = None
        self.approver_notes: Optional[str] = None
        self.decided_at: Optional[datetime] = None
        self.decided_by: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if approval request has expired."""
        return datetime.utcnow() > self.timeout_at
    
    def approve(
        self,
        approver: str,
        notes: Optional[str] = None,
        with_fixes: bool = False
    ):
        """Approve the request."""
        self.status = ApprovalStatus.APPROVED_WITH_FIXES if with_fixes else ApprovalStatus.APPROVED
        self.decision = self.status
        self.approver_notes = notes
        self.decided_at = datetime.utcnow()
        self.decided_by = approver
    
    def reject(self, approver: str, notes: str):
        """Reject the request."""
        self.status = ApprovalStatus.REJECTED
        self.decision = self.status
        self.approver_notes = notes
        self.decided_at = datetime.utcnow()
        self.decided_by = approver
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "request_id": self.request_id,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "artifact_data": self.artifact_data,
            "approver_role": self.approver_role,
            "requested_at": self.requested_at.isoformat(),
            "timeout_at": self.timeout_at.isoformat(),
            "status": self.status,
            "decision": self.decision,
            "approver_notes": self.approver_notes,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "decided_by": self.decided_by,
        }


class ApprovalManager:
    """Manages approval workflows and persistence."""
    
    def __init__(self):
        self.settings = get_settings()
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_history: List[ApprovalRequest] = []
        
        # In production, this would use Firestore
        self._storage = {}
    
    async def request_approval(
        self,
        artifact_type: ArtifactType,
        artifact_id: str,
        artifact_data: Dict[str, Any],
        approver_role: str = "campaign_manager",
        timeout_hours: Optional[int] = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        
        if timeout_hours is None:
            timeout_hours = self.settings.orchestration.approval_timeout_hours
        
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_data=artifact_data,
            approver_role=approver_role,
            requested_at=datetime.utcnow(),
            timeout_hours=timeout_hours,
        )
        
        # Store the request
        self.pending_approvals[request.request_id] = request
        await self._persist_request(request)
        
        # In production, this would send notifications
        await self._notify_approvers(request)
        
        return request
    
    async def wait_for_approval(
        self,
        request_id: str,
        poll_interval_seconds: int = 10,
    ) -> ApprovalRequest:
        """Wait for an approval decision or timeout."""
        
        request = self.pending_approvals.get(request_id)
        if not request:
            raise ValueError(f"Approval request {request_id} not found")
        
        # In development with auto-approve, immediately approve
        if self.settings.orchestration.auto_approve_in_dev:
            await asyncio.sleep(1)  # Simulate processing
            request.approve(
                approver="auto_approver",
                notes="Auto-approved in development mode"
            )
            await self._complete_approval(request)
            return request
        
        # Poll for approval or timeout
        while request.status == ApprovalStatus.PENDING:
            if request.is_expired():
                request.status = ApprovalStatus.REJECTED
                request.approver_notes = "Approval request timed out"
                await self._complete_approval(request)
                break
            
            # Check for updates from storage
            await self._refresh_request(request)
            
            if request.status == ApprovalStatus.PENDING:
                await asyncio.sleep(poll_interval_seconds)
        
        return request
    
    async def approve(
        self,
        request_id: str,
        approver: str,
        notes: Optional[str] = None,
        with_fixes: bool = False,
    ) -> ApprovalRequest:
        """Approve a pending request."""
        
        request = self.pending_approvals.get(request_id)
        if not request:
            # Try to load from storage
            request = await self._load_request(request_id)
            if not request:
                raise ValueError(f"Approval request {request_id} not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending (status: {request.status})")
        
        request.approve(approver, notes, with_fixes)
        await self._complete_approval(request)
        
        return request
    
    async def reject(
        self,
        request_id: str,
        approver: str,
        notes: str,
    ) -> ApprovalRequest:
        """Reject a pending request."""
        
        request = self.pending_approvals.get(request_id)
        if not request:
            # Try to load from storage
            request = await self._load_request(request_id)
            if not request:
                raise ValueError(f"Approval request {request_id} not found")
        
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending (status: {request.status})")
        
        request.reject(approver, notes)
        await self._complete_approval(request)
        
        return request
    
    async def get_pending_approvals(
        self,
        approver_role: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        
        pending = list(self.pending_approvals.values())
        
        if approver_role:
            pending = [r for r in pending if r.approver_role == approver_role]
        
        # Filter out expired requests
        active = []
        for request in pending:
            if request.is_expired():
                request.status = ApprovalStatus.REJECTED
                request.approver_notes = "Approval request timed out"
                await self._complete_approval(request)
            else:
                active.append(request)
        
        return active
    
    async def get_approval_history(
        self,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """Get approval history."""
        
        history = self.approval_history[-limit:]
        
        if artifact_type:
            history = [r for r in history if r.artifact_type == artifact_type]
        
        return history
    
    # Private methods for storage (would use Firestore in production)
    
    async def _persist_request(self, request: ApprovalRequest):
        """Persist approval request to storage."""
        self._storage[request.request_id] = request.to_dict()
    
    async def _refresh_request(self, request: ApprovalRequest):
        """Refresh request from storage."""
        stored = self._storage.get(request.request_id)
        if stored and stored["status"] != ApprovalStatus.PENDING:
            # Update from storage
            request.status = stored["status"]
            request.decision = stored["decision"]
            request.approver_notes = stored["approver_notes"]
            request.decided_at = datetime.fromisoformat(stored["decided_at"]) if stored["decided_at"] else None
            request.decided_by = stored["decided_by"]
    
    async def _load_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load request from storage."""
        stored = self._storage.get(request_id)
        if not stored:
            return None
        
        request = ApprovalRequest(
            request_id=stored["request_id"],
            artifact_type=stored["artifact_type"],
            artifact_id=stored["artifact_id"],
            artifact_data=stored["artifact_data"],
            approver_role=stored["approver_role"],
            requested_at=datetime.fromisoformat(stored["requested_at"]),
            timeout_hours=24,  # Calculate from timeout_at
        )
        
        request.status = stored["status"]
        request.decision = stored["decision"]
        request.approver_notes = stored["approver_notes"]
        request.decided_at = datetime.fromisoformat(stored["decided_at"]) if stored["decided_at"] else None
        request.decided_by = stored["decided_by"]
        
        return request
    
    async def _complete_approval(self, request: ApprovalRequest):
        """Complete an approval request."""
        
        # Move to history
        if request.request_id in self.pending_approvals:
            del self.pending_approvals[request.request_id]
        
        self.approval_history.append(request)
        
        # Update storage
        await self._persist_request(request)
    
    async def _notify_approvers(self, request: ApprovalRequest):
        """Send notifications to approvers."""
        # In production, this would send emails/Slack messages
        # For now, just log
        print(f"Approval requested: {request.request_id}")
        print(f"  Type: {request.artifact_type}")
        print(f"  Role: {request.approver_role}")
        print(f"  Timeout: {request.timeout_at}")


# CLI interface for manual approvals during development
class ApprovalCLI:
    """Command-line interface for handling approvals."""
    
    def __init__(self, manager: ApprovalManager):
        self.manager = manager
    
    async def interactive_approve(self):
        """Interactive approval session."""
        
        while True:
            # Get pending approvals
            pending = await self.manager.get_pending_approvals()
            
            if not pending:
                print("No pending approvals.")
                break
            
            print(f"\n{len(pending)} pending approval(s):")
            for i, request in enumerate(pending):
                print(f"\n[{i+1}] {request.artifact_type} - {request.artifact_id}")
                print(f"    Requested: {request.requested_at}")
                print(f"    Timeout: {request.timeout_at}")
                print(f"    Role: {request.approver_role}")
            
            # Get user choice
            choice = input("\nSelect approval (number) or 'q' to quit: ")
            
            if choice.lower() == 'q':
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(pending):
                    request = pending[idx]
                    await self._handle_single_approval(request)
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")
    
    async def _handle_single_approval(self, request: ApprovalRequest):
        """Handle a single approval request."""
        
        print(f"\nReviewing: {request.artifact_type} - {request.artifact_id}")
        print("Artifact data:")
        for key, value in request.artifact_data.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
        
        decision = input("\nDecision (a=approve, f=approve with fixes, r=reject): ")
        
        if decision.lower() == 'a':
            notes = input("Notes (optional): ")
            await self.manager.approve(
                request.request_id,
                approver="cli_user",
                notes=notes if notes else None
            )
            print("✓ Approved")
        
        elif decision.lower() == 'f':
            notes = input("Required fixes: ")
            await self.manager.approve(
                request.request_id,
                approver="cli_user",
                notes=notes,
                with_fixes=True
            )
            print("✓ Approved with fixes")
        
        elif decision.lower() == 'r':
            notes = input("Rejection reason: ")
            await self.manager.reject(
                request.request_id,
                approver="cli_user",
                notes=notes
            )
            print("✗ Rejected")
        
        else:
            print("Invalid decision")