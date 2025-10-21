# Bug Fix - Workspace Creation

## Issue

**Error**: `AttributeError: bpy_prop_collection: attribute "new" not found`

**Location**: `workspace_setup.py`, line 168

**Problem**: Attempted to use `bpy.data.workspaces.new("AI")` which doesn't exist in Blender's Python API. Workspaces cannot be created directly through the data API.

## Solution

Changed the workspace creation method to use `bpy.ops.workspace.duplicate()` instead.

### Before (Incorrect)

```python
def create_ai_workspace(self, context):
    if "AI" in bpy.data.workspaces:
        return bpy.data.workspaces["AI"]
    
    ai_workspace = bpy.data.workspaces.new("AI")  # ❌ This doesn't exist
    return ai_workspace
```

### After (Correct)

```python
def create_ai_workspace(self, context):
    if "AI" in bpy.data.workspaces:
        return bpy.data.workspaces["AI"]
    
    # Get Layout workspace or current one
    layout_workspace = bpy.data.workspaces.get("Layout")
    if not layout_workspace:
        layout_workspace = context.workspace
    
    # Switch to it and duplicate
    context.window.workspace = layout_workspace
    bpy.ops.workspace.duplicate()
    
    # Rename the duplicated workspace
    duplicated_workspace = context.workspace
    duplicated_workspace.name = "AI"
    
    return duplicated_workspace
```

## How It Works Now

1. Check if "AI" workspace already exists (avoid duplicates)
2. Find the "Layout" workspace to use as template
3. Switch to that workspace
4. Use `bpy.ops.workspace.duplicate()` to create a copy
5. Rename the copy to "AI"
6. Return the new workspace

## Why This Approach

- **Blender's API Design**: Workspaces are complex objects that can't be created from scratch
- **Duplication Method**: Standard approach in Blender to create new workspaces
- **Template**: Uses "Layout" workspace as a base, which has a sensible default 3D view
- **Fallback**: If "Layout" doesn't exist, uses the current workspace

## Testing

After this fix:
1. Click "Setup Workspace" button
2. ✅ Should create "AI" workspace successfully
3. ✅ Should duplicate and rename properly
4. ✅ Should switch to new workspace
5. ✅ Should split into dual viewports

## Technical Notes

### Blender Workspace API Limitations

- **No `new()` method**: Unlike other Blender data types (objects, materials, etc.)
- **Creation methods**: 
  - `bpy.ops.workspace.duplicate()` - Duplicate current workspace
  - `bpy.ops.workspace.append_activate()` - Append from another .blend file
- **Naming**: Can be changed after creation with `.name` property

### Alternative Approaches Considered

1. **Append from template file** ❌ Requires external .blend file
2. **Modify current workspace** ❌ Would affect user's existing setup
3. **Duplicate and rename** ✅ Clean, no external dependencies

## Status

✅ **Fixed** - Workspace creation now works correctly

## Files Modified

- `scripts/addons/styleengine/workspace_setup.py` (lines 160-187)

---

**Date**: Current session  
**Status**: Resolved  
**Impact**: Critical (blocked main feature)  
**Solution**: Changed API method for workspace creation

