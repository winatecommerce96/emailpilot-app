#!/usr/bin/env python3
"""
Test script for Rogue Creamery backfill
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_rogue_creamery_backfill():
    """
    Test the backfill process for Rogue Creamery
    """
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("KLAVIYO BACKFILL TEST - ROGUE CREAMERY")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Start backfill for Rogue Creamery
        print("\n1. Starting backfill for Rogue Creamery (1 year)...")
        
        response = await client.post(
            f"{base_url}/api/backfill/start/rogue-creamery",
            params={"years": 1, "include_orders": True}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Backfill started successfully")
            print(f"   - Client: {data.get('client_name')}")
            print(f"   - Client ID: {data.get('client_id')}")
            print(f"   - Years: {data.get('years')}")
            print(f"   - Include Orders: {data.get('include_orders')}")
            client_id = data.get('client_id')
        else:
            print(f"   ✗ Failed to start backfill: {response.text}")
            return
        
        # Step 2: Monitor progress
        print("\n2. Monitoring backfill progress...")
        print("   (Press Ctrl+C to stop monitoring)")
        
        completed = False
        last_progress = 0
        
        while not completed:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            response = await client.get(f"{base_url}/api/backfill/status/{client_id}")
            
            if response.status_code == 200:
                status = response.json()
                current_progress = status.get('progress', 0)
                
                # Only print if progress changed
                if current_progress != last_progress:
                    print(f"\n   Progress: {current_progress:.1f}%")
                    print(f"   - Status: {status.get('status')}")
                    print(f"   - Days Processed: {status.get('days_processed', 0)}")
                    print(f"   - Campaigns: {status.get('campaigns_synced', 0)}")
                    print(f"   - Flows: {status.get('flows_synced', 0)}")
                    print(f"   - Orders: {status.get('orders_synced', 0)}")
                    
                    if status.get('last_processed_date'):
                        print(f"   - Last Date: {status.get('last_processed_date')[:10]}")
                    
                    last_progress = current_progress
                
                if status.get('status') == 'completed':
                    completed = True
                    print("\n   ✓ Backfill completed successfully!")
                elif status.get('status') == 'failed':
                    print(f"\n   ✗ Backfill failed: {status.get('error')}")
                    return
        
        # Step 3: Get summary of backfilled data
        print("\n3. Fetching backfilled data summary...")
        
        response = await client.get(f"{base_url}/api/backfill/data/{client_id}/summary")
        
        if response.status_code == 200:
            summary = response.json()
            data_summary = summary.get('summary', {})
            
            print(f"   ✓ Data Summary:")
            print(f"   - Total Campaigns: {data_summary.get('campaigns', 0)}")
            print(f"   - Total Flows: {data_summary.get('flows', 0)}")
            print(f"   - Total Orders: {data_summary.get('orders', 0)}")
            print(f"   - Total Revenue: ${data_summary.get('total_revenue', 0):,.2f}")
            print(f"   - Average Order Value: ${data_summary.get('average_order_value', 0):,.2f}")
        
        # Step 4: Get sample of order data
        print("\n4. Fetching sample order data...")
        
        response = await client.get(
            f"{base_url}/api/backfill/data/{client_id}/orders",
            params={"limit": 5}
        )
        
        if response.status_code == 200:
            orders_data = response.json()
            orders = orders_data.get('orders', [])
            
            print(f"   ✓ Sample Orders (showing {len(orders)} of {orders_data.get('total_orders', 0)}):")
            
            for i, order in enumerate(orders[:5], 1):
                print(f"\n   Order {i}:")
                print(f"   - Date: {order.get('datetime', 'N/A')[:10]}")
                print(f"   - Order ID: {order.get('order_id', 'N/A')}")
                print(f"   - Value: ${order.get('value', 0):.2f}")
                print(f"   - Items: {order.get('item_count', 0)}")
                print(f"   - Source: {order.get('source', 'unknown')}")
    
    print("\n" + "=" * 60)
    print("BACKFILL TEST COMPLETED")
    print("=" * 60)
    print("\n✓ Access the management interface at:")
    print("  http://localhost:8000/static/backfill_manager.html")

if __name__ == "__main__":
    try:
        asyncio.run(test_rogue_creamery_backfill())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")