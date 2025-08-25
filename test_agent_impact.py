#!/usr/bin/env python3
"""
Test script to verify that different agents produce different copy styles
Run with: python3 test_agent_impact.py
"""

import asyncio
import httpx
import json
from typing import Dict, List
import re
from datetime import datetime

# Test configuration
COPYWRITING_URL = "http://localhost:8002"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_test(name):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Testing: {name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_info(msg):
    print(f"{YELLOW}ℹ️  {msg}{RESET}")

def print_variant(title, variant):
    print(f"\n{CYAN}--- {title} ---{RESET}")
    print(f"Subject A: {variant.get('subject_line_a', 'N/A')}")
    print(f"Subject B: {variant.get('subject_line_b', 'N/A')}")
    print(f"Preview: {variant.get('preview_text', 'N/A')[:50]}...")
    print(f"Hero H1: {variant.get('hero_h1', 'N/A')}")
    print(f"CTA: {variant.get('cta_copy', 'N/A')}")
    if variant.get('full_email_body'):
        body_preview = variant['full_email_body'][:150].replace('\n', ' ')
        print(f"Body: {body_preview}...")

def analyze_differences(variant1: Dict, variant2: Dict, agent1: str, agent2: str) -> Dict:
    """Analyze the differences between two variants to see if agents had impact"""
    differences = {
        "total_fields": 0,
        "different_fields": 0,
        "similarity_score": 0,
        "key_differences": []
    }
    
    # Fields to compare
    fields = ['subject_line_a', 'subject_line_b', 'preview_text', 'hero_h1', 'cta_copy', 'full_email_body']
    
    for field in fields:
        val1 = str(variant1.get(field, ''))
        val2 = str(variant2.get(field, ''))
        
        differences["total_fields"] += 1
        
        if val1 != val2:
            differences["different_fields"] += 1
            
            # Analyze the type of difference
            if field == 'full_email_body':
                # Check for agent-specific patterns
                if agent1 == "compliance_officer" or agent2 == "compliance_officer":
                    if "disclaimer" in val1.lower() or "terms" in val1.lower():
                        differences["key_differences"].append("Compliance language detected")
                    elif "disclaimer" in val2.lower() or "terms" in val2.lower():
                        differences["key_differences"].append("Compliance language detected")
                
                if agent1 == "data_driven_marketer" or agent2 == "data_driven_marketer":
                    # Check for numbers/statistics
                    if re.search(r'\d+%|\d+ out of \d+|statistics|study|research', val1) or \
                       re.search(r'\d+%|\d+ out of \d+|statistics|study|research', val2):
                        differences["key_differences"].append("Data/metrics included")
                
                if agent1 == "creative_copywriter" or agent2 == "creative_copywriter":
                    # Check for creative language
                    creative_markers = ['imagine', 'picture', 'story', 'journey', 'adventure', 'dream']
                    if any(marker in val1.lower() or marker in val2.lower() for marker in creative_markers):
                        differences["key_differences"].append("Creative storytelling detected")
            
            # Calculate rough similarity
            common_words = set(val1.lower().split()) & set(val2.lower().split())
            all_words = set(val1.lower().split()) | set(val2.lower().split())
            if all_words:
                field_similarity = len(common_words) / len(all_words)
                differences["similarity_score"] += field_similarity
    
    if differences["total_fields"] > 0:
        differences["similarity_score"] = differences["similarity_score"] / differences["total_fields"]
        differences["difference_percentage"] = (differences["different_fields"] / differences["total_fields"]) * 100
    
    return differences

async def test_single_agent(agent_id: str, brief: str, client_id: str = None) -> Dict:
    """Test copy generation with a single agent"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        request_data = {
            "brief_content": brief,  # Fixed field name
            "campaign_type": "email",
            "selected_agents": [agent_id],
            "selected_model": "gpt-3.5-turbo"
        }
        
        if client_id:
            request_data["client_id"] = client_id
        
        response = await client.post(
            f"{COPYWRITING_URL}/api/generate-copy",
            json=request_data
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("variants") and len(data["variants"]) > 0:
                return data["variants"][0]
        
        return None

async def test_agent_combinations():
    """Test different agent combinations to verify they produce different output"""
    print_test("Agent Impact Verification")
    
    # Test brief
    brief = """
    Create an email campaign for our Summer Sale event.
    - 30% off all products
    - Limited time: July 1-7
    - Target audience: existing customers
    - Goal: Drive sales and clear summer inventory
    """
    
    # Test cases: Different agents that should produce very different styles
    test_cases = [
        {
            "agent": "email_marketing_expert",
            "expected_style": "Engaging, psychological triggers, FOMO"
        },
        {
            "agent": "compliance_officer",
            "expected_style": "Factual, includes disclaimers, conservative"
        },
        {
            "agent": "creative_copywriter",
            "expected_style": "Creative, storytelling, vivid imagery"
        },
        {
            "agent": "data_driven_marketer",
            "expected_style": "Statistics, metrics, proof points"
        }
    ]
    
    results = {}
    
    # Generate copy with each agent
    for test_case in test_cases:
        agent_id = test_case["agent"]
        print_info(f"\nGenerating copy with {agent_id}...")
        
        try:
            variant = await test_single_agent(agent_id, brief)
            if variant:
                results[agent_id] = variant
                print_success(f"Generated variant with {agent_id}")
                print_variant(f"{agent_id} Output", variant)
            else:
                print_error(f"Failed to generate variant with {agent_id}")
        except Exception as e:
            print_error(f"Error with {agent_id}: {e}")
    
    # Compare results
    print_test("Analyzing Agent Impact")
    
    if len(results) < 2:
        print_error("Not enough variants generated to compare")
        return False
    
    # Compare each pair of agents
    comparisons = []
    agent_ids = list(results.keys())
    
    for i in range(len(agent_ids)):
        for j in range(i + 1, len(agent_ids)):
            agent1, agent2 = agent_ids[i], agent_ids[j]
            variant1, variant2 = results[agent1], results[agent2]
            
            diff_analysis = analyze_differences(variant1, variant2, agent1, agent2)
            comparisons.append({
                "agents": f"{agent1} vs {agent2}",
                "analysis": diff_analysis
            })
            
            print(f"\n{CYAN}Comparison: {agent1} vs {agent2}{RESET}")
            print(f"Different fields: {diff_analysis['different_fields']}/{diff_analysis['total_fields']}")
            print(f"Difference percentage: {diff_analysis.get('difference_percentage', 0):.1f}%")
            print(f"Similarity score: {(1 - diff_analysis['similarity_score']) * 100:.1f}% different")
            
            if diff_analysis['key_differences']:
                print(f"Key differences detected: {', '.join(diff_analysis['key_differences'])}")
    
    # Determine if agents are having impact
    print_test("Final Verdict")
    
    total_comparisons = len(comparisons)
    significant_differences = sum(1 for c in comparisons if c['analysis']['difference_percentage'] > 30)
    
    if significant_differences >= total_comparisons * 0.5:
        print_success(f"AGENTS ARE WORKING! {significant_differences}/{total_comparisons} comparisons show significant differences")
        
        # Check for specific agent behaviors
        if "compliance_officer" in results:
            body = results["compliance_officer"].get("full_email_body", "").lower()
            if "terms" in body or "disclaimer" in body or "subject to" in body:
                print_success("Compliance officer is adding legal language as expected")
        
        if "data_driven_marketer" in results:
            body = results["data_driven_marketer"].get("full_email_body", "")
            if re.search(r'\d+%|\d+ customers|\d+ days', body):
                print_success("Data-driven marketer is including metrics as expected")
        
        if "creative_copywriter" in results:
            body = results["creative_copywriter"].get("full_email_body", "").lower()
            creative_words = ['imagine', 'discover', 'transform', 'journey', 'unlock']
            if any(word in body for word in creative_words):
                print_success("Creative copywriter is using creative language as expected")
        
        return True
    else:
        print_error(f"AGENTS MAY NOT BE WORKING PROPERLY. Only {significant_differences}/{total_comparisons} show significant differences")
        print_info("Variants are too similar - agents may not be affecting output")
        return False

async def test_multiple_agents():
    """Test combining multiple agents"""
    print_test("Multiple Agent Combination Test")
    
    brief = "Create a promotional email for our new product launch"
    
    # Test with multiple agents
    print_info("Testing with multiple agents: creative_copywriter + data_driven_marketer")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{COPYWRITING_URL}/api/generate-copy",
            json={
                "brief_content": brief,  # Fixed field name
                "campaign_type": "email",
                "selected_agents": ["creative_copywriter", "data_driven_marketer"],
                "selected_model": "gpt-3.5-turbo"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("variants") and len(data["variants"]) > 0:
                variant = data["variants"][0]
                print_variant("Multi-Agent Output", variant)
                
                # Check if both agent styles are present
                body = variant.get("full_email_body", "").lower()
                has_creative = any(word in body for word in ['imagine', 'discover', 'transform'])
                has_data = bool(re.search(r'\d+%|\d+ customers|\d+ days', body))
                
                if has_creative and has_data:
                    print_success("Both agent styles detected in combined output!")
                    return True
                elif has_creative:
                    print_info("Only creative style detected")
                elif has_data:
                    print_info("Only data style detected")
                else:
                    print_error("Neither agent style strongly detected")
    
    return False

async def main():
    """Run all agent impact tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Agent Impact Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if service is running
    try:
        async with httpx.AsyncClient() as client:
            health = await client.get(f"{COPYWRITING_URL}/health")
            if health.status_code == 200:
                health_data = health.json()
                if not health_data.get("ok"):
                    print_info(f"Service running but providers are down: {health_data.get('providers')}")
                    print_info("Continuing with fallback generation...")
                else:
                    print_success("Copywriting service is healthy")
            else:
                print_error(f"Copywriting service returned status {health.status_code}")
                return
    except Exception as e:
        print_error(f"Copywriting service not running at {COPYWRITING_URL}: {e}")
        print_info("Start it with: cd copywriting && uvicorn main:app --port 8002 --reload")
        return
    
    # Run tests
    results = {
        "agent_combinations": await test_agent_combinations(),
        "multiple_agents": await test_multiple_agents()
    }
    
    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed in results.items():
        status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
        print(f"{test_name}: {status}")
    
    print(f"\n{BLUE}Total: {passed}/{total} passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 SUCCESS! Agents are now impacting copy generation!{RESET}")
        print(f"{GREEN}Different agents produce distinctly different copy styles.{RESET}")
    else:
        print(f"\n{YELLOW}⚠️  Some tests failed. Agents may need further tuning.{RESET}")

if __name__ == "__main__":
    asyncio.run(main())