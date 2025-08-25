"""
Klaviyo Feedback and Validation System
Helps identify and resolve discrepancies between API results and direct Klaviyo data
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field
import httpx

from app.deps.firestore import get_db
from app.utils.klaviyo_api import ensure_klaviyo_api_available, get_base_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/klaviyo/feedback", tags=["Klaviyo Feedback"])


class DataDiscrepancyReport(BaseModel):
    """Report of discrepancy between API and Klaviyo direct data"""
    query: str = Field(..., description="The original query that was executed")
    client_id: str = Field(..., description="Client ID used in the query")
    date_range: Dict[str, str] = Field(..., description="Date range used")
    api_response: Dict[str, Any] = Field(..., description="What our API returned")
    klaviyo_actual: Dict[str, Any] = Field(..., description="What Klaviyo shows directly")
    discrepancy_details: str = Field(..., description="Description of the discrepancy")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ValidationRequest(BaseModel):
    """Request to validate API results against expected values"""
    client_id: str
    start_date: str
    end_date: str
    expected_revenue: Optional[float] = None
    expected_orders: Optional[int] = None
    expected_campaign_revenue: Optional[float] = None
    expected_flow_revenue: Optional[float] = None
    notes: Optional[str] = None


class DebugInfo(BaseModel):
    """Detailed debug information for troubleshooting"""
    client_config: Dict[str, Any]
    api_request: Dict[str, Any]
    api_response: Dict[str, Any]
    klaviyo_direct_params: Dict[str, Any]
    potential_issues: List[str]


# Store feedback for analysis (in production, this would be in Firestore)
feedback_store: List[DataDiscrepancyReport] = []


@router.post("/report-discrepancy")
async def report_discrepancy(report: DataDiscrepancyReport) -> Dict[str, Any]:
    """
    Report a discrepancy between API results and Klaviyo direct data.
    This helps us identify patterns and fix issues.
    """
    try:
        # Store the feedback
        feedback_store.append(report)
        
        # Log for immediate attention
        logger.warning(f"Data discrepancy reported for client {report.client_id}")
        logger.warning(f"Query: {report.query}")
        logger.warning(f"API returned: {report.api_response}")
        logger.warning(f"Klaviyo shows: {report.klaviyo_actual}")
        logger.warning(f"Details: {report.discrepancy_details}")
        
        # Analyze the discrepancy
        analysis = analyze_discrepancy(report)
        
        # Store in Firestore for persistent tracking
        db = get_db()
        db.collection('klaviyo_feedback').add({
            **report.dict(),
            'analysis': analysis,
            'resolved': False
        })
        
        return {
            "status": "received",
            "message": "Discrepancy report received and logged",
            "analysis": analysis,
            "report_id": len(feedback_store)
        }
        
    except Exception as e:
        logger.error(f"Failed to process discrepancy report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_data(request: ValidationRequest) -> Dict[str, Any]:
    """
    Validate API results against expected values from Klaviyo.
    Helps identify where discrepancies occur.
    """
    try:
        # Get our API's data
        await ensure_klaviyo_api_available()
        base = get_base_url()
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Use revenue/last7 endpoint with custom date range
            url = f"{base}/clients/{request.client_id}/revenue/last7"
            params = {
                "start": request.start_date,
                "end": request.end_date
            }
            
            logger.info(f"Validation request: GET {url} with params {params}")
            response = await client.get(url, params=params)
            
            if response.status_code != 200:
                logger.error(f"API call failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail=f"API call failed: {response.text}")
            
            api_data = response.json()
        
        # Compare with expected values
        discrepancies = []
        
        if request.expected_revenue is not None:
            diff = abs(api_data.get('total', 0) - request.expected_revenue)
            if diff > 0.01:  # Allow for small rounding differences
                discrepancies.append({
                    "field": "total_revenue",
                    "api_value": api_data.get('total', 0),
                    "expected_value": request.expected_revenue,
                    "difference": diff,
                    "percentage_diff": (diff / request.expected_revenue * 100) if request.expected_revenue > 0 else 0
                })
        
        if request.expected_orders is not None:
            diff = abs(api_data.get('total_orders', 0) - request.expected_orders)
            if diff > 0:
                discrepancies.append({
                    "field": "total_orders",
                    "api_value": api_data.get('total_orders', 0),
                    "expected_value": request.expected_orders,
                    "difference": diff
                })
        
        if request.expected_campaign_revenue is not None:
            diff = abs(api_data.get('campaign_total', 0) - request.expected_campaign_revenue)
            if diff > 0.01:
                discrepancies.append({
                    "field": "campaign_revenue",
                    "api_value": api_data.get('campaign_total', 0),
                    "expected_value": request.expected_campaign_revenue,
                    "difference": diff,
                    "percentage_diff": (diff / request.expected_campaign_revenue * 100) if request.expected_campaign_revenue > 0 else 0
                })
        
        if request.expected_flow_revenue is not None:
            diff = abs(api_data.get('flow_total', 0) - request.expected_flow_revenue)
            if diff > 0.01:
                discrepancies.append({
                    "field": "flow_revenue",
                    "api_value": api_data.get('flow_total', 0),
                    "expected_value": request.expected_flow_revenue,
                    "difference": diff,
                    "percentage_diff": (diff / request.expected_flow_revenue * 100) if request.expected_flow_revenue > 0 else 0
                })
        
        # Determine validation status
        is_valid = len(discrepancies) == 0
        
        # Get debug information
        debug_info = await get_debug_info(request.client_id, request.start_date, request.end_date)
        
        result = {
            "valid": is_valid,
            "api_response": api_data,
            "expected_values": {
                "revenue": request.expected_revenue,
                "orders": request.expected_orders,
                "campaign_revenue": request.expected_campaign_revenue,
                "flow_revenue": request.expected_flow_revenue
            },
            "discrepancies": discrepancies,
            "debug_info": debug_info,
            "notes": request.notes
        }
        
        # Log validation results
        if not is_valid:
            logger.warning(f"Validation failed for client {request.client_id}")
            logger.warning(f"Discrepancies: {discrepancies}")
            
            # Store validation failure for analysis
            db = get_db()
            db.collection('klaviyo_validations').add({
                **result,
                'timestamp': datetime.now().isoformat(),
                'resolved': False
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/{client_id}")
async def debug_client_data(
    client_id: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Get detailed debug information for troubleshooting discrepancies.
    Shows exactly what parameters are being used and potential issues.
    """
    try:
        debug_info = await get_debug_info(client_id, start_date, end_date)
        
        # Also fetch the actual data for comparison
        await ensure_klaviyo_api_available()
        base = get_base_url()
        
        # Try multiple endpoint variations to see which work
        results = {}
        endpoints = [
            ("/clients/{}/revenue/last7", {"start": start_date, "end": end_date}),
            ("/clients/{}/weekly/metrics", {"start": start_date, "end": end_date})
        ]
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for endpoint_template, params in endpoints:
                try:
                    endpoint = endpoint_template.format(client_id)
                    url = f"{base}{endpoint}"
                    
                    response = await client.get(url, params=params)
                    results[endpoint] = {
                        "status": response.status_code,
                        "data": response.json() if response.status_code == 200 else None,
                        "error": str(response.text) if response.status_code != 200 else None
                    }
                except Exception as e:
                    results[endpoint] = {"error": str(e)}
        
        return {
            "client_id": client_id,
            "date_range": {"start": start_date, "end": end_date},
            "debug_info": debug_info,
            "endpoint_results": results,
            "recommendations": generate_recommendations(debug_info, results)
        }
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discrepancy-patterns")
async def get_discrepancy_patterns() -> Dict[str, Any]:
    """
    Analyze patterns in reported discrepancies to identify systemic issues.
    """
    try:
        db = get_db()
        reports = []
        
        # Get all feedback reports
        for doc in db.collection('klaviyo_feedback').stream():
            reports.append(doc.to_dict())
        
        # Analyze patterns
        patterns = {
            "total_reports": len(reports),
            "by_client": {},
            "by_issue_type": {},
            "common_date_ranges": {},
            "average_discrepancy_percentage": 0
        }
        
        for report in reports:
            # Count by client
            client = report.get('client_id', 'unknown')
            patterns['by_client'][client] = patterns['by_client'].get(client, 0) + 1
            
            # Categorize issue types
            if 'api_response' in report and 'klaviyo_actual' in report:
                api_total = report['api_response'].get('total', 0)
                actual_total = report['klaviyo_actual'].get('total', 0)
                
                if api_total != actual_total:
                    diff_percent = abs(api_total - actual_total) / actual_total * 100 if actual_total > 0 else 0
                    
                    if diff_percent > 50:
                        issue_type = "major_discrepancy"
                    elif diff_percent > 10:
                        issue_type = "moderate_discrepancy"
                    else:
                        issue_type = "minor_discrepancy"
                    
                    patterns['by_issue_type'][issue_type] = patterns['by_issue_type'].get(issue_type, 0) + 1
        
        # Add recommendations based on patterns
        patterns['recommendations'] = generate_pattern_recommendations(patterns)
        
        return patterns
        
    except Exception as e:
        logger.error(f"Pattern analysis failed: {e}")
        return {
            "error": str(e),
            "patterns": {},
            "recommendations": ["Unable to analyze patterns due to error"]
        }


