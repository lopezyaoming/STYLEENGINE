# Style Engine Addon - Installation Guide

## ✅ Addon is Ready for Distribution!

Your addon has been successfully fixed and packaged for distribution.

**Package Location:** `C:\Coding\STYLEENGINE\scripts\addons\styleengine.zip`  
**Package Size:** 37 KB  
**Compatible with:** Blender 4.2+

---

## What Was Fixed

### 1. Registration System
- ❌ **Before:** Had both `bl_info` and `blender_manifest.toml` causing conflicts
- ✅ **After:** Uses traditional `bl_info` system only (easier to distribute)

### 2. Path System
- ❌ **Before:** Hardcoded paths to `C:\Coding\STYLEENGINE\` that broke when installed
- ✅ **After:** Dynamic paths that work from any installation location

### 3. File Storage
The addon now intelligently chooses where to store temp files:

1. **Best:** Next to your .blend file in `temp/ai_vision/` (if saved)
2. **Good:** In your configured output path (if set)
3. **Fallback:** System temp directory

---

## Installation Instructions

### For End Users

1. **Download** the `styleengine.zip` file
2. **Open** Blender 4.2 or later
3. Go to **Edit → Preferences → Add-ons**
4. Click **Install from Disk...**
5. Navigate to and select `styleengine.zip`
6. **Enable** the addon by checking the checkbox next to "Style Engine"
7. **Configure** your RunComfy API credentials in the addon preferences:
   - Expand the addon details
   - Enter your `RUNCOMFY_API_TOKEN`
   - Enter your `RUNCOMFY_USER_ID`
   - Click "Test Connection" to verify

---

## Repackaging the Addon

If you make changes to the source code, simply run:

```powershell
.\package_addon.ps1
```

This script will:
- ✅ Include all necessary Python files
- ✅ Include README.md
- ❌ Exclude `__pycache__/` folders
- ❌ Exclude `.pyc` compiled files
- ❌ Exclude `.git/` folders

---

## Testing Before Distribution

### Test in Development Mode (Linked Folder)
1. In Blender, go to Preferences → Add-ons
2. Click Install from Disk
3. Select the `styleengine` **folder** (not ZIP)
4. Test all features

### Test in Production Mode (ZIP Install)
1. Uninstall the dev version
2. Install from the `styleengine.zip`
3. Test all features again
4. Verify temp files are created in correct locations

---

## Features to Test

- ✅ **Setup Workspace** - Creates AI Vision dual-view layout
- ✅ **AI Camera** - Camera positioning and background image
- ✅ **Render Passes** - Depth, AO, Combined passes
- ✅ **Cloud Generation** - RunComfy API integration
- ✅ **Auto-refresh** - Viewport updates with new AI images
- ✅ **Auto-generate** - Continuous generation cycles
- ✅ **IP Adapter** - Reference image support

---

## Troubleshooting

### Addon doesn't appear after installation
- Make sure you're using Blender 4.2 or later
- Check the System Console (Window → Toggle System Console) for errors

### Temp files not being created
- Save your .blend file first (recommended)
- Or set an output path in the addon panel

### API connection fails
- Verify your RunComfy credentials in preferences
- Click "Test Connection" to diagnose

---

## Support

For issues or questions:
- Check the console output (Window → Toggle System Console)
- Review the addon preferences for configuration options
- Ensure you have valid RunComfy API credentials

---

## Distribution

This addon is now **self-contained** and **portable**. You can:
- Share the `styleengine.zip` with team members
- Distribute it to clients
- Upload to addon repositories
- Include it in project deliverables

The addon will work correctly regardless of where Blender is installed or where the user's .blend files are located.

