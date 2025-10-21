# Style Engine - Session JSON Schema Documentation

## Overview

The `session.json` file is the central communication hub between Style Engine (Blender) and external AI generation systems. It's automatically created and updated in real-time as you work, storing every detail about your current session, settings, and creative intent.

**Location**: `data/temp/ai_vision/session.json`

**Update Behavior**: 
- Updates immediately when you change any UI setting
- Updates when you add/modify/delete object groups
- Updates when the workspace renders (timestamps)
- Uses atomic writes (temporary file → rename) to prevent corruption

---

## Full Schema Structure

```json
{
  "session_id": "string",
  "version": "string",
  "timestamp": "ISO 8601 datetime string",
  "scene_ref": {
    "blend_path": "string",
    "scene_name": "string",
    "camera_name": "string"
  },
  "agent_id": "string",
  "resolution": {
    "preset": "string",
    "width": integer,
    "height": integer
  },
  "lookup": "string",
  "global_prompt": "string",
  "depth_influence": float (0.0 - 1.0),
  "silhouette_influence": float (0.0 - 1.0),
  "objects": [
    {
      "group_id": "string",
      "label": "string",
      "object_ids": ["string"],
      "pass_index": integer,
      "keywords": ["string"],
      "mask": {
        "export": boolean,
        "type": "string",
        "path": "string"
      }
    }
  ],
  "routing": {
    "temp_dir": "string",
    "preview_out": "string",
    "passes_dir": "string",
    "commits_dir": "string"
  },
  "flags": {
    "live_preview": boolean,
    "autosave_every_sec": float
  }
}
```

---

## Field-by-Field Explanation

### Top-Level Fields

#### `session_id`
- **Type**: String
- **Purpose**: Unique identifier for this workflow session
- **Set By**: User in "Workspace Setup" UI
- **Default**: `"session-0001"`
- **Example**: `"project-cityscape-night-001"`
- **Use Case**: 
  - Organize multiple projects/sessions
  - Track different iterations of the same project
  - Future database/logging integration for AI generation history

#### `version`
- **Type**: String (semantic versioning)
- **Purpose**: Schema version number
- **Set By**: Automatically by Style Engine
- **Current**: `"0.1.0"`
- **Use Case**: 
  - Ensures compatibility between Blender addon and AI agents
  - Allows graceful handling of schema updates
  - External tools can check version before parsing

#### `timestamp`
- **Type**: String (ISO 8601 format with Z timezone)
- **Purpose**: Last update time
- **Set By**: Automatically updated on every JSON write
- **Example**: `"2025-10-21T22:01:47.078584Z"`
- **Use Case**:
  - File watchers can detect changes
  - Debugging: know when last update occurred
  - Session history and logging

---

### `scene_ref` Object

Contains references to the Blender file and scene being worked on.

#### `scene_ref.blend_path`
- **Type**: String (file path)
- **Purpose**: Path to the Blender file
- **Default**: `"//"` (means unsaved/untitled)
- **Example**: `"C:/Projects/Cityscape/scene_v01.blend"`
- **Use Case**:
  - Link generated images back to source file
  - Multi-file project management
  - Archiving and version control

#### `scene_ref.scene_name`
- **Type**: String
- **Purpose**: Name of the active Blender scene
- **Default**: `"Scene"`
- **Example**: `"CityBlock_01"`
- **Use Case**:
  - When a Blender file has multiple scenes
  - Helps AI agents understand context
  - Logging and organization

#### `scene_ref.camera_name`
- **Type**: String
- **Purpose**: Name of the AI vision camera
- **Fixed**: Always `"ai_camera"`
- **Use Case**:
  - Ensures AI agents render from the correct viewpoint
  - Future multi-camera workflows

---

### `agent_id`
- **Type**: String (identifier)
- **Purpose**: Selects which AI agent should process this session
- **Fixed**: Currently `"agent.comfy.local.v1"`
- **Future**: Will be selectable from a registry
- **Format**: `"agent.<platform>.<location>.<version>"`
- **Use Case**:
  - Different AI systems (ComfyUI, Automatic1111, custom pipelines)
  - Local vs. cloud agents
  - Specialized agents (fast preview, high quality, style-specific)

**Future Agent Examples**:
- `agent.comfy.local.v1` - Local ComfyUI instance
- `agent.runcomfy.cloud.v2` - Cloud-based RunComfy service
- `agent.custom.research.experimental` - Custom research pipeline

---

### `resolution` Object

Defines the output resolution for AI-generated images.

