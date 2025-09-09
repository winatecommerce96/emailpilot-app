"""
Calendar Holidays and Events API
Manages e-commerce holidays and Klaviyo events in Firestore
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from google.cloud import firestore

from app.deps import get_db
from app.data.ecommerce_holidays import (
    ECOMMERCE_HOLIDAYS,
    KLAVIYO_EVENTS,
    ECOMMERCE_SEASONS,
    get_holidays_for_month,
    get_holidays_for_date,
    get_active_seasons
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/holidays", tags=["Calendar Holidays"])

class HolidayCreate(BaseModel):
    date: str
    name: str
    type: str  # 'holiday', 'klaviyo', 'custom'
    category: str
    emoji: Optional[str] = "📅"
    description: Optional[str] = None
    admin_only: bool = True

class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None
    admin_only: Optional[bool] = None

@router.get("/")
async def get_holidays(
    year: int = Query(..., description="Year to fetch holidays for"),
    month: Optional[int] = Query(None, description="Specific month (1-12)"),
    include_klaviyo: bool = Query(True, description="Include Klaviyo events"),
    include_seasons: bool = Query(True, description="Include e-commerce seasons"),
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get holidays and events for a specific year/month"""
    try:
        holidays = []
        year_str = str(year)
        
        # Check if holidays are initialized in Firestore
        meta_doc = db.collection("calendar_holidays_meta").document(year_str).get()
        
        # Only use hardcoded data if NOT initialized in Firestore
        if not meta_doc.exists:
            # Get holidays from data file
            if month:
                holidays = get_holidays_for_month(year, month)
            else:
                # Get all holidays for the year
                if year_str in ECOMMERCE_HOLIDAYS:
                    holidays.extend(ECOMMERCE_HOLIDAYS[year_str])
                if include_klaviyo and year_str in KLAVIYO_EVENTS:
                    holidays.extend(KLAVIYO_EVENTS[year_str])
        
        # Get holidays from Firestore (both initialized and custom)
        firestore_holidays = []
        if month:
            start_date = f"{year}-{month:02d}-01"
            end_date = f"{year}-{month:02d}-31"
        else:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
        
        docs = db.collection("calendar_holidays")\
            .where("date", ">=", start_date)\
            .where("date", "<=", end_date)\
            .stream()
        
        for doc in docs:
            holiday_data = doc.to_dict()
            holiday_data["id"] = doc.id
            # Preserve original type if it exists
            if "type" not in holiday_data:
                holiday_data["type"] = "custom"
            firestore_holidays.append(holiday_data)
        
        # Combine holidays (no duplicates)
        all_holidays = holidays + firestore_holidays
        
        # Add season information if requested
        if include_seasons:
            for holiday in all_holidays:
                holiday["active_seasons"] = get_active_seasons(holiday["date"])
        
        # Sort by date
        all_holidays.sort(key=lambda x: x["date"])
        
        return {
            "holidays": all_holidays,
            "total": len(all_holidays),
            "year": year,
            "month": month,
            "stats": {
                "national_holidays": len([h for h in all_holidays if h.get("type") == "holiday"]),
                "klaviyo_events": len([h for h in all_holidays if h.get("type") == "klaviyo"]),
                "custom_events": len([h for h in all_holidays if h.get("type") == "custom"])
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching holidays: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/date/{date}")
async def get_holidays_for_specific_date(
    date: str,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Get all holidays and events for a specific date"""
    try:
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Get holidays from data
        holidays = get_holidays_for_date(date)
        
        # Get custom holidays from Firestore
        docs = db.collection("calendar_holidays")\
            .where("date", "==", date)\
            .stream()
        
        for doc in docs:
            holiday_data = doc.to_dict()
            holiday_data["id"] = doc.id
            holiday_data["type"] = "custom"
            holidays.append(holiday_data)
        
        # Get active seasons
        active_seasons = get_active_seasons(date)
        
        return {
            "date": date,
            "holidays": holidays,
            "active_seasons": active_seasons,
            "total": len(holidays)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching holidays for date {date}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom")
async def create_custom_holiday(
    holiday: HolidayCreate,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Create a custom holiday or event"""
    try:
        # Validate date format
        try:
            datetime.strptime(holiday.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Create holiday document
        holiday_data = holiday.dict()
        holiday_data["created_at"] = datetime.utcnow().isoformat()
        holiday_data["type"] = "custom"
        
        # Add to Firestore
        doc_ref = db.collection("calendar_holidays").add(holiday_data)
        holiday_id = doc_ref[1].id
        
        holiday_data["id"] = holiday_id
        
        return {
            "message": "Custom holiday created successfully",
            "holiday": holiday_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom holiday: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/custom/{holiday_id}")
async def update_custom_holiday(
    holiday_id: str,
    update_data: HolidayUpdate,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Update a custom holiday"""
    try:
        doc_ref = db.collection("calendar_holidays").document(holiday_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Holiday not found")
        
        # Prepare update data
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow().isoformat()
        
        # Update document
        doc_ref.update(update_dict)
        
        # Get updated document
        updated_doc = doc_ref.get()
        holiday_data = updated_doc.to_dict()
        holiday_data["id"] = holiday_id
        
        return {
            "message": "Holiday updated successfully",
            "holiday": holiday_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating holiday {holiday_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/custom/{holiday_id}")
async def delete_custom_holiday(
    holiday_id: str,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a custom holiday"""
    try:
        doc_ref = db.collection("calendar_holidays").document(holiday_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Holiday not found")
        
        # Delete document
        doc_ref.delete()
        
        return {"message": "Holiday deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting holiday {holiday_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize/{year}")
async def initialize_holidays_for_year(
    year: int,
    db: firestore.Client = Depends(get_db)
) -> Dict[str, Any]:
    """Initialize all holidays and events for a specific year in Firestore"""
    try:
        year_str = str(year)
        initialized_count = 0
        
        # Check if already initialized
        existing = db.collection("calendar_holidays_meta")\
            .document(year_str)\
            .get()
        
        if existing.exists:
            return {
                "message": f"Holidays for {year} already initialized",
                "initialized": False
            }
        
        # Initialize e-commerce holidays
        if year_str in ECOMMERCE_HOLIDAYS:
            for holiday in ECOMMERCE_HOLIDAYS[year_str]:
                holiday_data = holiday.copy()
                holiday_data["admin_only"] = True
                holiday_data["initialized"] = True
                holiday_data["created_at"] = datetime.utcnow().isoformat()
                
                db.collection("calendar_holidays").add(holiday_data)
                initialized_count += 1
        
        # Initialize Klaviyo events
        if year_str in KLAVIYO_EVENTS:
            for event in KLAVIYO_EVENTS[year_str]:
                event_data = event.copy()
                event_data["admin_only"] = True
                event_data["initialized"] = True
                event_data["created_at"] = datetime.utcnow().isoformat()
                
                db.collection("calendar_holidays").add(event_data)
                initialized_count += 1
        
        # Mark year as initialized
        db.collection("calendar_holidays_meta").document(year_str).set({
            "year": year,
            "initialized_at": datetime.utcnow().isoformat(),
            "holidays_count": initialized_count
        })
        
        return {
            "message": f"Successfully initialized {initialized_count} holidays and events for {year}",
            "year": year,
            "count": initialized_count,
            "initialized": True
        }
        
    except Exception as e:
        logger.error(f"Error initializing holidays for year {year}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/seasons")
async def get_ecommerce_seasons(
    date: Optional[str] = Query(None, description="Check active seasons for specific date")
) -> Dict[str, Any]:
    """Get e-commerce seasons information"""
    try:
        if date:
            # Validate date format
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
            active_seasons = get_active_seasons(date)
            return {
                "date": date,
                "active_seasons": active_seasons,
                "is_peak_season": any(s["intensity"] in ["high", "critical"] for s in active_seasons)
            }
        else:
            # Return all seasons
            return {
                "seasons": ECOMMERCE_SEASONS,
                "total": len(ECOMMERCE_SEASONS)
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching seasons: {e}")
        raise HTTPException(status_code=500, detail=str(e))