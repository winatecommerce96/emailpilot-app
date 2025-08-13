#!/usr/bin/env python3
"""
Test script to verify Secret Manager connectivity and secret loading.
"""
from app.services.secret_manager import get_secret_strict, get_secret_json_strict
import os
from google.auth import default as adc_default

# Get project from environment or ADC
proj_env = os.getenv("GOOGLE_CLOUD_PROJECT")
_, proj_adc = adc_default()
project = proj_env or proj_adc
assert project, "No project id available"

print("Project:", project)
print("Transport:", os.getenv("SECRET_MANAGER_TRANSPORT", "rest"))

# Load secrets
pid = get_secret_strict(project, "emailpilot-firestore-project")
sa = get_secret_json_strict(project, "emailpilot-google-credentials")
sk = get_secret_strict(project, "emailpilot-secret-key")

print("emailpilot-firestore-project:", pid)
print("google-credentials keys:", list(sa.keys())[:5])
print("secret-key length:", len(sk))