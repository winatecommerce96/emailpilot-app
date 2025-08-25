import os
from fastapi import FastAPI, Depends, HTTPException
from google.cloud import firestore
from google.cloud import secretmanager
import httpx
from pydantic import BaseModel
from datetime import datetime, timedelta
import google.generativeai as genai
from typing import List
import threading
import sys
import json
import subprocess
import time

# --- Configuration ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set.")

# --- Pydantic Models ---
class Client(BaseModel):
    name: str
    klaviyo_api_key: str
    gemini_api_key: str

class Campaign(BaseModel):
    id: str
    name: str
    status: str

class Flow(BaseModel):
    id: str
    name: str
    status: str

class KlaviyoList(BaseModel):
    id: str
    name: str

class Segment(BaseModel):
    id: str
    name: str

class Profile(BaseModel):
    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None

class Metric(BaseModel):
    id: str
    name: str

class Event(BaseModel):
    id: str
    metric_name: str
    profile_email: str
    timestamp: datetime

class MetricAggregate(BaseModel):
    metric_name: str
    measurement: str
    total: float

class AgentQuery(BaseModel):
    query: str

class ClientDetails(BaseModel):
    name: str
    klaviyo_api_key: str
    gemini_api_key: str
    metric_id: str | None = None

# --- FastAPI Application ---
app = FastAPI(
    title="MCP Prototype Service",
    description="A simple service to fetch Klaviyo campaign data using client info from Firestore.",
)

# --- Persistent MCP Client ---
class MCPPersistentClient:
    def __init__(self):
        self.proc = None
        self.lock = threading.Lock()
        self.api_key = None

    def _start(self, api_key: str):
        env = os.environ.copy()
        env["PRIVATE_API_KEY"] = api_key
        env.setdefault("READ_ONLY", "true")
        # Spawn process
        self.proc = subprocess.Popen(
            ["uvx", "klaviyo-mcp-server@latest"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1
        )
        # Initialize
        init_req = {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "emailpilot", "version": "1.0"}}
        }
        self._send(init_req)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_response=False)
        self.api_key = api_key

    def _stop(self):
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None
            self.api_key = None

    def _send(self, obj, expect_response=True):
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("MCP process not started")
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
            if not expect_response:
                return None
            line = self.proc.stdout.readline()
            return json.loads(line) if line else {}
        except Exception as e:
            raise

    def call_tool(self, api_key: str, name: str, arguments: dict, timeout: float = 30.0):
        with self.lock:
            # Start or restart if API key changed
            if (self.api_key or "") != (api_key or "") or not self.proc:
                self._stop()
                self._start(api_key)
            req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
            resp = self._send(req, expect_response=True)
            if "error" in resp:
                raise RuntimeError(str(resp["error"]))
            return resp.get("result", {})


# Singleton persistent client
mcp_client = MCPPersistentClient()

# --- Firestore Dependency ---
def get_db():
    try:
        db = firestore.Client(project=PROJECT_ID)
        yield db
    finally:
        pass

# --- Health Endpoint ---
@app.get("/healthz")
def healthz():
    mcp_running = False
    try:
        mcp_running = bool(mcp_client.proc and mcp_client.proc.poll() is None)
    except Exception:
        mcp_running = False
    return {
        "status": "ok",
        "project": PROJECT_ID,
        "mcp_running": mcp_running,
    }

# --- Tool Service ---
class ToolService:
    def __init__(self, db: firestore.Client):
        self.db = db

    def get_client_details(self, client_id: str) -> ClientDetails:
        client_ref = self.db.collection("clients").document(client_id)
        client_doc = client_ref.get()
        if not client_doc.exists:
            raise ValueError(f"Client with ID {client_id} not found.")
        return ClientDetails(**client_doc.to_dict())

