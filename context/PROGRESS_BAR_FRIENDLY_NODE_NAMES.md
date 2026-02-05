# Progress Bar Friendly Node Names

**Date**: 2026-01-26  
**Feature**: Display meaningful node names in progress bar instead of raw "Node 6" format

## Problem

The progress bar was displaying raw node identifiers like "Node 6", "Node 23" which didn't tell users what was actually happening during workflow execution.

## Solution

Implemented a workflow JSON lookup system that:
1. Stores the workflow JSON when it's submitted to ComfyUI
2. Extracts node ID from "Node 6" format
3. Looks up the node in the workflow JSON
4. Displays the `class_type` field (e.g., "KSampler", "VAEDecode", "SaveImage")

## Implementation

### Modified Files

#### 1. `progress_bar.py`

**Added to `BridgePollerState` class:**
```python
# Current workflow JSON for node name lookup
current_workflow = None
```

**Added helper function:**
```python
def _get_friendly_node_name(raw_node_name):
    """
    Convert raw node name (e.g., "Node 6") to friendly name (e.g., "KSampler").
    Looks up the node ID in the current workflow JSON to get the class_type.
    """
```

**Updated polling logic:**
- Calls `_get_friendly_node_name()` before displaying node name
- Clears workflow when job completes (idle state)

**Added public API:**
```python
def set_current_workflow(workflow_json):
    """
    Set the current workflow JSON for node name lookups.
    Call this immediately after submitting a workflow to ComfyUI.
    """
```

#### 2. `workspace_setup.py` (1 location)

Added after `queue_prompt()` call:
```python
# Store workflow for progress bar node name lookup
from . import progress_bar
progress_bar.set_current_workflow(workflow_json)
```

**Location:** Line ~2916 (main image generation)

#### 3. `ui_panel.py` (4 locations)

Added after each `queue_prompt()` call:
- **Refine Prompt** operator (~line 3047)
- **Generate Image Description** operator (~line 3197)
- **Generate Image Description From File** operator (~line 3378)
- **Generate Image Description From Viewport** operator (~line 3619)

#### 4. `pie_menu.py` (3 locations)

Added after each `queue_prompt()` call:
- **UV Texture** operator (~line 229)
- **Create Object** operator (~line 441)
- **Create Textured Object** operator (~line 655)

## Workflow JSON Structure

Workflows are structured as:
```json
{
  "6": {
    "class_type": "KSampler",
    "inputs": { ... },
    "_meta": { "title": "KSampler" }
  },
  "23": {
    "class_type": "VAEDecode",
    "inputs": { ... },
    "_meta": { "title": "VAE Decode" }
  }
}
```

When the bridge sends `"node_name": "Node 6"`, we:
1. Extract `"6"`
2. Look up `workflow_json["6"]["class_type"]`
3. Display `"KSampler"` instead

## Example Node Name Mappings

| Raw Name | Friendly Name | Description |
|----------|---------------|-------------|
| Node 3 | KSampler | Main sampling node |
| Node 4 | CheckpointLoaderSimple | Model loader |
| Node 14 | CLIPTextEncode | Prompt encoder |
| Node 23 | VAEDecode | VAE decoder |
| Node 42 | SaveImage | Image saver |
| Node 135 | SetNode | Value setter |

## Benefits

1. **User-friendly**: Shows what's actually happening ("KSampler" vs "Node 3")
2. **Educational**: Users learn ComfyUI node types
3. **Debugging**: Easier to identify slow/stuck nodes
4. **No overhead**: Lookup is instantaneous (dict lookup)
5. **Automatic cleanup**: Workflow cleared when job completes

## Error Handling

- If workflow JSON is not set: Falls back to raw name ("Node 6")
- If node ID not found: Falls back to raw name
- If any error during lookup: Falls back to raw name
- Graceful degradation ensures progress bar always works

## Testing Recommendations

1. Generate an image and watch the progress bar show:
   - "CheckpointLoaderSimple"
   - "CLIPTextEncode"
   - "KSampler"
   - "VAEDecode"
   - "SaveImage"

2. Generate text description and watch:
   - "LoadImage"
   - "Griptape Run: Agent"
   - "Griptape Display: Text"

3. Generate 3D object and watch:
   - "TripoSRModelLoader"
   - "TripoSRSampler"
   - "SaveGLTF"

All should show friendly names instead of "Node X" format.
