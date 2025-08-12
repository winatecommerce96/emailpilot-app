#!/usr/bin/env python3
"""
Check package compatibility before deployment to EmailPilot
This prevents dependency conflicts that can crash the application
"""
import sys
from pathlib import Path
import re

def parse_requirements(file_path):
    """Parse a requirements.txt file and extract package info"""
    packages = {}
    
    if not Path(file_path).exists():
        return packages
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Handle different requirement formats
                if '==' in line:
                    name, version = line.split('==', 1)
                    packages[name.strip()] = ('==', version.strip())
                elif '>=' in line:
                    name, version = line.split('>=', 1)
                    packages[name.strip()] = ('>=', version.strip())
                elif '<=' in line:
                    name, version = line.split('<=', 1)
                    packages[name.strip()] = ('<=', version.strip())
                elif '>' in line:
                    name, version = line.split('>', 1)
                    packages[name.strip()] = ('>', version.strip())
                elif '<' in line:
                    name, version = line.split('<', 1)
                    packages[name.strip()] = ('<', version.strip())
                else:
                    # No version specified
                    packages[line.strip()] = (None, None)
    
    return packages

def check_compatibility(emailpilot_reqs, package_reqs):
    """Check if package requirements conflict with EmailPilot"""
    conflicts = []
    warnings = []
    
    for pkg_name, (pkg_op, pkg_ver) in package_reqs.items():
        if pkg_name in emailpilot_reqs:
            ep_op, ep_ver = emailpilot_reqs[pkg_name]
            
            # Check for exact version conflicts
            if ep_op == '==' and pkg_op == '==' and ep_ver != pkg_ver:
                conflicts.append(f"❌ {pkg_name}: EmailPilot requires =={ep_ver}, package requires =={pkg_ver}")
            elif ep_op == '==' and pkg_op and pkg_op != '==':
                warnings.append(f"⚠️  {pkg_name}: EmailPilot has pinned version =={ep_ver}, package wants {pkg_op}{pkg_ver}")
            elif pkg_op == '==' and ep_op and ep_op != '==':
                warnings.append(f"⚠️  {pkg_name}: Package wants pinned version =={pkg_ver}, EmailPilot has {ep_op}{ep_ver}")
    
    return conflicts, warnings

def main():
    print("🔍 EmailPilot Package Compatibility Checker")
    print("=" * 50)
    
    # Find EmailPilot requirements
    emailpilot_req_path = Path("requirements_firestore.txt")
    if not emailpilot_req_path.exists():
        print("❌ Cannot find EmailPilot requirements_firestore.txt")
        sys.exit(1)
    
    # Parse EmailPilot requirements
    print("\n📋 Loading EmailPilot requirements...")
    emailpilot_reqs = parse_requirements(emailpilot_req_path)
    print(f"   Found {len(emailpilot_reqs)} packages")
    
    # Find package requirements
    if len(sys.argv) > 1:
        package_req_path = Path(sys.argv[1])
    else:
        # Try to find it in common locations
        for path in ["requirements.txt", "*/requirements.txt", "*/*/requirements.txt"]:
            matches = list(Path(".").glob(path))
            if matches:
                package_req_path = matches[0]
                break
        else:
            print("\n❌ Cannot find package requirements.txt")
            print("   Usage: python check_package_compatibility.py <path/to/requirements.txt>")
            sys.exit(1)
    
    # Parse package requirements
    print(f"\n📦 Loading package requirements from: {package_req_path}")
    package_reqs = parse_requirements(package_req_path)
    print(f"   Found {len(package_reqs)} packages")
    
    # Check compatibility
    print("\n🔍 Checking compatibility...")
    conflicts, warnings = check_compatibility(emailpilot_reqs, package_reqs)
    
    # Report results
    if conflicts:
        print("\n❌ CONFLICTS FOUND:")
        for conflict in conflicts:
            print(f"   {conflict}")
        print("\n⚠️  These conflicts WILL cause deployment failures!")
        print("   Do NOT install these package dependencies")
    else:
        print("\n✅ No direct conflicts found")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print("\n   These may cause issues, proceed with caution")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    if conflicts or warnings:
        print("   1. Do NOT run 'pip install -r requirements.txt' from the package")
        print("   2. Copy only the necessary code files")
        print("   3. Use EmailPilot's existing dependencies")
        print("   4. Test thoroughly before deploying")
    else:
        print("   1. Package appears compatible")
        print("   2. Still recommend testing before full deployment")
        print("   3. Consider using safe deployment mode")
    
    return len(conflicts)

if __name__ == "__main__":
    sys.exit(main())