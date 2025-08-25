#!/usr/bin/env python3
"""
Test suite for LangGraph workflow system
"""

import json
import sys
import unittest
from pathlib import Path
import tempfile
import subprocess

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.tools.codegen import load_workflow_schema, generate_runtime_file
from workflow.tools.inspect_agents import AgentInspector


class TestWorkflowSystem(unittest.TestCase):
    """Test the workflow system components"""
    
    def setUp(self):
        """Set up test environment"""
        self.workflow_dir = Path(__file__).parent
        self.test_schema = {
            "name": "test_workflow",
            "state": {
                "input": "str",
                "output": "str",
                "status": "str"
            },
            "nodes": [
                {
                    "id": "start",
                    "type": "python_fn",
                    "impl": "nodes.start:run"
                },
                {
                    "id": "process",
                    "type": "agent",
                    "impl": "agents.test_agent",
                    "params": {
                        "max_retries": 3
                    }
                },
                {
                    "id": "end",
                    "type": "python_fn",
                    "impl": "nodes.end:run"
                }
            ],
            "edges": [
                {"from": "start", "to": "process"},
                {"from": "process", "to": "end"}
            ],
            "checkpointer": {
                "type": "sqlite",
                "dsn": "sqlite:///test.db"
            }
        }
    
    def test_schema_validation(self):
        """Test schema validation"""
        # Valid schema should pass
        try:
            # Save test schema
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(self.test_schema, f)
                schema_path = f.name
            
            # Load and validate
            loaded = load_workflow_schema(schema_path)
            self.assertEqual(loaded["name"], "test_workflow")
            self.assertEqual(len(loaded["nodes"]), 3)
            self.assertEqual(len(loaded["edges"]), 2)
            
        finally:
            Path(schema_path).unlink()
    
    def test_invalid_schema(self):
        """Test invalid schema detection"""
        invalid_schema = {
            "name": "invalid",
            # Missing required fields
            "nodes": []
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_schema, f)
            schema_path = f.name
        
        try:
            with self.assertRaises(ValueError) as ctx:
                load_workflow_schema(schema_path)
            self.assertIn("Missing required field", str(ctx.exception))
        finally:
            Path(schema_path).unlink()
    
    def test_codegen(self):
        """Test code generation"""
        runtime_code = generate_runtime_file(self.test_schema)
        
        # Check for expected components
        self.assertIn("class GraphState(TypedDict):", runtime_code)
        self.assertIn("def compile_graph()", runtime_code)
        self.assertIn("def start_node(state: GraphState)", runtime_code)
        self.assertIn("def process_node(state: GraphState)", runtime_code)
        self.assertIn("def end_node(state: GraphState)", runtime_code)
        
        # Check state fields
        self.assertIn("input: str", runtime_code)
        self.assertIn("output: str", runtime_code)
        self.assertIn("status: str", runtime_code)
        
        # Check graph building
        self.assertIn('graph.add_node("start"', runtime_code)
        self.assertIn('graph.add_node("process"', runtime_code)
        self.assertIn('graph.add_node("end"', runtime_code)
        self.assertIn('graph.add_edge("start", "process")', runtime_code)
        self.assertIn('graph.add_edge("process", "end")', runtime_code)
    
    def test_agent_discovery(self):
        """Test agent discovery"""
        inspector = AgentInspector()
        
        # Test scanning - should find some agents
        catalog = inspector.generate_catalog()
        
        self.assertIn("agents", catalog)
        self.assertIn("tools", catalog)
        self.assertIn("summary", catalog)
        
        # Should find at least the calendar_planner agent we created
        agent_names = [a.get("name") for a in catalog["agents"]]
        self.assertIn("calendar_planner", agent_names)
    
    def test_workflow_schema_export(self):
        """Test exporting to workflow schema format"""
        inspector = AgentInspector()
        workflow_nodes = inspector.export_to_workflow_schema()
        
        self.assertIn("available_nodes", workflow_nodes)
        self.assertIn("metadata", workflow_nodes)
        
        # Check node format
        if workflow_nodes["available_nodes"]:
            node = workflow_nodes["available_nodes"][0]
            self.assertIn("id", node)
            self.assertIn("type", node)
            self.assertIn("impl", node)
    
    def test_conditional_edges(self):
        """Test conditional edge generation"""
        schema_with_conditions = {
            **self.test_schema,
            "edges": [
                {"from": "start", "to": "process"},
                {
                    "from": "process",
                    "to": "success",
                    "condition": "state.get('status') == 'ok'"
                },
                {
                    "from": "process",
                    "to": "failure",
                    "condition": "state.get('status') == 'error'"
                }
            ],
            "nodes": self.test_schema["nodes"] + [
                {"id": "success", "type": "python_fn", "impl": "nodes.success:run"},
                {"id": "failure", "type": "python_fn", "impl": "nodes.failure:run"}
            ]
        }
        
        runtime_code = generate_runtime_file(schema_with_conditions)
        
        # Check for router function
        self.assertIn("def route_process(state: GraphState)", runtime_code)
        self.assertIn("if state.get('status') == 'ok':", runtime_code)
        self.assertIn("elif state.get('status') == 'error':", runtime_code)
        self.assertIn('return "success"', runtime_code)
        self.assertIn('return "failure"', runtime_code)
    
    def test_human_gate_node(self):
        """Test human gate node generation"""
        schema_with_human = {
            **self.test_schema,
            "nodes": [
                {
                    "id": "review",
                    "type": "human_gate",
                    "impl": "nodes.review:run"
                }
            ],
            "edges": []
        }
        
        runtime_code = generate_runtime_file(schema_with_human)
        
        # Check for human gate implementation
        self.assertIn("def review_node(state: GraphState)", runtime_code)
        self.assertIn("HUMAN REVIEW REQUIRED", runtime_code)
        self.assertIn("Approve? (yes/no/file.json):", runtime_code)
    
    def test_cli_runner(self):
        """Test CLI runner script"""
        runner_path = self.workflow_dir / "run_graph.py"
        
        # Test help command
        result = subprocess.run(
            [sys.executable, str(runner_path), "--help"],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Run LangGraph workflow", result.stdout)
        self.assertIn("--inputs", result.stdout)
        self.assertIn("--stream", result.stdout)
        self.assertIn("--interactive", result.stdout)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow system"""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow execution"""
        workflow_dir = Path(__file__).parent
        
        # 1. Create a simple test workflow
        test_workflow = {
            "name": "integration_test",
            "state": {
                "message": "str",
                "processed": "bool"
            },
            "nodes": [
                {
                    "id": "input",
                    "type": "python_fn",
                    "impl": "nodes.input:run"
                },
                {
                    "id": "output",
                    "type": "python_fn",
                    "impl": "nodes.output:run"
                }
            ],
            "edges": [
                {"from": "input", "to": "output"}
            ],
            "checkpointer": {
                "type": "sqlite",
                "dsn": "sqlite:///integration_test.db"
            }
        }
        
        # Save workflow
        workflow_file = workflow_dir / "test_integration.json"
        with open(workflow_file, 'w') as f:
            json.dump(test_workflow, f)
        
        try:
            # 2. Run codegen
            result = subprocess.run(
                [sys.executable, str(workflow_dir / "tools" / "codegen.py")],
                capture_output=True,
                text=True,
                cwd=str(workflow_dir)
            )
            
            if result.returncode != 0:
                print(f"Codegen stderr: {result.stderr}")
            
            self.assertEqual(result.returncode, 0, "Codegen should succeed")
            
            # 3. Check generated files exist
            runtime_file = workflow_dir / "runtime" / "graph_compiled.py"
            stubs_file = workflow_dir / "runtime" / "nodes_stubs.py"
            
            self.assertTrue(runtime_file.exists(), "Runtime file should be generated")
            self.assertTrue(stubs_file.exists(), "Stubs file should be generated")
            
        finally:
            # Cleanup
            if workflow_file.exists():
                workflow_file.unlink()


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()