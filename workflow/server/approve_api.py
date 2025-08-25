"""
Approval API for human gate resume
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
from datetime import datetime
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workflow.nodes.human_review import get_pending_review, approve_review

router = APIRouter(prefix="/api/workflow")


@router.get("/approve/{run_id}")
async def get_review(run_id: str) -> Dict[str, Any]:
    """Get pending review details"""
    try:
        review = get_pending_review(run_id)
        
        if not review:
            raise HTTPException(status_code=404, detail=f"No pending review for run_id: {run_id}")
        
        return {
            "success": True,
            "review": review
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{run_id}")
async def submit_approval(
    run_id: str,
    approved: bool = Body(...),
    notes: Optional[str] = Body("")
) -> Dict[str, Any]:
    """Submit approval decision for human gate"""
    try:
        # Process approval
        approval = approve_review(run_id, approved, notes)
        
        return {
            "success": True,
            "approval": approval,
            "message": "Approval submitted successfully. Workflow will resume."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def list_pending_reviews() -> Dict[str, Any]:
    """List all pending reviews"""
    try:
        # Import here to access PENDING_REVIEWS
        from workflow.nodes.human_review import PENDING_REVIEWS
        
        reviews = []
        for run_id, review_data in PENDING_REVIEWS.items():
            reviews.append({
                "run_id": run_id,
                "brand": review_data.get("brand"),
                "month": review_data.get("month"),
                "timestamp": review_data.get("timestamp"),
                "campaign_count": len(review_data.get("candidates", []))
            })
        
        return {
            "success": True,
            "count": len(reviews),
            "reviews": reviews
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/batch")
async def batch_approve(
    approvals: Dict[str, Dict[str, Any]] = Body(...)
) -> Dict[str, Any]:
    """Submit multiple approvals at once"""
    results = {}
    errors = {}
    
    for run_id, decision in approvals.items():
        try:
            approved = decision.get("approved", False)
            notes = decision.get("notes", "")
            
            approval = approve_review(run_id, approved, notes)
            results[run_id] = {
                "success": True,
                "approval": approval
            }
            
        except Exception as e:
            errors[run_id] = str(e)
    
    return {
        "success": len(errors) == 0,
        "results": results,
        "errors": errors
    }