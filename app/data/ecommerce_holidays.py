"""
E-commerce Holidays and Klaviyo Events Data
Comprehensive list of holidays and events important for email marketing
"""

from typing import List, Dict, Any
from datetime import datetime, date

# E-commerce Important Holidays (US Market focused with global additions)
ECOMMERCE_HOLIDAYS = {
    "2025": [
        # January
        {"date": "2025-01-01", "name": "New Year's Day", "type": "holiday", "category": "major", "emoji": "🎊"},
        {"date": "2025-01-20", "name": "Martin Luther King Jr. Day", "type": "holiday", "category": "federal", "emoji": "✊"},
        {"date": "2025-01-29", "name": "Chinese New Year", "type": "holiday", "category": "cultural", "emoji": "🐍"},
        
        # February
        {"date": "2025-02-02", "name": "Super Bowl Sunday", "type": "holiday", "category": "sporting", "emoji": "🏈"},
        {"date": "2025-02-14", "name": "Valentine's Day", "type": "holiday", "category": "major", "emoji": "💝"},
        {"date": "2025-02-17", "name": "Presidents' Day", "type": "holiday", "category": "federal", "emoji": "🇺🇸"},
        {"date": "2025-02-25", "name": "Mardi Gras", "type": "holiday", "category": "cultural", "emoji": "🎭"},
        
        # March
        {"date": "2025-03-08", "name": "International Women's Day", "type": "holiday", "category": "awareness", "emoji": "👩"},
        {"date": "2025-03-17", "name": "St. Patrick's Day", "type": "holiday", "category": "cultural", "emoji": "☘️"},
        {"date": "2025-03-20", "name": "First Day of Spring", "type": "holiday", "category": "seasonal", "emoji": "🌸"},
        
        # April
        {"date": "2025-04-01", "name": "April Fools' Day", "type": "holiday", "category": "fun", "emoji": "🃏"},
        {"date": "2025-04-13", "name": "Palm Sunday", "type": "holiday", "category": "religious", "emoji": "🌴"},
        {"date": "2025-04-18", "name": "Good Friday", "type": "holiday", "category": "religious", "emoji": "✝️"},
        {"date": "2025-04-20", "name": "Easter Sunday", "type": "holiday", "category": "major", "emoji": "🐰"},
        {"date": "2025-04-22", "name": "Earth Day", "type": "holiday", "category": "awareness", "emoji": "🌍"},
        
        # May
        {"date": "2025-05-05", "name": "Cinco de Mayo", "type": "holiday", "category": "cultural", "emoji": "🇲🇽"},
        {"date": "2025-05-11", "name": "Mother's Day", "type": "holiday", "category": "major", "emoji": "👩‍👧"},
        {"date": "2025-05-26", "name": "Memorial Day", "type": "holiday", "category": "federal", "emoji": "🇺🇸"},
        
        # June
        {"date": "2025-06-14", "name": "Flag Day", "type": "holiday", "category": "patriotic", "emoji": "🏴"},
        {"date": "2025-06-15", "name": "Father's Day", "type": "holiday", "category": "major", "emoji": "👨‍👧"},
        {"date": "2025-06-19", "name": "Juneteenth", "type": "holiday", "category": "federal", "emoji": "✊"},
        {"date": "2025-06-21", "name": "First Day of Summer", "type": "holiday", "category": "seasonal", "emoji": "☀️"},
        
        # July
        {"date": "2025-07-04", "name": "Independence Day", "type": "holiday", "category": "major", "emoji": "🎆"},
        {"date": "2025-07-14", "name": "Bastille Day", "type": "holiday", "category": "international", "emoji": "🇫🇷"},
        {"date": "2025-07-24", "name": "Pioneer Day", "type": "holiday", "category": "regional", "emoji": "🚂"},
        
        # August
        {"date": "2025-08-26", "name": "Women's Equality Day", "type": "holiday", "category": "awareness", "emoji": "⚖️"},
        {"date": "2025-08-31", "name": "Summer Sale Season End", "type": "holiday", "category": "retail", "emoji": "🏖️"},
        
        # September
        {"date": "2025-09-01", "name": "Labor Day", "type": "holiday", "category": "federal", "emoji": "👷"},
        {"date": "2025-09-11", "name": "Patriot Day", "type": "holiday", "category": "remembrance", "emoji": "🇺🇸"},
        {"date": "2025-09-22", "name": "First Day of Fall", "type": "holiday", "category": "seasonal", "emoji": "🍂"},
        {"date": "2025-09-23", "name": "Rosh Hashanah", "type": "holiday", "category": "religious", "emoji": "🍎"},
        
        # October
        {"date": "2025-10-02", "name": "Yom Kippur", "type": "holiday", "category": "religious", "emoji": "📖"},
        {"date": "2025-10-13", "name": "Columbus Day", "type": "holiday", "category": "federal", "emoji": "⛵"},
        {"date": "2025-10-13", "name": "Indigenous Peoples' Day", "type": "holiday", "category": "cultural", "emoji": "🪶"},
        {"date": "2025-10-31", "name": "Halloween", "type": "holiday", "category": "major", "emoji": "🎃"},
        
        # November
        {"date": "2025-11-01", "name": "Day of the Dead", "type": "holiday", "category": "cultural", "emoji": "💀"},
        {"date": "2025-11-11", "name": "Veterans Day", "type": "holiday", "category": "federal", "emoji": "🎖️"},
        {"date": "2025-11-27", "name": "Thanksgiving", "type": "holiday", "category": "major", "emoji": "🦃"},
        {"date": "2025-11-28", "name": "Black Friday", "type": "holiday", "category": "retail", "emoji": "🛍️"},
        {"date": "2025-11-29", "name": "Small Business Saturday", "type": "holiday", "category": "retail", "emoji": "🏪"},
        
        # December
        {"date": "2025-12-01", "name": "Cyber Monday", "type": "holiday", "category": "retail", "emoji": "💻"},
        {"date": "2025-12-07", "name": "Pearl Harbor Day", "type": "holiday", "category": "remembrance", "emoji": "⚓"},
        {"date": "2025-12-21", "name": "First Day of Winter", "type": "holiday", "category": "seasonal", "emoji": "❄️"},
        {"date": "2025-12-24", "name": "Christmas Eve", "type": "holiday", "category": "major", "emoji": "🎅"},
        {"date": "2025-12-25", "name": "Christmas Day", "type": "holiday", "category": "major", "emoji": "🎄"},
        {"date": "2025-12-26", "name": "Boxing Day", "type": "holiday", "category": "international", "emoji": "🎁"},
        {"date": "2025-12-26", "name": "Kwanzaa Begins", "type": "holiday", "category": "cultural", "emoji": "🕯️"},
        {"date": "2025-12-31", "name": "New Year's Eve", "type": "holiday", "category": "major", "emoji": "🎉"},
    ]
}

