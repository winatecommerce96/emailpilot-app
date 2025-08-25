import asyncio
import types
from datetime import datetime, timedelta
import os
import sys

import pytest

# Ensure local app package is importable
sys.path.append(os.path.abspath('.'))

from app.services.klaviyo_data_service import KlaviyoDataService


class FakeDoc:
    def __init__(self, id, data_dict):
        self.id = id
        # This holds the actual document data
        self._data = data_dict
        self.exists = True

    def set(self, data, merge=False):
        if merge:
            self._data.update(data)
        else:
            # Replace content
            for k in list(self._data.keys()):
                self._data.pop(k, None)
            self._data.update(dict(data))

    def update(self, data):
        self.set(data, merge=True)

    def get(self):
        class Snap:
            def __init__(self, data, id):
                self._data = data
                self.id = id
                self.exists = True

            def to_dict(self):
                return dict(self._data)

        return Snap(self._data, self.id)

    def collection(self, name):
        bucket = self._data.setdefault(name, {})
        return FakeCollection(bucket)


class FakeQuery:
    def __init__(self, store, filters):
        self._store = store
        self._filters = filters

    def where(self, field, op, value):
        return FakeQuery(self._store, self._filters + [(field, op, value)])

    def stream(self):
        def match(doc):
            for field, op, value in self._filters:
                v = doc.get(field)
                if op == '==':
                    if v != value:
                        return False
                elif op == '>=':
                    if v is None or v < value:
                        return False
                elif op == '<':
                    if v is None or v >= value:
                        return False
            return True

        class Snap:
            def __init__(self, id, data):
                self.id = id
                self._data = data
                self.exists = True

            def to_dict(self):
                return dict(self._data)

        for id, data in self._store.items():
            if match(data):
                yield Snap(id, data)


class FakeCollection:
    def __init__(self, store):
        self._store = store

    def document(self, id):
        bucket = self._store.setdefault(id, {})
        return FakeDoc(id, bucket)

    def collection(self, name):
        sub = self._store.setdefault(name, {})
        return FakeCollection(sub)

    def where(self, field, op, value):
        # This assumes this collection is a terminal collection of docs
        return FakeQuery(self._store, [(field, op, value)])

    def stream(self):
        class Snap:
            def __init__(self, id, data):
                self.id = id
                self._data = data
                self.exists = True

            def to_dict(self):
                return dict(self._data)

        for id, data in self._store.items():
            if isinstance(data, dict):
                yield Snap(id, data)


class FakeDB:
    def __init__(self):
        self._root = {}

    def collection(self, name):
        bucket = self._root.setdefault(name, {})
        return FakeCollection(bucket)


def test_sync_client_data_writes_campaigns_and_flows(monkeypatch):
    # Setup fake DB and service
    db = FakeDB()
    svc = KlaviyoDataService(db=db)

    # Stub key resolver
    class KR:
        async def get_client_klaviyo_key(self, client_id):
            return "test-key"

    svc.key_resolver = KR()

    # Monkeypatch KlaviyoClient._get to return sample pages
    from app.services import klaviyo_client as kc

    async def fake_get(self, path, params=None):
        if "/campaigns" in path:
            now = datetime.utcnow()
            created = (now - timedelta(days=1)).isoformat() + "Z"
            return {
                "data": [
                    {
                        "type": "campaign",
                        "id": "cmp_1",
                        "attributes": {
                            "name": "August Promo",
                            "status": "sent",
                            "created": created,
                            "updated": created,
                        },
                    }
                ],
                "links": {"next": None},
            }
        if "/flows" in path:
            now = datetime.utcnow().isoformat() + "Z"
            return {
                "data": [
                    {
                        "type": "flow",
                        "id": "flw_1",
                        "attributes": {
                            "name": "Welcome Series",
                            "status": "live",
                            "created": now,
                            "updated": now,
                        },
                    }
                ],
                "links": {"next": None},
            }
        return {"data": [], "links": {"next": None}}

    monkeypatch.setattr(kc.KlaviyoClient, "_get", fake_get, raising=False)

    # Execute sync
    asyncio.run(svc.sync_client_data("client_123"))

    # Validate writes under clients/client_123/klaviyo/data/campaigns and flows
    campaigns = (
        db.collection("clients")
        .document("client_123")
        .collection("klaviyo")
        .document("data")
        .collection("campaigns")
        .stream()
    )
    flows = (
        db.collection("clients")
        .document("client_123")
        .collection("klaviyo")
        .document("data")
        .collection("flows")
        .stream()
    )

    campaigns_list = list(campaigns)
    flows_list = list(flows)

    assert len(campaigns_list) == 1
    assert campaigns_list[0].to_dict()["campaign_id"] == "cmp_1"
    assert len(flows_list) == 1
    assert flows_list[0].to_dict()["flow_id"] == "flw_1"
