# Style Engine - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     STYLE ENGINE ADDON                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  ui_panel   │  │   prefs     │  │    utils    │            │
│  │             │  │             │  │             │            │
│  │ • Panel     │  │ • API Keys  │  │ • Helpers   │            │
│  │ • Props     │  │ • Env Vars  │  │ • Validate  │            │
│  │ • Operators │  │ • Test Conn │  │ • Get Creds │            │
│  └─────┬───────┘  └──────┬──────┘  └──────┬──────┘            │
│        │                 │                 │                   │
│        └─────────────────┴─────────────────┘                   │
│                          │                                     │
│                ┌─────────▼──────────┐                          │
│                │  workspace_setup   │                          │
│                │                    │                          │
│                │ • Setup Workspace  │                          │
│                │ • Create Camera    │                          │
│                │ • Split Layout     │                          │
│                │ • Config BG Image  │                          │
│                └─────────┬──────────┘                          │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BLENDER SCENE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┬──────────────────────┐               │
│  │                      │                      │               │
│  │   LEFT VIEWPORT      │   RIGHT VIEWPORT     │               │
│  │   ═════════════      │   ══════════════     │               │
│  │                      │                      │               │
│  │   [3D Modeling]      │   [Camera View]      │               │
│  │                      │                      │               │
│  │   • Free Nav         │   • Locked to        │               │
│  │   • All Tools        │     ai_camera        │               │
│  │   • Standard View    │   • Shows BG Image   │               │
│  │                      │   • 100% Opacity     │               │
│  │                      │                      │               │
│  │   User Models  ─────▶│   AI Vision          │               │
│  │   Here               │   Displays Here      │               │
│  │                      │                      │               │
│  └──────────────────────┴──────────────────────┘               │
│                                │                                │
│                                │                                │
│                     ┌──────────▼──────────┐                    │
│                     │     ai_camera       │                    │
│                     │                     │                    │
│                     │ • Position: User's  │                    │
│                     │   current view      │                    │
│                     │ • BG Image: ON      │                    │
│                     │ • Opacity: 100%     │                    │
│                     │ • Display: FRONT    │                    │
│                     └──────────┬──────────┘                    │
│                                │                                │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   YourProject/                                                  │
│   ├── YourFile.blend                                            │
│   └── temp/                                                     │
│       └── ai_vision/                                            │
│           └── current_ai.png  ◀── Background image source       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow (Current MVP)

```
┌──────────────────────────────────────────────────────────────┐
│  1. USER ACTION                                              │
└────────┬─────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  User clicks "Setup Workspace" button                      │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  2. WORKSPACE SETUP                                        │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Create temp/ai_vision/ directory                  │ │
│  │  • Generate placeholder image                        │ │
│  │  • Create/find ai_camera object                      │ │
│  │  • Position at user's current view                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  3. CAMERA CONFIGURATION                                   │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Enable background images                          │ │
│  │  • Point to temp/ai_vision/current_ai.png           │ │
│  │  • Set opacity: 100%                                 │ │
│  │  • Set display depth: FRONT                          │ │
│  │  • Set as active camera                              │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  4. WORKSPACE LAYOUT                                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Create "AI" workspace                             │ │
│  │  • Switch to workspace                               │ │
│  │  • Split into left/right (via timer)                 │ │
│  │  • Lock right viewport to camera                     │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  5. RESULT                                                 │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Left: Modeling viewport                             │ │
│  │  Right: Camera view with background image overlay    │ │
│  │  Ready for AI pipeline integration                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

## Data Flow (Future - With AI Pipeline)

```
┌────────────────────────────────────────────────────────────┐
│  CONTINUOUS LOOP (Every X seconds)                         │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  1. CAPTURE                                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Timer triggers                                    │ │
│  │  • Render left viewport from ai_camera view          │ │
│  │  • Save to temp file                                 │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  2. PREPARE                                                │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Get scene description & keywords                  │ │
│  │  • Get object-specific keywords                      │ │
│  │  • Get depth influence & silhouette settings         │ │
│  │  • Build AI prompt                                   │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  3. API CALL                                               │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Get credentials (utils.get_runcomfy_api_token)   │ │
│  │  • Prepare request with image + prompt              │ │
│  │  • POST to RunComfy API                              │ │
│  │  • Wait for response                                 │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  4. PROCESS RESPONSE                                       │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Receive AI-generated image                        │ │
│  │  • Save as temp/ai_vision/current_ai.png            │ │
│  │  • Overwrite previous version                        │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  5. UPDATE DISPLAY                                         │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Reload image in Blender                           │ │
│  │  • Right viewport automatically updates              │ │
│  │  • User sees AI-styled version                       │ │
│  └──────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│  6. SCHEDULE NEXT                                          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  • Wait X seconds                                    │ │
│  │  • Return to step 1                                  │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
__init__.py
    ├─► prefs.py
    │       └─► Preferences panel
    │       └─► API key management
    │
    ├─► utils.py
    │       └─► get_runcomfy_api_token()
    │       └─► get_runcomfy_user_id()
    │       └─► validate_runcomfy_credentials()
    │       └─► get_api_headers()
    │
    ├─► workspace_setup.py
    │       └─► WM_OT_SetupWorkspace
    │       └─► WM_OT_ConfigureWorkspaceLayout
    │
    └─► ui_panel.py
            ├─► StyleEngineProperties
            ├─► WM_OT_Visualize ──┐
            ├─► WM_OT_Create3D    ├─► Use utils.py for API access
            ├─► WM_OT_Render ─────┘
            └─► VIEW3D_PT_StyleEngine
