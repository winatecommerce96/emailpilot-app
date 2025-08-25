from pathlib import Path
import hashlib
import subprocess

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def test_deterministic_codegen(tmp_path):
    subprocess.check_call(["python","tools/codegen.py"])
    p = Path('runtime/graph_compiled.py')
    h1 = sha(p)
    subprocess.check_call(["python","tools/codegen.py"])
    h2 = sha(p)
    assert h1 == h2

