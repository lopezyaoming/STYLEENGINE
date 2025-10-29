# IPAdapter Feature - Technical Analysis & Implementation Plan

**Date:** October 29, 2025  
**Status:** Planning Phase (Not Yet Implemented)

---

## 🎯 Feature Overview

### What is IPAdapter?
IPAdapter allows diffusion models to use a **reference image** as visual guidance, injecting its **style** or **identity** into the generation alongside the text prompt. This enables:
- **Style Transfer**: Apply artistic style from reference image
- **Composition**: Use reference for layout/structure
- **Strong Style Transfer**: Aggressive style application

### Use Cases
1. **Architectural Visualization**: Apply material/lighting style from reference photos
2. **Concept Art**: Match art direction from mood boards
3. **Character Consistency**: Maintain character appearance across generations
4. **Style Matching**: Apply specific artistic styles to 3D scenes

---

## 📊 Workflow Comparison Analysis

### Base Workflow (SDXLworkflow.json)
**Total Nodes:** 12  
**Model Flow:** Checkpoint → LoRA → KSampler

```
Node 4 (Checkpoint)
  ↓
Node 34 (LoRA) ─→ Node 3 (KSampler) → ... → Node 9 (Output)
```

### IPAdapter Workflow (IPAdapterworkflow.json)
**Total Nodes:** 20 (+8 new nodes)  
**Model Flow:** Checkpoint → LoRA → IPAdapter → KSampler

```
Node 43 (Load Reference Image)
  ↓
Node 44 (Resize to 1024x1024)
  ↓
Node 47 (Prep for CLIP)
  ↓
Node 48 (IPAdapter Encoder) ←─ Node 45 (IPAdapter Model)
  ↓                              Node 46 (CLIP Vision)
Node 49 (IPAdapter Embeds) ←─────┘
  ↓ (modified model)
Node 3 (KSampler) → ... → Node 9 (Output)
```

---

## 🔧 New Nodes Breakdown

### Node 43: Load Reference Image
```json
{
  "inputs": {
    "image": "Screenshot 2025-10-27 102902.jpg"
  },
  "class_type": "LoadImage",
  "_meta": {
    "title": "Load IPAdapter"
  }
}
```
**Purpose:** Load user's reference image  
**Variable:** Image file path (needs file picker in UI)

---

### Node 44: Resize Reference Image
```json
{
  "inputs": {
    "width": 1024,
    "height": 1024,
    "upscale_method": "nearest-exact",
    "keep_proportion": "stretch",
    "pad_color": "0, 0, 0",
    "crop_position": "center",
    "divisible_by": 2,
    "image": ["43", 0]
  },
  "class_type": "ImageResizeKJv2"
}
```
**Purpose:** Standardize reference image size  
**Fixed:** Always 1024x1024 (matches generation resolution)

---

### Node 45: IPAdapter Model Loader
```json
{
  "inputs": {
    "ipadapter_file": "ip-adapter-plus_sdxl_vit-h.bin"
  },
  "class_type": "IPAdapterModelLoader"
}
```
**Purpose:** Load IPAdapter weights  
**Fixed:** Uses SDXL IPAdapter model

---

### Node 46: CLIP Vision Loader
```json
{
  "inputs": {
    "clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
  },
  "class_type": "CLIPVisionLoader"
}
```
**Purpose:** Load CLIP vision encoder  
**Fixed:** Required for image encoding

---

### Node 47: Prep Image for CLIP Vision
```json
{
  "inputs": {
    "interpolation": "LANCZOS",
    "crop_position": "top",
    "sharpening": 0,
    "image": ["44", 0]
  },
  "class_type": "PrepImageForClipVision"
}
```
**Purpose:** Preprocess image for CLIP encoding  
**Fixed:** Standard preprocessing

---

### Node 48: IPAdapter Encoder
```json
{
  "inputs": {
    "weight": 1,
    "ipadapter": ["45", 0],
    "image": ["47", 0],
    "clip_vision": ["46", 0]
  },
  "class_type": "IPAdapterEncoder"
}
```
**Purpose:** Encode reference image into embeddings  
**Fixed:** Weight always 1 at encoding stage

---

