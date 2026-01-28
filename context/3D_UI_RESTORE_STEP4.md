# 3D UI Elements Restoration - Step 4

**Date**: 2026-01-27  
**Status**: ✅ Complete

## Changes Made

### Restored WM_OT_CreateTexturedObject Operator

**File**: `scripts/addons/styleengine/pie_menu.py`

**Location**: Lines 553-750 (replaced 10-line placeholder with 198-line full implementation)

**Source**: Exact copy from `context/3Dstyleengine/styleengine/pie_menu.py` (lines 580-777)

## Operator Details

### Purpose
Generate a new 3D mesh WITH UV-mapped textures from `current_ai.png` using Hunyuan 3D 2.1. Creates **complete textured asset** (mesh + PBR textures).

### bl_info
```python
bl_idname = "style_engine.create_textured_object"
bl_label = "Create Textured Object"
bl_description = "Generate a new 3D mesh WITH UV-mapped textures from current_ai.png"
bl_options = {'REGISTER', 'UNDO'}
```

## Implementation Pipeline

### Step 1: Get Reference Image
- Locates `current_ai.png` in temp directory
- Validates file exists
- Error if not found (user must generate image first)

### Step 2: Upload Image to Server
- Uses `server_client.upload_image()`
- Uploads to ComfyUI server
- Returns uploaded filename

### Step 3: Load Workflow
- Loads `workflows/objectCreateTexturedObject.json`
- Validates workflow file exists
- Parses JSON workflow

### Step 4: Configure Workflow with Quality Parameters
Uses `get_quality_params()` to configure **BOTH mesh AND texture** generation:

**Workflow Nodes Modified:**
- **Node 14** (Hy3D21LoadImageWithTransparency): Input image
- **Node 32** (StringConstant): Output filename prefix
- **Node 37** (Hy3DMeshGenerator): Mesh generation steps, seed
- **Node 9** (Hy3D21VAEDecode): Octree resolution, chunks
- **Node 30** (INTConstant): Max face count
- **Node 20** (Hy3DMultiViewsGenerator): View size, texture steps, texture size

**Quality-Based Parameters:**
| Preset | mesh_steps | octree | max_faces | view_size | texture_steps | texture_size |
|--------|-----------|--------|-----------|-----------|---------------|--------------|
| SKETCH | 10 | 96 | 20K | 512px | 4 | 512px |
| FAST | 15 | 128 | 50K | 512px | 6 | 512px |
| BALANCED | 25 | 256 | 200K | 768px | 10 | 1024px |
| DETAILED | 50 | 512 | 500K | 1024px | 30 | 2048px |

### Step 5: Submit Workflow (Non-Blocking)
- Calls `server_client.queue_prompt(workflow_json)`
- Returns `prompt_id` for tracking
- Background processing (2-3 minutes typical)
- Blender remains responsive
- User notification: "Generating textured 3D mesh... (2-3 minutes)"

### Step 6: Background Polling with Scheduled Import
Uses `runcomfy_polling.RunComfyPoller.start_polling()`:
- Monitors completion via callback
- `workflow_type='create_textured'`
- `deployment_id='server'`

**Optimization**: Heavy download/import operations scheduled separately via `bpy.app.timers.register()` to keep polling callback fast!

### Step 7: Download & Import (In Scheduled Timer)
When generation completes:

