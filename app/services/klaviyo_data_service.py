
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from google.cloud import firestore

from app.services.client_key_resolver import get_client_key_resolver
from app.deps.firestore import get_db
from app.services.klaviyo_client import KlaviyoClient
from app.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class KlaviyoDataService:
    """Fetch Klaviyo data and store it in Firestore per client.

    Schema (client-scoped):
    - clients/{client_id}/klaviyo/campaigns/{campaign_id}
    - clients/{client_id}/klaviyo/flows/{flow_id}
    """

    def __init__(self, db: Optional[firestore.Client] = None):
        # Use shared Firestore client helper to honor credentials/secret manager
        self.db = db or get_db()
        self.key_resolver = get_client_key_resolver()

    async def run_daily_sync(self):
        """
        Runs the daily sync for all clients.
        """
        logger.info("Starting daily Klaviyo data sync...")
        clients = self._get_all_clients()
        for client in clients:
            await self.sync_client_data(client['id'])
        logger.info("Daily Klaviyo data sync complete.")

    def _get_all_clients(self) -> list:
        """
        Gets all clients from Firestore.
        """
        clients_ref = self.db.collection('clients')
        docs = list(clients_ref.stream())
        return [doc.to_dict() for doc in docs if doc.exists]

    def _resolve_mcp_client_id(self, client_id: str) -> str:
        """MCP expects client slug in its secret naming (klaviyo-api-<slug>)."""
        try:
            snap = self.db.collection('clients').document(client_id).get()
            if snap.exists:
                data = snap.to_dict() or {}
                slug = data.get('client_slug')
                if slug:
                    return slug
                name = data.get('name') or client_id
                # Basic normalization fallback
                return name.lower().replace('&', 'and').replace(',', '').replace('.', '').replace(' ', '-').replace('--', '-')
        except Exception:
            pass
        return client_id

    async def sync_client_data(self, client_id: str) -> Dict[str, Any]:
        """
        Syncs Klaviyo data for a single client.
        """
        logger.info(f"Syncing data for client {client_id}...")
        api_key = await self.key_resolver.get_client_klaviyo_key(client_id)
        if not api_key:
            logger.warning(f"No Klaviyo API key for client {client_id}. Skipping.")
            return {"client_id": client_id, "campaigns": 0, "flows": 0, "metrics": False}

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=5)

        c_count = await self._sync_campaigns(client_id, api_key, start_date, end_date, write_daily=True)
        f_count = await self._sync_flows(client_id, api_key, start_date, end_date, write_daily=True)
        m_ok = await self._sync_metrics(client_id, api_key)

        return {"client_id": client_id, "campaigns": c_count, "flows": f_count, "metrics": m_ok}

    async def backfill_client_data(self, client_id: str) -> Dict[str, Any]:
        """
        Backfills Klaviyo data for a single client for the last 2 years.
        """
        logger.info(f"Backfilling data for client {client_id}...")
        api_key = await self.key_resolver.get_client_klaviyo_key(client_id)
        if not api_key:
            logger.warning(f"No Klaviyo API key for client {client_id}. Skipping.")
            return {"client_id": client_id, "days": 0, "campaigns": 0, "flows": 0}

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365 * 2)

        total_days = 0
        total_campaigns = 0
        total_flows = 0

        current = start_date
        while current < end_date:
            next_day = current + timedelta(days=1)
            # Write daily snapshots for this day
            total_campaigns += await self._sync_campaigns(client_id, api_key, current, next_day, write_daily=True)
            total_flows += await self._sync_flows(client_id, api_key, current, next_day, write_daily=True)
            total_days += 1
            current = next_day

        # Refresh metrics at end
        await self._sync_metrics(client_id, api_key)

        return {"client_id": client_id, "days": total_days, "campaigns": total_campaigns, "flows": total_flows}

    async def _sync_campaigns(self, client_id: str, api_key: str, start_date: datetime, end_date: datetime, write_daily: bool = False) -> int:
        """Sync campaigns (v2 API) for a client within a date window.

        We fetch recent pages and filter by created/updated timestamps locally,
        storing rich attributes and a best-effort `send_time` field for planning queries.
        """
        # Prefer MCP for campaigns (use slug)
        mcp = MCPClient()
        mcp_id = self._resolve_mcp_client_id(client_id)
        mcp_items: List[Dict[str, Any]] = await mcp.list_campaigns(mcp_id, start_date, end_date)
        # Normalize to data dict shape for downstream loop
        data = {"data": mcp_items, "links": {}}
        written = 0
        cleared_days: set[str] = set()
        while True:
            items: List[Dict[str, Any]] = data.get("data", [])
            for item in items:
                attributes = item.get("attributes", {}) or {}
                created = attributes.get("created") or attributes.get("created_at")
                updated = attributes.get("updated") or attributes.get("updated_at")

                # Choose a sensible event time for filtering and queries
                send_time = (
                    attributes.get("scheduled_at")
                    or attributes.get("send_time")
                    or created
                    or updated
                )
                try:
                    # If no timestamp, skip
                    if not send_time:
                        continue
                    ts = datetime.fromisoformat(str(send_time).replace("Z", "+00:00"))
                except Exception:
                    # If unparsable, keep but do not filter by window
                    ts = None

                # Filter by window if we have a timestamp
                if ts:
                    ts_naive = ts.replace(tzinfo=None)
                    if not (start_date <= ts_naive <= end_date):
                        continue

                campaign_id = item.get("id")
                if not campaign_id:
                    continue

                # Write under client-scoped subcollection
                doc_ref = (
                    self.db.collection("clients")
                    .document(client_id)
                    .collection("klaviyo")
                    .document("meta")  # ensure namespace exists (no-op via merge)
                )
                # Make sure klaviyo namespace exists (best-effort)
                try:
                    doc_ref.set({"t": firestore.SERVER_TIMESTAMP}, merge=True)
                except Exception:
                    pass

                campaign_ref = (
                    self.db.collection("clients")
                    .document(client_id)
                    .collection("klaviyo")
                    .document("data")
                    .collection("campaigns")
                    .document(campaign_id)
                )

                payload: Dict[str, Any] = {
                    "client_id": client_id,
                    "campaign_id": campaign_id,
                    "type": item.get("type"),
                    "attributes": attributes,
                    "name": attributes.get("name"),
                    "status": attributes.get("status"),
                    "created": created,
                    "updated": updated,
                    "scheduled_at": attributes.get("scheduled_at"),
                    "send_time": send_time,
                    "updated_at_firestore": firestore.SERVER_TIMESTAMP,
                }
                campaign_ref.set(payload, merge=True)
                written += 1

                # Optionally write daily snapshot and report
                if write_daily and ts:
                    day_str = ts.date().isoformat()
                    # Clear existing daily docs for the day once to avoid duplicates
                    if day_str not in cleared_days:
                        await self._clear_daily_day(client_id, day_str, kinds=("campaigns", "campaign_reports"))
                        cleared_days.add(day_str)
                    # Daily campaigns snapshot
                    daily_campaign_ref = (
                        self.db.collection("clients")
                        .document(client_id)
                        .collection("klaviyo")
                        .document("data")
                        .collection("daily")
                        .document("campaigns")
                        .collection(day_str)
                        .document(campaign_id)
                    )
                    daily_campaign_ref.set({
                        "client_id": client_id,
                        "campaign_id": campaign_id,
                        "name": attributes.get("name"),
                        "status": attributes.get("status"),
                        "send_time": send_time,
                        "attributes": attributes,
                        "date": day_str,
                        "updated_at_firestore": firestore.SERVER_TIMESTAMP,
                    }, merge=True)

                    # Daily campaign reports (basic: statistics from attributes if present)
                    stats = (attributes or {}).get("statistics", {})
                    daily_report_ref = (
                        self.db.collection("clients")
                        .document(client_id)
                        .collection("klaviyo")
                        .document("data")
                        .collection("daily")
                        .document("campaign_reports")
                        .collection(day_str)
                        .document(campaign_id)
                    )
                    daily_report_ref.set({
                        "client_id": client_id,
                        "campaign_id": campaign_id,
                        "date": day_str,
                        "statistics": stats,
                        "updated_at_firestore": firestore.SERVER_TIMESTAMP,
                    }, merge=True)

            break
        return written

    async def _sync_flows(self, client_id: str, api_key: str, start_date: datetime, end_date: datetime, write_daily: bool = False) -> int:
        """Sync flows (v2 API) for a client; store rich attributes."""
        klaviyo = KlaviyoClient(api_key)
        data = await klaviyo._get("/flows/")
        written = 0
        cleared_days: set[str] = set()
        while True:
            items: List[Dict[str, Any]] = data.get("data", [])
            for item in items:
                attributes = item.get("attributes", {}) or {}
                flow_id = item.get("id")
                if not flow_id:
                    continue

                flow_ref = (
                    self.db.collection("clients")
                    .document(client_id)
                    .collection("klaviyo")
                    .document("data")
                    .collection("flows")
                    .document(flow_id)
                )
                payload: Dict[str, Any] = {
                    "client_id": client_id,
                    "flow_id": flow_id,
                    "type": item.get("type"),
                    "attributes": attributes,
                    "name": attributes.get("name"),
                    "status": attributes.get("status"),
                    "created": attributes.get("created") or attributes.get("created_at"),
                    "updated": attributes.get("updated") or attributes.get("updated_at"),
                    "updated_at_firestore": firestore.SERVER_TIMESTAMP,
                }
                flow_ref.set(payload, merge=True)
                written += 1

            # Optionally write daily flows snapshot for each day in range
            if write_daily:
                day = start_date
                while day < end_date:
                    day_str = day.date().isoformat()
                    if day_str not in cleared_days:
                        await self._clear_daily_day(client_id, day_str, kinds=("flows",))
                        cleared_days.add(day_str)
                    for item in items:
                        attributes = item.get("attributes", {}) or {}
                        flow_id = item.get("id")
                        if not flow_id:
                            continue
                        daily_flow_ref = (
                            self.db.collection("clients")
                            .document(client_id)
                            .collection("klaviyo")
                            .document("data")
                            .collection("daily")
                            .document("flows")
                            .collection(day_str)
                            .document(flow_id)
                        )
                        daily_flow_ref.set({
                            "client_id": client_id,
                            "flow_id": flow_id,
                            "name": attributes.get("name"),
                            "status": attributes.get("status"),
                            "date": day_str,
                            "attributes": attributes,
                            "updated_at_firestore": firestore.SERVER_TIMESTAMP,
                        }, merge=True)
                    day = day + timedelta(days=1)

            next_link = (data.get("links") or {}).get("next")
            if not next_link:
                break
            data = await klaviyo._get(next_link.replace("https://a.klaviyo.com/api", ""))
        return written

    async def _clear_daily_day(self, client_id: str, day_str: str, kinds: tuple[str, ...]) -> None:
        """Delete existing daily docs for specified kinds (campaigns, flows, campaign_reports) for a given day."""
        try:
            base = (
                self.db.collection("clients")
                .document(client_id)
                .collection("klaviyo")
                .document("data")
                .collection("daily")
            )
            for kind in kinds:
                col = base.document(kind).collection(day_str)
                docs = list(col.stream())
                for d in docs:
                    d.reference.delete()
        except Exception as e:
            logger.warning(f"Failed to clear daily docs for {client_id} {day_str} {kinds}: {e}")

    async def _sync_metrics(self, client_id: str, api_key: str) -> bool:
        """Store a simple MTD metrics summary for planning context.

        For a richer implementation, replace with Klaviyo metric-aggregates API.
        """
        try:
            klaviyo = KlaviyoClient(api_key)
            summary = await klaviyo.mtd_summary()
            metrics_ref = (
                self.db.collection("clients")
                .document(client_id)
                .collection("klaviyo")
                .document("data")
                .collection("metrics")
                .document("mtd")
            )
            metrics_ref.set({
                "client_id": client_id,
                "type": "mtd_summary",
                "summary": summary,
                "as_of": datetime.utcnow().isoformat(),
                "updated_at_firestore": firestore.SERVER_TIMESTAMP,
            }, merge=True)
            return True
        except Exception as e:
            logger.error(f"Failed to sync metrics for {client_id}: {e}")
            return False

async def main():
    service = KlaviyoDataService()
    await service.run_daily_sync()

if __name__ == "__main__":
    asyncio.run(main())
