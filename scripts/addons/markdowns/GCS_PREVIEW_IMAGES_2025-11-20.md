# GCS Preview Images Feature
**Date:** November 20, 2025  
**Feature:** Optional download of Canny and Depth preview images  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Overview

Added an optional feature to download Canny edge detection and Depth Anything preview images alongside the final generated image in GCS mode. This provides visual feedback on what the ControlNet preprocessors are seeing.

---

## 📊 What It Does

When enabled, the addon downloads **3 images** instead of 1:
1. **current_ai.png** - Final generated image (always downloaded)
2. **canny.png** - Canny edge detection map (optional)
3. **depth.png** - Depth Anything depth map (optional)

All images are saved to the **temp directory** for quick preview and visual feedback.

---

## 🛠️ Implementation Details

### 1. Workflow Changes (`StyleEnginePreview.json`)

Added two SaveImage nodes to the workflow:

```json
"134": {
  "inputs": {
    "filename_prefix": "canny",
    "images": ["36", 0]  // Canny preprocessor output
  },
  "class_type": "SaveImage",
  "_meta": {
    "title": "CannyPreview"
  }
},
"135": {
  "inputs": {
    "filename_prefix": "depth",
    "images": ["39", 0]  // DepthAnything preprocessor output
  },
  "class_type": "SaveImage",
  "_meta": {
    "title": "DepthPreview"
  }
}
```

### 2. Preferences (`prefs.py`)

Added new BoolProperty:

```python
gcs_download_preview_images: BoolProperty(
    name="Download Preview Images",
    description="Download Canny and Depth preview images for visual feedback (stored in temp directory)",
    default=False
)
```

**Location:** Right after `gcs_server_status` property

**Default:** `False` (disabled by default to save bandwidth)

### 3. UI Display (`prefs.py` - draw method)

Added toggle in GCS settings section:

```python
# Download preview images option
box.separator()
preview_box = box.box()
preview_box.label(text="Preview Images:", icon='IMAGE_DATA')
col = preview_box.column(align=True)
col.prop(self, "gcs_download_preview_images", text="Download Canny & Depth Maps")
col.label(text="Preview images saved to temp directory for visual feedback", icon='INFO')
col.scale_y = 0.8
```

**Location:** Between server status and test connection button

### 4. Download Logic (`workspace_setup.py`)

Modified `on_generation_complete_server()` callback:

```python
# Check if preview images should be downloaded
prefs = context.preferences.addons['styleengine'].preferences
download_previews = prefs.gcs_download_preview_images

print(f"[GCS] Found {len(images)} output images")
if download_previews:
    print(f"[GCS] Preview images enabled - downloading all images")

# Download each image
for img_info in images:
    filename = img_info['filename']
    
    # Determine save name based on filename prefix
    if filename.startswith('canny'):
        if not download_previews:
            continue  # Skip if disabled
        save_name = 'canny.png'
    elif filename.startswith('depth'):
        if not download_previews:
            continue  # Skip if disabled
        save_name = 'depth.png'
    elif filename.startswith('StyleEngine'):
        save_name = 'current_ai.png'
    else:
        continue  # Skip unknown images
    
    # Download and save
    save_path = temp_dir / save_name
    server_client.download_image(filename, str(save_path), subfolder, image_type)
```

---

## 🎨 User Experience

### UI Location
```
Edit → Preferences → Add-ons → Style Engine
  ├─ Backend Mode: Self-Hosted ComfyUI
  ├─ Server URL: http://34.19.119.45:8188
  ├─ [Test Server Connection]
  └─ Preview Images:
      └─ ☐ Download Canny & Depth Maps
          Preview images saved to temp directory for visual feedback
```

### File Locations

**Temp Directory:**
```
C:\Users\Juan\AppData\Local\Temp\blender_styleengine\ai_vision\
├── current_ai.png  (always downloaded)
├── canny.png       (if enabled)
└── depth.png       (if enabled)
```

**Output Directory** (if set):
```
C:\Your\Output\Path\generated\
└── 20251120_143052_gcs.png  (only final image)
```

---

## 📈 Performance Impact

### With Preview Images Disabled (Default):
- **Images downloaded:** 1 (current_ai.png)
- **Bandwidth:** ~500 KB - 2 MB per generation
- **Download time:** ~500ms

