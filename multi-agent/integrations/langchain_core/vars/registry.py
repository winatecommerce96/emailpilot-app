"""
Variable Registry implementation with schema validation and defaults.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class VarType(str, Enum):
    """Variable types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"


class VarSource(str, Enum):
    """Variable source."""
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class VarVisibility(str, Enum):
    """Variable visibility."""
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"


@dataclass
class VarMeta:
    """
    Variable metadata definition.
    """
    name: str
    type: VarType
    required: bool = False
    default: Any = None
    description: str = ""
    example: Any = None
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    source: VarSource = VarSource.USER
    visibility: VarVisibility = VarVisibility.PUBLIC
    dependencies: List[str] = field(default_factory=list)
    validators: List[callable] = field(default_factory=list)
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this variable's constraints.
        
        Args:
            value: Value to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check type
        if self.type == VarType.STRING:
            if not isinstance(value, str):
                return False, f"Expected string, got {type(value).__name__}"
            if self.min_length and len(value) < self.min_length:
                return False, f"String too short (min: {self.min_length})"
            if self.max_length and len(value) > self.max_length:
                return False, f"String too long (max: {self.max_length})"
            if self.pattern:
                import re
                if not re.match(self.pattern, value):
                    return False, f"String doesn't match pattern: {self.pattern}"
        
        elif self.type == VarType.INTEGER:
            if not isinstance(value, int):
                return False, f"Expected integer, got {type(value).__name__}"
            if self.min_value is not None and value < self.min_value:
                return False, f"Value too small (min: {self.min_value})"
            if self.max_value is not None and value > self.max_value:
                return False, f"Value too large (max: {self.max_value})"
        
        elif self.type == VarType.FLOAT:
            if not isinstance(value, (int, float)):
                return False, f"Expected number, got {type(value).__name__}"
            if self.min_value is not None and value < self.min_value:
                return False, f"Value too small (min: {self.min_value})"
            if self.max_value is not None and value > self.max_value:
                return False, f"Value too large (max: {self.max_value})"
        
        elif self.type == VarType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"
        
        elif self.type == VarType.ARRAY:
            if not isinstance(value, list):
                return False, f"Expected array, got {type(value).__name__}"
            if self.min_length and len(value) < self.min_length:
                return False, f"Array too short (min: {self.min_length})"
            if self.max_length and len(value) > self.max_length:
                return False, f"Array too long (max: {self.max_length})"
        
        elif self.type == VarType.OBJECT:
            if not isinstance(value, dict):
                return False, f"Expected object, got {type(value).__name__}"
        
        # Check allowed values
        if self.allowed_values and value not in self.allowed_values:
            return False, f"Value not in allowed list: {self.allowed_values}"
        
        # Run custom validators
        for validator in self.validators:
            try:
                if not validator(value):
                    return False, f"Custom validation failed"
            except Exception as e:
                return False, f"Validator error: {str(e)}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Remove non-serializable fields
        data.pop("validators", None)
        return data


