# Global Strength Slider Remapping

## Date: January 27, 2026

## Overview

Remapped the global strength sliders for Style Transfer and Composition to use a more intuitive UI range (0.0-1.0) while maintaining the actual workflow range (0.0-1.5).

---

## Changes

### UI Range (What User Sees):
- **Before:** 0.0 to 5.0
- **After:** 0.0 to 1.0

### Workflow Range (What Gets Sent to ComfyUI):
- **Before:** Direct value (0.0-5.0)
- **After:** UI value × 1.5 (0.0-1.5)

### Scaling Formula:
```
workflow_value = ui_value × 1.5
```

### Examples:
| UI Value | Workflow Value |
|----------|----------------|
| 0.00     | 0.00          |
| 0.25     | 0.375         |
| 0.50     | 0.75          |
| 0.75     | 1.125         |
| 1.00     | 1.50          |

---

## Rationale

1. **More Intuitive:** 0-1 scale is standard for strength/opacity controls
2. **Better Defaults:** Most users work in 0.0-1.0 range anyway
3. **Prevents Overkill:** Old 5.0 max was unnecessarily high and caused over-aggressive styling
4. **Cleaner UX:** Normalized 0-1 scale is easier to understand

---

## Technical Implementation

### 1. Property Definition (`ui_panel.py`)

```python
style_transfer_strength: bpy.props.FloatProperty(
    name="Style Transfer Strength",
    description="Global strength for all Style Transfer images (0.0 to 1.0, scaled to 1.5 in workflow)",
    default=0.0,
    min=0.0,
    max=1.0,  # Changed from 5.0
    update=update_session_json
)

composition_strength: bpy.props.FloatProperty(
    name="Composition Strength",
    description="Global strength for all Composition images (0.0 to 1.0, scaled to 1.5 in workflow)",
    default=0.0,
    min=0.0,
    max=1.0,  # Changed from 5.0
    update=update_session_json
)
```

### 2. Session JSON Writing (`workspace_setup.py`)

```python
"reference_images": {
    # Global strengths (UI: 0.0-1.0, multiplied by 1.5 for workflow: 0.0-1.5)
    "style_transfer_strength": round(props.style_transfer_strength * 1.5, 3),
    "composition_strength": round(props.composition_strength * 1.5, 3),
    # ... rest of properties
}
```

### 3. Workflow Patching (Unchanged)

The workflow patching code remains unchanged because it reads from session.json, which already contains the scaled values:

```python
# These read scaled values from session.json
workflow_json["52"]["inputs"]["value"] = ref_images.get('style_transfer_strength', 0.0)
workflow_json["90"]["inputs"]["value"] = ref_images.get('composition_strength', 1.0)
```

---

## Files Modified

1. **`scripts/addons/styleengine/ui_panel.py`**
   - Changed `max` from 5.0 to 1.0 for both properties (lines 557-573)
   - Updated descriptions to mention scaling

2. **`scripts/addons/styleengine/workspace_setup.py`**
   - Added 1.5x multiplier when writing to session.json (lines 524-525)
   - Updated debug logging to clarify scaled values (lines 2353, 2629)

---

## User Impact

### What Users See:
- Slider now goes from 0.0 to 1.0 (instead of 0.0 to 5.0)
- More intuitive and familiar range
- Easier to find good values

### What Users Don't See:
- Behind the scenes, values are automatically multiplied by 1.5
- Workflow receives 0.0-1.5 range (optimal for IPAdapter)
- No loss of functionality or control

### Migration:
- **Old projects:** Values > 1.0 will be clamped to 1.0 on next save
  - Example: Old value 2.5 → New value 1.0 → Workflow 1.5
- **New projects:** Start with clean 0.0-1.0 range

---

## Debug Output

Console logs now clarify the scaling:

```
[GCS]   - Global Strengths (scaled 1.5x): ST=0.75, Comp=1.12, Force=0.00
```

```
🎚️ GLOBAL STRENGTHS (scaled 1.5x for workflow):
  Style Transfer Strength (Node 52): 0.75
  Composition Strength (Node 90): 1.125
  Force Transfer Strength (Node 91): 0.0
```

---

## Testing Checklist

- [x] UI slider limited to 0.0-1.0
- [x] Property stores UI value (0.0-1.0)
- [x] Session.json contains scaled value (0.0-1.5)
- [x] Workflow receives scaled value
- [x] Debug logs show scaled values
- [x] Manual entry clamped to 0.0-1.0
- [x] Old projects auto-migrate on save

---

## Related Changes

This change was made alongside:
- UI Simplification (hiding Transfer section)
- Advanced Control toggle (hiding individual weights)

Together these create a cleaner, more focused reference image UI.

---

## Status: ✅ Complete
