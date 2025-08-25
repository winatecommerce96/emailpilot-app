#!/usr/bin/env python3
"""
Test script for Firestore connectivity diagnostics.

This script tests the auto-detection and fallback mechanism for Firestore
transport selection (gRPC vs REST).

Usage:
    python test_firestore_connectivity.py
    
Environment variables:
    FIRESTORE_TRANSPORT_MODE: Override transport (grpc/rest/auto)
    GOOGLE_CLOUD_PROJECT: GCP project ID
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_diagnostics():
    """Run comprehensive Firestore connectivity diagnostics."""
    print("=" * 70)
    print("FIRESTORE CONNECTIVITY DIAGNOSTICS")
    print("=" * 70)
    
    # Import our diagnostic tools
    from checkpoints.firestore_client_factory import (
        FirestoreConnectivityDiagnostics,
        FirestoreClientFactory,
        get_firestore_client
    )
    
    # 1. Run full diagnostics
    print("\n1. Running connectivity diagnostics...")
    print("-" * 50)
    
    diagnostics = FirestoreConnectivityDiagnostics.run_full_diagnostics()
    
    # Pretty print results
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(diagnostics['timestamp']))}")
    print(f"\nDNS Check:")
    print(f"  Success: {diagnostics['dns_check']['success']}")
    print(f"  Message: {diagnostics['dns_check']['message']}")
    
    print(f"\nSRV Records Check:")
    print(f"  Success: {diagnostics['srv_check']['success']}")
    print(f"  Message: {diagnostics['srv_check']['message']}")
    
    print(f"\ngRPC Transport Test:")
    grpc_test = diagnostics.get('grpc_test', {})
    print(f"  Success: {grpc_test.get('success', 'N/A')}")
    print(f"  Message: {grpc_test.get('message', 'N/A')}")
    if grpc_test.get('latency'):
        print(f"  Latency: {grpc_test['latency']:.3f}s")
    
    print(f"\nREST Transport Test:")
    rest_test = diagnostics.get('rest_test', {})
    print(f"  Success: {rest_test.get('success', 'N/A')}")
    print(f"  Message: {rest_test.get('message', 'N/A')}")
    if rest_test.get('latency'):
        print(f"  Latency: {rest_test['latency']:.3f}s")
    
    print(f"\nRecommendation: {diagnostics['recommendation'].upper()}")
    print(f"Reasoning:")
    for reason in diagnostics.get('reasoning', []):
        print(f"  - {reason}")
    
    return diagnostics


def test_client_creation():
    """Test creating Firestore clients with different transport modes."""
    print("\n" + "=" * 70)
    print("FIRESTORE CLIENT CREATION TESTS")
    print("=" * 70)
    
    from checkpoints.firestore_client_factory import FirestoreClientFactory
    
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
    
    # Test 1: Auto mode (default)
    print("\n1. Testing AUTO mode...")
    print("-" * 50)
    try:
        start = time.time()
        client_auto = FirestoreClientFactory.create_client(
            project_id=project_id,
            transport="auto",
            run_diagnostics=True
        )
        elapsed = time.time() - start
        print(f"✓ Client created successfully in {elapsed:.2f}s")
        
        # Test a simple operation
        test_doc = client_auto.collection("_test").document("connectivity").get()
        print(f"✓ Test read operation successful")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 2: Explicit REST mode
    print("\n2. Testing explicit REST mode...")
    print("-" * 50)
    try:
        start = time.time()
        client_rest = FirestoreClientFactory.create_client(
            project_id=project_id,
            transport="rest",
            run_diagnostics=False
        )
        elapsed = time.time() - start
        print(f"✓ REST client created in {elapsed:.2f}s")
        
        # Test a simple operation
        test_doc = client_rest.collection("_test").document("connectivity").get()
        print(f"✓ Test read operation successful")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 3: Explicit gRPC mode
    print("\n3. Testing explicit gRPC mode...")
    print("-" * 50)
    try:
        start = time.time()
        client_grpc = FirestoreClientFactory.create_client(
            project_id=project_id,
            transport="grpc",
            run_diagnostics=False
        )
        elapsed = time.time() - start
        print(f"✓ gRPC client created in {elapsed:.2f}s")
        
        # Test a simple operation
        test_doc = client_grpc.collection("_test").document("connectivity").get()
        print(f"✓ Test read operation successful")
    except Exception as e:
        print(f"✗ Failed: {e}")
        print("  (This is expected if DNS/gRPC issues exist)")


def test_firestore_saver():
    """Test the RobustFirestoreSaver implementation."""
    print("\n" + "=" * 70)
    print("ROBUST FIRESTORE SAVER TEST")
    print("=" * 70)
    
    try:
        from checkpoints.firestore_saver import get_robust_firestore_saver
        
        print("\n1. Creating RobustFirestoreSaver...")
        print("-" * 50)
        
        saver = get_robust_firestore_saver(
            checkpoints_collection="test_checkpoints",
            writes_collection="test_writes"
        )
        print("✓ Saver created successfully")
        
        # Test checkpoint operations
        print("\n2. Testing checkpoint operations...")
        print("-" * 50)
        
        test_config = {
            "configurable": {
                "thread_id": "test_thread_123",
                "checkpoint_id": "checkpoint_001"
            }
        }
        
        test_checkpoint = {
            "id": "checkpoint_001",
            "data": {"test": "value"},
            "timestamp": time.time()
        }
        
        # Save checkpoint
        print("Saving checkpoint...")
        result = saver.put(test_config, test_checkpoint)
        print(f"✓ Checkpoint saved: {result}")
        
        # Retrieve checkpoint
        print("Retrieving checkpoint...")
        retrieved = saver.get(test_config)
        if retrieved:
            print(f"✓ Checkpoint retrieved successfully")
        else:
            print("✗ Failed to retrieve checkpoint")
        
    except Exception as e:
        print(f"✗ Saver test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all connectivity tests."""
    print("\n" + "=" * 70)
    print("FIRESTORE CONNECTIVITY TEST SUITE")
    print("=" * 70)
    print(f"Project: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'not set')}")
    print(f"Transport mode: {os.environ.get('FIRESTORE_TRANSPORT_MODE', 'auto')}")
    print(f"Force REST: {os.environ.get('FIRESTORE_TRANSPORT', 'not set')}")
    
    # Run diagnostics
    diagnostics = test_diagnostics()
    
    # Test client creation
    test_client_creation()
    
    # Test Firestore saver
    test_firestore_saver()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    recommendation = diagnostics.get('recommendation', 'unknown')
    print(f"Recommended transport: {recommendation.upper()}")
    
    if recommendation == 'rest':
        print("\nTo use REST transport, set environment variable:")
        print("  export FIRESTORE_TRANSPORT_MODE=rest")
        print("\nOr let the system auto-detect (default)")
    elif recommendation == 'grpc':
        print("\ngRPC transport is working well!")
        print("No configuration changes needed.")
    
    print("\nTo force a specific transport in your application:")
    print("  - Set FIRESTORE_TRANSPORT_MODE=rest for REST")
    print("  - Set FIRESTORE_TRANSPORT_MODE=grpc for gRPC")
    print("  - Set FIRESTORE_TRANSPORT_MODE=auto for auto-detection (default)")


if __name__ == "__main__":
    main()