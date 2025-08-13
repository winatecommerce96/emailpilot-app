#!/usr/bin/env python3
"""
Test script to verify Firestore connectivity after loading secrets.
"""
from app.core import config

print("Loaded project:", config.settings.project)
db = config.FIRESTORE
doc = db.collection("_health").document("startup")
doc.set({"ok": True}, merge=True)
got = doc.get()
assert got.exists and got.to_dict().get("ok") is True
print("Firestore write/read OK")