# Proxy module - imports the full app from main_firestore.py
# This maintains backwards compatibility with Dockerfile using app.main:app

import sys
import os

# Add parent directory to path so we can import main_firestore
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_firestore import app

# Re-export the app
__all__ = ['app']
