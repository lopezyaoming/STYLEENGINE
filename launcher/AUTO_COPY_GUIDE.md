# Auto-Copy Feature Guide

## What's New? ✨

The server now **automatically copies** ComfyUI's output to `current_ai.png` without any manual intervention!

---

## How It Works

### Before (Manual)
```
1. Send workflow to ComfyUI
2. Wait for ComfyUI to finish
3. Find the output file in ComfyUI/output/
4. Manually copy it to current_ai.png
5. Wait for Blender to refresh
```
**Problem**: Manual, slow, requires monitoring

### After (Automatic)
```
1. Send workflow to ComfyUI
   ↓
2. Server monitors in background ⏱️
   ↓
3. ComfyUI generates image 🎨
   ↓
4. Server auto-copies to current_ai.png 📸
   ↓
5. Blender auto-refreshes viewport ✨
```
**Result**: Fully automated, hands-free!

---

## Testing the Feature

### Step 1: Start Everything

1. **ComfyUI**
   ```bash
   # Navigate to your ComfyUI folder and start it
   # The server needs to know where ComfyUI is installed
   ```

2. **FastAPI Server**
   ```bash
   cd launcher
   python main.py
   ```

3. **Blender**
   - Open Blender
   - Load Style Engine addon
   - Set ComfyUI path in preferences
   - Click "Setup Workspace"
   - Enable "Refresh Viewport" checkbox

### Step 2: Send Test Workflow

#### Option A: Via Dashboard

1. Open http://localhost:8000
2. Click **"🧪 Send Test Workflow"** button
3. Watch the activity log:
   ```
   ✅ Workflow sent! Prompt ID: abc-123
      ├─ Prompt: "..."
      ├─ Resolution: 1024x1024
      ├─ Depth: depth0001.png
      ├─ ComfyUI: C:/ComfyUI/...
      └─ Output: Will auto-copy when ready ✨
   🔄 Auto-monitoring enabled
   ```

#### Option B: Via API

```bash
curl -X POST http://localhost:8000/debug/send_workflow
```

### Step 3: Watch the Magic Happen

**In the Server Console**, you'll see:
```
[Style Engine] Monitoring ComfyUI job: abc-123-def-456
[Style Engine] ✅ ComfyUI job complete!
[Style Engine] 📸 Copied output to current_ai.png
   Source: C:/ComfyUI/output/style_engine_output_00001_.png
   Dest: C:/Coding/STYLEENGINE/data/temp/ai_vision/current_ai.png
```

**In Blender**, the viewport automatically updates with the new image!

---

## Monitoring Progress

### Check Server Console

The server prints real-time updates:
- 🔄 When monitoring starts
- ⏱️ Checking ComfyUI every 2 seconds
- ✅ When job completes
- 📸 When output is copied
- ⚠️ If any errors occur

### Check current_ai.png Status

**Via API:**
```bash
curl http://localhost:8000/debug/current_ai_status
```

**Response:**
```json
{
  "exists": true,
  "path": "C:/Coding/STYLEENGINE/data/temp/ai_vision/current_ai.png",
  "size_bytes": 1234567,
  "modified": "2025-10-23T12:34:56",
  "age_seconds": 5.2
}
```

### Dashboard Status

The dashboard shows:
- Session status (active/idle)
- Last workflow sent
- Activity log with all events

---

## How the Monitoring Works

### 1. **Non-Blocking Response**
When you send a workflow, the server responds immediately:
```json
{
  "status": "success",
  "message": "Workflow sent! Monitoring for completion...",
  "monitoring": true
}
```

### 2. **Background Task**
A background task runs independently:
```python
async def wait_for_comfy_completion(prompt_id, output_dir, dest_path):
    while not complete:
        # Check ComfyUI history API every 2 seconds
        # When prompt_id appears in history = complete!
```

### 3. **Auto-Copy**
Once complete:
- Finds newest `style_engine_output_*.png` in ComfyUI output
- Copies it to `current_ai.png`
- Blender's auto-refresh picks it up

