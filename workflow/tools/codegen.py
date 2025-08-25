#!/usr/bin/env python3
"""
Production Codegen: Schema → LangGraph Runtime Compiler
Strict validation, idempotent generation, never touches /nodes/
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import ast
import re

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class SchemaValidator:
    """Strict schema validation with precise error messages"""
    
    REQUIRED_FIELDS = ["name", "state", "nodes", "edges", "checkpointer"]
    NODE_TYPES = ["python_fn", "agent", "human_gate"]
    CHECKPOINTER_TYPES = ["sqlite", "redis"]
    
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.errors = []
        self.warnings = []
    
    def validate(self) -> bool:
        """Validate schema completely"""
        self._validate_required_fields()
        self._validate_state()
        self._validate_nodes()
        self._validate_edges()
        self._validate_checkpointer()
        self._validate_metadata()
        
        if self.errors:
            raise ValidationError(self.errors, self.warnings)
        
        return True
    
    def _validate_required_fields(self):
        """Check all required top-level fields exist"""
        for field in self.REQUIRED_FIELDS:
            if field not in self.schema:
                self.errors.append(f"Missing required field: '{field}'")
    
    def _validate_state(self):
        """Validate state definition"""
        if "state" not in self.schema:
            return
        
        state = self.schema["state"]
        if not isinstance(state, dict):
            self.errors.append("'state' must be a dictionary")
            return
        
        for key, type_str in state.items():
            if not isinstance(key, str):
                self.errors.append(f"State key must be string, got: {type(key)}")
            
            # Validate Python type string
            if not self._is_valid_type_string(type_str):
                self.errors.append(f"Invalid type for state.{key}: '{type_str}'")
    
    def _validate_nodes(self):
        """Validate node definitions"""
        if "nodes" not in self.schema:
            return
        
        nodes = self.schema["nodes"]
        if not isinstance(nodes, list):
            self.errors.append("'nodes' must be a list")
            return
        
        if len(nodes) == 0:
            self.errors.append("At least one node is required")
            return
        
        node_ids = set()
        for i, node in enumerate(nodes):
            # Check required node fields
            if "id" not in node:
                self.errors.append(f"Node {i} missing 'id' field")
                continue
            
            if "type" not in node:
                self.errors.append(f"Node {node.get('id', i)} missing 'type' field")
            
            # Check for duplicate IDs
            node_id = node["id"]
            if node_id in node_ids:
                self.errors.append(f"Duplicate node ID: '{node_id}'")
            node_ids.add(node_id)
            
            # Validate node type
            node_type = node.get("type")
            if node_type and node_type not in self.NODE_TYPES:
                self.errors.append(f"Unknown node type for '{node_id}': '{node_type}' (allowed: {self.NODE_TYPES})")
            
            # Validate impl path
            if "impl" in node:
                impl = node["impl"]
                if not isinstance(impl, str):
                    self.errors.append(f"Node '{node_id}' impl must be string")
                elif not self._is_valid_impl_path(impl):
                    self.warnings.append(f"Node '{node_id}' impl path may be invalid: '{impl}'")
    
    def _validate_edges(self):
        """Validate edge definitions"""
        if "edges" not in self.schema or "nodes" not in self.schema:
            return
        
        edges = self.schema["edges"]
        if not isinstance(edges, list):
            self.errors.append("'edges' must be a list")
            return
        
        # Get valid node IDs
        node_ids = {node["id"] for node in self.schema["nodes"] if "id" in node}
        
        for i, edge in enumerate(edges):
            # Check required edge fields
            if "from" not in edge:
                self.errors.append(f"Edge {i} missing 'from' field")
            elif edge["from"] not in node_ids:
                self.errors.append(f"Edge {i} references unknown source node: '{edge['from']}'")
            
            if "to" not in edge:
                self.errors.append(f"Edge {i} missing 'to' field")
            elif edge["to"] not in node_ids:
                self.errors.append(f"Edge {i} references unknown target node: '{edge['to']}'")
            
            # Validate condition if present
            if "condition" in edge:
                condition = edge["condition"]
                if not isinstance(condition, str):
                    self.errors.append(f"Edge {i} condition must be string")
                elif not self._is_safe_condition(condition):
                    self.errors.append(f"Edge {i} has unsafe condition: '{condition}'")
    
    def _validate_checkpointer(self):
        """Validate checkpointer configuration"""
        if "checkpointer" not in self.schema:
            return
        
        checkpointer = self.schema["checkpointer"]
        if not isinstance(checkpointer, dict):
            self.errors.append("'checkpointer' must be a dictionary")
            return
        
        if "type" not in checkpointer:
            self.errors.append("Checkpointer missing 'type' field")
        elif checkpointer["type"] not in self.CHECKPOINTER_TYPES:
            self.errors.append(f"Unknown checkpointer type: '{checkpointer['type']}' (allowed: {self.CHECKPOINTER_TYPES})")
        
        if "dsn" not in checkpointer:
            self.errors.append("Checkpointer missing 'dsn' field")
    
    def _validate_metadata(self):
        """Validate optional metadata"""
        if "metadata" in self.schema:
            metadata = self.schema["metadata"]
            if not isinstance(metadata, dict):
                self.warnings.append("'metadata' should be a dictionary")
    
    def _is_valid_type_string(self, type_str: str) -> bool:
        """Check if type string is valid Python type"""
        valid_types = [
            "str", "int", "float", "bool", "list", "dict", "Any",
            "List", "Dict", "Optional", "Union", "Tuple", "Set"
        ]
        # Allow complex type annotations
        pattern = r'^[A-Za-z_][\w\[\], ]*$'
        return bool(re.match(pattern, type_str))
    
    def _is_valid_impl_path(self, impl: str) -> bool:
        """Check if implementation path looks valid"""
        # Format: module.path:function or module.path
        pattern = r'^[\w\.]+(:[\w]+)?$'
        return bool(re.match(pattern, impl))
    
    def _is_safe_condition(self, condition: str) -> bool:
        """Check if condition is safe to evaluate"""
        try:
            # Parse as Python expression
            tree = ast.parse(condition, mode='eval')
            # Check for dangerous operations
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call)):
                    if isinstance(node, ast.Call):
                        # Allow safe functions
                        func_name = ""
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                        
                        if func_name not in ['get', 'len', 'bool', 'str', 'int', 'float']:
                            return False
                    else:
                        return False
            return True
        except SyntaxError:
            return False
        except ImportError:
            # SafeEvaluator not available yet, use basic check
            return True


class ValidationError(Exception):
    """Schema validation error"""
    def __init__(self, errors: List[str], warnings: List[str]):
        self.errors = errors
        self.warnings = warnings
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        msg = "Schema validation failed:\n"
        if self.errors:
            msg += "\nERRORS:\n"
            for error in self.errors:
                msg += f"  ✗ {error}\n"
        if self.warnings:
            msg += "\nWARNINGS:\n"
            for warning in self.warnings:
                msg += f"  ⚠ {warning}\n"
        return msg


class CodeGenerator:
    """Generate LangGraph runtime from validated schema"""
    
    def __init__(self, schema: Dict[str, Any], deterministic: bool = True):
        self.schema = schema
        # Use fixed timestamp for deterministic builds
        self.timestamp = "GENERATED" if deterministic else datetime.now().isoformat()
        self.missing_impls = set()
        self.deterministic = deterministic
    
    def generate(self) -> Dict[str, str]:
        """Generate all runtime files"""
        files = {}
        
        # Generate main runtime file
        files["runtime/graph_compiled.py"] = self._generate_runtime()
        
        # Generate stubs for missing implementations
        if self.missing_impls:
            files["runtime/nodes_stubs.py"] = self._generate_stubs()
        
        return files
    
    def _generate_runtime(self) -> str:
        """Generate the main runtime file"""
        return f'''"""