#### `resolution.preset`
- **Type**: String
- **Purpose**: Named resolution preset
- **Options**: 
  - `"640x1536"`, `"768x1344"`, `"832x1216"`, `"896x1152"`
  - `"1024x1024"` (default)
  - `"1152x896"`, `"1216x832"`, `"1344x768"`, `"1536x640"`
  - `"native_XXXX"` (auto-detected from current_ai.png)
- **Use Case**:
  - Human-readable resolution indicator
  - Preset-based workflows
  - UI dropdown display

#### `resolution.width`
- **Type**: Integer (pixels)
- **Purpose**: Exact pixel width
- **Default**: `1024`
- **Range**: `640` to `1536` (based on available presets)
- **Use Case**: AI agents use this exact value for generation

#### `resolution.height`
- **Type**: Integer (pixels)
- **Purpose**: Exact pixel height
- **Default**: `1024`
- **Range**: `640` to `1536`
- **Use Case**: AI agents use this exact value for generation

**Note**: The `ai_camera` in Blender automatically adjusts to match these dimensions when rendering.

---

### `lookup`
- **Type**: String (free text)
- **Purpose**: RAG (Retrieval-Augmented Generation) search query
- **Set By**: User in "Image Generation" section
- **Default**: `""` (empty)
- **Example**: `"victorian architecture, gothic revival"`
- **Use Case**:
  - AI agents query knowledge bases or image databases
  - Find reference material matching the lookup terms
  - Augment generation with real-world visual data
  - Separate from creative prompt for cleaner logic

**How It Works**:
1. AI agent reads `lookup` field
2. Queries a reference database (images, style guides, etc.)
3. Uses retrieved material to inform generation
4. Combines with `global_prompt` for final result

---

### `global_prompt`
- **Type**: String (free text)
- **Purpose**: Master creative direction for all AI generation
- **Set By**: User in "Image Generation" section
- **Default**: `""`
- **Example**: `"Dark gothic city at night, neon lights, rain-soaked streets, cinematic lighting"`
- **Use Case**:
  - Primary instruction to the AI about style, mood, atmosphere
  - Applies to the entire scene
  - Can be overridden by per-object group keywords
  - Think of it as the "base layer" of creative intent

**Hierarchy**:
- Global Prompt (applies to everything)
  - ↓
- Group Keywords (applies to specific objects)
  - ↓
- AI interprets the combination

---

### `depth_influence`
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Controls how much 3D depth information affects generation
- **Set By**: User in "Influence" section
- **Default**: `0.5`
- **Range**: 
  - `0.0` = AI ignores depth, more creative freedom
  - `1.0` = AI strictly follows depth map, accurate 3D structure
- **Use Case**:
  - Balancing realism vs. artistic interpretation
  - Abstract styles use lower values
  - Architectural visualization uses higher values
- **Technical**: Affects depth pass weight in AI pipeline

---

### `silhouette_influence`
- **Type**: Float (0.0 to 1.0)
- **Purpose**: Controls how much object outlines affect generation
- **Set By**: User in "Influence" section
- **Default**: `0.75`
- **Range**:
  - `0.0` = AI ignores object boundaries
  - `1.0` = AI strictly respects object shapes
- **Use Case**:
  - Maintaining object integrity in stylized renders
  - Preventing "melting" effects in abstract styles
  - Architectural projects typically use higher values
- **Technical**: Affects ambient occlusion pass weight in AI pipeline

---

### `objects` Array

This is the core of per-object control. Each entry represents a group of scene objects with shared properties and keywords.

#### Object Group Structure

```json
{
  "group_id": "grp-buildings-001",
  "label": "buildings",
  "object_ids": ["Cube", "Cube.001", "Cube.002"],
  "pass_index": 12,
  "keywords": ["tall skyscrapers", "glass facades", "art deco"],
  "mask": {
    "export": true,
    "type": "object_index",
    "path": "//temp/ai_vision/passes/id_12.png"
  }
}
```

#### `objects[].group_id`
- **Type**: String (unique identifier)
- **Format**: `"grp-<label>-<counter>"`
- **Example**: `"grp-buildings-001"`, `"grp-vehicles-002"`
- **Purpose**: Stable, unique ID for this group
- **Use Case**:
  - Tracking groups across sessions
  - Future database integration
  - Debugging and logging

#### `objects[].label`
- **Type**: String (human-readable)
- **Purpose**: Short name for the group
- **Example**: `"buildings"`, `"trees"`, `"characters"`
- **Use Case**:
  - Display in UI and logs
  - Quick identification
  - Natural language processing by AI