def analyze_discrepancy(report: DataDiscrepancyReport) -> Dict[str, Any]:
    """Analyze a discrepancy report to identify potential causes"""
    analysis = {
        "potential_causes": [],
        "severity": "unknown",
        "recommended_actions": []
    }
    
    api_total = report.api_response.get('total', 0)
    actual_total = report.klaviyo_actual.get('total', 0)
    
    # Calculate discrepancy percentage
    if actual_total > 0:
        diff_percent = abs(api_total - actual_total) / actual_total * 100
        
        if diff_percent > 50:
            analysis['severity'] = "high"
            analysis['potential_causes'].append("Major data sync issue or wrong metric ID")
        elif diff_percent > 10:
            analysis['severity'] = "medium"
            analysis['potential_causes'].append("Possible timezone or date range mismatch")
        else:
            analysis['severity'] = "low"
            analysis['potential_causes'].append("Minor rounding or timing difference")
    
    # Check for specific patterns
    if api_total == 0 and actual_total > 0:
        analysis['potential_causes'].append("API may be using wrong metric ID or API key")
        analysis['recommended_actions'].append("Verify metric_id in Firestore matches Klaviyo")
    
    if 'campaign_total' in report.api_response:
        if report.api_response['campaign_total'] == 0 and report.klaviyo_actual.get('campaign_revenue', 0) > 0:
            analysis['potential_causes'].append("Campaign tracking may be misconfigured")
            analysis['recommended_actions'].append("Check campaign metric configuration")
    
    # Date range issues
    if 'date_range' in report.dict():
        analysis['potential_causes'].append("Possible timezone conversion issue")
        analysis['recommended_actions'].append("Verify timezone settings match Klaviyo account")
    
    return analysis


