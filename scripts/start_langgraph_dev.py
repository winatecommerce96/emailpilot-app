#!/usr/bin/env python3
"""
LangGraph Development Server
Alternative to LangGraph Studio for local development
"""

import os
import sys
import json
import uvicorn
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="LangGraph Development Server",
    description="Local development server for LangGraph workflows",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Workflow directory
WORKFLOW_DIR = Path("workflow")
WORKFLOW_DIR.mkdir(exist_ok=True)

class WorkflowSchema(BaseModel):
    """Workflow schema model"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    state: Dict[str, Any] = {}
    nodes: list = []
    edges: list = []
    metadata: Dict[str, Any] = {}

@app.get("/")
async def root():
    """Serve the workflow viewer UI"""
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>LangGraph Development Server</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
</head>
<body class="bg-gray-50">
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect } = React;
        
        function WorkflowViewer() {
            const [workflows, setWorkflows] = useState([]);
            const [selectedWorkflow, setSelectedWorkflow] = useState(null);
            const [loading, setLoading] = useState(true);
            
            useEffect(() => {
                loadWorkflows();
            }, []);
            
            async function loadWorkflows() {
                try {
                    const response = await fetch('/api/workflows');
                    const data = await response.json();
                    setWorkflows(data);
                    if (data.length > 0) {
                        loadWorkflow(data[0].name);
                    }
                } catch (error) {
                    console.error('Failed to load workflows:', error);
                } finally {
                    setLoading(false);
                }
            }
            
            async function loadWorkflow(name) {
                try {
                    const response = await fetch(`/api/workflows/${name}`);
                    const data = await response.json();
                    setSelectedWorkflow(data);
                } catch (error) {
                    console.error('Failed to load workflow:', error);
                }
            }
            
            async function runWorkflow() {
                if (!selectedWorkflow) return;
                
                try {
                    const response = await fetch(`/api/workflows/${selectedWorkflow.name}/run`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            brand: 'Test Brand',
                            month: '2025-10'
                        })
                    });
                    const result = await response.json();
                    alert(`Workflow started: ${result.run_id}`);
                } catch (error) {
                    alert(`Failed to run workflow: ${error}`);
                }
            }
            
            return (
                <div className="min-h-screen p-8">
                    <header className="mb-8">
                        <h1 className="text-3xl font-bold text-gray-900">LangGraph Development Server</h1>
                        <p className="text-gray-600 mt-2">Local workflow viewer and runner</p>
                    </header>
                    
                    {loading ? (
                        <div className="text-center py-12">
                            <div className="text-gray-500">Loading workflows...</div>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                            {/* Workflow List */}
                            <div className="bg-white rounded-lg shadow p-6">
                                <h2 className="text-lg font-semibold mb-4">Workflows</h2>
                                <div className="space-y-2">
                                    {workflows.map(wf => (
                                        <button
                                            key={wf.name}
                                            onClick={() => loadWorkflow(wf.name)}
                                            className={`w-full text-left p-3 rounded hover:bg-gray-50 ${
                                                selectedWorkflow?.name === wf.name ? 'bg-blue-50 border-blue-500 border' : 'border border-gray-200'
                                            }`}
                                        >
                                            <div className="font-medium">{wf.name}</div>
                                            <div className="text-sm text-gray-500">{wf.description}</div>
                                        </button>
                                    ))}
                                </div>
                                
                                {workflows.length === 0 && (
                                    <div className="text-gray-400 text-center py-8">
                                        No workflows found
                                    </div>
                                )}
                            </div>
                            
                            {/* Workflow Details */}
                            <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
                                {selectedWorkflow ? (
                                    <div>
                                        <div className="flex justify-between items-start mb-6">
                                            <div>
                                                <h2 className="text-xl font-semibold">{selectedWorkflow.name}</h2>
                                                <p className="text-gray-600">{selectedWorkflow.description}</p>
                                            </div>
                                            <button
                                                onClick={runWorkflow}
                                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                            >
                                                Run Workflow
                                            </button>
                                        </div>
                                        
                                        {/* Nodes */}
                                        <div className="mb-6">
                                            <h3 className="font-semibold mb-3">Nodes ({selectedWorkflow.nodes?.length || 0})</h3>
                                            <div className="space-y-2">
                                                {selectedWorkflow.nodes?.map(node => (
                                                    <div key={node.id} className="p-3 border rounded">
                                                        <div className="flex items-center justify-between">
                                                            <div>
                                                                <span className="font-medium">{node.id}</span>
                                                                <span className="ml-2 text-sm text-gray-500">({node.type})</span>
                                                            </div>
                                                            <span className="text-xs text-gray-400">{node.impl}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        
                                        {/* Edges */}
                                        <div className="mb-6">
                                            <h3 className="font-semibold mb-3">Edges ({selectedWorkflow.edges?.length || 0})</h3>
                                            <div className="space-y-1">
                                                {selectedWorkflow.edges?.map((edge, i) => (
                                                    <div key={i} className="text-sm">
                                                        <span className="font-mono">{edge.from}</span>
                                                        <span className="mx-2">→</span>
                                                        <span className="font-mono">{edge.to}</span>
                                                        {edge.condition && (
                                                            <span className="ml-2 text-gray-500">if {edge.condition}</span>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        
                                        {/* Raw JSON */}
                                        <details className="mt-6">
                                            <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">
                                                View Raw JSON
                                            </summary>
                                            <pre className="mt-2 p-3 bg-gray-100 rounded text-xs overflow-auto">
                                                {JSON.stringify(selectedWorkflow, null, 2)}
                                            </pre>
                                        </details>
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-gray-400">
                                        Select a workflow to view details
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                    
                    <footer className="mt-12 text-center text-sm text-gray-500">
                        <p>LangGraph Development Server • Port 8123</p>
                        <p className="mt-1">
                            <a href="/docs" className="text-blue-600 hover:underline">API Docs</a>
                            {' • '}
                            <a href="http://localhost:8000/static/workflow_editor.html" className="text-blue-600 hover:underline">
                                Workflow Editor
                            </a>
                        </p>
                    </footer>
                </div>
            );
        }
        
        ReactDOM.render(<WorkflowViewer />, document.getElementById('root'));
    </script>
</body>
</html>
    """)

