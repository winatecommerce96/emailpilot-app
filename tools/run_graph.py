#!/usr/bin/env python3
"""Run the compiled graph with basic pause/resume for a human gate.
State checkpoint stored under runtime/checkpoints/<run_id>.json
"""
import argparse, json, uuid
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/"runtime"
CHECKPOINTS = RUNTIME/"checkpoints"

def load_module():
    import importlib.util, sys
    mod_path = RUNTIME/"graph_compiled.py"
    spec = importlib.util.spec_from_file_location("graph_compiled", str(mod_path))
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    sys.modules["graph_compiled"] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brand', required=True)
    ap.add_argument('--month', required=True)
    ap.add_argument('--run-id', default=None)
    args = ap.parse_args()
    run_id = args.run_id or uuid.uuid4().hex
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    state: Dict[str, Any] = { 'brand': args.brand, 'month': args.month, 'run_id': run_id }
    mod = load_module()
    out = mod.run(state)
    (CHECKPOINTS/f"{run_id}.json").write_text(json.dumps(out, indent=2))
    print("RUN_ID:", run_id)
    print("VISITED:", out.get('visited'))

if __name__ == '__main__':
    main()

