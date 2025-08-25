#!/usr/bin/env python3
"""Test safe evaluation module"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow.tools.safe_eval import safe_eval, evaluate_condition, Conditions

def test_safe_eval():
    """Test safe evaluation of various expressions"""
    
    state = {
        "valid": True,
        "errors": ["error1", "error2"],
        "candidates": [
            {"type": "email", "revenue": 100},
            {"type": "sms", "revenue": 50}
        ],
        "total_revenue": 150,
        "approvals": {"approved": False}
    }
    
    tests = [
        # Basic comparisons
        ("state.get('valid', False)", True),
        ("not state.get('valid', False)", False),
        ("len(errors) > 0", True),
        ("len(errors) == 2", True),
        ("total_revenue > 100", True),
        
        # Complex conditions
        ("state.get('valid') and len(errors) > 0", True),
        ("state.get('valid') or state.get('approved')", True),
        
        # List operations
        ("sum([c.get('revenue', 0) for c in candidates])", 150),
        
        # String operations
        ("'email' in [c.get('type') for c in candidates]", True),
        
        # Unsafe operations (should fail)
        ("__import__('os')", None),  # Should raise ValueError
        ("eval('1+1')", None),  # Should raise ValueError
        ("exec('x = 1')", None),  # Should raise ValueError
    ]
    
    print("Testing Safe Evaluation:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for expression, expected in tests:
        try:
            result = safe_eval(expression, state)
            if expected is None:
                # Should have raised an error
                print(f"❌ FAIL: '{expression}' should have been blocked but returned: {result}")
                failed += 1
            elif result == expected:
                print(f"✅ PASS: '{expression}' → {result}")
                passed += 1
            else:
                print(f"❌ FAIL: '{expression}' → {result} (expected {expected})")
                failed += 1
        except ValueError as e:
            if expected is None:
                # Expected to fail
                print(f"✅ PASS: '{expression}' correctly blocked: {e}")
                passed += 1
            else:
                print(f"❌ FAIL: '{expression}' raised error: {e}")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: '{expression}' → {e}")
            failed += 1
    
    # Test Conditions helper
    print("\nTesting Conditions helpers:")
    print("-" * 40)
    
    condition_tests = [
        (Conditions.is_valid(state), True),
        (Conditions.has_errors(state), True),
        (Conditions.is_approved(state), False),
        (Conditions.above_threshold(state, "total_revenue", 100), True),
        (Conditions.above_threshold(state, "total_revenue", 200), False),
    ]
    
    for result, expected in condition_tests:
        if result == expected:
            print(f"✅ PASS: Condition returned {result}")
            passed += 1
        else:
            print(f"❌ FAIL: Condition returned {result} (expected {expected})")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} tests failed")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(test_safe_eval())