# Refactoring Summary: Centralized Dependency Injection

This document outlines the recent refactoring effort to centralize dependency injection for services like settings management and database connections.

## Key Changes

-   **Deleted Modules**: The following modules have been deleted and their functionality replaced:
    -   `app/core/config.py`
    -   `app/services/secret_manager.py`
    -   `app/services/firestore_client.py`

-   **New Modules**:
    -   `app/core/settings.py`: Manages application settings using Pydantic's `BaseSettings`.
    -   `app/services/secrets.py`: A new `SecretManagerService` for interacting with Google Secret Manager.
    -   `app/deps/`: A new package for centralized dependency injection functions.
        -   `app/deps/firestore.py`: Provides the `get_db` dependency for Firestore.
        -   `app/deps/secrets.py`: Provides the `get_secret_manager_service` dependency.

## How to Use the New System

To access application settings, the Firestore database, or the Secret Manager service, use the `Depends` function from FastAPI with the appropriate dependency function.

### Example: Accessing Settings

```python
from fastapi import APIRouter, Depends
from app.core.settings import Settings, get_settings

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(settings: Settings = Depends(get_settings)):
    # Use the settings object
    print(settings.google_cloud_project)
```

### Example: Accessing the Database

```python
from fastapi import APIRouter, Depends
from google.cloud import firestore
from app.deps import get_db

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(db: firestore.Client = Depends(get_db)):
    # Use the db object
    docs = db.collection("my-collection").stream()
```

### Example: Accessing the Secret Manager

```python
from fastapi import APIRouter, Depends
from app.services.secrets import SecretManagerService
from app.deps import get_secret_manager_service

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(secret_manager: SecretManagerService = Depends(get_secret_manager_service)):
    # Use the secret_manager object
    my_secret = secret_manager.get_secret("my-secret")
```
