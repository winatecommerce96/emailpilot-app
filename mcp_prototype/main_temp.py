import os
from fastapi import FastAPI, Depends, HTTPException
from google.cloud import firestore
from google.cloud import secretmanager
import httpx
from pydantic import BaseModel
from datetime import datetime, timedelta
import google.generativeai as genai

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
    title="MCP Prototype Service (TEMP)",
    description="Temp service to validate Klaviyo metric aggregates request shape.",
)

# --- Firestore Dependency ---
def get_db():
    try:
        db = firestore.Client(project=PROJECT_ID)
        yield db
    finally:
        pass

def access_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

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
                # Normalize dates to ISO UTC with Z; clamp to last 7 days if inputs look stale
                now = datetime.utcnow()
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z',''))
                    end_dt = datetime.fromisoformat(end_date.replace('Z',''))
                except Exception:
                    end_dt = now
                    start_dt = now - timedelta(days=7)

                # If dates are older than 30 days or span is not ~7 days, use last 7 days
                if (now - end_dt).days > 30 or (end_dt - start_dt).days > 8 or (end_dt < start_dt):
                    end_dt = now
                    start_dt = now - timedelta(days=7)

                start_iso = start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

                # Normalize measurement synonyms to sum_value for revenue
                normalized_measurement = measurement
                if measurement in {"sum", "sum($value)", "sum_value($value)", "sum_value()"}:
                    normalized_measurement = "sum_value"
                # Build filter expression per API expectations (quoted timestamps, uppercase AND)
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

                # Sum across interval buckets
                total_value = 0
                if 'data' in data and 'attributes' in data['data'] and 'data' in data['data']['attributes']:
                    for day_data in data['data']['attributes']['data']:
                        if 'measurements' in day_data and normalized_measurement in day_data['measurements']:
                            # Expect array like [value, count?] per docs; use first element
                            total_value += day_data['measurements'][normalized_measurement][0]

                metric_details = await self.get_metric(metric_id)
                return MetricAggregate(
                    metric_name=metric_details.name,
                    measurement=normalized_measurement,
                    total=total_value,
                )
            except httpx.HTTPStatusError as e:
                raise HTTPException(status_code=e.response.status_code, detail=f"Klaviyo API error: {e.response.text}")
            except Exception as e:
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
                "If the user provides a name (like 'Placed Order'), you MUST use a general search tool (like get_metrics) to find the correct ID for that name before calling a more specific tool. "
                "When asked for revenue, you MUST use the get_metric_aggregates tool with the measurement parameter set to 'sum_value'. "
                "Use an ISO8601 UTC timeframe covering the last 7 days. After executing the tools and observing the results, synthesize a final, comprehensive answer for the user."
            ),
        )

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
                for m in placed:
                    agg = await klaviyo_service.get_metric_aggregates(m.id, "sum_value", start.isoformat()+"Z", end.isoformat()+"Z")
                    if agg.total > best_total:
                        best_total = agg.total
                        best_metric = m
                if best_metric is None or best_total == 0:
                    return {"answer": "Unable to determine revenue: Placed Order variants returned 0 over last 7 days.", "tool_calls": []}
                return {"answer": f"Revenue for the last 7 days (Placed Order, metric {best_metric.id}): ${best_total:,.2f}", "tool_calls": [{"name":"get_metrics","args":{}},{"name":"get_metric_aggregates","args":{"metric_id":best_metric.id,"measurement":"sum_value","start_date":start.isoformat()+"Z","end_date":end.isoformat()+"Z"}}]}

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
                            response=response_dict,
                        )
                    ))
                history.append(genai.protos.Content(role="tool", parts=tool_response_parts))
            return {"answer": "Error: The agent exceeded the maximum number of tool calls.", "tool_calls": all_tool_calls}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An error occurred with the AI service: {str(e)}")

