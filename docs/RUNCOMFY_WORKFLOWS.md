# RunComfy Workflows - Configuration Guide

**Status:** Awaiting Workflow Deployment  
**Date:** October 29, 2025

---

## 🚨 Action Required

This document will be populated once workflows are deployed to RunComfy.

### Current Status
- ✅ SDXL workflow JSON prepared (ComfyUI/workflows/SDXLworkflow.json)
- ✅ IPAdapter workflow JSON prepared (ComfyUI/workflows/IPAdapterworkflow.json)
- ⏳ Workflows need to be uploaded to RunComfy
- ⏳ Workflow IDs need to be obtained
- ⏳ Workflow IDs need to be set in prefs.py

---

## Workflow Upload Process

### 1. Access RunComfy Dashboard
- Go to https://runcomfy.com
- Sign in with your account
- Navigate to "Workflows" section

### 2. Upload SDXL Workflow
- Click "New Workflow" or "Upload"
- Select: `ComfyUI/workflows/SDXLworkflow.json`
- Name: "Style Engine - SDXL"
- Note the generated **Workflow ID**

### 3. Upload IPAdapter Workflow
- Click "New Workflow" or "Upload"
- Select: `ComfyUI/workflows/IPAdapterworkflow.json`
- Name: "Style Engine - IPAdapter"
- Note the generated **Workflow ID**

---

## Configuration

Once you have the workflow IDs, update them in:

**File:** `scripts/addons/styleengine/prefs.py`

**Location:** Lines 49-58

```python
runcomfy_workflow_id_sdxl: StringProperty(
    name="SDXL Workflow ID",
    description="RunComfy workflow ID for SDXL generation (provided by developer)",
    default="PASTE_SDXL_WORKFLOW_ID_HERE"  # ← UPDATE THIS
)

runcomfy_workflow_id_ipadapter: StringProperty(
    name="IPAdapter Workflow ID",
    description="RunComfy workflow ID for IPAdapter generation (provided by developer)",
    default="PASTE_IPADAPTER_WORKFLOW_ID_HERE"  # ← UPDATE THIS
)
```

---

## Workflow Specifications

### SDXL Workflow

**Purpose:** Standard SDXL generation with depth and silhouette control

**Required Nodes:**

| Node ID | Type | Purpose | Input Source |
|---------|------|---------|--------------|
| 25 | PrimitiveString | Text prompt | session_data['global_prompt'] |
| 15 | LoadImage | Combined pass | combined0001.png (base64) |
| 40 | PrimitiveFloat | Silhouette strength | session_data['silhouette_influence'] |
| 41 | PrimitiveFloat | Depth strength | session_data['depth_influence'] |
| 42 | PrimitiveInt | Steps | session_data['steps'] |
| 9 | SaveImage | Output | N/A (result extraction) |

**Override Structure:**
```python
{
    "25": {"inputs": {"value": "prompt text"}},
    "15": {"inputs": {"image": "data:image/png;base64,..."}},
    "40": {"inputs": {"value": 0.75}},  # Silhouette 0.0-1.0
    "41": {"inputs": {"value": 0.5}},   # Depth 0.0-1.0
    "42": {"inputs": {"value": 15}}     # Steps 15-30
}
```

**Typical Generation Time:**
- Cold start: 2-5 minutes
- Warm instance: 15-30 seconds

**Hardware Recommendations:**
- Min: AMPERE_24 (A5000 24GB)
- Recommended: AMPERE_48 (A6000 48GB)

---

### IPAdapter Workflow

**Purpose:** SDXL generation with additional reference image guidance

**Required Nodes:**

| Node ID | Type | Purpose | Input Source |
|---------|------|---------|--------------|
| 25 | PrimitiveString | Text prompt | session_data['global_prompt'] |
| 15 | LoadImage | Combined pass | combined0001.png (base64) |
| 40 | PrimitiveFloat | Silhouette strength | session_data['silhouette_influence'] |
| 41 | PrimitiveFloat | Depth strength | session_data['depth_influence'] |
| 42 | PrimitiveInt | Steps | session_data['steps'] |
| **43** | **LoadImage** | **Reference image** | **ipadapter.reference_image (base64)** |
| **49** | **IPAdapterEmbeds** | **Weight type** | **ipadapter.weight_type** |
| **52** | **PrimitiveFloat** | **IP Strength** | **ipadapter.strength** |
| 9 | SaveImage | Output | N/A (result extraction) |

**Override Structure:**
```python
{
    "25": {"inputs": {"value": "prompt text"}},
    "15": {"inputs": {"image": "data:image/png;base64,..."}},
    "40": {"inputs": {"value": 0.75}},
    "41": {"inputs": {"value": 0.5}},
    "42": {"inputs": {"value": 15}},
    "43": {"inputs": {"image": "data:image/png;base64,..."}},  # Reference
    "49": {"inputs": {"weight_type": "style transfer"}},        # Mode
    "52": {"inputs": {"value": 0.75}}                          # Strength 0.0-1.5
}
```

**Weight Type Options:**
- `"style transfer"` - Apply artistic style from reference
- `"composition"` - Use reference for layout/structure
- `"strong style transfer"` - Aggressive style application

**Typical Generation Time:**
- Cold start: 3-6 minutes (larger model)
- Warm instance: 20-40 seconds

