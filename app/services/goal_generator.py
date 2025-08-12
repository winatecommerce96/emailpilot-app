"""
Resumable Goal Generator Service for EmailPilot
Handles AI goal generation with progress tracking and resume capability
"""

import json
import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from google.cloud import firestore
from google.cloud.secretmanager import SecretManagerServiceClient
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class ResumableGoalGenerator:
    def __init__(self):
        self.db = firestore.Client(project='emailpilot-438321')
        self.secret_client = SecretManagerServiceClient()
        self.model = None
        self.gemini_available = False
        
        # Initialize Gemini AI
        self._initialize_gemini()
        
        # Progress tracking collections
        self.progress_collection = 'goal_generation_progress'
        self.results_collection = 'goal_generation_results'
    
    def _initialize_gemini(self):
        """Initialize Gemini AI model"""
        try:
            # Get API key from Secret Manager
            api_key = self._get_secret('gemini-api-key')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.gemini_available = True
                logger.info("✅ Gemini AI connected for goal generation")
            else:
                logger.warning("⚠️ Gemini API key not found")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            self.gemini_available = False
    
    def _get_secret(self, secret_id: str) -> Optional[str]:
        """Get secret from Secret Manager"""
        try:
            name = f"projects/emailpilot-438321/secrets/{secret_id}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            logger.error(f"Error getting secret {secret_id}: {e}")
            return None
    
    async def get_progress(self, session_id: str) -> Dict[str, Any]:
        """Get generation progress for a session"""
        try:
            doc = self.db.collection(self.progress_collection).document(session_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
            return None
    
    async def save_progress(self, session_id: str, progress: Dict[str, Any]):
        """Save generation progress"""
        try:
            progress["last_updated"] = datetime.utcnow()
            self.db.collection(self.progress_collection).document(session_id).set(progress, merge=True)
            logger.info(f"Progress saved: {progress.get('completed_count', 0)}/{progress.get('total_count', 0)} clients")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    async def get_active_clients(self) -> List[Dict[str, Any]]:
        """Get list of active clients from Firestore"""
        try:
            clients = []
            docs = self.db.collection('clients').where('is_active', '==', True).stream()
            for doc in docs:
                client_data = doc.to_dict()
                client_data['id'] = doc.id
                clients.append(client_data)
            return clients
        except Exception as e:
            logger.error(f"Error getting clients: {e}")
            return []
    
    async def generate_monthly_goals_ai(self, client_name: str, client_id: str, 
                                       target_year: int, base_goal: float) -> Dict[int, float]:
        """Generate monthly goals using AI for seasonality"""
        if not self.gemini_available:
            # Fallback to simple calculation
            return {month: base_goal for month in range(1, 13)}
        
        try:
            prompt = f"""
            Generate monthly revenue goals for {client_name} for year {target_year}.
            Base monthly goal: ${base_goal:,.2f}
            
            Consider seasonality patterns and provide monthly goals.
            Return ONLY a JSON object with keys 1-12 (months) and revenue values.
            Example: {{"1": 15000, "2": 14000, "3": 16000, ...}}
            
            Make sure the yearly total is approximately {base_goal * 12:,.2f}
            """
            
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up response
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            monthly_goals = json.loads(text)
            
            # Validate and convert to proper format
            result = {}
            for month in range(1, 13):
                month_key = str(month)
                if month_key in monthly_goals:
                    result[month] = float(monthly_goals[month_key])
                else:
                    result[month] = base_goal
            
            return result
            
        except Exception as e:
            logger.error(f"AI generation failed for {client_name}: {e}")
            # Fallback to base goal for all months
            return {month: base_goal for month in range(1, 13)}
    
    async def generate_goals_for_client(self, client: Dict[str, Any], 
                                       target_year: int, session_id: str,
                                       selected_months: Optional[List[int]] = None) -> Dict[str, Any]:
        """Generate goals for a single client"""
        client_name = client.get('name', 'Unknown')
        client_id = client.get('id')
        
        logger.info(f"🎯 Generating goals for {client_name} ({target_year})")
        
        try:
            # Get current goal if exists
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # Try to get existing goal as base
            base_goal = 10000  # Default
            goals_query = self.db.collection('goals')\
                .where('client_id', '==', client_id)\
                .where('year', '==', current_year)\
                .limit(1)\
                .stream()
            
            for goal_doc in goals_query:
                goal_data = goal_doc.to_dict()
                if goal_data.get('revenue_goal'):
                    base_goal = goal_data['revenue_goal']
                    break
            
            # If no goal by ID, try by name
            if base_goal == 10000:
                goals_query = self.db.collection('goals')\
                    .where('client_id', '==', client_name)\
                    .where('year', '==', current_year)\
                    .limit(1)\
                    .stream()
                
                for goal_doc in goals_query:
                    goal_data = goal_doc.to_dict()
                    if goal_data.get('revenue_goal'):
                        base_goal = goal_data['revenue_goal']
                        break
            
            # Generate monthly goals
            start_time = time.time()
            monthly_goals = await self.generate_monthly_goals_ai(
                client_name, client_id, target_year, base_goal
            )
            generation_time = time.time() - start_time
            
            # Filter to selected months if specified
            months_to_generate = selected_months if selected_months else list(monthly_goals.keys())
            
            # Save goals to Firestore
            batch = self.db.batch()
            goals_saved = 0
            actual_goals = {}
            
            for month in months_to_generate:
                if month in monthly_goals:
                    goal_amount = monthly_goals[month]
                    actual_goals[month] = goal_amount
                    
                    # Create goal document
                    goal_ref = self.db.collection('goals').document()
                    goal_data = {
                        'client_id': client_id,
                        'client_name': client_name,
                        'year': target_year,
                        'month': month,
                        'revenue_goal': goal_amount,
                        'calculation_method': 'ai_generated',
                        'notes': f'AI-generated goal for {target_year}-{month:02d}',
                        'confidence': 'medium',
                        'human_override': False,
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow(),
                        'generation_session': session_id
                    }
                    batch.set(goal_ref, goal_data)
                    goals_saved += 1
            
            # Commit batch
            batch.commit()
            
            logger.info(f"✅ {client_name}: Generated {goals_saved} monthly goals in {generation_time:.1f}s")
            
            return {
                "status": "success",
                "client": client_name,
                "client_id": client_id,
                "year": target_year,
                "goals_generated": goals_saved,
                "generation_time": generation_time,
                "total_yearly_goal": sum(actual_goals.values()) if actual_goals else 0,
                "monthly_goals": actual_goals,
                "selected_months": months_to_generate,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"❌ {client_name}: Generation failed - {e}")
            return {
                "status": "failed",
                "client": client_name,
                "client_id": client_id,
                "year": target_year,
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    async def start_batch_generation(self, target_year: int, 
                                   client_ids: Optional[List[str]] = None,
                                   selected_months: Optional[List[int]] = None) -> str:
        """Start a new batch generation session"""
        try:
            # Get clients
            all_clients = await self.get_active_clients()
            
            if client_ids:
                # Filter to selected clients
                clients = [c for c in all_clients if c['id'] in client_ids]
            else:
                clients = all_clients
            
            # Create session
            session_id = f"goal_gen_{int(time.time())}"
            progress = {
                "session_id": session_id,
                "started_at": datetime.utcnow(),
                "target_year": target_year,
                "selected_months": selected_months,
                "total_count": len(clients),
                "completed_count": 0,
                "failed_count": 0,
                "completed_clients": [],
                "failed_clients": [],
                "current_client": None,
                "status": "running",
                "clients": [{"id": c['id'], "name": c['name']} for c in clients]
            }
            
            # Save initial progress
            await self.save_progress(session_id, progress)
            
            # Start generation in background
            asyncio.create_task(self._run_batch_generation(session_id, clients, target_year, selected_months))
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting batch generation: {e}")
            raise
    
    async def _run_batch_generation(self, session_id: str, clients: List[Dict], target_year: int, selected_months: Optional[List[int]] = None):
        """Run batch generation (background task)"""
        try:
            progress = await self.get_progress(session_id)
            results = []
            
            for i, client in enumerate(clients):
                # Update current client
                progress['current_client'] = client['name']
                await self.save_progress(session_id, progress)
                
                # Generate goals
                result = await self.generate_goals_for_client(client, target_year, session_id, selected_months)
                results.append(result)
                
                # Update progress
                if result['status'] == 'success':
                    progress['completed_clients'].append(client['id'])
                    progress['completed_count'] += 1
                else:
                    progress['failed_clients'].append(client['id'])
                    progress['failed_count'] += 1
                
                progress['current_client'] = None
                await self.save_progress(session_id, progress)
                
                # Small delay to prevent overload
                await asyncio.sleep(2)
            
            # Mark as completed
            progress['status'] = 'completed'
            progress['completed_at'] = datetime.utcnow()
            await self.save_progress(session_id, progress)
            
            # Save results
            self.db.collection(self.results_collection).document(session_id).set({
                'session_id': session_id,
                'target_year': target_year,
                'results': results,
                'summary': {
                    'total_clients': len(clients),
                    'successful': progress['completed_count'],
                    'failed': progress['failed_count'],
                    'total_yearly_revenue': sum(r['total_yearly_goal'] for r in results if r['status'] == 'success')
                },
                'created_at': datetime.utcnow()
            })
            
            logger.info(f"🎉 Batch generation {session_id} completed!")
            
        except Exception as e:
            logger.error(f"Error in batch generation: {e}")
            progress = await self.get_progress(session_id)
            if progress:
                progress['status'] = 'error'
                progress['error'] = str(e)
                await self.save_progress(session_id, progress)
    
    async def resume_generation(self, session_id: str) -> bool:
        """Resume a paused generation"""
        try:
            progress = await self.get_progress(session_id)
            
            if not progress:
                logger.error(f"Session {session_id} not found")
                return False
            
            if progress['status'] == 'completed':
                logger.info("Session already completed")
                return False
            
            if progress['status'] != 'paused':
                logger.info(f"Session status is {progress['status']}, cannot resume")
                return False
            
            # Get remaining clients
            completed_ids = set(progress.get('completed_clients', []))
            failed_ids = set(progress.get('failed_clients', []))
            all_client_ids = [c['id'] for c in progress.get('clients', [])]
            
            remaining_ids = [cid for cid in all_client_ids 
                           if cid not in completed_ids and cid not in failed_ids]
            
            if not remaining_ids:
                progress['status'] = 'completed'
                await self.save_progress(session_id, progress)
                return True
            
            # Get client details
            remaining_clients = []
            for client_id in remaining_ids:
                client_doc = self.db.collection('clients').document(client_id).get()
                if client_doc.exists:
                    client_data = client_doc.to_dict()
                    client_data['id'] = client_id
                    remaining_clients.append(client_data)
            
            # Resume generation
            progress['status'] = 'running'
            await self.save_progress(session_id, progress)
            
            # Continue in background
            asyncio.create_task(
                self._run_batch_generation(session_id, remaining_clients, progress['target_year'])
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error resuming generation: {e}")
            return False
    
    async def pause_generation(self, session_id: str) -> bool:
        """Pause a running generation"""
        try:
            progress = await self.get_progress(session_id)
            
            if not progress:
                return False
            
            if progress['status'] == 'running':
                progress['status'] = 'paused'
                progress['paused_at'] = datetime.utcnow()
                await self.save_progress(session_id, progress)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error pausing generation: {e}")
            return False
    
    async def get_generation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of generation sessions"""
        try:
            sessions = []
            docs = self.db.collection(self.progress_collection)\
                .order_by('started_at', direction=firestore.Query.DESCENDING)\
                .limit(limit)\
                .stream()
            
            for doc in docs:
                session_data = doc.to_dict()
                sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting generation history: {e}")
            return []