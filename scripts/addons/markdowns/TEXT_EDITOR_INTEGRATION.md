# Text Editor Integration - Automatic Prompt System

**Updated: 2025-11-04 21:25**

## Overview

Style Engine now features a **fully automatic prompt system** that uses Blender's built-in text editor for comfortable, multi-line prompt writing. No manual buttons or syncing required - everything happens automatically!

---

## 🎯 Key Features

### 1. **Automatic Workspace Layout**
When you run **"Setup Workspace"**, the addon creates an optimal layout:

```
┌─────────────────────────────┬─────────┐
│                             │         │
│                             │ CAMERA  │
│   MODELING VIEW (75%)       │  VIEW   │
│                             │ (LOCKED)│
│                             │         │
│                             ├─────────┤
│                             │  TEXT   │
│                             │ EDITOR  │
└─────────────────────────────┴─────────┘
       Left: 75%                Right: 25%
```

**Right Column Breakdown:**
- Top 2/3: Locked camera view showing AI preview
- Bottom 1/3: Text editor with your prompt

### 2. **Auto-Created Prompt File**
The addon automatically creates a text block called `STYLEENGINE_Prompt` with:
- Header with instructions and update timestamp
- Your default prompt as a starting point
- Support for comments (lines starting with `#`)
- Multi-line editing capabilities

### 3. **Cyclical Auto-Sync**
**No manual syncing required!** Every time you click **"Generate AI Image"**:
1. ✅ Auto-reads the text from the editor
2. ✅ Filters out comments (`#` lines) and empty lines
3. ✅ Updates the prompt used for generation
4. ✅ Continues with rendering and AI generation

---

## 📝 How to Use

### Step 1: Setup Workspace
Click **"Setup Workspace"** in the Style Engine panel. This will:
- Create the AI camera
- Split the workspace into modeling + camera + text editor
- Create the `STYLEENGINE_Prompt` text block
- Set up automatic pass rendering

### Step 2: Write Your Prompt
The text editor (bottom-right) is now ready! Write your prompt with:
- **Multiple lines** for readability
- **Comments** starting with `#` (ignored during generation)
- **Quick edits** anytime you want

Example:
```python
# STYLEENGINE_Prompt - Last updated: 2025-11-04 21:25
# Lines starting with # are comments and will be ignored
# Write your prompt below:

This is scene 1. 
Gotham city, dark atmosphere, rain.
A hamster wearing a detective outfit.
Film noir style, dramatic lighting.

# Notes: try adding "moody" or "cinematic"
```

### Step 3: Generate
Just click **"Generate AI Image"**! The prompt is automatically read from the text editor and used for generation.

---

## 🔄 Automatic Behavior

### What Happens Automatically:
✅ Text editor created in workspace layout  
✅ Prompt file (`STYLEENGINE_Prompt`) created  
✅ Prompt synced from editor on every generation  
✅ Comments and empty lines filtered out  
✅ Timestamp updated in prompt header  

### What You Control:
🎨 Edit your prompt anytime in the text editor  
🎨 Use single-line "Quick Edit" in the panel if needed  
🎨 Reposition camera with "Reposition AI Camera" button  
🎨 Toggle features in Advanced Settings  

---

## 🛠️ Technical Details

### Non-Invasive Design
- Uses standard Blender text editor (no custom UI)
- Works with all Blender themes and keyboard shortcuts
- Compatible with macOS, Windows, Linux
- No hardcoded paths - all relative references

### Files Involved
- `workspace_setup.py`: Creates layout and text editor automatically
- `utils.py`: Helper functions for reading/writing prompt text
- `ui_panel.py`: Simplified UI (no manual sync buttons)

### Text Block Naming
The prompt text block is always named: `STYLEENGINE_Prompt`
- Created automatically if it doesn't exist
- Persisted in your `.blend` file
- Can be manually edited or deleted

---

## 🚀 Benefits Over Old System

| Old System | New System |
|------------|------------|
| Single-line input box | Multi-line text editor |
| Manual sync buttons | Automatic sync on generate |
| No comment support | Lines starting with `#` ignored |
| Cramped editing | Full editor with syntax highlighting |
| Hidden in panel | Always visible in workspace |
| Manual setup | Auto-created with workspace |

---

## 🔍 Troubleshooting

### "I don't see the text editor"
- Make sure you ran **"Setup Workspace"**
- Check that `Enable Viewport Split` is ON in Advanced Settings
- Manually switch any area to "Text Editor" and select `STYLEENGINE_Prompt`

### "My prompt isn't updating"
- The prompt updates **only when you click Generate**
- Check the console for: `[Style Engine] ✓ Auto-synced prompt from text editor`
- Verify the text block is named exactly `STYLEENGINE_Prompt`

### "I want to use the old single-line input"
- You can! The "Current Prompt" field in the panel still works
- Edit it directly and it will be used for generation
- However, the text editor is recommended for longer prompts

---

## 🎨 Workflow Tips

### Iterative Prompting
1. Write a base prompt in the text editor
2. Generate and review the result
3. Edit the prompt directly in the editor
4. Generate again - no manual syncing needed!

### Using Comments
```python
# BASE SCENE
This is scene 1. Gotham city.

# CHARACTER (try different animals)
A hamster wearing a detective outfit.
# A cat wearing a trench coat.

# STYLE
Film noir, dramatic lighting.
```

### Quick Variations
Keep multiple prompt versions as comments, uncomment the one you want:

```python
# Version 1: Dark and moody
# This is scene 1. Gotham, dark, rain.

# Version 2: Bright and hopeful
This is scene 1. Metropolis, sunny, clear skies.
```

---

## 🔐 macOS Compatibility

Fully tested and compatible with macOS!
- No path separator issues (`/` vs `\`)
- No hardcoded paths
- Uses Blender's native text editor API
- Follows all macOS-proofing guidelines

---

## 📦 What Changed in This Update

### Added
- Automatic text editor creation in workspace layout
- Auto-sync prompt from editor on generation
- Comment support in prompts (`#` lines ignored)
- Timestamp in default prompt for version tracking

### Removed
- Manual "Open Prompt Editor" button
- Manual "Sync from Editor" button
- Manual "Save to Editor" button

### Changed
- Workspace layout: 75% modeling + 25% (camera + text editor)
- Text editor always shows prompt (no manual linking)
- UI simplified: "Current Prompt" is read-only preview

---

## 💡 Future Enhancements (Ideas)

- [ ] Prompt templates/presets
- [ ] Prompt history/undo
- [ ] Multi-prompt management for different scenes
- [ ] Syntax validation for common mistakes
- [ ] Token count estimation

---

**For more information, see:**
- `README_MACOS_PROOFING.md` - macOS compatibility details
- `UI_FEATURES.md` - Overall UI documentation
- `WORKFLOW_SYSTEM.md` - Complete workflow guide

