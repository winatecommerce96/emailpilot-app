#!/usr/bin/env python3
"""
Direct test of backfill service
"""

import asyncio
from app.services.klaviyo_data_service import KlaviyoDataService
from app.deps.firestore import get_db

async def test_direct_backfill():
    """
    Test backfill directly without API
    """
    print("Testing direct backfill for Rogue Creamery...")
    
    # Initialize service
    db = get_db()
    service = KlaviyoDataService(db)
    
    # Run backfill for Rogue Creamery (testing with just 7 days first)
    result = await service.backfill_client_data(
        client_id="rogue-creamery",
        years=0.02,  # About 7 days for quick test
        include_orders=True
    )
    
    print(f"\nBackfill Results:")
    print(f"- Days processed: {result['days']}")
    print(f"- Campaigns synced: {result['campaigns']}")
    print(f"- Flows synced: {result['flows']}")
    print(f"- Orders synced: {result['orders']}")
    
    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(test_direct_backfill())
        if result['days'] > 0:
            print("\n✓ Backfill test successful!")
            print("\nNow you can run the full year backfill via the web interface:")
            print("http://localhost:8000/static/backfill_manager.html")
        else:
            print("\n✗ No data was backfilled. Check API key configuration.")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()