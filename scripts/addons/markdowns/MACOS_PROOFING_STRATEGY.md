# 🛡️ macOS-Proofing Strategy for Blender Add-ons

**Date:** November 3, 2025  
**Goal:** Prevent future cross-platform compatibility issues

---

## 🎯 The Core Problem (Summary)

macOS Blender enforces **stricter Python import requirements** than Windows:
- Requires proper package structure with `__package__` attribute
- Relative imports (`from . import module`) need full package context
- File path separators must be handled correctly (`/` vs `\`)
- Import timing matters (modules must be registered before execution)

---

## ✅ Current Safeguards (Already Implemented)

### 1. **Bulletproof Import System**
```python
# Try standard imports first
try:
    from . import ui_panel
except (ImportError, ValueError) as e:
    # Fallback: Pre-register package + manual loading
    pkg = types.ModuleType('styleengine')
    sys.modules['styleengine'] = pkg
    # Load modules with full package context
```

✅ **Status:** Fully implemented in `__init__.py`

---

## 🔒 Additional Safeguards (Recommended)

### 2. **Pre-Flight Validation Script**

Create a validation script that checks package integrity BEFORE installation:

**File:** `scripts/addons/validate_package.py`

```python
#!/usr/bin/env python3
"""
Validate Blender addon package structure for cross-platform compatibility.
Run this before packaging the ZIP file.
"""

import sys
import os
import zipfile
from pathlib import Path

def validate_addon_zip(zip_path):
    """Validate addon ZIP structure."""
    errors = []
    warnings = []
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        files = zf.namelist()
        
        # 1. Check for proper folder structure
        if not any(f.startswith('styleengine/') for f in files):
            errors.append("❌ ZIP must contain 'styleengine/' folder at root")
        
        # 2. Check for art_director.py
        if 'styleengine/art_director.py' not in files:
            errors.append("❌ Missing styleengine/art_director.py")
        
        # 3. Check for required modules
        required = ['ui_panel.py', 'prefs.py', 'utils.py', 'workspace_setup.py']
        for module in required:
            if f'styleengine/{module}' not in files:
                errors.append(f"❌ Missing styleengine/{module}")
        
        # 4. Check for Windows path separators in file names
        for filename in files:
            if '\\' in filename:
                errors.append(f"❌ Windows path separator in: {filename}")
        
        # 5. Check bl_info in art_director.py
        init_content = zf.read('styleengine/art_director.py').decode('utf-8')
        if 'bl_info' not in init_content:
            errors.append("❌ Missing bl_info in art_director.py")
        
        # 6. Check for relative imports in modules
        for module in ['ui_panel.py', 'prefs.py', 'workspace_setup.py']:
            path = f'styleengine/{module}'
            if path in files:
                content = zf.read(path).decode('utf-8')
                if 'from . import' in content or 'from ..' in content:
                    # This is OK IF the fallback system is in place
                    if 'types.ModuleType' not in init_content:
                        warnings.append(f"⚠️ {module} uses relative imports but no fallback in art_director.py")
        
        # 7. Check file sizes (detect accidental binary inclusions)
        for filename in files:
            info = zf.getinfo(filename)
            if info.file_size > 1_000_000:  # 1 MB
                warnings.append(f"⚠️ Large file detected: {filename} ({info.file_size / 1024:.1f} KB)")
    
    return errors, warnings

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_package.py <path_to_zip>")
        sys.exit(1)
    
    zip_path = sys.argv[1]
    
    if not os.path.exists(zip_path):
        print(f"❌ File not found: {zip_path}")
        sys.exit(1)
    
    print(f"🔍 Validating: {zip_path}\n")
    
    errors, warnings = validate_addon_zip(zip_path)
    
    # Print results
    if errors:
        print("❌ ERRORS (Must fix):")
        for error in errors:
            print(f"  {error}")
        print()
    
    if warnings:
        print("⚠️ WARNINGS (Should fix):")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ Package structure is valid!")
        print("✅ Ready for cross-platform distribution\n")
        return 0
    elif not errors:
        print("✅ No critical errors (warnings only)\n")
        return 0
    else:
        print("❌ Fix errors before packaging\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

**Usage:**
```bash
python validate_package.py styleengine.zip
```

---

### 3. **Automated Testing Script**

Create a test script that can be run on different platforms:

**File:** `scripts/addons/test_imports.py`

```python
#!/usr/bin/env python3
"""
Test addon imports without Blender (basic validation).
This catches import errors early.
"""

import sys
import os
from pathlib import Path

def test_addon_imports():
    """Test if addon modules can be imported."""
    
    # Add styleengine directory to path
    addon_dir = Path(__file__).parent / "styleengine"
    sys.path.insert(0, str(addon_dir.parent))
    
    print("🧪 Testing addon imports...\n")
    
    try:
        # Test package import
        import styleengine
        print("✅ Package 'styleengine' imported")
        
        # Test individual modules
        modules = [
            'styleengine.utils',
            'styleengine.ui_panel',
            'styleengine.prefs',
            'styleengine.workspace_setup',
            'styleengine.runcomfy_client',
            'styleengine.runcomfy_deployment',
            'styleengine.runcomfy_polling',
        ]
        
        for module_name in modules:
            try:
                __import__(module_name)
                print(f"✅ Module '{module_name}' imported")
            except ImportError as e:
                print(f"❌ Failed to import '{module_name}': {e}")
                return False
        
        print("\n✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_addon_imports()
    sys.exit(0 if success else 1)
```

---

### 4. **Path Separator Auditing**

Audit all files for hardcoded path separators:

**File:** `scripts/addons/audit_paths.py`

```python
#!/usr/bin/env python3
"""
Audit Python files for hardcoded Windows path separators.
"""

import re
from pathlib import Path

def audit_file(filepath):
    """Check a file for hardcoded path separators."""
    issues = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        # Skip comments and strings that are clearly Windows-specific examples
        if line.strip().startswith('#'):
            continue
        
        # Look for hardcoded backslashes in paths
        # Pattern: looks like a path with backslashes
        if re.search(r'["\'][A-Za-z]:\\\\', line):  # e.g., "C:\\"
            issues.append((i, line.strip(), "Hardcoded Windows path"))
        
        # Look for path joins that might fail on Unix
        if 'os.path.join' not in line and re.search(r'["\'].*\\.*["\']', line):
            if 'replace' not in line and 'sep' not in line:
                issues.append((i, line.strip(), "Possible hardcoded backslash"))
    
    return issues

def main():
    addon_dir = Path(__file__).parent / "styleengine"
    
    print("🔍 Auditing Python files for path separator issues...\n")
    
    all_issues = []
    
    for py_file in addon_dir.glob("*.py"):
        issues = audit_file(py_file)
        if issues:
            all_issues.extend([(py_file.name, *issue) for issue in issues])
    
    if all_issues:
        print("⚠️ Found potential issues:\n")
        for filename, line_num, line_text, issue_type in all_issues:
            print(f"{filename}:{line_num}")
            print(f"  {issue_type}: {line_text[:80]}")
            print()
    else:
        print("✅ No path separator issues found!")
    
    return 0 if not all_issues else 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
```

---

### 5. **Update Packaging Script**

Enhance `package_addon.bat` to run validation automatically:

**File:** `scripts/addons/package_addon.bat` (additions)

```batch
@echo off
REM ... existing code ...

echo.
echo [5/6] Validating package structure...
python validate_package.py styleengine.zip
if errorlevel 1 (
    echo ERROR: Package validation failed!
    pause
    exit /b 1
)

echo.
echo [6/6] Package ready!
REM ... existing code ...
```

---

### 6. **Runtime Diagnostics**

Add diagnostic output to `__init__.py` that can be toggled:

```python
# At top of art_director.py
DEBUG_IMPORTS = os.environ.get('STYLEENGINE_DEBUG', '0') == '1'

def debug_print(msg):
    if DEBUG_IMPORTS:
        print(f"[Style Engine DEBUG] {msg}")

# In fallback import section:
debug_print(f"Platform: {sys.platform}")
debug_print(f"Python version: {sys.version}")
debug_print(f"Addon dir: {addon_dir}")
debug_print(f"__file__: {__file__}")
```

Users can enable by setting environment variable:
```bash
# macOS/Linux
export STYLEENGINE_DEBUG=1
blender

# Windows
set STYLEENGINE_DEBUG=1
blender.exe
```

---

### 7. **Documentation Updates**

Create a cross-platform testing checklist:

**File:** `scripts/addons/TESTING_CHECKLIST.md`

```markdown
# Cross-Platform Testing Checklist

## Before Packaging

- [ ] Run `python validate_package.py styleengine.zip`
- [ ] Run `python audit_paths.py`
- [ ] Check that ZIP structure is correct:
  ```
  styleengine.zip
  └── styleengine/
      ├── __init__.py
      ├── prefs.py
      └── ...
  ```
- [ ] Verify no Windows-specific paths in code
- [ ] Check that all `os.path.join()` is used (not string concatenation)

## Windows Testing

- [ ] Install from ZIP in Blender 4.2+
- [ ] Enable addon (check console for errors)
- [ ] Open preferences, verify UI appears
- [ ] Run "Setup Workspace"
- [ ] Test "Generate AI Image"

## macOS Testing

- [ ] Install from ZIP in Blender 4.2+
- [ ] Enable addon (check console for errors)
- [ ] Verify no import errors in console
- [ ] Open preferences, verify UI appears
- [ ] Run "Setup Workspace"
- [ ] Test "Generate AI Image"

## Linux Testing

- [ ] Install from ZIP in Blender 4.2+
- [ ] Enable addon (check console for errors)
- [ ] Open preferences, verify UI appears
- [ ] Run "Setup Workspace"
- [ ] Test "Generate AI Image"

## Compatibility Matrix

| Platform | Blender Version | Status |
|----------|----------------|--------|
| Windows 11 | 4.2 | ✅ Tested |
| Windows 11 | 4.3+ | ✅ Tested |
| macOS 14+ | 4.5+ | ⚠️ Needs testing |
| Ubuntu 22.04 | 4.2+ | ⚠️ Needs testing |
```

---

### 8. **CI/CD Pipeline (Advanced)**

Set up GitHub Actions to test on multiple platforms:

**File:** `.github/workflows/test-addon.yml`

```yaml
name: Test Addon Cross-Platform

on:
  push:
    branches: [ main, runcomfy ]
  pull_request:
    branches: [ main, runcomfy ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Validate package structure
        run: |
          cd scripts/addons
          python validate_package.py styleengine.zip
      
      - name: Audit path separators
        run: |
          cd scripts/addons
          python audit_paths.py
  
  test-import:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Test imports
        run: |
          cd scripts/addons
          python test_imports.py
```

---

## 📋 Implementation Priority

### **Immediate (Do Now)**

1. ✅ Run `validate_package.py` on current `styleengine.zip`
2. ✅ Run `audit_paths.py` to check for hardcoded separators
3. ✅ Update `package_addon.bat` to include validation step

### **Short-term (This Week)**

4. ⏳ Create `TESTING_CHECKLIST.md` and share with testers
5. ⏳ Add debug mode to `__init__.py`
6. ⏳ Find macOS tester to verify current package

### **Long-term (Next Sprint)**

7. ⏳ Set up CI/CD pipeline with GitHub Actions
8. ⏳ Create automated tests for Blender operators
9. ⏳ Document known platform differences

---

## 🎓 Best Practices Going Forward

### **Code Reviews**

When reviewing code changes, check for:
- ✅ No hardcoded path separators (`\\` or `/`)
- ✅ Use `os.path.join()` or `pathlib.Path`
- ✅ Use `.replace("\\", "/")` when passing to external systems
- ✅ No assumptions about how Blender loads addons
- ✅ Proper error handling for import failures

### **Before Every Release**

1. Run validation scripts
2. Test on at least 2 platforms (Windows + macOS or Linux)
3. Check Blender console for warnings/errors
4. Verify ZIP structure manually
5. Update version number in `bl_info`

### **Platform-Specific Notes**

**Windows:**
- More forgiving with imports
- Uses `\` as path separator
- Case-insensitive filesystem

**macOS:**
- Stricter import requirements (Blender 4.5+)
- Uses `/` as path separator
- Case-sensitive filesystem (sometimes)
- App sandboxing can affect file access

**Linux:**
- Uses `/` as path separator
- Case-sensitive filesystem
- May have permission issues with temp directories

---

## 🔗 Additional Resources

- [Python Import System Docs](https://docs.python.org/3/reference/import.html)
- [Blender Addon Guidelines](https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html)
- [Cross-Platform Python Best Practices](https://docs.python-guide.org/)

---

## ✅ Success Criteria

You'll know this is working when:

1. ✅ Package passes validation on all platforms
2. ✅ No import errors in Blender console
3. ✅ Addon installs and enables without manual intervention
4. ✅ All features work identically across platforms
5. ✅ CI/CD pipeline shows green on all platforms

---

**Last Updated:** November 3, 2025  
**Next Review:** After first macOS test session