#### `objects[].object_ids`
- **Type**: Array of strings
- **Purpose**: List of Blender object names in this group
- **Example**: `["Cube", "Cube.001", "Sphere"]`
- **Default**: `[]` (empty, objects not yet assigned)
- **Use Case**:
  - Link JSON data to actual 3D objects
  - Future: setting per-object properties (pass_index)
  - Future: automation and batch operations

**Note**: Assignment functionality coming soon. Currently, groups can be created but object assignment is manual.

#### `objects[].pass_index`
- **Type**: Integer (1 to 32767)
- **Purpose**: Blender's Object Index for masking
- **Auto-assigned**: Starts at 12, increments for each new group
- **Example**: First group = 12, second = 13, third = 14
- **Use Case**:
  - Render ID masks for per-object AI control
  - Inpainting specific areas
  - Isolating objects in post-processing

**Technical**: When objects are assigned to a group, their `obj.pass_index` property will be set to this value, allowing the compositor to render separate masks.

#### `objects[].keywords`
- **Type**: Array of strings
- **Purpose**: Specific descriptive terms for this group
- **Example**: `["red brick", "weathered", "tall", "victorian windows"]`
- **Set By**: User edits directly in UI
- **Parsing**: Comma-separated in UI, split into array in JSON
- **Use Case**:
  - Fine-grained control over object appearance
  - Override or extend global prompt
  - Per-object style directives

**Workflow Example**:
- Global Prompt: "Cyberpunk city at night"
- Buildings Group Keywords: "neon signs", "holographic ads", "glass and steel"
- Vehicles Group Keywords: "flying cars", "glowing engines"
- Result: AI generates a cohesive scene with specific details for each group

#### `objects[].mask.export`
- **Type**: Boolean
- **Purpose**: Whether to export a mask for this group
- **Fixed**: Always `true` (all groups get masks)
- **Use Case**: Future flexibility to disable masking for certain groups

#### `objects[].mask.type`
- **Type**: String
- **Purpose**: Type of mask to generate
- **Fixed**: Always `"object_index"`
- **Use Case**: 
  - Uses Blender's built-in Object Index pass
  - Future: could support other mask types (material-based, vertex color, etc.)

#### `objects[].mask.path`
- **Type**: String (relative file path)
- **Format**: `"//temp/ai_vision/passes/id_<pass_index>.png"`
- **Example**: `"//temp/ai_vision/passes/id_12.png"`
- **Purpose**: Where the mask image will be saved
- **Use Case**:
  - AI agents load these masks for targeted inpainting
  - Each group gets its own unique mask file
  - Allows simultaneous processing of multiple groups

---

### `routing` Object

Defines all file paths for inputs and outputs.

#### `routing.temp_dir`
- **Type**: String (relative path)
- **Value**: `"//temp/ai_vision/"`
- **Purpose**: Root directory for temporary session files
- **Resolves To**: `C:\Coding\STYLEENGINE\data\temp\ai_vision\`
- **Use Case**: 
  - All auto-generated files go here
  - Cleaned up between sessions
  - AI agents watch this directory

#### `routing.preview_out`
- **Type**: String (relative path)
- **Value**: `"//temp/ai_vision/current_ai.png"`
- **Purpose**: The current AI-generated image
- **Use Case**:
  - Displayed in the `ai_camera` background
  - Constantly updated by AI generation
  - Refreshed by Blender every update cycle

#### `routing.passes_dir`
- **Type**: String (relative path)
- **Value**: `"//temp/ai_vision/passes/"`
- **Purpose**: Directory containing all render passes
- **Contents**:
  - `combined0001.png` - Full rendered image
  - `depth0001.png` - Depth/Z pass (inverted via color ramp)
  - `ao0001.png` - Ambient occlusion pass
  - `id_<N>.png` - Object index masks (future)
- **Use Case**: AI agents read these passes as input for generation

#### `routing.commits_dir`
- **Type**: String (absolute path)
- **Set By**: User in "Workspace Setup" → "Output Path"
- **Example**: `"C:/Projects/Renders/"`
- **Purpose**: Where final, saved renders go
- **Use Case**:
  - User-controlled output location
  - Permanent storage (not auto-deleted)
  - Future "commit" or "save" functionality

---

### `flags` Object

Boolean settings and configuration flags.

#### `flags.live_preview`
- **Type**: Boolean
- **Purpose**: Whether real-time updates are active
- **Set By**: "Refresh Viewport" checkbox in UI
- **Default**: `true`
- **Use Case**:
  - Controls auto-rendering timer
  - Controls `current_ai.png` refresh watcher
  - AI agents can check if they should actively generate
  - Performance control (disable for heavy scenes)

**Effect When `true`**:
- Blender renders every 5 seconds
- `current_ai.png` is watched for updates
- `session.json` timestamp updates regularly

**Effect When `false`**:
- Timers stop
- No automatic rendering
- Manual updates only

#### `flags.autosave_every_sec`
- **Type**: Float (seconds)
- **Value**: `5.0`
- **Purpose**: Render interval timing
- **Use Case**:
  - AI agents know how often to expect new input
  - Synchronization between Blender and external tools
  - Future: may be user-configurable

---

## Integration Guide for AI Developers

If you're building an AI agent to consume this JSON:

### 1. File Watching

```python
import json
import time
from pathlib import Path