1. **Parse Output**: Finds GLB from Node 62 (Preview3D shows Node 49's saved file)
2. **Download**: Uses `server_client.download_mesh()`
3. **Import**: `bpy.ops.import_scene.gltf()` (heavy operation)
4. **Position**: Places at world origin (0, 0, 0)
5. **Name**: `AI_Textured_{timestamp}`

## Workflow Integration

### ComfyUI Workflow: objectCreateTexturedObject.json

**Key Nodes (Mesh Generation):**
1. **Node 63**: Image Rembg (Remove Background)
2. **Node 64**: ImageResizeKJv2 (1024x1024)
3. **Node 37**: Hy3DMeshGenerator (3D generation)
   - Model: `hunyuan3d-dit-v2-1.ckpt`
   - Configurable steps (10-50)
4. **Node 9**: Hy3D21VAEDecode (Latent → Mesh)
5. **Node 43**: Hy3D21PostprocessMesh
6. **Node 45**: Hy3DMeshUnwrap (UV unwrapping)

**Key Nodes (Texture Generation):**
7. **Node 19**: Hy3D21CameraConfig (6 view angles)
   - Azimuths: 0°, 90°, 180°, 270°, 0°, 180°
   - Elevations: 0°, 0°, 0°, 0°, 90°, -90°
8. **Node 20**: Hy3DMultiViewsGenerator
   - Configurable view_size, texture_steps, texture_size
9. **Node 21**: Hy3DBakeMaps (Texture baking)
10. **Node 49**: Hy3DInPaint (Seam filling)
11. **Node 44**: Hy3D21ExportMesh (GLB with textures)
12. **Node 62**: Preview3D (Shows result)

## Error Handling

### Validation Checks
- ✅ GCS mode required (not RunComfy Cloud)
- ✅ current_ai.png must exist
- ✅ Workflow JSON must exist
- ✅ Upload must succeed
- ✅ Download must succeed
- ✅ Import must succeed

### Error Messages
All errors use `self.report({'ERROR'}, ...)` and print detailed console logs with `[Create Textured]` prefix.

## Console Logging

Comprehensive step-by-step logging:
```
[Create Textured] ============================================
[Create Textured] STARTING TEXTURED MESH GENERATION
[Create Textured] ============================================
[Create Textured] Step 1: Getting reference image...
[Create Textured] ✓ Found: current_ai.png
[Create Textured] Step 2: Uploading image to server...
[Create Textured] ✓ Uploaded as: current_ai (123).png
[Create Textured] Step 3: Loading workflow...
[Create Textured] ✓ Loaded workflow: objectCreateTexturedObject.json
[Create Textured] Step 4: Configuring workflow...
[Create Textured] ✓ Quality: BALANCED
[Create Textured] ✓ Mesh: steps=25, octree=256, faces=200000
[Create Textured] ✓ Texture: view=768, steps=10, size=1024
[Create Textured] Step 5: Submitting workflow...
[Create Textured] ✓ Queued: abc123...
[Create Textured] ⏳ Processing (includes mesh + texture generation)...
[Create Textured] ✅ Submitted! Processing in background...
...
[Create Textured] ✓ Generation complete! Scheduling download/import...
[Create Textured] Starting download & import...
[Create Textured] ✓ Found: 3D/StyleEngine_Textured_1234567890.glb
[Create Textured] Downloading...
[Create Textured] ✓ Downloaded (5432.1 KB)
[Create Textured] Importing...
[Create Textured] ✅ Textured 3D mesh created: AI_Textured_1234567890
[Create Textured] COMPLETE!
```

## User Workflow

1. Generate AI image (Alt+W → Generate Image)
2. Alt+W → Object → **Create Textured Object**
3. Wait 2-3 minutes (watch console)
4. New textured mesh appears at origin
5. Mesh has full PBR materials (color, normal, roughness)

## Technical Notes

### Non-Blocking Design
- Uses Blender's timer system via `runcomfy_polling`
- **Callback optimization**: Heavy download/import scheduled separately via `bpy.app.timers.register(do_download_and_import, first_interval=0.1)`
- This keeps the polling callback fast and responsive
- User can continue working during generation

### Timer-Based Import
```python
def on_create_textured_complete(success, result=None, error=None, workflow_type=None):
    # Lightweight callback - just schedules heavy work
    def do_download_and_import():
        # Heavy operations: download GLB, import to Blender
        ...
        return None  # Don't repeat
    
    bpy.app.timers.register(do_download_and_import, first_interval=0.1)
```

This pattern prevents blocking the polling system during heavy import operations.

### Temporary Files
- Download location: `{temp}/styleengine_create/`
- Filename format: `StyleEngine_Textured_{timestamp}.glb`
- Files persist for debugging

### Import Behavior
- Uses Blender's native GLTF importer
- Preserves mesh topology
- Imports PBR materials automatically
- Textures embedded in GLB
- Automatically selects imported object

## Quality vs Speed vs Output

| Quality | Time | Vertices | Texture Res | File Size | Use Case |
|---------|------|----------|-------------|-----------|----------|
| **SKETCH** | ~90s | Low | 512px | ~1MB | Rapid concept |
| **FAST** | ~120s | Medium | 512px | ~2MB | Draft iteration |
| **BALANCED** | ~150s | High | 1024px | ~5MB | **Production (default)** |
| **DETAILED** | ~240s | Very High | 2048px | ~15MB | Hero assets |

## Differences from Other Operators

| Feature | Create Object | UV Texture | **Create Textured** |
|---------|--------------|------------|---------------------|
| **Input** | 2D image | 3D mesh + image | **2D image only** |
| **Output** | Mesh (no texture) | Mesh + textures | **Mesh + textures** |
| **Time** | 1-2 min | 1-2 min | **2-3 min** |
| **Workflow** | objectCreateObject.json | objectUVTexture.json | **objectCreateTexturedObject.json** |
| **Position** | World origin | Next to original | **World origin** |
| **Use Case** | Need geometry only | Texture existing mesh | **Complete asset from scratch** |

## Key Difference: Complete Pipeline

**Create Textured Object** = **Create Object** + **UV Texture** in one operation:
1. Generate 3D mesh from 2D image
2. Unwrap UVs automatically
3. Generate multi-view textures (6 angles)
4. Bake textures to mesh
5. Fill seams with inpainting
6. Export as complete GLB with PBR materials

This is the most complete 3D generation feature - single image → ready-to-use 3D asset!

## Next Steps

Step 5: Restore `WM_OT_OpenGenerationSettings` dialog (optional persistent settings UI)

## Source Verification

✅ **Exact copy confirmed** from `context/3Dstyleengine/styleengine/pie_menu.py` lines 580-777  
✅ **No modifications** - Restored as-is  
✅ **Workflow file exists** at `scripts/addons/styleengine/workflows/objectCreateTexturedObject.json`  
✅ **All dependencies present** (runcomfy_deployment, runcomfy_polling, server_client, bpy.app.timers)  
✅ **Timer optimization preserved** - Heavy import doesn't block polling callback
