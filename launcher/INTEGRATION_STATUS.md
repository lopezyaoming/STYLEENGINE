# Style Engine Integration Status

## ✅ What's Working Now

### 1. Dynamic Workflow Integration

The server now sends workflows to ComfyUI with **fully dynamic data** from Blender!

**Data Flow:**
```
Blender → session.json → FastAPI → Modified Workflow → ComfyUI
                ↓
         depth0001.png → ComfyUI/input/
```

**What Gets Injected:**

| Workflow Node | Parameter | Source | Value |
|--------------|-----------|--------|-------|
| Node 15 (LoadImage) | `image` | `data/temp/passes/depth0001.png` | Copied to ComfyUI input |
| Node 25 (PrimitiveString) | `value` | `session.json` → `global_prompt` | User's prompt from UI |
| Node 5 (EmptyLatentImage) | `width` | `session.json` → `resolution.width` | 1024 (or user-selected) |
| Node 5 (EmptyLatentImage) | `height` | `session.json` → `resolution.height` | 1024 (or user-selected) |
| Node 9 (SaveImage) | `filename_prefix` | Static | `style_engine_output` |

### 2. Current Workflow

1. **Blender renders** → Creates `depth0001.png` in `data/temp/passes/`
2. **Blender updates** → Updates `session.json` with prompt/resolution
3. **User clicks** → "🧪 Send Test Workflow" button in dashboard
4. **Server reads** → `session.json` and `depth0001.png`
5. **Server copies** → `depth0001.png` to `ComfyUI/input/`
6. **Server modifies** → BasicLCM.json with dynamic data
7. **Server sends** → Modified workflow to ComfyUI
8. **ComfyUI processes** → Generates image
9. **ComfyUI saves** → `style_engine_output_00001.png` to output folder
10. **Manual step** → Copy output to `current_ai.png`

### 3. Example Output

When you click "Send Test Workflow", you see:

```
Activity Log:
[12:34:56] Sending workflow to ComfyUI with dynamic data...
[12:34:57] ✅ Workflow sent! Prompt ID: abc-123-xyz
[12:34:57]    ├─ Prompt: "This is scene 1. Gotham, Hamster, Dark"
[12:34:57]    ├─ Resolution: 1024x1024
[12:34:57]    ├─ Depth: depth0001.png (copied to ComfyUI input)
[12:34:57]    └─ Output: style_engine_output_xxxxx.png → will need manual copy
[12:34:57] 📋 Next steps:
[12:34:57]    1. Wait for ComfyUI to finish processing
[12:34:57]    2. Check ComfyUI output folder: C:\...\ComfyUI\output
[12:34:57]    3. Find the newest style_engine_output_*.png file
[12:34:57]    4. Copy it to: C:\...\data\temp\ai_vision\current_ai.png
[12:34:57]    5. (Future: This will be automated)
```

---

## 🔄 Next Steps to Complete the Loop

### Step 1: Automatic Output Copy

**Current**: Manual copy required  
**Goal**: Automatically copy ComfyUI output to `current_ai.png`

**Implementation Options:**

#### Option A: Poll ComfyUI History API
```python
@app.get("/debug/get_latest_output/{prompt_id}")
async def get_latest_output(prompt_id: str):
    # 1. Poll ComfyUI history endpoint
    # 2. Wait for completion
    # 3. Get output filename
    # 4. Copy from ComfyUI/output to current_ai.png
    # 5. Return success
```

#### Option B: WebSocket Monitoring
```python
# Connect to ComfyUI WebSocket
# Listen for completion messages
# Auto-copy when done
```

#### Option C: Simple Polling After Send
```python
# After sending workflow:
# 1. Wait 10 seconds (or estimate based on steps)
# 2. Find newest file in ComfyUI/output with prefix "style_engine_output"
# 3. Copy to current_ai.png
```

**Recommendation**: Start with Option C (simplest), upgrade to A or B later.

---

### Step 2: Automatic Trigger from Blender

**Current**: Manual button click  
**Goal**: Auto-trigger when Blender finishes rendering

**Implementation Options:**

#### Option A: File Watching (Recommended)
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PassesWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("depth0001.png"):
            # Trigger workflow send
            asyncio.create_task(send_workflow_to_comfy())

