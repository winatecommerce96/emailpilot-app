"""
Report generation service that wraps your existing report tools
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import SessionLocal
from app.models import Report, Client

class ReportGeneratorService:
    def __init__(self):
        self.base_path = "/Users/Damon/klaviyo/klaviyo-audit-automation"
    
    def generate_weekly_report(self, report_id: int, client_id: Optional[int] = None):
        """Generate weekly report using existing scripts"""
        db = SessionLocal()
        
        try:
            # Get report record
            report = db.query(Report).filter(Report.id == report_id).first()
            if not report:
                return
            
            # Update status to running
            report.status = "running"
            db.commit()
            
            # Run your existing weekly report script
            result = subprocess.run(
                ["python3", "weekly_performance_update.py"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # Success
                report.status = "completed"
                report.completed_at = datetime.utcnow()
                report.slack_posted = "yes"
                report.data = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "type": "weekly",
                    "success": True,
                    "stdout": result.stdout[:1000] if result.stdout else None  # Truncate for storage
                }
            else:
                # Failed
                report.status = "failed"
                report.error_message = result.stderr[:1000] if result.stderr else "Unknown error"
                report.data = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "type": "weekly",
                    "success": False,
                    "error": result.stderr
                }
            
            db.commit()
            
        except subprocess.TimeoutExpired:
            report.status = "failed"
            report.error_message = "Report generation timed out"
            db.commit()
            
        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()
            
        finally:
            db.close()
    
    def generate_monthly_report(self, report_id: int, client_id: Optional[int] = None):
        """Generate monthly report using existing scripts"""
        db = SessionLocal()
        
        try:
            # Get report record
            report = db.query(Report).filter(Report.id == report_id).first()
            if not report:
                return
            
            # Update status to running
            report.status = "running"
            db.commit()
            
            # Run your existing monthly report script
            result = subprocess.run(
                ["python3", "monthly_performance_monitor.py"],
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=900  # 15 minute timeout
            )
            
            if result.returncode == 0:
                # Success
                report.status = "completed"
                report.completed_at = datetime.utcnow()
                report.slack_posted = "yes"
                report.data = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "type": "monthly",
                    "success": True,
                    "stdout": result.stdout[:1000] if result.stdout else None
                }
            else:
                # Failed
                report.status = "failed"
                report.error_message = result.stderr[:1000] if result.stderr else "Unknown error"
                report.data = {
                    "generated_at": datetime.utcnow().isoformat(),
                    "type": "monthly",
                    "success": False,
                    "error": result.stderr
                }
            
            db.commit()
            
        except subprocess.TimeoutExpired:
            report.status = "failed"
            report.error_message = "Report generation timed out"
            db.commit()
            
        except Exception as e:
            report.status = "failed"
            report.error_message = str(e)
            db.commit()
            
        finally:
            db.close()