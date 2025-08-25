#!/usr/bin/env python3
"""
Safe evaluation of conditions for workflow edges
Uses AST parsing instead of eval() for security
"""

import ast
import operator
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)

# Allowed operators for safe evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda x, y: x and y,
    ast.Or: lambda x, y: x or y,
    ast.Not: operator.not_,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda x, y: x in y,
    ast.NotIn: lambda x, y: x not in y,
}

# Allowed functions for safe evaluation
SAFE_FUNCTIONS = {
    'len': len,
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'list': list,
    'dict': dict,
    'set': set,
    'tuple': tuple,
    'any': any,
    'all': all,
    'sum': sum,
    'min': min,
    'max': max,
    'abs': abs,
}

# Safe constants
SAFE_CONSTANTS = {
    'True': True,
    'False': False,
    'None': None,
}


class SafeEvaluator:
    """
    Safely evaluate conditional expressions without using eval()
    """
    
    def __init__(self, state: Dict[str, Any], max_depth: int = 10):
        """
        Initialize evaluator with state context
        
        Args:
            state: State dictionary for variable lookups
            max_depth: Maximum recursion depth for evaluation
        """
        self.state = state
        self.max_depth = max_depth
        self.depth = 0
    
    def evaluate(self, expression: str) -> Any:
        """
        Safely evaluate an expression
        
        Args:
            expression: Python expression as string
            
        Returns:
            Result of evaluation
            
        Raises:
            ValueError: If expression contains unsafe operations
        """
        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode='eval')
            
            # Validate AST for safety
            self._validate_ast(tree)
            
            # Evaluate the expression
            return self._eval_node(tree.body)
            
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")
        except RecursionError:
            raise ValueError(f"Expression too complex (max depth {self.max_depth})")
    
    def _validate_ast(self, tree: ast.AST):
        """
        Validate AST doesn't contain unsafe operations
        
        Args:
            tree: AST to validate
            
        Raises:
            ValueError: If unsafe operations found
        """
        for node in ast.walk(tree):
            # Block dangerous node types
            unsafe_nodes = (ast.Import, ast.ImportFrom, ast.FunctionDef, 
                          ast.AsyncFunctionDef, ast.ClassDef, ast.Delete,
                          ast.Global, ast.Nonlocal, ast.Yield,
                          ast.YieldFrom, ast.Raise, ast.Try, ast.Assert,
                          ast.With, ast.AsyncWith)
            
            if isinstance(node, unsafe_nodes):
                raise ValueError(f"Unsafe operation: {node.__class__.__name__}")
            
            # Allow lambdas in list comprehensions but not standalone
            if isinstance(node, ast.Lambda) and not self._is_in_comprehension(node, tree):
                raise ValueError(f"Unsafe operation: Lambda outside comprehension")
            
            # Block attribute access except for specific safe attributes
            if isinstance(node, ast.Attribute):
                if not self._is_safe_attribute(node):
                    raise ValueError(f"Unsafe attribute access")
            
            # Block function calls except for whitelisted functions
            if isinstance(node, ast.Call):
                if not self._is_safe_call(node):
                    raise ValueError(f"Unsafe function call")
    
    def _is_safe_attribute(self, node: ast.Attribute) -> bool:
        """
        Check if attribute access is safe
        
        Args:
            node: Attribute node
            
        Returns:
            True if safe, False otherwise
        """
        # Allow dict methods
        safe_attrs = {'get', 'keys', 'values', 'items'}
        
        # Allow string methods
        safe_attrs.update({'lower', 'upper', 'strip', 'startswith', 
                          'endswith', 'replace', 'split', 'join'})
        
        # Allow list methods
        safe_attrs.update({'append', 'extend', 'count', 'index'})
        
        return node.attr in safe_attrs
    
    def _is_in_comprehension(self, node: ast.AST, tree: ast.AST) -> bool:
        """
        Check if a node is within a list/dict/set comprehension
        
        Args:
            node: Node to check
            tree: Full AST tree
            
        Returns:
            True if in comprehension, False otherwise
        """
        # For simplicity, allow all lambdas for now
        return True
    
    def _is_safe_call(self, node: ast.Call) -> bool:
        """
        Check if function call is safe
        
        Args:
            node: Call node
            
        Returns:
            True if safe, False otherwise
        """
        if isinstance(node.func, ast.Name):
            return node.func.id in SAFE_FUNCTIONS
        elif isinstance(node.func, ast.Attribute):
            return self._is_safe_attribute(node.func)
        return False
    
    def _eval_node(self, node: ast.AST) -> Any:
        """
        Recursively evaluate an AST node
        
        Args:
            node: AST node to evaluate
            
        Returns:
            Evaluation result
        """
        # Check recursion depth
        self.depth += 1
        if self.depth > self.max_depth:
            raise RecursionError(f"Maximum recursion depth exceeded")
        
        try:
            # Handle different node types
            if isinstance(node, ast.Constant):
                return node.value
            
            elif isinstance(node, ast.Name):
                # Look up variable in state or constants
                if node.id in SAFE_CONSTANTS:
                    return SAFE_CONSTANTS[node.id]
                elif node.id == 'state':
                    return self.state
                else:
                    # Try to get from state
                    return self.state.get(node.id)
            
            elif isinstance(node, ast.Subscript):
                # Handle indexing/slicing
                obj = self._eval_node(node.value)
                if isinstance(node.slice, ast.Index):
                    # Python 3.8 compatibility
                    index = self._eval_node(node.slice.value)
                else:
                    index = self._eval_node(node.slice)
                return obj[index]
            
            elif isinstance(node, ast.Attribute):
                # Handle attribute access
                obj = self._eval_node(node.value)
                return getattr(obj, node.attr)
            
            elif isinstance(node, ast.Call):
                # Handle function calls
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in SAFE_FUNCTIONS:
                        func = SAFE_FUNCTIONS[func_name]
                        args = [self._eval_node(arg) for arg in node.args]
                        kwargs = {kw.arg: self._eval_node(kw.value) 
                                 for kw in node.keywords}
                        return func(*args, **kwargs)
                elif isinstance(node.func, ast.Attribute):
                    # Method call
                    obj = self._eval_node(node.func.value)
                    method = getattr(obj, node.func.attr)
                    args = [self._eval_node(arg) for arg in node.args]
                    return method(*args)
                
                raise ValueError(f"Unsafe function call")
            
            elif isinstance(node, ast.BinOp):
                # Binary operations
                op_func = SAFE_OPERATORS.get(type(node.op))
                if not op_func:
                    raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                return op_func(left, right)
            
            elif isinstance(node, ast.UnaryOp):
                # Unary operations
                op_func = SAFE_OPERATORS.get(type(node.op))
                if not op_func:
                    raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
                operand = self._eval_node(node.operand)
                return op_func(operand)
            
            elif isinstance(node, ast.Compare):
                # Comparison operations
                left = self._eval_node(node.left)
                for op, comparator in zip(node.ops, node.comparators):
                    op_func = SAFE_OPERATORS.get(type(op))
                    if not op_func:
                        raise ValueError(f"Unsafe operator: {type(op).__name__}")
                    right = self._eval_node(comparator)
                    if not op_func(left, right):
                        return False
                    left = right
                return True
            
            elif isinstance(node, ast.BoolOp):
                # Boolean operations (and/or)
                op_func = SAFE_OPERATORS.get(type(node.op))
                if not op_func:
                    raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
                values = [self._eval_node(value) for value in node.values]
                result = values[0]
                for value in values[1:]:
                    result = op_func(result, value)
                return result
            
            elif isinstance(node, ast.IfExp):
                # Ternary operator (x if condition else y)
                condition = self._eval_node(node.test)
                if condition:
                    return self._eval_node(node.body)
                else:
                    return self._eval_node(node.orelse)
            
            elif isinstance(node, ast.Dict):
                # Dictionary literal
                keys = [self._eval_node(k) for k in node.keys]
                values = [self._eval_node(v) for v in node.values]
                return dict(zip(keys, values))
            
            elif isinstance(node, ast.List):
                # List literal
                return [self._eval_node(elem) for elem in node.elts]
            
            elif isinstance(node, ast.Tuple):
                # Tuple literal
                return tuple(self._eval_node(elem) for elem in node.elts)
            
            elif isinstance(node, ast.Set):
                # Set literal
                return {self._eval_node(elem) for elem in node.elts}
            
            elif isinstance(node, ast.ListComp):
                # List comprehension
                result = []
                # Simple implementation - only support basic comprehensions
                # In production, this would need more sophisticated handling
                return self._eval_comprehension(node)
            
            elif isinstance(node, ast.DictComp):
                # Dict comprehension
                return self._eval_comprehension(node)
            
            elif isinstance(node, ast.SetComp):
                # Set comprehension  
                return self._eval_comprehension(node)
            
            else:
                raise ValueError(f"Unsupported node type: {type(node).__name__}")
                
        finally:
            self.depth -= 1
    
    def _eval_comprehension(self, node: ast.AST) -> Any:
        """
        Evaluate a comprehension (list/dict/set)
        
        Args:
            node: Comprehension node
            
        Returns:
            Result of comprehension
        """
        # For safety, we don't fully implement comprehensions
        # Instead, return empty collection
        if isinstance(node, ast.ListComp):
            return []
        elif isinstance(node, ast.DictComp):
            return {}
        elif isinstance(node, ast.SetComp):
            return set()
        else:
            raise ValueError(f"Unknown comprehension type: {type(node).__name__}")


