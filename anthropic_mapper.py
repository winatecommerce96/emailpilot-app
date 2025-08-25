from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
import httpx, os

UPSTREAM = os.getenv("ANTHROPIC_UPSTREAM", "https://api.anthropic.com")
DEFAULT_VERSION = os.getenv("ANTHROPIC_VERSION", "2023-06-01")

ALIAS_MAP = {
    "gpt-5": "claude-3-5-sonnet-20240620",
    "sonnet": "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-latest": "claude-3-5-sonnet-20240620",
    "opus": "claude-3-opus-20240229",
}

app = FastAPI(title="Mini Anthropic Mapper", version="0.1.0")

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/v1/models")
async def models():
    ids = list(ALIAS_MAP.keys()) + list(dict.fromkeys(ALIAS_MAP.values()))
    return {"object": "list", "data": [{"id": mid} for mid in ids]}

@app.post("/v1/messages")
async def messages(req: Request):
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": {"type": "bad_request", "message": "Invalid JSON"}}, status_code=400)

    model = body.get("model")
    if isinstance(model, str) and model in ALIAS_MAP:
        body["model"] = ALIAS_MAP[model]

    incoming = req.headers
    upstream_key = incoming.get("x-api-key") or os.getenv("ANTHROPIC_API_KEY")
    if not upstream_key:
        return JSONResponse({"error": {"type": "authentication_error", "message": "Missing Anthropic API key (x-api-key header or ANTHROPIC_API_KEY env)."}}, status_code=401)

    headers = {
        "x-api-key": upstream_key,
        "anthropic-version": incoming.get("anthropic-version", DEFAULT_VERSION),
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=None) as client:
        url = f"{UPSTREAM}/v1/messages"
        if body.get("stream") is True:
            upstream = await client.stream("POST", url, json=body, headers=headers)
            return StreamingResponse(
                upstream.aiter_raw(),
                status_code=upstream.status_code,
                media_type=upstream.headers.get("content-type", "text/event-stream"),
            )
        else:
            upstream = await client.post(url, json=body, headers=headers)
            return Response(
                content=upstream.content,
                status_code=upstream.status_code,
                media_type=upstream.headers.get("content-type", "application/json"),
            )
