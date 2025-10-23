# Cyclical Auto-Generation Guide

## 🎉 What's New?

The Style Engine now features **fully automated, cyclical AI generation**! Once enabled, the system runs in a continuous feedback loop:

```
Blender renders passes (every 5s)
         ↓
Server detects new depth pass
         ↓
Auto-sends workflow to ComfyUI
         ↓
ComfyUI generates AI image
         ↓
Server auto-copies to current_ai.png
         ↓
Blender auto-refreshes viewport
         ↓
(repeat every 5 seconds)
```

**Result**: A real-time AI vision system that continuously updates based on your 3D scene! 🚀

---

## How It Works

### The Cyclical Process

1. **Blender** renders passes (Combined, Depth, AO) every 5 seconds
2. **Server monitor** detects when `depth0001.png` file is updated
3. **Auto-trigger** sends ComfyUI workflow with latest data
4. **ComfyUI** generates image based on:
   - Current depth pass
   - Global prompt from session
   - Resolution settings
5. **Auto-copy** copies output to `current_ai.png`
6. **Blender** refreshes viewport to show new AI image
7. **Repeat** after 5 seconds

### What Makes It Cyclical?

- **Blender** renders passes every 5 seconds (when "Refresh Viewport" is enabled)
- **Server** monitors depth pass every 3 seconds (when "Auto-Generate AI" is enabled)
- **Result**: Approximately every 5-8 seconds, a new AI image is generated based on your latest 3D scene

---

## Setup Instructions

### Step 1: Configure Everything

**In Blender:**

1. Open Blender preferences: **Edit → Preferences → Add-ons → Style Engine**
2. Set your **ComfyUI Path** (e.g., `C:\ComfyUI\...`)
3. Verify green checkmarks appear for ComfyUI folders

**In Blender Scene:**

1. Open Style Engine panel (press `N` in 3D view)
2. Expand **"Workspace Setup"** section
3. Click **"Setup Workspace"** button
4. Set your **Session ID**, **Output Path**, and **Resolution**
5. Set a **Global Prompt** in the "Image Generation" section

### Step 2: Start ComfyUI

```bash
# Navigate to your ComfyUI installation
cd C:\ComfyUI\...

# Run ComfyUI
# (depends on your installation type)
```

Make sure ComfyUI is running at `http://127.0.0.1:8188`

### Step 3: Start the Server

```bash
cd launcher
python main.py
```

You should see:
```
[Style Engine] Server started successfully!
[Style Engine] Dashboard: http://localhost:8000
[Style Engine] Auto-generation monitor initialized
[Style Engine] 🔄 Auto-generation monitor started
```

### Step 4: Enable Auto-Generation

**In Blender (Style Engine panel):**

1. ☑️ **Refresh Viewport** (enable render passes)
2. ☑️ **Auto-Generate AI** (enable auto-workflow triggering)

**That's it!** The cycle begins immediately.

---

## Monitoring the Cycle

### Dashboard (http://localhost:8000)

Open the dashboard to see real-time status:

**🔄 Auto-Generation Card:**
- **Monitor Status**: ✅ Running / ⏸️ Stopped
- **Auto-Generate**: ✅ Enabled / ❌ Disabled
- **Depth Pass**: ✅ Available / ❌ Not found

**📝 Activity Log:**
- Shows each workflow sent
- Shows when outputs are copied
- Real-time progress updates

### Server Console

The server prints detailed logs:

```
[Style Engine] 🆕 New render pass detected!
[Style Engine] 🚀 Auto-triggering ComfyUI workflow...
[Style Engine] 🎨 Workflow sent to ComfyUI (ID: abc-123)
[Style Engine] ✅ Auto-workflow sent (Prompt ID: abc-123)
[Style Engine] Monitoring ComfyUI job: abc-123
[Style Engine] ✅ ComfyUI job complete!
[Style Engine] 📸 Copied output to current_ai.png
```

### Blender Viewport

- The **right viewport** (camera view) updates with each new AI image
- Updates happen automatically every 5 seconds
- You'll see the AI "vision" evolve as you work

---

## Understanding the Timing

### Render Interval: 5 seconds