@app.get("/api/workflows")
async def list_workflows():
    """List all available workflows"""
    workflows = []
    
    # Check for workflow.json
    workflow_file = WORKFLOW_DIR / "workflow.json"
    if workflow_file.exists():
        try:
            with open(workflow_file) as f:
                data = json.load(f)
                workflows.append({
                    "name": data.get("name", "workflow"),
                    "description": data.get("description", ""),
                    "version": data.get("version", "1.0.0")
                })
        except Exception as e:
            logger.error(f"Failed to load workflow.json: {e}")
    
    # Check for other graph files
    for graph_file in WORKFLOW_DIR.glob("*.json"):
        if graph_file.name != "workflow.json":
            try:
                with open(graph_file) as f:
                    data = json.load(f)
                    workflows.append({
                        "name": graph_file.stem,
                        "description": data.get("description", ""),
                        "version": data.get("version", "1.0.0")
                    })
            except Exception:
                pass
    
    return workflows

@app.get("/api/workflows/{name}")
async def get_workflow(name: str):
    """Get a specific workflow schema"""
    # Try exact match first
    workflow_file = WORKFLOW_DIR / f"{name}.json"
    if not workflow_file.exists():
        # Try workflow.json if name matches
        workflow_file = WORKFLOW_DIR / "workflow.json"
        if workflow_file.exists():
            with open(workflow_file) as f:
                data = json.load(f)
                if data.get("name") != name:
                    raise HTTPException(status_code=404, detail="Workflow not found")
        else:
            raise HTTPException(status_code=404, detail="Workflow not found")
    
    try:
        with open(workflow_file) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflows/{name}/run")
async def run_workflow(name: str, context: Dict[str, Any]):
    """Run a workflow (mock implementation)"""
    import uuid
    from datetime import datetime
    
    # In a real implementation, this would trigger the actual workflow
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"Starting workflow '{name}' with run_id: {run_id}")
    logger.info(f"Context: {context}")
    
    # TODO: Integrate with actual workflow runner
    # from workflow.runner import WorkflowRunner
    # runner = WorkflowRunner(name)
    # result = await runner.run(context)
    
    return {
        "run_id": run_id,
        "status": "started",
        "workflow": name,
        "context": context,
        "message": "Workflow started (mock mode - integrate with actual runner)"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "langgraph-dev-server"}

if __name__ == "__main__":
    print("=" * 50)
    print("LangGraph Development Server")
    print("=" * 50)
    print("\nThis is a lightweight alternative to LangGraph Studio")
    print("for local development and testing.\n")
    print("Starting server on http://localhost:8123")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8123, reload=True)