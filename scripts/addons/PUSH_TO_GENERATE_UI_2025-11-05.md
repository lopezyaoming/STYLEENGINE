# Push-to-Generate UI Update

**Date:** 2025-11-05  
**Type:** Surgical UI-only change (minimal, non-invasive)  
**Status:** ✅ IMPLEMENTED

---

## The Problem (Ian's Feedback)

> "One thing that jumped out at me when I was using this for even a few seconds was this feeling of wanting to control when the ai made a generation with a hotkey. With the delay, there are all these micro lags within blender while the tool runs in the background that I felt myself wanting it to pause so i could work without interruption."
> 
> — Ian Hubert

**Core Issue:** Auto-generation creates workflow interruptions during modeling.  
**Solution:** Make manual "push-to-generate" the primary workflow, auto-generation secondary.

---

## The Solution: Surgical UI Reordering

**Before:**
- Single large toggle: "Generate Images" (plural) - continuous auto-generation

**After:**
1. **Large button (top):** "Generate Image" (singular) - one-shot generation
2. **Smaller toggle (below):** "Autogenerate" - continuous generation

---

## Changes Made

### 1. Side Panel UI (`ui_panel.py`)

**Lines 1151-1162:**

```python
# Generate Image - ONE-SHOT BUTTON (large, on top)
gen_row = gen_box.row()
gen_row.scale_y = 2.5  # Make it BIG
gen_row.operator("style_engine.generate_ai_quick", text="Generate Image", icon='IMAGE_DATA')

# Autogenerate - CONTINUOUS TOGGLE (smaller, below)
gen_row = gen_box.row()
gen_row.scale_y = 1.5  # Smaller than main button
gen_row.prop(style_props, "auto_generate", text="Autogenerate", icon='FILE_REFRESH', toggle=True)
```

**Changes:**
- ✅ Reordered buttons (one-shot first, auto second)
- ✅ Renamed "Generate Images" → "Generate Image" (singular)
- ✅ Renamed toggle → "Autogenerate"
- ✅ Changed icon to `FILE_REFRESH` (recycle/circular icon)
- ✅ Made autogenerate smaller (1.5x vs 2.5x)

---

### 2. Z Pie Menu (`heavypoly_integration.py`)

**Lines 88-102:**

```python
# 1. Generate Image - ONE-SHOT (large, on top)
row = col.row(align=True)
row.scale_y = 2.0  # Large button
row.operator("style_engine.generate_ai_quick", 
            text="Generate Image", 
            icon='IMAGE_DATA')

# 2. Autogenerate - CONTINUOUS TOGGLE (smaller, below)
if style_props:
    row = col.row(align=True)
    row.scale_y = 1.2  # Smaller than main button
    row.prop(style_props, "auto_generate", 
            text="Autogenerate", 
            icon='FILE_REFRESH', 
            toggle=True)
```

**Changes:**
- ✅ Removed "Render AI" button (not needed in pie)
- ✅ Removed "Setup AI" button (keeps pie clean)
- ✅ Matches side panel order and naming exactly
- ✅ Same icons and relative sizes

---

### 3. Property Name (`ui_panel.py`)

**Line 186:**

```python
auto_generate: bpy.props.BoolProperty(
    name="Autogenerate",  # Changed from "Generate Images"
    description="Toggle continuous AI generation ON/OFF...",
    default=False,
    update=update_auto_generate
)
```

---

## User Workflow

### New Primary Workflow: "Push-to-Generate"

1. **Model/sculpt freely** (no auto-generation, no interruptions)
2. **Ready for AI?** Click "Generate Image" button
3. **AI processes** in background
4. **Result appears** when ready
5. **Repeat** when ready for next iteration

### Secondary Workflow: "Autogenerate"

1. Toggle "Autogenerate" ON
2. Continuous generation cycles
3. Toggle OFF when you need to work uninterrupted

---

## Visual Changes

### Side Panel (View3D > Sidebar > Style Engine)

```
┌─────────────────────────────┐
│  Image Generation           │
├─────────────────────────────┤
│                             │
│  ┌─────────────────────┐   │
│  │  Generate Image     │   │  ← Large, primary
│  │  🖼️                  │   │
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │ 🔄 Autogenerate     │   │  ← Smaller, secondary
│  └─────────────────────┘   │
│                             │
└─────────────────────────────┘
```

### Z Pie Menu (HeavyPoly)

```
           NORTH
             │
             │
WEST ────────┼──────── EAST
             │           │
             │           ├─ Generate Image  (large)
             │           │
          SOUTH          └─ Autogenerate    (small)
```

---

## Technical Details

### What `generate_ai_quick` Does

From `heavypoly_integration.py`:

```python
def execute(self, context):
    # 1. Render combined pass (Workbench - fast!)
    workspace_setup.render_passes(context)
    
    # 2. Trigger cloud generation
    bpy.ops.style_engine.generate_ai_image_cloud()
    
    # 3. Done!
    return {'FINISHED'}
```

**It's a complete one-shot workflow:**
- Renders from current camera
- Uploads to RunComfy
- Starts AI generation
- Returns immediately (non-blocking)

---

## Why This Works

### Ian's Concerns Addressed:

1. ✅ **"Control when AI generates"** - Manual button is now primary
2. ✅ **"Micro lags during work"** - Autogenerate is OFF by default, opt-in
3. ✅ **"Pause to work"** - Just don't click the button (or toggle OFF)
4. ✅ **"Simple as possible"** - One button, one click, done

### Design Principles:

- ✅ **Primary action first** - Manual generation is the hero
- ✅ **Secondary action smaller** - Auto-generation is a power feature
- ✅ **Clear naming** - "Generate Image" (singular) = one shot
- ✅ **Visual hierarchy** - Size indicates importance
- ✅ **Icon clarity** - FILE_REFRESH = continuous/cycling

---

## Testing Checklist

### Side Panel:
- [ ] "Generate Image" button is large (2.5x height)
- [ ] "Generate Image" button has IMAGE_DATA icon
- [ ] "Autogenerate" toggle is below, smaller (1.5x height)
- [ ] "Autogenerate" toggle has FILE_REFRESH icon
- [ ] Clicking "Generate Image" triggers one generation
- [ ] Toggling "Autogenerate" ON starts continuous cycles
- [ ] Toggling "Autogenerate" OFF stops cycles

### Z Pie Menu (with HeavyPoly):
- [ ] Press Z → Right side shows Style Engine options
- [ ] "Generate Image" appears first (large)
- [ ] "Autogenerate" appears second (smaller)
- [ ] Same icons and naming as side panel
- [ ] Behavior matches side panel exactly

---

## Files Changed

| File | Lines | Changes |
|------|-------|---------|
| `ui_panel.py` | 1151-1162, 186 | Button reordering, property rename |
| `heavypoly_integration.py` | 68-102 | Pie menu update to match panel |

**Total changes:** ~30 lines (surgical, minimal)

---

## Backward Compatibility

✅ **No breaking changes:**
- Property name changed (UI only, not breaking)
- Operators unchanged
- Functionality unchanged
- Default behavior unchanged (auto-generate OFF by default)

---

## Credits

**Feedback:** Ian Hubert  
**Implementation:** Surgical UI-only solution  
**Design:** Push-to-generate as primary workflow

---

**TLDR:** Reordered buttons to make manual "Generate Image" the primary action (large, on top), with "Autogenerate" as a smaller secondary toggle. Matches in both side panel and Z pie menu. Zero workflow breaks, minimal code changes. ✅

