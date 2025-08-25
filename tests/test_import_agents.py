import json
import subprocess

def test_inspect_agents_runs():
    out = subprocess.check_output(["python","tools/inspect_agents.py"]).decode()
    data = json.loads(out)
    assert isinstance(data.get('agents'), list)
    assert isinstance(data.get('tools'), list)

