# Style Engine - Release Notes
**Version:** 0.2.2  
**Date:** November 21, 2025  
**Build:** styleengine.zip (364 KB, 29 files)

---

## 🎉 Major Features

### 1. **Per-Project Library System** 🆕
Automatic image management with project-based organization.

**Features:**
- ✅ Every generation automatically saved
- ✅ Per-project folders (`MyProject_styleengine/`)
- ✅ Session-based temp for unsaved files
- ✅ Automatic migration when saving .blend
- ✅ Never lose work

**Directory Structure:**
```
MyProject.blend
MyProject_styleengine/
├── generations/     ← All AI generations (timestamped)
├── iterations/      ← Projected textures (backup)
├── preview/         ← Canny/Depth maps
└── current_ai.png   ← Latest for camera
```

### 2. **Generation Browser** 🆕
Navigate through saved generations and remix textures.

**Features:**
- ✅ Previous/Next navigation (◀ ▶)
- ✅ Real-time camera updates
- ✅ Load any generation to current_ai
- ✅ Mix different generations on different objects
- ✅ Position indicator (Latest/X of N)

**Location:** Alt+W → RIGHT (Visualization section)

### 3. **Enhanced Texture Projection** 🆕
Improved projection workflow with archival system.

**Features:**
- ✅ Project on selected objects only (not all scene)
- ✅ Archival materials (iteration_000, iteration_001, etc.)
- ✅ Archival images (packed + external backup)
- ✅ Matte finish (roughness 1.0)
- ✅ Specular Tint connection (prevents white IOR look)

**Button:** "Project on Object" (renamed from "Project in Scene")

### 4. **Clean Slate System** 🆕
Fresh black placeholder on workspace setup.

**Features:**
- ✅ Black placeholder on every workspace setup
- ✅ No old temp images bleeding through
- ✅ Clear visual feedback (black = no generation)
- ✅ Professional, predictable behavior

### 5. **Template Cleanup** 🆕
Streamlined to 3 professional templates.

**Templates:**
- ✅ **Empty** - Blank slate for custom prompts
- ✅ **Vizdev** - Concept art / visual development
- ✅ **Photorealistic** - Professional photography

**Removed:** 7 random subject templates (dragons, robots, etc.)

---

## 🔧 Technical Improvements

### Session Management
- Unique session IDs for unsaved files
- Automatic migration on .blend save
- "Save As" detection
- Non-destructive migration (copies, not moves)

### File Naming
```
Format: YYYYMMDD_HHMMSS_mmm_backend.png
Example: 20251121_143022_001_gcs.png

Components:
- Date: YYYYMMDD
- Time: HHMMSS
- Milliseconds: 000-999
- Backend: gcs/runcomfy/local
```

### Iterations Folder
- External backup of projected textures
- Migrates with session data
- Portable and shareable
- Recoverable if .blend corrupts

---

## 🎨 Workflow Enhancements

### Iterative Remixing
```
1. Generate multiple AI variations
2. Navigate through them (◀ ▶)
3. Project different generations on different objects
4. Build complex scenes with mixed styles
```

### Project Continuity
```
1. Work on unsaved file → Images in session temp
2. Save .blend → Automatic migration to project library
3. Close and reopen → All history preserved
4. Navigate through generations → Continue work
```

### Texture Management
```
1. Project texture → Creates iteration_000
2. Texture saved to iterations/ folder
3. Packed into .blend file
4. Both external and embedded backup
```

---

## 📦 Package Contents

**Total:** 29 files, 364 KB

### Core Files:
- `__init__.py` (9.4 KB) - Main initialization
- `workspace_setup.py` (129.8 KB) - Core functionality + session management
- `ui_panel.py` (89.3 KB) - UI + texture projection
- `pie_menu.py` (19.7 KB) - Pie menu + generation browser
- `prefs.py` (47.9 KB) - Preferences
- `utils.py` (25.1 KB) - Utilities

### Workflows:
- `StyleEngineTexture.json` (22.5 KB) - Main img2img workflow
- `StyleEnginePreview.json` (22.3 KB) - Preview with Canny/Depth
- `StyleEngine.json` (21.9 KB) - Legacy workflow

