# Style Engine - Blender Addon

AI-powered visual feedback for 3D modeling. See your scenes through AI eyes in real-time.

---

## 🚀 Quick Start Guide

### Installation (2 minutes)

**Method 1: Install ZIP (Recommended)**
1. Download `styleengine.zip`
2. Open Blender 4.2+
3. Go to **Edit → Preferences → Add-ons**
4. Click **Install from Disk...**
5. Select `styleengine.zip`
6. Enable **Style Engine** checkbox

**Method 2: Development Install**
```powershell
# Run PowerShell as Administrator
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Blender Foundation\Blender\4.4\scripts\addons\styleengine" -Target "C:\Coding\STYLEENGINE\scripts\addons\styleengine"
```
Then reload scripts in Blender (F3 → "Reload Scripts")

### First Use (1 minute)

1. **Open Style Engine panel:**
   - Press `N` key in 3D viewport
   - Find "Style Engine" tab

2. **Configure RunComfy API** (in addon preferences):
   - Expand Style Engine addon details
   - Enter your `RUNCOMFY_API_TOKEN`
   - Enter your `RUNCOMFY_USER_ID`
   - Click "Test Connection"

3. **Setup workspace:**
   - Session ID: `myproject-001`
   - Resolution: `1024x1024`
   - Check ✓ **Refresh Viewport**
   - Click **Setup Workspace**

4. **Start creating:**
   - Global Prompt: `"futuristic cityscape at sunset"`
   - Add object groups with keywords
   - Model in left view, see AI interpretation on right

**That's it!** The addon auto-renders every 5 seconds and shows AI feedback in the camera view.

---

## What is Style Engine?

Style Engine is a Blender addon that creates an AI-powered "vision" workflow for 3D modeling. It allows you to see your 3D scene through the eyes of AI in real-time, giving you instant visual feedback as you model and build your scenes.

Think of it as a split-screen workflow: on the left, you have your normal Blender modeling workspace. On the right, you have a special camera that continuously shows you an AI-generated interpretation of what you're building. It's like having an AI artist sitting next to you, constantly sketching what your scene could look like when finished.

---

## Core Features

### 🖥️ Dual-Screen Workspace
- **Left View**: Your normal 3D modeling viewport where you work
- **Right View**: An AI vision camera that displays generated images
- The workspace automatically splits when you click "Setup Workspace"

### 📷 AI Vision Camera
- A special camera named `ai_camera` that spawns at your current viewpoint
- Displays AI-generated images as a background overlay (100% opacity)
- Constantly refreshes to show updated AI interpretations
- Automatically matches the resolution of the AI-generated images

### 🎬 Automatic Render Passes
- Every 5 seconds, the camera renders your scene with:
  - **Combined Pass**: The full rendered image
  - **Depth Pass**: Distance information (inverted for AI pipelines)
  - **Ambient Occlusion Pass**: Lighting and shadow detail
- All passes are automatically saved to a temporary folder
- The compositor is pre-configured with the right nodes to process these passes

### 📋 Session Management
- Every workspace session has a unique ID that tracks all your settings
- All your preferences, prompts, and object groups are saved in a `session.json` file
- This JSON file can be read by AI generation software to process your requests

### 🎨 Image Generation Controls
- **Lookup**: Text that helps the AI find relevant reference information
- **Global Prompt**: Your main creative direction for the AI
- **Object Groups**: Organize scene objects with specific keywords
  - Add unlimited groups (buildings, vehicles, characters, etc.)
  - Each group can have custom keywords to guide AI generation
  - Click groups to select them, edit their keywords directly in the UI
- **Influence Sliders**: Control how much depth and silhouette affect the generation
- **LoRa Models**: Apply LoRa models to modify generation style
  - Dynamic discovery from ComfyUI server
  - Dropdown selector with all available LoRas
  - Adjustable strength (0.0 to 1.0)
  - 5-minute cache for performance
  - Manual refresh button

---

## How to Use Style Engine

### 1. Initial Setup

1. **Install the Addon**:
   - Go to Edit → Preferences → Add-ons
   - Click "Install" and navigate to the Style Engine folder
   - Enable "Style Engine" in the addon list

2. **Configure API Keys** (Optional, for future AI generation):
   - In addon preferences, expand "RunComfy Settings"
   - Enter your `RUNCOMFY_API_TOKEN` and `RUNCOMFY_USER_ID`
   - Or enable "Prefer Environment Variables" to use system variables

### 2. Setting Up Your Workspace

1. Open the **Style Engine** panel in the 3D View sidebar (press `N` key)
2. In the **Workspace Setup** section:
   - Enter a unique **Session ID** (e.g., "project-cityscape-001")
   - Set your **Output Path** for final renders (e.g., "C:\Projects\Renders")
   - Choose an **AI Resolution** from the dropdown (default: 1024x1024)
   - Check **Refresh Viewport** to enable continuous updates (recommended)
3. Click **Setup Workspace**

**What happens:**
- A new workspace named "AI" is created and automatically opened
- Your screen splits into two 3D viewports
- A new camera (`ai_camera`) is created at your current view position
- The right viewport locks to this camera view
- The compositor is configured with all necessary render passes
- A `session.json` file is created in `data/temp/` with all your settings

### 3. Working with Image Generation

In the **Image Generation** section:

1. **Lookup** (Optional): Enter search terms to help the AI find reference material
   - Example: "victorian architecture" or "cyberpunk streets"

