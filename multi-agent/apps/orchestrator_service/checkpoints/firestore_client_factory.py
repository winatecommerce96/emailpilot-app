"""
Self-diagnosing Firestore client factory with automatic gRPC→REST fallback.

This module provides a robust Firestore client that automatically detects and handles
DNS/gRPC connectivity issues, falling back to REST transport when necessary.
"""

import os
import socket
import time
import logging
from typing import Optional, Literal, Dict, Any, Tuple
from contextlib import contextmanager
from functools import lru_cache

from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from google.api_core import exceptions as gcp_exceptions

logger = logging.getLogger(__name__)


class FirestoreConnectivityDiagnostics:
    """Diagnose Firestore connectivity and determine optimal transport."""
    
    @staticmethod
    def check_dns_resolution(hostname: str = "firestore.googleapis.com", timeout: float = 2.0) -> Tuple[bool, str]:
        """
        Check if DNS resolution works for Firestore endpoints.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            start = time.time()
            # Try to resolve the hostname
            socket.gethostbyname(hostname)
            resolution_time = time.time() - start
            
            if resolution_time > 1.0:
                return False, f"DNS resolution slow ({resolution_time:.2f}s), might cause gRPC timeouts"
            
            return True, f"DNS resolution successful ({resolution_time:.2f}s)"
            
        except socket.gaierror as e:
            return False, f"DNS resolution failed: {e}"
        except socket.timeout:
            return False, f"DNS resolution timed out after {timeout}s"
        except Exception as e:
            return False, f"Unexpected DNS error: {e}"
    
    @staticmethod
    def check_grpc_srv_records(domain: str = "firestore.googleapis.com") -> Tuple[bool, str]:
        """
        Check if gRPC SRV records can be resolved.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        srv_record = f"_grpc._tcp.{domain}"
        try:
            import dns.resolver
            
            resolver = dns.resolver.Resolver()
            resolver.timeout = 2.0
            resolver.lifetime = 2.0
            
            answers = resolver.resolve(srv_record, 'SRV')
            if answers:
                return True, f"SRV records found for {srv_record}"
            return False, f"No SRV records found for {srv_record}"
            
        except ImportError:
            # dnspython not installed, skip SRV check
            logger.debug("dnspython not installed, skipping SRV record check")
            return True, "SRV check skipped (dnspython not installed)"
        except Exception as e:
            return False, f"SRV record check failed: {e}"
    
    @staticmethod
    def test_firestore_connection(
        client: Client,
        test_collection: str = "_connectivity_test",
        timeout: float = 5.0
    ) -> Tuple[bool, str, float]:
        """
        Test actual Firestore connectivity with a simple operation.
        
        Returns:
            Tuple of (success: bool, message: str, latency: float)
        """
        try:
            start = time.time()
            
            # Try a simple read operation
            test_doc_ref = client.collection(test_collection).document("test")
            
            # Use a context manager for timeout
            with timeout_context(timeout):
                test_doc = test_doc_ref.get()
            
            latency = time.time() - start
            
            if latency > 3.0:
                return False, f"Connection successful but slow ({latency:.2f}s)", latency
            
            return True, f"Connection test successful ({latency:.2f}s)", latency
            
        except gcp_exceptions.DeadlineExceeded:
            latency = time.time() - start
            return False, f"Connection timed out after {latency:.2f}s", latency
        except Exception as e:
            latency = time.time() - start
            return False, f"Connection test failed: {e}", latency
    
    @classmethod
    def run_full_diagnostics(cls) -> Dict[str, Any]:
        """
        Run complete connectivity diagnostics.
        
        Returns:
            Dictionary with diagnostic results and recommended transport
        """
        results = {
            "timestamp": time.time(),
            "dns_check": {},
            "srv_check": {},
            "grpc_test": {},
            "rest_test": {},
            "recommendation": None,
            "reasoning": []
        }
        
        # Check DNS resolution
        dns_ok, dns_msg = cls.check_dns_resolution()
        results["dns_check"] = {"success": dns_ok, "message": dns_msg}
        
        if not dns_ok:
            results["reasoning"].append("DNS resolution failed - gRPC will not work")
            results["recommendation"] = "rest"
            return results
        
        # Check SRV records
        srv_ok, srv_msg = cls.check_grpc_srv_records()
        results["srv_check"] = {"success": srv_ok, "message": srv_msg}
        
        if not srv_ok:
            results["reasoning"].append("SRV records unavailable - gRPC might fail")
        
        # Test gRPC transport
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        try:
            grpc_client = firestore.Client(project=project_id)  # Default is gRPC
            grpc_ok, grpc_msg, grpc_latency = cls.test_firestore_connection(grpc_client)
            results["grpc_test"] = {
                "success": grpc_ok,
                "message": grpc_msg,
                "latency": grpc_latency
            }
            
            if grpc_ok and grpc_latency < 2.0:
                results["reasoning"].append(f"gRPC working well (latency: {grpc_latency:.2f}s)")
                results["recommendation"] = "grpc"
                return results
                
        except Exception as e:
            results["grpc_test"] = {
                "success": False,
                "message": f"gRPC client creation failed: {e}",
                "latency": None
            }
            results["reasoning"].append(f"gRPC client failed: {e}")
        
        # Test REST transport as fallback
        try:
            import google.auth
            from google.auth.transport import requests as auth_requests
            
            # Force REST transport
            os.environ["FIRESTORE_TRANSPORT"] = "rest"
            rest_client = firestore.Client(project=project_id)
            
            rest_ok, rest_msg, rest_latency = cls.test_firestore_connection(rest_client)
            results["rest_test"] = {
                "success": rest_ok,
                "message": rest_msg,
                "latency": rest_latency
            }
            
            if rest_ok:
                results["reasoning"].append(f"REST transport working (latency: {rest_latency:.2f}s)")
                results["recommendation"] = "rest"
            else:
                results["reasoning"].append("Both gRPC and REST failed")
                results["recommendation"] = "rest"  # REST as last resort
                
        except Exception as e:
            results["rest_test"] = {
                "success": False,
                "message": f"REST client creation failed: {e}",
                "latency": None
            }
            results["reasoning"].append(f"REST client failed: {e}")
            results["recommendation"] = "rest"  # Still try REST
        finally:
            # Clean up environment variable
            if "FIRESTORE_TRANSPORT" in os.environ:
                del os.environ["FIRESTORE_TRANSPORT"]
        
        return results


