# Style Engine - AI Vision MVP

## Overview

The AI Vision MVP creates a dual-screen workflow in Blender where:
- **Left viewport**: Normal 3D modeling workspace
- **Right viewport**: Locked camera view showing AI-generated images as an overlay

This skeleton implementation sets up the infrastructure for real-time AI visualization without yet implementing the actual AI generation pipeline.

## Features Implemented

### ✅ Setup Workspace Button
- Located in the Style Engine panel under "AI Vision Setup"
- One-click setup for the entire AI Vision workspace

### ✅ Workspace Creation
- Creates a new workspace called "AI"
- Automatically splits into left (modeling) and right (AI vision) viewports
- Left: Standard 3D viewport for modeling
- Right: Camera-locked viewport for AI visualization

### ✅ AI Camera System
- Creates a camera named `ai_camera`
- Positioned at the current view location (like Ctrl+Alt+0)
- Automatically set as the active camera
- Background image configured to display in front with 100% opacity

### ✅ Directory Structure
- Creates `/temp/ai_vision/` directory in your project folder
- Stores `current_ai.png` - the AI-generated image (placeholder for now)
- Generates a placeholder image if none exists

## How to Use

### Initial Setup

1. **Open Blender** with the Style Engine addon enabled
2. **Open the Style Engine panel** (Press `N` in 3D Viewport → Style Engine tab)
3. **Position your view** where you want the AI camera to start
4. **Click "Setup Workspace"** button

### What Happens

```
┌─────────────────────────────────────────────────────────────┐
│  1. Creates /temp/ai_vision/ directory                      │
│  2. Generates placeholder image: current_ai.png             │
│  3. Creates or finds "ai_camera" object                     │
│  4. Positions camera at your current viewpoint              │
│  5. Configures camera background image (100% opacity)       │
│  6. Creates "AI" workspace                                  │
│  7. Splits workspace: Left (modeling) | Right (camera)      │
│  8. Switches you to the new workspace                       │
└─────────────────────────────────────────────────────────────┘
```

### After Setup

The workspace will look like this:

```
┌────────────────────────┬────────────────────────┐
│                        │                        │
│   LEFT VIEWPORT        │   RIGHT VIEWPORT       │
│   (Normal 3D View)     │   (Camera View)        │
│                        │                        │
│   • Free navigation    │   • Locked to camera   │
│   • Model here         │   • Shows AI overlay   │
│   • Regular tools      │   • Background image   │
│                        │     at 100% opacity    │
│                        │                        │
│                        │                        │
└────────────────────────┴────────────────────────┘
```

## File Structure

```
YourProject/
├── YourBlendFile.blend
└── temp/
    └── ai_vision/
        └── current_ai.png    # AI-generated image (updated by AI pipeline)
```

## Technical Details

### Camera Configuration

The `ai_camera` is configured with:
- **Position**: Aligned to your current 3D view
- **Background Image**: Points to `temp/ai_vision/current_ai.png`
- **Alpha**: 1.0 (100% opacity)
- **Display Depth**: FRONT (rendered in front of scene)
- **Frame Method**: STRETCH (fills viewport)

### Workspace Properties

The "AI" workspace:
- **Left Area**: 50% width, standard 3D viewport
- **Right Area**: 50% width, camera-locked viewport
- **Active Camera**: Automatically set to `ai_camera`

### Placeholder Image

When first set up, a dark blue placeholder image is created (1920x1080) to verify the system is working.

## Next Steps (Not Yet Implemented)

The following features are planned but not yet implemented:

### 🔄 Auto-Refresh System
- Timer-based rendering (every X seconds)
- Automatic viewport capture
- AI pipeline integration
- Real-time image updates

### 🎨 AI Generation Pipeline
- Render current view
- Send to AI service (RunComfy)
- Process with AI model
- Update `current_ai.png`
- Refresh viewport display

### ⚙️ Settings
- Refresh interval control
- AI model selection
- Prompt configuration
- Image quality settings

## Troubleshooting

### Camera not visible
- Ensure `ai_camera` exists in your scene outliner
- Check that it's set as the active camera (camera icon in outliner)

### Background image not showing
- Verify `temp/ai_vision/current_ai.png` exists
- Check camera's background image settings (Camera Properties panel)
- Ensure background images are enabled in the camera settings

### Workspace doesn't split correctly
- Try running the setup again
- Manually split the workspace: drag from corner of viewport
- Set right viewport to camera view: View → Cameras → Active Camera

### "Setup Workspace" does nothing
- Check Blender's console for error messages
- Ensure the addon is properly enabled
- Save your file first to establish a project directory

## Development Notes

### For Developers

The setup operator does the following in order:

1. **`ensure_temp_directory()`**: Creates directory structure
2. **`create_ai_camera()`**: Creates/finds camera object  
3. **`align_camera_to_view()`**: Positions camera (Ctrl+Alt+0 behavior)
4. **`setup_camera_background()`**: Configures background image
5. **`create_ai_workspace()`**: Creates workspace if needed
6. **`setup_workspace_layout()`**: Splits viewport via timer callback
7. **Switch to workspace**: Changes active workspace

### Timer-Based Split

The viewport split uses `bpy.app.timers.register()` to delay the split operation by 0.1 seconds. This is necessary because workspace layout modifications require the workspace to be fully active.

### Rerunning Setup

If you run "Setup Workspace" multiple times:
- Reuses existing `ai_camera` if found
- Reuses existing "AI" workspace if found
- Updates camera position to current view
- Refreshes background image path

## API Reference

### Operators

#### `style_engine.setup_workspace`
**Description**: Main setup operator for AI Vision workspace  
**Location**: Style Engine Panel → AI Vision Setup  
**Returns**: `{'FINISHED'}` on success

#### `style_engine.configure_workspace_layout`  
**Description**: Internal operator for workspace splitting  
**Usage**: Called automatically via timer, not meant for manual use

### Properties

#### Camera: `ai_camera`
- **Type**: Camera Object
- **Location**: Aligned to current 3D view
- **Purpose**: Display AI-generated imagery

#### Image: `current_ai.png`
- **Location**: `temp/ai_vision/current_ai.png`
- **Size**: 1920x1080 (default)
- **Format**: PNG
- **Purpose**: AI output display

## Visual Reference

The reference image you provided shows the kind of stylized, AI-generated aesthetic this system is designed to produce - transforming your 3D scene into artistic visualizations in real-time.

---

**Status**: MVP - Core infrastructure complete, AI generation pipeline pending
**Version**: 0.0.1
**Last Updated**: Current session

