# Project Texture Path Fix - November 5, 2025

## Problem
"Project Texture" button was failing with error:
```
AI image not found at C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\data\temp\ai_vision\current_ai.png
```

## Root Cause

The `WM_OT_ProjectTexture` operator was **hardcoding the path** to the AI image:

```python
# WRONG (hardcoded):
addon_root = Path(__file__).parent.parent.parent.parent
img_path = addon_root / "data" / "temp" / "ai_vision" / "current_ai.png"
```

This assumed:
1. Addon installed relative to a "data" folder
2. Fixed directory structure
3. Ignored Blender's actual file location

**But the temp directory is actually dynamic!** It depends on:
1. Whether .blend file is saved (uses relative path)
2. User's output_path setting
3. System temp directory as fallback

## The Fix

Use the `get_temp_directory()` function like all other operators:

```python
# CORRECT (dynamic):
from . import workspace_setup
temp_dir = workspace_setup.get_temp_directory(context)
img_path = temp_dir / "current_ai.png"
```

This ensures the path matches where images are actually stored.

## How get_temp_directory() Works

Priority order:

### 1. Relative to .blend file (if saved)
```python
if bpy.data.is_saved:
    blend_dir = Path(bpy.path.abspath("//"))
    temp_dir = blend_dir / "temp" / "ai_vision"
```
Example: `C:\Projects\MyProject\temp\ai_vision\`

### 2. User's output_path setting
```python
if props.output_path:
    temp_dir = Path(props.output_path) / "temp" / "ai_vision"
```
Example: Custom location set in preferences

### 3. System temp directory (fallback)
```python
import tempfile
temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "ai_vision"
```
Example: `C:\Users\Juan\AppData\Local\Temp\blender_styleengine\ai_vision\`

## Why This Matters

Different users have different setups:
- **Saved .blend files**: Images relative to project
- **Unsaved files**: System temp directory
- **Custom output path**: User's preferred location

Hardcoding breaks all but one scenario!

## Files Affected

**Before**: Only `current_ai.png` lookup was broken
**After**: All path resolution uses `get_temp_directory()`

## Other Operators Using Correct Path

These already used `get_temp_directory()` correctly:
- ✅ `setup_workspace()` - creates temp directory
- ✅ `render_passes()` - saves render output
- ✅ `generate_ai_image_cloud()` - reads render, writes AI output
- ✅ `on_generation_complete()` - downloads AI image
- ✅ `refresh_ai_image()` - reloads AI image

Only `project_texture()` was hardcoded - now fixed!

## Console Output

You'll see the correct path in console:

**Before (wrong)**:
```
[Style Engine] Looking for image at: C:\...\Blender\4.4\data\temp\ai_vision\current_ai.png
AI image not found
```

**After (correct)**:
```
[Style Engine] Looking for AI image at: C:\Users\Juan\AppData\Local\Temp\blender_styleengine\ai_vision\current_ai.png
[Style Engine] Found image, loading for projection...
```

## Testing

To verify the fix:
1. Run "Setup Workspace"
2. Generate at least one AI image
3. Click "Project Texture"
4. Should succeed without "not found" error ✅

## Technical Details

### Why Hardcoded Path Failed:

The hardcoded path tried to go "up" from the addon directory:
```
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine\ui_panel.py
↑ parent
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\styleengine\
↑ parent  
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\addons\
↑ parent
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\scripts\
↑ parent (expected "data" here but it's in a different branch!)
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\
```

Then tried to find:
```
C:\Users\Juan\AppData\Roaming\Blender Foundation\Blender\4.4\data\temp\ai_vision\current_ai.png
```

But "data" doesn't exist in that path!

### Correct Approach:

Ask Blender/addon logic where the temp directory actually is:
```python
temp_dir = get_temp_directory(context)  # Returns actual location
img_path = temp_dir / "current_ai.png"  # Build path from there
```

## Related Issues

This same pattern should be used for:
- ✅ All temp file access
- ✅ All render output access
- ✅ All AI image access

**Never hardcode paths!** Always use `get_temp_directory()`.

---

**Status**: ✅ Fixed and packaged
**Impact**: Critical for "Project Texture" feature
**Breaking**: No - fix makes it work correctly
**Testing**: Verified path resolution logic

