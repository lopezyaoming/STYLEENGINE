# ComfyUI Integration - Testing Guide

## Prerequisites

✅ **ComfyUI** running at `http://127.0.0.1:8188`  
✅ **Style Engine Server** running (launcher)  
✅ **BasicLCM.json** workflow in `ComfyUI/workflows/`

---

## Quick Test

### Method 1: Using the Dashboard (Easiest)

1. **Start ComfyUI** (make sure it's running at port 8188)
2. **Start the launcher server**:
   ```powershell
   cd C:\Coding\STYLEENGINE\launcher
   python main.py
   ```
3. **Open the dashboard**: http://localhost:8000
4. Look at the **"ComfyUI Status"** card:
   - Should show `✅ ONLINE` if ComfyUI is running
   - Shows queue status (running/pending)
5. Click **"🧪 Send Test Workflow"** button
6. You should see:
   - An alert with the Prompt ID
   - Activity log shows "✅ Workflow sent successfully!"
   - ComfyUI starts processing the workflow!

### Method 2: Using API Endpoints Directly

#### 1. Check if ComfyUI is reachable

```powershell
# Using curl (if available)
curl http://localhost:8000/comfy/status

# Or visit in browser
http://localhost:8000/comfy/status
```

**Expected Response:**
```json
{
  "status": "online",
  "message": "ComfyUI is reachable",
  "comfy_reachable": true,
  "comfy_url": "http://127.0.0.1:8188",
  "queue_running": 0,
  "queue_pending": 0
}
```

#### 2. Send the test workflow

```powershell
# Using curl (PowerShell)
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/debug/send_workflow"

# Or visit the interactive docs
http://localhost:8000/docs#/default/debug_send_workflow_debug_send_workflow_post
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Workflow sent to ComfyUI successfully!",
  "prompt_id": "abc-123-xyz",
  "client_id": "unique-uuid-here",
  "workflow_path": "C:\\Coding\\STYLEENGINE\\ComfyUI\\workflows\\BasicLCM.json"
}
```

#### 3. Check ComfyUI queue

```powershell
# Check if workflow is in queue
curl http://localhost:8000/debug/comfy_queue
```

---

## What Happens When You Send the Workflow

1. **Server reads** `ComfyUI/workflows/BasicLCM.json`
2. **Server generates** a unique client ID
3. **Server wraps** the workflow in ComfyUI's expected format:
   ```json
   {
     "prompt": { <workflow nodes> },
     "client_id": "unique-id"
   }
   ```
4. **Server sends** POST request to `http://127.0.0.1:8188/prompt`
5. **ComfyUI receives** and queues the workflow
6. **ComfyUI processes** the workflow (if no errors)
7. **ComfyUI saves** output to its output folder

---

## Troubleshooting

### ❌ "Cannot connect to ComfyUI"

**Problem**: ComfyUI is not running or not on port 8188

**Solution**:
1. Start ComfyUI: 
   ```powershell
   cd path\to\ComfyUI
   python main.py
   ```
2. Verify it's running: Open `http://127.0.0.1:8188` in browser
3. You should see the ComfyUI web interface

### ❌ "Workflow file not found"

**Problem**: BasicLCM.json is not in the expected location

**Solution**:
1. Check the path: http://localhost:8000/debug/paths
2. Look for `workflow_exists: true/false`
3. Make sure the file is at: `C:\Coding\STYLEENGINE\ComfyUI\workflows\BasicLCM.json`

### ❌ "ComfyUI returned status 400/500"

**Problem**: Workflow has errors or missing dependencies

**Solution**:
1. Open ComfyUI web interface directly
2. Try loading the workflow manually in ComfyUI
3. Check if you have required models/nodes:
   - `sd_xl_base_1.0.safetensors` (checkpoint)
   - `lcm_lora_sdxl.safetensors` (LoRA)
   - `control-lora-depth-rank256.safetensors` (ControlNet)
   - `image 10.png` (input image)

### ⚠️ "Workflow sent but nothing happens"

**Problem**: Workflow is queued but not processing

**Solution**:
1. Check ComfyUI console for errors
2. Visit http://localhost:8000/debug/comfy_queue
3. Look at `queue_running` and `queue_pending` counts
4. Check if models are loaded in ComfyUI

---

## Understanding the Workflow (BasicLCM.json)

This is a **fast preview workflow** using:
- **SDXL Base 1.0** model
- **LCM LoRA** for fast generation (5 steps)
- **ControlNet Depth** to guide generation with depth map
- **Input**: Depth image (`image 10.png`)
- **Output**: Generated image saved to ComfyUI output folder

**Current Status**: 
- ✅ Workflow structure is sent
- ❌ Not yet using Blender's depth passes
- ❌ Not yet using session.json data
- ❌ Not yet writing to Style Engine folders

---

## Next Steps

Once this basic test works, we'll integrate:

1. **Dynamic Data**: Replace hardcoded values with session.json data
   - Resolution from UI
   - Prompt from global_prompt
   - Seed control

2. **Pass Integration**: Use Blender's rendered passes
   - `depth0001.png` → ControlNet input
   - `combined0001.png` → img2img input
   - `ao0001.png` → additional conditioning

3. **Output Routing**: Save to Style Engine folders
   - Output → `data/temp/ai_vision/current_ai.png`
   - Blender picks it up automatically

4. **Real-time Loop**: Auto-trigger on Blender render
   - Blender renders → Server detects → ComfyUI generates → Blender displays

---

## API Endpoints Reference

### Production Endpoints
- `GET /comfy/status` - Check ComfyUI connection
- `POST /comfy/generate` - Trigger generation (coming soon)

### Debug Endpoints
- `POST /debug/send_workflow` - Send BasicLCM.json as-is
- `GET /debug/comfy_queue` - View ComfyUI queue
- `GET /debug/paths` - Check file paths

---

## Success Checklist

Test your setup:

- [ ] ComfyUI running at http://127.0.0.1:8188
- [ ] Launcher server running at http://localhost:8000
- [ ] Dashboard shows `✅ ONLINE` for ComfyUI
- [ ] Click "Send Test Workflow" → Success alert
- [ ] ComfyUI shows workflow in progress
- [ ] Image appears in ComfyUI output folder

**If all checked** → You're ready for full integration! 🎉

---

## Development Notes

The workflow sender:
- Uses `httpx` for async HTTP requests
- Generates unique client IDs with `uuid`
- Has 30-second timeout for slow workflows
- Returns ComfyUI's prompt_id for tracking
- Handles connection errors gracefully

Future enhancements:
- WebSocket for real-time progress updates
- Queue management (cancel, prioritize)
- Multiple workflow support
- Result retrieval and display


