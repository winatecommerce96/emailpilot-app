"""
Application dependencies.
"""
from app.deps.secrets import get_secret_manager_service
from app.deps.firestore import get_db

__all__ = ["get_db", "get_secret_manager_service"]