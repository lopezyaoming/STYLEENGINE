# UI Simplification - Reference Images Section

## Date: January 27, 2026

## Changes Made

### 1. Hidden "Transfer" Category (SST1-SST5)
**Reason:** Too aggressive, does not produce great results, not used by artists in studio.

**Action:** Commented out the Transfer section in `ui_panel.py` (lines 2240-2250).

**Code preserved:** All Transfer properties (sst1_image, sst1_weight, etc.) remain functional. Only UI is hidden. Can be re-enabled by uncommenting.

### 2. Added "Advanced Control" Toggle
**Location:** Top of "Reference Images" section in N-panel.

**Purpose:** Controls visibility of individual weight sliders for reference images.

**Default:** OFF (individual sliders hidden, weights default to 1.0)

**When ON:** Shows individual weight slider (0.0-2.0) for each loaded reference image.

### 3. Conditional Individual Weight Sliders
**Before:** Every image slot always showed a weight slider.

**After:** Weight sliders only visible when "Advanced Control" is enabled.

**Benefit:** Cleaner UI for 90% of users who don't need per-image weight adjustment.

---

## Visual Comparison

### BEFORE (Old UI):
```
Reference Images
▼ Style
  Global Strength: [████---] 0.5
  ┌────┐ ┌────┐ ┌────┐
  │ST1 │ │ST2 │ │ST3 │
  │img │ │img │ │img │
  │[weight slider]│ │[weight slider]│ ...
  └────┘ └────┘ └────┘
▶ Composition
▶ Transfer           ← NOW HIDDEN
```

### AFTER (New UI - Default):
```
Reference Images
[Advanced Control] ← Toggle OFF by default

▼ Style
  Global Strength: [████---] 0.5
  ┌────┐ ┌────┐ ┌────┐
  │ST1 │ │ST2 │ │ST3 │
  │img │ │img │ │img │
  │[buttons]│ │[buttons]│ ...   ← NO weight sliders
  └────┘ └────┘ └────┘
▶ Composition
                     ← Transfer section HIDDEN
```

### AFTER (Advanced Control ON):
```
Reference Images
[✓ Advanced Control] ← Toggle ON

▼ Style
  Global Strength: [████---] 0.5
  ┌────┐ ┌────┐ ┌────┐
  │ST1 │ │ST2 │ │ST3 │
  │img │ │img │ │img │
  │[weight slider]│ ...   ← Weight sliders VISIBLE
  │[buttons]│ ...
  └────┘ └────┘ └────┘
▶ Composition
```

---

## Technical Details

### New Property Added:
```python
show_advanced_ref_controls: bpy.props.BoolProperty(
    name="Advanced Control",
    description="Show individual weight sliders for each reference image (default: all weights = 1.0)",
    default=False
)
```

### Modified Function Signature:
```python
def draw_reference_section(box, title, icon, show_prop, slots, strength_prop, show_weights=False):
```

### Modified Function Calls:
```python
draw_reference_section(ref_box, "Style", 'BRUSH_DATA', 
                     "show_style_transfer", st_slots, "style_transfer_strength",
                     show_weights=style_props.show_advanced_ref_controls)
```

---

## Files Modified
- `scripts/addons/styleengine/ui_panel.py`
  - Added `show_advanced_ref_controls` property (line 549-554)
  - Added Advanced Control toggle in UI (line 2094-2096)
  - Modified `draw_reference_section` function signature (line 2099)
  - Conditional weight slider display (line 2192-2195)
  - Commented out Transfer section (line 2240-2250)

---

## Rollback Instructions

To re-enable Transfer section:
1. Uncomment lines 2241-2250 in `ui_panel.py`

To always show weight sliders:
1. Remove the `if show_weights:` condition (line 2193)
2. Or set `show_advanced_ref_controls` default to `True`

---

## Benefits

1. **Cleaner UI** - 5 fewer collapsible sections (Transfer hidden)
2. **Less clutter** - No weight sliders by default
3. **Easier onboarding** - New users see simpler interface
4. **Power users not blocked** - Advanced Control toggle exposes all controls
5. **No functionality lost** - All properties remain functional

---

---

## Additional Change: Global Strength Remapping

### 4. Remapped Global Strength Sliders

**UI Range:**
- **Before:** 0.0 to 5.0
- **After:** 0.0 to 1.0

**Workflow Range (Behind the Scenes):**
- Values multiplied by 1.5 when sent to ComfyUI
- UI 0.5 → Workflow 0.75
- UI 1.0 → Workflow 1.5

**Rationale:**
- 0-1 scale is more intuitive (standard for strength/opacity)
- Old 5.0 max was unnecessarily high
- Most users work in 0.0-1.0 range anyway
- Cleaner UX with normalized scale

**Technical:**
- Property max changed from 5.0 to 1.0
- Session JSON writing applies 1.5x multiplier
- Workflow receives scaled value automatically

See: `GLOBAL_STRENGTH_REMAPPING.md` for full details

---

## Status: ✅ Complete