---

## Configuration

### Timeout Settings

Default: **120 seconds** (2 minutes)

To change, edit `server.py`:
```python
async def wait_for_comfy_completion(..., max_wait: int = 120):
```

### Check Interval

Default: **2 seconds**

To change, edit `server.py`:
```python
check_interval = 2  # Check every 2 seconds
```

---

## Troubleshooting

### ❌ "Timeout waiting for ComfyUI"

**Cause**: ComfyUI took longer than 120 seconds

**Fix**:
- Increase `max_wait` in server code
- Check ComfyUI console for errors
- Simplify the workflow for faster processing

---

### ❌ "Job complete but no output files found"

**Cause**: ComfyUI finished but didn't save output

**Fix**:
- Check ComfyUI output folder manually
- Verify the SaveImage node in workflow has correct settings
- Check ComfyUI console for errors

---

### ⚠️ Output not showing in Blender

**Cause**: Blender auto-refresh might be disabled

**Fix**:
- Check "Refresh Viewport" checkbox is enabled
- The refresh happens every 5 seconds
- Try manually changing viewport angle to force refresh

---

### 🔍 File copied but old image still visible

**Cause**: Image caching or refresh timing

**Fix**:
- Wait 5 seconds for auto-refresh
- Toggle the camera view (press 0 on numpad)
- Check file modification time with `/debug/current_ai_status`

---

## Technical Details

### API Flow

```
POST /debug/send_workflow
  ↓
1. Validate session.json and paths
2. Copy depth0001.png to ComfyUI/input
3. Read workflow from BasicLCM.json
4. Inject: prompt, resolution, depth image
5. Send to ComfyUI → get prompt_id
6. Add background task: wait_for_comfy_completion()
7. Return success response immediately
```

### Background Task Flow

```
wait_for_comfy_completion(prompt_id, output_dir, dest_path)
  ↓
Loop (max 120s):
  ↓
  GET http://127.0.0.1:8188/history/{prompt_id}
  ↓
  If prompt_id in history:
    ↓
    Find newest: style_engine_output_*.png
    ↓
    shutil.copy2(source, current_ai.png)
    ↓
    Print success ✅
    ↓
    Return True
  Else:
    ↓
    Wait 2 seconds
    ↓
    Continue loop
```

### File Naming

ComfyUI outputs: `style_engine_output_00001_.png`, `00002_.png`, etc.

Server finds the **newest** file (by modification time) and copies it.

---

## Benefits

✅ **Hands-free** - No manual copying
✅ **Fast** - Copies as soon as ready
✅ **Reliable** - Monitors until complete or timeout
✅ **Non-blocking** - Server responds immediately
✅ **Automatic** - Works with Blender's auto-refresh
✅ **Logged** - All actions printed to console

---

## Next Steps

Once this is working, we can:
1. **Auto-trigger** workflows when Blender updates passes
2. **Queue multiple** requests
3. **WebSocket notifications** for real-time updates
4. **History tracking** of generated images

---

## Quick Reference

| What | Where | Default |
|------|-------|---------|
| Monitoring interval | `check_interval` in `wait_for_comfy_completion()` | 2 seconds |
| Max wait time | `max_wait` parameter | 120 seconds |
| Output pattern | ComfyUI workflow (SaveImage node) | `style_engine_output_*.png` |
| Destination | `current_ai_path` | `data/temp/ai_vision/current_ai.png` |
| Check status | GET `/debug/current_ai_status` | Shows file info |

---

## Success Indicators

You know it's working when:

1. **Server console** shows:
   ```
   [Style Engine] Monitoring ComfyUI job: ...
   [Style Engine] ✅ ComfyUI job complete!
   [Style Engine] 📸 Copied output to current_ai.png
   ```

2. **Dashboard activity log** shows:
   ```
   ✅ Workflow sent!
   🔄 Auto-monitoring enabled
   ```

3. **Blender viewport** updates with new image automatically

4. **ComfyUI** shows the job completed successfully

---

Enjoy the automated workflow! 🎉