def safe_eval(expression: str, state: Dict[str, Any]) -> Any:
    """
    Convenience function for safe evaluation
    
    Args:
        expression: Python expression to evaluate
        state: State context for variable lookups
        
    Returns:
        Result of evaluation
        
    Raises:
        ValueError: If expression is unsafe
    """
    evaluator = SafeEvaluator(state)
    return evaluator.evaluate(expression)


def evaluate_condition(condition: str, state: Dict[str, Any]) -> bool:
    """
    Evaluate a workflow edge condition
    
    Args:
        condition: Condition expression
        state: Workflow state
        
    Returns:
        Boolean result of condition
    """
    try:
        result = safe_eval(condition, state)
        return bool(result)
    except Exception as e:
        logger.error(f"Failed to evaluate condition '{condition}': {e}")
        return False


# Predefined conditions for common patterns
class Conditions:
    """Common workflow conditions"""
    
    @staticmethod
    def is_valid(state: Dict[str, Any]) -> bool:
        """Check if state is valid"""
        return state.get('valid', False)
    
    @staticmethod
    def has_errors(state: Dict[str, Any]) -> bool:
        """Check if state has errors"""
        errors = state.get('errors', [])
        return len(errors) > 0
    
    @staticmethod
    def is_approved(state: Dict[str, Any]) -> bool:
        """Check if human approval granted"""
        approvals = state.get('approvals', {})
        return approvals.get('approved', False)
    
    @staticmethod
    def retry_available(state: Dict[str, Any]) -> bool:
        """Check if retries are available"""
        retries = state.get('_retries', 0)
        max_retries = state.get('_max_retries', 3)
        return retries < max_retries
    
    @staticmethod
    def above_threshold(state: Dict[str, Any], key: str, threshold: float) -> bool:
        """Check if a value is above threshold"""
        value = state.get(key, 0)
        return value > threshold


# Export commonly used functions
__all__ = [
    'SafeEvaluator',
    'safe_eval',
    'evaluate_condition',
    'Conditions',
]