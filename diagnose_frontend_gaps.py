#!/usr/bin/env python3
"""
Frontend Gap Analysis Tool
Identifies backend endpoints that don't have corresponding frontend UI
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

def find_api_endpoints(api_dir: str = "app/api") -> Dict[str, List[Tuple[str, str]]]:
    """Find all API endpoints defined in Python files"""
    endpoints = {}
    
    for file_path in Path(api_dir).glob("**/*.py"):
        if "__pycache__" in str(file_path):
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Find router endpoints
        router_pattern = r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)'
        matches = re.findall(router_pattern, content)
        
        if matches:
            rel_path = str(file_path).replace("app/api/", "")
            endpoints[rel_path] = [(method, path) for method, path in matches]
    
    return endpoints

def find_mounted_routers(main_file: str = "main_firestore.py") -> Set[str]:
    """Find which routers are actually mounted in the main app"""
    mounted = set()
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Find import statements for routers
    import_pattern = r'from app\.api\.(\w+) import .*router'
    imports = re.findall(import_pattern, content)
    
    # Find include_router statements
    include_pattern = r'app\.include_router\((\w+)'
    includes = re.findall(include_pattern, content)
    
    for imp in imports:
        mounted.add(f"{imp}.py")
    
    return mounted

def find_frontend_references(frontend_dir: str = "frontend/public") -> Set[str]:
    """Find API endpoints referenced in frontend code"""
    referenced = set()
    
    for file_path in Path(frontend_dir).glob("**/*.js"):
        if "node_modules" in str(file_path) or ".min.js" in str(file_path):
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find fetch calls
        fetch_pattern = r'fetch\(["\']([^"\']+)'
        matches = re.findall(fetch_pattern, content)
        referenced.update(matches)
        
        # Find axios/http calls
        api_pattern = r'(?:get|post|put|delete|patch)\(["\']([^"\']+)'
        matches = re.findall(api_pattern, content)
        referenced.update(matches)
    
    return referenced

def find_admin_tabs(app_js: str = "frontend/public/app.js") -> List[str]:
    """Find admin tabs defined in the frontend"""
    tabs = []
    
    with open(app_js, 'r') as f:
        content = f.read()
    
    # Find activeTab checks
    tab_pattern = r"activeTab === ['\"]([^'\"]+)['\"]"
    matches = re.findall(tab_pattern, content)
    tabs = list(set(matches))
    
    return sorted(tabs)

def analyze_gaps():
    """Main analysis function"""
    print("=" * 80)
    print("EmailPilot Frontend Gap Analysis")
    print("=" * 80)
    print()
    
    # Find all backend endpoints
    endpoints = find_api_endpoints()
    print(f"✅ Found {sum(len(e) for e in endpoints.values())} total backend endpoints in {len(endpoints)} files")
    
    # Find mounted routers
    mounted = find_mounted_routers()
    print(f"✅ Found {len(mounted)} mounted routers in main_firestore.py")
    
    # Find frontend references
    frontend_refs = find_frontend_references()
    print(f"✅ Found {len(frontend_refs)} API calls in frontend code")
    
    # Find admin tabs
    admin_tabs = find_admin_tabs()
    print(f"✅ Found {len(admin_tabs)} admin tabs in frontend")
    
    print("\n" + "=" * 80)
    print("ADMIN TABS IN FRONTEND:")
    print("=" * 80)
    for tab in admin_tabs:
        print(f"  • {tab}")
    
    print("\n" + "=" * 80)
    print("BACKEND ENDPOINTS WITHOUT FRONTEND UI:")
    print("=" * 80)
    
    # Group endpoints by feature area
    feature_groups = {
        'MCP': [],
        'AI & Agents': [],
        'Calendar': [],
        'Reports': [],
        'Admin': [],
        'Auth & OAuth': [],
        'Klaviyo': [],
        'Other': []
    }
    
    for file, file_endpoints in endpoints.items():
        # Skip if not mounted
        if file not in mounted and not any(m in file for m in mounted):
            continue
            
        for method, path in file_endpoints:
            # Check if endpoint is referenced in frontend
            full_path = f"/api{path}" if not path.startswith("/") else path
            
            # Skip if already referenced
            if any(ref in full_path or full_path in ref for ref in frontend_refs):
                continue
            
            # Categorize endpoint
            endpoint_info = f"{method.upper():6} {full_path} ({file})"
            
            if 'mcp' in file.lower() or 'mcp' in path.lower():
                feature_groups['MCP'].append(endpoint_info)
            elif 'agent' in file.lower() or 'ai' in file.lower():
                feature_groups['AI & Agents'].append(endpoint_info)
            elif 'calendar' in file.lower():
                feature_groups['Calendar'].append(endpoint_info)
            elif 'report' in file.lower():
                feature_groups['Reports'].append(endpoint_info)
            elif 'admin' in file.lower():
                feature_groups['Admin'].append(endpoint_info)
            elif 'auth' in file.lower() or 'oauth' in file.lower():
                feature_groups['Auth & OAuth'].append(endpoint_info)
            elif 'klaviyo' in file.lower():
                feature_groups['Klaviyo'].append(endpoint_info)
            else:
                feature_groups['Other'].append(endpoint_info)
    
    # Print grouped results
    for group, items in feature_groups.items():
        if items:
            print(f"\n🔸 {group} ({len(items)} endpoints):")
            for item in sorted(items)[:10]:  # Show first 10
                print(f"    {item}")
            if len(items) > 10:
                print(f"    ... and {len(items) - 10} more")
    
    print("\n" + "=" * 80)
    print("MISSING ADMIN SECTIONS:")
    print("=" * 80)
    
    # Suggest missing admin sections based on backend
    suggested_sections = {
        'agents': 'AI Agent Management',
        'asana': 'Asana Integration',
        'langchain': 'LangChain Admin',
        'tools': 'External Tools Management',
        'firebase': 'Firebase Calendar',
        'notifications': 'Admin Notifications',
        'discovery': 'Klaviyo Discovery',
        'performance': 'Performance Metrics',
        'reports': 'Advanced Reports'
    }
    
    for key, description in suggested_sections.items():
        if key not in admin_tabs:
            # Check if backend exists
            has_backend = any(key in str(f) for f in endpoints.keys())
            if has_backend:
                print(f"  ❌ {description} (backend exists, no frontend tab)")
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("=" * 80)
    print("""
1. Create a unified Admin Dashboard with dynamic menu generation
2. Add a 'Developer Tools' section showing all available endpoints
3. Implement auto-discovery of backend features
4. Create generic CRUD components for common patterns
5. Add an API explorer/tester in the admin interface
6. Build a feature flag system to enable/disable UI sections
7. Create documentation for adding new frontend features
    """)
    
    # Generate feature manifest
    print("\n" + "=" * 80)
    print("GENERATING FEATURE MANIFEST...")
    print("=" * 80)
    
    manifest = {
        'admin_tabs': admin_tabs,
        'backend_files': list(endpoints.keys()),
        'mounted_routers': list(mounted),
        'total_endpoints': sum(len(e) for e in endpoints.values()),
        'frontend_calls': len(frontend_refs),
        'gaps': {group: len(items) for group, items in feature_groups.items() if items}
    }
    
    import json
    with open('frontend_gaps_manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Manifest saved to frontend_gaps_manifest.json")
    print(f"\nSummary: Found {sum(manifest['gaps'].values())} backend endpoints without frontend UI")

if __name__ == "__main__":
    analyze_gaps()