```

## Operator Relationships

```
UI Button Click
      │
      ▼
┌─────────────────────────────────┐
│  style_engine.setup_workspace   │  Main MVP operator
│  (WM_OT_SetupWorkspace)         │
├─────────────────────────────────┤
│  • ensure_temp_directory()      │
│  • create_ai_camera()           │
│  • align_camera_to_view()       │
│  • setup_camera_background()    │
│  • create_ai_workspace()        │
│  • setup_workspace_layout()     │
└─────────┬───────────────────────┘
          │
          │ Triggers via timer
          ▼
┌─────────────────────────────────────┐
│  delayed_split_setup()              │  Internal method
│  (WM_OT_ConfigureWorkspaceLayout)   │
├─────────────────────────────────────┤
│  • Split viewport                   │
│  • Lock right view to camera        │
└─────────────────────────────────────┘
```

## File System Structure

```
STYLEENGINE/
│
├── Documentation
│   ├── README.md                 # Main overview
│   ├── MVP_AI_VISION.md         # MVP feature docs
│   ├── MVP_SUMMARY.md           # This implementation summary
│   ├── ARCHITECTURE.md          # This file
│   ├── TESTING_CHECKLIST.md     # Testing guide
│   └── API_SETUP_GUIDE.md       # Credentials guide
│
├── Addon Code
│   └── scripts/addons/styleengine/
│       ├── __init__.py          # Registration
│       ├── blender_manifest.toml # Blender 4.2+ metadata
│       ├── prefs.py             # Preferences
│       ├── utils.py             # Helpers
│       ├── workspace_setup.py   # MVP core
│       ├── ui_panel.py          # UI
│       └── README.md            # Code docs
│
├── Runtime Data (created at runtime)
│   └── temp/
│       └── ai_vision/
│           └── current_ai.png   # AI output
│
└── Context
    └── context/
        └── context.txt          # Project vision
```

## API Integration Points (Ready for Implementation)

```
┌─────────────────────────────────────────────────────────────┐
│  STYLE ENGINE                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  utils.get_runcomfy_api_token() ────────┐                  │
│  utils.get_runcomfy_user_id() ──────────┼──────┐           │
│  utils.get_api_headers() ───────────────┘      │           │
│                                                 │           │
└─────────────────────────────────────────────────┼───────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  RUNCOMFY API                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  POST /api/generate                                         │
│  Headers:                                                   │
│    Authorization: Bearer {token}                            │
│    Content-Type: application/json                           │
│  Body:                                                      │
│    {                                                        │
│      "user_id": "{user_id}",                                │
│      "image": "{base64_encoded_render}",                    │
│      "prompt": "{scene_description + keywords}",            │
│      "settings": {                                          │
│        "depth_influence": 0.5,                              │
│        "silhouette": 0.75                                   │
│      }                                                      │
│    }                                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Property Flow

```
UI Input (Style Engine Panel)
         │
         ▼
┌──────────────────────────────────┐
│  StyleEngineProperties           │
├──────────────────────────────────┤
│  • library_id                    │
│  • scene_description             │
│  • scene_keywords                │
│  • building_keywords             │
│  • tunnel_keywords               │
│  • ground_keywords               │
│  • depth_influence               │
│  • silhouette                    │
└────────┬─────────────────────────┘
         │
         │ Accessed via:
         │ context.scene.style_engine_props
         │
         ▼
┌──────────────────────────────────┐
│  Operators                       │
├──────────────────────────────────┤
│  • Read properties               │
│  • Build AI prompt               │
│  • Configure generation          │
│  • Send to API                   │
└──────────────────────────────────┘
```

## Timer System (For Future Auto-Refresh)

```
┌─────────────────────────────────────────────────────────────┐
│  bpy.app.timers.register()                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  def auto_refresh():                                        │
│      1. Capture viewport                                    │
│      2. Call AI API                                         │
│      3. Update current_ai.png                               │
│      4. Reload image                                        │
│      5. return INTERVAL  # Continue timer                   │
│                                                             │
│  Timer Properties:                                          │
│    • Interval: User-configurable (e.g., 30s)               │
│    • Persistent: True (continues between operations)        │
│    • Cancellable: Can be stopped by user                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## State Management

```
┌─────────────────────────────────────────────────────────────┐
│  SCENE STATE                                                │
├─────────────────────────────────────────────────────────────┤
│  • context.scene.camera = ai_camera                         │
│  • context.scene.style_engine_props = PropertyGroup         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  WORKSPACE STATE                                            │
├─────────────────────────────────────────────────────────────┤
│  • "AI" workspace created                                   │
│  • Left viewport: Free 3D view                              │
│  • Right viewport: Camera-locked                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  CAMERA STATE                                               │
├─────────────────────────────────────────────────────────────┤
│  • ai_camera.location = User's view position                │
│  • ai_camera.rotation = User's view rotation                │
│  • Background image enabled                                 │
│  • Image path: temp/ai_vision/current_ai.png               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  PREFERENCES STATE                                          │
├─────────────────────────────────────────────────────────────┤
│  • API credentials stored                                   │
│  • Environment variables checked                            │
│  • Use_env_vars preference                                  │
└─────────────────────────────────────────────────────────────┘
```

---

**This architecture provides a solid foundation for the AI vision system with clear separation of concerns and easy extensibility.**

