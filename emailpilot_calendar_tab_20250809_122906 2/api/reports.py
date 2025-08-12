"""
Reports API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import Report, Client
from app.services.report_generator import ReportGeneratorService
from app.schemas.report import ReportResponse, ReportCreate

router = APIRouter()

@router.get("/", response_model=List[ReportResponse])
async def get_reports(
    limit: int = 50,
    client_id: Optional[int] = None,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of reports"""
    query = db.query(Report)
    
    if client_id:
        query = query.filter(Report.client_id == client_id)
    
    if report_type:
        query = query.filter(Report.type == report_type)
    
    reports = query.order_by(Report.created_at.desc()).limit(limit).all()
    return reports

@router.post("/weekly/generate")
async def generate_weekly_report(
    background_tasks: BackgroundTasks,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Generate weekly performance report"""
    
    # Create report record
    report = Report(
        client_id=client_id,
        type="weekly",
        title=f"Weekly Report - {datetime.now().strftime('%Y-%m-%d')}",
        status="pending"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Start background task
    report_service = ReportGeneratorService()
    background_tasks.add_task(
        report_service.generate_weekly_report,
        report.id,
        client_id
    )
    
    return {
        "message": "Weekly report generation started",
        "report_id": report.id,
        "status": "pending"
    }

@router.post("/monthly/generate")
async def generate_monthly_report(
    background_tasks: BackgroundTasks,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Generate monthly performance report"""
    
    # Create report record
    report = Report(
        client_id=client_id,
        type="monthly",
        title=f"Monthly Report - {datetime.now().strftime('%Y-%m')}",
        status="pending"
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Start background task
    report_service = ReportGeneratorService()
    background_tasks.add_task(
        report_service.generate_monthly_report,
        report.id,
        client_id
    )
    
    return {
        "message": "Monthly report generation started",
        "report_id": report.id,
        "status": "pending"
    }

@router.get("/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get specific report"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

@router.get("/latest/weekly")
async def get_latest_weekly_report(
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get latest weekly report"""
    query = db.query(Report).filter(Report.type == "weekly")
    
    if client_id:
        query = query.filter(Report.client_id == client_id)
    
    report = query.order_by(Report.created_at.desc()).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="No weekly reports found")
    
    return report

@router.get("/latest/monthly")
async def get_latest_monthly_report(
    client_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get latest monthly report"""
    query = db.query(Report).filter(Report.type == "monthly")
    
    if client_id:
        query = query.filter(Report.client_id == client_id)
    
    report = query.order_by(Report.created_at.desc()).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="No monthly reports found")
    
    return report