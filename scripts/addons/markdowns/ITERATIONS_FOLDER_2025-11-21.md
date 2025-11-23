# Iterations Folder - Texture Backup System
**Date:** November 21, 2025  
**Feature:** External backup of projected texture iterations  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Purpose

The `iterations/` folder stores **external backups** of projected texture images. When you use "Project on Object", the texture is both:
1. **Packed into .blend file** (embedded in material)
2. **Saved to iterations folder** (external backup)

---

## 📁 Location

### Saved .blend:
```
MyProject.blend
MyProject_styleengine/
└── iterations/
    ├── iteration_000.png
    ├── iteration_001.png
    ├── iteration_002.png
    └── ...
```

### Unsaved .blend:
```
C:\Users\You\AppData\Local\Temp\blender_styleengine\
└── sessions\
    └── 20251121_143022_abc123\
        └── iterations\
            ├── iteration_000.png
            └── ...
```

---

## 🔄 Workflow

### When You Click "Project on Object":

1. **Material Created:**
   - Name: `iteration_000`, `iteration_001`, etc.
   - Image: Duplicated from `current_ai.png`
   - Packed into .blend file

2. **External Backup Saved:**
   - ✅ **NEW:** Saved to `iterations/iteration_000.png`
   - Same image as packed version
   - Available outside .blend file

3. **3D Snapshot Created** (if enabled):
   - Object: `Iteration_000` in "Iterations" collection
   - Has the `iteration_000` material applied
   - Hidden from viewport

---

## 💡 Why Both Packed + External?

### Packed (in .blend):
- ✅ Always available when opening .blend
- ✅ No broken links
- ✅ Self-contained project
- ❌ Can't access without opening .blend
- ❌ Increases .blend file size

### External (iterations folder):
- ✅ Can use in other software
- ✅ Easy to backup separately
- ✅ Can preview without opening .blend
- ✅ Recoverable if .blend corrupts
- ❌ Separate files to manage

**Solution:** Do both! Best of both worlds.

---

## 🎨 Use Cases

### 1. **Recovery**
If .blend file corrupts:
```
1. Open new .blend
2. Import textures from iterations/
3. Recreate materials
4. Continue working
```

### 2. **External Use**
Use textures in other software:
```
1. Navigate to MyProject_styleengine/iterations/
2. Copy iteration_002.png
3. Use in Photoshop, Substance, Unity, etc.
```

### 3. **Comparison**
Compare different iterations:
```
1. Open iterations folder
2. View all textures side-by-side
3. Choose best version
4. Load corresponding material in Blender
```

### 4. **Archival**
Long-term project archival:
```
1. Backup MyProject_styleengine/ folder
2. All textures preserved externally
3. Can rebuild project if needed
```

### 5. **Sharing**
Share textures with team:
```
1. Send iterations/ folder
2. Team can preview without Blender
3. Import into their projects
```

---

## 🔧 Technical Details

### Saving Process

When "Project on Object" is clicked:

```python
# 1. Duplicate current_ai.png
img_copy = img.copy()
img_copy.name = f"{iteration_name}.png"

# 2. Pack into .blend
img_copy.pack()

# 3. Save to external iterations folder
save_iteration_texture(context, img_path, iteration_name)
```

### Save Location Logic

```python
if bpy.data.is_saved:
    # Save to project library
    dest = MyProject_styleengine/iterations/iteration_000.png
else:
    # Save to session temp
    dest = .../sessions/SESSION_ID/iterations/iteration_000.png
    # Will migrate when .blend is saved
```

### Migration

When you save unsaved .blend:
```
1. Session iterations/ folder detected
2. All iteration_*.png files copied
3. Moved to MyProject_styleengine/iterations/
4. Available in project library
```

---

## 📊 File Naming

### Format:
```
iteration_XXX.png

Examples:
- iteration_000.png  (first projection)
- iteration_001.png  (second projection)
- iteration_002.png  (third projection)
```

### Numbering:
- Sequential: 000, 001, 002, etc.
- Matches material names
- Matches 3D snapshot names (Iteration_000)

---

## 🔍 Finding Your Textures

### Method 1: File Explorer
```
1. Navigate to .blend file location
2. Open MyProject_styleengine/ folder
3. Open iterations/ subfolder
4. All textures listed
```

### Method 2: Blender Console
```
Look for:
[Style Engine] 💾 Saved texture to: iteration_001.png
```

### Method 3: Blender Outliner
```
1. Expand "Iterations" collection
2. Select Iteration_001 object
3. Check material: iteration_001
4. Image is in iterations/iteration_001.png
```

---

## 🎯 Relationship to Other Systems

### vs. generations/
- **generations/**: All AI-generated images (timestamped)
- **iterations/**: Projected texture snapshots (numbered)

### vs. Packed Images
- **Packed**: Embedded in .blend, always available
- **iterations/**: External backup, portable

### vs. 3D Snapshots
- **3D Snapshots**: Geometry in "Iterations" collection
- **iterations/**: Textures used by those snapshots

---

## 💾 Storage Considerations

### File Size:
- Each iteration: ~2-5MB (depends on resolution)
- 10 iterations: ~20-50MB
- 100 iterations: ~200-500MB

### Cleanup:
- Manual: Delete unwanted iteration_*.png files
- Automatic cleanup: Not implemented (future feature)
- Safe to delete: Won't break .blend (packed version remains)

---

## ⚠️ Important Notes

### ✅ DO:
- Keep iterations/ folder with your .blend
- Include in backups
- Use for external software
- Delete unwanted iterations manually

### ❌ DON'T:
- Rename iteration files (breaks numbering)
- Delete iterations/ folder if you need external access
- Worry if deleted (packed version still in .blend)

---

## 🚀 Future Enhancements

### Potential Features:
1. **Iteration Browser UI**
   - Preview all iterations
   - Load specific iteration to camera
   - Compare side-by-side

2. **Export Options**
   - Export as image sequence
   - Batch export to specific folder
   - Convert to other formats

3. **Metadata**
   - Track which generation created each iteration
   - Store projection settings
   - Link to 3D snapshots

4. **Auto-Cleanup**
   - Delete old iterations after N days
   - Keep only last N iterations
   - Compress old iterations

---

## 📌 Summary

The `iterations/` folder provides **external backup** of projected textures:

**Key Features:**
- ✅ Automatic saving on "Project on Object"
- ✅ External backup (outside .blend)
- ✅ Portable and shareable
- ✅ Recoverable if .blend corrupts
- ✅ Usable in other software
- ✅ Migrates with session data

**Result:** Robust, portable texture management with both embedded and external copies! 🎨✨