session_path = Path("C:/Coding/STYLEENGINE/data/temp/ai_vision/session.json")

def load_session():
    with open(session_path, 'r') as f:
        return json.load(f)

# Poll for changes
last_timestamp = None
while True:
    session = load_session()
    if session['timestamp'] != last_timestamp:
        # Session updated, trigger generation
        process_session(session)
        last_timestamp = session['timestamp']
    time.sleep(1)  # Check every second
```

### 2. Reading Render Passes

```python
from PIL import Image

def load_passes(session):
    base_path = "C:/Coding/STYLEENGINE/data/temp/ai_vision/passes/"
    
    combined = Image.open(base_path + "combined0001.png")
    depth = Image.open(base_path + "depth0001.png")
    ao = Image.open(base_path + "ao0001.png")
    
    return {
        'combined': combined,
        'depth': depth,
        'ao': ao
    }
```

### 3. Applying Influence Settings

```python
def apply_influence(session, depth_map, ao_map):
    depth_weight = session['depth_influence']
    silhouette_weight = session['silhouette_influence']
    
    # Your AI model's conditioning logic here
    # Higher weights = stronger adherence to input
    conditioning = {
        'depth': depth_map * depth_weight,
        'controlnet_ao': ao_map * silhouette_weight
    }
    return conditioning
```

### 4. Processing Per-Object Groups

```python
def build_prompts(session):
    # Start with global prompt
    base_prompt = session['global_prompt']
    
    # Add per-object prompts
    for group in session['objects']:
        label = group['label']
        keywords = ", ".join(group['keywords'])
        
        # Load mask for this group
        mask_path = group['mask']['path'].replace('//', base_path)
        mask = Image.open(mask_path)
        
        # Your inpainting logic here
        inpaint_region(
            prompt=f"{base_prompt}, {keywords}",
            mask=mask,
            label=label
        )
```

### 5. Writing Output

```python
def save_preview(generated_image, session):
    output_path = "C:/Coding/STYLEENGINE/data/temp/ai_vision/current_ai.png"
    generated_image.save(output_path)
    
    # Blender will detect the change and update the camera background
```

---

## Schema Evolution (Future)

Potential additions in future versions:

- **`camera_position`**: 3D coordinates for external rendering
- **`materials[]`**: Per-group material overrides
- **`lighting`**: Scene lighting information
- **`style_reference`**: Path to reference images
- **`quality_preset`**: Speed vs. quality tradeoff
- **`seed`**: Random seed for reproducible results
- **`history[]`**: Previous generations in this session

---

## Troubleshooting

**JSON file doesn't update:**
- Check "Refresh Viewport" is enabled
- Change a UI setting to trigger an update
- Check Blender console for errors

**Invalid JSON format:**
- Should never happen (atomic writes prevent corruption)
- If it does, delete `session.json` and click "Setup Workspace" again

**AI agent can't find files:**
- Ensure paths in `routing` are correct
- Check that render passes are being generated
- Verify "Refresh Viewport" is enabled

**Groups don't appear in JSON:**
- Make sure you clicked "Add Group" (not just typed a name)
- Check that `session.json` updates after adding a group

---

## Summary

The `session.json` file is your single source of truth for:
- ✅ What you want to create (prompts, keywords)
- ✅ How it should look (influence settings, resolution)
- ✅ Where things are (file paths, scene references)
- ✅ What objects are involved (groups and masks)
- ✅ Technical settings (agent selection, timing)

It bridges the gap between Blender's 3D modeling capabilities and AI generation systems, enabling seamless, real-time collaboration between human creativity and machine generation.