### Node 49: IPAdapter Embeds
```json
{
  "inputs": {
    "weight": ["52", 0],              // ← User variable: IPStrength
    "weight_type": "style transfer",  // ← User variable: Type
    "start_at": 0,
    "end_at": 1,
    "embeds_scaling": "K+V",
    "model": ["34", 0],
    "ipadapter": ["45", 0],
    "pos_embed": ["48", 0],
    "neg_embed": ["48", 1],
    "clip_vision": ["46", 0]
  },
  "class_type": "IPAdapterEmbeds"
}
```
**Purpose:** Apply IPAdapter to model  
**User Variables:**
- `weight`: IPStrength (0.0-1.5)
- `weight_type`: Style mode (3 options)

---

### Node 52: IP Strength Primitive
```json
{
  "inputs": {
    "value": 0
  },
  "class_type": "PrimitiveFloat",
  "_meta": {
    "title": "IPStrength"
  }
}
```
**Purpose:** Control IPAdapter influence  
**User Variable:** Float slider 0.0-1.5  
**Default:** 0 (disabled)

---

## 🎨 UI Design Plan

### Location in Panel
```
┌─ Style Engine Panel ────────────────┐
│                                      │
│  [Workspace Setup]                   │
│                                      │
│  ┌─ Generation ───────────────────┐ │
│  │ Prompt: [____________]          │ │
│  │ Depth: [====|====] 0.5          │ │
│  │ Silhouette: [====|====] 0.5     │ │
│  │ Steps: [====|====] 15            │ │
│  └─────────────────────────────────┘ │
│                                      │
│  ┌─▼ IPAdapter (Optional) ─────────┐ │  ← NEW: Collapsible
│  │ ☐ Enable IPAdapter              │ │
│  │                                  │ │
│  │ Reference Image:                 │ │
│  │ [Browse...] [Clear]              │ │
│  │ 📷 style_reference.jpg           │ │
│  │                                  │ │
│  │ Mode: [Style Transfer ▼]         │ │
│  │   • Style Transfer               │ │
│  │   • Composition                  │ │
│  │   • Strong Style Transfer        │ │
│  │                                  │ │
│  │ Strength: [====|====] 0.75       │ │
│  │ (0.0 = Off, 1.5 = Max)           │ │
│  └─────────────────────────────────┘ │
│                                      │
│  [Generate AI]                       │
│                                      │
│  ┌─ Groups ───────────────────────┐ │
│  │ ...                             │ │
│  └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

### UI Controls Specification

#### 1. Enable Checkbox
```python
ipadapter_enabled: BoolProperty(
    name="Enable IPAdapter",
    description="Use reference image for style/composition guidance",
    default=False
)
```

#### 2. Reference Image Path
```python
ipadapter_reference_image: StringProperty(
    name="Reference Image",
    description="Path to reference image for IPAdapter",
    default="",
    subtype='FILE_PATH'
)
```

**UI Elements:**
- File browser button (`.png`, `.jpg`, `.jpeg` filters)
- Display current filename when set
- "Clear" button to remove reference
- Visual preview thumbnail (optional enhancement)

#### 3. Weight Type Dropdown
```python
ipadapter_weight_type: EnumProperty(
    name="Mode",
    description="IPAdapter application mode",
    items=[
        ('style transfer', "Style Transfer", 
         "Apply artistic style from reference image"),
        ('composition', "Composition", 
         "Use reference for layout and structure"),
        ('strong style transfer', "Strong Style Transfer", 
         "Aggressive style application")
    ],
    default='style transfer'
)
```

#### 4. Strength Slider
```python
ipadapter_strength: FloatProperty(
    name="Strength",
    description="IPAdapter influence (0.0=off, 1.5=maximum)",
    default=0.75,
    min=0.0,
    max=1.5,
    step=0.05,
    precision=2
)
```

---

## 📝 session.json Schema Extension

### New Section: `ipadapter`
```json
{
  "global_prompt": "...",
  "resolution": 1024,
  "depth_influence": 0.5,
  "silhouette_influence": 0.5,
  "steps": 15,
  
  "ipadapter": {
    "enabled": false,
    "reference_image": "",
    "weight_type": "style transfer",
    "strength": 0.75
  },
  
  "flags": {
    "auto_generate": false
  }
}
```

### Field Descriptions

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `enabled` | bool | - | `false` | Enable/disable IPAdapter |
| `reference_image` | string | - | `""` | Absolute path to reference image |
| `weight_type` | enum | 3 options | `"style transfer"` | Application mode |
| `strength` | float | 0.0-1.5 | `0.75` | Influence strength |

---

## 🔄 Workflow Injection Logic

### Decision Tree
```
Is IPAdapter enabled?
  ↓ NO
  Use base workflow (SDXLworkflow.json)
  Inject only: prompt, combined, depth/silhouette, steps
  
  ↓ YES
  Use IPAdapter workflow (IPAdapterworkflow.json)
  Inject: 
    - prompt (Node 25)
    - combined (Node 15)
    - depth/silhouette (Nodes 40, 41)
    - steps (Node 42)
    - reference_image (Node 43) ← NEW
    - weight_type (Node 49) ← NEW
    - strength (Node 52) ← NEW