2. **Global Prompt**: Describe your overall creative vision
   - Example: "Dark gothic city at night, neon lights, rain-soaked streets"

3. **Groups**: Organize your scene objects
   - Click **Add Group** to create a new group
   - Name it descriptively (e.g., "Buildings", "Vehicles", "Characters")
   - Enter **Keywords** to describe what these objects should become
     - Example: Buildings → "tall skyscrapers, glass facades, art deco"
   - Click **Assign** to link selected objects to the group (coming soon)
   - Click **Delete** to remove unwanted groups

4. **Influence** (Fine-tune AI behavior):
   - **Depth Influence**: How much 3D depth affects the generation (0.0 - 1.0)
   - **Silhouette Influence**: How much object outlines affect the generation (0.0 - 1.0)

### 4. Real-Time Updates

With **Refresh Viewport** enabled:
- The AI vision camera automatically renders every 5 seconds
- All render passes (Combined, Depth, AO) are saved to `data/temp/ai_vision/passes/`
- The `session.json` file updates whenever you change any setting
- Your `current_ai.png` image refreshes in the camera background

---

## Understanding the Workflow

### The Two-Screen Modality

Style Engine is built around a simple concept: **model on the left, see AI interpretation on the right**.

1. **Modeling Window (Left)**:
   - Work normally: add objects, move things around, build your scene
   - Your normal Blender tools and shortcuts work exactly as before

2. **AI Vision Camera (Right)**:
   - Shows you the "AI filter" view of your scene
   - As you model, the AI interprets your 3D geometry into stylized images
   - The camera passepartout (darkened area outside frame) is always at 100% for focus

### What Gets Saved Where

- **Temporary Files** (Auto-generated, constantly updated):
  - `data/temp/ai_vision/session.json` - Your current session settings
  - `data/temp/ai_vision/current_ai.png` - The latest AI-generated image
  - `data/temp/ai_vision/passes/` - Render passes (combined, depth, AO)

- **Output Files** (Your chosen output path):
  - Final committed renders go here when you save them manually

### Session JSON: The Bridge to AI

Every time you adjust a setting, Style Engine writes a `session.json` file. This file contains:
- Your session ID and resolution settings
- Your prompts and lookup terms
- All your object groups and their keywords
- Which render passes are enabled
- Where files should be saved

External AI generation software can read this JSON file to understand exactly what you want and how to process your scene. It's like a recipe card that tells the AI chef how to cook your 3D scene into a final image.

---

## Tips & Best Practices

### Session Management
- Use descriptive Session IDs: `project-cityscape-night-001`
- Groups reset when you start a new session (by design)
- Keep your Output Path organized by project

### Object Groups
- Name groups clearly: "MainBuildings", "BackgroundTrees", "HeroCar"
- Use specific keywords: instead of "car", try "red sports car, chrome details"
- You can have as many groups as needed - there's no limit

### Influence Settings
- Start with Depth at 0.5 and Silhouette at 0.75
- Lower values = AI has more creative freedom
- Higher values = AI follows your 3D geometry more closely

### Performance
- The 5-second auto-render interval is a good balance
- If your scene is complex, consider temporarily disabling "Refresh Viewport"
- Re-enable it when you want to see updates

---

## Troubleshooting

**The camera background isn't showing an image:**
- Make sure `current_ai.png` exists in `data/temp/ai_vision/`
- Check that "Refresh Viewport" is enabled
- The image updates every 5 seconds - give it a moment

**The workspace didn't split properly:**
- This is a Blender limitation - you may need to manually split the view
- Drag from the top-right corner of the viewport to split it

**Groups aren't saving:**
- Make sure you clicked "Add Group" to create them first
- Groups are stored in `session.json` - check the file was created

**Render passes aren't generating:**
- Ensure "Refresh Viewport" is checked
- Wait for the 5-second interval
- Check the Blender console for error messages (Window → Toggle System Console)

---

## File Structure

```
C:\Coding\STYLEENGINE\
├── scripts/
│   └── addons/
│       └── styleengine/
│           ├── __init__.py          # Main addon entry
│           ├── prefs.py             # API and preferences
│           ├── ui_panel.py          # UI and properties
│           ├── workspace_setup.py   # Workspace and compositor setup
│           ├── utils.py             # Helper functions
│           └── README.md            # This file
└── data/
    └── temp/
        └── ai_vision/
            ├── session.json         # Your session data (auto-updated)
            ├── current_ai.png       # Latest AI image
            └── combined.jpg         # Workbench render sent to AI (JPEG for fast upload, depth generated by AI)
```

---

## What's Next?

Style Engine is designed to be the foundation for a complete AI generation pipeline. The current version focuses on:
- ✅ Workspace setup and camera management
- ✅ Real-time render pass generation
- ✅ Session data management via JSON
- ✅ Dynamic object grouping system
- ✅ UI for controlling all settings

**Future Integration (Not Yet Implemented):**
- 🔄 Actual AI image generation from render passes
- 🔄 Object assignment to groups via "Assign" button
- 🔄 Communication with external AI agents
- 🔄 Committed render management

For technical details about the JSON schema and how to integrate AI generation, see `context/JSON_SCHEMA.md`.

---

## Need Help?

- Check the Blender Console for debug messages: Window → Toggle System Console
- All operations print status messages prefixed with `[Style Engine]`
- The `session.json` file shows exactly what settings are active


