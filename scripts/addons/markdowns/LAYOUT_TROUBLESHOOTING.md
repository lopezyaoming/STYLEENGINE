# Layout Troubleshooting Guide

**Issue**: Setup Workspace doesn't create the camera view above text editor

---

## 🔍 Diagnostic Steps

### Step 1: Enable Debug Mode
1. Edit → Preferences → Add-ons
2. Find "Style Engine" addon
3. Expand the addon settings (click arrow)
4. Check "Debug Mode" ✓
5. Click "Save Preferences"

### Step 2: Run Setup Workspace Again
1. Delete the current text editor area (if it exists)
   - Drag the text editor's corner to merge it back with main viewport
2. Click "Setup Workspace" again
3. Watch the console for debug messages

### Step 3: Check Console Output
Open the console (Window → Toggle System Console on Windows)

**Expected output:**
```
[Style Engine] Found 2 3D viewports after first split
[Style Engine] Right area dimensions: [width]x[height]
[Style Engine] ✓ Camera view configured (top)
[Style Engine] Total areas before horizontal split: 2
[Style Engine] Total areas after horizontal split: 3
[Style Engine] Found 3 VIEW_3D areas now
[Style Engine] Converting bottom area (height: [X]) to text editor
[Style Engine] ✓ Text editor configured (bottom)
[Style Engine] ✓ Workspace layout complete: Modeling | Camera + Prompt
```

**Problem indicators:**
- ❌ "WARNING: Horizontal split did not create new area"
- ❌ "Could not split for text editor: [error]"
- ❌ "WARNING: Bottom area is [TYPE], not TEXT_EDITOR"

---

## 🐛 Common Issues & Solutions

### Issue 1: Window Too Small
**Symptom**: Second split doesn't happen
**Cause**: Blender won't split if resulting areas are too small
**Solution**: 
- Resize Blender window to at least 1920x1080
- Or manually split: right-click area corner → Split Area

### Issue 2: Viewport Split Disabled
**Symptom**: Nothing happens at all
**Cause**: Feature disabled in preferences
**Solution**:
- Preferences → Add-ons → Style Engine
- Enable "Enable Viewport Split"
- Try again

### Issue 3: Blender Version < 4.2
**Symptom**: Errors about `temp_override`
**Cause**: Old Blender API
**Solution**: Update to Blender 4.2 or newer

### Issue 4: Screen Layout Locked
**Symptom**: Areas won't split
**Cause**: Workspace or screen is locked
**Solution**: 
- Check if there's a lock icon anywhere
- Try in a fresh workspace
- Or manually create layout

---

## 🛠️ Manual Layout Setup

If automatic setup doesn't work, create layout manually:

### Step 1: First Split (Vertical)
1. Hover over top-right corner of 3D viewport
2. Cursor changes to crosshair/plus
3. Drag LEFT to split vertically
4. Create left (large) and right (small) areas

### Step 2: Configure Camera View
1. In the RIGHT area, press Numpad 0 (camera view)
2. Press N → View → Lock Camera to View (check ON)

### Step 3: Second Split (Horizontal)
1. Hover over top-right corner of the RIGHT area
2. Drag DOWN to split horizontally
3. Create top (larger) and bottom (smaller) areas

### Step 4: Convert Bottom to Text Editor
1. In BOTTOM-RIGHT area, click the editor type icon (top-left)
2. Select "Text Editor"
3. In Text Editor, select dropdown → "STYLEENGINE_Prompt"

### Final Layout:
```
┌─────────────────┬─────────┐
│                 │ CAMERA  │
│   MODELING      │  (3D)   │
│   (3D View)     ├─────────┤
│                 │  TEXT   │
│                 │ EDITOR  │
└─────────────────┴─────────┘
```

---

## 📝 What to Report

If the issue persists, please report:

1. **Blender Version**: Help → About Blender → [version]
2. **OS**: Windows / macOS / Linux + version
3. **Window Size**: [width] x [height] pixels
4. **Console Output**: Copy all "[Style Engine]" messages
5. **Debug Mode**: Was it enabled? (yes/no)
6. **Screen Layout**: Screenshot of the result

---

## 🔬 Advanced Debugging

### Check Area Count
In Blender's Python Console:
```python
import bpy
areas = list(bpy.context.screen.areas)
print(f"Total areas: {len(areas)}")
for i, area in enumerate(areas):
    print(f"  Area {i}: {area.type} - {area.width}x{area.height}")
```

**Expected after setup:**
- Total areas: 3
- Area 0: VIEW_3D (large, left side)
- Area 1: VIEW_3D (smaller, top-right, camera view)
- Area 2: TEXT_EDITOR (small, bottom-right)

### Test Split Manually
In Blender's Python Console:
```python
import bpy

# Find 3D viewport
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        override = {'area': area, 'region': area.regions[-1]}
        with bpy.context.temp_override(**override):
            result = bpy.ops.screen.area_split(direction='VERTICAL', factor=0.75)
            print(f"Split result: {result}")
        break
```

If this prints `{'CANCELLED'}`, the split failed (window too small or locked).

---

## 📦 Updated Package

**New version timestamp**: `[Updated: 2025-11-04 21:45]`

Check if you have the latest version:
1. Look at the default prompt in the panel
2. Should show "21:45" (not "21:25" or older)
3. If older, reinstall the addon and restart Blender

---

## ✅ Success Checklist

After setup, you should have:
- [ ] 3 areas total in the window
- [ ] Left area: Large 3D viewport (modeling)
- [ ] Top-right area: 3D viewport in camera view (locked)
- [ ] Bottom-right area: Text editor showing STYLEENGINE_Prompt
- [ ] Console shows: "✓ Workspace layout complete"

---

## 💡 Workaround: Use Default Layout + Manual Text Editor

If splits keep failing:
1. Use the OLD layout (just left modeling + right camera)
2. Manually open Text Editor in another window/tab
3. Select STYLEENGINE_Prompt text block
4. Prompt will still auto-sync on generation!

You don't NEED the 3-area layout for the addon to work, it's just more convenient.

---

**Need help?** Enable Debug Mode and check console output first!

