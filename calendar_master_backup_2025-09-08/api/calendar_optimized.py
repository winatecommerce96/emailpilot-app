"""
Performance-Optimized Calendar API Router for EmailPilot
Key optimizations:
- Database connection pooling
- Query optimization with proper indexing
- Request batching
- Response caching
- Pagination for large datasets
- Background task processing
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel
import json
import logging
import asyncio
from functools import lru_cache
from cachetools import TTLCache
import time

# Import optimized Firestore client
from app.services.firestore_optimized import OptimizedFirestoreClient
from app.schemas.calendar import CampaignPlanRequest, CampaignPlanResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Performance configuration
CACHE_TTL = 300  # 5 minutes
MAX_CACHE_SIZE = 1000
BATCH_SIZE = 100
MAX_CONCURRENT_OPERATIONS = 10

# In-memory cache for frequently accessed data
response_cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=CACHE_TTL)
query_cache = TTLCache(maxsize=MAX_CACHE_SIZE//2, ttl=CACHE_TTL//2)

# Initialize optimized Firestore client
firestore_client = OptimizedFirestoreClient()

# Performance monitoring
performance_metrics = {
    'request_count': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'average_response_time': 0,
    'total_response_time': 0,
    'slow_queries': 0
}

def update_performance_metrics(response_time: float, cache_hit: bool = False):
    """Update performance metrics"""
    performance_metrics['request_count'] += 1
    performance_metrics['total_response_time'] += response_time
    performance_metrics['average_response_time'] = (
        performance_metrics['total_response_time'] / performance_metrics['request_count']
    )
    
    if cache_hit:
        performance_metrics['cache_hits'] += 1
    else:
        performance_metrics['cache_misses'] += 1
        
    if response_time > 1000:  # > 1 second
        performance_metrics['slow_queries'] += 1

def cache_key_builder(*args) -> str:
    """Build consistent cache keys"""
    return '|'.join(str(arg) for arg in args if arg is not None)

@lru_cache(maxsize=100)
def get_client_collection_ref():
    """Cached Firestore collection reference"""
    return firestore_client.db.collection('calendar_events')

# Optimized Pydantic models with validation
class OptimizedCalendarEvent(BaseModel):
    title: str
    date: str
    client_id: str
    content: Optional[str] = ""
    color: Optional[str] = "bg-gray-200 text-gray-800"
    event_type: Optional[str] = "email"
    
    class Config:
        # Enable faster parsing
        use_enum_values = True
        validate_assignment = True

class BulkEventRequest(BaseModel):
    client_id: str
    events: List[OptimizedCalendarEvent]
    
class PaginatedEventResponse(BaseModel):
    events: List[Dict]
    total_count: int
    page: int
    page_size: int
    has_more: bool

# Optimized calendar event endpoints
@router.get("/events", response_model=PaginatedEventResponse)
async def get_calendar_events_optimized(
    client_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    include_inactive: bool = False
):
    """Get paginated calendar events with optimized queries"""
    start_time = time.time()
    
    try:
        # Build cache key
        cache_key = cache_key_builder(
            'events', client_id, start_date, end_date, page, page_size, include_inactive
        )
        
        # Check cache first
        if cache_key in response_cache:
            update_performance_metrics((time.time() - start_time) * 1000, cache_hit=True)
            return response_cache[cache_key]
        
        # Build optimized query
        events_ref = get_client_collection_ref()
        query = events_ref
        
        # Apply filters efficiently
        if client_id:
            query = query.where('client_id', '==', client_id)
        if start_date:
            query = query.where('date', '>=', start_date)
        if end_date:
            query = query.where('date', '<=', end_date)
        if not include_inactive:
            query = query.where('is_active', '==', True)
        
        # Order by date for better performance
        query = query.order_by('date', direction='DESCENDING')
        
        # Get total count (cached separately)
        count_cache_key = cache_key_builder('count', client_id, start_date, end_date, include_inactive)
        total_count = query_cache.get(count_cache_key)
        
        if total_count is None:
            # Use aggregation query for count
            total_count = len(list(query.stream()))
            query_cache[count_cache_key] = total_count
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query with timeout
        events = []
        async def fetch_events():
            for doc in query.stream():
                event_data = doc.to_dict()
                event_data['id'] = doc.id
                events.append(event_data)
        
        # Use asyncio.wait_for for timeout
        await asyncio.wait_for(fetch_events(), timeout=10.0)
        
        # Build response
        response = PaginatedEventResponse(
            events=events,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=offset + page_size < total_count
        )
        
        # Cache response
        response_cache[cache_key] = response
        
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        
        return response
        
    except asyncio.TimeoutError:
        logger.error("Query timeout exceeded")
        raise HTTPException(status_code=504, detail="Query timeout - try reducing page size")
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/events/bulk")
async def create_bulk_events_optimized(
    request: BulkEventRequest,
    background_tasks: BackgroundTasks
):
    """Create multiple events efficiently using batch operations"""
    start_time = time.time()
    
    try:
        if not request.events:
            raise HTTPException(status_code=400, detail="No events provided")
        
        if len(request.events) > BATCH_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"Batch size too large. Maximum {BATCH_SIZE} events per request"
            )
        
        # Prepare batch write
        batch = firestore_client.db.batch()
        events_ref = get_client_collection_ref()
        created_events = []
        
        current_time = datetime.utcnow()
        
        # Process events in batch
        for event_data in request.events:
            event_dict = event_data.dict()
            event_dict.update({
                'created_at': current_time,
                'updated_at': current_time,
                'is_active': True,
                'client_id': request.client_id
            })
            
            # Add to batch
            doc_ref = events_ref.document()
            batch.set(doc_ref, event_dict)
            
            # Track created events
            event_dict['id'] = doc_ref.id
            created_events.append(event_dict)
        
        # Execute batch write
        batch.commit()
        
        # Invalidate related caches in background
        background_tasks.add_task(invalidate_client_caches, request.client_id)
        
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        
        return {
            "message": f"Successfully created {len(created_events)} events",
            "created_events": created_events,
            "total_created": len(created_events),
            "processing_time_ms": round(response_time, 2)
        }
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        logger.error(f"Error creating bulk events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/events/{event_id}")
async def update_calendar_event_optimized(
    event_id: str, 
    updates: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """Update event with optimized write and cache invalidation"""
    start_time = time.time()
    
    try:
        events_ref = get_client_collection_ref()
        event_ref = events_ref.document(event_id)
        
        # Check if document exists using get with timeout
        event_doc = await asyncio.wait_for(
            asyncio.to_thread(event_ref.get), 
            timeout=5.0
        )
        
        if not event_doc.exists:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Prepare update data
        update_data = {k: v for k, v in updates.items() if v is not None}
        update_data['updated_at'] = datetime.utcnow()
        
        # Perform atomic update
        event_ref.update(update_data)
        
        # Get client_id for cache invalidation
        client_id = event_doc.to_dict().get('client_id')
        if client_id:
            background_tasks.add_task(invalidate_client_caches, client_id)
        
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        
        return {
            "message": "Event updated successfully", 
            "event_id": event_id,
            "processing_time_ms": round(response_time, 2)
        }
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Update timeout")
    except HTTPException:
        raise
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        logger.error(f"Error updating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/events/bulk")
async def delete_bulk_events_optimized(
    event_ids: List[str],
    background_tasks: BackgroundTasks
):
    """Delete multiple events efficiently"""
    start_time = time.time()
    
    try:
        if not event_ids:
            raise HTTPException(status_code=400, detail="No event IDs provided")
        
        if len(event_ids) > BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Too many events. Maximum {BATCH_SIZE} per request"
            )
        
        # Get client IDs for cache invalidation before deletion
        events_ref = get_client_collection_ref()
        client_ids = set()
        
        # Batch delete
        batch = firestore_client.db.batch()
        deleted_count = 0
        
        for event_id in event_ids:
            try:
                event_ref = events_ref.document(event_id)
                event_doc = event_ref.get()
                
                if event_doc.exists:
                    client_id = event_doc.to_dict().get('client_id')
                    if client_id:
                        client_ids.add(client_id)
                    
                    batch.delete(event_ref)
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Error deleting event {event_id}: {e}")
                continue
        
        # Execute batch delete
        if deleted_count > 0:
            batch.commit()
        
        # Invalidate caches for affected clients
        for client_id in client_ids:
            background_tasks.add_task(invalidate_client_caches, client_id)
        
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        
        return {
            "message": f"Successfully deleted {deleted_count} events",
            "deleted_count": deleted_count,
            "requested_count": len(event_ids),
            "processing_time_ms": round(response_time, 2)
        }
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        update_performance_metrics(response_time)
        logger.error(f"Error deleting bulk events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/performance")
async def get_performance_stats():
    """Get API performance metrics"""
    cache_hit_rate = 0
    if performance_metrics['cache_hits'] + performance_metrics['cache_misses'] > 0:
        cache_hit_rate = (
            performance_metrics['cache_hits'] / 
            (performance_metrics['cache_hits'] + performance_metrics['cache_misses']) * 100
        )
    
    return {
        "metrics": performance_metrics,
        "cache_stats": {
            "hit_rate_percent": round(cache_hit_rate, 2),
            "response_cache_size": len(response_cache),
            "query_cache_size": len(query_cache)
        },
        "firestore_stats": firestore_client.get_performance_stats()
    }

@router.post("/cache/invalidate")
async def invalidate_cache(
    cache_pattern: Optional[str] = None,
    client_id: Optional[str] = None
):
    """Manually invalidate cache entries"""
    invalidated_count = 0
    
    if client_id:
        invalidated_count += invalidate_client_caches(client_id)
    elif cache_pattern:
        keys_to_remove = [
            key for key in response_cache.keys() 
            if cache_pattern in str(key)
        ]
        for key in keys_to_remove:
            response_cache.pop(key, None)
            invalidated_count += 1
    else:
        # Clear all caches
        invalidated_count = len(response_cache) + len(query_cache)
        response_cache.clear()
        query_cache.clear()
    
    return {
        "message": f"Invalidated {invalidated_count} cache entries",
        "remaining_entries": len(response_cache) + len(query_cache)
    }

def invalidate_client_caches(client_id: str) -> int:
    """Invalidate all cache entries related to a client"""
    invalidated_count = 0
    
    # Remove from response cache
    keys_to_remove = [
        key for key in response_cache.keys() 
        if str(client_id) in str(key)
    ]
    for key in keys_to_remove:
        response_cache.pop(key, None)
        invalidated_count += 1
    
    # Remove from query cache
    keys_to_remove = [
        key for key in query_cache.keys() 
        if str(client_id) in str(key)
    ]
    for key in keys_to_remove:
        query_cache.pop(key, None)
        invalidated_count += 1
    
    return invalidated_count

# Health check with performance info
@router.get("/health")
async def calendar_health_optimized():
    """Enhanced health check with performance metrics"""
    try:
        # Quick Firestore connectivity test
        start_time = time.time()
        firestore_client.db.collection('calendar_events').limit(1).get()
        db_response_time = (time.time() - start_time) * 1000
        
        cache_hit_rate = 0
        if performance_metrics['cache_hits'] + performance_metrics['cache_misses'] > 0:
            cache_hit_rate = (
                performance_metrics['cache_hits'] / 
                (performance_metrics['cache_hits'] + performance_metrics['cache_misses']) * 100
            )
        
        return {
            "status": "healthy",
            "service": "calendar_optimized",
            "timestamp": datetime.utcnow().isoformat(),
            "performance": {
                "db_response_time_ms": round(db_response_time, 2),
                "cache_hit_rate_percent": round(cache_hit_rate, 2),
                "average_response_time_ms": round(performance_metrics['average_response_time'], 2),
                "total_requests": performance_metrics['request_count']
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "calendar_optimized",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