```

### Injection Mapping

#### Base Injections (Always)
```python
base_overrides = {
    "25": {"inputs": {"value": prompt}},
    "15": {"inputs": {"image": "combined0001.png"}},
    "40": {"inputs": {"value": silhouette_influence}},
    "41": {"inputs": {"value": depth_influence}},
    "42": {"inputs": {"value": steps}}
}
```

#### IPAdapter Injections (When enabled)
```python
ipadapter_overrides = {
    "43": {  # Load reference image
        "inputs": {
            "image": reference_image_filename  # Just filename, not full path
        }
    },
    "49": {  # IPAdapter Embeds
        "inputs": {
            "weight_type": weight_type  # "style transfer", etc.
        }
    },
    "52": {  # IPStrength
        "inputs": {
            "value": strength  # 0.0-1.5
        }
    }
}
```

---

## 🚨 Implementation Challenges

### Challenge 1: Image Path Handling
**Problem:** Node 43 expects just a filename, but user provides full path

**Solution Options:**
1. **Copy to ComfyUI input folder** (Recommended for local)
   ```python
   # Copy reference image to ComfyUI/input/
   shutil.copy(user_path, comfyui_input_folder)
   # Inject just filename
   overrides["43"]["inputs"]["image"] = os.path.basename(user_path)
   ```

2. **For RunComfy Cloud: Base64 encode**
   ```python
   # Encode image to Base64
   with open(user_path, 'rb') as f:
       img_b64 = base64.b64encode(f.read()).decode('utf-8')
       img_uri = f"data:image/jpeg;base64,{img_b64}"
   
   # Inject data URI
   overrides["43"]["inputs"]["image"] = img_uri
   ```

---

### Challenge 2: File Size Limits
**Problem:** Reference images can be very large

**Solution:**
1. **Validate file size in UI**
   ```python
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   
   if os.path.getsize(filepath) > MAX_FILE_SIZE:
       self.report({'ERROR'}, "Image too large (max 10MB)")
   ```

2. **Resize before upload (for cloud)**
   ```python
   from PIL import Image
   
   img = Image.open(filepath)
   if img.width > 2048 or img.height > 2048:
       img.thumbnail((2048, 2048))
       img.save(temp_path, quality=85)
   ```

---

### Challenge 3: Model File Requirements
**Problem:** IPAdapter requires additional model files in ComfyUI

**Required Files:**
1. `ip-adapter-plus_sdxl_vit-h.bin` (~3.7GB)
2. `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` (~1.7GB)

**Solution:**
1. **Detection:** Check if files exist before enabling feature
   ```python
   def check_ipadapter_available():
       models_path = Path(comfyui_path) / "models" / "ipadapter"
       clip_path = Path(comfyui_path) / "models" / "clip_vision"
       
       ipadapter_exists = (models_path / "ip-adapter-plus_sdxl_vit-h.bin").exists()
       clip_exists = (clip_path / "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors").exists()
       
       return ipadapter_exists and clip_exists
   ```

2. **UI Feedback:** Show warning if not available
   ```python
   if not check_ipadapter_available():
       box.label(text="⚠ IPAdapter models not found", icon='ERROR')
       box.label(text="Download required files to enable")
   ```

---

### Challenge 4: Workflow Selection
**Problem:** Need to dynamically choose between base and IPAdapter workflows

**Solution:**
```python
def get_active_workflow(session_data):
    """Select appropriate workflow based on settings"""
    
    if session_data.get('ipadapter', {}).get('enabled', False):
        # Check if reference image is set
        ref_img = session_data['ipadapter'].get('reference_image', '')
        if ref_img and os.path.exists(ref_img):
            return "IPAdapterworkflow.json"
        else:
            print("[Warning] IPAdapter enabled but no valid reference image")
            return "SDXLworkflow.json"
    else:
        return "SDXLworkflow.json"