**Hardware Recommendations:**
- Min: AMPERE_48 (A6000 48GB) - IPAdapter requires more VRAM
- Recommended: AMPERE_48 (A6000 48GB)

---

## Node Mapping Reference

### Data Flow: Blender → RunComfy

```
Blender Scene Data (session.json)
    ↓
Global Prompt → Node 25 (PrimitiveString)
Silhouette Influence → Node 40 (PrimitiveFloat)
Depth Influence → Node 41 (PrimitiveFloat)
Steps → Node 42 (PrimitiveInt)
    ↓
Render Passes (workspace_setup.py)
    ↓
combined0001.png → Base64 → Node 15 (LoadImage)
depth0001.png → Base64 → (embedded in combined)
    ↓
[If IPAdapter enabled]
reference_image → Base64 → Node 43 (LoadImage)
weight_type → Node 49 (IPAdapterEmbeds)
strength → Node 52 (PrimitiveFloat)
    ↓
RunComfy API Submission
    ↓
Polling (runcomfy_polling.py)
    ↓
Result Download → current_ai.png
    ↓
[If output_path set]
Save to output_path/generated/{timestamp}_runcomfy.png
```

---

## Verification Checklist

Before deployment, ensure:

### SDXL Workflow
- [ ] Node 25 is PrimitiveString (prompt input)
- [ ] Node 15 is LoadImage (accepts base64 data URI)
- [ ] Node 40 is PrimitiveFloat (silhouette, range 0.0-1.0)
- [ ] Node 41 is PrimitiveFloat (depth, range 0.0-1.0)
- [ ] Node 42 is PrimitiveInt (steps, range 15-30)
- [ ] Node 9 is SaveImage (output extraction)
- [ ] Workflow compiles without errors in ComfyUI
- [ ] Test generation produces expected output

### IPAdapter Workflow
- [ ] All SDXL workflow checks (above)
- [ ] Node 43 is LoadImage (reference image, accepts base64)
- [ ] Node 49 is IPAdapterEmbeds (weight_type input)
- [ ] Node 52 is PrimitiveFloat (strength, range 0.0-1.5)
- [ ] IPAdapter model loaded correctly
- [ ] Test generation with reference image works

---

## Testing

### Local Testing (Before RunComfy Upload)

1. **Test in ComfyUI:**
   ```bash
   # Start local ComfyUI
   python main.py
   
   # Open workflow
   # - Load SDXLworkflow.json
   # - Manually set test values
   # - Queue prompt
   # - Verify output
   ```

2. **Test Override Structure:**
   ```python
   # In ComfyUI API console
   overrides = {
       "25": {"inputs": {"value": "test prompt"}},
       "15": {"inputs": {"image": "base64_data_here"}},
       # ... etc
   }
   ```

### RunComfy Testing (After Upload)

1. **Test API Client:**
   ```bash
   python tests/test_runcomfy_api.py
   ```

2. **Test in Blender:**
   - Load addon
   - Set workflow IDs in preferences
   - Set API credentials
   - Click "Generate (Cloud)"
   - Verify server status updates
   - Verify image downloads

---

## Troubleshooting

### Common Issues

**"Workflow ID not configured"**
- Solution: Set workflow IDs in addon preferences
- Location: Edit → Preferences → Add-ons → Style Engine → Workflow Configuration

**"Node not found"**
- Solution: Verify workflow node IDs match specifications
- Check: Node IDs must match exactly (25, 15, 40, 41, 42, 9)

**"Invalid image format"**
- Solution: Ensure base64 data URI format
- Format: `data:image/png;base64,iVBORw0KG...`

**"Deployment creation failed"**
- Solution: Check hardware tier compatibility
- IPAdapter requires AMPERE_48 (48GB VRAM minimum)

**"Generation timeout"**
- Solution: Increase timeout in Advanced Settings
- Default: 600s (10 minutes)
- Cold start may need more time

---

## Cost Estimates

### SDXL Workflow

| Hardware | Cost/Hour | Typical Gen | Cost/Gen |
|----------|-----------|-------------|----------|
| AMPERE_24 | $1.50/hr | 20s | $0.008 |
| AMPERE_48 | $2.50/hr | 20s | $0.014 |
| ADA_24 | $2.00/hr | 20s | $0.011 |

**Cold Start (first gen):**
- Time: 2-5 minutes
- Cost: $0.05-$0.21 (depending on hardware)

### IPAdapter Workflow

| Hardware | Cost/Hour | Typical Gen | Cost/Gen |
|----------|-----------|-------------|----------|
| AMPERE_48 | $2.50/hr | 30s | $0.021 |

**Cold Start (first gen):**
- Time: 3-6 minutes
- Cost: $0.13-$0.25

**Monthly Estimates:**
- Light use (10 gens/day): ~$4-6/month
- Regular use (50 gens/day): ~$21-31/month
- Heavy use (200 gens/day): ~$84-124/month

---

## Support

For workflow-related issues:
1. Check ComfyUI console for node errors
2. Verify base64 encoding of images
3. Test locally before RunComfy deployment
4. Review RunComfy deployment logs

For implementation issues:
- See: `context/RUNCOMFY_IMPLEMENTATION_STATUS.md`
- Check: Blender console for Style Engine logs
- Test: `tests/test_runcomfy_api.py`

---

**Last Updated:** October 29, 2025  
**Next Update:** After workflow deployment and ID acquisition

