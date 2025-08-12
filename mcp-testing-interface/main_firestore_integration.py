#!/usr/bin/env python3
"""
Integration script to add MCP routes to main_firestore.py
Run this on the production server to complete the backend integration
"""

import os
import sys
import shutil
from datetime import datetime

def find_main_file():
    """Find the main_firestore.py file"""
    possible_paths = [
        '/app/main_firestore.py',
        '/app/main.py',
        './main_firestore.py',
        './main.py'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def backup_file(filepath):
    """Create a backup of the main file"""
    backup_path = f"{filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def check_if_mcp_exists(content):
    """Check if MCP router is already registered"""
    if 'mcp_router' in content or '/api/mcp' in content:
        return True
    return False

def add_mcp_import(content):
    """Add MCP router import to imports section"""
    # Find the last import line
    lines = content.split('\n')
    last_import_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('from app.api') or line.startswith('import'):
            last_import_idx = i
    
    # Add MCP import after the last import
    import_line = "from app.api.mcp import router as mcp_router"
    
    # Check if import already exists
    if import_line not in content:
        lines.insert(last_import_idx + 1, import_line)
        print(f"✅ Added import: {import_line}")
        return '\n'.join(lines)
    
    return content

def add_mcp_router(content):
    """Add MCP router registration"""
    # Find where routers are registered
    lines = content.split('\n')
    
    # Look for existing router registrations
    router_line = 'app.include_router(mcp_router, prefix="/api/mcp", tags=["mcp"])'
    
    if router_line in content:
        print("ℹ️ MCP router already registered")
        return content
    
    # Find a good place to add the router (after other routers)
    for i, line in enumerate(lines):
        if 'app.include_router' in line and 'auth' in line.lower():
            # Add after auth router
            lines.insert(i + 1, router_line)
            print(f"✅ Added router registration: {router_line}")
            return '\n'.join(lines)
    
    # If no auth router found, look for any router
    for i, line in enumerate(lines):
        if 'app.include_router' in line:
            lines.insert(i + 1, router_line)
            print(f"✅ Added router registration: {router_line}")
            return '\n'.join(lines)
    
    print("⚠️ Could not find router registration section. Please add manually:")
    print(f"    {router_line}")
    return content

def integrate_mcp():
    """Main integration function"""
    print("🚀 Starting MCP Backend Integration")
    print("=" * 50)
    
    # Find main file
    main_file = find_main_file()
    if not main_file:
        print("❌ Could not find main_firestore.py or main.py")
        print("Please run this script from the app directory")
        return False
    
    print(f"📍 Found main file: {main_file}")
    
    # Read current content
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Check if MCP already exists
    if check_if_mcp_exists(content):
        print("ℹ️ MCP integration may already exist")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    # Create backup
    backup_path = backup_file(main_file)
    
    # Add import
    content = add_mcp_import(content)
    
    # Add router
    content = add_mcp_router(content)
    
    # Write updated content
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Integration complete!")
    print("\n📋 Next steps:")
    print("1. Verify the MCP files are in place:")
    print("   - /app/app/api/mcp.py")
    print("   - /app/app/services/mcp_service.py")
    print("   - /app/app/models/mcp_client.py")
    print("2. Run database migration:")
    print("   python migrate_mcp_only.py")
    print("3. Restart the application:")
    print("   gcloud run services update emailpilot-api --region=us-central1")
    
    return True

def verify_files():
    """Verify that MCP files exist"""
    required_files = [
        '/app/app/api/mcp.py',
        '/app/app/services/mcp_service.py',
        '/app/app/models/mcp_client.py',
        '/app/app/schemas/mcp_client.py',
        '/app/app/core/auth.py'
    ]
    
    print("\n📂 Checking for required MCP files...")
    all_present = True
    
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"  ✅ {filepath}")
        else:
            print(f"  ❌ {filepath} - MISSING")
            all_present = False
            
            # Try to find in staged packages
            filename = os.path.basename(filepath)
            staged = f"/app/staged_packages/mcp*/{filename}"
            import glob
            found = glob.glob(staged)
            if found:
                print(f"      Found in: {found[0]}")
                print(f"      Copy with: cp {found[0]} {filepath}")
    
    return all_present

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║         MCP Backend Integration Script                    ║
║                                                          ║
║  This script will add MCP API routes to your main app   ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check files first
    files_ok = verify_files()
    
    if not files_ok:
        print("\n⚠️ Some required files are missing!")
        print("Please copy them from the staged packages directory first.")
        response = input("\nContinue with integration anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Run integration
    if integrate_mcp():
        print("\n✅ SUCCESS! MCP backend integration is complete.")
        print("\n🎯 Test the integration:")
        print("   curl https://emailpilot.ai/api/mcp/models")
    else:
        print("\n❌ Integration failed or was cancelled.")