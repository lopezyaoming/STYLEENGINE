# Style Engine Addon - Deployment Fixes Applied

## Date: October 31, 2025

## Problems Fixed

### 1. ✅ Identity Crisis - Dual Registration System
**Problem:** The addon had both `bl_info` (Blender 3.x) and `blender_manifest.toml` (Blender 4.2+), causing registration conflicts when installed from ZIP.

**Solution:** Removed `blender_manifest.toml` to use the traditional addon system with `bl_info` only.

### 2. ✅ Hardcoded Path Assumptions
**Problem:** The addon assumed it would always be in `C:\Coding\STYLEENGINE\scripts\addons\styleengine\` and used this path structure to find data directories. When installed from ZIP, Blender places addons in the user's AppData directory, breaking all file operations.

**Solution:** 
- Replaced `ADDON_ROOT` with a new `get_temp_directory(context)` function
- The function intelligently chooses the best temp directory:
  1. **First priority:** `.blend` file directory (if saved) - `//temp/ai_vision/`
  2. **Second priority:** User's `output_path` setting (if configured)
  3. **Fallback:** System temp directory - `%TEMP%/blender_styleengine/ai_vision/`

## Files Modified

### `workspace_setup.py`
- Removed hardcoded `ADDON_ROOT` path calculation
- Added `get_temp_directory(context)` helper function
- Updated all file path operations to use the new function
- All functions now properly handle both dev and production environments

### `blender_manifest.toml`
- **DELETED** - No longer needed for traditional addon system

## How to Package and Install

### Creating the ZIP Package

1. Navigate to `C:\Coding\STYLEENGINE\scripts\addons\`
2. Zip the entire `styleengine` folder
3. Name it: `styleengine.zip`

**What to include in the ZIP:**
```
styleengine/
├── __init__.py         (with bl_info)
├── prefs.py
├── ui_panel.py
├── workspace_setup.py
├── utils.py
├── runcomfy_client.py
├── runcomfy_deployment.py
└── runcomfy_polling.py
```

**What NOT to include:**
- ❌ `__pycache__/` folders
- ❌ `.pyc` files
- ❌ `.git/` folders
- ❌ `blender_manifest.toml` (already deleted)

### Installing in Blender

1. Open Blender 4.2+
2. Go to **Edit → Preferences → Add-ons**
3. Click **Install from Disk...**
4. Select your `styleengine.zip`
5. Enable the addon by checking the checkbox
6. Configure your RunComfy API credentials in the preferences

## Testing the Addon

After installation, test these features:

1. **Setup Workspace** - Should create the AI Vision workspace
2. **Check temp files** - They should be created relative to your .blend file (if saved) or in your output path
3. **Generate AI** - Should work from any location, not just the dev directory

## Key Benefits

✅ **Portable** - Works from any installation location
✅ **Self-contained** - No dependency on project structure
✅ **User-friendly** - Temp files go to sensible locations
✅ **Compatible** - Works both in dev (linked folder) and production (ZIP install)

## Notes

- If your .blend file is saved, all temp files will be in `[your_blend_file_location]/temp/ai_vision/`
- If your .blend file is not saved, files go to your configured output path
- As a last resort, files go to system temp directory
- The addon no longer requires a specific folder structure

