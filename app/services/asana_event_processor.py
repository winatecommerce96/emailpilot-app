from __future__ import annotations
import logging
from typing import Any, Dict, List

from app.services.asana_client import AsanaClient

logger = logging.getLogger(__name__)


async def process_user_events(user_id: str, db, client: AsanaClient) -> Dict[str, Any]:
    """Process queued Asana webhook events for a user.

    - Reads events from users/{user_id}/asana/inbox/events
    - For task-related events, fetches latest task body from Asana and upserts into users/{user_id}/asana/data/tasks/{task_gid}
    - Marks events as processed by deleting them
    """
    inbox = (
        db.collection("users")
        .document(user_id)
        .collection("asana")
        .document("inbox")
        .collection("events")
    )
    events = list(inbox.stream())
    processed = 0
    errors: List[str] = []

    for snap in events:
        try:
            if not snap.exists:
                continue
            payload = snap.to_dict() or {}
            ev = payload.get("event") or payload
            resource = ev.get("resource") or {}
            rtype = resource.get("resource_type")
            gid = resource.get("gid")
            if rtype == "task" and gid:
                # fetch task
                body = await client.get_task(gid, opt_fields="name,completed,assignee,assignee.name,assignee.email,permalink_url,modified_at,projects,due_on")
                tdata = body.get("data", body)
                (
                    db.collection("users")
                    .document(user_id)
                    .collection("asana")
                    .document("data")
                    .collection("tasks")
                    .document(gid)
                    .set({"task": tdata, "updated_from": "webhook"}, merge=True)
                )
                processed += 1
            # delete event after processing
            snap.reference.delete()
        except Exception as e:
            logger.warning(f"Failed processing Asana event for {user_id}: {e}")
            errors.append(str(e))
            # keep event for retry

    return {"processed": processed, "pending": len(events) - processed, "errors": errors}

