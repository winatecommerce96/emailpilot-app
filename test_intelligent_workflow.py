#!/usr/bin/env python3
"""
Test script to verify the calendar workflow is using IntelligentQueryService
for natural language data gathering from Klaviyo MCP Enhanced.
"""

import asyncio
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "emailpilot_graph"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_intelligent_workflow():
    """Test the calendar workflow with intelligent query service"""
    
    try:
        # Import the workflow
        from emailpilot_graph.calendar_workflow import build_calendar_workflow
        
        logger.info("Building workflow graph...")
        workflow = build_calendar_workflow()
        
        # Test parameters
        test_input = {
            "client_id": "01J8XM973VJD0X0G2P37H3R3WV",  # Milagro Mushrooms
            "client_name": "Milagro Mushrooms",
            "selected_month": "2025-02",
            "campaign_count": 5,
            "client_sales_goal": 50000.0,
            "optimization_goal": "engagement",
            "llm_type": "gemini",
            "additional_context": "Valentine's Day promotions and wellness campaigns",
            "use_real_data": True,  # This will trigger IntelligentQueryService usage
            "status": "started",
            "errors": [],
            "execution_time": None
        }
        
        logger.info("Executing workflow with intelligent data gathering...")
        logger.info(f"Client: {test_input['client_name']}")
        logger.info(f"Month: {test_input['selected_month']}")
        logger.info(f"Use Real Data: {test_input['use_real_data']}")
        
        # Execute the workflow
        result = await workflow.ainvoke(test_input)
        
        # Check results
        logger.info("\n=== Workflow Results ===")
        
        # Check brand data
        if result.get("brand_data"):
            brand_data = result["brand_data"]
            logger.info(f"✅ Brand data retrieved: {len(brand_data.get('affinity_segments', []))} segments")
            if brand_data.get('affinity_segments'):
                logger.info(f"   Sample segment: {brand_data['affinity_segments'][0].get('name', 'Unknown')}")
        else:
            logger.warning("❌ No brand data retrieved")
        
        # Check historical insights
        if result.get("historical_insights"):
            insights = result["historical_insights"]
            logger.info(f"✅ Historical insights retrieved (source: {insights.get('data_source', 'unknown')})")
            if insights.get("summary"):
                summary = insights["summary"]
                logger.info(f"   Campaigns analyzed: {summary.get('campaign_count', 0)}")
                logger.info(f"   Avg open rate: {summary.get('avg_open_rate', 0):.2%}")
                logger.info(f"   Avg click rate: {summary.get('avg_click_rate', 0):.2%}")
                logger.info(f"   Total revenue: ${summary.get('total_revenue', 0):,.2f}")
            if insights.get("timing_insights"):
                timing = insights["timing_insights"]
                logger.info(f"   Best send time: {timing.get('best_send_hour', 'unknown')}")
                logger.info(f"   Best days: {', '.join(timing.get('best_days', []))}")
        else:
            logger.warning("❌ No historical insights retrieved")
        
        # Check final calendar
        if result.get("final_calendar"):
            calendar = result["final_calendar"]
            logger.info(f"✅ Calendar generated: {len(calendar.get('campaigns', []))} campaigns")
            if calendar.get('campaigns'):
                logger.info("\n   Campaign Schedule:")
                for i, campaign in enumerate(calendar['campaigns'][:3], 1):  # Show first 3
                    logger.info(f"   {i}. {campaign.get('date', 'No date')} - {campaign.get('name', 'Unnamed')}")
                    logger.info(f"      Segment: {campaign.get('segment', 'Unknown')}")
                    logger.info(f"      Theme: {campaign.get('theme', 'No theme')}")
        else:
            logger.warning("❌ No calendar generated")
        
        # Check if intelligent query was used
        if insights and insights.get('data_source') == 'klaviyo_mcp_intelligent':
            logger.info("\n✅ SUCCESS: Workflow used IntelligentQueryService for data gathering!")
        else:
            logger.warning("\n⚠️ WARNING: Workflow may not have used IntelligentQueryService")
        
        # Check for errors
        if result.get("errors"):
            logger.error(f"\nErrors encountered: {result['errors']}")
        
        logger.info(f"\nWorkflow status: {result.get('status', 'unknown')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_intelligent_query_service():
    """Directly test the IntelligentQueryService"""
    
    try:
        from app.services.intelligent_query_service import IntelligentQueryService, QueryMode
        
        logger.info("\n=== Testing IntelligentQueryService Directly ===")
        
        # Initialize service
        query_service = IntelligentQueryService()
        
        # Test queries
        test_queries = [
            "Show campaign performance for last 30 days",
            "List all active segments with engagement rates",
            "Get optimal send times based on open rates"
        ]
        
        client_id = "01J8XM973VJD0X0G2P37H3R3WV"  # Milagro Mushrooms
        
        for query in test_queries:
            logger.info(f"\nTesting query: '{query}'")
            
            result = await query_service.query(
                natural_query=query,
                client_id=client_id,
                mode=QueryMode.AUTO
            )
            
            if result.get("success"):
                logger.info(f"✅ Query successful")
                logger.info(f"   Mode used: {result.get('mode', 'unknown')}")
                logger.info(f"   Results available: {bool(result.get('results'))}")
            else:
                logger.warning(f"❌ Query failed: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        logger.error(f"Direct test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test runner"""
    
    logger.info("=" * 60)
    logger.info("Testing Calendar Workflow with IntelligentQueryService")
    logger.info("=" * 60)
    
    # Test the intelligent query service directly first
    await test_intelligent_query_service()
    
    # Then test the workflow
    await test_intelligent_workflow()
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())