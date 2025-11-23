# Project Texture - Archival Materials & Images
**Date:** November 21, 2025  
**Feature:** Create unique archival materials and images for each projection  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Overview

When projecting AI textures onto objects, the system now creates **unique archival copies** of both the material and the image. This ensures that projected textures remain frozen in time and don't update when new AI images are generated.

---

## 🔄 The Problem (Before)

### Old Behavior:
```
Generate AI Image → current_ai.png
                    ↓
Project on Object → Uses current_ai.png directly
                    ↓
Generate NEW Image → current_ai.png updates
                    ↓
❌ ALL projected objects update with new image!
```

**Issue:** Objects that were projected earlier would change their texture when a new AI image was generated, because they all referenced the same `current_ai.png` file.

---

## ✅ The Solution (After)

### New Behavior:
```
Generate AI Image → current_ai.png
                    ↓
Project on Object → Duplicate current_ai.png → iteration_001.png
                    Create new material → iteration_001
                    Assign to selected objects
                    ↓
Generate NEW Image → current_ai.png updates
                    ↓
✅ Previously projected objects keep iteration_001.png!
```

**Result:** Each projection creates a unique, frozen snapshot that never changes.

---

## 🎨 Implementation Details

### Automatic Iteration Numbering

The system automatically finds the next available iteration number:

```python
iteration_num = 0
while f"iteration_{iteration_num:03d}" in bpy.data.materials:
    iteration_num += 1

iteration_name = f"iteration_{iteration_num:03d}"
# Results in: iteration_000, iteration_001, iteration_002, etc.
```

### Image Duplication

```python
# Duplicate the current_ai.png image
img_copy = img.copy()
img_copy.name = f"{iteration_name}.png"  # e.g., "iteration_001.png"

# Pack the image into the .blend file
if not img_copy.packed_file:
    img_copy.pack()
```

**Benefits:**
- ✅ Image is embedded in .blend file (no external dependencies)
- ✅ Original `current_ai.png` remains untouched
- ✅ Each iteration has its own independent image data

### Material Creation

```python
# Create unique material for this iteration
mat = bpy.data.materials.new(name=iteration_name)  # e.g., "iteration_001"
mat.use_nodes = True

# Setup shader nodes
tex_node = nodes.new(type='ShaderNodeTexImage')
tex_node.image = img_copy  # Use the duplicated image

# Connect to Principled BSDF → Material Output
```

**Material Structure:**
```
iteration_001.png → Image Texture Node → Principled BSDF → Material Output
```

---

## 📊 Naming Convention

### Materials:
- `iteration_000` - First projection
- `iteration_001` - Second projection
- `iteration_002` - Third projection
- ... and so on

### Images:
- `iteration_000.png` - First projection image
- `iteration_001.png` - Second projection image
- `iteration_002.png` - Third projection image
- ... and so on

### Objects:
- Objects keep their original names
- Each object gets assigned the iteration material
- Multiple objects can share the same iteration material

---

## 🎬 Workflow Example

### Scenario: Creating Multiple Iterations

**Step 1: First Projection**
```
1. Generate AI image → current_ai.png created
2. Select Cube
3. Project on Object
   → iteration_000 material created
   → iteration_000.png image created
   → Cube gets iteration_000 material
```

**Step 2: Second Projection**
```
4. Generate NEW AI image → current_ai.png updates
5. Select Sphere
6. Project on Object
   → iteration_001 material created
   → iteration_001.png image created
   → Sphere gets iteration_001 material
   → Cube STILL has iteration_000 (unchanged!)
```

**Step 3: Third Projection**
```
7. Generate ANOTHER AI image → current_ai.png updates
8. Select Monkey
9. Project on Object
   → iteration_002 material created
   → iteration_002.png image created
   → Monkey gets iteration_002 material
   → Cube has iteration_000 (unchanged!)
   → Sphere has iteration_001 (unchanged!)
```

---

## 🔍 Technical Details

### Code Location
**File:** `scripts/addons/styleengine/ui_panel.py`  
**Operator:** `WM_OT_ProjectTexture`  
**Lines:** ~1025-1070

### Key Changes:

#### 1. Find Next Iteration Number
```python
iteration_num = 0
while f"iteration_{iteration_num:03d}" in bpy.data.materials:
    iteration_num += 1

iteration_name = f"iteration_{iteration_num:03d}"
```

#### 2. Duplicate Image
```python
img_copy = img.copy()
img_copy.name = f"{iteration_name}.png"

if not img_copy.packed_file:
    img_copy.pack()

print(f"[Style Engine] 📸 Created archival image: {img_copy.name}")
```

#### 3. Create Unique Material
```python
mat = bpy.data.materials.new(name=iteration_name)
mat.use_nodes = True

# ... setup nodes ...

tex_node.image = img_copy  # Use duplicated image

print(f"[Style Engine] 🎨 Created archival material: {mat.name}")
```

#### 4. Updated Success Message
```python
self.report({'INFO'}, f"Projected {iteration_name} onto {projected_count} objects")
print(f"[Style Engine] 🎨 Projected {iteration_name} onto {projected_count} objects")
```

---

## 🎯 Benefits

### For Artists:
- ✅ **Frozen Textures** - Projected textures never change
- ✅ **Multiple Iterations** - Build up complex scenes with different AI generations
- ✅ **No Confusion** - Clear naming shows which iteration each object uses
- ✅ **Embedded Data** - Images packed into .blend file (portable)

### For Workflow:
- ✅ **Non-Destructive** - Original `current_ai.png` always available
- ✅ **Iterative Design** - Layer multiple AI generations in one scene
- ✅ **Version Control** - Each iteration is numbered and tracked
- ✅ **Collaboration** - Share .blend files with all textures embedded

---

## 📦 Data Management

### What Gets Created:

**Per Projection:**
- 1 Material (e.g., `iteration_001`)
- 1 Image (e.g., `iteration_001.png`)
- N Objects assigned to that material

**Storage:**
- Images are packed into .blend file
- No external file dependencies
- All data travels with the .blend file

### Cleanup:

If you want to remove old iterations:
1. **Outliner** → Filter by "Orphan Data"
2. Select unused materials/images
3. Delete or purge orphan data

---

## 🧪 Testing Checklist

- [x] First projection creates `iteration_000`
- [x] Second projection creates `iteration_001`
- [x] Numbering increments correctly
- [x] Images are duplicated (not referenced)
- [x] Images are packed into .blend file
- [x] Materials are unique per iteration
- [x] Old projections don't update with new AI images
- [x] Multiple objects can share same iteration material
- [x] Console shows archival image/material creation
- [x] Success message shows iteration name

---

## 🚀 Future Enhancements

### Potential Features:
- Iteration browser/manager UI
- Preview thumbnails of each iteration
- Iteration metadata (timestamp, prompt, settings)
- Export iterations as image sequence
- Iteration comparison view
- Batch apply iteration to multiple objects

---

## 📌 Summary

The texture projection system now creates **archival copies** of both materials and images for each projection. This ensures that once a texture is projected onto an object, it remains frozen in time and won't change when new AI images are generated.

**Key Features:**
- ✅ Unique material per projection (`iteration_000`, `iteration_001`, etc.)
- ✅ Unique image per projection (`iteration_000.png`, `iteration_001.png`, etc.)
- ✅ Automatic numbering system
- ✅ Images packed into .blend file
- ✅ Non-destructive workflow
- ✅ Clear console logging

**Result:** Artists can build complex scenes with multiple AI generations, knowing that each projected texture will remain exactly as it was at the moment of projection! 🎨✨