### Templates:
- `STYLEENGINE_Empty.txt` - Blank slate
- `STYLEENGINE_Vizdev.txt` - Concept art
- `STYLEENGINE_Photorealistic.txt` - Photography

### Other:
- `template.blend` (235.9 KB) - Workspace template
- 7 prompt templates
- Documentation files
- RunComfy client modules

---

## 🎯 Key Features Summary

### Backend Support:
- ✅ Local ComfyUI
- ✅ RunComfy (serverless)
- ✅ GCS (self-hosted)

### Workflows:
- ✅ Text-to-image (txt2img)
- ✅ Image-to-image (img2img) with texture control
- ✅ ControlNet (Canny + Depth Anything)
- ✅ IPAdapter (15 reference images)

### UI Features:
- ✅ Pie menu (Alt+W)
- ✅ Visualization switcher (Combined/Silhouette/Depth)
- ✅ Render quality selector (Fast/Detailed)
- ✅ Generation browser (◀ ▶)
- ✅ Progress tracking
- ✅ Reference image thumbnails

### Data Management:
- ✅ Per-project libraries
- ✅ Session management
- ✅ Automatic migration
- ✅ Timestamped filenames
- ✅ External backups

### Texture Projection:
- ✅ Selected objects only
- ✅ Archival materials
- ✅ External texture backup
- ✅ Matte finish optimization
- ✅ Iteration snapshots

---

## 🚀 Installation

1. **Uninstall old version** (if installed)
2. **Restart Blender**
3. Edit → Preferences → Add-ons
4. Click "Install from Disk..."
5. Select `styleengine.zip`
6. Enable "Style Engine" addon
7. Configure API credentials

---

## 📊 What's New in This Build

### Major Features:
- 🆕 Per-Project Library System
- 🆕 Generation Browser with navigation
- 🆕 Enhanced texture projection (selected objects)
- 🆕 Archival materials and textures
- 🆕 Clean slate black placeholder
- 🆕 Template cleanup (3 professional templates)

### Improvements:
- 🔧 Session management with unique IDs
- 🔧 Automatic migration on save
- 🔧 Timestamped filenames with backend tracking
- 🔧 External texture backups
- 🔧 Matte finish with Specular Tint
- 🔧 Smart button states in UI

### Bug Fixes:
- 🐛 Fixed indentation errors in prefs.py
- 🐛 Fixed indentation errors in ui_panel.py
- 🐛 Fixed old temp images showing on workspace setup
- 🐛 Fixed thumbnail display issues

---

## 🎨 Recommended Workflow

### For Concept Artists:
1. Use **Vizdev** template
2. Generate multiple variations
3. Navigate with ◀ ▶
4. Project best generations on objects
5. Build scene with mixed styles

### For Product Visualization:
1. Use **Photorealistic** template
2. Set render quality to **Detailed** (EEVEE)
3. Generate with high texture influence
4. Project on product geometry
5. Export iterations for client review

### For Iterative Design:
1. Generate rough concepts quickly
2. Save all to project library
3. Navigate through history
4. Remix old with new
5. Build complex scenes incrementally

---

## ⚠️ Breaking Changes

### None!
All changes are backwards compatible. Existing workflows continue to work.

### Optional Migration:
- Old temp files remain in system temp
- New generations use project library
- Both systems coexist peacefully

---

## 🔮 Coming Soon (Future Releases)

### Phase 2: Advanced Browser
- Thumbnail previews
- Metadata display (prompt, settings, duration)
- Search and filter
- Export selections

### Phase 3: Project Management
- Generation history JSON
- Link generations to iterations
- Batch operations
- Auto-cleanup old generations

---

## 📌 Credits

**Development Team:** Spiri Bros Co  
**Technical Lead:** Juan  
**Feedback:** Ian (texture projection workflow)

---

## 🎯 Summary

This release transforms Style Engine into a **professional asset management system** with:
- Robust per-project organization
- Iterative remixing capabilities
- Never lose work
- Clean, predictable behavior

**Package:** `styleengine.zip` (364 KB, 29 files)  
**Ready for:** Production use, team distribution, client projects

**Install and enjoy the new iterative workflow!** 🎨✨


