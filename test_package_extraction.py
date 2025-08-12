#!/usr/bin/env python3
"""Test package extraction logic"""
import zipfile
from pathlib import Path
import tempfile
import shutil

def test_extraction():
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy the zip file to temp directory
        zip_path = Path("emailpilot_calendar_tab_20250809_122906.zip")
        if not zip_path.exists():
            print(f"❌ Zip file not found: {zip_path}")
            return
            
        # Extract the zip file
        extract_dir = temp_path / "test_extracted"
        extract_dir.mkdir()
        
        print(f"📦 Extracting to: {extract_dir}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        print(f"\n📁 Contents of extract_dir:")
        for item in extract_dir.iterdir():
            print(f"  - {item.name} {'(dir)' if item.is_dir() else '(file)'}")
        
        # Check for deployment script in root
        deploy_script = extract_dir / "deploy_to_emailpilot.sh"
        print(f"\n🔍 Checking root: {deploy_script}")
        print(f"   Exists: {deploy_script.exists()}")
        
        # Check for subdirectories
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        print(f"\n📂 Subdirectories found: {len(subdirs)}")
        
        if subdirs:
            for subdir in subdirs:
                print(f"\n📁 Contents of {subdir.name}:")
                for item in subdir.iterdir():
                    print(f"    - {item.name} {'(dir)' if item.is_dir() else '(file)'}")
                
                # Check for deployment script in subdirectory
                sub_deploy_script = subdir / "deploy_to_emailpilot.sh"
                print(f"\n🔍 Checking {subdir.name}: {sub_deploy_script}")
                print(f"   Exists: {sub_deploy_script.exists()}")
                
                if sub_deploy_script.exists():
                    print(f"   ✅ Found deployment script!")
                    print(f"   Full path: {sub_deploy_script}")

if __name__ == "__main__":
    test_extraction()