@contextmanager
def timeout_context(seconds: float):
    """Context manager for operation timeouts (simplified version)."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler and alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(seconds))
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


class FirestoreClientFactory:
    """
    Factory for creating Firestore clients with automatic transport selection.
    """
    
    _diagnostics_cache: Optional[Dict[str, Any]] = None
    _diagnostics_ttl: float = 300.0  # 5 minutes
    _last_diagnostics_time: float = 0
    
    @classmethod
    def create_client(
        cls,
        project_id: Optional[str] = None,
        transport: Optional[Literal["grpc", "rest", "auto"]] = "auto",
        run_diagnostics: bool = True,
        force_diagnostics: bool = False
    ) -> Client:
        """
        Create a Firestore client with optimal transport selection.
        
        Args:
            project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
            transport: Transport type - "grpc", "rest", or "auto" (default)
            run_diagnostics: Whether to run diagnostics for auto mode
            force_diagnostics: Force re-run diagnostics even if cached
            
        Returns:
            Configured Firestore client
        """
        if not project_id:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        
        # Handle explicit transport selection
        if transport in ["grpc", "rest"]:
            return cls._create_with_transport(project_id, transport)
        
        # Auto mode - determine best transport
        if transport != "auto":
            logger.warning(f"Unknown transport '{transport}', using auto mode")
        
        # Check if we need to run diagnostics
        if run_diagnostics:
            diagnostics = cls._get_diagnostics(force=force_diagnostics)
            recommended_transport = diagnostics.get("recommendation", "rest")
            
            logger.info(
                f"Auto-selected transport: {recommended_transport} "
                f"(reasoning: {'; '.join(diagnostics.get('reasoning', []))})"
            )
            
            return cls._create_with_transport(project_id, recommended_transport)
        
        # Default to REST for safety without diagnostics
        logger.info("Diagnostics disabled, defaulting to REST transport")
        return cls._create_with_transport(project_id, "rest")
    
    @classmethod
    def _get_diagnostics(cls, force: bool = False) -> Dict[str, Any]:
        """
        Get cached diagnostics or run new ones.
        
        Args:
            force: Force re-run even if cached
            
        Returns:
            Diagnostics results dictionary
        """
        current_time = time.time()
        
        # Check cache
        if not force and cls._diagnostics_cache:
            age = current_time - cls._last_diagnostics_time
            if age < cls._diagnostics_ttl:
                logger.debug(f"Using cached diagnostics (age: {age:.1f}s)")
                return cls._diagnostics_cache
        
        # Run new diagnostics
        logger.info("Running Firestore connectivity diagnostics...")
        diagnostics = FirestoreConnectivityDiagnostics.run_full_diagnostics()
        
        # Cache results
        cls._diagnostics_cache = diagnostics
        cls._last_diagnostics_time = current_time
        
        # Log summary
        logger.info(f"Diagnostics complete. Recommendation: {diagnostics['recommendation']}")
        for reason in diagnostics.get("reasoning", []):
            logger.debug(f"  - {reason}")
        
        return diagnostics
    
    @classmethod
    def _create_with_transport(
        cls,
        project_id: str,
        transport: Literal["grpc", "rest"]
    ) -> Client:
        """
        Create Firestore client with specific transport.
        
        Args:
            project_id: GCP project ID
            transport: Transport type
            
        Returns:
            Configured Firestore client
        """
        try:
            if transport == "rest":
                # Force REST transport via environment variable
                os.environ["FIRESTORE_TRANSPORT"] = "rest"
                logger.info(f"Creating Firestore client with REST transport for project: {project_id}")
            else:
                # Ensure gRPC is used (remove any REST override)
                if "FIRESTORE_TRANSPORT" in os.environ:
                    del os.environ["FIRESTORE_TRANSPORT"]
                logger.info(f"Creating Firestore client with gRPC transport for project: {project_id}")
            
            client = firestore.Client(project=project_id)
            
            # Quick connectivity test
            try:
                test_doc = client.collection("_health").document("connectivity").get()
                logger.debug(f"Firestore client created successfully with {transport} transport")
            except Exception as e:
                logger.warning(f"Firestore client created but connectivity test failed: {e}")
            
            return client
            
        except Exception as e:
            logger.error(f"Failed to create Firestore client with {transport} transport: {e}")
            
            # If gRPC failed, try REST as fallback
            if transport == "grpc":
                logger.info("Falling back to REST transport due to gRPC failure")
                return cls._create_with_transport(project_id, "rest")
            
            # If REST also failed, raise the error
            raise


@lru_cache(maxsize=1)
def get_firestore_client(
    project_id: Optional[str] = None,
    transport: Optional[str] = None
) -> Client:
    """
    Get or create a cached Firestore client with auto-transport selection.
    
    This is a convenience function for getting a singleton client instance.
    
    Args:
        project_id: GCP project ID (defaults to GOOGLE_CLOUD_PROJECT env var)
        transport: Override transport selection (defaults to auto)
        
    Returns:
        Cached Firestore client instance
    """
    # Get transport from environment or use auto
    if not transport:
        transport = os.environ.get("FIRESTORE_TRANSPORT_MODE", "auto")
    
    return FirestoreClientFactory.create_client(
        project_id=project_id,
        transport=transport,
        run_diagnostics=True,
        force_diagnostics=False
    )


# Startup diagnostics logging
def log_startup_diagnostics():
    """Log diagnostics information at module import time."""
    logger.info("=" * 60)
    logger.info("Firestore Client Factory initialized")
    logger.info(f"Project: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'not set')}")
    logger.info(f"Transport mode: {os.environ.get('FIRESTORE_TRANSPORT_MODE', 'auto')}")
    logger.info(f"Force REST: {os.environ.get('FIRESTORE_TRANSPORT', 'not set')}")
    logger.info("=" * 60)


# Run startup diagnostics when module is imported
log_startup_diagnostics()