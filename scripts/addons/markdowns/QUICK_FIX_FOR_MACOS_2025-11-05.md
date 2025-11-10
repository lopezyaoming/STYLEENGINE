# Quick Fix for macOS Installation Issue
**For Ian's Mac** | Date: Nov 5, 2025 | **CRITICAL UPDATE**

## 🎯 THE REAL ISSUE (JUST DISCOVERED!)

The ZIP file had **BACKSLASHES** (`styleengine\file.py`) instead of **FORWARD SLASHES** (`styleengine/file.py`)!

On macOS/Linux, backslashes create files with `\` in their NAMES, not directories!

So the ZIP extracted as:
```
styleengine\__init__.py  ← This is a FILE NAME, not a folder!
```

Instead of:
```
styleengine/
  __init__.py  ← File inside folder
```

**This has been FIXED!** Fresh ZIP now uses forward slashes.

---

## ✅ SOLUTION (5 minutes)

### 1. Remove Old Version
- Open Blender
- **Edit → Preferences → Add-ons**
- Search "Style Engine"
- Click **❌ Remove** (not just disable!)
- **Quit Blender**

### 2. Install Fresh Version
- Restart Blender
- **Edit → Preferences → Add-ons**
- Click **Install from Disk...**
- Select: `styleengine.zip` (attached)
- Enable checkbox

### 3. Verify
Look for this in console:
```
[Style Engine] utils.py exists: True  ← Should say "True"!
```

---

## 🔧 What We Fixed

1. **Enhanced path detection** - 3 layers of fallback for macOS quirks
2. **Better error messages** - Tells you exactly what's wrong
3. **Path separator safety** - Uses `os.path.join()` everywhere (no more `/` vs `\` issues)

---

## 📦 Files Included

- `styleengine.zip` - Fresh addon package with fix
- `MACOS_CLEAN_INSTALL_GUIDE.md` - Detailed instructions (if needed)

---

## ❓ Still Having Issues?

Send console output from Blender:
- **Window → Toggle System Console** (macOS: check terminal)
- Look for lines starting with `[Style Engine]`
- Share the debug output

---

## ✨ This Should Fix

- ❌ "Cannot write a single file with an animation format selected" → **FIXED** (surgical render settings)
- ❌ Path detection errors → **FIXED** (enhanced detection)
- ❌ Import errors on macOS → **FIXED** (fallback loader)
- ✅ Works with HEAVYPOLY and other addons

---

**Ready to test!** 🚀

