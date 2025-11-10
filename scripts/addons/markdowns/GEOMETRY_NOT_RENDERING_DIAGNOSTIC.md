# Geometry Not Rendering - Diagnostic Version

## Problem Report
User reports: "The outputs I'm getting are definitely not influenced by the geometry in my scene."

This suggests the AI is generating images, but they don't reflect the actual 3D geometry in Blender.

## Potential Root Causes

### 1. ❌ Incorrect Viewport Shading Modifications (FIXED)
**Issue**: The code was modifying `scene.display.shading` (viewport shading), which has **no effect** on `bpy.ops.render.render()`.

```python
# WRONG - This affects VIEWPORT only, not renders:
workbench = scene.display.shading
workbench.show_shadows = False
```

**Fix**: Removed these incorrect viewport shading modifications. Workbench render engine uses different settings.

### 2. 🔍 Cached File Issue (DIAGNOSTIC ADDED)
**Issue**: If the render fails silently, we might be encoding and sending an **old cached `combined0001.png`** from a previous run.

**Fix**: 
- Now **deletes old file** before rendering to force fresh output
- Checks file **modification timestamp** after render
- Warns if file is older than 10 seconds

### 3. 🔍 Hidden Objects (DIAGNOSTIC ADDED)
**Issue**: Objects might be hidden from render (`hide_render = True`), causing empty renders.

**Fix**: 
- Counts visible mesh objects before rendering
- Warns if no visible objects found
- Prints total vs visible object count

### 4. 🔍 Silent Render Failure (DIAGNOSTIC ADDED)
**Issue**: `bpy.ops.render.render()` might fail without error, leaving no output file.

**Fix**: 
- Checks if output file exists after render
- Lists all files in temp directory if output missing
- Reports render duration to detect hangs

## Diagnostic Output

When you run this version, you'll see detailed output like:

### ✅ **Good Output** (Everything Working):
```
[Style Engine] Deleted old combined pass to force fresh render
[Style Engine] 🔍 Scene has 5 visible mesh objects for rendering
[Style Engine] 🎨 Rendering from ai_camera (Workbench)...
[Style Engine] Render took 0.35s
[Style Engine] ✓ Combined pass: combined0001.png (fresh, 0.2s old, 524288 bytes)
```

### ⚠️ **Bad Output** (No Geometry):
```
[Style Engine] 🔍 Scene has 0 visible mesh objects for rendering
[Style Engine] ⚠️ WARNING: No visible mesh objects! Render will be empty!
[Style Engine] Total objects: 5
[Style Engine] Check: Are objects hidden from render? (hide_render property)
```

### ❌ **Bad Output** (Cached File):
```
[Style Engine] 🔍 Scene has 5 visible mesh objects for rendering
[Style Engine] 🎨 Rendering from ai_camera (Workbench)...
[Style Engine] Render took 0.01s
[Style Engine] ⚠️ WARNING: combined0001.png is 45.3s old - may be cached!
```

### ❌ **Bad Output** (Render Failed):
```
[Style Engine] 🎨 Rendering from ai_camera (Workbench)...
[Style Engine] Render took 0.02s
[Style Engine] ❌ ERROR: Combined pass not found at combined0001.png
[Style Engine] Render may have failed silently!
[Style Engine] Files in temp dir: ['session.json', 'current_ai.png']
```

## How to Use This Diagnostic Version

1. **Install** the new packaged addon
2. **Run "Setup Workspace"** to create the AI camera
3. **Toggle "Generate Images" ON** to start a generation cycle
4. **Watch the Blender console** (Window → Toggle System Console on Windows)
5. **Look for the diagnostic messages** listed above

## Expected Findings

Based on the diagnostic output, you'll know exactly what's wrong:

| Console Message | Diagnosis | Solution |
|----------------|-----------|----------|
| "0 visible mesh objects" | Objects hidden from render | Check object visibility settings |
| "combined0001.png is X.Xs old" | Using cached file | Check render output path |
| "Combined pass not found" | Render failing | Check Blender console for errors |
| "Render took 0.01s" | Suspiciously fast = failed | Check scene/camera setup |
| "Render took 0.3-1.0s" + "fresh" | Working correctly! | Issue elsewhere in pipeline |

## Next Steps

**After running the diagnostic:**

1. **Share the console output** with me
2. I'll identify the exact issue
3. We'll implement the permanent fix

## Technical Details

### What Changed:
1. Removed incorrect `scene.display.shading` modifications
2. Added `os.remove()` to delete old render before creating new
3. Added visible object count check
4. Added file timestamp verification
5. Added render duration logging
6. Added temp directory file listing on failure

### Why This Works:
- **Forced fresh render**: Deleting old file ensures we're not using cache
- **Visibility check**: Catches hidden objects before wasting time rendering
- **Timestamp check**: Verifies the file was just created, not reused
- **Duration check**: Fast renders (< 0.1s) indicate failure
- **File listing**: Shows what's actually in the directory

---

**Status**: ✅ Diagnostic version packaged and ready
**Action Required**: Run addon and share console output