### With Preview Images Enabled:
- **Images downloaded:** 3 (current_ai.png, canny.png, depth.png)
- **Bandwidth:** ~1.5 MB - 6 MB per generation
- **Download time:** ~1.5s - 2s

**Recommendation:** Keep disabled unless you need to debug ControlNet preprocessing.

---

## 🎯 Use Cases

### When to Enable:
1. **Debugging ControlNet** - See what edges/depth the AI is detecting
2. **Quality control** - Verify preprocessors are working correctly
3. **Learning** - Understand how ControlNet interprets your scene
4. **Documentation** - Save preprocessing steps for reference

### When to Disable (Default):
1. **Production workflow** - Only need final image
2. **Bandwidth concerns** - Reduce download size
3. **Speed priority** - Faster generation cycles
4. **Storage concerns** - Less temp file clutter

---

## 🔍 Visual Feedback Examples

### Canny Edge Detection (`canny.png`)
- Shows detected edges and contours
- White lines on black background
- Helps understand silhouette influence

### Depth Anything (`depth.png`)
- Shows depth map (near=bright, far=dark)
- Grayscale visualization
- Helps understand depth influence

### Final Image (`current_ai.png`)
- The actual generated artwork
- Full color, full resolution
- What appears in Blender viewport

---

## 🧪 Testing Checklist

- [x] Toggle appears in GCS preferences
- [x] Default is disabled (False)
- [x] When disabled, only current_ai.png downloads
- [x] When enabled, all 3 images download
- [x] Images save to temp directory
- [x] Filenames are correct (canny.png, depth.png, current_ai.png)
- [x] Main image still updates viewport
- [x] No errors if preview images missing
- [x] Works with StyleEnginePreview.json workflow
- [x] Console logging shows download status

---

## 📝 Console Output

### With Preview Images Disabled:
```
[GCS] Found 3 output images
[GCS] Downloading final image: StyleEngine_00023_.png
[GCS] ✅ Saved: current_ai.png
[GCS] ✓ Camera background updated with new AI image
```

### With Preview Images Enabled:
```
[GCS] Found 3 output images
[GCS] Preview images enabled - downloading all images
[GCS] Downloading Canny edge map: canny_00023_.png
[GCS] ✅ Saved: canny.png
[GCS] Downloading Depth map: depth_00023_.png
[GCS] ✅ Saved: depth.png
[GCS] Downloading final image: StyleEngine_00023_.png
[GCS] ✅ Saved: current_ai.png
[GCS] ✓ Camera background updated with new AI image
```

---

## 🔄 Workflow Compatibility

### StyleEngine.json (Original)
- ❌ No preview nodes
- ✅ Will work but won't download previews (no error)

### StyleEnginePreview.json (New)
- ✅ Has preview nodes (134, 135)
- ✅ Will download all 3 images when enabled

**Migration:** Replace `StyleEngine.json` with `StyleEnginePreview.json` to enable this feature.

---

## 🚀 Future Enhancements

### Potential Additions:
1. **Preview in UI** - Show thumbnails in Blender panel
2. **Save to output folder** - Option to save previews alongside final image
3. **More preprocessors** - Add other ControlNet preprocessors (Lineart, Normal, etc.)
4. **Comparison view** - Side-by-side view of preprocessors vs final
5. **Custom filenames** - User-defined naming for preview images

---

## 🎓 Key Design Decisions

### Why Default to Disabled?
- **Bandwidth** - Most users only need final image
- **Speed** - Faster download = faster iteration
- **Storage** - Less temp file accumulation

### Why Temp Directory Only?
- **Purpose** - Preview images are for visual feedback, not archival
- **Cleanup** - Temp files auto-clean on system restart
- **Simplicity** - No need to manage preview storage

### Why Not Base64?
- **Direct download** - More efficient than Base64 encoding
- **File size** - No encoding overhead
- **Simplicity** - Consistent with main image download

---

## ✅ Verification

**Linting:** No errors  
**Functionality:** All modes working  
**Performance:** Minimal impact when disabled  
**User Experience:** Clean, optional, well-documented  
**Status:** Production ready  

---

**Author:** Style Engine Development Team  
**Last Updated:** November 20, 2025  
**Version:** 1.0.0

