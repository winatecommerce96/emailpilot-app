#!/usr/bin/env python3
"""
Preflight checklist runner for EmailPilot.

Runs verifiable checks locally and can update docs/ROLLOUT_CHECKLIST.md
checkboxes when invoked with --write. Designed to be safe and idempotent.

Automated checks covered:
- Backend /health probe at http://localhost:8000/health
- Smoke tests: pytest -q tests/test_smoke.py
- Revenue API /healthz probe at http://127.0.0.1:9090/healthz
- Large logs scan (>500M) and big file scan (>200M)

Usage:
  python scripts/preflight_checklist.py           # report only
  python scripts/preflight_checklist.py --write   # update checklist boxes

Note: Only marks items it can confidently verify; leaves others for manual.
"""
import argparse
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "ROLLOUT_CHECKLIST.md"


def http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "preflight-check/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def run_smoke_tests() -> bool:
    try:
        # Prefer using local venv pytest if available
        cmd = [sys.executable, "-m", "pytest", "-q", "tests/test_smoke.py"]
        proc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return proc.returncode == 0
    except Exception:
        return False


def scan_large_files(patterns=("*.log", "*.out"), threshold_bytes=500 * 1024 * 1024):
    over = []
    for pat in patterns:
        for p in ROOT.rglob(pat):
            try:
                if p.is_file() and p.stat().st_size >= threshold_bytes:
                    over.append(p)
            except FileNotFoundError:
                continue
    # logs/ directory catch-all
    logs_dir = ROOT / "logs"
    if logs_dir.exists():
        for p in logs_dir.rglob("*"):
            try:
                if p.is_file() and p.stat().st_size >= threshold_bytes:
                    over.append(p)
            except FileNotFoundError:
                continue
    return sorted(set(over))


def scan_big_nonlogs(threshold_bytes=200 * 1024 * 1024):
    over = []
    skip_dirs = {".git", ".venv", "node_modules", "__pycache__", "archive"}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        # Skip logs and outs
        if p.suffix in (".log", ".out"):
            continue
        # Skip large tarballs or obvious backups if desired? Keep simple.
        if any(seg in skip_dirs for seg in p.parts):
            continue
        try:
            if p.stat().st_size >= threshold_bytes:
                over.append(p)
        except FileNotFoundError:
            continue
    return sorted(set(over))


def mark_checkbox(text: str, line_pattern: str, check: bool) -> str:
    # Matches a markdown checklist line starting with - [ ] or - [x] then the text
    # We permit flexible spacing and case on [x]
    pattern = re.compile(rf"^(\s*-)\s*\[( |x|X)\]\s*{re.escape(line_pattern)}\s*$")
    out_lines = []
    changed = False
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            box = "x" if check else " "
            new_line = f"{m.group(1)} [{box}] {line_pattern}"
            if new_line != line:
                changed = True
            out_lines.append(new_line)
        else:
            out_lines.append(line)
    return "\n".join(out_lines), changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Update checklist markdown with results")
    args = ap.parse_args()

    # Run checks
    backend_ok = http_ok("http://localhost:8000/health")
    revenue_ok = http_ok("http://127.0.0.1:9090/healthz")
    smoke_ok = run_smoke_tests()
    large_logs = scan_large_files()
    big_files = scan_big_nonlogs()

    print("Preflight summary:")
    print(f"- Backend /health: {'OK' if backend_ok else 'NOT OK'}")
    print(f"- Revenue /healthz: {'OK' if revenue_ok else 'NOT OK'}")
    print(f"- Smoke tests: {'PASS' if smoke_ok else 'FAIL/NOT RUN'}")
    print(f"- Large logs >500M: {len(large_logs)} found")
    for p in large_logs[:5]:
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
        print(f"  • {p} ({sz/1024/1024:.1f} MB)")
    print(f"- Big non-log files >200M: {len(big_files)} found")
    for p in big_files[:5]:
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
        print(f"  • {p} ({sz/1024/1024:.1f} MB)")

    if not args.write:
        return 0

    if not DOC.exists():
        print(f"Checklist doc not found at {DOC}", file=sys.stderr)
        return 2

    text = DOC.read_text(encoding="utf-8")
    changed_any = False

    text, ch = mark_checkbox(text, "Start backend; verify `GET /health` returns 200.", backend_ok)
    changed_any = changed_any or ch

    text, ch = mark_checkbox(text, "Run smoke tests: `pytest -q tests/test_smoke.py`.", smoke_ok)
    changed_any = changed_any or ch

    text, ch = mark_checkbox(text, "`GET :9090/healthz` returns 200.", revenue_ok)
    changed_any = changed_any or ch

    text, ch = mark_checkbox(text, "`GET /api/admin/ops/logs/large?threshold=500M` returns no oversized logs;", len(large_logs) == 0)
    changed_any = changed_any or ch

    text, ch = mark_checkbox(text, "`GET /api/admin/ops/files/big?threshold=200M` has no unexpected large files.", len(big_files) == 0)
    changed_any = changed_any or ch

    if changed_any:
        DOC.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
        print(f"Updated {DOC} with check results.")
    else:
        print("No changes to checklist (already up-to-date or checks failed).")

    return 0


if __name__ == "__main__":
    sys.exit(main())

