# Visualization Switcher - Quick Summary
**Feature:** Quick visualization switching in pie menu  
**Hotkey:** `Alt+W` → Right slot  
**Status:** ✅ Ready to use

---

## 🎯 What It Does

Replaces the deprecated "Reference Image" slot in the pie menu with a **Visualization Switcher** that lets you instantly switch the camera background between:

| Mode | Shows | File | Icon |
|------|-------|------|------|
| **Combined** | Final generated image | `current_ai.png` | 🖼️ |
| **Silhouette** | Canny edge detection | `canny.png` | 🔲 |
| **Depth** | Depth Anything map | `depth.png` | ➡️ |

---

## 🎮 How to Use

1. Press `Alt+W` (Style Engine pie menu)
2. Look at **RIGHT** position
3. Click **Combined**, **Silhouette**, or **Depth**
4. Camera background switches instantly! ✨

---

## ⚙️ Requirements

- ✅ Backend Mode = "Self-Hosted ComfyUI" (GCS)
- ✅ "Download Preview Images" enabled in preferences
- ✅ At least one generation completed

**If disabled:** Pie menu shows a helpful message explaining how to enable it.

---

## 🎨 Why It's Useful

### For Debugging:
- See what edges the AI detects (Silhouette)
- See what depth the AI perceives (Depth)
- Compare with final result (Combined)

### For Quality Control:
- Verify ControlNet preprocessing is working
- Identify issues before generation
- Understand AI decision-making

### For Learning:
- Understand how ControlNet interprets your scene
- See correlation between preprocessing and results
- Improve scene setup for better AI output

---

## 🔄 Auto-Reset

After each generation, visualization automatically resets to **Combined** (final image). This ensures you always see the new result first!

---

## 📁 Files Modified

1. **`ui_panel.py`** - Added `visualization_type` property with update callback
2. **`pie_menu.py`** - Replaced "Reference Image" slot with visualization switcher
3. **`workspace_setup.py`** - Auto-reset to COMBINED after generation

---

## 🚀 Next Steps

1. Reload addon in Blender
2. Enable "Download Preview Images" in GCS preferences
3. Generate an image
4. Press `Alt+W` → Right → Try switching views!

---

**Quick Tip:** Use this feature to understand what the AI "sees" and improve your scene setup for better results! 🎯

