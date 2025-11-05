#!/usr/bin/env python3
"""
Style Engine - Cross-Platform Addon Packaging Script
Creates a proper ZIP with forward slashes for macOS/Linux compatibility
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path

def create_addon_package():
    """Create styleengine.zip with proper cross-platform structure."""
    
    # Paths
    script_dir = Path(__file__).parent
    source_dir = script_dir / 'styleengine'
    output_zip = script_dir / 'styleengine.zip'
    
    # Files to include
    files_to_include = [
        '__init__.py',
        'prefs.py',
        'ui_panel.py',
        'workspace_setup.py',
        'utils.py',
        'runcomfy_client.py',
        'runcomfy_deployment.py',
        'runcomfy_polling.py',
        'README.md',
    ]
    
    print("=" * 60)
    print("  Style Engine - Addon Packaging (Python)")
    print("=" * 60)
    print()
    
    # Check source directory
    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        return False
    
    # Remove old ZIP
    if output_zip.exists():
        print(f"Removing old ZIP: {output_zip.name}")
        output_zip.unlink()
    
    print("Creating addon package...")
    print()
    
    # Create ZIP with proper structure
    missing_files = []
    
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        print("Including files:")
        for filename in files_to_include:
            source_file = source_dir / filename
            
            if source_file.exists():
                # CRITICAL: Use forward slashes for cross-platform compatibility
                arcname = f"styleengine/{filename}"
                zf.write(source_file, arcname)
                print(f"  [+] {filename}")
            else:
                print(f"  [!] {filename} (not found, skipping)")
                missing_files.append(filename)
    
    print()
    print("Excluding:")
    print("  [-] __pycache__/")
    print("  [-] *.pyc files")
    print("  [-] .git/")
    print()
    
    if not output_zip.exists():
        print("ERROR: Failed to create ZIP")
        return False
    
    # Get ZIP size
    zip_size_kb = output_zip.stat().st_size // 1024
    
    print("=" * 60)
    print("  ZIP CREATED")
    print("=" * 60)
    print()
    print(f"Package created: {output_zip}")
    print(f"Size: {zip_size_kb} KB")
    print()
    
    # Verify structure
    print("Verifying ZIP structure...")
    with zipfile.ZipFile(output_zip, 'r') as zf:
        entries = zf.namelist()
        
        # Check for proper structure (forward slashes)
        has_proper_structure = all('styleengine/' in entry for entry in entries)
        has_backslashes = any('\\' in entry for entry in entries)
        
        print(f"  Entries in ZIP: {len(entries)}")
        print(f"  Sample entries:")
        for entry in entries[:5]:
            print(f"    - {entry}")
        
        print()
        if has_proper_structure and not has_backslashes:
            print("  [OK] Proper structure with forward slashes")
        elif has_backslashes:
            print("  [ERROR] ZIP contains backslashes! (macOS will fail)")
            return False
        else:
            print("  [WARNING] Structure may be incorrect")
    
    print()
    print("=" * 60)
    print("  SUCCESS!")
    print("=" * 60)
    print()
    print("Installation steps:")
    print("1. Open Blender 4.2+")
    print("2. Edit -> Preferences -> Add-ons")
    print("3. Click Install from Disk...")
    print(f"4. Select: {output_zip}")
    print("5. Enable the Style Engine addon")
    print()
    print("Cross-platform compatible: Windows, macOS, Linux")
    print()
    
    if missing_files:
        print(f"WARNING: {len(missing_files)} file(s) were missing:")
        for f in missing_files:
            print(f"  - {f}")
        print()
    
    return True

if __name__ == '__main__':
    success = create_addon_package()
    sys.exit(0 if success else 1)