Generated LangGraph Runtime
Generated at: {self.timestamp}
Schema: {self.schema["name"]} v{self.schema.get("metadata", {}).get("version", "1.0.0")}

DO NOT EDIT - This file is generated by tools/codegen.py
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional, Union
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
from workflow.tools.safe_eval import evaluate_condition

logger = logging.getLogger(__name__)

# State definition
{self._generate_state_class()}

# Node imports
{self._generate_imports()}

# Node implementations
{self._generate_node_functions()}

# Graph builder
{self._generate_graph_builder()}

# Export
__all__ = ["compile_graph", "GraphState", "run_workflow"]

def run_workflow(inputs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to run the workflow"""
    app = compile_graph()
    # Build initial state with sorted keys for determinism
    initial_state = {{
        "run_id": inputs.get("run_id", ""),
        "user_id": inputs.get("user_id"),
        "inputs": inputs
    }}
    # Add remaining inputs in sorted order
    for key in sorted(inputs.keys()):
        if key not in ["run_id", "user_id", "inputs"]:
            initial_state[key] = inputs[key]
    return app.invoke(initial_state, config=config or {{}})
'''
    
    def _generate_state_class(self) -> str:
        """Generate TypedDict for state"""
        fields = []
        for key, type_str in self.schema["state"].items():
            py_type = self._python_type_from_string(type_str)
            fields.append(f'    {key}: {py_type}')
        
        return f"""class GraphState(TypedDict):
    \"\"\"State for the {self.schema['name']} workflow\"\"\"
{chr(10).join(fields)}"""
    
    def _generate_imports(self) -> str:
        """Generate import statements"""
        imports = []
        stub_imports = []
        
        for node in self.schema["nodes"]:
            impl = node.get("impl", "")
            if not impl:
                continue
            
            if ":" in impl:
                module, func = impl.rsplit(":", 1)
                # Check if module exists
                module_path = Path(__file__).parent.parent / (module.replace(".", "/") + ".py")
                if module_path.exists():
                    imports.append(f"from workflow.{module} import {func}")
                else:
                    self.missing_impls.add(node["id"])
                    stub_imports.append(node["id"])
            else:
                # Agent or tool reference
                if node["type"] == "agent":
                    imports.append(f"from workflow.{impl} import create")
                    imports.append(f"# Agent: {impl}")
        
        import_lines = "\n".join(imports)
        
        if stub_imports:
            import_lines += f"\n\n# Stub imports for missing implementations\nfrom workflow.runtime.nodes_stubs import {', '.join([f'{nid}_stub' for nid in stub_imports])}"
        
        return import_lines
    
    def _generate_node_functions(self) -> str:
        """Generate wrapper functions for nodes"""
        functions = []
        
        for node in self.schema["nodes"]:
            node_id = node["id"]
            node_type = node["type"]
            impl = node.get("impl", "")
            params = node.get("params", {})
            
            if node_type == "agent":
                func_code = self._generate_agent_node(node_id, impl, params)
            elif node_type == "human_gate":
                func_code = self._generate_human_gate_node(node_id, impl, params)
            else:  # python_fn
                func_code = self._generate_python_fn_node(node_id, impl, params)
            
            functions.append(func_code)
        
        return "\n".join(functions)
    
    def _generate_agent_node(self, node_id: str, impl: str, params: Dict) -> str:
        """Generate agent node wrapper"""
        return f'''
def {node_id}_node(state: GraphState) -> GraphState:
    \"\"\"Node: {node_id} (agent)\"\"\"
    try:
        # Store params in state for node to access
        state["_node_params"] = {params}
        
        # Import and create agent
        module_path = "{impl}"
        if ":" in module_path:
            module, func = module_path.rsplit(":", 1)
            exec(f"from workflow.{{module}} import {{func}}")
            agent = eval(f"{{func}}({params})")
        else:
            from workflow.{impl} import create
            agent = create({params})
        
        # Execute agent
        result = agent.invoke(state)
        
        # Clean up params
        if "_node_params" in result:
            del result["_node_params"]
        
        return result
        
    except Exception as e:
        logger.error(f"Error in {node_id}: {{e}}")
        if "{node_id}" in {list(self.missing_impls)}:
            logger.warning(f"Using stub for {node_id}")
            from workflow.runtime.nodes_stubs import {node_id}_stub
            return {node_id}_stub(state)
        raise'''
    
    def _generate_human_gate_node(self, node_id: str, impl: str, params: Dict) -> str:
        """Generate human gate node wrapper"""
        return f'''
def {node_id}_node(state: GraphState) -> GraphState:
    \"\"\"Node: {node_id} (human gate)\"\"\"
    try:
        state["_node_params"] = {params}
        
        if "{impl}":
            module, func = "{impl}".rsplit(":", 1)
            from workflow.{impl.rsplit(":", 1)[0]} import {impl.rsplit(":", 1)[1]}
            result = {impl.rsplit(":", 1)[1]}(state)
        else:
            # Default human gate implementation
            import json
            print("\\n" + "="*60)
            print("🛑 HUMAN REVIEW REQUIRED")
            print("="*60)
            print(json.dumps({{k: v for k, v in state.items() if k != "inputs"}}, indent=2, default=str))
            
            response = input("\\nApprove? (yes/no): ").strip().lower()
            state["approvals"] = {{
                "approved": response == "yes",
                "timestamp": datetime.now().isoformat(),
                "notes": response if response not in ["yes", "no"] else ""
            }}
            result = state
        
        if "_node_params" in result:
            del result["_node_params"]
        return result
        
    except Exception as e:
        logger.error(f"Error in {node_id}: {{e}}")
        raise'''
    
    def _generate_python_fn_node(self, node_id: str, impl: str, params: Dict) -> str:
        """Generate Python function node wrapper"""
        if node_id in self.missing_impls:
            return f'''
def {node_id}_node(state: GraphState) -> GraphState:
    \"\"\"Node: {node_id} (python_fn) - STUB\"\"\"
    logger.warning(f"Using stub for {node_id} - implementation not found: {impl}")
    from workflow.runtime.nodes_stubs import {node_id}_stub
    return {node_id}_stub(state)'''
        
        return f'''
def {node_id}_node(state: GraphState) -> GraphState:
    \"\"\"Node: {node_id} (python_fn)\"\"\"
    try:
        state["_node_params"] = {params}
        
        from workflow.{impl.rsplit(":", 1)[0]} import {impl.rsplit(":", 1)[1]}
        result = {impl.rsplit(":", 1)[1]}(state)
        
        if "_node_params" in result:
            del result["_node_params"]
        return result
        
    except Exception as e:
        logger.error(f"Error in {node_id}: {{e}}")
        raise'''
    
    def _generate_graph_builder(self) -> str:
        """Generate the graph compilation function"""
        nodes = self.schema["nodes"]
        edges = self.schema["edges"]
        checkpointer = self.schema["checkpointer"]
        
        # Build node registration
        node_adds = []
        for node in nodes:
            node_adds.append(f'    graph.add_node("{node["id"]}", {node["id"]}_node)')
        
        # Build edges
        edge_adds = []
        conditional_edges = {}
        
        for edge in edges:
            if "condition" in edge:
                # Group conditional edges by source
                if edge["from"] not in conditional_edges:
                    conditional_edges[edge["from"]] = []
                conditional_edges[edge["from"]].append(edge)
            else:
                edge_adds.append(f'    graph.add_edge("{edge["from"]}", "{edge["to"]}")')
        
        # Build conditional edges
        cond_edge_code = []
        for source, cond_edges in conditional_edges.items():
            # Create router function
            router_code = f'''
    def route_{source}(state: GraphState) -> str:
        \"\"\"Router for {source}\"\"\"'''
            
            for i, edge in enumerate(cond_edges):
                condition = edge["condition"]
                target = edge["to"]
                if i == 0:
                    router_code += f'''
        if evaluate_condition("{condition}", state):
            return "{target}"'''
                else:
                    router_code += f'''
        elif evaluate_condition("{condition}", state):
            return "{target}"'''
            
            # Add default
            router_code += f'''
        return END'''
            
            cond_edge_code.append(router_code)
            cond_edge_code.append(f'    graph.add_conditional_edges("{source}", route_{source})')
        
        # Checkpointer setup
        if checkpointer["type"] == "sqlite":
            checkpointer_code = f'''
    # SQLite checkpointer
    checkpointer = SqliteSaver.from_conn_string("{checkpointer["dsn"]}")'''
        elif checkpointer["type"] == "redis":
            checkpointer_code = f'''
    # Redis checkpointer
    try:
        from langgraph.checkpoint.redis import RedisSaver
        checkpointer = RedisSaver.from_conn_string("{checkpointer["dsn"]}")
    except ImportError:
        logger.warning("Redis not available, using in-memory checkpointer")
        checkpointer = MemorySaver()'''
        else:
            checkpointer_code = '''
    # In-memory checkpointer (default)
    checkpointer = MemorySaver()'''
        
        return f'''def compile_graph() -> StateGraph:
    \"\"\"Compile the {self.schema["name"]} workflow\"\"\"
    
    # Create graph
    graph = StateGraph(GraphState)
    
    # Add nodes
{chr(10).join(node_adds)}
    
    # Add edges
{chr(10).join(edge_adds)}
    
    # Add conditional edges
{"".join(cond_edge_code)}
    
    # Set entry point
    graph.set_entry_point("{nodes[0]["id"]}")
    
    # Setup checkpointer
{checkpointer_code}
    
    # Compile
    app = graph.compile(checkpointer=checkpointer)
    
    return app'''
    
    def _generate_stubs(self) -> str:
        """Generate stub implementations"""
        stubs = []
        
        for node_id in self.missing_impls:
            stubs.append(f'''
def {node_id}_stub(state: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Stub implementation for {node_id}\"\"\"
    import logging
    logging.warning(f"STUB: {node_id} - no implementation found")
    # Pass through state unchanged
    return state''')
        
        return f'''"""
Node stubs - placeholder implementations for missing nodes
Generated by tools/codegen.py at {self.timestamp}

These are fallback implementations. Replace with actual implementations in /nodes/
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

{"".join(stubs)}
'''
    
    def _python_type_from_string(self, type_str: str) -> str:
        """Convert string type to Python type annotation"""
        # Handle common types
        type_map = {
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "dict": "Dict[str, Any]",
            "list": "List[Any]",
            "Any": "Any"
        }
        
        # Return mapped type or original if complex
        if type_str in type_map:
            return type_map[type_str]
        
        # Handle complex types (List[...], Dict[...], Optional[...])
        return type_str


def load_workflow_schema(schema_path: str = "workflow.json") -> Dict[str, Any]:
    """Load and validate workflow schema"""
    workflow_dir = Path(__file__).parent.parent
    schema_file = workflow_dir / schema_path
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    with open(schema_file) as f:
        schema = json.load(f)
    
    # Validate schema
    validator = SchemaValidator(schema)
    validator.validate()
    
    return schema


def main():
    """Main codegen function"""
    try:
        # Load and validate schema
        print("Loading schema...")
        schema = load_workflow_schema()
        print(f"✓ Loaded schema: {schema['name']}")
        
        # Validate
        print("Validating schema...")
        validator = SchemaValidator(schema)
        validator.validate()
        print(f"✓ Schema validation passed")
        
        if validator.warnings:
            print(f"\n⚠ Warnings:")
            for warning in validator.warnings:
                print(f"  - {warning}")
        
        # Generate code (deterministic by default)
        print("\nGenerating code...")
        generator = CodeGenerator(schema, deterministic=True)
        files = generator.generate()
        
        # Write files
        workflow_dir = Path(__file__).parent.parent
        for rel_path, content in files.items():
            file_path = workflow_dir / rel_path
            file_path.parent.mkdir(exist_ok=True, parents=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"✓ Generated: {rel_path}")
        
        # Report missing implementations
        if generator.missing_impls:
            print(f"\n⚠ Missing implementations (stubs generated):")
            for impl in generator.missing_impls:
                print(f"  - {impl}")
        
        print(f"\n✅ Codegen completed successfully!")
        print(f"   Files generated in /runtime/")
        print(f"   Run with: python workflow/run_graph.py")
        
        return 0
        
    except ValidationError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Codegen failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())