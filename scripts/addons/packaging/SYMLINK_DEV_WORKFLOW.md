# ⚠️ CRITICAL: Symlink Development Workflow

## Overview

**The developer uses a dedicated Blender 4.4 installation exclusively for Style Engine development with a SYMLINK setup.**

This means:
- Development files: `C:\Coding\STYLEENGINE\scripts\addons\styleengine\`
- Blender 4.4 addon folder: `C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine`
- **The Blender folder is a SYMLINK pointing to the development folder**

## ⚠️ WARNING: Packaging Can Break the Symlink!

### What Breaks the Symlink

**Installing the packaged ZIP in Blender 4.4 will DESTROY the symlink!**

When you:
1. Package the addon (`package_addon_EASY.bat`)
2. Test it by installing in Blender 4.4 (Edit → Preferences → Install Add-on)
3. Blender **replaces** the symlink with actual files
4. Development workflow breaks - changes in Cursor won't sync to Blender

### Symptoms of Broken Symlink

- Version number doesn't update in Blender preferences
- Code changes in Cursor don't reflect in Blender
- `bl_info` author shows old values
- Console shows loading from `styleengine_backup` folder

## 🔧 How to Restore the Symlink

If the symlink breaks, follow these steps:

### Step 1: Check if Symlink is Broken

Run in PowerShell:
```powershell
Get-Item "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" | Select-Object LinkType, Target
```

**If broken**: LinkType will be blank (empty `{}`)
**If working**: LinkType will show `SymbolicLink`

### Step 2: Delete Broken Folder

Run PowerShell **as Administrator**:
```powershell
Remove-Item "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" -Recurse -Force
```

### Step 3: Recreate Symlink

Run PowerShell **as Administrator**:
```powershell
New-Item -ItemType SymbolicLink -Path "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" -Target "C:\Coding\STYLEENGINE\scripts\addons\styleengine"
```

### Step 4: Verify Symlink

Run in PowerShell:
```powershell
Get-Item "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" | Select-Object Mode, LinkType
```

**Success**: Mode shows `d----l` (the `l` means link)

### Step 5: Restart Blender

Fully close and reopen Blender 4.4. Changes should now sync correctly.

## 📋 Best Practices for Agents

### When Packaging the Addon:

1. ✅ **DO**: Run `package_addon_EASY.bat` to create `styleengine.zip`
2. ✅ **DO**: Test the package in a **different** Blender installation (not 4.4)
3. ✅ **DO**: Test on virtual machines or other computers
4. ❌ **DON'T**: Install the packaged ZIP in Blender 4.4 (dev install)
5. ❌ **DON'T**: Copy files to the Blender 4.4 addon folder manually

### When Testing:

- Use Blender's addon toggle (off/on) to reload code changes
- Or restart Blender to see `bl_info` updates
- The symlink allows instant code updates without reinstalling

### If You Need to Test the Package Locally:

**Option 1: Use Different Blender Version**
- Install in Blender 4.2, 4.3, or other versions
- Keep 4.4 pristine with symlink

**Option 2: Use Portable Blender**
- Download portable Blender
- Test installation there
- Won't affect dev environment

**Option 3: Virtual Machine**
- Test in VM or Docker
- Safest for distribution testing

## 🔍 Quick Symlink Health Check

Before and after packaging, run this diagnostic:

```powershell
# Quick check script
$path = "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine"
$item = Get-Item $path -ErrorAction SilentlyContinue

if ($item.LinkType -eq "SymbolicLink") {
    Write-Host "✅ SYMLINK OK - Target: $($item.Target)" -ForegroundColor Green
} elseif ($item) {
    Write-Host "❌ SYMLINK BROKEN - Regular folder detected" -ForegroundColor Red
    Write-Host "Run the restoration steps in SYMLINK_DEV_WORKFLOW.md"
} else {
    Write-Host "❌ FOLDER MISSING - Symlink needs creation" -ForegroundColor Red
}
```

## 📁 File Locations Reference

| Purpose | Path |
|---------|------|
| **Development Source** | `C:\Coding\STYLEENGINE\scripts\addons\styleengine\` |
| **Blender 4.4 Dev Install** | `C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine` (SYMLINK) |
| **Packaged ZIP** | `C:\Coding\STYLEENGINE\scripts\addons\packaging\styleengine.zip` |

## 🚨 Emergency Recovery

If everything breaks and you need to start fresh:

1. Uninstall addon from Blender preferences
2. Delete any `styleengine*` folders in Blender's addon directory
3. Recreate symlink using Step 3 above
4. Restart Blender
5. Addon will load from development folder via symlink

## Notes for Future Agents

- The symlink is **intentional and required** for the development workflow
- The developer edits code in Cursor at `C:\Coding\STYLEENGINE\`
- Changes must sync instantly to Blender without reinstalling
- Blender 4.4 is a **dedicated development environment**
- Production testing should use other Blender installations
- **NEVER install packages in the dev environment** - it breaks the symlink

---

**Last Updated**: 2025-12-01  
**Blender Version**: 4.4 (Development Install)  
**Development Folder**: `C:\Coding\STYLEENGINE\scripts\addons\styleengine\`