# Start observer on startup
```

#### Option B: Polling (Simpler)
```python
# Check depth0001.png timestamp every 2 seconds
# If newer than last check, trigger workflow
```

#### Option C: Blender Callback (Most Reliable)
```python
# In Blender addon (workspace_setup.py):
def on_render_complete(scene):
    # Call FastAPI endpoint
    requests.post("http://localhost:8000/trigger/generation")
```

**Recommendation**: Option C (most reliable) + Option A (backup)

---

### Step 3: Complete the Real-Time Loop

Once Steps 1 & 2 are done:

```
┌─────────────────────────────────────────────────────────┐
│                    REAL-TIME LOOP                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Blender renders (every 5 sec)                       │
│     └→ Creates depth0001.png                            │
│     └→ Updates session.json                             │
│          ↓                                               │
│  2. FastAPI detects change (file watch/callback)        │
│     └→ Reads session.json                               │
│     └→ Copies depth0001.png to ComfyUI                  │
│     └→ Injects dynamic data                             │
│     └→ Sends workflow to ComfyUI                        │
│          ↓                                               │
│  3. ComfyUI processes (~5-10 sec with LCM)              │
│     └→ Generates image                                  │
│     └→ Saves style_engine_output_xxxxx.png              │
│          ↓                                               │
│  4. FastAPI monitors completion                         │
│     └→ Detects new output file                          │
│     └→ Copies to current_ai.png                         │
│          ↓                                               │
│  5. Blender refreshes (auto, every 2 sec)               │
│     └→ Shows new AI image in camera background          │
│                                                          │
│  → LOOP REPEATS                                         │
│                                                          │
│  Total cycle time: ~10-15 seconds                       │
│  (5s Blender render + 5-10s ComfyUI generation)         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Priority

### Phase 1 (Now): Manual Testing ✅
- [x] Read session.json
- [x] Copy depth pass to ComfyUI
- [x] Inject dynamic data
- [x] Send to ComfyUI
- [x] Manual copy of output

### Phase 2: Auto-Copy Output
- [ ] Add endpoint to monitor ComfyUI completion
- [ ] Auto-copy output to current_ai.png
- [ ] Test full workflow

### Phase 3: Auto-Trigger
- [ ] Add file watcher for depth0001.png
- [ ] OR add Blender callback endpoint
- [ ] Auto-trigger workflow send

### Phase 4: Polish
- [ ] Error handling & retries
- [ ] Progress indicators
- [ ] Queue management (prevent flooding)
- [ ] Performance optimization

---

## 📊 Current Test Results

### What You Should See:

1. **In Blender:**
   - Session ID: `session-0001`
   - Global Prompt: `"This is scene 1. Gotham, Hamster, Dark"`
   - Resolution: `1024x1024`
   - Refresh Viewport: ON

2. **In Dashboard:**
   - Session info populated
   - ComfyUI status: ✅ ONLINE
   - Click "Send Test Workflow"

3. **In ComfyUI:**
   - Workflow starts processing
   - Uses your prompt and depth map
   - Generates at 1024x1024
   - Saves to output folder

4. **Result:**
   - Image in `ComfyUI/output/style_engine_output_00001.png`
   - Shows your scene rendered with the prompt style!

---

## 🐛 Troubleshooting

### "Depth pass not found"
- Make sure "Refresh Viewport" is ON in Blender
- Wait for Blender to render (happens every 5 seconds)
- Check `data/temp/passes/depth0001.png` exists

### "ComfyUI input folder not found"
- Check ComfyUI installation path
- Server looks in:
  1. `C:\Coding\STYLEENGINE\ComfyUI\input`
  2. `C:\Coding\ComfyUI\input` (sibling folder)
  3. `C:\Users\<you>\ComfyUI\input` (home directory)

### "Workflow processes but no visible style"
- Check that ComfyUI has the required models:
  - `sd_xl_base_1.0.safetensors` in `models/checkpoints/`
  - `lcm_lora_sdxl.safetensors` in `models/loras/`
  - `control-lora-depth-rank256.safetensors` in `models/controlnet/`

### "Image is all black/white"
- The depth map might need adjustment
- Try a different scene with more varied depth
- Adjust the "Depth Influence" slider in Blender (0.5 default)

---

## 🎉 Success Criteria

You'll know it's fully working when:

1. ✅ You can type a prompt in Blender
2. ✅ Click "Send Test Workflow" in dashboard
3. ✅ ComfyUI generates an image with your prompt
4. ✅ The depth from Blender influences the generation
5. ✅ The output is at the correct resolution

**Then you're ready for automation!**


