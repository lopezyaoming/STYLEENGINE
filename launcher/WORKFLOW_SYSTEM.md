# Dynamic Workflow System Guide

## 🎉 What's New?

The Style Engine now features a **dynamic workflow system** with full parameter injection! You can:
- Switch between multiple ComfyUI workflows via dashboard
- Workflows are auto-detected from `/ComfyUI/workflows/` folder
- All parameters (depth, silhouette, steps, resolution, prompt) are dynamically injected
- Add new workflows without touching the server code

---

## 📋 Available Workflows

### 1. **BasicLCM.json**
- **Speed**: ⚡⚡⚡ Very Fast (5 steps)
- **Quality**: Good for rapid iteration
- **Features**: LCM model, basic depth ControlNet
- **Best for**: Quick previews, testing

### 2. **DepthLCM.json** (Default)
- **Speed**: ⚡⚡ Fast (5 steps)
- **Quality**: Enhanced depth processing
- **Features**: LCM model + DepthAnything preprocessor
- **Best for**: Better depth understanding, real-time feedback

### 3. **SDXLworkflow.json**
- **Speed**: ⚡ Moderate (15-30 steps, adjustable)
- **Quality**: ⭐⭐⭐ High quality, artistic
- **Features**: 
  - Dual ControlNet (Depth + Canny/Silhouette)
  - DepthAnything preprocessor
  - xl_more_art LoRA
  - Adjustable steps
- **Best for**: Final renders, high-quality output

---

## 🎛️ Parameter Injection

All workflows automatically receive these parameters from Blender:

| Parameter | Source | Node | Description |
|-----------|--------|------|-------------|
| **Image Input** | `combined0001.png` | Node 15 | Blender render pass |
| **Prompt** | Global Prompt (UI) | Node 25 | Text prompt for generation |
| **Resolution** | Resolution dropdown | Node 5 | Width × Height |
| **Depth Influence** | Depth Influence slider | Node 41 | Depth ControlNet strength (0.0-1.0) |
| **Silhouette Influence** | Silhouette Influence slider | Node 40 | Canny/Silhouette strength (0.0-1.0) |
| **Steps** | Steps slider (UI) | Node 42 | Sampling steps (15-30) |

### How It Works

The server reads your `session.json` and intelligently injects data:

```python
# In Blender UI:
depth_influence = 0.85
silhouette_influence = 0.75
steps = 20
global_prompt = "cyberpunk cityscape"

# Server injects into workflow:
workflow["41"]["inputs"]["value"] = 0.85  # Depth
workflow["40"]["inputs"]["value"] = 0.75  # Silhouette
workflow["42"]["inputs"]["value"] = 20    # Steps
workflow["25"]["inputs"]["value"] = "cyberpunk cityscape"
```

---

## 🚀 Using the System

### Switch Workflows via Dashboard

1. Open http://localhost:8000
2. Find the **"⚙️ Workflow Selection"** card
3. Use the dropdown to select a workflow
4. Changes apply immediately
5. Next render uses the new workflow

### Switch Workflows via API

```bash
# Get available workflows
curl http://localhost:8000/workflows

# Set active workflow
curl -X POST http://localhost:8000/workflows/set/SDXLworkflow.json

# Check current workflow
curl http://localhost:8000/workflows/active
```

### In Blender

1. Open Style Engine panel
2. Adjust **"Influence"** sliders:
   - **Depth Influence**: How much depth guides generation
   - **Silhouette Influence**: How much edges/outlines guide generation
   - **Steps**: More steps = better quality (slower)
3. Changes auto-save to `session.json`
4. Next render uses updated values

---

## 📁 Adding New Workflows

### Step 1: Create Your Workflow

1. Design workflow in ComfyUI
2. Save as JSON in `ComfyUI/workflows/YourWorkflow.json`

### Step 2: Use Standard Node IDs

For auto-injection to work, use these node IDs:

```json
{
  "5": { "class_type": "EmptyLatentImage" },   // Width/Height
  "9": { "class_type": "SaveImage" },          // Output
  "15": { "class_type": "LoadImage" },         // Input image
  "25": { "class_type": "PrimitiveString" },   // Prompt
  "40": { "class_type": "PrimitiveFloat" },    // Silhouette (optional)
  "41": { "class_type": "PrimitiveFloat" },    // Depth (optional)
  "42": { "class_type": "PrimitiveInt" }       // Steps (optional)
}
```

### Step 3: It Just Works!

- Server auto-detects new workflow
- Appears in dashboard dropdown
- All parameters injected automatically
- No server restart needed

---

## 🎨 Workflow Comparison

| Feature | BasicLCM | DepthLCM | SDXLworkflow |
|---------|----------|----------|--------------|
| Speed | 🔥 5s | 🔥 7s | ⏱️ 15-45s |
| Quality | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Depth | ✅ Basic | ✅ Enhanced | ✅ Enhanced |
| Silhouette | ❌ | ❌ | ✅ Canny |
| Steps Control | ❌ Fixed | ❌ Fixed | ✅ 15-30 |
| LoRAs | ✅ LCM | ✅ LCM | ✅ LCM + Art |
| Best For | Testing | Real-time | Finals |

---

## 🔧 Advanced: Custom Node Mapping

### Non-Standard Workflows

If your workflow uses different node IDs, you have two options:

