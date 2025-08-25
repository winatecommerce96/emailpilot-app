#!/usr/bin/env python3
"""
Quick test to verify agents are affecting copy generation
"""

import requests
import json
import time

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def test_agent_impact():
    """Quick test to verify agents work"""
    print(f"{BLUE}Quick Agent Impact Test{RESET}\n")
    
    # Simple brief
    brief = "Create a summer sale email. 30% off everything. July 1-7."
    
    # Test 1: Creative Copywriter
    print(f"{YELLOW}Test 1: Creative Copywriter{RESET}")
    response1 = requests.post("http://localhost:8002/api/generate-copy", 
        json={
            "brief_content": brief,
            "selected_agents": ["creative_copywriter"],
            "selected_model": "gpt-3.5-turbo"
        },
        timeout=30
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        if data1.get("variants"):
            variant1 = data1["variants"][0]
            print(f"Subject: {variant1.get('subject_line_a', 'N/A')}")
            body1 = variant1.get('full_email_body', '')[:200]
            print(f"Body preview: {body1}...")
            
            # Check for creative language
            creative_words = ['imagine', 'discover', 'transform', 'adventure', 'dream', 'journey']
            has_creative = any(word in body1.lower() for word in creative_words)
            if has_creative:
                print(f"{GREEN}✓ Creative language detected!{RESET}")
            else:
                print(f"{YELLOW}⚠ Creative language not strongly present{RESET}")
    else:
        print(f"{RED}✗ Failed: {response1.status_code}{RESET}")
        return False
    
    print()
    
    # Test 2: Compliance Officer
    print(f"{YELLOW}Test 2: Compliance Officer{RESET}")
    response2 = requests.post("http://localhost:8002/api/generate-copy",
        json={
            "brief_content": brief,
            "selected_agents": ["compliance_officer"],
            "selected_model": "gpt-3.5-turbo"
        },
        timeout=30
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        if data2.get("variants"):
            variant2 = data2["variants"][0]
            print(f"Subject: {variant2.get('subject_line_a', 'N/A')}")
            body2 = variant2.get('full_email_body', '')[:200]
            print(f"Body preview: {body2}...")
            
            # Check for compliance language
            compliance_words = ['terms', 'conditions', 'disclaimer', 'subject to', 'valid', 'restrictions']
            has_compliance = any(word in body2.lower() for word in compliance_words)
            if has_compliance:
                print(f"{GREEN}✓ Compliance language detected!{RESET}")
            else:
                print(f"{YELLOW}⚠ Compliance language not strongly present{RESET}")
    else:
        print(f"{RED}✗ Failed: {response2.status_code}{RESET}")
        return False
    
    print()
    
    # Compare the two
    print(f"{BLUE}Comparison:{RESET}")
    if variant1 and variant2:
        # Check if subjects are different
        if variant1.get('subject_line_a') != variant2.get('subject_line_a'):
            print(f"{GREEN}✓ Subject lines are different{RESET}")
        else:
            print(f"{RED}✗ Subject lines are identical{RESET}")
        
        # Check if bodies are different
        body1_full = variant1.get('full_email_body', '')
        body2_full = variant2.get('full_email_body', '')
        
        if body1_full != body2_full:
            # Calculate similarity
            words1 = set(body1_full.lower().split())
            words2 = set(body2_full.lower().split())
            common = len(words1 & words2)
            total = len(words1 | words2)
            similarity = (common / total * 100) if total > 0 else 0
            
            print(f"{GREEN}✓ Bodies are different ({100-similarity:.1f}% different){RESET}")
            
            if similarity < 70:  # More than 30% different
                print(f"{GREEN}✓✓ AGENTS ARE WORKING! Significant differences detected.{RESET}")
                return True
            else:
                print(f"{YELLOW}⚠ Bodies are somewhat different but could be more distinct{RESET}")
                return True
        else:
            print(f"{RED}✗ Bodies are identical - agents not working{RESET}")
            return False
    
    return False

if __name__ == "__main__":
    try:
        # Check service health first
        health = requests.get("http://localhost:8002/health", timeout=5)
        if health.status_code == 200:
            health_data = health.json()
            print(f"Service status: {health_data.get('ok', False)}")
            print(f"Providers: {health_data.get('providers', {})}\n")
        
        # Run test
        success = test_agent_impact()
        
        if success:
            print(f"\n{GREEN}SUCCESS! Agents are impacting copy generation.{RESET}")
        else:
            print(f"\n{RED}FAILURE: Agents may not be working properly.{RESET}")
            
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error: {e}{RESET}")
        print("Make sure the copywriting service is running on port 8002")