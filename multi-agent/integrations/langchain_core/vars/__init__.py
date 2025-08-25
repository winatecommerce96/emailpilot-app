"""
Variable Registry for agent configuration.
"""

from .registry import (
    VarMeta,
    VariableRegistry,
    get_variable_registry,
    register_variable
)

__all__ = [
    "VarMeta",
    "VariableRegistry",
    "get_variable_registry",
    "register_variable"
]