#### Option 1: Rename Nodes in ComfyUI

Match the standard IDs (5, 9, 15, 25, 40, 41, 42).

#### Option 2: Extend Injection Logic

Edit `launcher/server.py`:

```python
def inject_workflow_data(workflow: dict, session_data: dict) -> dict:
    # ... existing code ...
    
    # Add custom node mappings
    if "YOUR_NODE_ID" in workflow:
        workflow["YOUR_NODE_ID"]["inputs"]["param"] = value
    
    return workflow
```

---

## 📊 Monitoring

### Dashboard Shows:
- **Active Workflow**: Currently selected workflow
- **Available**: Total count of detected workflows
- **Dropdown**: All available workflows (sorted alphabetically)
- **Activity Log**: Real-time injection data when sending workflows

### Example Log:
```
✅ Workflow sent! Prompt ID: abc-123
   ├─ Workflow: SDXLworkflow.json
   ├─ Prompt: "cyberpunk cityscape"
   ├─ Resolution: 1024x1024
   ├─ Combined Pass: combined0001.png
   ├─ Depth Influence: 0.85
   ├─ Silhouette Influence: 0.75
   ├─ Steps: 20
   ├─ ComfyUI: C:/ComfyUI/...
   └─ Output: Will auto-copy to current_ai.png
```

---

## 🎯 Workflow Strategy

### For Rapid Iteration:
1. Use **BasicLCM** or **DepthLCM**
2. Set Steps to 15 (if adjustable)
3. Lower resolution (640x1536, 768x1344)
4. Cycle time: ~5-10 seconds

### For Quality Output:
1. Use **SDXLworkflow**
2. Set Steps to 25-30
3. Higher resolution (1024x1024, 1152x896)
4. Adjust Depth/Silhouette influence for control
5. Cycle time: ~30-60 seconds

### For Mixed Workflow:
1. Start with **DepthLCM** for layout/composition
2. Switch to **SDXLworkflow** when ready for quality
3. Fine-tune with influence sliders
4. Export final renders

---

## 🔄 Auto-Generation with Workflows

When "Auto-Generate AI" is enabled:

```
1. Blender renders passes (every 5s)
2. Server detects combined0001.png update
3. Server reads active workflow
4. Server injects all parameters from session.json
5. Workflow sent to ComfyUI
6. Output auto-copied to current_ai.png
7. Blender viewport updates
8. Repeat!
```

**All workflows work with auto-generation!**

---

## 🐛 Troubleshooting

### ❌ "Workflow not found"
- **Cause**: File not in `ComfyUI/workflows/` directory
- **Fix**: Move workflow JSON to workflows folder, refresh dashboard

### ❌ "Parameters not injecting"
- **Cause**: Workflow uses non-standard node IDs
- **Fix**: 
  1. Check workflow JSON for correct node IDs
  2. Rename nodes in ComfyUI to match standard IDs (5, 9, 15, 25, etc.)

### ⚠️ "Workflow runs but ignores sliders"
- **Cause**: Workflow missing optional nodes (40, 41, 42)
- **Fix**: This is normal - not all workflows support all parameters. BasicLCM doesn't use steps, for example.

### 🐌 "Workflow too slow"
- **Cause**: High steps value in SDXLworkflow
- **Fix**: Reduce Steps slider to 15-20 in Blender UI

---

## 📚 API Reference

### `GET /workflows`
Get all available workflows.

**Response:**
```json
{
  "workflows": ["BasicLCM.json", "DepthLCM.json", "SDXLworkflow.json"],
  "active": "DepthLCM.json",
  "count": 3
}
```

### `GET /workflows/active`
Get currently active workflow.

**Response:**
```json
{
  "active_workflow": "DepthLCM.json"
}
```

### `POST /workflows/set/{workflow_name}`
Set active workflow.

**Example:**
```bash
curl -X POST http://localhost:8000/workflows/set/SDXLworkflow.json
```

**Response:**
```json
{
  "status": "success",
  "active_workflow": "SDXLworkflow.json",
  "message": "Switched to SDXLworkflow.json"
}
```

---

## 🎓 Best Practices

1. **Name workflows descriptively**: `FastDraft.json`, `HighQuality.json`, `ExperimentalX.json`
2. **Use standard node IDs** for seamless integration
3. **Test workflows manually** before enabling auto-generation
4. **Document custom workflows** with comments in JSON
5. **Keep workflow files organized** in the workflows directory
6. **Version your workflows**: `SDXLv1.json`, `SDXLv2.json`

---

## 🚀 Future Enhancements

Planned features:
- [ ] Workflow presets (Fast/Medium/Slow)
- [ ] Per-workflow custom parameters
- [ ] Workflow metadata (description, author, version)
- [ ] Hot-reload workflows without server restart
- [ ] Workflow validation and error checking
- [ ] Workflow templates for easy creation

---

## 📋 Quick Reference

| Action | How |
|--------|-----|
| **Switch workflow** | Dashboard dropdown or API |
| **Add workflow** | Drop JSON in `/workflows/` folder |
| **Adjust parameters** | Blender UI sliders |
| **Check active** | Dashboard or `/workflows/active` |
| **View all** | `/workflows` endpoint |
| **Test workflow** | Dashboard "Send Test Workflow" button |

---

Enjoy the flexibility! 🎨✨

