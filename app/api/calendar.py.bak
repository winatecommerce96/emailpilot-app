"""
Calendar API Router for EmailPilot - Unified Deployment
Integrates calendar generation workflow from emailpilot-simple with Clerk authentication
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field
import uuid
import logging
import os
import sys
from pathlib import Path
from google.cloud import firestore

# Import authentication dependency
from app.api.clerk_auth import verify_clerk_session
from app.deps.firestore import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Global state for lazy-initialized calendar components
_calendar_state = {
    'initialized': False,
    'calendar_agent': None,
    'calendar_tool': None,
    'mcp_client': None,
    'rag_client': None,
    'firestore_client': None,
    'cache': None,
    'storage_client': None,
    'workflow_status': {}  # In-memory job status cache
}

# Pydantic models for request/response
class WorkflowRequest(BaseModel):
    """Request model for workflow execution"""
    client_name: str = Field(..., description="Client name for the workflow")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    stage: str = Field(default='full', description="Workflow stage: 'full', 'rag', 'mcp', 'generate'")
    prompt_name: Optional[str] = Field(default=None, description="Optional custom prompt name")

class PromptRequest(BaseModel):
    """Request model for prompt management"""
    content: str = Field(..., description="Prompt template content")

class RAGRequest(BaseModel):
    """Request model for RAG data fetching"""
    client_name: str = Field(..., description="Client name")
    query: Optional[str] = Field(default=None, description="Optional search query")

class MCPRequest(BaseModel):
    """Request model for MCP data fetching"""
    client_name: str = Field(..., description="Client name")
    data_types: List[str] = Field(default=['campaigns', 'flows'], description="Data types to fetch")

# Pydantic models for calendar events CRUD
class CalendarEventCreate(BaseModel):
    """Request model for creating a calendar event"""
    client_id: str = Field(..., description="Client ID")
    title: str = Field(..., description="Event title")
    event_date: str = Field(..., description="Event date (YYYY-MM-DD or ISO format)")
    description: Optional[str] = Field(None, description="Event description")
    content: Optional[str] = Field(None, description="Event content")
    color: Optional[str] = Field("bg-gray-200 text-gray-800", description="Event color class")
    event_type: Optional[str] = Field("campaign", description="Event type")
    status: Optional[str] = Field("planned", description="Event status")
    send_time: Optional[str] = Field(None, description="Send time (HH:MM)")
    segment: Optional[str] = Field(None, description="Target segment")
    subject_a: Optional[str] = Field(None, description="Subject line A")
    subject_b: Optional[str] = Field(None, description="Subject line B")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class CalendarEventUpdate(BaseModel):
    """Request model for updating a calendar event"""
    title: Optional[str] = None
    event_date: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    send_time: Optional[str] = None
    segment: Optional[str] = None
    subject_a: Optional[str] = None
    subject_b: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BulkEventsCreate(BaseModel):
    """Request model for bulk creating events"""
    client_id: str = Field(..., description="Client ID")
    events: List[CalendarEventCreate] = Field(..., description="List of events to create")

def standard_response(success: bool, data: Any = None, error: Optional[str] = None) -> Dict[str, Any]:
    """Standardized API response format"""
    response = {
        'success': success,
        'timestamp': datetime.utcnow().isoformat()
    }
    if data is not None:
        response['data'] = data
    if error is not None:
        response['error'] = error
    return response

async def initialize_calendar_components():
    """
    Lazy initialization of calendar components on first request.

    This avoids blocking the app startup and allows the auth system
    to be available immediately while calendar components load.
    """
    if _calendar_state['initialized']:
        return

    logger.info("Initializing calendar components...")

    try:
        # Add emailpilot-simple to Python path
        emailpilot_simple_path = str(Path(__file__).parent.parent.parent.parent / "emailpilot-simple")
        if emailpilot_simple_path not in sys.path:
            sys.path.insert(0, emailpilot_simple_path)

        # Import calendar components
        from tools import CalendarTool
        from agents.calendar_agent import CalendarAgent
        from data.native_mcp_client import NativeMCPClient as MCPClient
        from data.enhanced_rag_client import EnhancedRAGClient as RAGClient
        from data.firestore_client import FirestoreClient
        from data.mcp_cache import MCPCache
        from google.cloud import storage

        # Initialize components
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        if not project_id or not anthropic_api_key:
            raise RuntimeError("Missing required environment variables: GOOGLE_CLOUD_PROJECT or ANTHROPIC_API_KEY")

        # Initialize data layer clients
        rag_base_path = Path(emailpilot_simple_path) / "rag_data"
        rag_client = RAGClient(rag_base_path=rag_base_path)

        firestore_client = FirestoreClient(project_id=project_id)

        cache = MCPCache()

        mcp_client = MCPClient(project_id=project_id)
        await mcp_client.__aenter__()

        # Initialize calendar agent
        model = "claude-sonnet-4-20250514"
        calendar_agent = CalendarAgent(
            anthropic_api_key=anthropic_api_key,
            mcp_client=mcp_client,
            rag_client=rag_client,
            firestore_client=firestore_client,
            cache=cache,
            model=model
        )

        # Initialize storage client for production
        storage_client = None
        if os.getenv('ENVIRONMENT') == 'production':
            try:
                storage_client = storage.Client(project=project_id)
                logger.info("Production: Using GCS for output storage")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {e}")

        # Initialize calendar tool
        output_dir = Path(emailpilot_simple_path) / "outputs"
        calendar_tool = CalendarTool(
            calendar_agent=calendar_agent,
            output_dir=output_dir,
            validate_outputs=True,
            storage_client=storage_client
        )

        # Store in global state
        _calendar_state['calendar_agent'] = calendar_agent
        _calendar_state['calendar_tool'] = calendar_tool
        _calendar_state['mcp_client'] = mcp_client
        _calendar_state['rag_client'] = rag_client
        _calendar_state['firestore_client'] = firestore_client
        _calendar_state['cache'] = cache
        _calendar_state['storage_client'] = storage_client
        _calendar_state['initialized'] = True

        logger.info("Calendar components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize calendar components: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize calendar system: {str(e)}"
        )

async def execute_workflow_background(
    job_id: str,
    client_name: str,
    start_date: str,
    end_date: str,
    user_id: str,
    calendar_tool,
    db: firestore.Client
):
    """
    Execute workflow in background and update job state.

    Job status is persisted to Firestore for durability across server restarts.
    """
    try:
        # Update status to stage-1
        job_data = {
            'status': 'stage-1',
            'current_stage': 1,
            'updated_at': datetime.utcnow().isoformat()
        }
        _calendar_state['workflow_status'][job_id].update(job_data)

        # Persist to Firestore
        db.collection("calendar_jobs").document(job_id).update(job_data)

        logger.info(f"[Job {job_id}] Starting workflow for {client_name} ({start_date} to {end_date})")

        # Execute complete workflow
        result = await calendar_tool.run_workflow(
            client_name=client_name,
            start_date=start_date,
            end_date=end_date,
            save_outputs=True
        )

        # Update final status
        if result.get('success', False):
            final_data = {
                'status': 'completed',
                'current_stage': None,
                'results': result,
                'updated_at': datetime.utcnow().isoformat()
            }
            logger.info(f"[Job {job_id}] Workflow completed successfully")
        else:
            final_data = {
                'status': 'failed',
                'current_stage': None,
                'error': result.get('error', 'Unknown error'),
                'updated_at': datetime.utcnow().isoformat()
            }
            logger.error(f"[Job {job_id}] Workflow failed: {final_data['error']}")

        # Update both memory and Firestore
        _calendar_state['workflow_status'][job_id].update(final_data)
        db.collection("calendar_jobs").document(job_id).update(final_data)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Job {job_id}] Workflow execution error: {error_msg}")

        error_data = {
            'status': 'failed',
            'current_stage': None,
            'error': error_msg,
            'updated_at': datetime.utcnow().isoformat()
        }

        # Update both memory and Firestore
        _calendar_state['workflow_status'][job_id].update(error_data)
        db.collection("calendar_jobs").document(job_id).update(error_data)

@router.get("/health")
async def calendar_health(
    current_user: dict = Depends(verify_clerk_session)
):
    """
    Health check endpoint for calendar API.

    Requires authentication.
    """
    return standard_response(
        success=True,
        data={
            'status': 'healthy',
            'service': 'calendar',
            'initialized': _calendar_state['initialized'],
            'user': current_user.get('email') or current_user.get('user_id')
        }
    )

@router.post("/workflow/run")
async def run_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db)
):
    """
    Execute workflow stage or full workflow.

    Requires authentication. Jobs are associated with the authenticated user.

    For full workflow:
    - Returns immediately with job_id
    - Workflow executes in background
    - Poll GET /calendar/jobs/{job_id} for status

    For individual stages:
    - Executes synchronously
    - Returns results directly
    """
    await initialize_calendar_components()

    user_id = current_user.get("user_id") or current_user.get("email")
    calendar_tool = _calendar_state['calendar_tool']

    client_name = request.client_name
    start_date = request.start_date
    end_date = request.end_date
    stage = request.stage
    prompt_name = request.prompt_name

    logger.info(f"User {user_id} requested workflow: client={client_name}, stage={stage}")

    if stage == 'full':
        # Full workflow - execute in background
        job_id = str(uuid.uuid4())

        job_data = {
            'job_id': job_id,
            'status': 'queued',
            'client_name': client_name,
            'start_date': start_date,
            'end_date': end_date,
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'current_stage': None,
            'results': None,
            'error': None
        }

        # Store in memory
        _calendar_state['workflow_status'][job_id] = job_data

        # Persist to Firestore
        db.collection("calendar_jobs").document(job_id).set(job_data)

        # Schedule background task
        background_tasks.add_task(
            execute_workflow_background,
            job_id,
            client_name,
            start_date,
            end_date,
            user_id,
            calendar_tool,
            db
        )

        logger.info(f"[Job {job_id}] Queued for user {user_id}")

        return standard_response(
            success=True,
            data={
                'job_id': job_id,
                'status': 'queued',
                'message': 'Workflow started in background. Poll /api/calendar/jobs/{job_id} for status.'
            }
        )

    # Individual stage execution (synchronous)
    try:
        if stage == 'rag':
            result = await calendar_tool.calendar_agent.rag_client.get_client_context(client_name)
        elif stage == 'mcp':
            result = await calendar_tool.calendar_agent.fetch_all_klaviyo_data(client_name)
        elif stage == 'generate':
            result = await calendar_tool.calendar_agent.generate_calendar(
                client_name=client_name,
                start_date=start_date,
                end_date=end_date,
                prompt_name=prompt_name
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stage: {stage}. Must be 'full', 'rag', 'mcp', or 'generate'"
            )

        logger.info(f"User {user_id} completed stage {stage} for {client_name}")

        return standard_response(
            success=True,
            data={
                'stage': stage,
                'result': result
            }
        )

    except Exception as e:
        logger.error(f"Stage {stage} error for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    db: firestore.Client = Depends(get_db)
):
    """
    Get status and results for a workflow job.

    Requires authentication. Users can only access their own jobs.
    """
    user_id = current_user.get("user_id") or current_user.get("email")

    # Try memory first (fast path)
    if job_id in _calendar_state['workflow_status']:
        job_data = _calendar_state['workflow_status'][job_id]

        # Verify user owns this job
        if job_data.get('user_id') != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this job"
            )

        return standard_response(success=True, data=job_data)

    # Fetch from Firestore (durability path)
    job_doc = db.collection("calendar_jobs").document(job_id).get()

    if not job_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job_data = job_doc.to_dict()

    # Verify user owns this job
    if job_data.get('user_id') != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this job"
        )

    # Cache in memory for subsequent requests
    _calendar_state['workflow_status'][job_id] = job_data

    return standard_response(success=True, data=job_data)

@router.get("/prompts/{prompt_name}")
async def get_prompt(
    prompt_name: str
):
    """
    Get a prompt template by name.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        prompt_path = Path(__file__).parent.parent.parent.parent / "emailpilot-simple" / "prompts" / f"{prompt_name}.yaml"

        if not prompt_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt '{prompt_name}' not found"
            )

        with open(prompt_path, 'r') as f:
            import yaml
            prompt_data = yaml.safe_load(f)

        logger.info(f"User {current_user.get('email')} retrieved prompt: {prompt_name}")

        return standard_response(success=True, data=prompt_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.put("/prompts/{prompt_name}")
async def update_prompt(
    prompt_name: str,
    request: PromptRequest
):
    """
    Update a prompt template.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        prompt_path = Path(__file__).parent.parent.parent.parent / "emailpilot-simple" / "prompts" / f"{prompt_name}.yaml"

        # Backup existing prompt
        if prompt_path.exists():
            backup_path = prompt_path.with_suffix('.yaml.bak')
            import shutil
            shutil.copy2(prompt_path, backup_path)

        # Write new prompt
        import yaml
        with open(prompt_path, 'w') as f:
            yaml.dump({'content': request.content}, f)

        logger.info(f"User {current_user.get('email')} updated prompt: {prompt_name}")

        return standard_response(
            success=True,
            data={'message': f"Prompt '{prompt_name}' updated successfully"}
        )

    except Exception as e:
        logger.error(f"Error updating prompt {prompt_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/rag/data")
async def fetch_rag_data(
    request: RAGRequest
):
    """
    Fetch RAG (Retrieval-Augmented Generation) data for a client.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        rag_client = _calendar_state['rag_client']

        if request.query:
            result = await rag_client.search(request.client_name, request.query)
        else:
            result = await rag_client.get_client_context(request.client_name)

        logger.info(f"User {current_user.get('email')} fetched RAG data for {request.client_name}")

        return standard_response(success=True, data=result)

    except Exception as e:
        logger.error(f"Error fetching RAG data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/mcp/data")
async def fetch_mcp_data(
    request: MCPRequest
):
    """
    Fetch Klaviyo data via MCP (Model Context Protocol) servers.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        calendar_agent = _calendar_state['calendar_agent']

        result = await calendar_agent.fetch_all_klaviyo_data(
            client_name=request.client_name,
            data_types=request.data_types
        )

        logger.info(f"User {current_user.get('email')} fetched MCP data for {request.client_name}")

        return standard_response(success=True, data=result)

    except Exception as e:
        logger.error(f"Error fetching MCP data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/outputs/{output_type}")
async def get_workflow_outputs(
    output_type: str,
    client_name: Optional[str] = None
):
    """
    Retrieve workflow outputs (calendars, summaries, etc.).

    Requires authentication.

    output_type: 'calendar', 'summary', 'rag', 'mcp', 'all'
    """
    await initialize_calendar_components()

    try:
        storage_client = _calendar_state['storage_client']
        output_dir = Path(__file__).parent.parent.parent.parent / "emailpilot-simple" / "outputs"

        # Production: fetch from GCS
        if storage_client:
            bucket_name = os.getenv('GCS_BUCKET_NAME', 'emailpilot-outputs')
            bucket = storage_client.bucket(bucket_name)

            prefix = f"{client_name}/" if client_name else ""
            if output_type != 'all':
                prefix += f"{output_type}_"

            blobs = list(bucket.list_blobs(prefix=prefix, max_results=100))

            outputs = []
            for blob in blobs:
                if output_type == 'all' or output_type in blob.name:
                    outputs.append({
                        'name': blob.name,
                        'size': blob.size,
                        'updated': blob.updated.isoformat(),
                        'url': blob.public_url
                    })

            logger.info(f"User {current_user.get('email')} fetched {len(outputs)} outputs from GCS")

            return standard_response(success=True, data={'outputs': outputs})

        # Development: fetch from local filesystem
        outputs = []

        if client_name:
            client_dir = output_dir / client_name
            if client_dir.exists():
                for file_path in client_dir.glob('*'):
                    if output_type == 'all' or output_type in file_path.stem:
                        outputs.append({
                            'name': file_path.name,
                            'path': str(file_path),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })
        else:
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    if output_type == 'all' or output_type in file_path.stem:
                        outputs.append({
                            'name': file_path.name,
                            'path': str(file_path.relative_to(output_dir)),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })

        logger.info(f"User {current_user.get('email')} fetched {len(outputs)} outputs from filesystem")

        return standard_response(success=True, data={'outputs': outputs})

    except Exception as e:
        logger.error(f"Error fetching outputs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/cache")
async def view_cache(
    current_user: dict = Depends(verify_clerk_session)
):
    """
    View MCP cache statistics.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        cache = _calendar_state['cache']

        stats = {
            'size': len(cache._cache) if hasattr(cache, '_cache') else 0,
            'keys': list(cache._cache.keys()) if hasattr(cache, '_cache') else []
        }

        logger.info(f"User {current_user.get('email')} viewed cache stats")

        return standard_response(success=True, data=stats)

    except Exception as e:
        logger.error(f"Error viewing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/cache")
async def clear_cache(
    current_user: dict = Depends(verify_clerk_session)
):
    """
    Clear MCP cache.

    Requires authentication.
    """
    await initialize_calendar_components()

    try:
        cache = _calendar_state['cache']

        if hasattr(cache, 'clear'):
            cache.clear()
            message = "Cache cleared successfully"
        elif hasattr(cache, '_cache'):
            cache._cache.clear()
            message = "Cache cleared successfully"
        else:
            message = "Cache clear not supported"

        logger.info(f"User {current_user.get('email')} cleared cache")

        return standard_response(success=True, data={'message': message})

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ============================================================================
# Calendar Events CRUD Endpoints (Firestore-backed, Clerk authentication required)
# ============================================================================

@router.get("/events")
async def get_events(
    client_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: firestore.Client = Depends(get_db)
):
    """
    Get calendar events for a client within a date range.

    Query params:
    - client_id: Required client identifier
    - start_date: Optional start date (YYYY-MM-DD)
    - end_date: Optional end date (YYYY-MM-DD)

    Returns: Array of events directly (not wrapped in data field)
    """
    try:
        # Start with base query for client
        query = db.collection("calendar_events").where("client_id", "==", client_id)

        # Add date range filters if provided
        if start_date:
            query = query.where("event_date", ">=", start_date)
        if end_date:
            query = query.where("event_date", "<=", end_date)

        # Execute query
        docs = query.stream()

        # Convert to list of dicts with id field
        events = []
        for doc in docs:
            event_data = doc.to_dict()
            event_data['id'] = doc.id
            events.append(event_data)

        logger.info(f"Retrieved {len(events)} events for client {client_id}")

        # Return array directly (not wrapped in standard_response)
        return events

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )

