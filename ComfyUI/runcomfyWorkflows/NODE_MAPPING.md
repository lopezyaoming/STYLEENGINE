# RunComfy Workflow Node Mapping

**Deployment ID:** `408d6662-46ff-49bb-a480-cb6d7df7c4cd`

This single deployment handles both SDXL and IPAdapter workflows dynamically based on the overrides sent.

---

## SDXL Workflow Nodes

| Node ID | Class Type | Purpose | Override Key | Value Source |
|---------|-----------|---------|--------------|--------------|
| 25 | PrimitiveString | Text prompt | `value` | `session_data['global_prompt']` |
| 15 | LoadImage | Combined pass | `image` | combined0001.png (base64) |
| 40 | PrimitiveFloat | Canny/Silhouette strength | `value` | `session_data['silhouette_influence']` (0.0-1.0) |
| 41 | PrimitiveFloat | Depth strength | `value` | `session_data['depth_influence']` (0.0-1.0) |
| 42 | PrimitiveInt | Generation steps | `value` | `session_data['steps']` (15-30) |
| 9 | SaveImage | Output | N/A | Result extraction |

**Override Structure:**
```python
{
    "25": {"inputs": {"value": "your prompt here"}},
    "15": {"inputs": {"image": "data:image/png;base64,..."}},
    "40": {"inputs": {"value": 0.75}},  # Silhouette
    "41": {"inputs": {"value": 0.5}},   # Depth
    "42": {"inputs": {"value": 15}}     # Steps
}
```

---

## IPAdapter Workflow Nodes

All SDXL nodes PLUS:

| Node ID | Class Type | Purpose | Override Key | Value Source |
|---------|-----------|---------|--------------|--------------|
| 43 | LoadImage | Reference image | `image` | reference_image.png (base64) |
| 49 | IPAdapterEmbeds | IPAdapter mode | `weight_type` | `session_data['ipadapter']['weight_type']` |
| 52 | PrimitiveFloat | IPAdapter strength | `value` | `session_data['ipadapter']['strength']` (0.0-1.5) |

**Override Structure:**
```python
{
    # All SDXL overrides (25, 15, 40, 41, 42) PLUS:
    "43": {"inputs": {"image": "data:image/png;base64,..."}},  # Reference
    "49": {"inputs": {"weight_type": "style transfer"}},       # Mode
    "52": {"inputs": {"value": 0.75}}                          # Strength
}
```

**weight_type Options:**
- `"style transfer"` - Apply artistic style from reference
- `"composition"` - Use reference for layout/structure  
- `"strong style transfer"` - Aggressive style application

---

## Implementation Status

✅ **Deployment ID set in prefs.py:**
- `runcomfy_deployment_id_sdxl` = `408d6662-46ff-49bb-a480-cb6d7df7c4cd`
- `runcomfy_deployment_id_ipadapter` = `408d6662-46ff-49bb-a480-cb6d7df7c4cd`

✅ **Node mapping confirmed:**
- SDXL: Nodes 25, 15, 40, 41, 42, 9 ✓
- IPAdapter: SDXL nodes + 43, 49, 52 ✓

✅ **Override logic implemented:**
- `workspace_setup.py::build_runcomfy_overrides()` matches node structure

---

## Testing Checklist

Before full integration test:

### 1. Test API Connection
```bash
# Set credentials
export RUNCOMFY_API_TOKEN="your_token"
export RUNCOMFY_USER_ID="your_user_id"

# Run test
python tests/test_runcomfy_api.py
```

### 2. Test Deployment Access
```python
# Should confirm deployment exists and is enabled
client.get_deployment("408d6662-46ff-49bb-a480-cb6d7df7c4cd")
```

### 3. Test SDXL Inference
```python
overrides = {
    "25": {"inputs": {"value": "test prompt"}},
    "40": {"inputs": {"value": 0.75}},
    "41": {"inputs": {"value": 0.5}},
    "42": {"inputs": {"value": 15}}
}
# Note: Node 15 (image) requires actual base64 data
```

### 4. Test IPAdapter Inference  
```python
overrides = {
    # SDXL overrides (above) PLUS:
    "43": {"inputs": {"image": "data:image/png;base64,..."}},
    "49": {"inputs": {"weight_type": "style transfer"}},
    "52": {"inputs": {"value": 0.75}}
}
```

---

## Notes

- **Single Deployment**: Both workflows share one deployment (simpler, cheaper)
- **Dynamic Selection**: Workflow type determined by which overrides are sent
- **No Workflow IDs Needed**: Deployment handles both internally
- **Model Name Differences**: RunComfy uses different model names (e.g., `juggernautXL_version6Rundiffusion.safetensors`) but functionality is identical

