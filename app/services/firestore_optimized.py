"""
Optimized Firestore service with connection pooling and query optimization
Key optimizations:
- Connection pooling
- Query result caching
- Batch operations
- Index recommendations
- Performance monitoring
"""

import os
import time
import asyncio
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.oauth2 import service_account
from cachetools import TTLCache
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class OptimizedFirestoreClient:
    def __init__(self):
        self.db = None
        self.connection_pool = None
        self.performance_stats = {
            'queries_executed': 0,
            'average_query_time': 0,
            'total_query_time': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_operations': 0
        }
        
        # Query result cache
        self.query_cache = TTLCache(maxsize=500, ttl=300)  # 5 min TTL
        
        # Connection pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix='firestore')
        
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize optimized Firestore client"""
        try:
            # Use application default credentials or service account
            if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                self.db = firestore.Client()
            else:
                # Try to get credentials from secret manager or environment
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'emailpilot-dev')
                
                # For development, use default credentials
                self.db = firestore.Client(project=project_id)
            
            # Test connection
            self.db.collection('health_check').limit(1).get()
            logger.info("OptimizedFirestoreClient initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise
    
    def update_performance_stats(self, query_time: float, cache_hit: bool = False):
        """Update performance statistics"""
        self.performance_stats['queries_executed'] += 1
        
        if cache_hit:
            self.performance_stats['cache_hits'] += 1
        else:
            self.performance_stats['cache_misses'] += 1
            self.performance_stats['total_query_time'] += query_time
            self.performance_stats['average_query_time'] = (
                self.performance_stats['total_query_time'] / 
                (self.performance_stats['queries_executed'] - self.performance_stats['cache_hits'])
            )
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        total_requests = self.performance_stats['cache_hits'] + self.performance_stats['cache_misses']
        cache_hit_rate = 0
        if total_requests > 0:
            cache_hit_rate = (self.performance_stats['cache_hits'] / total_requests) * 100
        
        return {
            **self.performance_stats,
            'cache_hit_rate_percent': round(cache_hit_rate, 2),
            'cache_size': len(self.query_cache)
        }
    
    def build_cache_key(self, collection: str, filters: List = None, order_by: str = None) -> str:
        """Build consistent cache key for queries"""
        key_parts = [collection]
        
        if filters:
            for filter_item in filters:
                key_parts.append(str(filter_item))
        
        if order_by:
            key_parts.append(order_by)
        
        return '|'.join(key_parts)
    
    async def get_collection_with_cache(
        self,
        collection_name: str,
        filters: List[tuple] = None,
        order_by: str = None,
        limit: int = None,
        use_cache: bool = True
    ) -> List[Dict]:
        """Get collection documents with caching"""
        cache_key = self.build_cache_key(collection_name, filters, order_by)
        
        # Check cache first
        if use_cache and cache_key in self.query_cache:
            self.update_performance_stats(0, cache_hit=True)
            return self.query_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Build query
            collection_ref = self.db.collection(collection_name)
            query = collection_ref
            
            # Apply filters
            if filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)
            
            # Apply ordering
            if order_by:
                direction = firestore.Query.DESCENDING if order_by.startswith('-') else firestore.Query.ASCENDING
                field = order_by.lstrip('-')
                query = query.order_by(field, direction=direction)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            # Execute query in thread pool
            loop = asyncio.get_event_loop()
            docs = await loop.run_in_executor(
                self.executor,
                lambda: list(query.stream())
            )
            
            # Convert to list of dicts
            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                results.append(doc_data)
            
            query_time = (time.time() - start_time) * 1000
            self.update_performance_stats(query_time)
            
            # Cache results
            if use_cache:
                self.query_cache[cache_key] = results
            
            return results
            
        except Exception as e:
            query_time = (time.time() - start_time) * 1000
            self.update_performance_stats(query_time)
            logger.error(f"Error querying collection {collection_name}: {e}")
            raise
    
    async def batch_write(self, operations: List[Dict]) -> Dict:
        """Perform batch write operations"""
        if not operations:
            return {"success": True, "operations_count": 0}
        
        start_time = time.time()
        batch = self.db.batch()
        
        try:
            for operation in operations:
                op_type = operation['type']
                collection = operation['collection']
                doc_id = operation.get('doc_id')
                data = operation.get('data', {})
                
                if op_type == 'create':
                    doc_ref = self.db.collection(collection).document(doc_id) if doc_id else self.db.collection(collection).document()
                    batch.set(doc_ref, data)
                elif op_type == 'update':
                    doc_ref = self.db.collection(collection).document(doc_id)
                    batch.update(doc_ref, data)
                elif op_type == 'delete':
                    doc_ref = self.db.collection(collection).document(doc_id)
                    batch.delete(doc_ref)
            
            # Execute batch in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, batch.commit)
            
            # Update stats
            self.performance_stats['batch_operations'] += 1
            operation_time = (time.time() - start_time) * 1000
            
            # Clear relevant caches
            self.invalidate_cache_by_collections([op['collection'] for op in operations])
            
            return {
                "success": True,
                "operations_count": len(operations),
                "processing_time_ms": round(operation_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Batch operation failed: {e}")
            raise
    
    def invalidate_cache_by_collections(self, collections: List[str]):
        """Invalidate cache entries for specific collections"""
        keys_to_remove = []
        for key in self.query_cache.keys():
            if any(collection in str(key) for collection in collections):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.query_cache.pop(key, None)
    
    def get_index_recommendations(self, collection_name: str, query_patterns: List[Dict]) -> List[str]:
        """Generate Firestore index recommendations based on query patterns"""
        recommendations = []
        
        for pattern in query_patterns:
            filters = pattern.get('filters', [])
            order_by = pattern.get('order_by')
            
            if len(filters) > 1 or (filters and order_by):
                # Composite index needed
                fields = []
                for field, operator, _ in filters:
                    fields.append(f"{field} ({operator})")
                
                if order_by:
                    direction = "DESC" if order_by.startswith('-') else "ASC"
                    field = order_by.lstrip('-')
                    fields.append(f"{field} ({direction})")
                
                index_def = f"Collection: {collection_name}, Fields: {', '.join(fields)}"
                recommendations.append(index_def)
        
        return list(set(recommendations))  # Remove duplicates
    
    async def optimize_query(self, collection_name: str, query_config: Dict) -> Dict:
        """Optimize query based on collection statistics"""
        try:
            # Get collection statistics
            stats_key = f"stats_{collection_name}"
            if stats_key not in self.query_cache:
                # Count documents (expensive operation, cache for longer)
                collection_ref = self.db.collection(collection_name)
                doc_count = len(list(collection_ref.limit(1000).stream()))  # Sample count
                
                self.query_cache[stats_key] = {
                    'estimated_size': doc_count,
                    'last_updated': time.time()
                }
            
            stats = self.query_cache[stats_key]
            
            # Optimize based on collection size
            if stats['estimated_size'] > 1000:
                # Large collection - recommend pagination
                query_config['limit'] = min(query_config.get('limit', 100), 100)
                
            if stats['estimated_size'] > 10000:
                # Very large collection - enable aggressive caching
                query_config['cache_ttl'] = 600  # 10 minutes
                
            return {
                "optimized_config": query_config,
                "collection_stats": stats,
                "recommendations": [
                    f"Collection has ~{stats['estimated_size']} documents",
                    "Consider pagination for large result sets",
                    "Use specific field queries instead of full scans"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error optimizing query: {e}")
            return {"optimized_config": query_config, "error": str(e)}
    
    async def health_check(self) -> Dict:
        """Perform health check with performance metrics"""
        try:
            start_time = time.time()
            
            # Test read operation
            test_doc = await self.get_collection_with_cache(
                'calendar_events',
                limit=1,
                use_cache=False
            )
            
            read_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "read_latency_ms": round(read_time, 2),
                "performance_stats": self.get_performance_stats(),
                "connection_pool_active": self.executor._threads if self.executor._threads else 0
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "performance_stats": self.get_performance_stats()
            }
    
    def cleanup(self):
        """Clean up resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        self.query_cache.clear()
