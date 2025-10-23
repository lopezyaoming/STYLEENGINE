# Synchronized Render-Generate Cycle

## 🎯 Problem Solved

Previously, the system had a **queue backup problem**:
- Blender rendered passes every 5 seconds
- ComfyUI took 15-30 seconds to generate
- Result: Multiple workflows queued up
- By the time you saw output, it was based on old data

## ✅ Solution: Synchronous Cycle

The system now uses a **synchronized render-generate cycle** with no queue backup:

```
Blender Renders → Server Sends Workflow → ComfyUI Generates → Output Copied → Blender Renders Again
        ↑_______________________________________________________________________________|
```

**Key principle**: Blender only renders when the previous AI generation is complete.

---

## 🔄 How It Works

### The Cycle

```
1. Blender renders passes (Combined, Depth, AO)
   ↓
2. Server detects new combined0001.png
   ↓
3. Server checks: Is generation in progress?
   - YES → Wait, don't send workflow
   - NO → Send workflow to ComfyUI
   ↓
4. Server sets flag: generation_in_progress = True
   ↓
5. ComfyUI processes workflow
   ↓
6. Server monitors ComfyUI history API
   ↓
7. Generation complete!
   ↓
8. Server copies output to current_ai.png
   ↓
9. Server sets flag: generation_in_progress = False
   ↓
10. Blender's timer checks: Is generation complete?
    - YES → Render again (go to step 1)
    - NO → Wait 5 seconds, check again
```

### State Management

The server maintains two global flags:

```python
_generation_in_progress = False  # Is ComfyUI currently generating?
_last_generation_complete_time = 0  # When did last generation finish?
```

**Blender checks** these flags before rendering.  
**Server updates** these flags based on ComfyUI status.

---

## 🎛️ Synchronization Points

### Point 1: Server Monitor (monitor_depth_changes)

```python
# Before sending workflow:
if _generation_in_progress:
    print("Waiting for previous generation...")
    await asyncio.sleep(3)
    continue  # Don't send new workflow
```

**Effect**: Server won't send new workflows while one is in progress.

### Point 2: Blender Render Timer (auto_render_passes)

```python
# Before rendering:
if auto_generate_enabled:
    response = check_server_ready()
    if not response['ready']:
        print("Waiting for AI generation...")
        return RENDER_INTERVAL  # Try again in 5 seconds
```

**Effect**: Blender won't render if AI is still generating.

### Point 3: Completion Handler (wait_for_comfy_completion)

```python
# After copying output:
_generation_in_progress = False
_last_generation_complete_time = time.time()
print("Generation complete, ready for next render")
```

**Effect**: Signals that it's safe to render again.

---

## 📊 Timing Analysis

### Before (Queue Backup):
```
T+0s:  Blender renders
T+5s:  Blender renders (workflow 1 sent)
T+10s: Blender renders (workflow 2 sent)
T+15s: Blender renders (workflow 3 sent)
T+20s: Workflow 1 completes (shows 20s old data)
T+25s: Blender renders (workflow 4 sent)
T+30s: Workflow 2 completes (shows 25s old data)
...
Result: Always 20-30 seconds behind, 3-4 workflows queued
```

### After (Synchronized):
```
T+0s:  Blender renders → Workflow 1 sent → [LOCK]
T+5s:  Blender checks → LOCKED, wait
T+10s: Blender checks → LOCKED, wait
T+15s: Blender checks → LOCKED, wait
T+20s: Workflow 1 completes → [UNLOCK]
T+25s: Blender renders → Workflow 2 sent → [LOCK]
T+45s: Workflow 2 completes → [UNLOCK]
T+50s: Blender renders → Workflow 3 sent → [LOCK]
...
Result: Always shows latest data, 0 workflows queued
```

**Effective cycle time**: 20-30 seconds per iteration (depends on ComfyUI speed)

---

## 🚀 Benefits

