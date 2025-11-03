#!/usr/bin/env python3
"""
Validate Blender addon package structure for cross-platform compatibility.
Run this before packaging the ZIP file.

Usage:
    python validate_package.py styleengine.zip
"""

import sys
import os
import zipfile
from pathlib import Path

def validate_addon_zip(zip_path):
    """Validate addon ZIP structure."""
    errors = []
    warnings = []
    
    print(f"📦 Opening ZIP file: {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            
            print(f"📄 Found {len(files)} files in ZIP\n")
            
            # 1. Check for proper folder structure
            if not any(f.startswith('styleengine/') for f in files):
                errors.append("❌ ZIP must contain 'styleengine/' folder at root")
            else:
                print("✅ Found 'styleengine/' folder at root")
            
            # 2. Check for __init__.py
            if 'styleengine/__init__.py' not in files:
                errors.append("❌ Missing styleengine/__init__.py")
            else:
                print("✅ Found styleengine/__init__.py")
            
            # 3. Check for required modules
            required = ['ui_panel.py', 'prefs.py', 'utils.py', 'workspace_setup.py', 
                       'runcomfy_client.py', 'runcomfy_deployment.py', 'runcomfy_polling.py']
            for module in required:
                if f'styleengine/{module}' not in files:
                    errors.append(f"❌ Missing styleengine/{module}")
                else:
                    print(f"✅ Found styleengine/{module}")
            
            # 4. Check for Windows path separators in file names
            for filename in files:
                if '\\' in filename:
                    errors.append(f"❌ Windows path separator in: {filename}")
            
            print()
            
            # 5. Check bl_info in __init__.py
            try:
                init_content = zf.read('styleengine/__init__.py').decode('utf-8')
                if 'bl_info' not in init_content:
                    errors.append("❌ Missing bl_info in __init__.py")
                else:
                    print("✅ Found bl_info in __init__.py")
                
                # Check for fallback import system
                if 'types.ModuleType' in init_content and 'sys.modules' in init_content:
                    print("✅ macOS fallback import system detected")
                else:
                    warnings.append("⚠️ No macOS fallback import system found")
                
            except KeyError:
                errors.append("❌ Cannot read styleengine/__init__.py")
            
            print()
            
            # 6. Check for relative imports in modules
            for module in ['ui_panel.py', 'prefs.py', 'workspace_setup.py', 
                          'runcomfy_deployment.py', 'runcomfy_polling.py']:
                path = f'styleengine/{module}'
                if path in files:
                    try:
                        content = zf.read(path).decode('utf-8')
                        if 'from . import' in content or 'from ..' in content:
                            # This is OK IF the fallback system is in place
                            if 'types.ModuleType' not in init_content:
                                warnings.append(f"⚠️ {module} uses relative imports but no fallback in __init__.py")
                            else:
                                print(f"✅ {module} uses relative imports (fallback present)")
                    except:
                        warnings.append(f"⚠️ Could not read {path}")
            
            print()
            
            # 7. Check file sizes (detect accidental binary inclusions)
            large_files = []
            for filename in files:
                if filename.endswith('.py'):  # Only check Python files
                    info = zf.getinfo(filename)
                    if info.file_size > 500_000:  # 500 KB
                        large_files.append((filename, info.file_size))
            
            if large_files:
                warnings.append("⚠️ Large Python files detected:")
                for filename, size in large_files:
                    warnings.append(f"    {filename}: {size / 1024:.1f} KB")
            
            # 8. Check for __pycache__ or .pyc files (should not be in ZIP)
            cache_files = [f for f in files if '__pycache__' in f or f.endswith('.pyc')]
            if cache_files:
                warnings.append(f"⚠️ Found {len(cache_files)} cache files (should remove):")
                for f in cache_files[:5]:  # Show first 5
                    warnings.append(f"    {f}")
                if len(cache_files) > 5:
                    warnings.append(f"    ... and {len(cache_files) - 5} more")
            else:
                print("✅ No cache files found")
            
            # 9. Check for README
            if 'styleengine/README.md' in files:
                print("✅ Found README.md")
            else:
                warnings.append("⚠️ No README.md found (optional but recommended)")
    
    except zipfile.BadZipFile:
        errors.append("❌ File is not a valid ZIP archive")
    except Exception as e:
        errors.append(f"❌ Error reading ZIP: {e}")
    
    return errors, warnings

def main():
    print("🔍 Style Engine Addon Package Validator")
    print("=" * 50)
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python validate_package.py <path_to_zip>")
        print()
        print("Example:")
        print("  python validate_package.py styleengine.zip")
        sys.exit(1)
    
    zip_path = sys.argv[1]
    
    if not os.path.exists(zip_path):
        print(f"❌ File not found: {zip_path}")
        sys.exit(1)
    
    errors, warnings = validate_addon_zip(zip_path)
    
    # Print results
    print()
    print("=" * 50)
    print()
    
    if errors:
        print("❌ ERRORS (Must fix before distribution):")
        print()
        for error in errors:
            print(f"  {error}")
        print()
    
    if warnings:
        print("⚠️ WARNINGS (Should review):")
        print()
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ VALIDATION PASSED!")
        print("✅ Package structure is valid")
        print("✅ Ready for cross-platform distribution")
        print()
        return 0
    elif not errors:
        print("✅ VALIDATION PASSED (with warnings)")
        print("✅ No critical errors found")
        print("⚠️ Review warnings before distribution")
        print()
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("❌ Fix errors before packaging")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())

