#!/usr/bin/env python3
"""
Agent Discovery: Scan codebase for LangChain agents and tools
"""

import json
import ast
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import importlib.util
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class AgentInspector:
    """Discovers and catalogs agents, tools, and Runnables in the codebase"""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path(__file__).parent.parent.parent
        self.agents = []
        self.tools = []
        self.runnables = []  # New: track Runnable exports
        self.factories = []  # New: track agent factories
        self.errors = []
    
    def scan_directory(self, directory: Path, pattern: str = "*.py") -> List[Path]:
        """Recursively scan directory for Python files"""
        files = []
        for file_path in directory.rglob(pattern):
            # Skip test files and __pycache__
            if '__pycache__' in str(file_path) or 'test_' in file_path.name:
                continue
            files.append(file_path)
        return files
    
    def extract_agent_definitions(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract agent definitions from a Python file"""
        agents = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for agent dictionary patterns
            agent_patterns = [
                r'(\w+_AGENT)\s*=\s*\{[^}]+\}',  # AGENT_NAME = {...}
                r'agents\s*=\s*\[[^\]]+\]',       # agents = [...]
                r'register_agent\([^)]+\)',        # register_agent(...)
            ]
            
            for pattern in agent_patterns:
                matches = re.finditer(pattern, content, re.DOTALL)
                for match in matches:
                    agent_text = match.group(0)
                    # Try to extract agent metadata
                    agent_info = self._parse_agent_definition(agent_text, file_path)
                    if agent_info:
                        agents.append(agent_info)
            
            # Look for LangChain specific patterns
            if 'from langchain' in content or 'import langchain' in content:
                # Parse AST for more accurate extraction
                try:
                    tree = ast.parse(content)
                    agents.extend(self._extract_from_ast(tree, file_path))
                except SyntaxError as e:
                    self.errors.append(f"Syntax error in {file_path}: {e}")
                    
        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")
        
        return agents
    
    def _parse_agent_definition(self, agent_text: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse agent definition from text"""
        agent_info = {
            "file": str(file_path.relative_to(self.base_path)),
            "type": "agent"
        }
        
        # Extract name
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', agent_text)
        if name_match:
            agent_info["name"] = name_match.group(1)
        
        # Extract description
        desc_match = re.search(r'"description"\s*:\s*"([^"]+)"', agent_text)
        if desc_match:
            agent_info["description"] = desc_match.group(1)
        
        # Extract tools
        tools_match = re.search(r'"allowed_tools"\s*:\s*\[([^\]]+)\]', agent_text)
        if tools_match:
            tools_str = tools_match.group(1)
            tools = [t.strip().strip('"\'') for t in tools_str.split(',')]
            agent_info["tools"] = tools
        
        # Extract policy
        policy_match = re.search(r'"policy"\s*:\s*\{([^}]+)\}', agent_text)
        if policy_match:
            policy_str = policy_match.group(1)
            policy = {}
            for item in policy_str.split(','):
                if ':' in item:
                    key, val = item.split(':', 1)
                    key = key.strip().strip('"\'')
                    val = val.strip().strip('"\'')
                    try:
                        val = int(val)
                    except:
                        pass
                    policy[key] = val
            agent_info["policy"] = policy
        
        # Only return if we found a name
        if "name" in agent_info:
            return agent_info
        return None
    
    def _extract_from_ast(self, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Extract agent definitions from AST"""
        agents = []
        
        class AgentVisitor(ast.NodeVisitor):
            def __init__(self, file_path, base_path):
                self.file_path = file_path
                self.base_path = base_path
                self.agents = []
            
            def visit_Assign(self, node):
                # Look for dictionary assignments
                if isinstance(node.value, ast.Dict):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id
                            if 'AGENT' in name or 'agent' in name.lower():
                                # Try to extract dictionary content
                                agent_dict = self._ast_dict_to_dict(node.value)
                                if agent_dict and 'name' in agent_dict:
                                    agent_dict['file'] = str(self.file_path.relative_to(self.base_path))
                                    agent_dict['type'] = 'agent'
                                    agent_dict['var_name'] = name
                                    self.agents.append(agent_dict)
                self.generic_visit(node)
            
            def _ast_dict_to_dict(self, node):
                """Convert AST Dict to Python dict"""
                result = {}
                for key, val in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant):
                        key_str = key.value
                    elif isinstance(key, ast.Str):
                        key_str = key.s
                    else:
                        continue
                    
                    if isinstance(val, ast.Constant):
                        result[key_str] = val.value
                    elif isinstance(val, ast.Str):
                        result[key_str] = val.s
                    elif isinstance(val, ast.Num):
                        result[key_str] = val.n
                    elif isinstance(val, ast.List):
                        result[key_str] = [self._ast_to_value(v) for v in val.elts]
                    elif isinstance(val, ast.Dict):
                        result[key_str] = self._ast_dict_to_dict(val)
                return result
            
            def _ast_to_value(self, node):
                """Convert AST node to value"""
                if isinstance(node, (ast.Constant, ast.Str)):
                    return node.value if isinstance(node, ast.Constant) else node.s
                elif isinstance(node, ast.Num):
                    return node.n
                return None
        
        visitor = AgentVisitor(file_path, self.base_path)
        visitor.visit(tree)
        return visitor.agents
    
    def _extract_tool_functions(self, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Extract @tool decorated functions with typed arguments"""
        tools = []
        
        class ToolVisitor(ast.NodeVisitor):
            def __init__(self, file_path, base_path):
                self.file_path = file_path
                self.base_path = base_path
                self.tools = []
            
            def visit_FunctionDef(self, node):
                # Check for @tool decorator
                for decorator in node.decorator_list:
                    decorator_name = ""
                    if isinstance(decorator, ast.Name):
                        decorator_name = decorator.id
                    elif isinstance(decorator, ast.Attribute):
                        decorator_name = decorator.attr
                    
                    if decorator_name == "tool":
                        tool_info = {
                            "name": node.name,
                            "file": str(self.file_path.relative_to(self.base_path)),
                            "type": "tool",
                            "decorator": "@tool",
                            "args": self._extract_function_args(node)
                        }
                        
                        # Extract docstring
                        if node.body and isinstance(node.body[0], ast.Expr):
                            if isinstance(node.body[0].value, ast.Constant):
                                tool_info["description"] = node.body[0].value.value
                        
                        self.tools.append(tool_info)
                
                self.generic_visit(node)
            
            def _extract_function_args(self, node):
                """Extract function arguments with type annotations"""
                args_info = []
                for arg in node.args.args:
                    arg_info = {"name": arg.arg}
                    if arg.annotation:
                        arg_info["type"] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                    args_info.append(arg_info)
                return args_info
        
        visitor = ToolVisitor(file_path, self.base_path)
        visitor.visit(tree)
        return visitor.tools
    
    def extract_runnables(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract Runnable exports from Python files"""
        runnables = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for Runnable assignments
            runnable_patterns = [
                r'(\w+):\s*Runnable\s*=',  # var: Runnable = ...
                r'(\w+)\s*=\s*Runnable',    # var = Runnable...
                r'(\w+)\s*=\s*.*\.invoke',  # Objects with .invoke method
            ]
            
            for pattern in runnable_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    var_name = match.group(1)
                    runnable_info = {
                        "name": var_name,
                        "file": str(file_path.relative_to(self.base_path)),
                        "type": "runnable",
                        "var_name": var_name
                    }
                    
                    # Check if it's exported (at module level)
                    if re.match(r'^\w+:', content[match.start():], re.MULTILINE):
                        runnable_info["exported"] = True
                    
                    runnables.append(runnable_info)
            
            # Also check for LCEL pipeline patterns
            if 'RunnableParallel' in content or 'RunnableLambda' in content:
                # Parse AST to find pipeline definitions
                tree = ast.parse(content)
                runnables.extend(self._extract_lcel_pipelines(tree, file_path))
                
        except Exception as e:
            self.errors.append(f"Error extracting runnables from {file_path}: {e}")
        
        return runnables
    
    def _extract_lcel_pipelines(self, tree: ast.AST, file_path: Path) -> List[Dict[str, Any]]:
        """Extract LCEL pipeline definitions"""
        pipelines = []
        
        class PipelineVisitor(ast.NodeVisitor):
            def __init__(self, file_path, base_path):
                self.file_path = file_path
                self.base_path = base_path
                self.pipelines = []
            
            def visit_Assign(self, node):
                # Look for pipeline assignments
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Check if value contains LCEL components
                        if self._is_lcel_expression(node.value):
                            pipeline_info = {
                                "name": target.id,
                                "file": str(self.file_path.relative_to(self.base_path)),
                                "type": "lcel_pipeline",
                                "var_name": target.id
                            }
                            
                            # Check for type annotation
                            if isinstance(target, ast.AnnAssign) and target.annotation:
                                if "Runnable" in ast.unparse(target.annotation) if hasattr(ast, 'unparse') else "":
                                    pipeline_info["exported"] = True
                            
                            self.pipelines.append(pipeline_info)
                
                self.generic_visit(node)
            
            def _is_lcel_expression(self, node):
                """Check if node is an LCEL expression"""
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        return node.func.id in ['RunnableParallel', 'RunnableLambda', 'RunnablePassthrough']
                elif isinstance(node, ast.BinOp):
                    # Check for pipe operator |
                    if isinstance(node.op, ast.BitOr):
                        return True
                return False
        
        visitor = PipelineVisitor(file_path, self.base_path)
        visitor.visit(tree)
        return visitor.pipelines
    
    def extract_agent_factories(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract agent factory functions (create* functions)"""
        factories = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            class FactoryVisitor(ast.NodeVisitor):
                def __init__(self, file_path, base_path):
                    self.file_path = file_path
                    self.base_path = base_path
                    self.factories = []
                
                def visit_FunctionDef(self, node):
                    # Check if function name starts with 'create'
                    if node.name.startswith('create'):
                        factory_info = {
                            "name": node.name,
                            "file": str(self.file_path.relative_to(self.base_path)),
                            "type": "agent_factory",
                            "returns": None
                        }
                        
                        # Check return type annotation
                        if node.returns:
                            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
                            factory_info["returns"] = return_type
                            
                            # Check if it returns AgentExecutor or Runnable
                            if "AgentExecutor" in return_type or "Runnable" in return_type:
                                factory_info["creates_agent"] = True
                        
                        # Extract parameters
                        params = []
                        for arg in node.args.args:
                            param = {"name": arg.arg}
                            if arg.annotation:
                                param["type"] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else str(arg.annotation)
                            params.append(param)
                        factory_info["params"] = params
                        
                        # Extract docstring
                        if node.body and isinstance(node.body[0], ast.Expr):
                            if isinstance(node.body[0].value, ast.Constant):
                                factory_info["description"] = node.body[0].value.value
                        
                        self.factories.append(factory_info)
                    
                    self.generic_visit(node)
            
            visitor = FactoryVisitor(file_path, self.base_path)
            visitor.visit(tree)
            factories.extend(visitor.factories)
            
        except Exception as e:
            self.errors.append(f"Error extracting factories from {file_path}: {e}")
        
        return factories
    
    def extract_tool_definitions(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract tool definitions from a Python file"""
        tools = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse AST for @tool decorated functions with typed args
            tree = ast.parse(content)
            tools.extend(self._extract_tool_functions(tree, file_path))
            
            # Look for tool patterns
            tool_patterns = [
                r'@tool\s*\n\s*def\s+(\w+)',           # @tool decorator
                r'Tool\(\s*name\s*=\s*["\']([^"\']+)', # Tool(name=...)
                r'def\s+(\w+_tool)\s*\(',              # function ending in _tool
            ]
            
            for pattern in tool_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    tool_name = match.group(1)
                    tool_info = {
                        "name": tool_name,
                        "file": str(file_path.relative_to(self.base_path)),
                        "type": "tool"
                    }
                    
                    # Try to extract description from docstring
                    func_match = re.search(
                        rf'def\s+{tool_name}\s*\([^)]*\)[^:]*:\s*"""([^"]+)"""',
                        content, re.DOTALL
                    )
                    if func_match:
                        tool_info["description"] = func_match.group(1).strip()
                    
                    tools.append(tool_info)
            
        except Exception as e:
            self.errors.append(f"Error reading {file_path}: {e}")
        
        return tools
    
    def scan_langchain_agents(self) -> Dict[str, Any]:
        """Scan for LangChain agents specifically"""
        langchain_dir = self.base_path / "multi-agent" / "integrations" / "langchain_core"
        
        if not langchain_dir.exists():
            return {"agents": [], "tools": [], "runnables": [], "factories": [], "errors": ["LangChain directory not found"]}
        
        # Scan agents directory
        agents_dir = langchain_dir / "agents"
        if agents_dir.exists():
            for file_path in self.scan_directory(agents_dir):
                self.agents.extend(self.extract_agent_definitions(file_path))
                self.factories.extend(self.extract_agent_factories(file_path))
        
        # Scan tools directory
        tools_dir = langchain_dir / "tools"
        if tools_dir.exists():
            for file_path in self.scan_directory(tools_dir):
                self.tools.extend(self.extract_tool_definitions(file_path))
        
        # Also check admin directory for registry
        admin_dir = langchain_dir / "admin"
        if admin_dir.exists():
            registry_file = admin_dir / "registry.py"
            if registry_file.exists():
                agents_from_registry = self._extract_from_registry(registry_file)
                self.agents.extend(agents_from_registry)
        
        # Scan workflow directory for pipelines and runnables
        workflow_dir = self.base_path / "workflow"
        if workflow_dir.exists():
            # Scan pipelines directory
            pipelines_dir = workflow_dir / "pipelines"
            if pipelines_dir.exists():
                for file_path in self.scan_directory(pipelines_dir):
                    self.runnables.extend(self.extract_runnables(file_path))
            
            # Scan agents directory for factories
            agents_dir = workflow_dir / "agents"
            if agents_dir.exists():
                for file_path in self.scan_directory(agents_dir):
                    self.factories.extend(self.extract_agent_factories(file_path))
        
        return {
            "agents": self.agents,
            "tools": self.tools,
            "runnables": self.runnables,
            "factories": self.factories,
            "errors": self.errors
        }
    
    def _extract_from_registry(self, registry_file: Path) -> List[Dict[str, Any]]:
        """Extract agent definitions from registry file"""
        agents = []
        
        try:
            # Try to import the registry module
            spec = importlib.util.spec_from_file_location("registry", registry_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for get_agent_registry or similar functions
                if hasattr(module, 'get_agent_registry'):
                    registry = module.get_agent_registry()
                    if hasattr(registry, 'list_agents'):
                        agent_list = registry.list_agents()
                        for agent_data in agent_list:
                            agent_data['file'] = str(registry_file.relative_to(self.base_path))
                            agent_data['from_registry'] = True
                            agents.append(agent_data)
                
        except Exception as e:
            # Fallback to text parsing if import fails
            self.errors.append(f"Could not import registry: {e}")
            agents.extend(self.extract_agent_definitions(registry_file))
        
        return agents
    
    def scan_mcp_tools(self) -> List[Dict[str, Any]]:
        """Scan for MCP (Model Context Protocol) tools"""
        mcp_tools = []
        
        # Look for MCP service definitions
        mcp_paths = [
            self.base_path / "app" / "services" / "mcp_service.py",
            self.base_path / "app" / "api" / "mcp.py",
            self.base_path / "app" / "api" / "mcp_klaviyo.py"
        ]
        
        for mcp_path in mcp_paths:
            if mcp_path.exists():
                tools = self._extract_mcp_tools(mcp_path)
                mcp_tools.extend(tools)
        
        return mcp_tools
    
    def _extract_mcp_tools(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract MCP tool definitions"""
        tools = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Look for MCP tool patterns
            tool_matches = re.finditer(
                r'tools\s*=\s*\[([^\]]+)\]',
                content, re.DOTALL
            )
            
            for match in tool_matches:
                tools_text = match.group(1)
                # Parse individual tools
                tool_defs = re.finditer(
                    r'\{\s*"name"\s*:\s*"([^"]+)"[^}]+\}',
                    tools_text, re.DOTALL
                )
                for tool_def in tool_defs:
                    tool_name = tool_def.group(1)
                    tools.append({
                        "name": tool_name,
                        "file": str(file_path.relative_to(self.base_path)),
                        "type": "mcp_tool",
                        "protocol": "MCP"
                    })
            
        except Exception as e:
            self.errors.append(f"Error extracting MCP tools from {file_path}: {e}")
        
        return tools
    
    def generate_catalog(self) -> Dict[str, Any]:
        """Generate complete catalog of agents and tools"""
        # Scan LangChain agents
        langchain_results = self.scan_langchain_agents()
        
        # Scan MCP tools
        mcp_tools = self.scan_mcp_tools()
        
        # Scan general Python tools
        app_dir = self.base_path / "app"
        if app_dir.exists():
            for file_path in self.scan_directory(app_dir):
                self.tools.extend(self.extract_tool_definitions(file_path))
        
        # Combine all results
        catalog = {
            "agents": langchain_results["agents"],
            "tools": langchain_results["tools"] + mcp_tools + self.tools,
            "runnables": langchain_results.get("runnables", []) + self.runnables,
            "factories": langchain_results.get("factories", []) + self.factories,
            "errors": langchain_results.get("errors", []) + self.errors,
            "summary": {
                "total_agents": len(langchain_results["agents"]),
                "total_tools": len(langchain_results["tools"] + mcp_tools + self.tools),
                "total_runnables": len(langchain_results.get("runnables", []) + self.runnables),
                "total_factories": len(langchain_results.get("factories", []) + self.factories),
                "langchain_agents": len(langchain_results["agents"]),
                "langchain_tools": len(langchain_results["tools"]),
                "mcp_tools": len(mcp_tools),
                "other_tools": len(self.tools),
                "runnables": len(self.runnables),
                "factories": len(self.factories)
            }
        }
        
        return catalog
    
    def export_to_json(self, output_path: Optional[Path] = None) -> Path:
        """Export catalog to JSON file"""
        catalog = self.generate_catalog()
        
        if not output_path:
            output_path = self.base_path / "workflow" / "agents_catalog.json"
        
        with open(output_path, 'w') as f:
            json.dump(catalog, f, indent=2, default=str)
        
        return output_path
    
    def export_to_workflow_schema(self) -> Dict[str, Any]:
        """Export agents as workflow-compatible node definitions"""
        catalog = self.generate_catalog()
        
        nodes = []
        
        # Add agents
        for agent in catalog["agents"]:
            node = {
                "id": agent["name"].replace("_", "-"),
                "type": "agent",
                "impl": f"agents.{agent['name']}",
                "description": agent.get("description", ""),
                "params": {
                    "tool_allowlist": agent.get("tools", [])
                }
            }
            if "policy" in agent:
                node["params"]["policy"] = agent["policy"]
            nodes.append(node)
        
        # Add tools
        for tool in catalog["tools"]:
            node = {
                "id": tool["name"].replace("_", "-"),
                "type": "tool",
                "impl": f"tools.{tool['name']}",
                "description": tool.get("description", "")
            }
            if tool.get("type") == "mcp_tool":
                node["protocol"] = "MCP"
            if "args" in tool:
                node["args"] = tool["args"]
            nodes.append(node)
        
        # Add runnables
        for runnable in catalog.get("runnables", []):
            node = {
                "id": runnable["name"].replace("_", "-"),
                "type": "runnable" if runnable["type"] == "runnable" else "pipeline",
                "impl": f"{runnable['file'].replace('.py', '').replace('/', '.')}:{runnable['name']}",
                "description": f"Runnable from {runnable['file']}",
                "exported": runnable.get("exported", False)
            }
            nodes.append(node)
        
        # Add factories
        for factory in catalog.get("factories", []):
            node = {
                "id": factory["name"].replace("_", "-"),
                "type": "factory",
                "impl": f"{factory['file'].replace('.py', '').replace('/', '.')}:{factory['name']}",
                "description": factory.get("description", f"Factory function {factory['name']}"),
                "returns": factory.get("returns", "unknown"),
                "params": factory.get("params", [])
            }
            if factory.get("creates_agent"):
                node["creates_agent"] = True
            nodes.append(node)
        
        return {
            "available_nodes": nodes,
            "metadata": catalog["summary"]
        }


def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover agents and tools in codebase")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--format", choices=["catalog", "workflow"], default="catalog",
                        help="Output format")
    parser.add_argument("--base-path", help="Base path to scan")
    
    args = parser.parse_args()
    
    inspector = AgentInspector(Path(args.base_path) if args.base_path else None)
    
    if args.format == "workflow":
        result = inspector.export_to_workflow_schema()
        output_path = args.output or "workflow/available_nodes.json"
    else:
        result = inspector.generate_catalog()
        output_path = args.output or "workflow/agents_catalog.json"
    
    output = Path(output_path)
    output.parent.mkdir(exist_ok=True, parents=True)
    
    with open(output, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"Agent discovery complete!")
    print(f"Output written to: {output}")
    
    if "summary" in result:
        print(f"\nSummary:")
        for key, value in result["summary"].items():
            print(f"  {key}: {value}")
    
    if result.get("errors"):
        print(f"\nWarnings ({len(result['errors'])}):")
        for error in result["errors"][:5]:
            print(f"  - {error}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())