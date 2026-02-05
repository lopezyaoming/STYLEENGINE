# Text Operators Non-Blocking Fix

**Date**: 2026-01-26  
**Issue**: Progress bar only showed updates for image generation workflows, not text generation workflows  
**Root Cause**: Text generation operators used blocking `while` loops that froze the Blender UI, preventing progress bar updates

## Changes Made

### 1. Added Helper Function

Added `_extract_text_from_griptape_output(outputs)` in `ui_panel.py` (before `WM_OT_RefinePrompt` class):
- Centralized text extraction logic from Griptape workflow outputs
- Tries multiple node IDs (17, 19, 20) and output formats
- Handles list-of-characters format, dict keys, and string formats

### 2. Converted Four Text Operators to Non-Blocking Polling

All four operators now use `runcomfy_polling.RunComfyPoller.start_polling()` instead of blocking `while` loops:

#### 2.1 `WM_OT_RefinePrompt` (Refine Prompt)
- **Before**: Blocking while loop (lines 3054-3200)
- **After**: Non-blocking polling with callback (lines 3047-3107)
- **Workflow**: `Text/TextRefine.json`
- **Callback**: Updates `<p>` tag in text editor when completed

#### 2.2 `WM_OT_GenerateImageDescription` (Describe Current Image)
- **Before**: Blocking while loop (lines 3205-3330)
- **After**: Non-blocking polling with callback (lines 3197-3262)
- **Workflow**: `Text/TextImage.json`
- **Callback**: Updates `<v>` tag in text editor when completed

#### 2.3 `WM_OT_GenerateImageDescriptionFromFile` (Describe Image from File)
- **Before**: Blocking while loop (lines 3386-3496)
- **After**: Non-blocking polling with callback (lines 3378-3460)
- **Workflow**: `Text/TextImage.json`
- **Callback**: Appends to `<v>` tag in text editor when completed

#### 2.4 `WM_OT_GenerateImageDescriptionFromViewport` (Describe Viewport)
- **Before**: Blocking while loop (lines 3624-3733)
- **After**: Non-blocking polling with callback (lines 3616-3697)
- **Workflow**: `Text/TextViewport.json`
- **Callback**: Appends to `<v>` tag in text editor when completed

## Technical Details

### Non-Blocking Pattern

Each operator now follows this pattern:

```python
# 1. Submit workflow
response = server_client.queue_prompt(workflow)
prompt_id = response['prompt_id']

# 2. Define callback
def on_complete(success, result=None, error=None, workflow_type=None):
    if not success:
        print(f"Failed: {error}")
        return
    
    # Extract text using helper
    text = _extract_text_from_griptape_output(result.get('outputs', {}))
    
    # Update text editor
    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
    # ... update text block ...
    
    # Save snapshot
    workspace_setup.save_prompt_snapshot(bpy.context, prefix="...")

# 3. Start non-blocking polling
runcomfy_polling.RunComfyPoller.start_polling(
    deployment_id='server',
    request_id=prompt_id,
    callback=on_complete,
    workflow_type='text'
)

return {'FINISHED'}  # Operator returns immediately
```

### Key Benefits

1. **Progress Bar Works**: UI no longer freezes, progress bar can update in real-time
2. **Responsive Blender**: Users can continue working in Blender while text workflows run
3. **Consistent with Image Workflows**: All workflows now use the same non-blocking polling system
4. **Cleaner Code**: Removed ~150 lines of duplicate text extraction logic per operator

## Expected Behavior

### Before
- Text workflows: Progress bar stuck at 0%, Blender UI frozen
- Image workflows: Progress bar updates, UI responsive
- 3D object workflows: Progress bar updates, UI responsive

### After
- Text workflows: Progress bar updates, UI responsive
- Image workflows: Progress bar updates, UI responsive (no change)
- 3D object workflows: Progress bar updates, UI responsive (no change)

## Testing Recommendations

1. **Refine Prompt**: Click "Refine Prompt" button, watch progress bar update
2. **Describe Current Image**: Generate image, then click "Describe Current Image", watch progress bar
3. **Describe Image from File**: Click "Describe Image from File", select a jpg/png, watch progress bar
4. **Describe Viewport**: Click "Describe Viewport", watch progress bar update during render + description

All operators should now show real-time progress in the N-panel progress bar.

## Files Modified

- `scripts/addons/styleengine/ui_panel.py`:
  - Added `_extract_text_from_griptape_output()` helper function
  - Converted `WM_OT_RefinePrompt` to non-blocking
  - Converted `WM_OT_GenerateImageDescription` to non-blocking
  - Converted `WM_OT_GenerateImageDescriptionFromFile` to non-blocking
  - Converted `WM_OT_GenerateImageDescriptionFromViewport` to non-blocking
  - Total: ~500 lines refactored, net reduction of ~300 lines

## Related Files (No Changes Needed)

- `scripts/addons/styleengine/runcomfy_polling.py`: Already supports text workflows via `workflow_type='text'`
- `scripts/bridge.py`: Already listens to all ComfyUI WebSocket messages (no filtering by workflow type)
- `scripts/addons/styleengine/progress_bar.py`: Already polls bridge service for all workflows

## Notes

- Text extraction from Griptape outputs can be complex (list of characters, nested dicts, etc.)
- Helper function handles all known output formats
- Callbacks use `bpy.context` instead of `context` parameter (callbacks run in different context)
- All operators properly save prompt history snapshots in callbacks
