#!/usr/bin/env python3
"""Test the AI-enhanced MCP Natural Language query processor"""
import httpx
import json
from typing import Dict, Any

# Test queries covering all required functionality
TEST_QUERIES = [
    {
        "query": "Give me a total Revenue number only for campaigns in the last 30 days",
        "client_id": "christopher-bean-coffee",
        "expected": ["metrics.aggregate"]
    },
    {
        "query": "What are the open and click rates for our recent campaigns?",
        "client_id": "christopher-bean-coffee",
        "expected": ["campaigns.list", "campaigns.get_metrics"]
    },
    {
        "query": "Show me all active segments with their sizes and engagement rates",
        "client_id": "christopher-bean-coffee",
        "expected": ["segments.list", "segments.get_profiles"]
    },
    {
        "query": "Calculate total revenue for last 30 days including revenue per campaign",
        "client_id": "christopher-bean-coffee",
        "expected": ["metrics.aggregate", "campaigns.list"]
    },
    {
        "query": "What times of day have the best open rates?",
        "client_id": "christopher-bean-coffee",
        "expected": ["metrics.timeline", "campaigns.get_metrics"]
    },
    {
        "query": "Which subject lines performed best last month?",
        "client_id": "christopher-bean-coffee",
        "expected": ["campaigns.list", "campaigns.get"]
    }
]

def test_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single query against the AI endpoint"""
    url = "http://localhost:8000/api/mcp/nl/query"
    
    print(f"\n{'='*60}")
    print(f"Testing: {query_data['query']}")
    print(f"Client: {query_data['client_id']}")
    print("-" * 40)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json={
                "query": query_data["query"],
                "client_id": query_data["client_id"],
                "context": {}
            })
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                print(f"Strategies used: {len(result.get('strategies', []))}")
                
                # Show strategies
                for strategy in result.get('strategies', []):
                    print(f"  - {strategy['tool_name']}: {strategy['description']}")
                
                # Check if revenue data present for revenue queries
                if "revenue" in query_data["query"].lower():
                    if result.get('total_revenue') is not None:
                        print(f"  💰 Total Revenue: ${result['total_revenue']:,.2f}")
                    if result.get('aggregated_results', {}).get('revenue_data'):
                        rev_data = result['aggregated_results']['revenue_data']
                        print(f"  📊 Revenue Data Found: {len(rev_data)} items")
                
                # Show interpretation
                if result.get('interpretation'):
                    print(f"\nInterpretation:\n{result['interpretation'][:200]}...")
                    
                return result
            else:
                print(f"❌ Failed: HTTP {response.status_code}")
                print(f"Error: {response.text}")
                return {"error": response.text}
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"error": str(e)}

def main():
    print("Testing AI-Enhanced MCP Natural Language Query Processor")
    print("=" * 60)
    
    results = []
    for query_data in TEST_QUERIES:
        result = test_query(query_data)
        results.append({
            "query": query_data["query"],
            "success": "error" not in result,
            "has_strategies": len(result.get("strategies", [])) > 0,
            "has_results": bool(result.get("aggregated_results"))
        })
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    print(f"✅ Successful queries: {success_count}/{len(results)}")
    print(f"📊 Queries with strategies: {sum(1 for r in results if r['has_strategies'])}/{len(results)}")
    print(f"📈 Queries with results: {sum(1 for r in results if r['has_results'])}/{len(results)}")
    
    print("\nDetails:")
    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        print(f"{i}. {status} {r['query'][:50]}...")
        if r["success"]:
            print(f"   Strategies: {'Yes' if r['has_strategies'] else 'No'}")
            print(f"   Results: {'Yes' if r['has_results'] else 'No'}")

if __name__ == "__main__":
    main()
