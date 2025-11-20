# GCS Generation Status Indicator
**Date:** November 20, 2025  
**Feature:** Minimal UI status display for GCS workflow progress  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Overview

Added a clean, minimal status indicator to the Style Engine UI panel that shows:
1. **Current generation status** (Generating/Queued with elapsed time)
2. **Last generation time** (for comparison with previous workflows)
3. **Ready state** (when idle)

The indicator is **laconic** and **non-intrusive** - only appears when relevant and provides just enough information for users to track progress.

---

## 📊 What It Shows

### During Generation
```
┌─────────────────────────────────┐
│ Generating: 15s     [ANIMATION] │
│ Previous: 23s       [CLOCK]     │
└─────────────────────────────────┘
```

### When Idle (After Generation)
```
┌─────────────────────────────────┐
│ Ready               [CHECKMARK] │
│ Previous: 23s       [CLOCK]     │
└─────────────────────────────────┘
```

### When Queued
```
┌─────────────────────────────────┐
│ Queued: 3s          [TIME]      │
│ Previous: 23s       [CLOCK]     │
└─────────────────────────────────┘
```

---

## 🛠️ Implementation Details

### 1. Backend Tracking (`runcomfy_polling.py`)

#### Added Class Variable
```python
class RunComfyPoller:
    active_requests = {}
    last_generation_time = 0  # NEW: Track last completed generation duration
```

#### Record Generation Time on Completion
```python
# In _poll_tick() - Server API mode
if status_str == 'success':
    cls.last_generation_time = int(elapsed)  # Record duration
    state.callback(success=True, result=prompt_data, workflow_type=state.workflow_type)
    completed.append(request_id)

# In _poll_tick() - Serverless API mode
if state.status == 'completed':
    cls.last_generation_time = int(elapsed)  # Record duration
    result = client.get_result(state.deployment_id, request_id)
    state.callback(success=True, result=result, workflow_type=state.workflow_type)
    completed.append(request_id)
```

#### New Method: `get_status_summary()`
```python
@classmethod
def get_status_summary(cls):
    """
    Get concise status summary for UI display.
    
    Returns:
        dict: {
            'is_generating': bool,
            'elapsed': int (seconds),
            'last_generation_time': int (seconds),
            'status_text': str ('Idle'/'Queued'/'Generating'/'Processing')
        }
    """
    if not cls.active_requests:
        return {
            'is_generating': False,
            'elapsed': 0,
            'last_generation_time': cls.last_generation_time,
            'status_text': 'Idle'
        }
    
    # Get first active request
    state = next(iter(cls.active_requests.values()))
    current_time = time.time()
    elapsed = int(current_time - state.start_time)
    
    # Determine status text
    if state.status == 'in_queue':
        status_text = 'Queued'
    elif state.status == 'in_progress':
        status_text = 'Generating'
    else:
        status_text = 'Processing'
    
    return {
        'is_generating': True,
        'elapsed': elapsed,
        'last_generation_time': cls.last_generation_time,
        'status_text': status_text
    }
```

---

### 2. UI Display (`ui_panel.py`)

#### Location
Added right after the "Output Path" section, before "Prompt Builder".

#### Implementation
```python
# --- Generation Status (MINIMAL) ---
try:
    from . import runcomfy_polling
    from . import runcomfy_deployment
    
    # Only show status if using GCS mode
    prefs = context.preferences.addons['styleengine'].preferences
    if hasattr(prefs, 'api_backend') and prefs.api_backend == 'GCS':
        status = runcomfy_polling.RunComfyPoller.get_status_summary()
        
        # Only show box if generating or if we have last generation time
        if status['is_generating'] or status['last_generation_time'] > 0:
            layout.separator()
            status_box = layout.box()
            row = status_box.row()
            
            if status['is_generating']:
                # Show current generation status
                icon = 'RENDER_ANIMATION' if status['status_text'] == 'Generating' else 'TIME'
                row.label(text=f"{status['status_text']}: {status['elapsed']}s", icon=icon)
            else:
                # Show idle status with last generation time
                row.label(text="Ready", icon='CHECKMARK')
            
            # Show last generation time if available
            if status['last_generation_time'] > 0:
                row = status_box.row()
                row.scale_y = 0.8
                row.label(text=f"Previous: {status['last_generation_time']}s", icon='SORTTIME')
except Exception as e:
    # Silently fail if status unavailable
    pass
```

---

## 🎨 Design Principles

### 1. **Minimal & Laconic**
- Only 2 lines of information maximum
- No verbose messages or excessive details
- Compact box that doesn't dominate the UI

### 2. **Contextual Display**
- Only shows when relevant (GCS mode active)
- Only shows when generating OR when there's a previous time to display
- Hides completely when not needed

### 3. **Useful Comparison**
- Shows "Previous: Xs" so users can compare current generation with last one
- Helps users estimate remaining time based on past performance
- Persists across generations for reference

### 4. **Clear Status Icons**
- `RENDER_ANIMATION` - Active generation (animated icon)
- `TIME` - Queued (waiting)
- `CHECKMARK` - Ready (idle)
- `SORTTIME` - Previous time (clock icon)

### 5. **Non-Intrusive**
- Wrapped in try/except to never break the UI
- Silently fails if polling system unavailable
- Doesn't require user interaction

---

## 🔄 Status Flow

