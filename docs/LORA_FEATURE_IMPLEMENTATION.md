# LoRa Model Selection Feature

**Version**: 0.3.2  
**Date**: December 29, 2025  
**Status**: ✅ Implemented and Tested

---

## 📋 Overview

The LoRa (Low-Rank Adaptation) feature allows users to apply LoRa models to AI generation directly from the Style Engine pie menu. LoRa models modify the base SDXL model to achieve specific artistic styles, rendering techniques, or aesthetic effects.

**Key Features:**
- 🔄 **Dynamic Discovery**: Automatically fetches available LoRa models from your ComfyUI server
- 💾 **Smart Caching**: 5-minute cache to minimize server requests
- 🎚️ **Adjustable Strength**: Fine-tune LoRa influence (0.0 to 1.0)
- 🔄 **Manual Refresh**: Button to force immediate update from server
- 🎯 **Workflow Integration**: Seamlessly applies to Node 34 (LoraLoader) in ComfyUI

---

## 🎮 User Guide

### Accessing LoRa Controls

1. **Open Style Engine Pie Menu**: `Shift+E` (default hotkey)
2. **Navigate to "Generate Image"** section (bottom/south position)
3. **Scroll down** to find the **LoRa** box
4. **Enable**: Check "Use LoRa" toggle

### UI Layout

```
┌─────────────────────────────┐
│ LoRa                 [📦]   │
├─────────────────────────────┤
│ ☑ Use LoRa                  │
│                             │
│ Model:              [📁]    │
│ [Dropdown Menu ▼] [🔄]     │
│ ┌────────────────────────┐  │
│ │ None                   │  │
│ │ Xl More Art Full       │✓ │
│ │ Add Detail Xl          │  │
│ │ Sdxlrender V2 0        │  │
│ │ Anime Pencil Concept   │  │
│ │ Pixel Art Xl V1 1      │  │
│ └────────────────────────┘  │
│                             │
│ Strength:           [💪]    │
│ [=======|===] 0.80          │
│                             │
│ ✓ Active: Xl More Art       │
└─────────────────────────────┘
```

### Using LoRa

1. **Enable LoRa**: Check the "Use LoRa" checkbox
2. **Select Model**: Click dropdown to see available LoRas (fetched from server)
3. **Adjust Strength**: Use slider to set influence (0.0 = off, 1.0 = full strength)
4. **Generate**: Create images with LoRa applied

### Refreshing LoRa List

- **Automatic**: List refreshes every 5 minutes
- **Manual**: Click the 🔄 refresh button next to the dropdown
- **On Cache Clear**: Opens dropdown after clearing cache

---

## 🔧 Technical Implementation

### Architecture

```
┌─────────────────────────────────────────────┐
│ User opens dropdown                         │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ get_lora_items() callback                   │
│ - Check 5-minute cache                      │
│ - If expired, fetch from server             │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ GET http://server:8188/object_info          │
│ - Query ComfyUI Backend API                │
│ - Parse LoraLoader node definition          │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Extract: LoraLoader.input.required.lora_name│
│ Returns: ["lora1.safetensors", ...]        │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Transform to UI items                       │
│ - Convert to readable names                 │
│ - Cache for 5 minutes                       │
│ - Display in dropdown                       │
└─────────────────────────────────────────────┘
```

### Data Flow

```
UI Property → session.json → Workflow Override → ComfyUI Node 34
```

1. **User Selection**: `lora_name` property in `StyleEngineProperties`
2. **Session Storage**: Written to `session.json` under `lora` section
3. **Workflow Integration**: Applied to Node 34 inputs in `StyleEngine.json`
4. **Generation**: ComfyUI applies LoRa during image generation

---

## 📝 Code Structure

### Files Modified

#### 1. `ui_panel.py` (Lines 17-90, 822-864, 1731-1752)

**Added Components:**
- `_lora_cache`: Global cache dictionary
- `get_lora_items()`: Dynamic callback function
- `lora_enabled`: Boolean property
- `lora_name`: EnumProperty with callback
- `lora_strength_model`: Float property
- `WM_OT_RefreshLoraList`: Refresh operator