Blender renders new passes every 5 seconds when "Refresh Viewport" is enabled.

### Monitor Interval: 3 seconds

The server checks for depth pass changes every 3 seconds.

### ComfyUI Processing: Variable

Depends on your workflow complexity and GPU speed. Typical: 2-10 seconds.

### Example Timeline

```
T+0s:  Blender renders passes
T+3s:  Server detects change, sends workflow
T+3s:  ComfyUI starts processing
T+8s:  ComfyUI finishes, server copies output
T+10s: Blender renders passes again
T+13s: Server detects new change, sends workflow
...cycle continues...
```

**Effective cycle time**: ~10-15 seconds per iteration (depending on ComfyUI speed)

---

## Controlling the Cycle

### Start/Stop

**Enable:**
- ☑️ Check "Auto-Generate AI" in Blender

**Disable:**
- ☐ Uncheck "Auto-Generate AI" in Blender

The monitor continues running, but workflows are only sent when enabled.

### Pause Rendering

**To pause Blender rendering** (but keep AI generation available):
- ☐ Uncheck "Refresh Viewport"

**To pause AI generation** (but keep rendering):
- ☐ Uncheck "Auto-Generate AI"

### Full Stop

**To stop everything:**
1. ☐ Uncheck "Refresh Viewport"
2. ☐ Uncheck "Auto-Generate AI"

**To resume:**
1. ☑️ Check "Refresh Viewport"
2. ☑️ Check "Auto-Generate AI"

---

## Session JSON Integration

The auto-generation flag is saved in `session.json`:

```json
{
  "flags": {
    "live_preview": true,
    "auto_generate": true,
    "autosave_every_sec": 5.0
  }
}
```

The server reads this flag every 3 seconds to determine whether to auto-trigger workflows.

---

## API Endpoints

### Check Auto-Generation Status

```bash
GET /auto_generate/status
```

**Response:**
```json
{
  "monitor_running": true,
  "auto_generate_enabled": true,
  "last_depth_mtime": 1698765432.123,
  "depth_exists": true,
  "session_exists": true
}
```

---

## Use Cases

### 1. Real-Time Design Exploration

**Scenario**: You're designing a character and want instant AI feedback

**Setup**:
- Enable auto-generation
- Set prompt: "cyberpunk character, neon lighting, detailed"
- Model in Blender
- Watch AI vision update in real-time

### 2. Iterative Scene Building

**Scenario**: Building an environment and want to see how AI interprets it

**Setup**:
- Enable auto-generation
- Set prompt: "gothic cathedral interior, dramatic lighting"
- Place objects, adjust camera
- AI vision shows full scene interpretation every 5 seconds

### 3. Animation Preview

**Scenario**: Creating an animation and want AI to visualize each frame

**Setup**:
- Enable auto-generation
- Animate camera/objects
- Play animation (scrub timeline)
- Each frame triggers new AI generation

---

## Troubleshooting

### ❌ "Auto-generate enabled but no workflows sent"

**Causes:**
1. Depth pass not updating (Refresh Viewport disabled)
2. ComfyUI not running
3. ComfyUI path not set correctly

**Fix:**
1. Check "Refresh Viewport" is enabled
2. Start ComfyUI at http://127.0.0.1:8188
3. Verify ComfyUI path in Blender preferences

---

### ⚠️ "Workflows sent but Blender viewport not updating"

**Causes:**
1. `current_ai.png` not being copied
2. Blender refresh interval too slow
3. Image permissions issue

**Fix:**
1. Check server console for "📸 Copied output to current_ai.png"
2. Toggle camera view (press `0`) to force refresh
3. Check file permissions in `data/temp/ai_vision/`

---

### 🐌 "Cycle is too slow"

**Cause**: ComfyUI processing takes too long

**Fix**:
1. Reduce image resolution in Blender settings
2. Simplify ComfyUI workflow (fewer nodes, faster models)
3. Upgrade GPU for faster processing

---

### 🔥 "Too many requests, ComfyUI queue backing up"

**Cause**: Blender renders faster than ComfyUI can process

**Fix**:
1. Increase Blender render interval (edit `RENDER_INTERVAL` in `workspace_setup.py`)
2. Pause auto-generation during intensive work
3. Let the queue clear before re-enabling

