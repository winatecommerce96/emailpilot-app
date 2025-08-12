"""
Goal management service that wraps your existing goal tools
"""

import os
import subprocess
import json
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import SessionLocal
from app.models import Goal, Client

class GoalManagerService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.base_path = "/Users/Damon/klaviyo/klaviyo-audit-automation"
    
    def generate_yearly_goals(self, client_id: int, year: int):
        """Generate AI-powered yearly goals for a client"""
        try:
            # Get client
            client = self.db.query(Client).filter(Client.id == client_id).first()
            if not client:
                return
            
            # Use your existing resumable goal generator
            result = subprocess.run([
                "python3", "-c", f"""
import sys
sys.path.append('{self.base_path}')
from resumable_goal_generator import ResumableGoalGenerator

generator = ResumableGoalGenerator()
generator.generate_batch_goals({year}, ['{client.name}'])
"""
            ], 
                cwd=self.base_path,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout for AI generation
            )
            
            if result.returncode == 0:
                # Load generated goals from your JSON files and import to database
                self._import_generated_goals(client_id, year)
            
        except Exception as e:
            print(f"Goal generation failed for client {client_id}: {e}")
    
    def _import_generated_goals(self, client_id: int, year: int):
        """Import goals from your JSON files into the database"""
        try:
            # Read from your monthly_specific_goals.json
            goals_file = os.path.join(self.base_path, "monthly_specific_goals.json")
            
            if os.path.exists(goals_file):
                with open(goals_file, 'r') as f:
                    data = json.load(f)
                
                # Get client name
                client = self.db.query(Client).filter(Client.id == client_id).first()
                if not client:
                    return
                
                # Import goals for this client and year
                monthly_goals = data.get("monthly_goals", {})
                
                for key, goal_data in monthly_goals.items():
                    if (goal_data.get("client_name") == client.name and 
                        goal_data.get("year") == year):
                        
                        # Check if goal already exists in database
                        existing = self.db.query(Goal).filter(
                            Goal.client_id == client_id,
                            Goal.year == year,
                            Goal.month == goal_data.get("month")
                        ).first()
                        
                        if existing:
                            # Update existing
                            existing.revenue_goal = goal_data.get("revenue_goal")
                            existing.calculation_method = goal_data.get("calculation_method", "ai_suggested")
                            existing.notes = goal_data.get("notes", "")
                            existing.human_override = goal_data.get("human_override", False)
                            existing.updated_at = datetime.utcnow()
                        else:
                            # Create new
                            new_goal = Goal(
                                client_id=client_id,
                                year=year,
                                month=goal_data.get("month"),
                                revenue_goal=goal_data.get("revenue_goal"),
                                calculation_method=goal_data.get("calculation_method", "ai_suggested"),
                                notes=goal_data.get("notes", ""),
                                human_override=goal_data.get("human_override", False)
                            )
                            self.db.add(new_goal)
                
                self.db.commit()
                
        except Exception as e:
            print(f"Failed to import goals: {e}")
    
    def get_progress(self):
        """Get goal generation progress from your existing system"""
        try:
            # Check your existing progress files
            progress_file = os.path.join(self.base_path, "goal_generation_progress.json")
            
            if os.path.exists(progress_file):
                with open(progress_file, 'r') as f:
                    return json.load(f)
            
            return {"status": "no_progress", "message": "No active goal generation"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}