**Key Functions:**

```python
def get_lora_items(self, context):
    """
    Dynamic callback to fetch available LoRa models from ComfyUI server.
    Caches results for 5 minutes to avoid excessive API calls.
    """
    # Check cache validity (5 minutes)
    # If expired → fetch from server
    # Parse /object_info response
    # Return formatted items for dropdown
```

#### 2. `pie_menu.py` (Lines 348-387)

**Added UI Section:**
- LoRa box with icon
- Enable checkbox
- Model dropdown with refresh button
- Strength slider
- Active LoRa indicator

#### 3. `workspace_setup.py` (Lines 509-520, 2262-2282)

**Added Data Handling:**
- `lora` section in `session.json`
- Node 34 override logic in workflow builder
- Conditional enable/disable based on toggle

**Session JSON Structure:**
```json
{
  "lora": {
    "enabled": true,
    "name": "xl_more_art-full_v1.safetensors",
    "strength_model": 0.8,
    "strength_clip": 0.8
  }
}
```

**Workflow Override (Node 34):**
```python
if lora_config.get('enabled', False) and lora_config.get('name') != 'NONE':
    workflow_json["34"]["inputs"]["lora_name"] = lora_config['name']
    workflow_json["34"]["inputs"]["strength_model"] = lora_config.get('strength_model', 0.8)
    workflow_json["34"]["inputs"]["strength_clip"] = lora_config.get('strength_clip', 0.8)
else:
    # Disable LoRa
    workflow_json["34"]["inputs"]["strength_model"] = 0.0
    workflow_json["34"]["inputs"]["strength_clip"] = 0.0
```

---

## 🔍 API Integration

### ComfyUI `/object_info` Endpoint

The feature queries the ComfyUI Backend API's `/object_info` endpoint, which returns node definitions including available models:

**Request:**
```http
GET http://your-server:8188/object_info
```

**Response (Excerpt):**
```json
{
  "LoraLoader": {
    "input": {
      "required": {
        "lora_name": [
          [
            "xl_more_art-full_v1.safetensors",
            "add-detail-xl.safetensors",
            "SDXLrender_v2.0.safetensors",
            "anime_pencil_concept.safetensors"
          ]
        ],
        "strength_model": ["FLOAT", {...}],
        "strength_clip": ["FLOAT", {...}]
      }
    }
  }
}
```

### Parsing Logic

```python
if 'LoraLoader' in object_info:
    lora_loader = object_info['LoraLoader']
    lora_name_input = lora_loader['input']['required'].get('lora_name')
    
    if lora_name_input and isinstance(lora_name_input, list):
        lora_list = lora_name_input[0]  # Extract filename list
        # Convert to UI items
```

---

## 🎨 Name Formatting

**Server Filename** → **Display Name**

Examples:
- `xl_more_art-full_v1.safetensors` → "Xl More Art Full V1"
- `add-detail-xl.safetensors` → "Add Detail Xl"
- `SDXLrender_v2.0.safetensors` → "Sdxlrender V2 0"

**Logic:**
1. Remove `.safetensors` extension
2. Replace `_` and `-` with spaces
3. Capitalize each word
4. Truncate if > 35 characters

---

## ⚙️ Configuration

### Cache Settings

**Default**: 5 minutes (300 seconds)

**Modify** in `ui_panel.py`:
```python
_lora_cache = {
    'items': [],
    'timestamp': 0,
    'cache_duration': 300  # Change this value
}
```

### Fallback Behavior

If server fetch fails:
- Falls back to minimal default list:
  - "None"
  - "More Art Full" (default LoRa)
- Logs warning to console
- UI remains functional

### Backend Mode

LoRa discovery only works in **GCS mode** (self-hosted ComfyUI).

In **RunComfy Cloud mode**, falls back to default list.

---

## 🧪 Testing

### Console Output

**Successful Fetch:**
```
[Style Engine] Fetching LoRa list from ComfyUI server...
[Style Engine] ✓ Found 15 LoRa models on server
```

