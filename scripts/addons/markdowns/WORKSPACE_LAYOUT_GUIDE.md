# Workspace Layout Guide - Style Engine

**Updated: 2025-11-04 21:25**

## Automatic Layout Configuration

When you run **"Setup Workspace"**, Style Engine creates an optimal layout for AI-assisted 3D modeling.

---

## 📐 Layout Diagram

```
╔═══════════════════════════════════════════════════════════════════════╗
║                          BLENDER WINDOW                               ║
╠═══════════════════════════════════╦═══════════════════════════════════╣
║                                   ║                                   ║
║                                   ║     ┌───────────────────────┐    ║
║                                   ║     │   AI CAMERA VIEW      │    ║
║                                   ║     │   (LOCKED)            │    ║
║           MODELING VIEW           ║     │                       │    ║
║           (3D Viewport)           ║     │   Shows:              │    ║
║                                   ║     │   - Combined pass     │    ║
║           - Free navigation       ║     │   - AI preview        │    ║
║           - Model your scene      ║     │   - Depth viz (AO)    │    ║
║           - Position objects      ║     │                       │    ║
║           - Edit geometry         ║     │   Press Numpad 0      │    ║
║                                   ║     │   to toggle           │    ║
║                                   ║     └───────────────────────┘    ║
║                                   ║              66%                  ║
║           75% of screen           ╠═══════════════════════════════════╣
║                                   ║                                   ║
║                                   ║     ┌───────────────────────┐    ║
║                                   ║     │   TEXT EDITOR         │    ║
║                                   ║     │   STYLEENGINE_Prompt  │    ║
║                                   ║     │                       │    ║
║                                   ║     │   Write your prompts  │    ║
║                                   ║     │   Multi-line support  │    ║
║                                   ║     │   Comment support (#) │    ║
║                                   ║     │   Auto-syncs          │    ║
║                                   ║     └───────────────────────┘    ║
║                                   ║              33%                  ║
╚═══════════════════════════════════╩═══════════════════════════════════╝
```

---

## 📏 Proportions

### Horizontal Split
```
├────────────────────────────────┤├─────────┤
           75%                        25%
    (Modeling View)        (Camera + Text Editor)
```

### Right Column Vertical Split
```
┌─────────┐
│         │
│ CAMERA  │ ← 66% (top 2/3)
│  VIEW   │
│ LOCKED  │
├─────────┤
│  TEXT   │
│ EDITOR  │ ← 33% (bottom 1/3)
└─────────┘
```

---

## 🎯 Area Purposes

### Left: Modeling View (75%)
**Purpose**: Main workspace for 3D modeling
- **Type**: 3D Viewport
- **Perspective**: User-controlled (free navigation)
- **Lock**: Not locked (you can rotate, pan, zoom)
- **Use For**:
  - Building your scene
  - Positioning objects
  - Selecting and editing geometry
  - Standard Blender modeling workflow

### Top-Right: Camera View (16.5% of total screen)
**Purpose**: AI preview and rendering output
- **Type**: 3D Viewport
- **Perspective**: Camera (Numpad 0 view)
- **Lock**: Locked to camera (`space.lock_camera = True`)
- **Use For**:
  - Preview what the AI sees
  - View combined pass with depth info
  - See the exact render framing
  - Monitor AI generation results

### Bottom-Right: Text Editor (8.5% of total screen)
**Purpose**: Comfortable prompt writing
- **Type**: Text Editor
- **Text Block**: `STYLEENGINE_Prompt`
- **Lock**: Not locked (editable)
- **Use For**:
  - Writing multi-line prompts
  - Adding comments and notes
  - Organizing prompt variations
  - Quick edits between generations

---

## 🔄 Setup Process

### What Happens When You Click "Setup Workspace"

```python
1. Create/find AI workspace
   └─> Duplicates current workspace or creates "AI" workspace

2. Create AI camera
   └─> Named "AI Camera" (configurable in Advanced Settings)
   └─> Positioned at current view or (0, -10, 5)

3. Setup render passes
   └─> Combined pass (RGB render)
   └─> Depth pass (Z-buffer for AI understanding)
   └─> AO pass (ambient occlusion for detail)

4. SPLIT WORKSPACE - First split (vertical)
   └─> Direction: VERTICAL
   └─> Factor: 0.75 (75% left, 25% right)
   └─> Creates: Modeling view (left) + New area (right)

5. CONFIGURE CAMERA VIEW
   └─> Right area -> Camera perspective
   └─> Lock camera = True
   └─> Show background images = True

6. SPLIT AGAIN - Second split (horizontal)
   └─> Area: Right area from step 4
   └─> Direction: HORIZONTAL
   └─> Factor: 0.66 (66% top, 33% bottom)
   └─> Creates: Camera view (top) + New area (bottom)

7. CONVERT TO TEXT EDITOR
   └─> Bottom area -> Text Editor type
   └─> Create STYLEENGINE_Prompt text block
   └─> Load prompt from properties
   └─> Enable line numbers and syntax highlighting

8. START AUTO-REFRESH
   └─> Timer-based background image updates
   └─> Shows latest AI generation in camera view
```

---

## ⚙️ Configuration Options

### Advanced Settings (Preferences)
You can customize the layout behavior:

