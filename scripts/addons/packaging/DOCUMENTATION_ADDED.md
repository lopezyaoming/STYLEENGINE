# Symlink Workflow Documentation - Added 2025-12-01

## Problem Addressed

The developer uses a dedicated Blender 4.4 installation with a symlink-based development workflow. During packaging/testing, the symlink was accidentally destroyed when the packaged ZIP was installed in Blender 4.4, breaking the instant code sync between Cursor and Blender.

## Documentation Created

### 1. **SYMLINK_DEV_WORKFLOW.md** (Comprehensive Guide)
**Location**: `scripts/addons/packaging/SYMLINK_DEV_WORKFLOW.md`

**Contents**:
- Full explanation of symlink workflow
- Why symlinks break (installing ZIP overwrites them)
- Symptoms of broken symlink
- Step-by-step restoration instructions
- Best practices for agents
- Testing alternatives (other Blender versions, VMs)
- Quick diagnostic scripts
- File location reference
- Emergency recovery steps

**Target Audience**: Future AI agents and developers

### 2. **00_READ_FIRST_SYMLINK_WARNING.txt** (Quick Reference)
**Location**: `scripts/addons/packaging/00_READ_FIRST_SYMLINK_WARNING.txt`

**Contents**:
- TL;DR warning banner
- Critical do's and don'ts
- Quick restoration steps
- File named with `00_` prefix to appear first in directory listings

**Target Audience**: Quick reference for agents who need immediate guidance

### 3. **Updated README.md** (Main Documentation)
**Location**: `scripts/addons/packaging/README.md`

**Changes**:
- Added prominent warning section at top
- Links to SYMLINK_DEV_WORKFLOW.md
- Clearly states to never test in Blender 4.4

### 4. **Updated package_addon_EASY.bat** (Warning Banner)
**Location**: `scripts/addons/packaging/package_addon_EASY.bat`

**Changes**:
- Added comment block warning in REM section
- Added echo warning during execution
- Shows warning message before packaging starts

### 5. **Updated package_addon_modern.py** (Code Documentation)
**Location**: `scripts/addons/packaging/package_addon_modern.py`

**Changes**:
- Added warning section to module docstring
- References SYMLINK_DEV_WORKFLOW.md
- Visible to agents reading the code

## Key Points for Future Agents

### ✅ DO:
1. Run `package_addon_EASY.bat` to create packages
2. Test packages in Blender 4.2, 4.3, or other versions
3. Use portable Blender or VMs for testing
4. Keep Blender 4.4 pristine with symlink

### ❌ DON'T:
1. Install packaged ZIP in Blender 4.4
2. Copy files to Blender 4.4's addon folder
3. Delete or modify the symlink

## Symlink Restoration (Quick Reference)

If symlink breaks, run in PowerShell as Administrator:

```powershell
# Step 1: Remove broken folder
Remove-Item "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" -Recurse -Force

# Step 2: Recreate symlink
New-Item -ItemType SymbolicLink -Path "C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine" -Target "C:\Coding\STYLEENGINE\scripts\addons\styleengine"

# Step 3: Restart Blender
```

## File Structure

```
scripts/addons/packaging/
├── 00_READ_FIRST_SYMLINK_WARNING.txt  ← Quick TL;DR warning
├── SYMLINK_DEV_WORKFLOW.md            ← Full comprehensive guide
├── README.md                           ← Updated with warning section
├── package_addon_EASY.bat              ← Updated with warning banner
├── package_addon_modern.py             ← Updated with warning in docstring
└── DOCUMENTATION_ADDED.md              ← This file
```

## Testing Verification

✅ Symlink restored and working
✅ Version 0.3.1 showing correctly in Blender
✅ Code changes sync from Cursor to Blender
✅ Documentation comprehensive and accessible
✅ Warnings visible in multiple locations

## Future Maintenance

When updating packaging:
- Keep symlink warnings prominent
- Update SYMLINK_DEV_WORKFLOW.md if workflow changes
- Maintain warnings in all packaging scripts
- Test recovery steps periodically

---

**Date Created**: 2025-12-01  
**Developer**: Juan Jose Lopez  
**Development Environment**: Blender 4.4 with symlink to C:\Coding\STYLEENGINE  
**Purpose**: Prevent accidental symlink destruction during packaging/testing