### ✅ No Queue Backup
- Only 1 workflow in ComfyUI at a time
- No wasted computation on outdated data

### ✅ Always Fresh Data
- Every generation uses the latest render passes
- Every generation uses the latest prompt/settings

### ✅ Predictable Performance
- You know exactly when next update will happen
- No mysterious delays from queue backup

### ✅ Resource Efficient
- Blender doesn't render unnecessarily
- ComfyUI processes one thing at a time
- Lower GPU/CPU usage overall

### ✅ Responsive to Changes
- Change prompt → next cycle uses it
- Adjust sliders → next cycle uses them
- Move camera → next cycle captures it

---

## 🎯 API Endpoints

### `GET /render/ready`
**Purpose**: Check if Blender should render.

**Response**:
```json
{
  "ready": true,
  "generation_in_progress": false,
  "last_complete_time": 1698765432.123,
  "seconds_since_complete": 5.2
}
```

**Usage**:
- Blender calls this before rendering
- If `ready` is `false`, wait and try again
- If `ready` is `true`, proceed with render

### `GET /auto_generate/status`
**Purpose**: Monitor overall auto-generation status.

**Response**:
```json
{
  "monitor_running": true,
  "auto_generate_enabled": true,
  "generation_in_progress": false,
  "ready_for_render": true,
  "depth_exists": true,
  "session_exists": true
}
```

**Usage**:
- Dashboard uses this to show status
- `ready_for_render` = inverse of `generation_in_progress`

---

## 🎨 User Experience

### What You'll See

**Dashboard**:
- "🔄 Generating..." - ComfyUI is processing
- "✅ Enabled (Ready)" - Waiting for next render

**Blender Console**:
```
[Style Engine] Auto-rendering from ai_camera...
[Style Engine] Render complete
[Style Engine] 🆕 New combined pass detected!
[Style Engine] 🚀 Auto-triggering ComfyUI workflow...
[Style Engine] 🔒 Generation in progress, blocking new renders...
[Style Engine] ⏸️ Waiting for AI generation to complete...
[Style Engine] ⏸️ Waiting for AI generation to complete...
[Style Engine] ⏸️ Waiting for AI generation to complete...
[Style Engine] 📸 Copied output to current_ai.png
[Style Engine] ✅ Generation complete, ready for next render
[Style Engine] Auto-rendering from ai_camera...
```

**Server Console**:
```
[Style Engine] 🆕 New combined pass detected!
[Style Engine] 🚀 Auto-triggering ComfyUI workflow...
[Style Engine] 🎨 Workflow sent to ComfyUI (ID: abc-123)
[Style Engine] 🔒 Generation in progress, blocking new renders...
[Style Engine] Monitoring ComfyUI job: abc-123
[Style Engine] ✅ ComfyUI job complete!
[Style Engine] 📸 Copied output to current_ai.png
[Style Engine] ✅ Generation complete, ready for next render
```

### What You Won't See Anymore

❌ Long queues in ComfyUI  
❌ Outdated AI images  
❌ Confusing delays  
❌ Wasted renders  

---

## ⚙️ Configuration

### Adjust Check Interval

Blender checks server readiness every `RENDER_INTERVAL` seconds (default: 5s).

**To change**, edit `workspace_setup.py`:
```python
RENDER_INTERVAL = 5.0  # Change to 3.0 for faster checks
```

### Adjust Monitor Interval

Server checks for new passes every 3 seconds.

**To change**, edit `server.py` in `monitor_depth_changes()`:
```python
await asyncio.sleep(3)  # Change to 2 for faster detection
```

### Adjust ComfyUI Timeout

Server waits up to 120 seconds for ComfyUI to complete.

**To change**, edit `server.py` in `wait_for_comfy_completion()`:
```python
async def wait_for_comfy_completion(..., max_wait: int = 120):
    # Change max_wait to 180 for slower workflows
```

---

## 🐛 Troubleshooting

### ❌ "Always waiting for generation to complete"