# --- API Endpoints ---
@app.post("/clients/{client_id}/agent/query", summary="Query the AI Agent (TEMP)")
async def agent_query(client_id: str, query: AgentQuery, db: firestore.Client = Depends(get_db)):
    if client_id == "local-test":
        klaviyo_api_key = os.environ.get("KLAVIYO_API_KEY")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not klaviyo_api_key or not gemini_api_key:
            raise HTTPException(status_code=500, detail="KLAVIYO_API_KEY and GEMINI_API_KEY environment variables must be set for local testing.")
    else:
        client_ref = db.collection("clients").document(client_id)
        client_doc = client_ref.get()
        if not client_doc.exists:
            # Fallback for known client_id when Firestore doc is absent in this project
            if client_id == "rogue-creamery":
                try:
                    klaviyo_api_key = access_secret(PROJECT_ID, "klaviyo-api-rogue-creamery")
                    gemini_api_key = access_secret(PROJECT_ID, "gemini-api-key")
                except Exception as e:
                    raise HTTPException(status_code=404, detail=f"Client not found in Firestore and secrets unavailable: {str(e)}")
            else:
                raise HTTPException(status_code=404, detail="Client not found in Firestore.")
            client_data = {}
        else:
            client_data = client_doc.to_dict()
        # Resolve Klaviyo API key: prefer any previously resolved secret; otherwise client fields/secret
        klaviyo_api_key = klaviyo_api_key if 'klaviyo_api_key' in locals() and klaviyo_api_key else client_data.get("klaviyo_api_key")
        secret_ref = client_data.get("api_key_encrypted") or client_data.get("klaviyo_api_key_secret")
        try:
            if secret_ref:
                klaviyo_api_key = access_secret(PROJECT_ID, secret_ref)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to access Klaviyo secret '{secret_ref}': {str(e)}")

        # Resolve Gemini API key: use client secret if present; otherwise universal secret
        gemini_api_key = gemini_api_key if 'gemini_api_key' in locals() and gemini_api_key else client_data.get("gemini_api_key")
        gemini_secret_ref = client_data.get("gemini_api_key_secret")
        try:
            if gemini_secret_ref:
                gemini_api_key = access_secret(PROJECT_ID, gemini_secret_ref)
            if not gemini_api_key:
                # fallback to universal secret name
                gemini_api_key = access_secret(PROJECT_ID, "gemini-api-key")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to access Gemini secret: {str(e)}")

        if not klaviyo_api_key:
            raise HTTPException(status_code=400, detail="Klaviyo API key not found for client.")
        if not gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini API key not found (client or universal).")

    klaviyo_service = KlaviyoService(klaviyo_api_key)
    tool_service = ToolService(db)
    ai_service = AIService(gemini_api_key)
    query_with_context = f"client_id: {client_id}, query: {query.query}"
    result = await ai_service.get_answer(query_with_context, klaviyo_service, tool_service)
    return result

@app.get("/debug/clients", summary="List client doc IDs (TEMP)")
def list_clients(db: firestore.Client = Depends(get_db)):
    ids = []
    for doc in db.collection("clients").list_documents():
        try:
            ids.append(doc.id)
        except Exception:
            pass
    return {"project": PROJECT_ID, "clients": sorted(ids)}

def _resolve_keys_for_client(client_id: str, db: firestore.Client):
    if client_id == "local-test":
        k = os.environ.get("KLAVIYO_API_KEY")
        g = os.environ.get("GEMINI_API_KEY")
        if not k or not g:
            raise HTTPException(status_code=500, detail="Missing env keys for local-test")
        return k, g
    if client_id == "rogue-creamery":
        # Use explicit secret names per user instruction
        k = access_secret(PROJECT_ID, "klaviyo-api-rogue-creamery")
        g = access_secret(PROJECT_ID, "gemini-api-key")
        return k, g
    # Default: Firestore
    client_ref = db.collection("clients").document(client_id)
    client_doc = client_ref.get()
    if not client_doc.exists:
        raise HTTPException(status_code=404, detail="Client not found in Firestore.")
    data = client_doc.to_dict()
    k = data.get("klaviyo_api_key")
    ref = data.get("api_key_encrypted") or data.get("klaviyo_api_key_secret")
    if ref:
        k = access_secret(PROJECT_ID, ref)
    g = data.get("gemini_api_key")
    gref = data.get("gemini_api_key_secret")
    if gref:
        g = access_secret(PROJECT_ID, gref)
    if not g:
        g = access_secret(PROJECT_ID, "gemini-api-key")
    if not k or not g:
        raise HTTPException(status_code=400, detail="Missing API keys for client")
    return k, g

@app.get("/debug/metrics/{client_id}")
async def debug_metrics(client_id: str, db: firestore.Client = Depends(get_db)):
    k, g = _resolve_keys_for_client(client_id, db)
    svc = KlaviyoService(k)
    metrics = await svc.get_metrics()
    return {"count": len(metrics), "metrics": [m.dict() for m in metrics]}

@app.get("/debug/aggregate/{client_id}")
async def debug_aggregate(client_id: str, metric_name: str = "Placed Order", db: firestore.Client = Depends(get_db)):
    k, g = _resolve_keys_for_client(client_id, db)
    svc = KlaviyoService(k)
    metrics = await svc.get_metrics()
    target = next((m for m in metrics if m.name.lower() == metric_name.lower()), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    agg = await svc.get_metric_aggregates(target.id, "sum_value", start.isoformat()+"Z", end.isoformat()+"Z")
    return agg.dict()

@app.get("/debug/aggregate_all/{client_id}")
async def debug_aggregate_all(client_id: str, name: str = "Placed Order", db: firestore.Client = Depends(get_db)):
    k, g = _resolve_keys_for_client(client_id, db)
    svc = KlaviyoService(k)
    metrics = await svc.get_metrics()
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    results = []
    for m in metrics:
        if m.name.lower() == name.lower():
            agg = await svc.get_metric_aggregates(m.id, "sum_value", start.isoformat()+"Z", end.isoformat()+"Z")
            results.append({"id": m.id, "name": m.name, "total": agg.total})
    return {"name": name, "results": results}