```
User Triggers Generation
         ↓
    [Queued: 2s]
         ↓
  [Generating: 5s]
         ↓
  [Generating: 15s]
         ↓
  [Generating: 23s]
         ↓
    [Complete!]
         ↓
     [Ready]
  [Previous: 23s]  ← Persists for comparison
         ↓
User Triggers Again
         ↓
  [Generating: 8s]
  [Previous: 23s]  ← Can compare: "Faster than last time!"
```

---

## 📏 UI Dimensions

### Box Size
- **Width:** Full panel width (auto)
- **Height:** 2 rows (compact)
  - Row 1: Current status (normal scale)
  - Row 2: Previous time (0.8 scale - smaller)

### Text Format
- **Current status:** `"Status: Xs"` (e.g., "Generating: 15s")
- **Previous time:** `"Previous: Xs"` (e.g., "Previous: 23s")

### Spacing
- `layout.separator()` before box (visual breathing room)
- No separator after (flows into Prompt Builder)

---

## 🎯 User Benefits

### 1. **Progress Awareness**
Users know the workflow is running and can see elapsed time incrementing.

### 2. **Time Estimation**
By comparing current elapsed time with previous generation time, users can estimate:
- "Last one took 23s, I'm at 15s now, probably ~8s left"
- "This is taking longer than usual, maybe it's more complex"

### 3. **Workflow Validation**
Users can validate their workflow performance:
- "My optimized workflow went from 45s to 23s - success!"
- "Adding more reference images increased time from 20s to 35s"

### 4. **Server Confirmation**
The status appearing confirms the GCS server connection is active and processing.

### 5. **No Guesswork**
Instead of wondering "Is it working?", users have clear visual feedback.

---

## 🧪 Testing Scenarios

### Scenario 1: First Generation (No Previous Time)
```
Before: (no status box shown)
During: [Generating: 15s]
After:  [Ready] [Previous: 15s]
```

### Scenario 2: Subsequent Generations
```
Before: [Ready] [Previous: 23s]
During: [Generating: 8s] [Previous: 23s]
After:  [Ready] [Previous: 8s]  ← Updated
```

### Scenario 3: Queue Wait
```
[Queued: 3s] [Previous: 23s]
[Queued: 8s] [Previous: 23s]
[Generating: 2s] [Previous: 23s]
```

### Scenario 4: Switch to RunComfy Mode
```
(Status box disappears - only shows for GCS mode)
```

### Scenario 5: Blender Restart
```
(Previous time resets to 0, box hidden until first generation)
```

---

## 🔧 Configuration

### Enable/Disable
The status indicator is **always enabled** for GCS mode. No user configuration needed.

### Visibility Logic
```python
# Shows if:
if api_backend == 'GCS' AND (is_generating OR last_generation_time > 0):
    # Display status box
```

### Update Frequency
- Updates every time the UI redraws (typically 60 FPS)
- Elapsed time increments in real-time
- No performance impact (simple dict lookup)

---

## 🚀 Future Enhancements (Optional)

### 1. **Progress Bar**
Add a visual progress bar (requires WebSocket implementation):
```python
status_box.progress(
    factor=0.65,  # 65% complete
    type='BAR',
    text="65%"
)
```

### 2. **Estimated Time Remaining**
Calculate based on previous generation time:
```python
if status['is_generating'] and status['last_generation_time'] > 0:
    remaining = max(0, status['last_generation_time'] - status['elapsed'])
    row.label(text=f"Est. remaining: {remaining}s", icon='TIME')
```

### 3. **Cancel Button**
Allow users to cancel in-progress generations:
```python
if status['is_generating']:
    row.operator("style_engine.cancel_generation", text="", icon='X')
```

### 4. **Average Time Tracking**
Track average of last 5 generations for better estimation:
```python
last_5_times = [23, 25, 22, 24, 23]
avg_time = sum(last_5_times) / len(last_5_times)  # 23.4s
```

---

## 📝 Code Locations

### Modified Files
1. **`runcomfy_polling.py`**
   - Line ~51: Added `last_generation_time` class variable
   - Line ~136: Record time on Server API completion
   - Line ~191: Record time on Serverless API completion
   - Line ~318: Added `get_status_summary()` method

2. **`ui_panel.py`**
   - Line ~1586: Added status indicator after Output Path section

### Dependencies
- `runcomfy_polling.RunComfyPoller` - Status tracking
- `runcomfy_deployment.is_server_mode()` - Mode detection (optional, using prefs instead)
- `bpy.types.AddonPreferences` - API backend preference

---

## ✅ Verification Checklist

- [x] Status shows "Generating: Xs" during active generation
- [x] Status shows "Queued: Xs" when waiting in queue
- [x] Status shows "Ready" when idle
- [x] Previous time displays correctly after completion
- [x] Previous time persists across multiple generations
- [x] Previous time updates with each new completion
- [x] Status only shows in GCS mode
- [x] Status hidden in RunComfy mode
- [x] No errors if polling system unavailable
- [x] UI remains responsive during generation
- [x] Icons display correctly for each status
- [x] Text is readable and concise
- [x] Box doesn't dominate the UI
- [x] Spacing is appropriate

---

## 🎓 Key Takeaways

1. **Less is More** - Minimal UI with maximum information density
2. **Contextual Display** - Only show when relevant
3. **Comparative Data** - Previous time enables user estimation
4. **Fail-Safe Design** - Wrapped in try/except to never break UI
5. **Mode-Specific** - Only shows for GCS mode where it's relevant

---

**Author:** Style Engine Development Team  
**Last Updated:** November 20, 2025  
**Version:** 1.0.0