```python
# Enable/Disable Features
enable_viewport_split = True   # Toggle entire split system
enable_camera_switching = True # Allow camera activation
enable_workspace_creation = True # Create "AI" workspace

# Custom Names
camera_name_override = "AI Camera"
workspace_name_override = "AI"
```

### Manual Override
If automatic splitting fails, you can manually:
1. Split viewport: Drag from top-right corner of any area
2. Set camera view: View → Cameras → Active Camera (Numpad 0)
3. Lock camera: Sidebar (N) → View → Lock Camera to View
4. Add text editor: Click area type icon → Text Editor
5. Select text: Dropdown → `STYLEENGINE_Prompt`

---

## 🎨 Workflow Example

### Typical Session Flow

```
1. Open Blender → Style Engine panel
   └─> Click "Setup Workspace"
      └─> Layout automatically configured ✓

2. Left viewport: Model your scene
   └─> Add objects, materials, lights
   └─> Position everything

3. Bottom-right: Write your prompt
   └─> "A cinematic shot of a futuristic city"
   └─> Add comments for variations

4. Click "Generate AI Image"
   └─> Prompt auto-synced from text editor ✓
   └─> Renders passes automatically ✓
   └─> Sends to AI ✓
   └─> Updates camera view automatically ✓

5. Review in camera view (top-right)
   └─> See AI generation result
   └─> Compare with your 3D model

6. Iterate!
   └─> Edit prompt in text editor
   └─> Adjust 3D scene
   └─> Generate again
   └─> Repeat until perfect
```

---

## 🚀 Benefits of This Layout

### ✅ Efficiency
- **One screen, all tools**: No window switching
- **Always visible**: Camera and prompt in view
- **Quick comparison**: See 3D model and AI result side-by-side

### ✅ Ergonomics
- **Comfortable editing**: Text editor at bottom
- **Main focus**: 75% for modeling (where you spend most time)
- **Preview visible**: Always see what AI will receive

### ✅ Automatic
- **No manual setup**: One click creates entire layout
- **No manual sync**: Prompt updates on generation
- **No manual refresh**: Camera view auto-updates

---

## 🔧 Troubleshooting

### "Split didn't work"
**Causes:**
- Window too small (minimum ~1920x1080 recommended)
- Blender version < 4.2 (uses old API)
- `enable_viewport_split = False` in preferences

**Solutions:**
- Increase window size
- Update Blender to 4.2+
- Enable viewport split in Advanced Settings
- Split manually (see Manual Override above)

### "Can't see text editor"
**Causes:**
- Second split failed (but camera view worked)
- Text editor area too small
- Wrong text block selected

**Solutions:**
- Manually convert any area to Text Editor
- Select `STYLEENGINE_Prompt` from dropdown
- Resize areas by dragging borders

### "Camera view is not locked"
**Causes:**
- Lock camera setting didn't apply
- You manually unlocked it

**Solutions:**
- In camera view: Press N → View → Lock Camera to View
- Or re-run "Setup Workspace"

### "Prompt not syncing"
**Causes:**
- Text block renamed
- Wrong text block in editor

**Solutions:**
- Ensure text block is named exactly: `STYLEENGINE_Prompt`
- Check console for sync messages
- Manually type in "Current Prompt" field in panel

---

## 📱 Responsive Behavior

The layout adapts to different screen sizes:

### Large Screen (≥1920x1080)
- Ideal: All areas comfortably visible
- Modeling: 1440px width
- Camera: 384px width, 256px height
- Text: 384px width, 128px height

### Medium Screen (~1366x768)
- Functional: All areas visible but compact
- Modeling: 1024px width
- Camera: 342px width, 227px height
- Text: 342px width, 113px height

### Small Screen (<1366x768)
- Cramped: May need to resize areas manually
- Consider using single viewport + external text editor
- Or disable viewport split in preferences

---

## 🎥 Camera View Details

### Background Image Setup
The camera view shows background images automatically:
- **Layer 1**: Combined pass (RGB render)
- **Layer 2**: Depth pass (when toggled)
- **Auto-refresh**: Every 0.5 seconds (configurable)

### Camera Controls
Even though locked, you can:
- **Reposition**: Use "Reposition AI Camera" button
- **Unlock temporarily**: Toggle Lock Camera to View
- **View from camera**: Numpad 0 in any viewport

---

## 🔬 Technical Implementation

### Code Location
`workspace_setup.py` → `_delayed_split_setup_standalone(camera)`

### Key Operations
```python
# First split: 75% / 25%
bpy.ops.screen.area_split(
    direction='VERTICAL', 
    factor=0.75
)

# Second split: 66% / 33%
bpy.ops.screen.area_split(
    direction='HORIZONTAL', 
    factor=0.66
)

# Convert to text editor
bottom_area.type = 'TEXT_EDITOR'
bottom_area.spaces.active.text = prompt_text
```

### macOS Compatibility
✅ No path separators (`/` or `\`)  
✅ No hardcoded paths  
✅ Uses Blender's native area splitting API  
✅ Fully tested on macOS, Windows, Linux  

---

**Related Documentation:**
- `TEXT_EDITOR_INTEGRATION.md` - Prompt system details
- `UI_FEATURES.md` - Panel and controls
- `WORKFLOW_SYSTEM.md` - Complete workflow guide
- `README_MACOS_PROOFING.md` - Cross-platform compatibility

