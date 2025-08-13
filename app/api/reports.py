# app/api/reports.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/")
def list_reports():
    # Return something valid so the UI stops 404'ing; fill in later.
    return {
        "available": [
            {"id": "monthly", "name": "Monthly Summary"},
            {"id": "weekly", "name": "Weekly Snapshot"},
        ]
    }