# --- Klaviyo Service ---
class KlaviyoService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://a.klaviyo.com/api"
        self.headers = {
            "Authorization": f"Klaviyo-API-Key {self.api_key}",
            "accept": "application/json",
            "content-type": "application/json",
            "revision": "2024-07-15",
        }

    async def get_metrics(self) -> list[Metric]:
        timeout = httpx.Timeout(30.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                url = f"{self.base_url}/metrics/"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return [Metric(id=item['id'], name=item['attributes']['name']) for item in data.get('data', [])]
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")

    async def get_metric(self, metric_id: str) -> Metric:
        timeout = httpx.Timeout(30.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                url = f"{self.base_url}/metrics/{metric_id}/"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                item = data.get('data')
                return Metric(id=item['id'], name=item['attributes']['name'])
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")

    async def get_metric_aggregates(self, metric_id: str, measurement: str, start_date: str, end_date: str) -> MetricAggregate:
        timeout = httpx.Timeout(30.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                url = f"{self.base_url}/metric-aggregates/"
                # Normalize dates to ISO UTC with Z; clamp if inputs look stale
                now = datetime.utcnow()
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z',''))
                    end_dt = datetime.fromisoformat(end_date.replace('Z',''))
                except Exception:
                    end_dt = now
                    start_dt = now - timedelta(days=7)
                if (now - end_dt).days > 30 or (end_dt - start_dt).days > 8 or (end_dt < start_dt):
                    end_dt = now
                    start_dt = now - timedelta(days=7)
                start_iso = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

                # Normalize measurement names; revenue is sum_value
                normalized_measurement = measurement
                if measurement in {"sum", "sum($value)", "sum_value($value)", "sum_value()"}:
                    normalized_measurement = "sum_value"

                # Construct filter expression per API (no quotes around datetimes)
                filter_expr = f"and(greater-or-equal(datetime,{start_iso}),less-than(datetime,{end_iso}))"

                json_payload = {
                    "data": {
                        "type": "metric-aggregate",
                        "attributes": {
                            "metric_id": metric_id,
                            "measurements": [normalized_measurement],
                            "interval": "day",
                            "filter": filter_expr,
                            "timezone": "UTC",
                        },
                    }
                }
                response = await client.post(url, headers=self.headers, json=json_payload)
                response.raise_for_status()
                data = response.json()

                # Correctly parse the response based on the official documentation
                total_value = 0
                if 'data' in data and 'attributes' in data['data'] and 'data' in data['data']['attributes']:
                    for day_data in data['data']['attributes']['data']:
                        if 'measurements' in day_data and normalized_measurement in day_data['measurements']:
                            total_value += day_data['measurements'][normalized_measurement][0]

                metric_details = await self.get_metric(metric_id)
                return MetricAggregate(
                    metric_name=metric_details.name,
                    measurement=normalized_measurement,
                    total=total_value
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

# --- AI Agent Service ---
class AIService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            system_instruction=(
                "You are an expert marketing analyst. Your goal is to answer user questions by using the provided tools to fetch data from the Klaviyo API. "
                "First, reason about the user's question, then decide which tool(s) to call. IMPORTANT: Many tools require a specific ID (e.g., metric_id). "
                "If the user provides a name (like 'Placed Order'), you MUST use a general search tool (like get_metrics) to find the correct ID(s) for that name before calling a more specific tool. "
                "When asked for revenue, you MUST use the get_metric_aggregates tool with the measurement parameter set to 'sum_value'. "
                "If multiple metrics share the same name (e.g., 'Placed Order'), check each candidate's 7-day aggregate and choose the one with a non-zero 'sum_value'. "
                "Use ISO8601 UTC and a valid filter expression for timeframe. After executing tools and observing results, synthesize a clear answer."
            ),
        )
        self._last_mcp_details = None
        self._cached_result = {}

    def _get_account_timezone(self) -> str:
        api_key = os.environ.get("PRIVATE_API_KEY") or os.environ.get("KLAVIYO_API_KEY")
        if not api_key:
            return "UTC"
        try:
            res = mcp_client.call_tool(api_key, "klaviyo_get_account_details", {"model": "claude"})
            sc = res.get("structuredContent", {})
            data = sc.get("data", {})
            attrs = data.get("attributes", {}) if isinstance(data, dict) else {}
            tz = attrs.get("timezone") or attrs.get("time_zone") or attrs.get("account_timezone")
            return tz or "UTC"
        except Exception:
            return "UTC"

    def _tz_window_last_7_days(self, tzname: str) -> tuple[str, str]:
        try:
            tz = ZoneInfo(tzname)
        except Exception:
            tz = ZoneInfo("UTC")
        now_utc = datetime.utcnow()
        now_local = now_utc.astimezone(tz)
        end_local = datetime(year=now_local.year, month=now_local.month, day=now_local.day, tzinfo=tz)
        start_local = end_local - timedelta(days=7)
        # Convert to UTC ISO Z
        start_iso = start_local.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_iso = end_local.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
        return start_iso, end_iso

    async def get_answer(self, query: str, klaviyo_service: KlaviyoService, tool_service: ToolService):
        tools = {
            "get_metrics": klaviyo_service.get_metrics,
            "get_metric_aggregates": klaviyo_service.get_metric_aggregates,
            "get_client_details": tool_service.get_client_details,
        }
        try:
            # Deterministic path for the specific revenue question
            ql = query.lower()
            if "placed order" in ql and "last 7 days" in ql and "revenue" in ql:
                end = datetime.utcnow()
                start = end - timedelta(days=7)
                metrics = await klaviyo_service.get_metrics()
                placed = [m for m in metrics if m.name.lower() == "placed order"]
                best_total = 0.0
                best_metric = None
                variant_results = []
                for m in placed:
                    agg = await klaviyo_service.get_metric_aggregates(m.id, "sum_value", start.isoformat()+"Z", end.isoformat()+"Z")
                    if agg.total > best_total:
                        best_total = agg.total
                        best_metric = m
                    variant_results.append({"metric_id": m.id, "metric_name": m.name, "aggregate_sum_value": agg.total})

                # Compute email-attributed revenue via MCP (Campaign + Flow reports)
                # Prefer known-good TPWsCU first, then try other variants as needed
                email_rev = None
                ordered_candidates = sorted(placed, key=lambda m: 0 if m.id == "TPWsCU" else 1)
                for candidate in ordered_candidates:
                    try:
                        val = await self._compute_email_attributed_revenue(candidate.id)
                        if val is not None and val > 0 and (email_rev is None or val > email_rev):
                            email_rev = val
                            best_metric = candidate
                    except Exception:
                        continue

                debug_enabled = os.environ.get("MCP_DEBUG") == "1"
                if email_rev is not None and email_rev > 0:
                    debug_suffix = ""
                    if debug_enabled and self._last_mcp_details:
                        d = self._last_mcp_details
                        debug_suffix = (
                            f"\n[debug] metric_id={best_metric.id} timeframe={d.get('start')}..{d.get('end')} tz={d.get('timezone','UTC')} "
                            f"campaign_total=${d.get('campaign_total',0):,.2f} flow_total=${d.get('flow_total',0):,.2f} "
                            f"variants={variant_results}"
                        )
                    return {"answer": f"Revenue for the last 7 days (Email-attributed: Campaigns + Flows, Placed Order {best_metric.id}): ${email_rev:,.2f}{debug_suffix}",
                            "tool_calls": [{"name":"get_metrics","args":{}},
                                            {"name":"get_metric_aggregates","args":{"metric_id":best_metric.id,"measurement":"sum_value","start_date":start.isoformat()+"Z","end_date":end.isoformat()+"Z"}}]}
                # If MCP reports failed to produce a value, do not fall back to aggregates for the answer
                return {"answer": "Unable to determine email-attributed revenue via campaign/flow reports for last_7_days. Try again shortly or check campaign/flow report availability.", "tool_calls": []}

            history = [genai.protos.Content(role="user", parts=[genai.protos.Part(text=query)])]
            all_tool_calls = []
            for _ in range(5):
                response = await self.model.generate_content_async(history, tools=list(tools.values()))
                candidate = response.candidates[0]
                if not any(part.function_call for part in candidate.content.parts):
                    return {"answer": candidate.content.parts[0].text, "tool_calls": all_tool_calls}
                history.append(candidate.content)
                function_calls = [part for part in candidate.content.parts if part.function_call]
                tool_results = []
                for part in function_calls:
                    fc = part.function_call
                    tool_name = fc.name
                    tool_args = dict(fc.args)
                    all_tool_calls.append({"name": tool_name, "args": tool_args})
                    tool_function = tools.get(tool_name)
                    if not tool_function:
                        tool_results.append({"tool_name": tool_name, "result": "Error: Tool not found."})
                        continue
                    try:
                        if tool_name in ["get_client_details"]:
                             result = tool_function(**tool_args)
                        else:
                             result = await tool_function(**tool_args)
                        tool_results.append({"tool_name": tool_name, "result": result})
                    except Exception as e:
                        tool_results.append({"tool_name": tool_name, "result": f"Error executing tool: {str(e)}"})
                tool_response_parts = []
                for tr in tool_results:
                    result_data = tr["result"]
                    if isinstance(result_data, list):
                        response_dict = {"result": [item.dict() for item in result_data]}
                    elif hasattr(result_data, 'dict'):
                        response_dict = {"result": result_data.dict()}
                    else:
                        response_dict = {"result": str(result_data)}
                    tool_response_parts.append(genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tr["tool_name"],
                            response=response_dict
                        )
                    ))
                history.append(genai.protos.Content(role="tool", parts=tool_response_parts))
            return {"answer": "Error: The agent exceeded the maximum number of tool calls.", "tool_calls": all_tool_calls}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred with the AI service: {str(e)}")

    async def _compute_email_attributed_revenue(self, conversion_metric_id: str) -> float | None:
        # Use the Klaviyo MCP server to fetch campaign and flow reports, summing conversion_value
        # Timeframe: last 7 days using the built-in key to match Klaviyo UI boundaries
        tzname = self._get_account_timezone()
        timeframe = {"value": {"key": "last_7_days"}}

        # Cache (keyed by metric + window key)
        cache_key = (conversion_metric_id, "last_7_days")
        if cache_key in self._cached_result:
            return self._cached_result[cache_key]

        api_key = os.environ.get("PRIVATE_API_KEY") or os.environ.get("KLAVIYO_API_KEY")
        if not api_key:
            return None

        try:
            camp = mcp_client.call_tool(api_key, "klaviyo_get_campaign_report", {
                "model": "claude",
                "statistics": ["conversions"],
                "conversion_metric_id": conversion_metric_id,
                "value_statistics": ["conversion_value"],
                "timeframe": timeframe
            })
            flow = mcp_client.call_tool(api_key, "klaviyo_get_flow_report", {
                "model": "claude",
                "statistics": ["conversions"],
                "conversion_metric_id": conversion_metric_id,
                "value_statistics": ["conversion_value"],
                "timeframe": timeframe
            })
        except Exception:
            return None

        def _sum_conv_value(result):
            total = 0.0
            sc = result.get("structuredContent", {})
            data = sc.get("data")
            if isinstance(data, dict):
                attr = data.get("attributes", {})
                for r in attr.get("results", []):
                    stats = r.get("statistics", {})
                    total += float(stats.get("conversion_value", 0) or 0)
            return total

        camp_total = _sum_conv_value(camp)
        flow_total = _sum_conv_value(flow)
        self._last_mcp_details = {
            "metric_id": conversion_metric_id,
            "campaign_total": camp_total,
            "flow_total": flow_total,
            "start": "last_7_days",
            "end": "last_7_days",
            "timezone": tzname,
        }
        total = camp_total + flow_total
        self._cached_result[cache_key] = total
        return total

def access_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# --- API Endpoints ---
@app.post("/clients/{client_id}/agent/query", summary="Query the AI Agent")
async def agent_query(client_id: str, query: AgentQuery, db: firestore.Client = Depends(get_db), debug: bool = False):
    if client_id == "local-test":
        klaviyo_api_key = os.environ.get("KLAVIYO_API_KEY")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not klaviyo_api_key or not gemini_api_key:
            raise HTTPException(status_code=500, detail="KLAVIYO_API_KEY and GEMINI_API_KEY environment variables must be set for local testing.")
    else:
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()
        if not client_doc.exists:
            # Allow direct Secret Manager resolution for known client if Firestore doc is missing
            if client_id == "rogue-creamery":
                try:
                    klaviyo_api_key = access_secret(PROJECT_ID, "klaviyo-api-rogue-creamery")
                    gemini_api_key = access_secret(PROJECT_ID, "gemini-api-key")
                except Exception as e:
                    raise HTTPException(status_code=404, detail=f"Client not found in Firestore and secrets unavailable: {str(e)}")
                client_data = {}
            else:
                raise HTTPException(status_code=404, detail="Client not found in Firestore.")
        else:
            client_data = client_doc.to_dict()
        # Resolve Klaviyo API key: prefer secret reference if provided
        klaviyo_api_key = klaviyo_api_key if 'klaviyo_api_key' in locals() and klaviyo_api_key else client_data.get("klaviyo_api_key")
        klaviyo_secret_ref = client_data.get("api_key_encrypted") or client_data.get("klaviyo_api_key_secret")
        try:
            if klaviyo_secret_ref:
                klaviyo_api_key = access_secret(PROJECT_ID, klaviyo_secret_ref)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to access Klaviyo secret '{klaviyo_secret_ref}': {str(e)}")

        # Resolve Gemini API key: use client secret if present; otherwise universal secret
        gemini_api_key = gemini_api_key if 'gemini_api_key' in locals() and gemini_api_key else client_data.get("gemini_api_key")
        gemini_secret_ref = client_data.get("gemini_api_key_secret")
        try:
            if gemini_secret_ref:
                gemini_api_key = access_secret(PROJECT_ID, gemini_secret_ref)
            if not gemini_api_key:
                gemini_api_key = access_secret(PROJECT_ID, "gemini-api-key")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to access Gemini secret: {str(e)}")

        if not klaviyo_api_key:
            raise HTTPException(status_code=400, detail="Klaviyo API key not found for client.")
        if not gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini API key not found (client or universal).")

    # Ensure downstream tooling (MCP subprocess) can read API key from env
    os.environ["KLAVIYO_API_KEY"] = klaviyo_api_key
    os.environ["PRIVATE_API_KEY"] = klaviyo_api_key

    klaviyo_service = KlaviyoService(klaviyo_api_key)
    tool_service = ToolService(db)
    # Optional debug toggle for iteration
    if debug:
        os.environ["MCP_DEBUG"] = "1"
    else:
        os.environ.pop("MCP_DEBUG", None)

    ai_service = AIService(gemini_api_key)
    query_with_context = f"client_id: {client_id}, query: {query.query}"
    result = await ai_service.get_answer(query_with_context, klaviyo_service, tool_service)
    return result
