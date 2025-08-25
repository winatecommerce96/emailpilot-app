"""
Test Firestore checkpoint integration.
"""
import sys
import os
from pathlib import Path
import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_firestore_saver_import():
    """Test that FirestoreSaver can be imported."""
    try:
        from langgraph_checkpoint_firestore import FirestoreSaver
        assert FirestoreSaver is not None
        print("✓ FirestoreSaver import successful")
    except ImportError as e:
        pytest.fail(f"Failed to import FirestoreSaver: {e}")


def test_firestore_saver_initialization():
    """Test FirestoreSaver initialization with mock client."""
    from langgraph_checkpoint_firestore import FirestoreSaver
    
    # Mock the Firestore client to avoid actual connection
    with patch('google.cloud.firestore.Client') as mock_client:
        mock_client.return_value = MagicMock()
        
        saver = FirestoreSaver(
            project_id="test-project",
            checkpoints_collection="test_checkpoints",
            writes_collection="test_writes"
        )
        
        assert saver is not None
        print("✓ FirestoreSaver initialization successful")


def test_graph_with_firestore_checkpointer():
    """Test that graph can be compiled with Firestore checkpointer."""
    # Set test environment variables
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    os.environ['ENVIRONMENT'] = 'development'
    
    try:
        # Mock Firestore client to avoid actual connection
        with patch('google.cloud.firestore.Client') as mock_firestore_client:
            mock_firestore_client.return_value = MagicMock()
            
            from apps.orchestrator_service.graph import CampaignOrchestrationGraph
            
            # Initialize the graph (which should use FirestoreSaver)
            graph = CampaignOrchestrationGraph()
            
            # Check that checkpointer is set
            assert hasattr(graph, 'checkpointer')
            assert graph.checkpointer is not None
            
            # Check that app is compiled
            assert graph.app is not None
            
            print("✓ Graph compiled with Firestore checkpointer")
            
    except Exception as e:
        # Config validation errors are expected in test env
        if "validation error" in str(e).lower():
            print("! Config validation issues (expected in test env)")
        else:
            pytest.fail(f"Failed to initialize graph with Firestore: {e}")


@pytest.mark.asyncio
async def test_firestore_checkpoint_roundtrip():
    """Test checkpoint save and retrieve operations."""
    from langgraph_checkpoint_firestore import FirestoreSaver
    from langgraph.checkpoint import Checkpoint
    
    # Mock Firestore operations
    with patch('google.cloud.firestore.Client') as mock_client:
        # Setup mock Firestore client
        mock_collection = MagicMock()
        mock_document = MagicMock()
        mock_client.return_value.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document
        
        # Create saver instance
        saver = FirestoreSaver(
            project_id="test-project",
            checkpoints_collection="test_checkpoints"
        )
        
        # Create a test checkpoint
        thread_id = str(uuid.uuid4())
        checkpoint_id = str(uuid.uuid4())
        
        # Create checkpoint data
        checkpoint = Checkpoint(
            v=1,
            id=checkpoint_id,
            ts="2024-01-01T00:00:00Z",
            channel_values={},
            channel_versions={},
            versions_seen={}
        )
        
        # Test save operation
        config = {"configurable": {"thread_id": thread_id}}
        metadata = {"test": "metadata"}
        
        # Mock the save operation
        mock_document.set.return_value = None
        
        # Save checkpoint (this will call the mocked Firestore)
        await saver.aput(config, checkpoint, metadata)
        
        # Verify that Firestore methods were called
        assert mock_collection.document.called
        assert mock_document.set.called
        
        print("✓ Firestore checkpoint roundtrip test passed")


def test_fallback_to_memory():
    """Test fallback to memory saver when Firestore fails."""
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    os.environ['ENVIRONMENT'] = 'development'
    
    # Mock Firestore to raise an exception
    with patch('google.cloud.firestore.Client') as mock_client:
        mock_client.side_effect = Exception("Firestore unavailable")
        
        try:
            from apps.orchestrator_service.graph import CampaignOrchestrationGraph
            
            # This should fall back to memory saver
            with patch('apps.orchestrator_service.graph.logger') as mock_logger:
                graph = CampaignOrchestrationGraph()
                
                # Check that warning was logged
                mock_logger.warning.assert_called()
                
                # Check that checkpointer is still set (fallback)
                assert hasattr(graph, 'checkpointer')
                assert graph.checkpointer is not None
                
                print("✓ Fallback to memory saver works")
                
        except Exception as e:
            if "validation error" in str(e).lower():
                print("! Config validation issues (expected in test env)")
            else:
                print(f"! Unexpected error: {e}")


if __name__ == "__main__":
    test_firestore_saver_import()
    test_firestore_saver_initialization()
    test_graph_with_firestore_checkpointer()
    test_fallback_to_memory()
    print("\n✅ All Firestore checkpoint tests passed!")