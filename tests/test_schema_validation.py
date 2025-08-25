import json
from pathlib import Path

def test_workflow_json_loadable():
    p = Path('workflow/workflow.json')
    data = json.loads(p.read_text())
    assert 'nodes' in data and 'edges' in data and 'state' in data