async def get_debug_info(client_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Get detailed debug information for a client"""
    db = get_db()
    
    # Get client configuration
    client_doc = db.collection('clients').document(client_id).get()
    if not client_doc.exists:
        return {"error": "Client not found"}
    
    client_data = client_doc.to_dict()
    
    # Identify potential issues
    potential_issues = []
    
    if not client_data.get('klaviyo_api_key'):
        potential_issues.append("No Klaviyo API key configured")
    
    if not client_data.get('metric_id'):
        potential_issues.append("No metric_id configured")
    
    # Check date format
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        potential_issues.append("Invalid date format - should be YYYY-MM-DD")
    
    # Check if dates are in the future
    if datetime.strptime(end_date, "%Y-%m-%d") > datetime.now():
        potential_issues.append("End date is in the future")
    
    return {
        "client_config": {
            "has_api_key": bool(client_data.get('klaviyo_api_key')),
            "metric_id": client_data.get('metric_id'),
            "name": client_data.get('name'),
            "timezone": client_data.get('timezone', 'Not configured')
        },
        "api_request": {
            "client_id": client_id,
            "start_date": start_date,
            "end_date": end_date,
            "url_pattern": f"/clients/{client_id}/revenue/custom"
        },
        "klaviyo_direct_params": {
            "metric_id": client_data.get('metric_id'),
            "date_filter": f"greater-or-equal({start_date}),less-or-equal({end_date})",
            "timezone": "Account timezone should be used"
        },
        "potential_issues": potential_issues
    }


def generate_recommendations(debug_info: Dict[str, Any], results: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on debug information"""
    recommendations = []
    
    # Check for common issues
    if debug_info.get('potential_issues'):
        for issue in debug_info['potential_issues']:
            if "metric_id" in issue:
                recommendations.append("Verify the metric_id in Firestore matches the 'Placed Order' metric in Klaviyo")
            if "API key" in issue:
                recommendations.append("Ensure the Klaviyo API key has proper permissions for metrics data")
            if "timezone" in issue:
                recommendations.append("Check that timezone settings are consistent between our system and Klaviyo")
    
    # Check endpoint results
    for endpoint, result in results.items():
        if result.get('status') == 401:
            recommendations.append(f"Authentication failed for {endpoint} - verify API key permissions")
        elif result.get('status') == 404:
            recommendations.append(f"Endpoint {endpoint} not found - may need to update API integration")
        elif result.get('status') == 200 and result.get('data', {}).get('total', 0) == 0:
            recommendations.append(f"No data returned from {endpoint} - verify metric configuration")
    
    if not recommendations:
        recommendations.append("No obvious issues detected - compare exact parameters with Klaviyo UI")
    
    return recommendations


def generate_pattern_recommendations(patterns: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on discrepancy patterns"""
    recommendations = []
    
    if patterns['by_issue_type'].get('major_discrepancy', 0) > 0:
        recommendations.append("Multiple major discrepancies detected - review metric ID configuration")
    
    if len(patterns['by_client']) > 0:
        most_affected = max(patterns['by_client'].items(), key=lambda x: x[1])
        recommendations.append(f"Client {most_affected[0]} has the most discrepancies - prioritize fixing")
    
    return recommendations


@router.post("/tune-parameters")
async def tune_parameters(
    client_id: str = Body(...),
    adjustments: Dict[str, Any] = Body(...)
) -> Dict[str, Any]:
    """
    Apply tuning adjustments to improve accuracy.
    Adjustments can include timezone offsets, metric ID corrections, etc.
    """
    try:
        db = get_db()
        
        # Update client configuration with adjustments
        client_ref = db.collection('clients').document(client_id)
        client_ref.update({
            'klaviyo_tuning': adjustments,
            'tuning_updated_at': datetime.now().isoformat()
        })
        
        # Log the tuning
        db.collection('klaviyo_tuning_log').add({
            'client_id': client_id,
            'adjustments': adjustments,
            'timestamp': datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "message": f"Tuning parameters updated for client {client_id}",
            "adjustments": adjustments
        }
        
    except Exception as e:
        logger.error(f"Failed to apply tuning: {e}")
        raise HTTPException(status_code=500, detail=str(e))