# Klaviyo-specific important dates and events
KLAVIYO_EVENTS = {
    "2025": [
        # Q1 Events
        {"date": "2025-01-15", "name": "Q1 Planning Deadline", "type": "klaviyo", "category": "planning", "emoji": "📋"},
        {"date": "2025-02-01", "name": "February Flow Review", "type": "klaviyo", "category": "review", "emoji": "🔄"},
        {"date": "2025-03-01", "name": "Spring Campaign Launch", "type": "klaviyo", "category": "campaign", "emoji": "🚀"},
        {"date": "2025-03-15", "name": "Q1 Performance Review", "type": "klaviyo", "category": "review", "emoji": "📊"},
        
        # Q2 Events
        {"date": "2025-04-15", "name": "Q2 Planning Deadline", "type": "klaviyo", "category": "planning", "emoji": "📋"},
        {"date": "2025-05-01", "name": "Mother's Day Campaign Start", "type": "klaviyo", "category": "campaign", "emoji": "💐"},
        {"date": "2025-06-01", "name": "Summer Sale Prep", "type": "klaviyo", "category": "campaign", "emoji": "☀️"},
        {"date": "2025-06-15", "name": "Q2 Performance Review", "type": "klaviyo", "category": "review", "emoji": "📊"},
        
        # Q3 Events
        {"date": "2025-07-15", "name": "Q3 Planning Deadline", "type": "klaviyo", "category": "planning", "emoji": "📋"},
        {"date": "2025-08-01", "name": "Back-to-School Campaign", "type": "klaviyo", "category": "campaign", "emoji": "🎒"},
        {"date": "2025-09-01", "name": "Fall Campaign Launch", "type": "klaviyo", "category": "campaign", "emoji": "🍁"},
        {"date": "2025-09-15", "name": "Q3 Performance Review", "type": "klaviyo", "category": "review", "emoji": "📊"},
        
        # Q4 Events - Critical for E-commerce
        {"date": "2025-10-01", "name": "Q4 Strategy Lock", "type": "klaviyo", "category": "planning", "emoji": "🔒"},
        {"date": "2025-10-15", "name": "Holiday Campaign Setup", "type": "klaviyo", "category": "campaign", "emoji": "🎄"},
        {"date": "2025-11-01", "name": "BFCM Flows Live", "type": "klaviyo", "category": "campaign", "emoji": "🛒"},
        {"date": "2025-11-15", "name": "Peak Season Start", "type": "klaviyo", "category": "season", "emoji": "⚡"},
        {"date": "2025-12-15", "name": "Last-Minute Gift Push", "type": "klaviyo", "category": "campaign", "emoji": "🎁"},
        {"date": "2025-12-26", "name": "Year-End Sale Launch", "type": "klaviyo", "category": "campaign", "emoji": "🎊"},
    ]
}

