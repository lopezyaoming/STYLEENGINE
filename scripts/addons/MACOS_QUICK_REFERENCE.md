# 🚀 macOS-Proofing Quick Reference

**Quick guide for developers to prevent cross-platform issues**

---

## ⚡ Before Every Release

```bash
# 1. Validate package structure
python validate_package.py styleengine.zip

# 2. Audit for path issues
python audit_paths.py

# 3. Check ZIP structure manually
unzip -l styleengine.zip | head -20
```

**Expected structure:**
```
styleengine.zip
└── styleengine/
    ├── __init__.py          ← Must contain macOS fallback
    ├── prefs.py
    ├── ui_panel.py
    ├── workspace_setup.py
    ├── utils.py
    ├── runcomfy_client.py
    ├── runcomfy_deployment.py
    ├── runcomfy_polling.py
    └── README.md
```

---

## 🛡️ The macOS Problem (Simplified)

**What happened:**
- macOS Blender 4.5+ has stricter Python import requirements
- Relative imports (`from . import module`) failed without proper package context
- Caused "No module named" errors on macOS only

**The fix:**
```python
# In __init__.py - Pre-register the package before loading modules
import types
import sys

if 'styleengine' not in sys.modules:
    pkg = types.ModuleType('styleengine')
    pkg.__package__ = 'styleengine'
    pkg.__path__ = [addon_dir]
    sys.modules['styleengine'] = pkg
```

**This creates a proper Python package context before any modules are loaded.**

---

## ✅ Checklist: Is My Code macOS-Safe?

### **Imports**
- [ ] `__init__.py` has fallback import system
- [ ] No bare `import module` for local modules (use `from . import module`)
- [ ] All modules registered in `sys.modules` before execution

### **Paths**
- [ ] Use `os.path.join()` or `pathlib.Path` for all path operations
- [ ] No hardcoded backslashes (`\\`) in paths
- [ ] Use `.replace("\\", "/")` when sending paths to external systems
- [ ] No hardcoded temp directories (use `tempfile.gettempdir()`)

### **File Operations**
- [ ] Check if files exist before reading
- [ ] Use context managers (`with open(...)`)
- [ ] Handle both Unix (`/`) and Windows (`\`) separators

### **Testing**
- [ ] Tested on Windows
- [ ] Tested on macOS 14+ with Blender 4.5+
- [ ] No console errors on any platform
- [ ] ZIP structure verified

---

## 🚨 Red Flags in Code Review

**Watch for these patterns that break on macOS:**

```python
# ❌ BAD: Hardcoded Windows paths
path = "C:\\Users\\name\\file.txt"

# ✅ GOOD: Platform-agnostic
from pathlib import Path
path = Path.home() / "file.txt"
```

```python
# ❌ BAD: String concatenation for paths
path = base_dir + "\\" + filename

# ✅ GOOD: os.path.join
import os
path = os.path.join(base_dir, filename)
```

```python
# ❌ BAD: Assuming import order
from . import ui_panel  # Might fail if ui_panel not registered

# ✅ GOOD: Fallback system handles this
try:
    from . import ui_panel
except ImportError:
    # Fallback loading with full package context
```

```python
# ❌ BAD: Hardcoded temp directory
temp = "C:\\temp\\myfile.txt"

# ✅ GOOD: Use system temp
import tempfile
temp = os.path.join(tempfile.gettempdir(), "myfile.txt")
```

---

## 🔧 Validation Tools

### **validate_package.py**

Checks ZIP structure and package integrity.

**What it checks:**
- ✅ Correct folder structure (`styleengine/` at root)
- ✅ All required files present
- ✅ `bl_info` exists in `__init__.py`
- ✅ macOS fallback import system detected
- ✅ No Windows path separators in filenames
- ✅ No `__pycache__` or `.pyc` files
- ✅ No excessively large files

**Usage:**
```bash
python validate_package.py styleengine.zip
```

**Expected output:**
```
✅ VALIDATION PASSED!
✅ Package structure is valid
✅ Ready for cross-platform distribution
```

---

### **audit_paths.py**

Scans Python files for hardcoded path separators.

**What it checks:**
- ✅ Hardcoded Windows absolute paths (`C:\\`)
- ✅ Hardcoded backslashes in paths
- ✅ Path string concatenation (should use `os.path.join`)
- ✅ Hardcoded temp directories

**Usage:**
```bash
python audit_paths.py
```

**Expected output:**
```
✅ No cross-platform issues found!
✅ All path operations appear to be platform-safe
```

---

## 📝 Quick Testing Commands

### **Windows (PowerShell)**
```powershell
# Package addon
.\package_addon.bat

# Validate manually
python validate_package.py styleengine.zip

# Audit paths
python audit_paths.py
```

### **macOS/Linux (Bash)**
```bash
# Package addon (if you have the posix script)
./package_addon_posix.ps1

# Validate
python3 validate_package.py styleengine.zip

# Audit
python3 audit_paths.py

# Check ZIP structure
unzip -l styleengine.zip
```

---

## 🎯 Testing Priority

**Must test before release:**
1. ✅ Windows 10/11 + Blender 4.2+
2. ⚠️ macOS 14+ + Blender 4.5+ **(CRITICAL - this is where issues appear)**
3. ⚠️ Linux (Ubuntu/Fedora) + Blender 4.2+

**How to find macOS testers:**
- Blender community forums
- Discord servers (Blender, ComfyUI)
- Local developer meetups
- Beta testing programs

---

## 🐛 Common macOS Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `No module named 'styleengine.__init__.ui_panel'` | Package not registered | Add fallback in `__init__.py` |
| `attempted relative import with no known parent package` | No package context | Pre-register package in `sys.modules` |
| `No such file or directory: '.../ui_panel.py'` | Wrong ZIP structure | Ensure `styleengine/` folder at root |
| Paths with `\` don't work | Hardcoded Windows separators | Use `os.path.join()` or `Path` |

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `MACOS_PROOFING_STRATEGY.md` | Complete strategy and implementation plan |
| `CROSS_PLATFORM_TESTING.md` | Detailed testing checklist for all platforms |
| `MACOS_QUICK_REFERENCE.md` | This file - quick developer reference |
| `COMPLETE_MACOS_SOLUTION.md` | Original deep dive into the problem |

---

## 🎓 Key Takeaways

1. **macOS is stricter** - What works on Windows might not work on macOS
2. **Test early** - Get macOS testers involved before release
3. **Use validation tools** - Run `validate_package.py` before every release
4. **Avoid hardcoded paths** - Always use `os.path.join()` or `pathlib.Path`
5. **Package context matters** - Pre-register modules in `sys.modules`

---

## ✅ Definition of "macOS-Proof"

Your addon is macOS-proof when:

- [x] Package passes `validate_package.py`
- [x] Code passes `audit_paths.py`
- [x] Installs without errors on macOS Blender 4.5+
- [x] No import errors in console
- [x] All features work identically to Windows
- [x] Tested on real macOS hardware

---

## 🚀 Next Steps

1. **Now:** Run validation tools on current package
2. **This week:** Find macOS tester
3. **Before release:** Complete testing checklist
4. **After release:** Monitor for platform-specific issues

---

**Remember:** Cross-platform compatibility is not optional - it's essential for a professional addon!

---

**Last Updated:** November 3, 2025  
**See also:** `MACOS_PROOFING_STRATEGY.md` for complete implementation details

