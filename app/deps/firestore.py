import os
from google.cloud import firestore

def get_db():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    # In emulator mode, the client uses FIRESTORE_EMULATOR_HOST automatically
    return firestore.Client(project=project_id)
