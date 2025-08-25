"""
Custom FirestoreSaver implementation using self-diagnosing client factory.

This replaces langgraph_checkpoint_firestore.FirestoreSaver with a version
that automatically handles DNS/gRPC issues by falling back to REST transport.
"""

import uuid
import logging
from typing import Any, Dict, Optional, Iterator, Sequence, Tuple
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata, CheckpointTuple
from google.cloud.firestore_v1 import Client, DocumentReference, CollectionReference
from google.api_core import exceptions as gcp_exceptions

from .firestore_client_factory import get_firestore_client

logger = logging.getLogger(__name__)


class RobustFirestoreSaver(BaseCheckpointSaver):
    """
    A Firestore-based checkpoint saver with automatic transport fallback.
    
    This implementation automatically detects and handles DNS/gRPC connectivity
    issues, falling back to REST transport when necessary.
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        checkpoints_collection: str = "langgraph_checkpoints",
        writes_collection: str = "langgraph_writes",
        client: Optional[Client] = None,
        auto_diagnostics: bool = True
    ):
        """
        Initialize the Firestore checkpoint saver.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT)
            checkpoints_collection: Name of collection for storing checkpoints
            writes_collection: Name of collection for storing writes
            client: Pre-configured Firestore client (optional)
            auto_diagnostics: Run connectivity diagnostics on first use
        """
        super().__init__()
        
        self.project_id = project_id
        self.checkpoints_collection_name = checkpoints_collection
        self.writes_collection_name = writes_collection
        self.auto_diagnostics = auto_diagnostics
        self._client = client
        self._diagnostics_run = False
        
        logger.info(
            f"Initialized RobustFirestoreSaver for project: {project_id or 'auto'}, "
            f"checkpoints: {checkpoints_collection}, writes: {writes_collection}"
        )
    
    @property
    def client(self) -> Client:
        """Get or create the Firestore client with auto-transport selection."""
        if self._client is None:
            # Run diagnostics on first client creation
            run_diagnostics = self.auto_diagnostics and not self._diagnostics_run
            
            logger.info("Creating Firestore client with auto-transport selection...")
            self._client = get_firestore_client(
                project_id=self.project_id,
                transport=None  # Auto-detect
            )
            
            self._diagnostics_run = True
            logger.info("Firestore client created successfully")
            
        return self._client
    
    @property
    def checkpoints_collection(self) -> CollectionReference:
        """Get the checkpoints collection reference."""
        return self.client.collection(self.checkpoints_collection_name)
    
    @property
    def writes_collection(self) -> CollectionReference:
        """Get the writes collection reference."""
        return self.client.collection(self.writes_collection_name)
    
    def _get_checkpoint_key(self, config: Dict[str, Any]) -> str:
        """Extract checkpoint key from config."""
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        
        if not thread_id:
            raise ValueError("thread_id must be provided in config['configurable']")
        
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id", "")
        
        # Create a composite key
        parts = [str(thread_id)]
        if checkpoint_ns:
            parts.append(str(checkpoint_ns))
        if checkpoint_id:
            parts.append(str(checkpoint_id))
        
        return "_".join(parts)
    
    def get(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """
        Get a checkpoint from Firestore.
        
        Args:
            config: Configuration containing thread_id and optional checkpoint_id
            
        Returns:
            Checkpoint if found, None otherwise
        """
        try:
            key = self._get_checkpoint_key(config)
            doc_ref = self.checkpoints_collection.document(key)
            
            doc = doc_ref.get()
            if not doc.exists:
                logger.debug(f"No checkpoint found for key: {key}")
                return None
            
            data = doc.to_dict()
            logger.debug(f"Retrieved checkpoint for key: {key}")
            
            # Convert stored data back to Checkpoint format
            return self._deserialize_checkpoint(data)
            
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")
            return None
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[CheckpointMetadata] = None
    ) -> Dict[str, Any]:
        """
        Save a checkpoint to Firestore.
        
        Args:
            config: Configuration containing thread_id
            checkpoint: Checkpoint data to save
            metadata: Optional metadata for the checkpoint
            
        Returns:
            Configuration with checkpoint_id
        """
        try:
            key = self._get_checkpoint_key(config)
            doc_ref = self.checkpoints_collection.document(key)
            
            # Serialize checkpoint data
            data = self._serialize_checkpoint(checkpoint, metadata)
            
            # Add timestamp
            data["updated_at"] = datetime.utcnow()
            data["checkpoint_key"] = key
            
            # Save to Firestore
            doc_ref.set(data)
            logger.debug(f"Saved checkpoint for key: {key}")
            
            # Return config with checkpoint_id
            return {
                **config,
                "configurable": {
                    **config.get("configurable", {}),
                    "checkpoint_id": checkpoint.get("id", str(uuid.uuid4()))
                }
            }
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            raise
    
    def put_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """
        Save writes to Firestore.
        
        Args:
            config: Configuration containing thread_id
            writes: Sequence of (channel, value) tuples
            task_id: Task identifier
        """
        try:
            key = f"{self._get_checkpoint_key(config)}_{task_id}"
            doc_ref = self.writes_collection.document(key)
            
            data = {
                "checkpoint_key": self._get_checkpoint_key(config),
                "task_id": task_id,
                "writes": [{"channel": ch, "value": val} for ch, val in writes],
                "created_at": datetime.utcnow()
            }
            
            doc_ref.set(data)
            logger.debug(f"Saved writes for task: {task_id}")
            
        except Exception as e:
            logger.error(f"Error saving writes: {e}")
            raise
    
    def list(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints from Firestore.
        
        Args:
            config: Optional configuration for filtering
            filter: Additional filter criteria
            before: List checkpoints before this config
            limit: Maximum number of checkpoints to return
            
        Yields:
            CheckpointTuple instances
        """
        try:
            query = self.checkpoints_collection
            
            # Apply filters if provided
            if config:
                thread_id = config.get("configurable", {}).get("thread_id")
                if thread_id:
                    # Filter by thread_id prefix in checkpoint_key
                    query = query.where("checkpoint_key", ">=", str(thread_id))
                    query = query.where("checkpoint_key", "<", str(thread_id) + "\uffff")
            
            # Order by timestamp
            query = query.order_by("updated_at", direction="DESCENDING")
            
            # Apply limit if specified
            if limit:
                query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            for doc in docs:
                if doc.exists:
                    data = doc.to_dict()
                    checkpoint = self._deserialize_checkpoint(data)
                    metadata = data.get("metadata", {})
                    
                    # Create CheckpointTuple
                    yield CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": data.get("thread_id"),
                                "checkpoint_id": checkpoint.get("id")
                            }
                        },
                        checkpoint=checkpoint,
                        metadata=metadata,
                        parent_config=None  # Would need to track this separately
                    )
                    
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
            return
    
    def _serialize_checkpoint(
        self,
        checkpoint: Checkpoint,
        metadata: Optional[CheckpointMetadata] = None
    ) -> Dict[str, Any]:
        """
        Serialize checkpoint data for storage.
        
        Args:
            checkpoint: Checkpoint to serialize
            metadata: Optional metadata
            
        Returns:
            Serialized data dictionary
        """
        return {
            "checkpoint": checkpoint,
            "metadata": metadata or {},
            "version": "1.0"
        }
    
    def _deserialize_checkpoint(self, data: Dict[str, Any]) -> Checkpoint:
        """
        Deserialize checkpoint data from storage.
        
        Args:
            data: Stored data dictionary
            
        Returns:
            Checkpoint instance
        """
        return data.get("checkpoint", {})
    
    async def aget(self, config: Dict[str, Any]) -> Optional[Checkpoint]:
        """Async version of get (delegates to sync version)."""
        return self.get(config)
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: Optional[CheckpointMetadata] = None
    ) -> Dict[str, Any]:
        """Async version of put (delegates to sync version)."""
        return self.put(config, checkpoint, metadata)
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: Sequence[Tuple[str, Any]],
        task_id: str
    ) -> None:
        """Async version of put_writes (delegates to sync version)."""
        return self.put_writes(config, writes, task_id)


def get_robust_firestore_saver(
    project_id: Optional[str] = None,
    checkpoints_collection: str = "langgraph_checkpoints",
    writes_collection: str = "langgraph_writes"
) -> RobustFirestoreSaver:
    """
    Factory function to create a RobustFirestoreSaver instance.
    
    Args:
        project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT)
        checkpoints_collection: Name of collection for storing checkpoints
        writes_collection: Name of collection for storing writes
        
    Returns:
        Configured RobustFirestoreSaver instance
    """
    return RobustFirestoreSaver(
        project_id=project_id,
        checkpoints_collection=checkpoints_collection,
        writes_collection=writes_collection,
        auto_diagnostics=True
    )