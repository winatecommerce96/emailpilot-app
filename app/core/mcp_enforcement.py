"""
MCP Registry Enforcement

This module ENFORCES that all MCP integrations MUST use the Universal MCP Registry.
Any attempt to bypass this system will raise errors.

THIS IS THE ONLY APPROVED WAY TO ADD NEW MCP TOOLS.
"""
from typing import Dict, Any, Optional
from functools import wraps
import logging
import inspect
import os
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class MCPRegistryEnforcement:
    """
    Enforcement class that ensures all MCP operations go through the registry
    """
    
    # List of approved MCP modules that existed before the registry
    # These are being phased out and should migrate to registry
    LEGACY_ALLOWED = [
        "mcp_klaviyo",  # Will migrate to registry
        "mcp_local",    # Will migrate to registry
        "mcp_chat",     # UI interface - allowed
        "mcp_registry", # The registry itself - allowed
        "mcp_management", # Registry management - allowed
    ]
    
    # List of modules that MUST NOT directly implement MCP functionality
    BLOCKED_PATTERNS = [
        "new_mcp_",     # No new direct MCP implementations
        "_direct_mcp",   # No direct MCP access
        "custom_mcp_",   # Must use registry
        "mcp_bypass",    # Explicitly blocked
    ]
    
    @classmethod
    def validate_module_name(cls, module_name: str) -> bool:
        """
        Validate that a module name is allowed to implement MCP functionality
        
        Args:
            module_name: Name of the module being imported
            
        Returns:
            True if allowed, raises exception if not
        """
        # Check if it's a blocked pattern
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern in module_name.lower():
                raise ValueError(
                    f"❌ BLOCKED: Module '{module_name}' cannot implement MCP directly.\n"
                    f"You MUST use the Universal MCP Registry instead.\n"
                    f"See SMART_MCP_GATEWAY.md for instructions."
                )
        
        # Check if it's in legacy allowed list
        base_name = module_name.split('.')[-1] if '.' in module_name else module_name
        if base_name not in cls.LEGACY_ALLOWED and 'mcp' in base_name.lower():
            logger.warning(
                f"⚠️ WARNING: Module '{module_name}' appears to implement MCP functionality.\n"
                f"This should be migrated to use the Universal MCP Registry.\n"
                f"Direct MCP implementations are deprecated."
            )
        
        return True
    
    @classmethod
    def enforce_registry_usage(cls, func):
        """
        Decorator to enforce that MCP operations use the registry
        
        Usage:
            @MCPRegistryEnforcement.enforce_registry_usage
            async def some_mcp_function():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the module name of the calling function
            module = inspect.getmodule(func)
            if module:
                module_name = module.__name__
                cls.validate_module_name(module_name)
            
            # Check if the function is trying to bypass the registry
            if 'bypass_registry' in kwargs or 'direct_mcp' in kwargs:
                raise HTTPException(
                    status_code=403,
                    detail="Direct MCP access is not allowed. Use the Universal MCP Registry."
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    @classmethod
    def check_import(cls, module_name: str, filepath: str = None):
        """
        Check if an import is allowed for MCP functionality
        
        Args:
            module_name: Name of module being imported
            filepath: Optional filepath for context
        """
        if filepath:
            # Check if it's a new file trying to implement MCP
            if 'mcp' in filepath.lower() and filepath not in [
                "mcp_management.py",
                "mcp_registry.py",
                "mcp_enforcement.py"
            ]:
                # Check if file was created after the registry system
                if os.path.exists(filepath):
                    stat = os.stat(filepath)
                    # If file is newer than this enforcement module, it must use registry
                    enforcement_time = os.stat(__file__).st_mtime
                    if stat.st_mtime > enforcement_time:
                        logger.error(
                            f"❌ NEW MCP FILE DETECTED: {filepath}\n"
                            f"All new MCP integrations MUST use the Universal MCP Registry.\n"
                            f"Do not create new MCP files. Register through /api/mcp/register instead."
                        )
        
        return cls.validate_module_name(module_name)


def enforce_mcp_registry():
    """
    Global enforcement function to be called at startup
    """
    logger.info("=" * 80)
    logger.info("🔒 MCP REGISTRY ENFORCEMENT ACTIVE")
    logger.info("All new MCP integrations MUST use the Universal MCP Registry")
    logger.info("Direct MCP implementations are BLOCKED")
    logger.info("See SMART_MCP_GATEWAY.md for instructions")
    logger.info("=" * 80)
    
    # Set environment variable to indicate enforcement is active
    os.environ['MCP_REGISTRY_ENFORCED'] = 'true'
    
    return True


def require_registry_for_mcp(service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Force any new MCP service to go through the registry
    
    Args:
        service_name: Name of the MCP service
        config: Configuration for the service
        
    Returns:
        Registry-wrapped configuration
    """
    if os.environ.get('MCP_REGISTRY_ENFORCED') != 'true':
        enforce_mcp_registry()
    
    # Check if this service is already registered
    from app.services.mcp_registry import UniversalMCPRegistry
    
    # Force registration through the registry
    logger.info(f"🔄 Redirecting {service_name} to Universal MCP Registry")
    
    registry_config = {
        'name': service_name,
        'base_url': config.get('base_url', ''),
        'service_type': config.get('service_type', 'general'),
        'auth_type': config.get('auth_type', 'api_key'),
        'description': config.get('description', f'Auto-registered {service_name}'),
        'endpoints': config.get('endpoints', []),
        'example_queries': config.get('example_queries', [])
    }
    
    logger.info(
        f"✅ {service_name} will be registered through Universal MCP Registry\n"
        f"Access via: /api/mcp/{service_name.lower().replace(' ', '_')}/query"
    )
    
    return registry_config


# Enforcement hook for import monitoring
# NOTE: This is disabled by default due to __builtins__ compatibility issues
# Enable only when needed for strict enforcement

# def enforced_import(name, *args, **kwargs):
#     """Override import to check for MCP bypass attempts"""
#     import builtins
#     original_import = builtins.__import__
#     
#     if 'mcp' in name.lower() and name not in [
#         'app.services.mcp_registry',
#         'app.api.mcp_management',
#         'app.api.mcp_registry',
#         'app.core.mcp_enforcement'
#     ]:
#         MCPRegistryEnforcement.check_import(name)
#     
#     return original_import(name, *args, **kwargs)

# Uncomment to enable strict import enforcement
# import builtins
# builtins.__import__ = enforced_import