---

## Advanced Configuration

### Change Blender Render Interval

**File**: `scripts/addons/styleengine/workspace_setup.py`

```python
RENDER_INTERVAL = 5.0  # Change to 10.0 for slower updates
```

### Change Server Monitor Interval

**File**: `launcher/server.py`

```python
# In monitor_depth_changes()
await asyncio.sleep(3)  # Change to 5 for slower checks
```

### Change ComfyUI Timeout

**File**: `launcher/server.py`

```python
async def wait_for_comfy_completion(..., max_wait: int = 120):
    # Change max_wait to increase timeout
```

---

## Performance Tips

### For Best Performance:

1. **Use lower resolutions** (640x1536, 768x1344) for faster generation
2. **Simplify ComfyUI workflow** (fewer nodes = faster)
3. **Use fast models** (LCM, Lightning) for near real-time results
4. **Close unnecessary programs** to free GPU memory
5. **Adjust render intervals** to match your hardware capabilities

### Recommended Specs:

- **Minimum**: GTX 1660 Ti, 8GB VRAM, 16GB RAM
- **Recommended**: RTX 3060, 12GB VRAM, 32GB RAM
- **Optimal**: RTX 4070+, 16GB+ VRAM, 64GB RAM

---

## What's Happening Behind the Scenes

### Blender Side:

```python
# Every 5 seconds (auto_render_passes timer)
1. Set camera to ai_camera
2. Set render engine to Eevee Next
3. Render passes (Combined, Z, AO)
4. Save to data/temp/passes/
5. Update session.json timestamp
```

### Server Side:

```python
# Every 3 seconds (monitor_depth_changes task)
1. Read session.json
2. Check if auto_generate is enabled
3. Check depth0001.png modification time
4. If changed:
   a. Copy depth to ComfyUI input
   b. Inject session data into workflow
   c. Send to ComfyUI
   d. Monitor for completion
   e. Auto-copy output to current_ai.png
```

### ComfyUI Side:

```
1. Receive workflow via /prompt endpoint
2. Load depth0001.png from input folder
3. Process through nodes (LCM, samplers, etc.)
4. Save output to output folder
5. Server detects completion via /history endpoint
```

---

## Success Indicators

You know it's working when you see all of these:

1. **Dashboard** shows:
   - Monitor Status: ✅ Running
   - Auto-Generate: ✅ Enabled
   - Depth Pass: ✅ Available

2. **Server console** shows:
   - `🆕 New render pass detected!`
   - `🎨 Workflow sent to ComfyUI`
   - `📸 Copied output to current_ai.png`

3. **Blender viewport** shows:
   - New AI images appearing every 5-15 seconds
   - Images match your current 3D scene

4. **ComfyUI UI** shows:
   - Jobs completing successfully
   - No errors in console

---

## Limitations

- **Not suitable for** animation rendering (use manual triggering instead)
- **Resource intensive** (runs continuously)
- **Network latency** if ComfyUI is on different machine
- **File system delays** on slow drives (use SSD recommended)

---

## Future Enhancements

Planned features:
- [ ] Adjustable cycle speed (fast/medium/slow presets)
- [ ] Queue management (prevent backup)
- [ ] Adaptive timing (adjust based on ComfyUI speed)
- [ ] History tracking (save every generated image)
- [ ] WebSocket notifications (faster updates)
- [ ] Multi-camera support (multiple AI visions)

---

## Quick Reference

| Setting | Location | Effect |
|---------|----------|--------|
| Refresh Viewport | Blender panel | Enables render pass updates |
| Auto-Generate AI | Blender panel | Enables auto-workflow triggering |
| Render Interval | `workspace_setup.py` | How often Blender renders (default: 5s) |
| Monitor Interval | `server.py` | How often server checks for changes (default: 3s) |
| ComfyUI Timeout | `server.py` | Max wait for ComfyUI (default: 120s) |

---

## Congratulations! 🎉

You now have a fully automated, cyclical AI vision system integrated into your Blender workflow!

Experiment with different prompts, resolutions, and scene compositions to see how the AI interprets your 3D world in real-time.

Happy creating! 🚀✨

