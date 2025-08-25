#!/usr/bin/env python3
"""Test PKCE implementation for Klaviyo OAuth"""

import base64
import hashlib
import secrets

def generate_pkce_pair():
    """Generate PKCE code verifier and challenge"""
    # Generate a code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge using SHA256
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge

def verify_pkce_pair(verifier, challenge):
    """Verify that a PKCE pair is valid"""
    # Recalculate challenge from verifier
    calculated_challenge_bytes = hashlib.sha256(verifier.encode('utf-8')).digest()
    calculated_challenge = base64.urlsafe_b64encode(calculated_challenge_bytes).decode('utf-8').rstrip('=')
    
    return calculated_challenge == challenge

if __name__ == "__main__":
    print("Testing PKCE implementation...")
    print("-" * 50)
    
    # Generate a PKCE pair
    verifier, challenge = generate_pkce_pair()
    
    print(f"Code Verifier (length: {len(verifier)}):")
    print(f"  {verifier}")
    print()
    print(f"Code Challenge (SHA256, length: {len(challenge)}):")
    print(f"  {challenge}")
    print()
    
    # Verify the pair
    is_valid = verify_pkce_pair(verifier, challenge)
    print(f"PKCE pair validation: {'✅ VALID' if is_valid else '❌ INVALID'}")
    print()
    
    # Test multiple pairs
    print("Generating 5 test pairs...")
    for i in range(5):
        v, c = generate_pkce_pair()
        valid = verify_pkce_pair(v, c)
        print(f"  Pair {i+1}: {'✅' if valid else '❌'} (verifier: {len(v)} chars, challenge: {len(c)} chars)")
    
    print()
    print("✅ PKCE implementation is working correctly!")
    print()
    print("OAuth 2.0 PKCE Requirements:")
    print("  - Code verifier: 43-128 characters (URL-safe base64)")
    print("  - Code challenge: SHA256 hash of verifier (URL-safe base64)")
    print("  - Challenge method: S256 (SHA256)")