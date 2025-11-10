# Style Engine - Addon Packaging

Modern, cross-platform packaging system for the Style Engine Blender addon.

## 🚀 Quick Start

### Windows
**Double-click:** `package_addon_EASY.bat`

### macOS/Linux
```bash
python3 package_addon_modern.py
```

---

## 📦 What Gets Packaged

The packaging script **automatically includes ALL files** from the `styleengine/` directory except:

### ✅ Included (Everything!)
- All Python files (`*.py`)
- README.md
- template.blend
- Any other addon files

### ❌ Excluded (Cache/Temp only)
- `__pycache__/` and `*.pyc` files
- `.git/` and version control files
- `.DS_Store` and macOS resource forks
- IDE files (`.vscode/`, `.idea/`)
- The `packaging/` directory itself

**No source files are ever deleted!** The script only creates a ZIP package.

---

## 📋 Files in This Directory

### Current (Use These!)

| File | Description |
|------|-------------|
| `package_addon_modern.py` | **Main packaging script** (Python 3.7+) |
| `package_addon_EASY.bat` | **Windows wrapper** - Easy double-click packaging |
| `package_config.txt` | Configuration (currently for reference only) |
| `README.md` | This file |

### Deprecated (OLD_* files)

All files starting with `OLD_` are previous versions kept for reference:

- `OLD_package_addon.bat` - Old Windows batch script
- `OLD_package_addon.py` - Old Python script
- `OLD_package_addon.ps1` - Old PowerShell script
- `OLD_package_addon_fixed.ps1` - Old PowerShell variant
- `OLD_package_addon_posix.ps1` - Old POSIX-focused variant
- `OLD_package_addon_advanced.bat` - Old advanced batch script

**You can safely delete OLD_* files** if you don't need them for reference.

---

## 🛠️ How It Works

### Cross-Platform ZIP Creation

The modern packaging script ensures **100% cross-platform compatibility**:

1. **Forward Slashes Only**
   - ZIP entries use `/` (forward slashes)
   - Works on Windows, macOS, and Linux
   - macOS Blender 4.5+ installation compatible

2. **Proper Structure**
   ```
   styleengine.zip
   └── styleengine/
       ├── __init__.py
       ├── prefs.py
       ├── ui_panel.py
       ├── workspace_setup.py
       ├── utils.py
       ├── heavypoly_integration.py
       ├── pie_menu.py
       ├── runcomfy_client.py
       ├── runcomfy_deployment.py
       ├── runcomfy_polling.py
       ├── runcomfy_server_client.py
       ├── runcomfy_server_manager.py
       ├── template.blend
       └── README.md
   ```

3. **Validation**
   - Checks for backslashes (would break macOS)
   - Verifies required files exist
   - Reports package statistics

---

## 📊 Package Output

After running the packaging script, you'll get:

```
styleengine.zip
```

Located in the `packaging/` directory. This ZIP is ready to distribute!

### Installation Instructions (Include with distribution)

1. Open Blender 4.2 or newer
2. Edit → Preferences → Add-ons
3. Click "Install from Disk..."
4. Select `styleengine.zip`
5. Enable "Style Engine" addon
6. Configure API credentials in addon preferences

---

## 🔧 Advanced Usage

### Running Manually

```bash
# From packaging directory
python package_addon_modern.py

# Or from project root
python scripts/addons/packaging/package_addon_modern.py
```

### Customizing Exclusions

Edit `package_addon_modern.py` and modify the `EXCLUDE_PATTERNS` set:

```python
EXCLUDE_PATTERNS = {
    '__pycache__',
    '*.pyc',
    # Add your own patterns here
    'my_test_file.py',
    'experimental_feature.py',
}
```

---

## 🐛 Troubleshooting

### "Python not found"
Install Python 3.7 or newer from https://www.python.org/

### "Source directory not found"
Make sure you're running the script from the `packaging/` directory or that the `styleengine/` folder exists one level up.

### "ZIP has backslashes"
This is a critical error. The script should use forward slashes. Report this issue if you see it.

---

## 📝 Technical Details

### Why Forward Slashes Matter

ZIP files use forward slashes (`/`) as path separators in the ZIP standard. Using backslashes (`\`) breaks compatibility with:
- macOS Blender 4.5+ installation
- Linux systems
- Standard-compliant ZIP tools

### Python's `zipfile` Module

We use `PurePosixPath` to ensure forward slashes even when running on Windows:

```python
from pathlib import PurePosixPath
posix_path = PurePosixPath(windows_path)  # Converts \ to /
```

This guarantees cross-platform compatibility without complex string manipulation.

---

## 🎯 Design Philosophy

1. **Non-Destructive** - Never deletes source files
2. **Inclusive by Default** - Packages everything automatically
3. **Exclude Intelligently** - Only excludes cache/temp/IDE files
4. **Cross-Platform First** - Works everywhere, no special cases
5. **Simple to Use** - Double-click on Windows, one command elsewhere

---

## 📚 Related Documentation

- **Addon Rules**: See workspace rules at project root
- **Blender Addon Guidelines**: https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html
- **ZIP Standard**: https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT

---

## ✨ Version History

- **2025-11-10**: Modern packaging script created
  - Automatic file inclusion
  - Cross-platform ZIP with forward slashes
  - Comprehensive validation
  - Non-destructive operation
  - Old scripts renamed to OLD_*

---

For questions or issues, check the main project README or contact the development team.