**Cause**: `_generation_in_progress` stuck as `True`

**Fix**:
1. Restart the server
2. Check ComfyUI is running and responding
3. Check ComfyUI console for errors

### ⚠️ "Renders but never sends to ComfyUI"

**Cause**: Auto-generate might be disabled

**Fix**:
1. Check "Auto-Generate AI" checkbox is enabled in Blender
2. Check `/auto_generate/status` endpoint shows `auto_generate_enabled: true`

### 🐌 "Cycle is very slow"

**Cause**: ComfyUI workflow takes a long time

**Fix**:
1. Switch to faster workflow (BasicLCM, DepthLCM)
2. Reduce resolution in Blender
3. Reduce Steps slider value
4. This is working as designed - cycle waits for quality

### 🔄 "Want faster updates, willing to accept queue"

**Solution**: Disable the synchronization by commenting out the ready check in `auto_render_passes()`:

```python
# if props.auto_generate:
#     try:
#         req = urllib.request.Request('http://localhost:8000/render/ready')
#         ...
```

**Note**: This brings back the queue backup problem!

---

## 📈 Performance Comparison

| Metric | Before (Async) | After (Sync) |
|--------|----------------|--------------|
| **Queue Size** | 3-5 workflows | 0-1 workflows |
| **Data Freshness** | 20-30s behind | Real-time |
| **CPU Usage** | High (constant) | Moderate (pulsed) |
| **GPU Usage** | 100% (queued) | Efficient (on-demand) |
| **Cycle Time** | 5s (false speed) | 20-30s (true speed) |
| **Wasted Renders** | Many | None |
| **Predictability** | Poor | Excellent |

---

## 🔮 Future Enhancements

Planned improvements:
- [ ] WebSocket notifications (no polling needed)
- [ ] Parallel rendering (render while AI generates, use for next cycle)
- [ ] Adaptive timing (auto-adjust based on ComfyUI speed)
- [ ] Queue limit option (allow 1-2 queued workflows)
- [ ] Priority system (interrupt low-priority for high-priority)

---

## 📚 Technical Details

### State Machine

```
State: IDLE
  → Blender renders
  → New passes detected
  → Transition to GENERATING

State: GENERATING
  → Workflow sent to ComfyUI
  → _generation_in_progress = True
  → Monitor ComfyUI status
  → On complete: copy output
  → _generation_in_progress = False
  → Transition to IDLE

State: IDLE (again)
  → Blender checks ready
  → Ready = True
  → Blender renders
  → Cycle repeats
```

### Race Condition Prevention

**Q**: What if Blender renders just as generation completes?  
**A**: No problem! Blender checks `ready` status immediately before rendering. Even if status changes between check and render, the new render will trigger a new cycle.

**Q**: What if server crashes mid-generation?  
**A**: `_generation_in_progress` resets to `False` on server startup. First render after restart will work normally.

**Q**: What if multiple Blender instances connect?  
**A**: Each Blender independently checks `ready` status. Only one will succeed in triggering generation (first one to update combined pass). Others will see `in_progress = True` and wait.

---

## ✅ Summary

**Old way**: Blender renders every 5s, floods ComfyUI, queue backup  
**New way**: Blender waits for AI, one cycle at a time, always fresh

**Result**: True real-time AI vision with predictable, efficient performance! 🚀✨

---

## 🎓 Best Practices

1. **Let it breathe**: Don't expect 5-second cycles with SDXLworkflow. 20-30 seconds is normal and healthy.
2. **Match workflow to need**: Use fast workflows (BasicLCM, DepthLCM) for iteration, slow workflows (SDXLworkflow) for finals.
3. **Trust the system**: The "waiting" is good! It means you're getting the latest data.
4. **Monitor the logs**: Console messages tell you exactly what's happening.
5. **Adjust if needed**: RENDER_INTERVAL can be lowered for faster checks (but same cycle time).

---

Enjoy synchronized, queue-free AI vision! 🎨✨

