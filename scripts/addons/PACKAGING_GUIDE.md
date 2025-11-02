# Style Engine - Packaging Guide

## 📦 **Distribution Scripts**

We provide **three packaging methods** to create distribution-ready addon packages:

### **1. `package_addon.bat` - Simple & Fast** ⚡
**Use when:** Quick packaging for testing or immediate deployment

**Features:**
- ✅ Fast execution
- ✅ Simple output
- ✅ Cross-platform compatible ZIP
- ✅ Automatic cleanup

**Usage:**
```batch
cd C:\Coding\STYLEENGINE\scripts\addons
package_addon.bat
```

---

### **2. `package_addon_advanced.bat` - Robust & Professional** 🏆
**Use when:** Production releases, team distribution, quality assurance

**Features:**
- ✅ Configuration file support (`package_config.txt`)
- ✅ Comprehensive validation
- ✅ Detailed logging (`package_log.txt`)
- ✅ ZIP integrity verification
- ✅ Color-coded output
- ✅ Error tracking
- ✅ File count reporting

**Usage:**
```batch
cd C:\Coding\STYLEENGINE\scripts\addons
package_addon_advanced.bat
```

---

### **3. `package_addon.ps1` - PowerShell Native** 💻
**Use when:** PowerShell environment preferred

**Features:**
- ✅ Native PowerShell experience
- ✅ Clean output formatting
- ✅ Cross-platform compatible ZIP

**Usage:**
```powershell
cd C:\Coding\STYLEENGINE\scripts\addons
.\package_addon.ps1
```

---

## 🔧 **Configuration**

### **Edit `package_config.txt` to customize packaging:**

```
# Core addon files (required)
__init__.py
prefs.py
ui_panel.py
workspace_setup.py
utils.py

# RunComfy integration
runcomfy_client.py
runcomfy_deployment.py
runcomfy_polling.py

# Documentation
README.md

# Add new files here:
# new_feature.py
# assets/icon.png
# locales/en_US.json
```

**Adding files:** Just add the filename (with relative path if in subdirectory)
**Comments:** Lines starting with `#` are ignored
**Subdirectories:** Automatically created as needed

---

## 📋 **What Gets Packaged**

### **✅ Included:**
- All Python source files (`.py`)
- README and documentation (`.md`)
- Configuration files specified in config
- Subdirectories as needed

### **❌ Excluded (Automatic):**
- `__pycache__/` directories
- Compiled Python files (`.pyc`)
- Git directories (`.git/`)
- Other ZIP files (`.zip`)
- OS temp files (`.DS_Store`, `Thumbs.db`)
- Log files from previous runs

---

## 🎯 **Packaging Workflow**

### **Development Cycle:**
```
1. Make changes to addon files
2. Test in dev environment (symlink)
3. Run: package_addon.bat
4. Test the ZIP on another computer
5. If issues: fix → repeat
6. When ready: package_addon_advanced.bat (for production)
```

### **Release Checklist:**
- [ ] All features tested in dev mode
- [ ] Version number updated in `__init__.py`
- [ ] README updated with changes
- [ ] `package_config.txt` includes all new files
- [ ] Run `package_addon_advanced.bat`
- [ ] Check `package_log.txt` for warnings
- [ ] Test ZIP on Windows, macOS, Linux
- [ ] Verify addon loads without errors
- [ ] Test all major features work
- [ ] Tag release in git
- [ ] Distribute ZIP

---

## 🌍 **Cross-Platform Compatibility**

### **ZIP Structure (Works on All Platforms):**
```
styleengine.zip
└── styleengine/
    ├── __init__.py
    ├── prefs.py
    ├── ui_panel.py
    ├── workspace_setup.py
    ├── utils.py
    ├── runcomfy_client.py
    ├── runcomfy_deployment.py
    ├── runcomfy_polling.py
    └── README.md
```

**Why this works:**
- ✅ Forward slashes in paths (universal)
- ✅ No Windows-specific line endings forced
- ✅ No platform-specific metadata
- ✅ Python's relative imports work everywhere
- ✅ ZIP format is cross-platform standard

