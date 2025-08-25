#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT/"workflow"/"workflow.json").read_text())
nodes = schema.get('nodes',[])

out = { 'agents': [], 'tools': [] }
for n in nodes:
    t = n.get('type')
    impl = n.get('impl') or f"runtime.nodes_stubs:{n.get('id')}"
    item = {
        'id': n.get('id'),
        'type': t,
        'impl': impl,
        'params': n.get('params',{})
    }
    if t == 'agent': out['agents'].append(item)
    elif t == 'tool': out['tools'].append(item)

print(json.dumps(out, indent=2))

