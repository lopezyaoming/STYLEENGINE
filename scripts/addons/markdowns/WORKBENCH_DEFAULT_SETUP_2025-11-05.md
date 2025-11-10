# Workbench Default Setup - November 5, 2025

## Feature: Scene-Wide Workbench Configuration

**New behavior**: When "Setup Workspace" runs, it now configures the **entire scene** to use Workbench rendering by default with optimized settings.

## What This Does

### Before (Temporary Switching):
```python
# During render_passes() only:
scene.render.engine = 'BLENDER_WORKBENCH'  # Temporary
# ... render ...
scene.render.engine = original_engine  # Restored after render
```

**Problem**: If user manually triggered a render (F12), it would use their original engine (EEVEE/Cycles), which:
- Takes 10-100x longer
- Can cause confusion about what's being sent to AI
- Doesn't match the optimized render path

### After (Permanent Scene Configuration):
```python
# During setup_workspace():
scene.render.engine = 'BLENDER_WORKBENCH'  # SCENE DEFAULT
scene.display.render_aa = 'OFF'
scene.render.resolution_percentage = 100
# ... other optimizations ...
```

**Benefits**: 
- ✅ Consistent rendering everywhere (F12, auto-cycles, manual tests)
- ✅ No confusion about which engine is being used
- ✅ Maximum performance by default
- ✅ Scene is "pre-configured" for Style Engine workflow

## What Gets Configured

When you click "Setup Workspace", the scene is now configured with:

### 1. Render Engine
```python
scene.render.engine = 'BLENDER_WORKBENCH'
```
Fast, real-time rendering suitable for geometry capture.

### 2. Anti-Aliasing
```python
scene.display.render_aa = 'OFF'
scene.display.viewport_aa = 'OFF'
```
Disabled for maximum speed. AI doesn't need perfect edges.

### 3. Resolution
```python
scene.render.resolution_x = 1024  # (or user's selected resolution)
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
```
Set to SDXL native resolution at 100% (no scaling).

### 4. Output Format
```python
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.compression = 15
```
PNG with alpha channel, moderate compression.

## Console Output

When you run "Setup Workspace", you'll see:

**Normal mode**:
```
[Style Engine] Scene configured: Workbench render @ 1024x1024
```

**Debug mode** (if enabled in preferences):
```
[Style Engine] ✓ Render engine: BLENDER_WORKBENCH (scene default)
[Style Engine] ✓ Anti-aliasing: OFF (fast rendering)
[Style Engine] ✓ Resolution: 1024x1024 @ 100%
[Style Engine] ✓ Output format: PNG, RGBA
```

## Why This Is Better

### Consistency
- User presses F12 → Gets Workbench render (fast, consistent with AI input)
- Auto-generation cycle → Gets Workbench render (same)
- Manual "Render Passes" → Gets Workbench render (same)

### Performance
- No expensive EEVEE/Cycles renders by accident
- Anti-aliasing disabled = faster
- 100% resolution = no confusion about scaling

### Transparency
- User can see in Blender's UI that Workbench is selected
- No "hidden" render engine switching
- Clear what's being sent to AI

## Technical Details

### Blender 4.x Display Settings

In Blender 4.2+, anti-aliasing for Workbench is controlled via:
```python
scene.display.render_aa   # Render anti-aliasing
scene.display.viewport_aa  # Viewport anti-aliasing
```

Options for `render_aa`:
- `'OFF'` - No AA (fastest) ✅ **We use this**
- `'FXAA'` - Fast approximate AA
- `'5'`, `'8'`, `'11'`, `'16'`, `'32'` - Multisample AA (slow)

### Workbench Characteristics

Workbench is ideal for Style Engine because:
1. **Fast**: ~0.1-0.3s per render (vs 5-30s for EEVEE)
2. **Simple**: Flat/solid shading, no complex materials
3. **Geometry-focused**: Shows shape/form clearly
4. **Predictable**: No lighting/shader surprises

Perfect for ControlNet depth/canny preprocessing!

## User Impact

### What Users Will Notice:
1. After "Setup Workspace", the render engine dropdown shows "Workbench"
2. Pressing F12 will be much faster than before
3. Render settings panel shows simplified Workbench options

### What Users Won't Notice:
- Everything still works the same way
- AI generations use the same fast rendering
- No functional changes to workflow

### If User Wants Different Engine:
Users can still manually switch to EEVEE/Cycles for final beauty renders. Style Engine operations will continue using Workbench internally (temporary switching during render_passes()).

## Validation

Expected behavior after "Setup Workspace":
- [x] Scene render engine set to Workbench
- [x] Anti-aliasing disabled
- [x] Resolution set to user's selected SDXL resolution
- [x] Resolution percentage = 100%
- [x] Output format = PNG with RGBA
- [x] Console shows configuration summary
- [ ] F12 render uses Workbench (user to test)
- [ ] Generation cycles remain fast (user to verify)

## Integration with Existing Code

The `render_passes()` function still does temporary switching for safety:

```python
def render_passes(context):
    # Store original
    original_engine = scene.render.engine
    
    # Force Workbench (even if user changed it)
    scene.render.engine = 'BLENDER_WORKBENCH'
    
    # ... render ...
    
    # Restore
    scene.render.engine = original_engine
```

This ensures Style Engine always uses Workbench, even if:
- User manually switched to EEVEE for a beauty render
- Another addon changed the engine
- Scene was saved with different engine

**Defense in depth**: Scene default + temporary forcing = bulletproof.

---

**Status**: ✅ Implemented and packaged
**Impact**: Medium-High - improves consistency and performance
**User-facing**: Visible (render engine dropdown changes)
**Breaking**: No - fully backward compatible

