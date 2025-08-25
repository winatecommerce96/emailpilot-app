EmailPilot Agent Usage

Overview
- This repo includes a Claude Code agent, `@emailpilot-engineer`, tailored to the EmailPilot stack (FastAPI + Firestore + React).
- It follows the project rules in CLAUDE.md: single entrypoint `main_firestore.py`, Firestore-only backend, static assets under `/static/dist/`, and `--host localhost`.
- “gpt5” items are deprecated; use native Claude models. No gateway setup required.

Prerequisites
- Claude Code CLI installed and authenticated.
- Project dependencies installed in `.venv` when running or testing code.

List Agents
```
claude /agents
```

Use the EmailPilot Agent
```
claude "use @emailpilot-engineer to review /api/admin/upload-package and propose minimal improvements with a test plan"
```

Common Prompts
- Backend endpoint work:
  - `use @emailpilot-engineer to optimize /api/admin/upload-package validation and extraction; keep changes minimal and add a targeted test.`
- Firestore-safe changes:
  - `use @emailpilot-engineer and prefer the Firestore emulator; avoid touching secrets or production config.`
- Frontend asset paths:
  - `use @emailpilot-engineer to ensure all HTML references use /static/dist/ and build passes.`
- QA and tests:
  - `use @emailpilot-engineer and then hand off to @qa-reviewer and @test-runner after changes.`

Local Server Commands (reference)
```
source .venv/bin/activate
pip install -r requirements.txt
make build
uvicorn main_firestore:app --port 8000 --host localhost --reload
# or
make dev
```

Health Checks
```
curl -s http://localhost:8000/health   # {"status":"ok"}
curl -s http://localhost:8000/version  # {"version":"1.0.0"}
```

Tips
- Always use `http://localhost:8000` (not 127.0.0.1).
- Keep patches tight and reversible; avoid unrelated refactors.
- SQLAlchemy-related code is deprecated; code against Firestore.

