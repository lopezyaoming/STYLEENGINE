# HeavyPoly Prompt Below Camera Feature

**Date:** 2025-11-05  
**Type:** Layout Enhancement (HeavyPoly Mode)  
**Status:** ✅ IMPLEMENTED

---

## The Request

> "In the HEAVYPOLY version, the bottom heavypoly text should be left alone, but our text should appear just on the bottom of the AI_CAMERA window as a new space. Let's leave heavypolys text as it is, and let's just add that. It just makes a lot more sense when you see the text right behind the image."
> 
> — Juan

---

## The Problem

**Before:**
- Style Engine hijacked HeavyPoly's existing text editor
- Prompt was in a separate location (not visually connected to AI output)
- HeavyPoly's text editor was overwritten with our prompt

**Issues:**
- ❌ HeavyPoly's text editor was lost
- ❌ Prompt felt disconnected from AI camera view
- ❌ Less intuitive workflow

---

## The Solution

**After:**
1. Find Image Editor → Convert to AI camera (3D View)
2. **Split camera area horizontally** (70% camera / 30% prompt)
3. Add Text Editor **directly below AI camera** with Style Engine prompt
4. **Leave HeavyPoly's original text editor untouched**

---

## Layout Comparison

### Before (Old Hijack)

```
┌─────────────────┬──────────┐
│                 │          │
│   AI Camera     │ HeavyPoly│
│   (Image Editor │ UI       │
│    converted)   │          │
│                 │          │
├─────────────────┴──────────┤
│ Style Engine Prompt        │  ← HIJACKED HeavyPoly text
│ (OVERWROTE HeavyPoly text) │
└────────────────────────────┘
```

**Problem:** HeavyPoly's text was lost!

---

### After (New Split Layout)

```
┌─────────────────┬──────────┐
│                 │          │
│   AI Camera     │ HeavyPoly│
│   (80% height)  │ UI       │
│                 │          │
├─────────────────┤          │
│ SE Prompt (20%) │          │
├─────────────────┴──────────┤
│ HeavyPoly Text             │  ← UNTOUCHED!
│ (Original preserved)       │
└────────────────────────────┘
```

**Benefits:**
- ✅ Prompt is **directly below** AI camera (visual proximity)
- ✅ HeavyPoly's text editor is **preserved**
- ✅ More intuitive workflow

---

## Implementation

### File: `workspace_setup.py`

**Function:** `_hijack_heavypoly_areas_standalone(screen, camera)`

### Changes:

#### STEP 1: Convert Image Editor to Camera View (Unchanged)
```python
# Find Image Editor
if area.type == 'IMAGE_EDITOR':
    # Change to 3D View
    area.type = 'VIEW_3D'
    
    # Lock to camera
    space.region_3d.view_perspective = 'CAMERA'
    space.camera = camera
    space.region_3d.view_camera_zoom = 0  # Auto-fit
```

#### STEP 2: Split Camera Area Horizontally (NEW!)
```python
# Split the camera area horizontally
with context.temp_override(area=camera_area, region=camera_area.regions[-1]):
    result = bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.8)
```

**Split ratio:** 80% camera / 20% prompt

**Timing fix:** Uses `bpy.app.timers.register()` with 0.1s delay to find and configure the bottom area after Blender processes the split

#### STEP 3: Add Text Editor Below (NEW!)
```python
# Find the newly created bottom area
for area in screen.areas:
    if area.type == 'VIEW_3D' and area.x == camera_x and area.y < camera_y:
        bottom_area = area
        break

# Convert to Text Editor
bottom_area.type = 'TEXT_EDITOR'

# Load our prompt
prompt_text = utils.get_or_create_prompt_text()
space.text = prompt_text
```

#### STEP 4: Leave HeavyPoly's Text Untouched (REMOVED!)
```python
# ❌ OLD CODE (REMOVED):
# elif area.type == 'TEXT_EDITOR':
#     space.text = prompt_text  # This hijacked HeavyPoly's text

# ✅ NEW BEHAVIOR: Don't touch existing text editors at all
```

---

## Technical Details

### Area Split Operation

**Direction:** `HORIZONTAL` (top/bottom split)  
**Factor:** `0.7` (70% top, 30% bottom)

```python
bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.7)
```

**Why 80/20?**
- Camera needs majority of space for AI output viewing
- 20% is enough for prompt text (usually 1-3 lines)
- Keeps prompt compact but readable

### Area Detection

After split, we need to find the newly created bottom area:

```python
# Original camera area position
camera_x = camera_area.x
camera_y = camera_area.y

# Find new area: Same X, lower Y, same type (VIEW_3D initially)
for area in screen.areas:
    if area.type == 'VIEW_3D' and area.x == camera_x and area.y < camera_y:
        bottom_area = area  # This is the new split!
```

**Key insight:** After horizontal split, the new area has:
- Same X position
- Lower Y position (bottom)
- Initially same type as parent (VIEW_3D)

### Timing Fix (Critical!)

**Problem:** Immediately after `bpy.ops.screen.area_split()`, the areas list isn't updated yet!

**Solution:** Use timer to delay the configuration:

