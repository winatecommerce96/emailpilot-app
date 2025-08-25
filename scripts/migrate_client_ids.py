#!/usr/bin/env python3
"""
Migrate Firestore client document IDs from random IDs to human-readable slugs.

For each document in collection 'clients':
 - Read 'client_slug'
 - Copy document to new ID = client_slug (if not exists)
 - Optionally copy subcollections (TODO if required)
 - Write a tombstone in old doc with redirect_to

Run with GOOGLE_CLOUD_PROJECT set appropriately.
"""

import os
from google.cloud import firestore

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise SystemExit("Set GOOGLE_CLOUD_PROJECT")

db = firestore.Client(project=PROJECT_ID)

def migrate_one(doc_ref):
    doc = doc_ref.get()
    if not doc.exists:
        return
    data = doc.to_dict() or {}
    slug = data.get("client_slug")
    if not slug:
        print(f"[skip] {doc_ref.id}: missing client_slug")
        return
    if slug == doc_ref.id:
        print(f"[ok] {doc_ref.id} already uses slug")
        return
    new_ref = db.collection("clients").document(slug)
    if new_ref.get().exists:
        print(f"[skip] new id exists: {slug}")
        return
    # Shallow copy fields
    new_ref.set(data)
    # Tombstone / redirect
    doc_ref.set({"redirect_to": slug}, merge=True)
    print(f"[migrated] {doc_ref.id} -> {slug}")

def main():
    for doc_ref in db.collection("clients").list_documents():
        migrate_one(doc_ref)

if __name__ == "__main__":
    main()

