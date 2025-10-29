# Save Iterations Feature

## Summary
Added a "Save Iterations" feature that automatically saves AI-generated images alongside their corresponding 3D iteration snapshots and assigns them as materials.

## Implementation Details

### 1. New Property
**Location**: `scripts/addons/styleengine/ui_panel.py`

```python
save_iterations: bpy.props.BoolProperty(
    name="Save Iterations",
    description="Automatically save iteration snapshots with their corresponding AI images",
    default=True
)
```

- **Default**: `True` (automatically enabled)
- **Location in UI**: Workspace Setup section, after Resolution dropdown

### 2. UI Changes
**Location**: Workspace Setup panel

Added a new checkbox between "Set Resolution" and "Output Path":
- Label: "Save Iterations"
- Icon: `SAVE_COPY`
- When enabled: Iterations are saved with their images
- When disabled: Snapshot creation is skipped

### 3. Enhanced Iteration Workflow

#### Modified: `create_iteration_snapshot()`
- Now checks if `save_iterations` is enabled
- If disabled, prints skip message and returns early
- If enabled, proceeds with snapshot creation and calls image/material setup

#### New Method: `save_iteration_image_and_material()`
Handles the complete image saving and material assignment workflow:

**Step 1: Copy AI Image**
- Source: `data/temp/ai_vision/current_ai.png`
- Destination: `generated/Iteration_XXX.png`
- Creates `generated/` folder if it doesn't exist

**Step 2: Load Image into Blender**
- Loads the saved image into Blender's image data
- Names it with the iteration name

**Step 3: Create Material**
- Material name: `Iteration_XXX_Material`
- Uses Shader Nodes (Principled BSDF setup)
- Node setup:
  - Image Texture node → Base Color input
  - Principled BSDF → Material Output

**Step 4: Assign Material**
- Assigns the material to the iteration object
- Replaces existing material slot 0 or appends if none exists

### 4. File Structure

```
STYLEENGINE/
├── generated/              # NEW - Auto-created
│   ├── Iteration_000.png
│   ├── Iteration_001.png
│   └── ...
├── data/
│   └── temp/
│       └── ai_vision/
│           └── current_ai.png  # Source image
└── scripts/
    └── addons/
        └── styleengine/
            └── ui_panel.py     # Modified
```

### 5. New Imports
Added to `ui_panel.py`:
```python
import shutil
from pathlib import Path
```

## User Experience Flow

1. **User enables "Save Iterations"** (default: ON)
2. **User clicks "Project Texture"**
3. **System automatically**:
   - Duplicates all meshes
   - Joins them into single object named `Iteration_XXX`
   - Copies current AI image to `generated/Iteration_XXX.png`
   - Creates material with AI image as Base Color
   - Assigns material to iteration object
   - Hides object from viewport (eye icon)
   - Disables object in renders (camera icon)
   - Places object in "Iterations" collection

4. **Result**: 
   - Hidden iteration object with textured material
   - Saved image in `generated/` folder
   - Sequential naming (000, 001, 002...)

## Console Output

When feature is **enabled**:
```
[Style Engine] 📦 Duplicated 4 objects
[Style Engine] 💾 Created Iteration_001 in Iterations collection
[Style Engine]    └─ Hidden from viewport (eye icon) and disabled in renders
[Style Engine] 📸 Saved image: Iteration_001.png
[Style Engine] 🎨 Material 'Iteration_001_Material' assigned with texture
```

When feature is **disabled**:
```
[Style Engine] ⏭️ Save Iterations disabled, skipping snapshot
```

## Benefits

1. **Archive Management**: All iterations saved with matching images
2. **Material Ready**: Each iteration has its texture pre-assigned
3. **Clean Workflow**: Automatically organized in dedicated folder
4. **Non-Destructive**: Original objects remain untouched
5. **Version Control**: Sequential naming for easy tracking
6. **Toggleable**: Can be disabled when not needed

## Technical Notes

- Image format: PNG (preserves quality and alpha)
- Material setup: Full Shader Nodes with Principled BSDF
- Collection: "Iterations" (auto-created)
- Visibility: Hidden viewport + disabled renders
- Selectability: Maintained (not grayed out in outliner)

## Error Handling

- Checks if AI image exists before copying
- Creates `generated/` folder if missing
- Handles material replacement gracefully
- Comprehensive exception catching with error logging