```python
def delayed_prompt_setup():
    # Find and configure bottom area
    for area in screen.areas:
        if area.type == 'VIEW_3D' and area.x == camera_x and area.y < camera_y:
            bottom_area = area
            # Convert to Text Editor and load prompt
            break
    return None  # Don't repeat

# Wait 0.1 seconds for Blender to process the split
bpy.app.timers.register(delayed_prompt_setup, first_interval=0.1)
```

**Why this works:**
- Split operation completes immediately (returns `{'FINISHED'}`)
- But Blender's internal area list takes a moment to update
- Timer callback runs after Blender finishes processing
- Bottom area is now findable and configurable

---

## User Experience

### Workflow Improvements

1. **Visual Proximity**
   - AI output image **above** ⬆️
   - Prompt text **below** ⬇️
   - Connected layout = clearer workflow

2. **HeavyPoly Compatibility**
   - Original text editor preserved
   - HeavyPoly shortcuts still work
   - No workflow interruption

3. **Clean Separation**
   - AI camera: 80% (main focus)
   - Prompt: 20% (quick reference, compact)
   - HeavyPoly text: Separate (original workflow)

---

## Error Handling

### If Split Fails

```python
try:
    result = bpy.ops.screen.area_split(...)
    
    if result == {'FINISHED'}:
        # Success! Configure prompt area
        pass
    else:
        print("⚠️ Split failed")
        print("ℹ️ Prompt available in Text Editor menu")
        
except Exception as e:
    print(f"⚠️ Could not split area: {e}")
    traceback.print_exc()
```

**Fallback:** Prompt is still accessible via:
- Text Editor menu → STYLEENGINE_Prompt
- Still usable, just not in optimal location

---

## Testing Checklist

### HeavyPoly Mode (with `enable_heavypoly_compatibility` ON)

1. **Setup Workspace**
   - [ ] Click "Setup AI Workspace"
   - [ ] AI workspace created from HeavyPoly "Modeling"

2. **Layout Verification**
   - [ ] AI camera appears (top 70% of left area)
   - [ ] Style Engine prompt appears **directly below** camera (bottom 30%)
   - [ ] HeavyPoly text editor **still exists** (separate area)

3. **Functionality**
   - [ ] Can edit Style Engine prompt
   - [ ] Can still use HeavyPoly text editor
   - [ ] Both text editors work independently

4. **Visual Check**
   - [ ] Prompt is visually connected to AI output
   - [ ] Split ratio looks balanced (70/30)
   - [ ] No UI overlaps or glitches

---

## Console Output

### Successful Hijack

```
[Style Engine] 🔧 Hijacking HeavyPoly window areas...
[Style Engine]   📷 Found Image Editor at (1234, 567)
[Style Engine]   ✅ Converted to camera-locked 3D View
[Style Engine]   📝 Creating Style Engine prompt area below AI camera...
[Style Engine]   ✅ Split camera area (80% camera / 20% prompt)
[Style Engine]   ✅ Style Engine prompt loaded below AI camera
[Style Engine] 🎉 HeavyPoly workspace hijacked! (Camera + Prompt added, HeavyPoly text untouched)
```

### If Split Fails

```
[Style Engine] ⚠️  Split failed: {'CANCELLED'}
[Style Engine] ℹ️  Prompt available in Text Editor menu
```

---

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `workspace_setup.py` | 471-594 | Rewritten `_hijack_heavypoly_areas_standalone()` |

**Total changes:** ~60 lines (function rewrite)

---

## Benefits Summary

✅ **Visual Proximity:** Prompt right below AI camera  
✅ **HeavyPoly Preserved:** Original text editor untouched  
✅ **Better UX:** Clearer connection between prompt and output  
✅ **No Conflicts:** Both text editors work independently  
✅ **Graceful Fallback:** Prompt still accessible if split fails

---

## Design Philosophy

> "It just makes a lot more sense when you see the text right behind the image."

The new layout reinforces the mental model:
1. **Input** (prompt) ➡️ **Output** (AI image)
2. Visual proximity = clearer cause-and-effect
3. HeavyPoly workflow preserved = no friction

**Perfect for Ian's workflow!**

---

---

## Bug Fixes (2025-11-05)

### Issue 1: "Could not find bottom area after split"

**Problem:**
```
[Style Engine] ⚠️  Could not find bottom area after split
```

**Root cause:** Blender's area list isn't immediately updated after `area_split()`. The code was looking for the new area instantly, before Blender finished processing.

**Solution:** Added `bpy.app.timers.register()` with 0.1s delay to find and configure the bottom area **after** Blender updates the areas list.

### Issue 2: Wrong split ratio

**Problem:** Camera area was too small (70%), prompt too large (30%)

**Solution:** Changed factor from `0.7` to `0.8` → Camera now gets 80%, prompt gets 20% (more balanced for viewing AI output)

---

**TLDR:** In HeavyPoly mode, Style Engine now splits the AI camera area horizontally and adds the prompt **directly below** the camera view (80/20 split), while leaving HeavyPoly's original text editor completely untouched. Uses timer delay to ensure Blender processes the split before configuring the prompt area. Visual proximity + compatibility + proper timing = win! ✅