**Using Cache:**
```
[Style Engine] Using cached LoRa list (15 items, age: 127s)
```

**Refresh:**
```
[Style Engine] LoRa cache cleared - will refresh on next dropdown open
```

**Generation with LoRa:**
```
[GCS] 🎨 LoRa enabled: xl_more_art-full_v1.safetensors
[GCS]    Strength: 0.80
```

**Generation without LoRa:**
```
[GCS] LoRa disabled
```

### Test Procedure

1. ✅ Start ComfyUI server (GCS mode)
2. ✅ Set Style Engine backend to GCS
3. ✅ Open pie menu and enable LoRa
4. ✅ Open dropdown (should fetch from server)
5. ✅ Check console for "Found X LoRa models"
6. ✅ Select a LoRa and adjust strength
7. ✅ Generate image
8. ✅ Check console for "LoRa enabled" message
9. ✅ Verify Node 34 receives correct values

---

## 🚨 Error Handling

### Server Unreachable
```python
except Exception as e:
    print(f"[Style Engine] ⚠️ Failed to fetch LoRas from server: {e}")
    return default_items  # Fallback
```

### Invalid Response
```python
if not lora_list or not isinstance(lora_list, list):
    print("[Style Engine] Using default LoRa list")
    return default_items
```

### Timeout
```python
server_client._request('GET', '/object_info', timeout=5)
```

---

## 📊 Performance

### Cache Benefits
- **Without cache**: ~100-200ms per dropdown open (network request)
- **With cache**: ~1ms per dropdown open (memory read)
- **Cache duration**: 5 minutes
- **Manual refresh**: Available via button

### Network Usage
- **Endpoint**: `/object_info` (typically 50-100KB response)
- **Frequency**: Every 5 minutes (max)
- **Timeout**: 5 seconds
- **Retry**: None (immediate fallback)

---

## 🔮 Future Enhancements

### Potential Features
1. **Multiple LoRa Support**: Stack multiple LoRas with different strengths
2. **LoRa Browser**: Visual preview of LoRa effects
3. **Favorites System**: Save frequently used LoRas
4. **LoRa Presets**: Save LoRa + strength combinations
5. **Local Folder Scanning**: Support for local ComfyUI installations
6. **LoRa Categories**: Group by style, quality, etc.
7. **CLIP Strength Control**: Separate slider for CLIP strength
8. **Thumbnail Previews**: Show example images for each LoRa

---

## 📚 Related Documentation

- **Workflow Node Mapping**: See `ComfyUI/runcomfyWorkflows/NODE_MAPPING.md`
- **GCS Mode Setup**: See `docs/API_SETUP_GUIDE.md`
- **Pie Menu Usage**: See `docs/USER_GUIDE.txt`
- **Architecture**: See `docs/ARCHITECTURE.md`

---

## 🐛 Troubleshooting

### Issue: Dropdown shows only "None" and "More Art Full"

**Cause**: Server fetch failed or not in GCS mode

**Solution**:
1. Check backend mode in preferences (must be GCS)
2. Verify ComfyUI server is running
3. Test server connection in preferences
4. Check console for error messages

### Issue: LoRa not applied to generated images

**Cause**: LoRa enabled but strength set to 0, or Node 34 not in workflow

**Solution**:
1. Check strength slider is > 0
2. Verify "Use LoRa" is checked
3. Check console for "LoRa enabled" message
4. Verify workflow includes Node 34 (LoraLoader)

### Issue: Cache not refreshing

**Cause**: Cache timestamp not clearing properly

**Solution**:
1. Click refresh button (🔄)
2. Restart Blender
3. Check `_lora_cache` in code

---

## 📄 Version History

### v0.3.2 (2025-12-29)
- ✅ Implemented dynamic LoRa discovery from ComfyUI server
- ✅ Added 5-minute caching system
- ✅ Created refresh operator and UI button
- ✅ Integrated with workflow Node 34
- ✅ Added session.json storage
- ✅ Comprehensive error handling

---

**Document Version**: 1.0  
**Last Updated**: December 29, 2025  
**Maintainer**: Style Engine Development Team

