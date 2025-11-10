# macOS Clean Installation Guide
**Critical fix for path detection issues**

## 🚨 THE PROBLEM

If you see this error:
```
Missing files: ['_init_.py', 'utils.py', 'ui_panel.py', 'prefs.py']
```

Note the `'_init_.py'` with **SINGLE underscores** instead of double underscores `'__init__.py'`.

**This means an OLD version is still installed!**

---

## ✅ SOLUTION: Clean Installation

### Step 1: Fully Uninstall Old Version

1. Open Blender
2. Go to **Edit → Preferences → Add-ons**
3. Search for "Style Engine"
4. If found:
   - Click the **❌ Remove** button (not just disable!)
   - **Confirm removal**
5. **Quit Blender completely**

### Step 2: Manual Cleanup (if needed)

If the addon still appears after removal, manually delete:

```bash
# macOS default addon location
~/Library/Application Support/Blender/4.5/scripts/addons/styleengine/

# Or portable install
/Applications/Blender.app/Contents/Resources/portable/scripts/addons/styleengine/
```

**Commands:**
```bash
# Check both locations
ls -la ~/Library/Application\ Support/Blender/*/scripts/addons/ | grep style
ls -la /Applications/Blender.app/Contents/Resources/portable/scripts/addons/ | grep style

# Remove if found
rm -rf ~/Library/Application\ Support/Blender/*/scripts/addons/styleengine/
rm -rf /Applications/Blender.app/Contents/Resources/portable/scripts/addons/styleengine/
```

### Step 3: Restart Blender

**Important:** Fully restart Blender to clear cached modules.

### Step 4: Fresh Install

1. Open Blender
2. Go to **Edit → Preferences → Add-ons**
3. Click **Install from Disk...**
4. Select: `styleengine.zip` (the latest version)
5. Click **Install Add-on**
6. **Enable** the checkbox next to "Style Engine"

### Step 5: Verify Installation

Check the Blender console for:

```
[Style Engine] Initial path detection:
  __file__ = /path/to/styleengine/__init__.py
  addon_dir = /path/to/styleengine
  Checking: /path/to/styleengine/utils.py → True
[Style Engine] Final addon_dir: /path/to/styleengine
[Style Engine] utils.py exists: True
```

✅ If you see `True`, the addon is correctly installed!

---

## 🔍 What's Been Fixed (2025-11-05)

### Enhanced Path Detection

The addon now has **3-layer path detection**:

1. **Standard detection**: Check if `__file__` points to styleengine directory
2. **Subdirectory search**: Look for `styleengine/` subdirectory
3. **__name__ fallback**: Use Python's `__name__` to find correct path

### Better Error Messages

If installation still fails, you'll now see:

```
[Style Engine] ❌ Addon path verification failed!

Current directory: /path/to/wrong/location
Missing files: ['__init__.py', 'utils.py', ...]

Possible causes:
1. OLD VERSION STILL INSTALLED - Most likely cause!
   → Fully uninstall addon from Blender preferences
   → Restart Blender
   → Reinstall fresh styleengine.zip

2. ZIP structure is incorrect
   → ZIP should contain: styleengine/__init__.py, styleengine/utils.py, etc.

3. macOS/Blender installation quirk
   → Path separators or permissions issue

Debug info:
  __file__ = ...
  __name__ = ...
  Directory contents: [...]
```

This helps diagnose the exact issue!

---

## 🧪 Verify ZIP Structure (Developer)

Before distributing, verify the ZIP structure:

```bash
# macOS/Linux
unzip -l styleengine.zip | head -20

# Expected output:
# styleengine/__init__.py
# styleengine/utils.py
# styleengine/ui_panel.py
# styleengine/prefs.py
# styleengine/workspace_setup.py
# ...
```

**Correct structure:**
```
styleengine.zip
└── styleengine/
    ├── __init__.py
    ├── utils.py
    ├── ui_panel.py
    ├── prefs.py
    ├── workspace_setup.py
    ├── runcomfy_client.py
    ├── runcomfy_deployment.py
    ├── runcomfy_polling.py
    └── README.md
```

**Incorrect structure (will fail):**
```
styleengine.zip
├── __init__.py  ← WRONG! Files at root
├── utils.py
└── ...
```

---

## 🛠️ Troubleshooting

### Issue: "Import errors" on macOS

**Symptom:**
```
ImportError: attempted relative import with no known parent package
```

**Solution:**
This is handled automatically by the enhanced fallback loader. If you still see this, follow the clean install steps above.

### Issue: Path separators (\ vs /)

**Symptom:**
```
FileNotFoundError: No such file or directory: '/path/to/styleengine\utils.py'
```

**Solution:**
The addon now uses `os.path.join()` exclusively for all path operations. This is cross-platform safe.

### Issue: Permissions denied

**Symptom:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Check/fix permissions
chmod -R 755 ~/Library/Application\ Support/Blender/*/scripts/addons/styleengine/
```

---

## 📋 Installation Checklist

- [ ] Fully uninstalled old version (removed, not just disabled)
- [ ] Restarted Blender
- [ ] Installed fresh `styleengine.zip`
- [ ] Enabled addon checkbox
- [ ] Checked console for successful path detection
- [ ] Tested "Setup Workspace" operator

---

## 🎯 For Developers: Path Safety Patterns

When adding new code, **always** use:

```python
# ✅ GOOD - Cross-platform safe
file_path = os.path.join(base_dir, 'subfolder', 'file.py')

# ❌ BAD - Windows-only
file_path = base_dir + '\\subfolder\\file.py'

# ❌ BAD - Unix-only
file_path = base_dir + '/subfolder/file.py'

# ❌ BAD - Mixed (nightmare)
file_path = base_dir + '\\subfolder/file.py'
```

**String literals in paths:**
```python
# ✅ GOOD
from pathlib import Path
temp_dir = Path(temp_base) / 'ai_vision' / 'output.png'

# ✅ GOOD
import os
temp_dir = os.path.join(temp_base, 'ai_vision', 'output.png')
```

---

## 📚 Related Documentation

- `COMPLETE_MACOS_SOLUTION.md` - Technical deep dive
- `MACOS_PATH_FIX_2025-11-05.md` - Latest path detection fix
- `CROSS_PLATFORM_TESTING.md` - Full testing checklist
- `validate_package.py` - ZIP structure validator

---

## Version

- **Date**: 2025-11-05
- **Fix**: Enhanced 3-layer path detection + better error messages
- **Compatible**: Blender 4.2 - 4.5+ (Windows, macOS, Linux)

