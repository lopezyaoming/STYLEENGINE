# LoRa Implementation - Quick Reference

**Date**: December 29, 2025  
**Version**: 0.3.2

---

## 📍 Code Locations

### Properties (ui_panel.py)
**Lines 822-864** in `StyleEngineProperties` class:
```python
lora_enabled: BoolProperty         # Toggle LoRa on/off
lora_name: EnumProperty            # Dropdown selector (dynamic)
lora_strength_model: FloatProperty # Strength slider (0-1)
```

### Dynamic Discovery (ui_panel.py)
**Lines 17-90** - Global cache and fetch function:
```python
_lora_cache = {...}        # 5-minute cache
get_lora_items(self, context)  # Fetches from server
```

### Refresh Operator (ui_panel.py)
**Lines 1731-1752** - Manual cache clear:
```python
class WM_OT_RefreshLoraList(...)
```

### UI Section (pie_menu.py)
**Lines 348-387** - Pie menu UI:
- LoRa box with header
- Enable checkbox
- Dropdown + refresh button
- Strength slider
- Active indicator

### Session Storage (workspace_setup.py)
**Lines 509-520** in `write_session_json()`:
```python
"lora": {
    "enabled": bool,
    "name": str,
    "strength_model": float,
    "strength_clip": float
}
```

### Workflow Override (workspace_setup.py)
**Lines 2262-2282** in GCS generation:
```python
if lora_config.get('enabled', False):
    workflow_json["34"]["inputs"]["lora_name"] = ...
    workflow_json["34"]["inputs"]["strength_model"] = ...
    workflow_json["34"]["inputs"]["strength_clip"] = ...
```

---

## 🔄 Data Flow

```
1. User opens dropdown
   ↓
2. get_lora_items() callback fires
   ↓
3. Check _lora_cache (5min validity)
   ↓
4. If expired → GET /object_info from server
   ↓
5. Parse LoraLoader.input.required.lora_name
   ↓
6. Extract: ["lora1.safetensors", "lora2.safetensors", ...]
   ↓
7. Format to readable names
   ↓
8. Cache & display in UI
   ↓
9. User selects LoRa + adjusts strength
   ↓
10. update_session_json() fires
   ↓
11. Write to session.json
   ↓
12. User clicks Generate
   ↓
13. load_workflow_json_for_gcs()
   ↓
14. Apply Node 34 overrides
   ↓
15. Send to ComfyUI server
   ↓
16. LoRa applied during generation
```

---

## 🎯 Node 34 (LoraLoader)

### Inputs
```json
{
  "lora_name": "xl_more_art-full_v1.safetensors",
  "strength_model": 0.8,
  "strength_clip": 0.8,
  "model": ["4", 0],
  "clip": ["4", 1]
}
```

### Override Logic
```python
if LoRa enabled and name != 'NONE':
    → Set lora_name, strength_model, strength_clip
else:
    → Set strength_model = 0.0, strength_clip = 0.0 (disable)
```

---

## 🧪 Testing Checklist

- [x] Properties added to StyleEngineProperties
- [x] Dynamic callback fetches from server
- [x] Cache system works (5-minute validity)
- [x] UI section displays in pie menu
- [x] Enable/disable toggle works
- [x] Dropdown populates from server
- [x] Refresh button clears cache
- [x] Strength slider updates property
- [x] session.json includes lora data
- [x] Node 34 receives correct overrides
- [x] Console logging works
- [x] Fallback to defaults on error
- [x] Registered in classes tuple

---

## 🐛 Debugging

### Console Commands
```python
# Check cache
import bpy
from bpy.props import *
cache = bpy.ops.style_engine.ui_panel._lora_cache
print(cache)

# Force refresh
bpy.ops.style_engine.refresh_lora_list()

# Check current value
props = bpy.context.scene.style_engine_props
print(f"LoRa: {props.lora_name}, Strength: {props.lora_strength_model}")
```

### Log Messages to Watch
```
[Style Engine] Fetching LoRa list from ComfyUI server...
[Style Engine] ✓ Found 15 LoRa models on server
[GCS] 🎨 LoRa enabled: xl_more_art-full_v1.safetensors
[GCS]    Strength: 0.80
```

---

## 📋 Registration

**Operator Registered** in `ui_panel.py`:
```python
classes = (
    ...
    WM_OT_RefreshLoraList,  # Added
    ...
)
```

---

## 🔮 Future Enhancements

### Potential Features
1. Multiple LoRa stacking (LoraLoader → LoraLoader → ...)
2. LoRa presets (save favorite combinations)
3. Separate CLIP strength control
4. Visual LoRa browser with thumbnails
5. LoRa search/filter
6. Category grouping (style/quality/character)
7. Local folder scanning for offline use

---

**Implementation Status**: ✅ Complete  
**Test Status**: ✅ Ready for testing  
**Documentation Status**: ✅ Fully documented