class VariableRegistry:
    """
    Registry for managing agent variables.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._variables: Dict[str, Dict[str, VarMeta]] = {}
        self._global_vars: Dict[str, VarMeta] = {}
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default global variables."""
        # Common global variables
        self.register_global_variable(VarMeta(
            name="user_id",
            type=VarType.STRING,
            description="User identifier",
            source=VarSource.SYSTEM,
            visibility=VarVisibility.INTERNAL
        ))
        
        self.register_global_variable(VarMeta(
            name="brand",
            type=VarType.STRING,
            description="Brand context",
            source=VarSource.USER,
            example="acme"
        ))
        
        self.register_global_variable(VarMeta(
            name="month",
            type=VarType.STRING,
            description="Month context (YYYY-MM)",
            pattern=r"^\d{4}-\d{2}$",
            example="2024-11"
        ))
        
        self.register_global_variable(VarMeta(
            name="max_tokens",
            type=VarType.INTEGER,
            default=2000,
            min_value=100,
            max_value=10000,
            description="Maximum tokens for response",
            source=VarSource.ADMIN
        ))
        
        self.register_global_variable(VarMeta(
            name="temperature",
            type=VarType.FLOAT,
            default=0.7,
            min_value=0.0,
            max_value=2.0,
            description="LLM temperature",
            source=VarSource.ADMIN
        ))
    
    def register_agent_variable(self, agent_name: str, var: VarMeta):
        """
        Register a variable for an agent.
        
        Args:
            agent_name: Agent name
            var: Variable metadata
        """
        if agent_name not in self._variables:
            self._variables[agent_name] = {}
        
        self._variables[agent_name][var.name] = var
        logger.debug(f"Registered variable {var.name} for agent {agent_name}")
    
    def register_global_variable(self, var: VarMeta):
        """
        Register a global variable.
        
        Args:
            var: Variable metadata
        """
        self._global_vars[var.name] = var
        logger.debug(f"Registered global variable {var.name}")
    
    def get_agent_variables(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Get all variables for an agent.
        
        Args:
            agent_name: Agent name
        
        Returns:
            List of variable definitions
        """
        variables = []
        
        # Add global variables
        for var in self._global_vars.values():
            if var.visibility != VarVisibility.PRIVATE:
                variables.append(var.to_dict())
        
        # Add agent-specific variables
        if agent_name in self._variables:
            for var in self._variables[agent_name].values():
                if var.visibility != VarVisibility.PRIVATE:
                    variables.append(var.to_dict())
        
        return variables
    
    def validate_inputs(
        self,
        agent_name: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and coerce inputs for an agent.
        
        Args:
            agent_name: Agent name
            inputs: Input values
        
        Returns:
            Validated and coerced inputs
        
        Raises:
            ValueError: If validation fails
        """
        validated = {}
        errors = []
        
        # Get all variables
        all_vars = {**self._global_vars}
        if agent_name in self._variables:
            all_vars.update(self._variables[agent_name])
        
        # Validate each variable
        for var_name, var_meta in all_vars.items():
            if var_name in inputs:
                value = inputs[var_name]
                
                # Validate
                is_valid, error = var_meta.validate(value)
                if not is_valid:
                    errors.append(f"{var_name}: {error}")
                else:
                    validated[var_name] = value
            
            elif var_meta.required:
                # Check for default
                if var_meta.default is not None:
                    validated[var_name] = var_meta.default
                else:
                    errors.append(f"{var_name}: Required but not provided")
            
            elif var_meta.default is not None:
                # Use default
                validated[var_name] = var_meta.default
        
        # Check for unknown variables
        for key in inputs:
            if key not in all_vars:
                logger.warning(f"Unknown variable: {key}")
                # Pass through unknown variables
                validated[key] = inputs[key]
        
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")
        
        return validated
    
    def coerce_defaults(
        self,
        agent_name: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply defaults to inputs.
        
        Args:
            agent_name: Agent name
            inputs: Input values
        
        Returns:
            Inputs with defaults applied
        """
        result = dict(inputs)
        
        # Get all variables
        all_vars = {**self._global_vars}
        if agent_name in self._variables:
            all_vars.update(self._variables[agent_name])
        
        # Apply defaults
        for var_name, var_meta in all_vars.items():
            if var_name not in result and var_meta.default is not None:
                result[var_name] = var_meta.default
        
        return result
    
    def get_example(self, agent_name: str) -> Dict[str, Any]:
        """
        Get example inputs for an agent.
        
        Args:
            agent_name: Agent name
        
        Returns:
            Example input dictionary
        """
        example = {}
        
        # Get all variables
        all_vars = {**self._global_vars}
        if agent_name in self._variables:
            all_vars.update(self._variables[agent_name])
        
        # Build example
        for var_name, var_meta in all_vars.items():
            if var_meta.example is not None:
                example[var_name] = var_meta.example
            elif var_meta.default is not None:
                example[var_name] = var_meta.default
            elif var_meta.allowed_values:
                example[var_name] = var_meta.allowed_values[0]
            else:
                # Generate example based on type
                if var_meta.type == VarType.STRING:
                    example[var_name] = f"example_{var_name}"
                elif var_meta.type == VarType.INTEGER:
                    example[var_name] = 1
                elif var_meta.type == VarType.FLOAT:
                    example[var_name] = 1.0
                elif var_meta.type == VarType.BOOLEAN:
                    example[var_name] = True
                elif var_meta.type == VarType.ARRAY:
                    example[var_name] = []
                elif var_meta.type == VarType.OBJECT:
                    example[var_name] = {}
        
        return example


# Global registry instance
_registry: Optional[VariableRegistry] = None


def get_variable_registry() -> VariableRegistry:
    """Get the global variable registry."""
    global _registry
    if _registry is None:
        _registry = VariableRegistry()
    return _registry


def register_variable(
    agent_name: Optional[str] = None,
    **kwargs
) -> VarMeta:
    """
    Register a variable.
    
    Args:
        agent_name: Agent name (None for global)
        **kwargs: Variable metadata fields
    
    Returns:
        Created VarMeta
    """
    registry = get_variable_registry()
    
    # Convert type string to enum
    if "type" in kwargs and isinstance(kwargs["type"], str):
        kwargs["type"] = VarType(kwargs["type"])
    
    var = VarMeta(**kwargs)
    
    if agent_name:
        registry.register_agent_variable(agent_name, var)
    else:
        registry.register_global_variable(var)
    
    return var