---

## 🔍 **Troubleshooting**

### **"PowerShell not found" error:**
**Solution:** You need Windows 10+ with PowerShell 5.0+
```batch
powershell -version
```

### **"Source directory not found":**
**Solution:** Run script from `scripts/addons/` directory
```batch
cd C:\Coding\STYLEENGINE\scripts\addons
```

### **Files missing from ZIP:**
**Solution 1:** Check `package_config.txt` has all files listed
**Solution 2:** Verify files exist in `styleengine/` folder
**Solution 3:** Check `package_log.txt` for warnings

### **"Invalid package structure" error:**
**Solution:** Ensure `__init__.py`, `prefs.py`, and `ui_panel.py` exist
These are critical addon files and must be present.

### **ZIP won't install in Blender:**
**Solution 1:** Extract ZIP and check folder structure (should be `styleengine/` folder inside)
**Solution 2:** Check Blender console for Python errors (Window → Toggle System Console)
**Solution 3:** Verify `bl_info` dict exists in `__init__.py`

---

## 📊 **Validation**

### **Advanced Script Validates:**
1. ✅ Source directory exists
2. ✅ Config file present (or falls back to defaults)
3. ✅ PowerShell available
4. ✅ `__init__.py` has `bl_info` dictionary
5. ✅ Critical files copied successfully
6. ✅ Package structure is valid
7. ✅ ZIP created successfully
8. ✅ ZIP is readable and contains expected files

### **Check Validation Log:**
```batch
type package_log.txt
```

Look for:
- `[ERROR]` - Critical issues
- `[WARNING]` - Non-critical issues
- `[SUCCESS]` - Package created successfully

---

## 🚀 **Advanced Usage**

### **Batch Processing Multiple Addons:**
Create `package_all.bat`:
```batch
@echo off
call package_addon.bat
if errorlevel 1 (
    echo Packaging failed!
    exit /b 1
)
echo All addons packaged successfully!
```

### **Automated Testing:**
```batch
@echo off
call package_addon.bat
if errorlevel 1 exit /b 1

REM Test install (requires Blender in PATH)
blender --background --python test_addon_install.py
```

### **CI/CD Integration:**
```yaml
# GitHub Actions example
- name: Package Addon
  run: |
    cd scripts/addons
    ./package_addon.bat
    
- name: Upload Artifact
  uses: actions/upload-artifact@v3
  with:
    name: styleengine-addon
    path: scripts/addons/styleengine.zip
```

---

## 💡 **Best Practices**

1. **Always test the ZIP:**
   - Install on fresh Blender
   - Test on different OS if possible
   - Verify all features work

2. **Keep config file updated:**
   - Add new files immediately
   - Document why each file is included
   - Review periodically for unused files

3. **Version control:**
   - Commit before packaging
   - Tag releases: `v0.1.0`
   - Keep ZIPs out of git (add to `.gitignore`)

4. **Documentation:**
   - Update README before packaging
   - Include installation instructions
   - Document breaking changes

5. **Clean builds:**
   - Delete old ZIPs first
   - Clear `__pycache__` from dev folder
   - Use fresh temp directories

---

## 📝 **Quick Reference**

### **File Purposes:**
| File | Purpose |
|------|---------|
| `package_addon.bat` | Simple, fast packaging |
| `package_addon_advanced.bat` | Production-ready packaging with validation |
| `package_addon.ps1` | PowerShell-native packaging |
| `package_config.txt` | File list for packaging |
| `package_log.txt` | Generated log file |
| `styleengine.zip` | Generated distribution package |

### **Common Commands:**
```batch
REM Quick package
package_addon.bat

REM Production package
package_addon_advanced.bat

REM View log
type package_log.txt

REM Clean up
del styleengine.zip package_log.txt
```

---

## 🆘 **Support**

If packaging fails:
1. Check `package_log.txt`
2. Verify file structure
3. Run advanced script for detailed diagnostics
4. Check Windows Event Viewer for system issues
5. Try PowerShell script as alternative

**Remember:** The generated ZIP works on **Windows, macOS, and Linux**! 🌍

