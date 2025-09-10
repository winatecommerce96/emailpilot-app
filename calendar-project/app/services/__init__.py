"""
Services package initialization.

This module provides initialization utilities for all services
used by the calendar application.
"""

from .firestore_service import initialize_firestore_service, get_firestore_service
from .database_adapter import *
from .google_service import (
    GoogleService, 
    GoogleServiceManager, 
    google_service,
    read_document,
    create_calendar_export,
    ai_chat,
    extract_campaigns
)

__all__ = [
    'initialize_firestore_service',
    'get_firestore_service',
    'GoogleService',
    'GoogleServiceManager',
    'google_service',
    'read_document',
    'create_calendar_export',
    'ai_chat',
    'extract_campaigns'
]