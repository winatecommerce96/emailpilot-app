"""
Admin Services Catalog API

Serves the consolidated services catalog for Admin UI consumption.
Reads from docs/services_catalog.json and exposes both a wrapped and raw form.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
import os
from datetime import datetime

router = APIRouter(prefix="/api/admin/services", tags=["Admin Services"])


def _catalog_path() -> Path:
    # repo_root/app/api/admin_services.py -> repo_root
    return Path(__file__).resolve().parents[2] / "docs" / "services_catalog.json"


def _read_catalog():
    p = _catalog_path()
    if not p.exists():
        raise HTTPException(status_code=404, detail="services_catalog.json not found")
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data, p
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read catalog: {e}")


@router.get("")
def list_services():
    data, p = _read_catalog()
    return JSONResponse(
        status_code=200,
        content={
            "items": data,
            "count": len(data) if isinstance(data, list) else 0,
            "source": str(p),
            "last_modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        },
    )


@router.get("/catalog")
def get_catalog_raw():
    data, _ = _read_catalog()
    # Return the exact array for UI consumption
    return JSONResponse(status_code=200, content=data)


@router.get("/status")
def get_services_status():
    """Service catalog status endpoint for admin dashboard"""
    try:
        data, p = _read_catalog()
        return {
            "status": "operational",
            "catalog_loaded": True,
            "services_count": len(data) if isinstance(data, list) else 0,
            "last_updated": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            "source_file": str(p),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "catalog_loaded": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