# E-commerce peak seasons and important periods
ECOMMERCE_SEASONS = [
    {"start": "2025-01-01", "end": "2025-01-31", "name": "New Year Sales", "intensity": "high"},
    {"start": "2025-02-01", "end": "2025-02-14", "name": "Valentine's Season", "intensity": "high"},
    {"start": "2025-03-15", "end": "2025-04-20", "name": "Spring/Easter Season", "intensity": "medium"},
    {"start": "2025-05-01", "end": "2025-05-11", "name": "Mother's Day Season", "intensity": "high"},
    {"start": "2025-06-01", "end": "2025-06-15", "name": "Father's Day Season", "intensity": "medium"},
    {"start": "2025-07-01", "end": "2025-07-04", "name": "Independence Day Sales", "intensity": "medium"},
    {"start": "2025-08-15", "end": "2025-09-07", "name": "Back-to-School", "intensity": "high"},
    {"start": "2025-10-15", "end": "2025-10-31", "name": "Halloween Season", "intensity": "medium"},
    {"start": "2025-11-01", "end": "2025-11-30", "name": "Black Friday/Cyber Monday", "intensity": "critical"},
    {"start": "2025-12-01", "end": "2025-12-24", "name": "Holiday Shopping Season", "intensity": "critical"},
    {"start": "2025-12-26", "end": "2025-12-31", "name": "Year-End Clearance", "intensity": "high"},
]

def get_holidays_for_month(year: int, month: int) -> List[Dict[str, Any]]:
    """Get all holidays and events for a specific month"""
    holidays = []
    year_str = str(year)
    
    # Add e-commerce holidays
    if year_str in ECOMMERCE_HOLIDAYS:
        for holiday in ECOMMERCE_HOLIDAYS[year_str]:
            holiday_date = datetime.strptime(holiday["date"], "%Y-%m-%d")
            if holiday_date.month == month:
                holidays.append(holiday)
    
    # Add Klaviyo events
    if year_str in KLAVIYO_EVENTS:
        for event in KLAVIYO_EVENTS[year_str]:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            if event_date.month == month:
                holidays.append(event)
    
    return sorted(holidays, key=lambda x: x["date"])

def get_holidays_for_date(date_str: str) -> List[Dict[str, Any]]:
    """Get all holidays and events for a specific date"""
    holidays = []
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    year_str = str(target_date.year)
    
    # Check e-commerce holidays
    if year_str in ECOMMERCE_HOLIDAYS:
        for holiday in ECOMMERCE_HOLIDAYS[year_str]:
            if holiday["date"] == date_str:
                holidays.append(holiday)
    
    # Check Klaviyo events
    if year_str in KLAVIYO_EVENTS:
        for event in KLAVIYO_EVENTS[year_str]:
            if event["date"] == date_str:
                holidays.append(event)
    
    return holidays

def get_active_seasons(date_str: str) -> List[Dict[str, Any]]:
    """Get any active e-commerce seasons for a given date"""
    active_seasons = []
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    for season in ECOMMERCE_SEASONS:
        start_date = datetime.strptime(season["start"], "%Y-%m-%d").date()
        end_date = datetime.strptime(season["end"], "%Y-%m-%d").date()
        
        if start_date <= target_date <= end_date:
            active_seasons.append(season)
    
    return active_seasons

def generate_recurring_holidays(start_year: int, end_year: int) -> Dict[str, List[Dict[str, Any]]]:
    """Generate recurring holidays for multiple years"""
    holidays_by_year = {}
    
    for year in range(start_year, end_year + 1):
        year_str = str(year)
        holidays_by_year[year_str] = []
        
        # Copy holidays from 2025 and adjust dates
        if "2025" in ECOMMERCE_HOLIDAYS:
            for holiday in ECOMMERCE_HOLIDAYS["2025"]:
                new_holiday = holiday.copy()
                # Adjust year in date
                old_date = datetime.strptime(holiday["date"], "%Y-%m-%d")
                # Handle moveable holidays (simplified - would need more complex logic for actual implementation)
                new_date = old_date.replace(year=year)
                new_holiday["date"] = new_date.strftime("%Y-%m-%d")
                holidays_by_year[year_str].append(new_holiday)
    
    return holidays_by_year