```

---

## 📋 Implementation Checklist

### Phase 1: UI Components
- [ ] Add `ipadapter_enabled` BoolProperty to scene props
- [ ] Add `ipadapter_reference_image` StringProperty with FILE_PATH subtype
- [ ] Add `ipadapter_weight_type` EnumProperty with 3 options
- [ ] Add `ipadapter_strength` FloatProperty (0.0-1.5)
- [ ] Create collapsible box in UI panel (above "Groups")
- [ ] Add file browser operator for reference image
- [ ] Add "Clear" button to remove reference
- [ ] Display current filename when set
- [ ] Show model availability warning if needed

### Phase 2: Session Data
- [ ] Update `write_session_json` to include IPAdapter section
- [ ] Add validation for reference image path
- [ ] Ensure default values are set correctly
- [ ] Update JSON schema documentation

### Phase 3: Workflow Logic (Local ComfyUI)
- [ ] Create `get_active_workflow()` function
- [ ] Implement reference image copy to ComfyUI input folder
- [ ] Create IPAdapter injection overrides
- [ ] Test workflow switching
- [ ] Handle missing model files gracefully

### Phase 4: Cloud Compatibility (RunComfy)
- [ ] Implement Base64 encoding for reference images
- [ ] Add file size validation (<5MB for cloud)
- [ ] Test IPAdapter workflow on RunComfy
- [ ] Update cloud deployment to include IPAdapter models
- [ ] Document cloud-specific limitations

### Phase 5: Testing
- [ ] Test with various image formats (PNG, JPG, JPEG)
- [ ] Test with different image sizes
- [ ] Test all three weight_type modes
- [ ] Test strength range (0.0, 0.75, 1.5)
- [ ] Test workflow switching (enable/disable)
- [ ] Test error cases (missing file, invalid format)

### Phase 6: Documentation
- [ ] Update user guide with IPAdapter section
- [ ] Document required model files
- [ ] Provide example reference images
- [ ] Create tutorial video/screenshots
- [ ] Add to troubleshooting guide

---

## 💡 Usage Examples

### Example 1: Architectural Style Transfer
```
Scene: Modern building 3D model
Reference: Photo of brutalist concrete architecture
Mode: Style Transfer
Strength: 1.0
Result: Building rendered in brutalist style
```

### Example 2: Lighting/Mood Composition
```
Scene: Interior space wireframe
Reference: Cinematic still with dramatic lighting
Mode: Composition
Strength: 0.6
Result: Interior with similar lighting setup
```

### Example 3: Material Application
```
Scene: Product visualization
Reference: Photo of desired material finish
Mode: Strong Style Transfer
Strength: 1.2
Result: Product with material from reference
```

---

## 🔮 Future Enhancements

### v1.1: Advanced Features
- [ ] Multiple reference images (weighted blend)
- [ ] Region-specific IPAdapter (masked application)
- [ ] Reference image library/presets
- [ ] Thumbnail preview of reference in UI
- [ ] Drag-and-drop reference image support

### v1.2: Optimization
- [ ] Automatic image preprocessing
- [ ] Smart strength recommendations
- [ ] Reference image caching
- [ ] Batch processing with different references

---

## 📊 Performance Impact

### Memory Requirements
- **Additional VRAM:** ~2GB (IPAdapter + CLIP Vision models)
- **Generation Time:** +5-10 seconds (encoding overhead)
- **Storage:** ~5.4GB (model files)

### Recommended Hardware
- **Minimum:** 12GB VRAM GPU (for SDXL + IPAdapter)
- **Recommended:** 16GB+ VRAM GPU
- **Cloud:** Use AMPERE_48 or higher tier

---

## 🎓 Technical References

### Model Information
- **IPAdapter Paper:** https://arxiv.org/abs/2308.06721
- **CLIP Vision:** https://github.com/openai/CLIP
- **ComfyUI IPAdapter:** https://github.com/cubiq/ComfyUI_IPAdapter_plus

### Node Documentation
- `IPAdapterModelLoader`: Loads .bin IPAdapter weights
- `CLIPVisionLoader`: Loads CLIP vision encoder
- `IPAdapterEncoder`: Encodes image to embeddings
- `IPAdapterEmbeds`: Applies embeddings to diffusion model

---

**Status:** ✅ Planning Complete - Ready for Implementation  
**Next Step:** Await implementation approval before coding

---

## 📝 Notes for Implementation

1. **Priority:** Implement local version first, then adapt for cloud
2. **Testing:** Start with small reference images (<1MB) for quick testing
3. **User Education:** Include clear examples of each weight_type in docs
4. **Error Handling:** Graceful degradation if IPAdapter unavailable
5. **Performance:** Consider adding "IPAdapter Disabled" option in preferences for users without sufficient VRAM

**Implementation will begin after approval.**