@router.post("/events")
async def create_event(
    event: CalendarEventCreate,
    db: firestore.Client = Depends(get_db)
):
    """
    Create a new calendar event.

    Returns the created event with its ID.
    """
    try:
        # Prepare event data
        event_data = event.dict()
        event_data['created_at'] = datetime.utcnow().isoformat()
        event_data['updated_at'] = datetime.utcnow().isoformat()

        # Create document in Firestore
        doc_ref = db.collection("calendar_events").document()
        doc_ref.set(event_data)

        # Return created event with ID
        event_data['id'] = doc_ref.id

        logger.info(f"Created event {doc_ref.id} for client {event.client_id}")

        return event_data

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )

@router.put("/events/{event_id}")
async def update_event(
    event_id: str,
    event_update: CalendarEventUpdate,
    db: firestore.Client = Depends(get_db)
):
    """
    Update an existing calendar event.

    Returns the updated event.
    """
    try:
        doc_ref = db.collection("calendar_events").document(event_id)

        # Check if document exists
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )

        # Prepare update data (only include non-None fields)
        update_data = {k: v for k, v in event_update.dict().items() if v is not None}
        update_data['updated_at'] = datetime.utcnow().isoformat()

        # Update document
        doc_ref.update(update_data)

        # Fetch and return updated event
        updated_doc = doc_ref.get()
        event_data = updated_doc.to_dict()
        event_data['id'] = event_id

        logger.info(f"Updated event {event_id}")

        return event_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    db: firestore.Client = Depends(get_db)
):
    """
    Delete a calendar event.

    Returns success message.
    """
    try:
        doc_ref = db.collection("calendar_events").document(event_id)

        # Check if document exists
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {event_id} not found"
            )

        # Delete document
        doc_ref.delete()

        logger.info(f"Deleted event {event_id}")

        return {"success": True, "message": f"Event {event_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )

@router.post("/create-bulk-events")
async def create_bulk_events(
    bulk_request: BulkEventsCreate,
    db: firestore.Client = Depends(get_db)
):
    """
    Create multiple calendar events in a single request.

    More efficient than creating events one by one.

    Returns: List of created event IDs and count.
    """
    try:
        created_events = []
        batch = db.batch()

        # Prepare all events for batch write
        for event in bulk_request.events:
            event_data = event.dict()
            event_data['client_id'] = bulk_request.client_id  # Ensure client_id is set
            event_data['created_at'] = datetime.utcnow().isoformat()
            event_data['updated_at'] = datetime.utcnow().isoformat()

            # Create document reference
            doc_ref = db.collection("calendar_events").document()
            batch.set(doc_ref, event_data)

            created_events.append({
                'id': doc_ref.id,
                'title': event.title,
                'event_date': event.event_date
            })

        # Commit batch
        batch.commit()

        logger.info(f"Bulk created {len(created_events)} events for client {bulk_request.client_id}")

        return {
            "success": True,
            "count": len(created_events),
            "events": created_events
        }

    except Exception as e:
        logger.error(f"Error bulk creating events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create events: {str(e)}"
        )
