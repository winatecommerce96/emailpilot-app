<!-- GPT‑5 Orchestration Policy: place at top of CLAUDE.md if adopting permanently -->
# Agent Policy (GPT‑5)
- Primary model: **GPT‑5 (alias: sonnet)**; background tasks: **GPT‑5‑mini (alias: haiku)**.
- Always Plan → Act → Verify with explicit tests.
- Prefer diffs/patches; summarize changes before writing.
- After significant edits, invoke **qa-reviewer** and **test-runner** subagents.
- Never read or edit `.env*`, `secrets/**`, SSH keys, or production credentials.
- On failures: localize, propose the minimal fix, re‑run tests.

