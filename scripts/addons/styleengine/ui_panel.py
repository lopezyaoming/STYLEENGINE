# ================================================================
#    Style Engine UI Panel. Blender Python Script
# ================================================================

import bpy
import bpy.utils.previews
import shutil
from pathlib import Path
from . import utils
from . import workspace_setup

# Global preview collection for reference image thumbnails
# This persists across draw calls to avoid loading images repeatedly
preview_collections = {}

# Global cache for LoRa list to avoid repeated API calls
_lora_cache = {
    'items': [],
    'timestamp': 0,
    'cache_duration': 300  # 5 minutes
}


def _load_lora_ignore_list():
    """
    Load LoRa ignore list from loras/ignore.txt.
    Returns a set of patterns to exclude from dropdown.
    Supports both full paths and filenames.
    """
    from pathlib import Path
    
    try:
        addon_dir = Path(__file__).parent
        ignore_file = addon_dir / "loras" / "ignore.txt"
        
        print(f"[Style Engine] Looking for ignore list at: {ignore_file}")
        
        if not ignore_file.exists():
            print(f"[Style Engine] ignore.txt not found, no LoRAs will be filtered")
            return set()
        
        ignored = set()
        with open(ignore_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    # Add both the full path AND just the filename
                    # This handles both "file.safetensors" and "LoRAs/subfolder/file.safetensors"
                    ignored.add(line)  # Full path
                    filename = line.split('/')[-1]
                    ignored.add(filename)  # Just filename
        
        if ignored:
            print(f"[Style Engine] Loaded {len(ignored)} ignore patterns from ignore.txt")
        else:
            print(f"[Style Engine] ignore.txt is empty, no LoRAs filtered")
        
        return ignored
        
    except Exception as e:
        print(f"[Style Engine] ⚠️ Error loading ignore.txt: {e}")
        import traceback
        traceback.print_exc()
        return set()


def get_lora_items(self, context):
    """
    Dynamic callback to fetch available LoRa models from ComfyUI server.
    Caches results for 5 minutes to avoid excessive API calls.
    Filters out LoRAs listed in loras/ignore.txt.
    """
    import time
    from . import runcomfy_deployment
    
    # Check cache validity
    current_time = time.time()
    cache_age = current_time - _lora_cache['timestamp']
    
    # Default fallback items
    default_items = [
        ('NONE', "None", "No LoRa"),
        ('xl_more_art-full_v1.safetensors', "More Art Full", "Default LoRa"),
    ]
    
    # Return cached if valid
    if _lora_cache['items'] and cache_age < _lora_cache['cache_duration']:
        return _lora_cache['items']
    
    # Load ignore list
    ignored_loras = _load_lora_ignore_list()
    
    # Check if in GCS mode (self-hosted ComfyUI)
    try:
        prefs = context.preferences.addons['styleengine'].preferences
        
        if hasattr(prefs, 'api_backend') and prefs.api_backend == 'GCS':
            # Try to fetch from server
            try:
                server_client = runcomfy_deployment.get_server_client()
                
                # Fetch /object_info from ComfyUI server
                print("[Style Engine] Fetching LoRa list from ComfyUI server...")
                object_info = server_client._request('GET', '/object_info', timeout=5)
                
                if 'LoraLoader' in object_info:
                    lora_loader = object_info['LoraLoader']
                    
                    # Extract lora_name options: input.required.lora_name[0]
                    if 'input' in lora_loader and 'required' in lora_loader['input']:
                        lora_name_input = lora_loader['input']['required'].get('lora_name')
                        
                        if lora_name_input and isinstance(lora_name_input, list) and len(lora_name_input) > 0:
                            lora_list = lora_name_input[0]
                            
                            if isinstance(lora_list, list) and lora_list:
                                # Build items from server response
                                items = [('NONE', "None", "No LoRa")]
                                filtered_count = 0
                                
                                for lora_file in lora_list:
                                    # Skip if in ignore list
                                    if lora_file in ignored_loras:
                                        filtered_count += 1
                                        print(f"[Style Engine]   ✗ Filtered: {lora_file}")
                                        continue
                                    
                                    # Create readable display name
                                    display_name = lora_file.replace('.safetensors', '').replace('_', ' ').replace('-', ' ')
                                    display_name = ' '.join(word.capitalize() for word in display_name.split())
                                    
                                    # Truncate long names
                                    if len(display_name) > 35:
                                        display_name = display_name[:32] + "..."
                                    
                                    items.append((
                                        lora_file,           # Value: exact filename
                                        display_name,        # Display: readable name
                                        f"LoRa: {lora_file}" # Tooltip
                                    ))
                                
                                # Cache the results
                                _lora_cache['items'] = items
                                _lora_cache['timestamp'] = current_time
                                
                                print(f"[Style Engine] ✓ Found {len(items)-1} LoRa models on server ({filtered_count} filtered)")
                                return items
                
            except Exception as e:
                print(f"[Style Engine] ⚠️ Failed to fetch LoRas from server: {e}")
        
        # Fallback to default list
        print("[Style Engine] Using default LoRa list")
        return default_items
        
    except Exception as e:
        print(f"[Style Engine] Error in LoRa callback: {e}")
        return default_items

# ----------------------------------------------------------------
# 1. PROPERTY GROUP
# ----------------------------------------------------------------
class ObjectGroup(bpy.types.PropertyGroup):
    """Individual object group with keywords."""
    name: bpy.props.StringProperty(
        name="Group Name",
        default="NewGroup"
    )
    
    keywords: bpy.props.StringProperty(
        name="Keywords",
        default="",
        update=lambda self, context: context.scene.style_engine_props.update_session_json(context)
    )
    
    pass_index: bpy.props.IntProperty(
        name="Pass Index",
        default=12,
        min=1,
        max=32767
    )
    
    object_ids: bpy.props.StringProperty(
        name="Object IDs",
        description="Comma-separated list of object names",
        default=""
    )


class RefineFeatureItem(bpy.types.PropertyGroup):
    """A single feature string inside a subject_matter entry."""
    value: bpy.props.StringProperty(name="Feature", default="")


class RefineSubjectItem(bpy.types.PropertyGroup):
    """One subject_matter entry in the Refine Image JSON schema."""
    label: bpy.props.StringProperty(name="Label", default="object_1")
    style: bpy.props.StringProperty(name="Style", default="")
    scale: bpy.props.StringProperty(name="Scale", default="")
    color: bpy.props.StringProperty(name="Color", default="")
    material: bpy.props.StringProperty(name="Material", default="")
    features: bpy.props.CollectionProperty(type=RefineFeatureItem)
    features_index: bpy.props.IntProperty(default=0)
    show_expanded: bpy.props.BoolProperty(default=True)


class RefineTagItem(bpy.types.PropertyGroup):
    """A single thematic tag string."""
    value: bpy.props.StringProperty(name="Tag", default="")


def _build_refine_json(props):
    """Serialize the Refine Image form into a JSON string."""
    import json as _json
    subjects = []
    for subj in props.refine_subjects:
        features = [f.value for f in subj.features if f.value.strip()]
        subjects.append({
            "label": subj.label,
            "style": subj.style,
            "scale": subj.scale,
            "color": subj.color,
            "material": subj.material,
            "features": features,
        })
    tags = [t.value for t in props.refine_tags if t.value.strip()]
    data = {
        "metadata": {
            "filename": props.refine_meta_filename,
            "dimensions": props.refine_meta_dimensions,
            "aspect_ratio": props.refine_meta_aspect,
        },
        "visual_style": {
            "art_style": props.refine_style_art_style,
            "medium": props.refine_style_medium,
            "lighting_condition": props.refine_style_lighting,
        },
        "composition": {
            "perspective": props.refine_comp_perspective,
            "focal_point": props.refine_comp_focal_point,
        },
        "subject_matter": subjects,
        "thematic_tags": tags,
    }
    return _json.dumps(data, indent=2)


def _populate_refine_from_json(props, json_str):
    """Populate the Refine Image form fields from a JSON string."""
    import json as _json
    data = _json.loads(json_str)

    meta = data.get("metadata", {})
    props.refine_meta_filename = meta.get("filename", "")
    props.refine_meta_dimensions = meta.get("dimensions", "")
    props.refine_meta_aspect = meta.get("aspect_ratio", "")

    vs = data.get("visual_style", {})
    props.refine_style_art_style = vs.get("art_style", "")
    props.refine_style_medium = vs.get("medium", "")
    props.refine_style_lighting = vs.get("lighting_condition", "")

    comp = data.get("composition", {})
    props.refine_comp_perspective = comp.get("perspective", "")
    props.refine_comp_focal_point = comp.get("focal_point", "")

    props.refine_subjects.clear()
    for subj_data in data.get("subject_matter", []):
        subj = props.refine_subjects.add()
        subj.label = subj_data.get("label", "object")
        subj.style = subj_data.get("style", "")
        subj.scale = subj_data.get("scale", "")
        subj.color = subj_data.get("color", "")
        subj.material = subj_data.get("material", "")
        subj.show_expanded = False
        for feat_str in subj_data.get("features", []):
            feat = subj.features.add()
            feat.value = feat_str

    props.refine_tags.clear()
    for tag_str in data.get("thematic_tags", []):
        tag = props.refine_tags.add()
        tag.value = tag_str


def _get_gemini_instruction_items():
    """Scan templates/instructions_*.txt and return enum items for the dropdown."""
    from pathlib import Path
    items = [('NONE', "None", "No style instructions")]
    templates_dir = Path(__file__).parent / "templates"
    if templates_dir.exists():
        for f in sorted(templates_dir.glob("instructions_*.txt")):
            name = f.stem.replace("instructions_", "")
            items.append((name, name, f"Load {f.name}"))
    return items


def _on_ai_model_changed(self, context):
    """Update prompt text and camera when the user toggles between SDXL and Gemini."""
    from . import utils
    utils.set_prompt_text_for_model(self.ai_model)

    if self.ai_model == 'GEMINI':
        from . import workspace_setup
        workspace_setup.sync_ai_camera_from_scene(context)


def _on_gemini_instructions_changed(self, context):
    """Load the selected instruction file into STYLEENGINE_Instructions text block."""
    from pathlib import Path
    
    text_name = "STYLEENGINE_Instructions"
    
    if self.gemini_instructions == 'NONE':
        if text_name in bpy.data.texts:
            bpy.data.texts[text_name].clear()
        return
    
    templates_dir = Path(__file__).parent / "templates"
    instr_file = templates_dir / f"instructions_{self.gemini_instructions}.txt"
    
    if not instr_file.exists():
        print(f"[Gemini] Instruction file not found: {instr_file.name}")
        return
    
    content = instr_file.read_text(encoding='utf-8').strip()
    
    if text_name in bpy.data.texts:
        text_block = bpy.data.texts[text_name]
        text_block.clear()
        text_block.write(content)
    else:
        text_block = bpy.data.texts.new(text_name)
        text_block.write(content)
    
    print(f"[Gemini] Loaded instructions: {self.gemini_instructions} ({len(content)} chars)")


class StyleEngineProperties(bpy.types.PropertyGroup):
    """Stores all the properties for the Style Engine panel."""
    
    def update_session_json(self, context):
        """Update session.json when any property changes."""
        from . import workspace_setup
        workspace_setup.write_session_json(context)

    library_id: bpy.props.StringProperty(
        name="Session ID",
        description="Unique identifier for this workflow session",
        default="session-0001",
        update=update_session_json
    )
    
    output_path: bpy.props.StringProperty(
        name="Output Path",
        description="Local directory to store renders and outputs (leave empty to use default)",
        default="",
        subtype='DIR_PATH',
        update=update_session_json
    )
    
    lookup: bpy.props.StringProperty(
        name="Lookup",
        description="RAG system lookup query",
        default="",
        update=update_session_json
    )

    global_prompt: bpy.props.StringProperty(
        name="Global Prompt",
        description="Master prompt for AI generation",
        default="",  # Start blank - user writes their own prompt
        update=update_session_json
    )
    
    negative_prompt: bpy.props.StringProperty(
        name="Negative Prompt",
        description="Negative prompt extracted from Prompt Builder",
        default="",
        update=update_session_json
    )
    
    show_workspace_setup: bpy.props.BoolProperty(
        name="Show Workspace Setup",
        description="Expand or collapse the workspace setup section",
        default=False
    )
    
    show_image_generation: bpy.props.BoolProperty(
        name="Show Image Generation",
        description="Expand or collapse the image generation section",
        default=False
    )
    
    show_settings: bpy.props.BoolProperty(
        name="Show Settings",
        description="Expand or collapse the settings section",
        default=False
    )
    
    # N Panel category dropdowns
    show_file_settings: bpy.props.BoolProperty(
        name="Show File Settings",
        description="Expand or collapse the File section",
        default=False
    )
    
    # Unified seed for all AI workflows
    seed_value: bpy.props.IntProperty(
        name="Seed",
        description="Random seed for all AI workflows (image, PBR, 3D generation)",
        default=0,
        min=0,
        max=2147483647,
    )
    
    # AI Model selection
    ai_model: bpy.props.EnumProperty(
        name="AI Model",
        description="Select the AI model for image generation",
        items=[
            ('SDXL', "Stable Diffusion", "SDXL with ControlNet (default)"),
            ('GEMINI', "Gemini 3 Pro", "Gemini nano-banana image generation"),
        ],
        default='GEMINI',
        update=lambda self, context: _on_ai_model_changed(self, context)
    )
    
    # Gemini-specific settings
    gemini_temperature: bpy.props.FloatProperty(
        name="Temperature",
        description="Creativity level (0=faithful to input, 1=maximum creativity)",
        default=0.0,
        min=0.0,
        max=1.0,
        step=1,
    )
    gemini_image_size: bpy.props.EnumProperty(
        name="Image Size",
        description="Output image resolution for Gemini generation",
        items=[
            ('1K', "1K", "1024px"),
            ('2K', "2K", "2048px"),
            ('4K', "4K", "4096px"),
        ],
        default='1K'
    )
    gemini_alignment: bpy.props.BoolProperty(
        name="Alignment",
        description="Enable spatial alignment (uses viewport render as reference image)",
        default=True
    )
    sdxl_remove_bg: bpy.props.BoolProperty(
        name="Remove Background",
        description="Remove background from SDXL output image (uses InspyrenetRembg)",
        default=False
    )

    gemini_remove_bg: bpy.props.BoolProperty(
        name="Remove Background",
        description="Remove background from Gemini output image (uses InspyrenetRembg)",
        default=False
    )

    # Gemini reference images (5 slots, no weights)
    show_gemini_references: bpy.props.BoolProperty(
        name="Show Gemini References",
        description="Expand or collapse the Gemini Reference Images section",
        default=False
    )
    gemini_ref1_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Gemini Reference 1"
    )
    gemini_ref2_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Gemini Reference 2"
    )
    gemini_ref3_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Gemini Reference 3"
    )
    gemini_ref4_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Gemini Reference 4"
    )
    gemini_ref5_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Gemini Reference 5"
    )

    gemini_instructions: bpy.props.EnumProperty(
        name="Instructions",
        description="Style instructions to append to the prompt",
        items=lambda self, context: _get_gemini_instruction_items(),
        update=lambda self, context: _on_gemini_instructions_changed(self, context),
    )
    
    # Patch system state
    patch_mode_active: bpy.props.BoolProperty(
        name="Patch Mode",
        description="Toggle patch camera mode for fixing edge textures",
        default=False
    )
    
    show_view_settings: bpy.props.BoolProperty(
        name="Show View Settings",
        description="Expand or collapse the View section",
        default=False
    )
    
    show_visualization: bpy.props.BoolProperty(
        name="Show Visualization",
        description="Expand or collapse the Visualization section",
        default=False
    )
    
    show_text_generation: bpy.props.BoolProperty(
        name="Show Text Generation",
        description="Expand or collapse the Text Generation section",
        default=False
    )
    
    prompt_llm_profile: bpy.props.EnumProperty(
        name="Prompt LLM Profile",
        description="Which ComfyUI text/vision workflows to use for Refine Prompt and image description",
        items=[
            ('DEFAULT', "Default", "TextRefine, TextImage, TextViewport JSON workflows"),
            ('BLACKHAMSTER', "Blackhamster Agents", "AgentTextRefine and AgentImageRefine workflows"),
        ],
        default='DEFAULT',
        update=update_session_json,
    )
    
    show_image_generation_main: bpy.props.BoolProperty(
        name="Show Image Generation",
        description="Expand or collapse the Image Generation section",
        default=False
    )

    show_refine_image: bpy.props.BoolProperty(
        name="Show Refine Image",
        description="Expand or collapse the Refine Image JSON editor",
        default=False
    )

    use_structured_editing: bpy.props.BoolProperty(
        name="Use structured editing",
        description="Pass the JSON form as a structured instruction to the agent",
        default=False
    )

    # Refine Image — Metadata
    refine_meta_filename: bpy.props.StringProperty(name="Filename", default="")
    refine_meta_dimensions: bpy.props.StringProperty(name="Dimensions", default="")
    refine_meta_aspect: bpy.props.StringProperty(name="Aspect Ratio", default="")

    # Refine Image — Visual Style
    refine_style_art_style: bpy.props.StringProperty(name="Art Style", default="")
    refine_style_medium: bpy.props.StringProperty(name="Medium", default="")
    refine_style_lighting: bpy.props.StringProperty(name="Lighting Condition", default="")

    # Refine Image — Composition
    refine_comp_perspective: bpy.props.StringProperty(name="Perspective", default="")
    refine_comp_focal_point: bpy.props.StringProperty(name="Focal Point", default="")

    # Refine Image — Subject matter (dynamic collection)
    refine_subjects: bpy.props.CollectionProperty(type=RefineSubjectItem)
    refine_subjects_index: bpy.props.IntProperty(default=0)

    # Refine Image — Thematic tags (dynamic collection)
    refine_tags: bpy.props.CollectionProperty(type=RefineTagItem)
    refine_tags_index: bpy.props.IntProperty(default=0)

    show_influence: bpy.props.BoolProperty(
        name="Show Influence",
        description="Expand or collapse the Influence section",
        default=False
    )
    
    show_reference_images: bpy.props.BoolProperty(
        name="Show Reference Images",
        description="Expand or collapse the Reference Images section",
        default=False
    )
    
    show_loras: bpy.props.BoolProperty(
        name="Show LoRas",
        description="Expand or collapse the LoRas section",
        default=False
    )
    
    show_3d_generation: bpy.props.BoolProperty(
        name="Show 3D Generation",
        description="Expand or collapse the 3D Generation section",
        default=False
    )
    
    show_3d_single_image: bpy.props.BoolProperty(
        name="Show 3D from Single Image",
        description="Expand or collapse the 3D from Single Image section",
        default=False
    )
    
    show_3d_multiview: bpy.props.BoolProperty(
        name="Show 3D from Multiview",
        description="Expand or collapse the 3D from Multiview section",
        default=False
    )

    omni_control_type: bpy.props.EnumProperty(
        name="Control Mode",
        description="Spatial conditioning method sent to Hunyuan3D-Omni",
        items=[
            ('BBOX',  "Bounding Box", "Send normalised bounding box (fast, no extra export)"),
            ('POINT', "Point Cloud",  "Export active mesh as a uniform point cloud (.ply)"),
            ('VOXEL', "Voxel Mesh",   "Export remeshed watertight mesh as a .ply guide"),
        ],
        default='BBOX',
    )

    omni_mc_res: bpy.props.EnumProperty(
        name="Mesh Quality",
        description="Marching-cubes resolution used by Omni (higher = more detail, slower)",
        items=[
            ('256', "Fast",        "~200k faces — quick preview"),
            ('384', "Balanced",    "~600k faces"),
            ('512', "High Detail", "~1.5M faces — production quality"),
        ],
        default='512',
    )

    omni_guidance_scale: bpy.props.FloatProperty(
        name="Guidance Scale",
        description=(
            "Controls how strictly the 3D output adheres to the spatial conditioning. "
            "Low (1-3): smoother, more creative. High (7+): strict adherence, may produce "
            "'chewed-up' geometry. Default 4.5 is a balanced midpoint."
        ),
        default=4.5,
        min=1.0,
        max=10.0,
        step=50,
        precision=1,
    )

    omni_remesh_depth: bpy.props.IntProperty(
        name="Remesh Depth",
        description=(
            "Octree depth for the smooth remesh applied before Point Cloud / Voxel export. "
            "Lower (1-5): coarser but cleaner shape — better for complex or thin geometry. "
            "Higher (7-9): denser but may produce 'blobby' results that confuse the model."
        ),
        default=5,
        min=1,
        max=9,
    )

    omni_pc_as_mesh: bpy.props.BoolProperty(
        name="Export as Mesh PLY",
        description=(
            "Export the point cloud as a mesh PLY (vertices + faces) instead of a "
            "point-only PLY. Ensures the server can correctly normalise the data."
        ),
        default=False,
    )

    omni_precenter: bpy.props.BoolProperty(
        name="Pre-center Vertices",
        description=(
            "Subtract the mesh bounding-box centre from all vertices before export, "
            "placing the guide at the world origin. Ensures reliable server-side "
            "normalisation regardless of trimesh version."
        ),
        default=True,
    )

    # ----------------------------------------------------------------
    # TRELLIS2 generation properties
    # ----------------------------------------------------------------
    trellis_quality: bpy.props.EnumProperty(
        name="Quality",
        description="TRELLIS2 pipeline resolution. Quick=512³, Balanced=1024³ cascade, Detailed=1536³ cascade",
        items=[
            ('512',          "Quick",    "512³ — ~3 s on A100, fast iteration"),
            ('1024_cascade', "Balanced", "1024³ cascade — ~17 s, default quality"),
            ('1536_cascade', "Detailed", "1536³ cascade — ~60 s, maximum quality"),
        ],
        default='1024_cascade',
    )

    trellis_steps: bpy.props.IntProperty(
        name="Steps",
        description="Diffusion steps per stage (sparse, shape, texture). Range 4–50. Higher = more detail, slower",
        default=12,
        min=4,
        max=50,
    )

    trellis_guidance: bpy.props.FloatProperty(
        name="Guidance",
        description="CFG guidance strength. Higher = closer to input image, less creative. Range 1–20",
        default=7.5,
        min=1.0,
        max=20.0,
        step=10,
        precision=1,
    )

    trellis_texture_size: bpy.props.EnumProperty(
        name="Texture Size",
        description="Output texture atlas resolution",
        items=[
            ('1024', "1 K", "1024 px — fast, lower detail"),
            ('2048', "2 K", "2048 px — balanced"),
            ('4096', "4 K", "4096 px — maximum detail"),
        ],
        default='4096',
    )

    trellis_remove_bg: bpy.props.BoolProperty(
        name="Remove BG",
        description=(
            "Remove background from current_ai.png before sending to TRELLIS2. "
            "TRELLIS2 requires a transparent-background RGBA PNG — enable this unless "
            "the image already has a clean transparent background."
        ),
        default=True,
    )

    # Retexture-specific overrides
    trellis_tex_steps: bpy.props.IntProperty(
        name="Tex Steps",
        description="Diffusion steps for retexture pass. Range 1–50",
        default=12,
        min=1,
        max=50,
    )

    trellis_tex_guidance: bpy.props.FloatProperty(
        name="Tex Guidance",
        description="CFG guidance for retexture. Lower = more creative, higher = closer to reference",
        default=1.0,
        min=0.1,
        max=10.0,
        step=10,
        precision=1,
    )

    trellis_tex_resolution: bpy.props.EnumProperty(
        name="Tex Resolution",
        description="Voxel resolution for the texturing pass",
        items=[
            ('512',  "512",  "Fast texturing pass"),
            ('1024', "1024", "Standard quality"),
            ('1536', "1536", "High quality, slower"),
        ],
        default='1024',
    )

    trellis_decimation: bpy.props.IntProperty(
        name="Max Polygons",
        description=(
            "Maximum polygon count for the generated mesh. "
            "Very high values (>500k) can crash Blender during import "
            "due to NumPy memory limits. Keep at 300k or below for safety."
        ),
        default=300000,
        min=10000,
        max=1000000,
        step=10000,
    )

    # ----------------------------------------------------------------
    # Hunyuan3D-Part segmentation properties
    # ----------------------------------------------------------------
    part_point_num: bpy.props.IntProperty(
        name="Point Samples",
        description="P3-SAM surface sample count. Reduce below 50000 if CUDA OOM",
        default=50000,
        min=1000,
        max=50000,
    )

    part_prompt_num: bpy.props.IntProperty(
        name="Query Points",
        description="P3-SAM query points. Max safe value on 40GB VRAM is 128",
        default=128,
        min=32,
        max=128,
    )

    show_groups: bpy.props.BoolProperty(
        name="Groups",
        description="Expand or collapse the groups section",
        default=False
    )

    active_group_index: bpy.props.IntProperty(
        name="Active Group Index",
        description="Currently selected group",
        default=0
    )
    
    # Dynamic groups collection
    object_groups: bpy.props.CollectionProperty(type=ObjectGroup)
    
    # Counter for generating unique group IDs
    group_counter: bpy.props.IntProperty(default=1)

    # Properties for the influence sliders (stored as 0-1, displayed as percentage)
    depth_influence: bpy.props.FloatProperty(
        name="Depth Influence",
        description="Controls the influence of depth (0.0 to 1.0)",
        default=0.5,
        min=0.0,
        max=1.0,
        update=update_session_json
    )

    silhouette_influence: bpy.props.FloatProperty(
        name="Silhouette Influence",
        description="Controls the strength of the silhouette (0.0 to 1.0)",
        default=0.5,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    texture_influence: bpy.props.FloatProperty(
        name="Viewport",
        description="Controls how much of the render to keep in img2img workflow (GCS mode). 1.0 = keep 100% of render, 0.0 = full AI generation ignoring render",
        default=0.0,
        min=0.0,
        max=1.0,  # UI shows 0-1, internally scaled to 0-0.7 when sent
        update=update_session_json
    )
    
    steps: bpy.props.IntProperty(
        name="Steps",
        description="Number of sampling steps for AI generation (15-30)",
        default=25,
        min=15,
        max=30,
        update=update_session_json
    )
    
    render_quality: bpy.props.EnumProperty(
        name="Render Quality",
        description="Quality of render sent to AI (affects img2img workflow)",
        items=[
            ('FAST', "Fast", "Workbench render - fast preview quality, good for quick iterations", 'SHADING_WIRE', 0),
            ('DETAILED', "Detailed", "EEVEE render - high quality, better for img2img when texture_influence is low", 'SHADING_RENDERED', 1),
        ],
        default='DETAILED',
        update=update_session_json
    )

    # Workspace settings
    def update_refresh_viewport(self, context):
        """
        Refresh viewport setting (now deprecated - always on-demand).
        Image refresh happens automatically when generation completes.
        This property is kept for compatibility but does nothing.
        """
        # No timer registration needed - refresh is on-demand via on_generation_complete
        if self.refresh_viewport:
            print("[Style Engine] Image refresh: on-demand (refreshes when generation completes)")
        else:
            print("[Style Engine] Note: Image refresh is always on-demand, no timer to disable")
    
    refresh_viewport: bpy.props.BoolProperty(
        name="Refresh Viewport",
        description="Automatically refresh AI image when it changes",
        default=True,
        update=update_refresh_viewport
    )
    
    def update_auto_generate(self, context):
        """Update auto-generate and sync refresh_viewport."""
        # Sync refresh_viewport with auto_generate
        self.refresh_viewport = self.auto_generate
        # Update session JSON
        self.update_session_json(context)
        
        # ✅ Start cyclical auto-generation if enabled
        if self.auto_generate:
            # Check if ai_camera exists
            if "ai_camera" not in bpy.data.objects:
                print("[Style Engine] ⚠️ Cannot start auto-generate: ai_camera not found!")
                print("[Style Engine] Please run 'Setup Workspace' first.")
                self.auto_generate = False  # Disable to prevent infinite errors
                return
            
            from . import workspace_setup
            print("[Style Engine] 🚀 Auto-generate enabled! Starting cyclical generation...")
            # Start the first generation cycle
            bpy.app.timers.register(workspace_setup.start_generation_cycle, first_interval=0.5)
        else:
            print("[Style Engine] Auto-generate disabled. Stopping cyclical generation.")
    
    auto_generate: bpy.props.BoolProperty(
        name="Autogenerate",
        description="Toggle continuous AI generation ON/OFF (when enabled, continuously renders and generates images)",
        default=False,
        update=update_auto_generate
    )
    
    # Prompt Builder - simple template-based prompt system
    def update_prompt_builder(self, context):
        """When Prompt Builder is enabled, auto-load templates"""
        # Update session.json
        self.update_session_json(context)
        
        # Auto-load templates when enabled
        if self.use_prompt_builder:
            from . import utils
            count, message = utils.load_all_templates()
            print(f"[Style Engine] Prompt Builder enabled: {message}")
            # Show info to user
            if context:
                context.area.tag_redraw() if hasattr(context, 'area') and context.area else None
    
    use_prompt_builder: bpy.props.BoolProperty(
        name="Enable Prompt Builder",
        description="Automatic: parses HTML tags if present, otherwise uses raw text",
        default=True,  # Always enabled by default
        update=update_prompt_builder
    )
    
    def update_background_opacity(self, context):
        """Update the ai_camera background image opacity."""
        if "ai_camera" in bpy.data.objects:
            ai_camera = bpy.data.objects["ai_camera"]
            cam_data = ai_camera.data
            
            # Update background images opacity
            for bg in cam_data.background_images:
                bg.alpha = self.background_opacity
                
            print(f"[Style Engine] Background opacity set to: {self.background_opacity:.2f}")
    
    background_opacity: bpy.props.FloatProperty(
        name="Background Opacity",
        description="Transparency of the AI background image (0=invisible, 1=opaque)",
        default=1.0,
        min=0.0,
        max=1.0,
        update=update_background_opacity
    )
    
    def update_visualization_type(self, context):
        """Switch camera background between Combined, Canny, and Depth visualizations."""
        from pathlib import Path
        from . import workspace_setup
        
        # Get temp directory
        temp_dir = workspace_setup.get_temp_directory(context)
        
        # Determine which image to display
        if self.visualization_type == 'COMBINED':
            image_path = temp_dir / "current_ai.png"
            display_name = "Combined (Final)"
        elif self.visualization_type == 'CANNY':
            image_path = temp_dir / "canny.png"
            display_name = "Silhouette (Canny)"
        elif self.visualization_type == 'DEPTH':
            image_path = temp_dir / "depth.png"
            display_name = "Depth Map"
        else:
            return
        
        # Check if file exists
        if not image_path.exists():
            print(f"[Visualization] ⚠️ {display_name} not found at {image_path}")
            print(f"[Visualization] Enable 'Download Preview Images' in preferences and generate an image first")
            return
        
        # Update camera background
        if "ai_camera" in bpy.data.objects:
            ai_camera = bpy.data.objects["ai_camera"]
            cam_data = ai_camera.data
            
            if cam_data.background_images:
                bg = cam_data.background_images[0]
                
                # Load or reload the image
                image_name = image_path.name
                if image_name in bpy.data.images:
                    img = bpy.data.images[image_name]
                    img.reload()
                else:
                    img = bpy.data.images.load(str(image_path))
                
                bg.image = img
                print(f"[Visualization] ✓ Switched to: {display_name}")
                
                # Force viewport update
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        else:
            print(f"[Visualization] ⚠️ ai_camera not found. Setup workspace first.")
    
    visualization_type: bpy.props.EnumProperty(
        name="Visualization Type",
        description="Switch between different visualization modes",
        items=[
            ('COMBINED', "Combined", "Final generated image", 'IMAGE_DATA', 0),
            ('CANNY', "Silhouette", "Canny edge detection (what the AI sees as edges)", 'MESH_PLANE', 1),
            ('DEPTH', "Depth", "Depth map (what the AI sees as depth)", 'EMPTY_SINGLE_ARROW', 2),
        ],
        default='COMBINED',
        update=update_visualization_type
    )
    
    def update_ai_resolution(self, context):
        """
        ROCK SOLID: Update resolution immediately when user changes dropdown.
        This is CRITICAL - SDXL native resolutions directly influence output quality.
        Updates Blender's render settings, camera background, and session.json in real-time.
        """
        from . import workspace_setup
        
        try:
            # 1. Parse new resolution (SDXL native format)
            res_str = self.ai_resolution
            width, height = map(int, res_str.split('x'))
            
            # 2. Update Blender's render resolution IMMEDIATELY
            context.scene.render.resolution_x = width
            context.scene.render.resolution_y = height
            
            print(f"[Style Engine] ✓ Resolution set to: {width}x{height} (SDXL native)")
            
            # 3. Update camera background image if camera exists
            prefs = context.preferences.addons['styleengine'].preferences
            camera_name = prefs.camera_name_override
            
            if camera_name in bpy.data.objects:
                camera = bpy.data.objects[camera_name]
                if camera.type == 'CAMERA':
                    # Get temp directory
                    temp_dir = workspace_setup.get_temp_directory(context)
                    placeholder_path = temp_dir / "current_ai.png"
                    
                    # Resize existing image or create new placeholder
                    if "current_ai.png" in bpy.data.images:
                        img = bpy.data.images["current_ai.png"]
                        
                        # Check if image needs resizing
                        if img.size[0] != width or img.size[1] != height:
                            # Recreate image at new resolution
                            bpy.data.images.remove(img)
                            new_img = bpy.data.images.new("current_ai.png", width=width, height=height)
                            
                            # Fill with placeholder color (dark blue)
                            pixels = [0.1, 0.1, 0.2, 1.0] * (width * height)
                            new_img.pixels = pixels
                            
                            # Save to disk
                            new_img.filepath_raw = str(placeholder_path)
                            new_img.file_format = 'PNG'
                            new_img.save()
                            
                            # Update camera background reference
                            if len(camera.data.background_images) > 0:
                                bg_img = camera.data.background_images[0]
                                bg_img.image = new_img
                                
                                # Maintain opacity setting
                                bg_img.alpha = self.background_opacity
                                
                                print(f"[Style Engine] ✓ Camera background resized to {width}x{height}")
                    
                    # Force viewport redraw for immediate visual feedback
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            
            # 4. Update session.json (critical for workflow JSON compatibility)
            workspace_setup.write_session_json(context)
            
        except Exception as e:
            print(f"[Style Engine] Error updating resolution: {e}")
            import traceback
            traceback.print_exc()
    
    ai_resolution: bpy.props.EnumProperty(
        name="AI Resolution",
        description="Resolution for AI generation (SDXL native resolutions - directly affects output quality)",
        items=[
            ('640x1536', '640 x 1536', 'Portrait tall'),
            ('768x1344', '768 x 1344', 'Portrait'),
            ('832x1216', '832 x 1216', 'Portrait medium'),
            ('896x1152', '896 x 1152', 'Portrait slight'),
            ('1024x1024', '1024 x 1024', 'Square'),
            ('1152x896', '1152 x 896', 'Landscape slight'),
            ('1216x832', '1216 x 832', 'Landscape medium'),
            ('1344x768', '1344 x 768', 'Landscape'),
            ('1536x640', '1536 x 640', 'Landscape wide'),
        ],
        default='1024x1024',
        update=update_ai_resolution  # Live, instant update - CRITICAL for SDXL workflow
    )
    
    save_iterations: bpy.props.BoolProperty(
        name="Save Iterations",
        description="Automatically save iteration snapshots with their corresponding AI images",
        default=True
    )
    
    # Generation browser - track current generation index
    current_generation_index: bpy.props.IntProperty(
        name="Current Generation",
        description="Index of currently displayed generation (0 = latest, -1 = newest)",
        default=-1,  # -1 means "latest/newest"
        min=-1
    )
    
    # Prompt browser - track current prompt index
    current_prompt_index: bpy.props.IntProperty(
        name="Current Prompt",
        description="Index of currently displayed prompt snapshot (0 = oldest, -1 = latest)",
        default=-1,  # -1 means "latest/newest"
        min=-1
    )
    
    # Model browser - track current model index
    current_model_index: bpy.props.IntProperty(
        name="Current Model",
        description="Index of currently selected model (0 = oldest, -1 = latest)",
        default=-1,  # -1 means "latest/newest"
        min=-1
    )
    
    # ================================================================
    # REFERENCE IMAGE SYSTEM (15 slots: 5 per mode)
    # ================================================================
    
    # Collapsible sections for reference modes
    show_style_transfer: bpy.props.BoolProperty(
        name="Show Style Transfer",
        description="Expand or collapse the Style Transfer section",
        default=False
    )
    
    show_composition: bpy.props.BoolProperty(
        name="Show Composition",
        description="Expand or collapse the Composition section",
        default=False
    )
    
    show_force_transfer: bpy.props.BoolProperty(
        name="Show Force Style Transfer",
        description="Expand or collapse the Force Style Transfer section",
        default=False
    )
    
    # Advanced control toggle for reference images
    show_advanced_ref_controls: bpy.props.BoolProperty(
        name="Advanced Control",
        description="Show individual weight sliders for each reference image (default: all weights = 1.0)",
        default=False
    )
    
    # Global strength sliders (UI: 0.0-1.0, Workflow: 0.0-1.5 via 1.5x multiplier)
    style_transfer_strength: bpy.props.FloatProperty(
        name="Style Transfer Strength",
        description="Global strength for all Style Transfer images (0.0 to 1.0, scaled to 1.5 in workflow)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    composition_strength: bpy.props.FloatProperty(
        name="Composition Strength",
        description="Global strength for all Composition images (0.0 to 1.0, scaled to 1.5 in workflow)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    force_transfer_strength: bpy.props.FloatProperty(
        name="Force Style Transfer Strength",
        description="Global strength for all Force Style Transfer images (0.0 to 5.0)",
        default=0.0,
        min=0.0,
        max=5.0,
        update=update_session_json
    )
    
    # Style Transfer images (ST1-ST5)
    st1_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Style Transfer 1"
    )
    st1_weight: bpy.props.FloatProperty(
        name="ST1 Weight",
        description="Individual weight for Style Transfer image 1 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    st2_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Style Transfer 2"
    )
    st2_weight: bpy.props.FloatProperty(
        name="ST2 Weight",
        description="Individual weight for Style Transfer image 2 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    st3_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Style Transfer 3"
    )
    st3_weight: bpy.props.FloatProperty(
        name="ST3 Weight",
        description="Individual weight for Style Transfer image 3 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    st4_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Style Transfer 4"
    )
    st4_weight: bpy.props.FloatProperty(
        name="ST4 Weight",
        description="Individual weight for Style Transfer image 4 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    st5_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Style Transfer 5"
    )
    st5_weight: bpy.props.FloatProperty(
        name="ST5 Weight",
        description="Individual weight for Style Transfer image 5 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    # Composition images (COMP1-COMP5)
    comp1_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Composition 1"
    )
    comp1_weight: bpy.props.FloatProperty(
        name="COMP1 Weight",
        description="Individual weight for Composition image 1 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    comp2_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Composition 2"
    )
    comp2_weight: bpy.props.FloatProperty(
        name="COMP2 Weight",
        description="Individual weight for Composition image 2 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    comp3_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Composition 3"
    )
    comp3_weight: bpy.props.FloatProperty(
        name="COMP3 Weight",
        description="Individual weight for Composition image 3 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    comp4_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Composition 4"
    )
    comp4_weight: bpy.props.FloatProperty(
        name="COMP4 Weight",
        description="Individual weight for Composition image 4 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    comp5_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Composition 5"
    )
    comp5_weight: bpy.props.FloatProperty(
        name="COMP5 Weight",
        description="Individual weight for Composition image 5 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    # Force Style Transfer images (SST1-SST5)
    sst1_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Force Style Transfer 1"
    )
    sst1_weight: bpy.props.FloatProperty(
        name="SST1 Weight",
        description="Individual weight for Force Style Transfer image 1 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    sst2_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Force Style Transfer 2"
    )
    sst2_weight: bpy.props.FloatProperty(
        name="SST2 Weight",
        description="Individual weight for Force Style Transfer image 2 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    sst3_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Force Style Transfer 3"
    )
    sst3_weight: bpy.props.FloatProperty(
        name="SST3 Weight",
        description="Individual weight for Force Style Transfer image 3 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    sst4_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Force Style Transfer 4"
    )
    sst4_weight: bpy.props.FloatProperty(
        name="SST4 Weight",
        description="Individual weight for Force Style Transfer image 4 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    sst5_image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Force Style Transfer 5"
    )
    sst5_weight: bpy.props.FloatProperty(
        name="SST5 Weight",
        description="Individual weight for Force Style Transfer image 5 (0.0 to 1.0)",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    # IPAdapter properties
    show_ipadapter: bpy.props.BoolProperty(
        name="Show IPAdapter",
        description="Expand or collapse the IPAdapter section",
        default=False
    )
    
    use_ipadapter: bpy.props.BoolProperty(
        name="Use image reference",
        description="Enable IPAdapter workflow with reference image guidance",
        default=False,
        update=update_session_json
    )
    
    ipadapter_reference_image: bpy.props.StringProperty(
        name="Reference Image",
        description="Path to reference image for style/composition guidance",
        default="",
        subtype='FILE_PATH',
        update=update_session_json
    )
    
    ipadapter_weight_type: bpy.props.EnumProperty(
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
        default='style transfer',
        update=update_session_json
    )
    
    ipadapter_strength: bpy.props.FloatProperty(
        name="Strength",
        description="IPAdapter influence (0.0=off, 5.0=maximum)",
        default=0.75,
        min=0.0,
        max=5.0,
        step=5,
        precision=2,
        update=update_session_json
    )
    
    # ================================================================
    # LORA CONFIGURATION
    # ================================================================
    
    lora_enabled: bpy.props.BoolProperty(
        name="Use LoRa",
        description="Enable LoRa model for generation",
        default=False,
        update=update_session_json
    )
    
    lora_name: bpy.props.EnumProperty(
        name="LoRa Model",
        description="Select LoRa model to use (fetched from ComfyUI server in GCS mode)",
        items=get_lora_items,  # Dynamic callback - fetches from server
        update=update_session_json
    )
    
    lora_strength_model: bpy.props.FloatProperty(
        name="LoRa Strength",
        description="LoRa influence on the model (0.0 to 1.0)",
        default=0.8,
        min=0.0,
        max=1.0,
        step=1,
        precision=2,
        update=update_session_json
    )
    
    # LoRa 2 (second LoRa slot for stacking)
    lora2_enabled: bpy.props.BoolProperty(
        name="Use LoRa 2",
        description="Enable second LoRa model for stacking effects",
        default=False,
        update=update_session_json
    )
    
    lora2_name: bpy.props.EnumProperty(
        name="LoRa 2 Model",
        description="Select second LoRa model (fetched from ComfyUI server in GCS mode)",
        items=get_lora_items,  # Dynamic callback - fetches from server
        update=update_session_json
    )
    
    lora2_strength_model: bpy.props.FloatProperty(
        name="LoRa 2 Strength",
        description="Second LoRa influence on the model (0.0 to 1.0)",
        default=0.8,
        min=0.0,
        max=1.0,
        step=1,
        precision=2,
        update=update_session_json
    )
    
    # ================================================================
    # 3D OBJECT GENERATION CONFIGURATION
    # ================================================================
    
    object_quality: bpy.props.EnumProperty(
        name="3D Quality",
        description="Generation quality preset for 3D object creation",
        items=[
            ('SKETCH', "Sketch", "Ultra-fast preview - Lowest detail for concept testing"),
            ('FAST', "Fast", "Quick preview - Draft quality for rapid iteration"),
            ('BALANCED', "Balanced", "Production quality - Recommended for most work"),
            ('DETAILED', "Detailed", "Maximum detail - Ultra-high quality for hero assets"),
        ],
        default='BALANCED',
        update=update_session_json
    )


# ----------------------------------------------------------------
# 2. OPERATORS
# ----------------------------------------------------------------
# Legacy operators removed - no longer needed


class WM_OT_RerollSeed(bpy.types.Operator):
    """Randomize the seed for AI workflows"""
    bl_idname = "style_engine.reroll_seed"
    bl_label = "Reroll Seed"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import random
        context.scene.style_engine_props.seed_value = random.randint(0, 2147483647)
        return {'FINISHED'}


class WM_OT_AlignAICameraToView(bpy.types.Operator):
    """Align AI camera to current 3D viewport."""
    bl_idname = "style_engine.align_camera_to_view"
    bl_label = "Reposition AI Camera"
    bl_description = "Move AI camera to match current 3D viewport view (like Ctrl+Alt+Numpad0)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        camera_name = prefs.camera_name_override
        
        # Find ai_camera
        if camera_name not in bpy.data.objects:
            self.report({'ERROR'}, f"Camera '{camera_name}' not found. Run 'Setup Workspace' first.")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects[camera_name]
        
        if ai_camera.type != 'CAMERA':
            self.report({'ERROR'}, f"'{camera_name}' is not a camera!")
            return {'CANCELLED'}
        
        # Find active 3D viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Get current view matrix
                        view_matrix = space.region_3d.view_matrix.inverted()
                        
                        # Align camera to view
                        ai_camera.matrix_world = view_matrix
                        
                        self.report({'INFO'}, "AI camera repositioned to current view")
                        
                        if prefs.debug_mode:
                            print(f"[Style Engine] ✓ Camera '{camera_name}' aligned to view")
                            print(f"[Style Engine]   Location: {ai_camera.location}")
                        
                        return {'FINISHED'}
        
        self.report({'WARNING'}, "No 3D viewport found")
        return {'CANCELLED'}


class WM_OT_BringBackgroundForward(bpy.types.Operator):
    """Bring AI background image in front of objects"""
    bl_idname = "style_engine.bring_background_forward"
    bl_label = "Bring Forward"
    bl_description = "Display AI background image in front of 3D objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        camera_name = prefs.camera_name_override
        
        if camera_name not in bpy.data.objects:
            self.report({'WARNING'}, f"Camera '{camera_name}' not found")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects[camera_name]
        if ai_camera.type != 'CAMERA':
            self.report({'WARNING'}, f"'{camera_name}' is not a camera")
            return {'CANCELLED'}
        
        cam_data = ai_camera.data
        if len(cam_data.background_images) > 0:
            cam_data.background_images[0].display_depth = 'FRONT'
            self.report({'INFO'}, "Background image brought forward")
            print("[Style Engine] ✓ Background display_depth: FRONT (in front of objects)")
            
            # Redraw viewports
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No background image found on camera")
            return {'CANCELLED'}


class WM_OT_SendBackgroundBack(bpy.types.Operator):
    """Send AI background image behind objects"""
    bl_idname = "style_engine.send_background_back"
    bl_label = "Send to Back"
    bl_description = "Display AI background image behind 3D objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        camera_name = prefs.camera_name_override
        
        if camera_name not in bpy.data.objects:
            self.report({'WARNING'}, f"Camera '{camera_name}' not found")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects[camera_name]
        if ai_camera.type != 'CAMERA':
            self.report({'WARNING'}, f"'{camera_name}' is not a camera")
            return {'CANCELLED'}
        
        cam_data = ai_camera.data
        if len(cam_data.background_images) > 0:
            cam_data.background_images[0].display_depth = 'BACK'
            self.report({'INFO'}, "Background image sent to back")
            print("[Style Engine] ✓ Background display_depth: BACK (behind objects)")
            
            # Redraw viewports
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No background image found on camera")
            return {'CANCELLED'}


# Prompt editor operators removed - text editor now auto-created in workspace layout
# and auto-syncs on generation (no manual buttons needed)


class WM_OT_AddGroup(bpy.types.Operator):
    """Add a new object group."""
    bl_idname = "style_engine.add_group"
    bl_label = "Add Group"
    
    group_name: bpy.props.StringProperty(
        name="Group Name",
        default="NewGroup"
    )
    
    def invoke(self, context, event):
        # Show popup dialog for name input
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "group_name")
    
    def execute(self, context):
        props = context.scene.style_engine_props
        
        # Create new group
        new_group = props.object_groups.add()
        new_group.name = self.group_name if self.group_name else f"Group_{props.group_counter}"
        new_group.keywords = ""
        new_group.pass_index = 12 + len(props.object_groups) - 1  # Unique pass index
        new_group.object_ids = ""
        
        # Increment counter
        props.group_counter += 1
        
        # Set as active
        props.active_group_index = len(props.object_groups) - 1
        
        # Update session JSON
        from . import workspace_setup
        workspace_setup.write_session_json(context)
        
        self.report({'INFO'}, f"Created group: {new_group.name}")
        print(f"[Style Engine] Created group: {new_group.name}")
        
        return {'FINISHED'}


class WM_OT_AssignGroup(bpy.types.Operator):
    """Assign selected objects to active group."""
    bl_idname = "style_engine.assign_group"
    bl_label = "Assign to Group"
    
    def execute(self, context):
        # Placeholder - will assign selected objects to group
        selected = [obj.name for obj in context.selected_objects]
        self.report({'INFO'}, f"Assign - Selected: {len(selected)} objects")
        print(f"[Style Engine] Assign Group clicked - {selected}")
        return {'FINISHED'}


class WM_OT_RenameGroup(bpy.types.Operator):
    """Rename the active group."""
    bl_idname = "style_engine.rename_group"
    bl_label = "Rename Group"
    
    def execute(self, context):
        # Placeholder - will open rename dialog
        self.report({'INFO'}, "Rename Group - Coming soon")
        print("[Style Engine] Rename Group clicked")
        return {'FINISHED'}


class WM_OT_SelectGroup(bpy.types.Operator):
    """Select a group to make it active."""
    bl_idname = "style_engine.select_group"
    bl_label = "Select Group"
    
    group_index: bpy.props.IntProperty()
    
    def execute(self, context):
        props = context.scene.style_engine_props
        props.active_group_index = self.group_index
        
        group_names = ["BUILDINGS", "TUNNELS", "GROUND"]
        if self.group_index < len(group_names):
            print(f"[Style Engine] Selected group: {group_names[self.group_index]}")
        
        return {'FINISHED'}


class WM_OT_DeleteGroup(bpy.types.Operator):
    """Delete the active group."""
    bl_idname = "style_engine.delete_group"
    bl_label = "Delete Group"
    
    def execute(self, context):
        props = context.scene.style_engine_props
        active = props.active_group_index
        
        if 0 <= active < len(props.object_groups):
            group_name = props.object_groups[active].name
            props.object_groups.remove(active)
            
            # Adjust active index if needed
            if props.active_group_index >= len(props.object_groups):
                props.active_group_index = max(0, len(props.object_groups) - 1)
            
            # Update session JSON
            from . import workspace_setup
            workspace_setup.write_session_json(context)
            
            self.report({'INFO'}, f"Deleted group: {group_name}")
            print(f"[Style Engine] Deleted group: {group_name}")
        else:
            self.report({'WARNING'}, "No group selected")
        
        return {'FINISHED'}


class WM_OT_ProjectTexture(bpy.types.Operator):
    """Project AI texture onto selected objects from camera view."""
    bl_idname = "style_engine.project_texture"
    bl_label = "Project Texture"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Check if ai_camera exists
        if "ai_camera" not in bpy.data.objects:
            self.report({'ERROR'}, "AI Camera not found. Please setup workspace first.")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects["ai_camera"]
        
        # Get path to current_ai.png using the correct temp directory
        from . import workspace_setup
        temp_dir = workspace_setup.get_temp_directory(context)
        img_path = temp_dir / "current_ai.png"
        
        print(f"[Style Engine] Looking for AI image at: {img_path}")
        
        if not img_path.exists():
            self.report({'ERROR'}, f"AI image not found at {img_path}. Generate an image first.")
            return {'CANCELLED'}
        
        print(f"[Style Engine] Found image, loading for projection...")
        
        # Load or reload the image
        img_name = "current_ai.png"
        if img_name in bpy.data.images:
            img = bpy.data.images[img_name]
            img.filepath = str(img_path)
            img.reload()
        else:
            img = bpy.data.images.load(str(img_path))
            img.name = img_name
        
        # Store original state
        original_active = context.view_layer.objects.active
        original_selected = list(context.selected_objects)
        original_mode = context.object.mode if context.object else 'OBJECT'
        original_camera = context.scene.camera
        
        # Temporarily set ai_camera as scene camera for projection
        context.scene.camera = ai_camera
        
        # Make sure we're in object mode
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get only selected mesh objects (changed from all scene objects)
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects selected. Please select objects to project texture onto.")
            return {'CANCELLED'}
        
        # Find next iteration number for unique material/image naming
        iteration_num = 0
        while f"iteration_{iteration_num:03d}" in bpy.data.materials:
            iteration_num += 1
        
        iteration_name = f"iteration_{iteration_num:03d}"
        
        # Duplicate the current_ai.png image to create an archival copy
        # This ensures the texture won't change when new AI images are generated
        img_copy = img.copy()
        img_copy.name = f"{iteration_name}.png"
        
        # Pack the image so it's embedded in the .blend file
        if not img_copy.packed_file:
            img_copy.pack()
        
        print(f"[Style Engine] 📸 Created archival image: {img_copy.name}")
        
        # Save texture to project library iterations folder (external backup)
        self.save_iteration_texture(context, img_path, iteration_name)
        
        # Create a new unique material for this iteration
        mat = bpy.data.materials.new(name=iteration_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        
        # Clear default nodes
        nodes.clear()
        
        # Create Principled BSDF
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        
        # Set roughness to 1.0 for matte finish
        bsdf.inputs['Roughness'].default_value = 1.0
        
        # Create Image Texture node with the duplicated image
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.location = (-300, 0)
        tex_node.image = img_copy  # Use the duplicated image, not the original
        
        # Create Material Output
        output = nodes.new(type='ShaderNodeOutputMaterial')
        output.location = (300, 0)
        
        # Connect nodes
        # Connect texture to Base Color
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        
        # Connect texture to Specular Tint to prevent white/washed out IOR look
        # This tints the specular reflections and refractions with the texture color
        if 'Specular Tint' in bsdf.inputs:
            links.new(tex_node.outputs['Color'], bsdf.inputs['Specular Tint'])
        
        # Connect BSDF to output
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        print(f"[Style Engine] 🎨 Created archival material: {mat.name}")
        
        # Simple projection: Project from active view onto all selected objects at once
        projected_count = 0
        
        try:
            # Assign material to all selected objects
            for obj in mesh_objects:
                if len(obj.data.materials) == 0:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat
                projected_count += 1
                print(f"[Style Engine] ✓ Assigned material to {obj.name}")
            
            # Enter edit mode (works with all selected objects)
            bpy.ops.object.mode_set(mode='EDIT')
            
            # Select all faces
            bpy.ops.mesh.select_all(action='SELECT')
            
            # Find 3D viewport and temporarily switch to camera view for projection
            viewport_3d = None
            space_3d = None
            original_view_perspective = None
            
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    viewport_3d = area
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space_3d = space
                            original_view_perspective = space.region_3d.view_perspective
                            break
                    break
            
            if space_3d and original_view_perspective:
                # Temporarily switch to camera view
                space_3d.region_3d.view_perspective = 'CAMERA'
                print(f"[Style Engine] Temporarily switched viewport to camera view for projection")
            
            # Temporarily match render resolution to the actual texture dimensions so the
            # camera projection matrix is pixel-perfect regardless of image aspect ratio.
            # correct_aspect=False: camera_bounds=True already bakes aspect into the projection
            # matrix; the additional viewport-pixel correction would distort non-square images.
            _proj_img = bpy.data.images.get("current_ai.png")
            _orig_rx = context.scene.render.resolution_x
            _orig_ry = context.scene.render.resolution_y
            if _proj_img and _proj_img.size[0] > 0 and _proj_img.size[1] > 0:
                context.scene.render.resolution_x = _proj_img.size[0]
                context.scene.render.resolution_y = _proj_img.size[1]
            bpy.ops.uv.project_from_view(
                camera_bounds=True,
                correct_aspect=False,
                scale_to_bounds=False
            )
            context.scene.render.resolution_x = _orig_rx
            context.scene.render.resolution_y = _orig_ry
            
            # Restore original viewport perspective
            if space_3d and original_view_perspective:
                space_3d.region_3d.view_perspective = original_view_perspective
                print(f"[Style Engine] Restored viewport to original view")
            
            # Initialize coverage map for patch system (while still in edit mode)
            # Return to object mode
            bpy.ops.object.mode_set(mode='OBJECT')
            
            print(f"[Style Engine] ✓ Projected texture from ai_camera onto {projected_count} objects")
            
        except Exception as e:
            print(f"[Style Engine] ✗ Error during projection: {e}")
            
            # Restore viewport perspective if it was changed
            if 'space_3d' in locals() and space_3d and 'original_view_perspective' in locals() and original_view_perspective:
                try:
                    space_3d.region_3d.view_perspective = original_view_perspective
                    print(f"[Style Engine] Restored viewport after error")
                except:
                    pass
            
            # Make sure we're back in object mode
            if context.object and context.object.mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
        
        # Restore original camera
        context.scene.camera = original_camera
        
        # Restore original selection
        for o in context.selected_objects:
            o.select_set(False)
        for obj in original_selected:
            if obj.name in context.scene.objects:
                obj.select_set(True)
        
        if original_active and original_active.name in context.scene.objects:
            context.view_layer.objects.active = original_active
        
        # Restore original mode
        if original_mode == 'EDIT':
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except:
                pass
        
        self.report({'INFO'}, f"Projected {iteration_name} onto {projected_count} objects")
        print(f"[Style Engine] 🎨 Projected {iteration_name} onto {projected_count} objects")
        
        # Create iteration snapshot
        self.create_iteration_snapshot(context, mesh_objects)
        
        return {'FINISHED'}
    
    def save_iteration_texture(self, context, source_image_path, iteration_name):
        """
        Save iteration texture to project library iterations folder.
        Provides external backup of projected textures.
        
        Args:
            context: Blender context
            source_image_path: Path to current_ai.png
            iteration_name: Name like 'iteration_000'
        """
        from . import workspace_setup
        from pathlib import Path
        import shutil
        
        # Get project library
        project_lib = workspace_setup.get_project_library(context)
        
        if project_lib:
            # Save to project library Textures folder
            textures_dir = project_lib / "Textures"
            textures_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = textures_dir / f"{iteration_name}.png"
            
            try:
                shutil.copy2(source_image_path, dest_path)
                print(f"[Style Engine] 💾 Saved texture to: {dest_path.name}")
            except Exception as e:
                print(f"[Style Engine] ⚠️ Failed to save texture to Textures folder: {e}")
        else:
            # .blend not saved - save to session temp
            import tempfile
            session_id = workspace_setup.get_session_id()
            temp_base = Path(tempfile.gettempdir()) / "blender_styleengine" / "sessions"
            textures_dir = temp_base / session_id / "Textures"
            textures_dir.mkdir(parents=True, exist_ok=True)
            
            dest_path = textures_dir / f"{iteration_name}.png"
            
            try:
                shutil.copy2(source_image_path, dest_path)
                print(f"[Style Engine] 💾 Saved texture to session: {dest_path.name}")
                print(f"[Style Engine] ℹ️  Save .blend to migrate to project library")
            except Exception as e:
                print(f"[Style Engine] ⚠️ Failed to save texture: {e}")
    
    def create_iteration_snapshot(self, context, mesh_objects):
        """Create a snapshot of all meshes joined into a single iteration object."""
        if not mesh_objects:
            return
        
        props = context.scene.style_engine_props
        
        # Check if save iterations is enabled
        if not props.save_iterations:
            print("[Style Engine] ⏭️ Save Iterations disabled, skipping snapshot")
            return
        
        # Ensure we're in object mode
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get or create "Iterations" collection
        if "Iterations" not in bpy.data.collections:
            iterations_collection = bpy.data.collections.new("Iterations")
            context.scene.collection.children.link(iterations_collection)
            print("[Style Engine] Created 'Iterations' collection")
        else:
            iterations_collection = bpy.data.collections["Iterations"]
        
        # Find next iteration number
        iteration_num = 0
        while f"Iteration_{iteration_num:03d}" in bpy.data.objects:
            iteration_num += 1
        
        iteration_name = f"Iteration_{iteration_num:03d}"
        
        # Deselect all
        for obj in context.selected_objects:
            obj.select_set(False)
        
        # Select all mesh objects
        for obj in mesh_objects:
            obj.select_set(True)
        
        # Set one as active for duplication
        if mesh_objects:
            context.view_layer.objects.active = mesh_objects[0]
        
        # Get current objects before duplication
        objects_before = set(bpy.data.objects)
        
        # Duplicate all selected objects at once
        bpy.ops.object.duplicate(linked=False)
        
        # Find the new duplicated objects
        objects_after = set(bpy.data.objects)
        duplicates = list(objects_after - objects_before)
        
        print(f"[Style Engine] 📦 Duplicated {len(duplicates)} objects")
        
        # Deselect originals, keep duplicates selected
        for obj in mesh_objects:
            obj.select_set(False)
        
        # Set one as active
        if duplicates:
            context.view_layer.objects.active = duplicates[0]
            
            # Join all duplicates into one mesh (Ctrl+J equivalent)
            if len(duplicates) > 1:
                bpy.ops.object.join()
            
            # Get the joined object (active object after join)
            joined_obj = context.active_object
            
            # Rename it
            joined_obj.name = iteration_name
            
            # Unlink from current collection and link to Iterations collection
            for coll in joined_obj.users_collection:
                coll.objects.unlink(joined_obj)
            iterations_collection.objects.link(joined_obj)
            
            # Hide from viewport (eye icon in outliner)
            joined_obj.hide_viewport = True
            
            # Disable in renders (camera icon)
            joined_obj.hide_render = True
            
            # Ensure object is not "disabled" (gray font) - keep it selectable
            joined_obj.hide_select = False
            
            # Deselect
            joined_obj.select_set(False)
            
            print(f"[Style Engine] 💾 Created {iteration_name} in Iterations collection")
            print(f"[Style Engine]    └─ Hidden from viewport (eye icon) and disabled in renders")
            
            # Copy AI image to generated folder and assign material
            self.save_iteration_image_and_material(iteration_name, joined_obj)
    
    def save_iteration_image_and_material(self, iteration_name, obj):
        """Copy the AI image and assign it as the base color material."""
        try:
            # Get project root (go up from addon root)
            addon_root = Path(__file__).parent.parent.parent.parent
            
            # Path to current AI image
            ai_image_path = addon_root / "data" / "temp" / "ai_vision" / "current_ai.png"
            
            if not ai_image_path.exists():
                print(f"[Style Engine] ⚠️ AI image not found at {ai_image_path}")
                return
            
            # Create generated folder if it doesn't exist
            generated_folder = addon_root / "generated"
            generated_folder.mkdir(exist_ok=True)
            
            # Copy image to generated folder with iteration name
            dest_image_path = generated_folder / f"{iteration_name}.png"
            shutil.copy2(ai_image_path, dest_image_path)
            print(f"[Style Engine] 📸 Saved image: {dest_image_path.name}")
            
            # Load the image into Blender
            if iteration_name in bpy.data.images:
                bpy.data.images.remove(bpy.data.images[iteration_name])
            
            img = bpy.data.images.load(str(dest_image_path))
            img.name = iteration_name
            
            # Create or get material
            mat_name = f"{iteration_name}_Material"
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
            else:
                mat = bpy.data.materials.new(name=mat_name)
                mat.use_nodes = True
            
            # Clear existing nodes and create new setup
            nodes = mat.node_tree.nodes
            nodes.clear()
            
            # Create nodes
            output_node = nodes.new(type='ShaderNodeOutputMaterial')
            output_node.location = (300, 0)
            
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf_node.location = (0, 0)
            
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (-300, 0)
            tex_node.image = img
            
            # Connect nodes
            links = mat.node_tree.links
            links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
            
            # Assign material to object
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            
            print(f"[Style Engine] 🎨 Material '{mat_name}' assigned with texture")
            
        except Exception as e:
            print(f"[Style Engine] ❌ Error saving iteration image/material: {e}")


# ================================================================
# NANO IMAGE GENERATION (POC)
# ================================================================

class WM_OT_NanoGenerate(bpy.types.Operator):
    """Generate image from a plane's texture using Gemini nano-banana"""
    bl_idname = "style_engine.nano_generate"
    bl_label = "Nano Generate"
    bl_description = "Send a plane's painted texture + prompt to Gemini nano-banana for image generation"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import json
        import time
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        from . import utils
        from .runcomfy_server_client import extract_output_images
        
        # 1. Validate
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh with a painted texture")
            return {'CANCELLED'}
        
        if not obj.data.materials:
            self.report({'ERROR'}, "Selected object has no material")
            return {'CANCELLED'}
        
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Nano requires Server mode")
            return {'CANCELLED'}
        
        # 2. Extract texture from material node tree
        tex_image = None
        for mat in obj.data.materials:
            if mat and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        tex_image = node.image
                        break
                if tex_image:
                    break
        
        if not tex_image:
            self.report({'ERROR'}, "No texture image found in material. Paint on the plane first.")
            return {'CANCELLED'}
        
        # Save texture to temp
        temp_dir = workspace_setup.get_temp_directory(context)
        tex_path = temp_dir / f"nano_input_{int(time.time())}.png"
        tex_image.save_render(str(tex_path))
        print(f"[Nano] Extracted texture: {tex_image.name} -> {tex_path.name}")
        
        # 3. Parse prompt (only positive from <p> tag)
        prompt_text = ""
        raw_prompt = utils.get_prompt_from_text_editor()
        if raw_prompt:
            positive, _ = utils.process_prompt_builder(raw_prompt)
            prompt_text = positive or ""
        
        if not prompt_text:
            self.report({'ERROR'}, "No prompt found in <p> tag")
            return {'CANCELLED'}
        
        print(f"[Nano] Prompt: {prompt_text[:80]}...")
        
        try:
            # 4. Upload texture
            server_client = runcomfy_deployment.get_server_client()
            upload_resp = server_client.upload_image(str(tex_path), overwrite=True)
            uploaded_name = upload_resp.get("name", "")
            
            if not uploaded_name:
                self.report({'ERROR'}, "Failed to upload texture")
                return {'CANCELLED'}
            
            print(f"[Nano] Uploaded: {uploaded_name}")
            
            # 5. Load and patch workflow
            workflow_file = Path(__file__).parent / "workflows" / "Image" / "TestImageNano.json"
            if not workflow_file.exists():
                self.report({'ERROR'}, "TestImageNano.json not found")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            workflow["56"]["inputs"]["image"] = uploaded_name
            workflow["63"]["inputs"]["text"] = prompt_text
            
            print(f"[Nano] Patched node 56 (image): {uploaded_name}")
            print(f"[Nano] Patched node 63 (prompt): {prompt_text[:60]}...")
            
            # 6. Submit
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Nano] Queued: {prompt_id[:8]}...")
            
            progress_bar.set_current_workflow(workflow)
            
            # Capture for callback
            obj_name = obj.name
            
            def on_nano_complete(success, result=None, error=None, workflow_type=None):
                print(f"[Nano] ============================================")
                print(f"[Nano] GENERATION COMPLETE")
                print(f"[Nano] ============================================")
                
                if not success:
                    print(f"[Nano] Failed: {error}")
                    return
                
                try:
                    images = extract_output_images(result)
                    if not images:
                        print(f"[Nano] No output images found")
                        return
                    
                    # Download the output image
                    nano_img_path = None
                    for img_info in images:
                        filename = img_info['filename']
                        save_path = workspace_setup.get_temp_directory(bpy.context) / f"nano_output_{int(time.time())}.png"
                        server_client.download_image(filename, str(save_path), img_info.get('subfolder', ''))
                        nano_img_path = save_path
                        print(f"[Nano] Downloaded: {save_path.name}")
                        break
                    
                    if not nano_img_path:
                        print(f"[Nano] No image downloaded")
                        return
                    
                    # Schedule material creation on main thread
                    def _create_material():
                        try:
                            # Auto-increment naming
                            nano_num = 0
                            while f"nano_{nano_num:03d}" in bpy.data.materials:
                                nano_num += 1
                            mat_name = f"nano_{nano_num:03d}"
                            
                            # Load image
                            img = bpy.data.images.load(str(nano_img_path))
                            img.name = f"{mat_name}.png"
                            img.pack()
                            
                            # Create material
                            mat = bpy.data.materials.new(name=mat_name)
                            mat.use_nodes = True
                            nodes = mat.node_tree.nodes
                            nodes.clear()
                            
                            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                            bsdf.location = (0, 0)
                            bsdf.inputs['Roughness'].default_value = 1.0
                            
                            tex = nodes.new(type='ShaderNodeTexImage')
                            tex.location = (-300, 0)
                            tex.image = img
                            
                            output = nodes.new(type='ShaderNodeOutputMaterial')
                            output.location = (300, 0)
                            
                            mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
                            mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                            
                            # Assign to object
                            target = bpy.data.objects.get(obj_name)
                            if target and target.type == 'MESH':
                                if target.data.materials:
                                    target.data.materials[0] = mat
                                else:
                                    target.data.materials.append(mat)
                                print(f"[Nano] Assigned {mat_name} to {target.name}")
                            
                            print(f"[Nano] ============================================")
                            print(f"[Nano] MATERIAL CREATED: {mat_name}")
                            print(f"[Nano] ============================================")
                            
                        except Exception as e:
                            print(f"[Nano] Material error: {e}")
                            import traceback
                            traceback.print_exc()
                        return None
                    
                    bpy.app.timers.register(_create_material, first_interval=0.1)
                    
                except Exception as e:
                    print(f"[Nano] Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 7. Poll
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_nano_complete,
                workflow_type='nano'
            )
            
            self.report({'INFO'}, "Nano generation submitted...")
            print(f"[Nano] Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Nano failed: {str(e)}")
            print(f"[Nano] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


# ================================================================
# NANO 3D GENERATION (POC)
# ================================================================

class WM_OT_Nano3DGenerate(bpy.types.Operator):
    """Generate 3D mesh from a nano-generated texture on a plane"""
    bl_idname = "style_engine.nano_3d_generate"
    bl_label = "Nano 3D"
    bl_description = "Send the plane's nano texture to generate a 3D mesh, positioned on the plane"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        import json
        import time
        import tempfile
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh with a nano texture")
            return {'CANCELLED'}
        
        if not obj.data.materials:
            self.report({'ERROR'}, "Selected object has no material")
            return {'CANCELLED'}
        
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Requires Server mode")
            return {'CANCELLED'}
        
        # Extract texture from material
        tex_image = None
        for mat in obj.data.materials:
            if mat and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        tex_image = node.image
                        break
                if tex_image:
                    break
        
        if not tex_image:
            self.report({'ERROR'}, "No texture found on selected object")
            return {'CANCELLED'}
        
        print(f"[Nano 3D] ============================================")
        print(f"[Nano 3D] STARTING 3D MESH FROM NANO TEXTURE")
        print(f"[Nano 3D] Source: {obj.name}, Texture: {tex_image.name}")
        print(f"[Nano 3D] ============================================")
        
        try:
            # Save texture to temp with unique name
            temp_dir = workspace_setup.get_temp_directory(context)
            tex_path = temp_dir / f"nano3d_input_{int(time.time())}.png"
            tex_image.save_render(str(tex_path))
            print(f"[Nano 3D] Extracted texture: {tex_path.name}")
            
            # Upload
            server_client = runcomfy_deployment.get_server_client()
            upload_resp = server_client.upload_image(str(tex_path), overwrite=True)
            uploaded_name = upload_resp.get("name", "")
            print(f"[Nano 3D] Uploaded: {uploaded_name}")
            
            # Load objectCreateObject.json
            addon_dir = Path(__file__).parent
            workflow_path = addon_dir / "workflows" / "Object" / "objectCreateObject.json"
            
            if not workflow_path.exists():
                self.report({'ERROR'}, "objectCreateObject.json not found")
                return {'CANCELLED'}
            
            with open(workflow_path, 'r') as f:
                workflow_json = json.load(f)
            
            # Patch workflow
            from . import pie_menu
            style_props = context.scene.style_engine_props
            quality = style_props.object_quality if hasattr(style_props, 'object_quality') else 'BALANCED'
            params = pie_menu.get_quality_params(quality)
            
            workflow_json["14"]["inputs"]["image"] = uploaded_name
            workflow_json["32"]["inputs"]["string"] = f"Nano3D_{int(time.time())}"
            workflow_json["37"]["inputs"]["seed"] = style_props.seed_value
            workflow_json["37"]["inputs"]["steps"] = params['mesh_steps']
            workflow_json["9"]["inputs"]["octree_resolution"] = params['octree_resolution']
            workflow_json["9"]["inputs"]["num_chunks"] = params['num_chunks']
            workflow_json["30"]["inputs"]["value"] = params['max_faces']
            
            output_name = workflow_json["32"]["inputs"]["string"]
            print(f"[Nano 3D] Quality: {quality}, Output: {output_name}")
            
            # Submit
            result = server_client.queue_prompt(workflow_json)
            prompt_id = result['prompt_id']
            print(f"[Nano 3D] Queued: {prompt_id[:8]}...")
            
            progress_bar.set_current_workflow(workflow_json)
            
            # Capture plane info for positioning
            plane_name = obj.name
            plane_location = obj.location.copy()
            plane_dimensions = obj.dimensions.copy()
            
            temp_mesh_dir = Path(tempfile.gettempdir()) / "styleengine_create"
            temp_mesh_dir.mkdir(parents=True, exist_ok=True)
            download_path = temp_mesh_dir / f"{output_name}.glb"
            
            def on_nano3d_complete(success, result=None, error=None, workflow_type=None):
                print(f"[Nano 3D] ============================================")
                print(f"[Nano 3D] GENERATION COMPLETE")
                print(f"[Nano 3D] ============================================")
                
                if not success:
                    print(f"[Nano 3D] Failed: {error}")
                    return
                
                outputs = result.get('outputs', {})
                output_filename = None
                
                if '44' in outputs:
                    node_44 = outputs['44']
                    if isinstance(node_44, dict) and 'gltf' in node_44:
                        files = node_44['gltf']
                        if files and isinstance(files, list) and len(files) > 0:
                            file_info = files[0]
                            output_filename = file_info.get('filename') if isinstance(file_info, dict) else file_info
                
                if not output_filename:
                    output_filename = f"{output_name}_00001_.glb"
                    print(f"[Nano 3D] Using constructed filename: {output_filename}")
                
                import threading
                
                def _download_thread():
                    try:
                        print(f"[Nano 3D] Downloading...")
                        dl_success = server_client.download_mesh(
                            output_filename, str(download_path),
                            file_type="output"
                        )
                        
                        if not dl_success:
                            print(f"[Nano 3D] Download failed")
                            return
                        
                        print(f"[Nano 3D] Downloaded: {download_path.name}")
                        
                        def _do_import():
                            try:
                                original_selected = list(bpy.context.selected_objects)
                                bpy.ops.import_scene.gltf(filepath=str(download_path))
                                newly_imported = [o for o in bpy.context.selected_objects if o not in original_selected]
                                
                                if newly_imported:
                                    new_obj = newly_imported[0]
                                    new_obj.name = f"Nano3D_{int(time.time())}"
                                    
                                    # Position on top of the source plane
                                    new_obj.location.x = plane_location.x
                                    new_obj.location.y = plane_location.y
                                    new_obj.location.z = plane_location.z
                                    
                                    workspace_setup.save_mesh_to_library(bpy.context, download_path, mesh_type='mesh')
                                    print(f"[Nano 3D] Imported: {new_obj.name} at plane position")
                                
                                print(f"[Nano 3D] ============================================")
                                print(f"[Nano 3D] COMPLETE")
                                print(f"[Nano 3D] ============================================")
                                
                            except Exception as e:
                                print(f"[Nano 3D] Import error: {e}")
                                import traceback
                                traceback.print_exc()
                            return None
                        
                        bpy.app.timers.register(_do_import, first_interval=0.1)
                        
                    except Exception as e:
                        print(f"[Nano 3D] Download error: {e}")
                        import traceback
                        traceback.print_exc()
                
                threading.Thread(target=_download_thread, daemon=True).start()
            
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_nano3d_complete,
                workflow_type='nano_3d'
            )
            
            self.report({'INFO'}, "Nano 3D generation submitted...")
            print(f"[Nano 3D] Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Nano 3D failed: {str(e)}")
            print(f"[Nano 3D] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


# ================================================================
# OMNI 3D GENERATION (Hunyuan3D-Omni via VM server)
# ================================================================

OMNI_PORT = 8190


def _has_pointcloud_exporter():
    """
    Point cloud export is handled internally via a pure-Python PLY writer —
    no external addon required.  Always returns True so the UI warning is
    never shown.
    """
    return True


def _write_ply_pointcloud(mesh_obj, out_path, precenter=True):
    """
    Write the world-space vertices of mesh_obj to a binary-little-endian PLY
    file at out_path.  No external addon required — pure Python + mathutils.
    Applies Blender Z-up → Y-up conversion: (x, z, -y).
    When precenter=True, subtracts the bounding-box centre before writing so
    the guide arrives at the server origin-centred (more robust normalisation).
    Returns out_path (Path) on success, raises on failure.
    """
    import struct
    from pathlib import Path

    verts = [mesh_obj.matrix_world @ v.co for v in mesh_obj.data.vertices]

    if precenter and verts:
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        zs = [v.z for v in verts]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        cz = (min(zs) + max(zs)) / 2
        from mathutils import Vector
        offset = Vector((cx, cy, cz))
        verts = [v - offset for v in verts]

    n = len(verts)
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "end_header\n"
    ).encode('ascii')

    out = Path(out_path)
    with out.open('wb') as f:
        f.write(header)
        for v in verts:
            # Blender Z-up → Y-up: X stays, Blender-Z → Y, Blender-Y → -Z
            f.write(struct.pack('<fff', v.x, v.z, -v.y))
    return out


def _write_ply_mesh(mesh_obj, out_path, yup=False, precenter=False):
    """
    Write the world-space geometry of mesh_obj (vertices + triangulated faces) to
    a binary-little-endian PLY file.

    yup=False  (default for voxel): coordinates kept in Blender Z-up space.
               omni_server.py's infer_voxel() applies a -90° X-axis rotation to
               convert Z-up → Y-up internally.
    yup=True   (for point-cloud-as-mesh): applies Blender Z-up → Y-up conversion
               (x, z, -y) so trimesh loads the data in the correct orientation
               without any extra server-side rotation.

    precenter=True: subtracts the bounding-box centre before writing so the guide
               arrives at the server already origin-centred.

    Returns out_path (Path) on success, raises on failure.
    """
    import struct
    from pathlib import Path

    mesh = mesh_obj.data
    mw = mesh_obj.matrix_world

    verts = [mw @ v.co for v in mesh.vertices]

    if precenter and verts:
        xs = [v.x for v in verts]
        ys = [v.y for v in verts]
        zs = [v.z for v in verts]
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        cz = (min(zs) + max(zs)) / 2
        from mathutils import Vector
        offset = Vector((cx, cy, cz))
        verts = [v - offset for v in verts]

    mesh.calc_loop_triangles()
    tris = [(lt.vertices[0], lt.vertices[1], lt.vertices[2]) for lt in mesh.loop_triangles]

    n_v = len(verts)
    n_f = len(tris)

    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {n_v}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        f"element face {n_f}\n"
        "property list uchar int vertex_indices\n"
        "end_header\n"
    ).encode('ascii')

    out = Path(out_path)
    with out.open('wb') as f:
        f.write(header)
        for v in verts:
            if yup:
                # Blender Z-up → Y-up: X stays, Blender-Z → Y, Blender-Y → -Z
                f.write(struct.pack('<fff', v.x, v.z, -v.y))
            else:
                f.write(struct.pack('<fff', v.x, v.y, v.z))
        for tri in tris:
            f.write(struct.pack('<Biii', 3, tri[0], tri[1], tri[2]))
    return out


def _export_mesh_as_voxel(obj, out_path, remesh_depth=5, precenter=True):
    """
    Duplicate obj, apply a smooth remesh to make the geometry watertight and
    uniform, then export as a full mesh PLY (vertices + faces) for Omni's voxel
    conditioning path.  The original object is never modified.

    remesh_depth: octree depth for the smooth remesh (1-9, lower = coarser/cleaner).
    precenter:    if True, subtract the bounding-box centre before writing.

    Returns out_path (Path) on success, or None on failure.
    """
    from pathlib import Path

    original_active = bpy.context.view_layer.objects.active
    original_selected = list(bpy.context.selected_objects)

    try:
        # --- 1. Duplicate the source mesh ---
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()
        temp_obj = bpy.context.active_object
        print(f"[Omni] Duplicated '{obj.name}' → '{temp_obj.name}' for voxel export")

        # --- 2. Smooth remesh for watertight, uniform geometry ---
        remesh_mod = temp_obj.modifiers.new(name="OmniRemesh", type='REMESH')
        if remesh_mod is None or remesh_mod.type != 'REMESH':
            raise RuntimeError("Failed to add REMESH modifier to duplicate")
        remesh_mod.mode = 'SMOOTH'
        remesh_mod.octree_depth = remesh_depth
        remesh_mod.use_remove_disconnected = True
        print(f"[Omni] Added Smooth Remesh (depth={remesh_depth}, watertight)")

        # --- 3. Apply all modifiers ---
        bpy.ops.object.convert(target='MESH')
        print(f"[Omni] Applied modifiers — {len(temp_obj.data.vertices)} vertices, "
              f"{len(temp_obj.data.polygons)} faces")

        # --- 4. Write mesh PLY (Z-up; server applies -90° X rotation to Y-up) ---
        ply_path = _write_ply_mesh(temp_obj, out_path, yup=False, precenter=precenter)
        print(f"[Omni] Exported voxel mesh: {ply_path.name} ({ply_path.stat().st_size // 1024} KB)")

        return ply_path

    except Exception as e:
        print(f"[Omni] Voxel mesh export error: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        try:
            temp_ref = bpy.context.active_object
            if temp_ref and temp_ref != obj:
                bpy.data.objects.remove(temp_ref, do_unlink=True)
        except Exception:
            pass
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            bpy.context.view_layer.objects.active = original_active
        except Exception:
            pass


def _export_mesh_as_pointcloud(obj, out_path, remesh_depth=5, as_mesh=True, precenter=True):
    """
    Duplicate obj, apply a smooth remesh for uniform surface sampling, then
    export the resulting geometry as a PLY point cloud or mesh file.

    remesh_depth: octree depth for the smooth remesh (1-9, lower = coarser/cleaner).
    as_mesh:      if True, write vertices + faces (mesh PLY) with Y-up conversion so
                  trimesh loads it as a Trimesh and normalize_mesh works correctly.
                  if False, write point-only PLY (legacy behaviour).
    precenter:    if True, subtract the bounding-box centre before writing.

    The original object is never modified.
    Returns out_path (Path) on success, or None on failure.
    """
    from pathlib import Path

    original_active = bpy.context.view_layer.objects.active
    original_selected = list(bpy.context.selected_objects)

    try:
        # --- 1. Duplicate the source mesh ---
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.duplicate()
        temp_obj = bpy.context.active_object
        print(f"[Omni] Duplicated '{obj.name}' → '{temp_obj.name}' for point cloud export")

        # --- 2. Smooth remesh for uniform vertex distribution ---
        # Use the data API (returns the modifier directly) to avoid index
        # confusion with pre-existing Geometry Nodes or other modifiers.
        remesh_mod = temp_obj.modifiers.new(name="OmniRemesh", type='REMESH')
        if remesh_mod is None or remesh_mod.type != 'REMESH':
            raise RuntimeError("Failed to add REMESH modifier to duplicate")
        remesh_mod.mode = 'SMOOTH'
        remesh_mod.octree_depth = remesh_depth
        remesh_mod.use_remove_disconnected = False
        print(f"[Omni] Added Smooth Remesh (depth={remesh_depth})")

        # --- 3. Apply all modifiers so we have a plain mesh ---
        bpy.ops.object.convert(target='MESH')
        print(f"[Omni] Applied modifiers — {len(temp_obj.data.vertices)} vertices")

        # --- 4. Write PLY: mesh (with faces + Y-up) or point-only ---
        if as_mesh:
            ply_path = _write_ply_mesh(temp_obj, out_path, yup=True, precenter=precenter)
            print(f"[Omni] Exported point cloud (mesh PLY, Y-up): "
                  f"{ply_path.name} ({ply_path.stat().st_size // 1024} KB)")
        else:
            ply_path = _write_ply_pointcloud(temp_obj, out_path, precenter=precenter)
            print(f"[Omni] Exported point cloud (point-only PLY): "
                  f"{ply_path.name} ({ply_path.stat().st_size // 1024} KB)")

        return ply_path

    except Exception as e:
        print(f"[Omni] Point cloud export error: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # --- 5. Always clean up the duplicate ---
        try:
            temp_ref = bpy.context.active_object
            if temp_ref and temp_ref != obj:
                bpy.data.objects.remove(temp_ref, do_unlink=True)
        except Exception:
            pass
        # Restore original selection state
        bpy.ops.object.select_all(action='DESELECT')
        for o in original_selected:
            try:
                o.select_set(True)
            except Exception:
                pass
        try:
            bpy.context.view_layer.objects.active = original_active
        except Exception:
            pass


def _get_omni_url():
    """Derive the Omni server URL from addon preferences (same host as ComfyUI, port 8190)."""
    from urllib.parse import urlparse
    try:
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        base_url = prefs.gcs_server_url
        if not base_url:
            return None
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.path.split('/')[0].split(':')[0]
        scheme = parsed.scheme if parsed.scheme else 'http'
        return f"{scheme}://{host}:{OMNI_PORT}"
    except Exception:
        return None


def _get_proportional_bbox(obj):
    """Extract a ratio-safe bounding box from a Blender mesh object.
    Returns [x_min, y_min, z_min, x_max, y_max, z_max] normalized to unit cube."""
    from mathutils import Vector
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    width = max(xs) - min(xs)
    depth = max(ys) - min(ys)
    height = max(zs) - min(zs)
    max_dim = max(width, depth, height, 0.001)
    hx = (width / max_dim) * 0.5
    hy = (depth / max_dim) * 0.5
    hz = (height / max_dim) * 0.5
    # Swap y↔z: Blender is Z-up, Omni/GLTF is Y-up
    # Blender Z (height) → Omni Y, Blender Y (depth) → Omni Z
    return [-hx, -hz, -hy, hx, hz, hy]


class WM_OT_OmniGenerate(bpy.types.Operator):
    """Generate 3D mesh using Hunyuan3D-Omni with bounding box from selected object"""
    bl_idname = "style_engine.omni_generate"
    bl_label = "Omni Mesh"
    bl_description = "Send current_ai.png + active mesh bounding box to Hunyuan3D-Omni for 3D generation"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.active_object and context.active_object.type == 'MESH')

    def execute(self, context):
        import json
        import time
        import uuid
        import threading
        import urllib.request
        import urllib.error
        from pathlib import Path
        from . import workspace_setup

        obj = context.active_object
        omni_url = _get_omni_url()
        if not omni_url:
            self.report({'ERROR'}, "Server URL not configured in preferences")
            return {'CANCELLED'}

        temp_dir = workspace_setup.get_temp_directory(context)
        image_path = temp_dir / "current_ai.png"

        if not image_path.exists():
            self.report({'ERROR'}, "No AI image found — generate an image first (Generate Image button)")
            return {'CANCELLED'}

        print(f"[Omni] ============================================")
        print(f"[Omni] STARTING OMNI 3D GENERATION")
        print(f"[Omni] Server: {omni_url}")
        print(f"[Omni] Proxy object: {obj.name}")
        print(f"[Omni] ============================================")

        # Extract bbox
        bbox = _get_proportional_bbox(obj)
        print(f"[Omni] Bbox (normalized): {[f'{v:.3f}' for v in bbox]}")

        # Capture proxy bbox for post-import matching
        from mathutils import Vector
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        zs = [c.z for c in corners]
        proxy_bbox_min = Vector((min(xs), min(ys), min(zs)))
        proxy_bbox_max = Vector((max(xs), max(ys), max(zs)))
        proxy_bbox_center = (proxy_bbox_min + proxy_bbox_max) / 2
        proxy_max_dim = max(proxy_bbox_max.x - proxy_bbox_min.x,
                            proxy_bbox_max.y - proxy_bbox_min.y,
                            proxy_bbox_max.z - proxy_bbox_min.z, 0.001)
        proxy_name = obj.name
        print(f"[Omni] Proxy bbox center: {proxy_bbox_center}, max_dim: {proxy_max_dim:.3f}")

        # Read new Omni settings from scene properties
        props = context.scene.style_engine_props
        omni_control       = getattr(props, 'omni_control_type',    'BBOX')
        omni_mc_res        = getattr(props, 'omni_mc_res',           '512')
        omni_guidance      = getattr(props, 'omni_guidance_scale',    4.5)
        omni_use_ema       = getattr(props, 'omni_use_ema',          False)
        omni_flashvdm      = getattr(props, 'omni_flashvdm',         False)
        omni_remesh_depth  = getattr(props, 'omni_remesh_depth',      5)
        omni_pc_as_mesh    = getattr(props, 'omni_pc_as_mesh',        True)
        omni_precenter     = getattr(props, 'omni_precenter',         True)

        print(f"[Omni] Control mode: {omni_control} | Guidance: {omni_guidance:.1f} | "
              f"EMA: {omni_use_ema} | FlashVDM: {omni_flashvdm}")
        if omni_control in ('POINT', 'VOXEL'):
            print(f"[Omni] Export — remesh_depth: {omni_remesh_depth} | "
                  f"pc_as_mesh: {omni_pc_as_mesh} | precenter: {omni_precenter}")

        # --- Guide file: point cloud or voxel mesh ---
        guide_ply_data = None
        if omni_control == 'POINT':
            ply_path = temp_dir / f"omni_pc_{uuid.uuid4().hex[:8]}.ply"
            result_path = _export_mesh_as_pointcloud(
                obj, ply_path,
                remesh_depth=omni_remesh_depth,
                as_mesh=omni_pc_as_mesh,
                precenter=omni_precenter,
            )
            if result_path is None:
                self.report({'ERROR'}, "Point cloud export failed — check console for details")
                return {'CANCELLED'}
            with open(str(result_path), 'rb') as f:
                guide_ply_data = f.read()
            print(f"[Omni] Point cloud ready: {result_path.name} ({len(guide_ply_data) / 1024:.1f} KB)")

        elif omni_control == 'VOXEL':
            ply_path = temp_dir / f"omni_vox_{uuid.uuid4().hex[:8]}.ply"
            result_path = _export_mesh_as_voxel(
                obj, ply_path,
                remesh_depth=omni_remesh_depth,
                precenter=omni_precenter,
            )
            if result_path is None:
                self.report({'ERROR'}, "Voxel mesh export failed — check console for details")
                return {'CANCELLED'}
            with open(str(result_path), 'rb') as f:
                guide_ply_data = f.read()
            print(f"[Omni] Voxel mesh ready: {result_path.name} ({len(guide_ply_data) / 1024:.1f} KB)")

        # Read image
        with open(str(image_path), 'rb') as f:
            image_data = f.read()

        # Build multipart POST
        boundary = f"----OmniBoundary{uuid.uuid4().hex}"
        body_parts = []

        # Image file field
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(f'Content-Disposition: form-data; name="image"; filename="current_ai.png"'.encode())
        body_parts.append(b'Content-Type: image/png')
        body_parts.append(b'')
        body_parts.append(image_data)

        # Spatial conditioning — bbox fields OR guide file (point cloud / voxel mesh)
        if omni_control == 'BBOX':
            field_names = ['x_min', 'y_min', 'z_min', 'x_max', 'y_max', 'z_max']
            for name, val in zip(field_names, bbox):
                body_parts.append(f'--{boundary}'.encode())
                body_parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
                body_parts.append(b'')
                body_parts.append(str(val).encode())
        elif omni_control in ('POINT', 'VOXEL') and guide_ply_data is not None:
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(b'Content-Disposition: form-data; name="guide_file"; filename="guide.ply"')
            body_parts.append(b'Content-Type: application/octet-stream')
            body_parts.append(b'')
            body_parts.append(guide_ply_data)

        # control_type scalar field
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="control_type"')
        body_parts.append(b'')
        body_parts.append(omni_control.lower().encode())

        # mc_res scalar field
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="mc_res"')
        body_parts.append(b'')
        body_parts.append(omni_mc_res.encode())

        # guidance_scale scalar field
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="guidance_scale"')
        body_parts.append(b'')
        body_parts.append(f"{omni_guidance:.1f}".encode())

        # use_ema flag
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="use_ema"')
        body_parts.append(b'')
        body_parts.append(b'true' if omni_use_ema else b'false')

        # flashvdm flag
        body_parts.append(f'--{boundary}'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="flashvdm"')
        body_parts.append(b'')
        body_parts.append(b'true' if omni_flashvdm else b'false')

        body_parts.append(f'--{boundary}--'.encode())
        body_parts.append(b'')
        request_body = b'\r\n'.join(body_parts)

        # Submit to Omni server
        try:
            req = urllib.request.Request(
                f"{omni_url}/generate",
                data=request_body,
                headers={
                    'Content-Type': f'multipart/form-data; boundary={boundary}',
                    'User-Agent': 'StyleEngine-Blender/1.0'
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
            job_id = resp_data.get('job_id')
            if not job_id:
                self.report({'ERROR'}, "Omni server returned no job_id")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reach Omni server: {e}")
            print(f"[Omni] Connection error: {e}")
            return {'CANCELLED'}

        print(f"[Omni] Submitted job: {job_id[:8]}...")
        self.report({'INFO'}, "Omni 3D generation submitted... (watch progress bar)")

        # Polling + download via bpy.app.timers
        captured = {
            'job_id': job_id,
            'omni_url': omni_url,
            'proxy_bbox_center': proxy_bbox_center,
            'proxy_max_dim': proxy_max_dim,
            'proxy_name': proxy_name,
            'start_time': time.time(),
        }

        def _poll_omni():
            job_id = captured['job_id']
            url = captured['omni_url']
            elapsed = time.time() - captured['start_time']

            if elapsed > 600:
                print(f"[Omni] Timeout after {elapsed:.0f}s")
                return None

            try:
                req = urllib.request.Request(f"{url}/status/{job_id}")
                req.add_header('User-Agent', 'StyleEngine-Blender/1.0')
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                print(f"[Omni] Poll error: {e}")
                return 4.0

            status = data.get('status', 'unknown')
            progress = data.get('progress', 0)

            if status == 'completed':
                print(f"[Omni] Generation complete! Downloading...")

                def _download_thread():
                    try:
                        dl_req = urllib.request.Request(f"{url}/download/{job_id}")
                        dl_req.add_header('User-Agent', 'StyleEngine-Blender/1.0')
                        with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
                            glb_data = dl_resp.read()

                        dl_path = Path(workspace_setup.get_temp_directory(bpy.context)) / f"omni_{job_id[:8]}.glb"
                        with open(str(dl_path), 'wb') as f:
                            f.write(glb_data)

                        print(f"[Omni] Downloaded: {dl_path.name} ({len(glb_data) / 1024:.1f} KB)")

                        _import_retries = [0]
                        _MAX_RETRIES = 20  # 20 × 0.2s = 4s max wait

                        def _do_import():
                            try:
                                from mathutils import Vector

                                # Ensure object mode before any operations
                                if bpy.context.mode != 'OBJECT':
                                    bpy.ops.object.mode_set(mode='OBJECT')

                                original_set = set(bpy.data.objects)
                                bpy.ops.import_scene.gltf(filepath=str(dl_path))
                                newly = [o for o in bpy.data.objects if o not in original_set]

                                if not newly:
                                    print(f"[Omni] Import succeeded but no new objects found")
                                    return None

                                # Separate mesh objects from empties/other types
                                mesh_objs = [o for o in newly if o.type == 'MESH']
                                non_mesh = [o for o in newly if o.type != 'MESH']

                                # Unparent mesh objects, keeping world transform
                                for mo in mesh_objs:
                                    if mo.parent:
                                        world_mat = mo.matrix_world.copy()
                                        mo.parent = None
                                        mo.matrix_world = world_mat

                                # Delete empties/non-mesh imports (GLTF scene roots)
                                for nm in non_mesh:
                                    bpy.data.objects.remove(nm, do_unlink=True)

                                if not mesh_objs:
                                    print(f"[Omni] No mesh objects found after import")
                                    return None

                                # Apply transforms so bound_box reflects real geometry size
                                bpy.ops.object.select_all(action='DESELECT')
                                for mo in mesh_objs:
                                    mo.select_set(True)
                                bpy.context.view_layer.objects.active = mesh_objs[0]
                                bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

                                # Measure imported mesh world-space bounding box
                                all_corners = []
                                for mo in mesh_objs:
                                    all_corners += [mo.matrix_world @ Vector(c) for c in mo.bound_box]
                                imp_xs = [c.x for c in all_corners]
                                imp_ys = [c.y for c in all_corners]
                                imp_zs = [c.z for c in all_corners]
                                imp_max_dim = max(max(imp_xs)-min(imp_xs),
                                                 max(imp_ys)-min(imp_ys),
                                                 max(imp_zs)-min(imp_zs), 0.001)
                                imp_center = Vector((
                                    (min(imp_xs) + max(imp_xs)) / 2,
                                    (min(imp_ys) + max(imp_ys)) / 2,
                                    (min(imp_zs) + max(imp_zs)) / 2,
                                ))

                                # Scale: match proxy's largest dimension
                                scale_factor = captured['proxy_max_dim'] / imp_max_dim
                                proxy_center = captured['proxy_bbox_center']

                                mesh_name = f"Omni_Mesh_{int(time.time())}"
                                for i, mo in enumerate(mesh_objs):
                                    mo.name = mesh_name if i == 0 else f"{mesh_name}_{i}"
                                    mo.scale = mo.scale * scale_factor
                                    # Shift so imported bbox center lands on proxy bbox center
                                    mo.location = mo.location + (proxy_center - imp_center * scale_factor)

                                print(f"[Omni] Scale factor: {scale_factor:.4f} (proxy {captured['proxy_max_dim']:.3f}m / imported {imp_max_dim:.3f}m)")

                                # Hide proxy
                                proxy = bpy.data.objects.get(captured['proxy_name'])
                                if proxy:
                                    proxy.hide_set(True)

                                workspace_setup.save_mesh_to_library(bpy.context, dl_path, mesh_type='mesh')
                                print(f"[Omni] Imported: {mesh_name} ({len(mesh_objs)} mesh(es)), centered at {proxy_center}")
                                print(f"[Omni] ============================================")
                                print(f"[Omni] OMNI 3D COMPLETE")
                                print(f"[Omni] ============================================")

                            except RuntimeError as e:
                                # Blender is mid-redraw — retry after a short delay
                                if "drawing/rendering" in str(e) or "can't modify blend data" in str(e):
                                    _import_retries[0] += 1
                                    if _import_retries[0] <= _MAX_RETRIES:
                                        print(f"[Omni] Blend data busy (redraw), retrying... ({_import_retries[0]}/{_MAX_RETRIES})")
                                        return 0.2  # reschedule timer
                                    else:
                                        print(f"[Omni] ❌ Import abandoned after {_MAX_RETRIES} retries — Blender stayed busy too long")
                                else:
                                    print(f"[Omni] Import error: {e}")
                                    import traceback
                                    traceback.print_exc()

                            except Exception as e:
                                print(f"[Omni] Import error: {e}")
                                import traceback
                                traceback.print_exc()

                            return None  # unregister timer

                        bpy.app.timers.register(_do_import, first_interval=0.5)

                    except Exception as e:
                        print(f"[Omni] Download error: {e}")
                        import traceback
                        traceback.print_exc()

                threading.Thread(target=_download_thread, daemon=True).start()
                return None

            elif status == 'failed':
                print(f"[Omni] Generation failed on server")
                return None

            return 4.0

        bpy.app.timers.register(_poll_omni, first_interval=4.0)
        print(f"[Omni] Polling started (every 4s, timeout 10min)")

        return {'FINISHED'}


# ================================================================
# TRELLIS2 — Image → 3D  (generate)  and  Mesh → Retexture
# ================================================================

TRELLIS_POLL_INTERVAL  = 2.0   # seconds between /status polls
TRELLIS_TIMEOUT        = 900.0 # 15 minutes hard timeout

PART_PORT              = 7860  # Hunyuan3D-Part Gradio service


def _get_part_url():
    """Derive the Hunyuan3D-Part URL from addon preferences (same host, port 7860)."""
    from urllib.parse import urlparse
    try:
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        base_url = prefs.gcs_server_url
        if not base_url:
            return None
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.path.split('/')[0].split(':')[0]
        scheme = parsed.scheme if parsed.scheme else 'http'
        return f"{scheme}://{host}:{PART_PORT}"
    except Exception:
        return None


def _get_trellis_url():
    """Derive the TRELLIS2 base URL from addon preferences (same host, port 8195)."""
    from urllib.parse import urlparse
    try:
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        base_url = prefs.gcs_server_url
        if not base_url:
            return None
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.path.split('/')[0].split(':')[0]
        scheme = parsed.scheme if parsed.scheme else 'http'
        return f"{scheme}://{host}:8195"
    except Exception:
        return None


def _image_has_alpha(image_path):
    """Return True if the PNG at image_path has a non-opaque alpha channel.
    Uses Blender's own Image API to avoid PIL dependency."""
    try:
        import struct, zlib
        # Fastest check: read PNG IHDR to get colour type
        with open(str(image_path), 'rb') as f:
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n':
                return False
            f.read(4)   # IHDR length
            f.read(4)   # 'IHDR'
            f.read(4)   # width
            f.read(4)   # height
            f.read(1)   # bit depth
            color_type = struct.unpack('B', f.read(1))[0]
        # colour type 4 = greyscale+alpha, 6 = RGBA
        return color_type in (4, 6)
    except Exception:
        return False


def _run_rembg_on_comfyui(context, input_path, output_path):
    """Submit current_ai.png to ComfyUI's UtilsImageRB.json (InspyrenetRembg),
    poll until done, download the RGBA result to output_path.
    Returns True on success, False on failure.
    This call BLOCKS the calling thread (must be called from a background thread)."""
    import json as _json
    import time as _time
    import urllib.request as _url
    from pathlib import Path
    from . import runcomfy_deployment, runcomfy_server_client

    addon_dir = Path(__file__).parent
    wf_path   = addon_dir / "workflows" / "Image" / "UtilsImageRB.json"
    if not wf_path.exists():
        print(f"[TRELLIS] UtilsImageRB.json not found at {wf_path}")
        return False

    with open(str(wf_path), 'r') as f:
        workflow = _json.load(f)

    try:
        server_client = runcomfy_deployment.get_server_client()

        # Upload input image
        upload_resp   = server_client.upload_image(str(input_path), overwrite=True)
        uploaded_name = upload_resp['name']

        # Patch workflow node 1 (LoadImage)
        workflow["1"]["inputs"]["image"] = uploaded_name

        # Queue
        q_resp    = server_client.queue_prompt(workflow)
        prompt_id = q_resp.get('prompt_id')
        if not prompt_id:
            print("[TRELLIS] UtilsImageRB: no prompt_id returned")
            return False

        # Poll history
        comfy_url = f"{runcomfy_deployment.get_server_client().server_url}"
        deadline  = _time.time() + 120
        while _time.time() < deadline:
            _time.sleep(1.5)
            hist_resp = _url.urlopen(f"{comfy_url}/history/{prompt_id}", timeout=5)
            hist      = _json.loads(hist_resp.read())
            if prompt_id in hist:
                entry = hist[prompt_id]
                outputs = entry.get('outputs', {})
                # Node "3" is SaveImage → outputs
                for node_id, node_out in outputs.items():
                    imgs = node_out.get('images', [])
                    if imgs:
                        img_info  = imgs[0]
                        img_fname = img_info['filename']
                        subfolder = img_info.get('subfolder', '')
                        folder    = img_info.get('type', 'output')
                        dl_url    = (f"{comfy_url}/view?filename={img_fname}"
                                     f"&subfolder={subfolder}&type={folder}")
                        dl_req    = _url.Request(dl_url)
                        with _url.urlopen(dl_req, timeout=30) as dl_resp:
                            rgba_data = dl_resp.read()
                        with open(str(output_path), 'wb') as out_f:
                            out_f.write(rgba_data)
                        print(f"[TRELLIS] RembG done: {output_path.name} "
                              f"({len(rgba_data)//1024} KB)")
                        return True
        print("[TRELLIS] UtilsImageRB timed out after 120s")
        return False
    except Exception as e:
        print(f"[TRELLIS] UtilsImageRB error: {e}")
        import traceback; traceback.print_exc()
        return False


class WM_OT_TrellisGenerate(bpy.types.Operator):
    """Generate a textured 3D mesh with TRELLIS2 from current_ai.png"""
    bl_idname  = "style_engine.trellis_generate"
    bl_label   = "Generate 3D (TRELLIS2)"
    bl_description = (
        "Send current_ai.png to the TRELLIS2 server to generate a fully textured 3D mesh. "
        "An active mesh object is used as the size reference. "
        "If Remove BG is on, background is stripped via ComfyUI first."
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only requires current_ai.png — mesh is optional (used for scale matching only)
        try:
            from . import workspace_setup
            td = workspace_setup.get_temp_directory(context)
            return (td / "current_ai.png").exists()
        except Exception:
            return True  # fail-open: let execute() surface the real error

    def execute(self, context):
        import time
        import threading
        from pathlib import Path
        from . import workspace_setup, trellis_client

        trellis_url = _get_trellis_url()
        if not trellis_url:
            self.report({'ERROR'}, "Server URL not configured in preferences")
            return {'CANCELLED'}

        props    = context.scene.style_engine_props
        temp_dir = workspace_setup.get_temp_directory(context)
        src_img  = temp_dir / "current_ai.png"

        if not src_img.exists():
            self.report({'ERROR'}, "No AI image found — generate an image first")
            return {'CANCELLED'}

        # ── Optionally capture proxy bbox for post-import scale matching ─
        # If no active mesh is selected the result is imported at native scale,
        # centred at the world origin — still fully useful.
        from mathutils import Vector
        obj = context.active_object if (context.active_object
                                        and context.active_object.type == 'MESH') else None
        if obj:
            corners  = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
            proxy_min     = Vector((min(xs), min(ys), min(zs)))
            proxy_max_v   = Vector((max(xs), max(ys), max(zs)))
            proxy_center  = (proxy_min + proxy_max_v) / 2
            proxy_max_dim = max(proxy_max_v.x - proxy_min.x,
                                proxy_max_v.y - proxy_min.y,
                                proxy_max_v.z - proxy_min.z, 0.001)
            proxy_name    = obj.name
        else:
            proxy_center  = Vector((0, 0, 0))
            proxy_max_dim = None  # signals "no scaling" in _do_import
            proxy_name    = None

        # ── Read TRELLIS params ──────────────────────────────────────────
        quality      = getattr(props, 'trellis_quality',      '1024_cascade')
        steps        = getattr(props, 'trellis_steps',        12)
        guidance     = getattr(props, 'trellis_guidance',     7.5)
        tex_size     = int(getattr(props, 'trellis_texture_size', '4096'))
        remove_bg    = getattr(props, 'trellis_remove_bg',    True)
        seed         = getattr(props, 'seed_value',           42)
        decimation   = getattr(props, 'trellis_decimation',   300000)

        print(f"[TRELLIS] ============================================")
        print(f"[TRELLIS] STARTING TRELLIS2 3D GENERATION")
        print(f"[TRELLIS] Server: {trellis_url}")
        print(f"[TRELLIS] Quality: {quality} | Steps: {steps} | Guidance: {guidance}")
        print(f"[TRELLIS] Remove BG: {remove_bg} | Texture: {tex_size}px | Max Polys: {decimation}")
        if proxy_name:
            print(f"[TRELLIS] Proxy: {proxy_name} (max_dim {proxy_max_dim:.3f} m)")
        else:
            print(f"[TRELLIS] No proxy mesh — importing at native scale")
        print(f"[TRELLIS] ============================================")

        self.report({'INFO'}, "TRELLIS2 3D generation started…")

        captured = {
            'trellis_url':    trellis_url,
            'proxy_name':     proxy_name,
            'proxy_center':   proxy_center,
            'proxy_max_dim':  proxy_max_dim,
            'temp_dir':       temp_dir,
            'start_time':     time.time(),
            'job_id':         None,
            'error':          None,
        }

        def _submit_thread():
            try:
                input_img = src_img

                # Step 1 (optional): remove background via ComfyUI
                if remove_bg and not _image_has_alpha(src_img):
                    rgba_path = temp_dir / "trellis_rgba.png"
                    print("[TRELLIS] Removing background via UtilsImageRB…")
                    ok = _run_rembg_on_comfyui(bpy.context, src_img, rgba_path)
                    if ok:
                        input_img = rgba_path
                        print("[TRELLIS] Background removed ✓")
                    else:
                        print("[TRELLIS] ⚠️  RembG failed, submitting without BG removal")
                else:
                    if _image_has_alpha(src_img):
                        print("[TRELLIS] Image already has alpha channel, skipping rembg")
                    else:
                        print("[TRELLIS] Remove BG disabled, submitting as-is")

                # Step 2: submit to TRELLIS2
                job_id = trellis_client.submit_generate(
                    trellis_url,
                    str(input_img),
                    pipeline_type      = quality,
                    seed               = seed,
                    steps              = steps,
                    guidance           = guidance,
                    texture_size       = tex_size,
                    decimation_target  = decimation,
                )
                print(f"[TRELLIS] Job submitted: {job_id[:8]}…")
                captured['job_id'] = job_id

            except Exception as e:
                print(f"[TRELLIS] Submit error: {e}")
                import traceback; traceback.print_exc()
                captured['error'] = str(e)

        threading.Thread(target=_submit_thread, daemon=True).start()

        # ── Poll with bpy.app.timers ─────────────────────────────────────
        def _poll():
            from . import trellis_client as tc

            if captured['error']:
                print(f"[TRELLIS] Generation failed: {captured['error']}")
                return None

            if captured['job_id'] is None:
                return TRELLIS_POLL_INTERVAL  # still submitting

            elapsed = time.time() - captured['start_time']
            if elapsed > TRELLIS_TIMEOUT:
                print(f"[TRELLIS] Timed out after {elapsed:.0f}s")
                return None

            try:
                status_data = tc.poll_status(captured['trellis_url'], captured['job_id'])
            except Exception as e:
                print(f"[TRELLIS] Poll error: {e}")
                return TRELLIS_POLL_INTERVAL

            status   = status_data.get('status',   'unknown')
            progress = status_data.get('progress', 0.0)
            message  = status_data.get('message',  '')
            print(f"[TRELLIS] [{int(progress*100):3d}%] {message}")

            if status == 'done':
                print(f"[TRELLIS] Done in {status_data.get('gen_time', '?'):.1f}s "
                      f"— downloading GLB…")

                def _download_and_import():
                    try:
                        job_id   = captured['job_id']
                        dl_path  = captured['temp_dir'] / f"trellis_{job_id[:8]}.glb"
                        nbytes   = tc.download_glb(captured['trellis_url'], job_id,
                                                    str(dl_path), index=0)
                        print(f"[TRELLIS] Downloaded: {dl_path.name} ({nbytes//1024} KB)")
                        _import_retries = [0]
                        _MAX_RETRIES    = 60  # 60 × 2s = 120s window for large meshes

                        def _do_import():
                            try:
                                if bpy.context.mode != 'OBJECT':
                                    bpy.ops.object.mode_set(mode='OBJECT')

                                original_set = set(bpy.data.objects)
                                bpy.ops.import_scene.gltf(filepath=str(dl_path))
                                newly = [o for o in bpy.data.objects if o not in original_set]

                                if not newly:
                                    print("[TRELLIS] Import succeeded but no new objects")
                                    return None

                                mesh_objs = [o for o in newly if o.type == 'MESH']
                                non_mesh  = [o for o in newly if o.type != 'MESH']

                                # Unparent meshes, keeping world transform
                                for mo in mesh_objs:
                                    if mo.parent:
                                        wm = mo.matrix_world.copy()
                                        mo.parent = None
                                        mo.matrix_world = wm

                                # Remove GLTF scene-root empties
                                for nm in non_mesh:
                                    bpy.data.objects.remove(nm, do_unlink=True)

                                if not mesh_objs:
                                    print("[TRELLIS] No mesh objects after import")
                                    return None

                                # Apply transforms so bound_box reflects real geo
                                bpy.ops.object.select_all(action='DESELECT')
                                for mo in mesh_objs:
                                    mo.select_set(True)
                                bpy.context.view_layer.objects.active = mesh_objs[0]
                                bpy.ops.object.transform_apply(
                                    location=False, rotation=True, scale=True)

                                # Measure imported bbox
                                all_corners = []
                                for mo in mesh_objs:
                                    all_corners += [mo.matrix_world @ Vector(c)
                                                    for c in mo.bound_box]
                                ix = [c.x for c in all_corners]
                                iy = [c.y for c in all_corners]
                                iz = [c.z for c in all_corners]
                                imp_max_dim = max(max(ix)-min(ix),
                                                  max(iy)-min(iy),
                                                  max(iz)-min(iz), 0.001)
                                imp_center  = Vector((
                                    (min(ix)+max(ix))/2,
                                    (min(iy)+max(iy))/2,
                                    (min(iz)+max(iz))/2,
                                ))

                                # Scale + translate to match proxy (optional)
                                mesh_name = f"Trellis_{job_id[:8]}"
                                if captured['proxy_max_dim'] is not None:
                                    scale_factor = captured['proxy_max_dim'] / imp_max_dim
                                    proxy_center = captured['proxy_center']
                                    for i, mo in enumerate(mesh_objs):
                                        mo.name     = mesh_name if i == 0 else f"{mesh_name}_{i}"
                                        mo.scale    = mo.scale * scale_factor
                                        mo.location = (mo.location
                                                       + (proxy_center - imp_center * scale_factor))
                                    print(f"[TRELLIS] Scale: {scale_factor:.4f} "
                                          f"(proxy {captured['proxy_max_dim']:.3f}m / "
                                          f"imported {imp_max_dim:.3f}m)")
                                    # Hide proxy
                                    proxy = bpy.data.objects.get(captured['proxy_name'])
                                    if proxy:
                                        proxy.hide_set(True)
                                else:
                                    for i, mo in enumerate(mesh_objs):
                                        mo.name = mesh_name if i == 0 else f"{mesh_name}_{i}"
                                    print(f"[TRELLIS] No proxy — imported at native scale")

                                from . import workspace_setup as ws
                                ws.save_mesh_to_library(bpy.context, dl_path,
                                                        mesh_type='textured')
                                print(f"[TRELLIS] ============================================")
                                print(f"[TRELLIS] TRELLIS2 3D COMPLETE: {mesh_name}")
                                print(f"[TRELLIS] ============================================")

                            except RuntimeError as e:
                                if ("drawing/rendering" in str(e)
                                        or "can't modify blend data" in str(e)):
                                    _import_retries[0] += 1
                                    if _import_retries[0] <= _MAX_RETRIES:
                                        print(f"[TRELLIS] Blend data busy, retry "
                                              f"{_import_retries[0]}/{_MAX_RETRIES}")
                                        return 2.0
                                    else:
                                        print("[TRELLIS] ❌ Import abandoned after retries")
                                else:
                                    print(f"[TRELLIS] Import error: {e}")
                                    import traceback; traceback.print_exc()
                            except Exception as e:
                                print(f"[TRELLIS] Import error: {e}")
                                import traceback; traceback.print_exc()
                            return None

                        bpy.app.timers.register(_do_import, first_interval=2.0)

                    except Exception as e:
                        print(f"[TRELLIS] Download error: {e}")
                        import traceback; traceback.print_exc()

                threading.Thread(target=_download_and_import, daemon=True).start()
                return None

            elif status == 'failed':
                err = status_data.get('error', 'unknown error')
                print(f"[TRELLIS] Server reported failure: {err}")
                return None

            return TRELLIS_POLL_INTERVAL

        bpy.app.timers.register(_poll, first_interval=TRELLIS_POLL_INTERVAL)
        return {'FINISHED'}


class WM_OT_TrellisRetexture(bpy.types.Operator):
    """Retexture the active mesh using TRELLIS2 and current_ai.png as reference"""
    bl_idname  = "style_engine.trellis_retexture"
    bl_label   = "Retexture Mesh (TRELLIS2)"
    bl_description = (
        "Export the active mesh as a temp GLB and submit it with current_ai.png "
        "to TRELLIS2 /retexture. The result is a new separately imported mesh "
        "with freshly generated PBR textures."
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.active_object and context.active_object.type == 'MESH')

    def execute(self, context):
        import time
        import threading
        from pathlib import Path
        from . import workspace_setup, trellis_client

        trellis_url = _get_trellis_url()
        if not trellis_url:
            self.report({'ERROR'}, "Server URL not configured in preferences")
            return {'CANCELLED'}

        obj      = context.active_object
        props    = context.scene.style_engine_props
        temp_dir = workspace_setup.get_temp_directory(context)
        src_img  = temp_dir / "current_ai.png"

        if not src_img.exists():
            self.report({'ERROR'}, "No AI image found — generate or upload an image first")
            return {'CANCELLED'}

        # ── Capture proxy info for post-import positioning ───────────────
        from mathutils import Vector
        corners      = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        proxy_min    = Vector((min(xs), min(ys), min(zs)))
        proxy_max    = Vector((max(xs), max(ys), max(zs)))
        proxy_center = (proxy_min + proxy_max) / 2
        proxy_max_dim = max(proxy_max.x - proxy_min.x,
                            proxy_max.y - proxy_min.y,
                            proxy_max.z - proxy_min.z, 0.001)
        proxy_name   = obj.name

        # ── Export active mesh to temp GLB ───────────────────────────────
        import uuid
        mesh_glb = temp_dir / f"trellis_input_{uuid.uuid4().hex[:8]}.glb"

        # Deselect all, select only the target mesh
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        try:
            bpy.ops.export_scene.gltf(
                filepath        = str(mesh_glb),
                export_format   = 'GLB',
                use_selection   = True,
                export_apply    = True,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Mesh export failed: {e}")
            return {'CANCELLED'}

        if not mesh_glb.exists():
            self.report({'ERROR'}, "Mesh export produced no file")
            return {'CANCELLED'}

        print(f"[TRELLIS] Exported mesh: {mesh_glb.name} "
              f"({mesh_glb.stat().st_size // 1024} KB)")

        # ── Read retexture params ────────────────────────────────────────
        tex_steps      = getattr(props, 'trellis_tex_steps',      12)
        tex_guidance   = getattr(props, 'trellis_tex_guidance',    1.0)
        tex_resolution = int(getattr(props, 'trellis_tex_resolution', '1024'))
        tex_size       = int(getattr(props, 'trellis_texture_size',   '2048'))
        seed           = getattr(props, 'seed_value',              0)

        print(f"[TRELLIS] ============================================")
        print(f"[TRELLIS] STARTING TRELLIS2 RETEXTURE")
        print(f"[TRELLIS] Server: {trellis_url}")
        print(f"[TRELLIS] Tex res: {tex_resolution} | Atlas: {tex_size}px | "
              f"Steps: {tex_steps} | Guidance: {tex_guidance}")
        print(f"[TRELLIS] Proxy: {proxy_name}")
        print(f"[TRELLIS] ============================================")

        self.report({'INFO'}, "TRELLIS2 retexture started…")

        captured = {
            'trellis_url':   trellis_url,
            'proxy_name':    proxy_name,
            'proxy_center':  proxy_center,
            'proxy_max_dim': proxy_max_dim,
            'temp_dir':      temp_dir,
            'start_time':    time.time(),
            'job_id':        None,
            'error':         None,
        }

        def _submit_thread():
            try:
                job_id = trellis_client.submit_retexture(
                    trellis_url,
                    str(src_img),
                    str(mesh_glb),
                    seed                 = seed,
                    tex_resolution       = tex_resolution,
                    texture_size         = tex_size,
                    tex_steps            = tex_steps,
                    tex_guidance         = tex_guidance,
                )
                print(f"[TRELLIS] Retexture job: {job_id[:8]}…")
                captured['job_id'] = job_id
            except Exception as e:
                print(f"[TRELLIS] Retexture submit error: {e}")
                import traceback; traceback.print_exc()
                captured['error'] = str(e)

        threading.Thread(target=_submit_thread, daemon=True).start()

        # ── Poll ─────────────────────────────────────────────────────────
        def _poll():
            from . import trellis_client as tc

            if captured['error']:
                print(f"[TRELLIS] Retexture failed: {captured['error']}")
                return None

            if captured['job_id'] is None:
                return TRELLIS_POLL_INTERVAL

            elapsed = time.time() - captured['start_time']
            if elapsed > TRELLIS_TIMEOUT:
                print(f"[TRELLIS] Retexture timed out after {elapsed:.0f}s")
                return None

            try:
                status_data = tc.poll_status(captured['trellis_url'], captured['job_id'])
            except Exception as e:
                print(f"[TRELLIS] Retexture poll error: {e}")
                return TRELLIS_POLL_INTERVAL

            status   = status_data.get('status',   'unknown')
            progress = status_data.get('progress', 0.0)
            message  = status_data.get('message',  '')
            print(f"[TRELLIS-RT] [{int(progress*100):3d}%] {message}")

            if status == 'done':
                print(f"[TRELLIS] Retexture done in "
                      f"{status_data.get('gen_time','?'):.1f}s — downloading…")

                def _download_and_import():
                    try:
                        job_id  = captured['job_id']
                        dl_path = captured['temp_dir'] / f"trellis_rt_{job_id[:8]}.glb"
                        nbytes  = tc.download_glb(captured['trellis_url'], job_id,
                                                   str(dl_path), index=0)
                        print(f"[TRELLIS] Downloaded: {dl_path.name} ({nbytes//1024} KB)")

                        _import_retries = [0]
                        _MAX_RETRIES    = 60  # 60 × 2s = 120s window for large meshes

                        def _do_import():
                            try:
                                if bpy.context.mode != 'OBJECT':
                                    bpy.ops.object.mode_set(mode='OBJECT')

                                original_set = set(bpy.data.objects)
                                bpy.ops.import_scene.gltf(filepath=str(dl_path))
                                newly = [o for o in bpy.data.objects
                                         if o not in original_set]
                                if not newly:
                                    print("[TRELLIS] Retexture: no new objects after import")
                                    return None

                                mesh_objs = [o for o in newly if o.type == 'MESH']
                                non_mesh  = [o for o in newly if o.type != 'MESH']

                                for mo in mesh_objs:
                                    if mo.parent:
                                        wm = mo.matrix_world.copy()
                                        mo.parent = None
                                        mo.matrix_world = wm
                                for nm in non_mesh:
                                    bpy.data.objects.remove(nm, do_unlink=True)

                                if not mesh_objs:
                                    print("[TRELLIS] Retexture: no mesh after filtering")
                                    return None

                                bpy.ops.object.select_all(action='DESELECT')
                                for mo in mesh_objs:
                                    mo.select_set(True)
                                bpy.context.view_layer.objects.active = mesh_objs[0]
                                bpy.ops.object.transform_apply(
                                    location=False, rotation=True, scale=True)

                                # Scale + position same as generate
                                all_corners = []
                                for mo in mesh_objs:
                                    all_corners += [mo.matrix_world @ Vector(c)
                                                    for c in mo.bound_box]
                                ix = [c.x for c in all_corners]
                                iy = [c.y for c in all_corners]
                                iz = [c.z for c in all_corners]
                                imp_max_dim = max(max(ix)-min(ix),
                                                  max(iy)-min(iy),
                                                  max(iz)-min(iz), 0.001)
                                imp_center  = Vector((
                                    (min(ix)+max(ix))/2,
                                    (min(iy)+max(iy))/2,
                                    (min(iz)+max(iz))/2,
                                ))
                                scale_factor = captured['proxy_max_dim'] / imp_max_dim
                                proxy_center = captured['proxy_center']
                                mesh_name    = f"Trellis_RT_{job_id[:8]}"
                                for i, mo in enumerate(mesh_objs):
                                    mo.name    = mesh_name if i == 0 else f"{mesh_name}_{i}"
                                    mo.scale   = mo.scale * scale_factor
                                    mo.location = (mo.location
                                                   + (proxy_center - imp_center * scale_factor))

                                # Hide proxy
                                proxy = bpy.data.objects.get(captured['proxy_name'])
                                if proxy:
                                    proxy.hide_set(True)

                                from . import workspace_setup as ws
                                ws.save_mesh_to_library(bpy.context, dl_path,
                                                        mesh_type='uv_textured')
                                print(f"[TRELLIS] Retexture complete: {mesh_name}")

                            except RuntimeError as e:
                                if ("drawing/rendering" in str(e)
                                        or "can't modify blend data" in str(e)):
                                    _import_retries[0] += 1
                                    if _import_retries[0] <= _MAX_RETRIES:
                                        print(f"[TRELLIS] Busy, retry "
                                              f"{_import_retries[0]}/{_MAX_RETRIES}")
                                        return 2.0
                                    else:
                                        print("[TRELLIS] ❌ Retexture import abandoned")
                                else:
                                    print(f"[TRELLIS] Retexture import error: {e}")
                                    import traceback; traceback.print_exc()
                            except Exception as e:
                                print(f"[TRELLIS] Retexture import error: {e}")
                                import traceback; traceback.print_exc()
                            return None

                        bpy.app.timers.register(_do_import, first_interval=2.0)

                    except Exception as e:
                        print(f"[TRELLIS] Retexture download error: {e}")
                        import traceback; traceback.print_exc()

                threading.Thread(target=_download_and_import, daemon=True).start()
                return None

            elif status == 'failed':
                err = status_data.get('error', 'unknown error')
                print(f"[TRELLIS] Retexture server failure: {err}")
                return None

            return TRELLIS_POLL_INTERVAL

        bpy.app.timers.register(_poll, first_interval=TRELLIS_POLL_INTERVAL)
        return {'FINISHED'}


# ================================================================
# Hunyuan3D-Part — Segment Mesh
# ================================================================

class WM_OT_SegmentMesh(bpy.types.Operator):
    """Segment the active mesh into parts using Hunyuan3D-Part (P3-SAM + XPart)"""
    bl_idname  = "style_engine.segment_mesh"
    bl_label   = "Segment Mesh"
    bl_description = (
        "Export the active mesh and send it to the Hunyuan3D-Part service. "
        "Returns a reassembled GLB with individual parts reconstructed by XPart. "
        "Requires an active mesh object. Pipeline takes 2–5 minutes."
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(context.active_object and context.active_object.type == 'MESH')

    def execute(self, context):
        import time
        import threading
        import json
        import uuid
        import urllib.request
        import urllib.error
        from pathlib import Path
        from . import workspace_setup

        part_url = _get_part_url()
        if not part_url:
            self.report({'ERROR'}, "Server URL not configured in preferences")
            return {'CANCELLED'}

        obj      = context.active_object
        props    = context.scene.style_engine_props
        temp_dir = workspace_setup.get_temp_directory(context)

        # ── Capture proxy bbox for post-import scaling ───────────────────
        from mathutils import Vector
        corners   = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        proxy_min     = Vector((min(xs), min(ys), min(zs)))
        proxy_max_v   = Vector((max(xs), max(ys), max(zs)))
        proxy_center  = (proxy_min + proxy_max_v) / 2
        proxy_max_dim = max(proxy_max_v.x - proxy_min.x,
                            proxy_max_v.y - proxy_min.y,
                            proxy_max_v.z - proxy_min.z, 0.001)
        proxy_name    = obj.name

        # ── Prepare mesh: merge vertices, keep largest island, export GLB ──
        token    = uuid.uuid4().hex[:8]
        obj_path = temp_dir / f"part_input_{token}.glb"

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        try:
            # Work on a temporary copy so the original is untouched
            bpy.ops.object.duplicate(linked=False)
            work_obj = context.active_object
            work_obj.name = f"_part_prep_{token}"

            # Enter edit mode for cleanup
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')

            # Find the largest part by face count among the separated pieces
            candidates = [o for o in context.selected_objects if o.type == 'MESH']
            if candidates:
                largest = max(candidates, key=lambda o: len(o.data.polygons))
                # Remove everything except the largest
                for c in candidates:
                    if c is not largest:
                        bpy.data.objects.remove(c, do_unlink=True)
                # Select only the largest for export
                bpy.ops.object.select_all(action='DESELECT')
                largest.select_set(True)
                context.view_layer.objects.active = largest
            else:
                largest = work_obj

            print(f"[Part] Cleaned mesh: {len(largest.data.polygons)} faces "
                  f"(merge + keep largest island)")

            # Export as GLB (geometry only, no textures)
            bpy.ops.export_scene.gltf(
                filepath=str(obj_path),
                export_format='GLB',
                use_selection=True,
                export_materials='NONE',
                export_apply=True,
            )

            # Clean up the temporary object
            bpy.data.objects.remove(largest, do_unlink=True)

        except Exception as e:
            # Clean up any leftover temp objects on failure
            for o in list(bpy.data.objects):
                if o.name.startswith(f"_part_prep_{token}"):
                    bpy.data.objects.remove(o, do_unlink=True)
            self.report({'ERROR'}, f"Mesh export failed: {e}")
            import traceback; traceback.print_exc()
            return {'CANCELLED'}

        if not obj_path.exists():
            self.report({'ERROR'}, "Mesh export produced no file")
            return {'CANCELLED'}

        print(f"[Part] Exported: {obj_path.name} ({obj_path.stat().st_size // 1024} KB)")

        # ── Read params ──────────────────────────────────────────────────
        point_num  = getattr(props, 'part_point_num',  50000)
        prompt_num = getattr(props, 'part_prompt_num', 128)
        seed       = getattr(props, 'seed_value',      42)

        print(f"[Part] ============================================")
        print(f"[Part] STARTING Hunyuan3D-Part SEGMENTATION")
        print(f"[Part] Server:  {part_url}")
        print(f"[Part] Proxy:   {proxy_name} (max_dim {proxy_max_dim:.3f} m)")
        print(f"[Part] Params:  point_num={point_num}, prompt_num={prompt_num}, seed={seed}")
        print(f"[Part] ============================================")

        self.report({'INFO'}, "Hunyuan3D-Part segmentation started (2–5 min)…")

        captured = {
            'part_url':      part_url,
            'proxy_name':    proxy_name,
            'proxy_center':  proxy_center,
            'proxy_max_dim': proxy_max_dim,
            'temp_dir':      temp_dir,
            'token':         token,
            'start_time':    time.time(),
            'done':          False,
            'error':         None,
            'dl_path':       None,
        }

        # ----------------------------------------------------------------
        # Background thread: upload → predict → download
        # ----------------------------------------------------------------
        _UA = {"User-Agent": "StyleEngine-Blender/1.0"}

        def _try_request(url, data=None, headers=None, method="GET", timeout=60,
                         soft_errors=(404,)):
            """Fire an HTTP request.

            Returns (response_bytes, status_code).
            For codes in *soft_errors* returns (error_body_or_None, code) instead
            of raising.  All other HTTP errors are raised.
            """
            hdrs = dict(_UA)
            if headers:
                hdrs.update(headers)
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read(), resp.getcode()
            except urllib.error.HTTPError as e:
                if e.code in soft_errors:
                    try:
                        err_body = e.read()
                    except Exception:
                        err_body = None
                    return err_body, e.code
                raise

        def _parse_sse_result(sse_bytes):
            """Parse a Gradio SSE stream and return the final 'complete' data list."""
            event_type = None
            all_events = []
            for raw_line in sse_bytes.split(b"\n"):
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    payload = line.split(":", 1)[1].strip()
                    all_events.append((event_type, payload))
                    print(f"[Part] SSE event={event_type} data={payload[:300]}")
                    if event_type == "error":
                        # Gradio sends data: null or data: "error message"
                        if payload and payload != "null":
                            raise RuntimeError(f"Gradio pipeline error: {payload}")
                        raise RuntimeError(
                            "Gradio pipeline returned an error (no detail). "
                            "Check the Hunyuan3D-Part server/container logs for "
                            "the Python traceback."
                        )
                    if event_type == "complete":
                        return json.loads(payload)
            print(f"[Part] SSE stream ended without 'complete'. "
                  f"Events received: {[e[0] for e in all_events]}")
            return None

        def _segment_thread():
            try:
                orig_name = obj_path.name
                boundary  = f"----PartUpload{token}"

                # ── Step 1: upload mesh ──────────────────────────────────
                with open(str(obj_path), 'rb') as f:
                    file_data = f.read()

                upload_body = (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="files"; filename="{orig_name}"\r\n'
                    f"Content-Type: application/octet-stream\r\n\r\n"
                ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

                upload_ct = {"Content-Type": f"multipart/form-data; boundary={boundary}"}

                file_input = None
                for upload_url in [
                    f"{part_url}/gradio_api/upload",
                    f"{part_url}/upload",
                    f"{part_url}/api/upload",
                ]:
                    body, status = _try_request(upload_url, data=upload_body,
                                                headers=upload_ct, method="POST",
                                                soft_errors=(404, 405))
                    if status in (404, 405):
                        print(f"[Part] {upload_url} -> {status}, trying next...")
                        continue
                    remote_paths = json.loads(body.decode())
                    first = remote_paths[0]
                    remote_path = first.get("path", first) if isinstance(first, dict) else first
                    file_input = {
                        "path": remote_path,
                        "orig_name": orig_name,
                        "meta": {"_type": "gradio.FileData"},
                    }
                    print(f"[Part] Uploaded via {upload_url} -> {remote_path}")
                    break

                if file_input is None:
                    import base64 as _b64
                    b64 = _b64.b64encode(file_data).decode()
                    file_input = {
                        "name": orig_name,
                        "data": f"data:application/octet-stream;base64,{b64}",
                        "meta": {"_type": "gradio.FileData"},
                    }
                    print(f"[Part] No upload endpoint found -- embedding as base64 "
                          f"({len(b64) // 1024} KB)")

                # ── Step 2: call /run_pipeline (single endpoint, full pipeline) ──
                # Parameters (from /gradio_api/info):
                #   mesh_file, mode, point_num, prompt_num, prompt_bs,
                #   threshold, post_process, num_inference_steps,
                #   octree_resolution, guidance_scale, dual_guidance_scale,
                #   eta, mc_level, num_chunks, seed
                # Returns 5 outputs: assembled GLB, exploded GLB, bbox GLB,
                #   aabb.npy, status markdown

                json_ct = {"Content-Type": "application/json"}
                last_server_error = None

                pipeline_data = [
                    file_input,             # mesh_file
                    "Full Pipeline",        # mode
                    point_num,              # point_num (default 50000)
                    prompt_num,             # prompt_num (default 128)
                    16,                     # prompt_bs
                    0.95,                   # threshold (NMS IoU merge)
                    False,                  # post_process (merge pass)
                    50,                     # num_inference_steps
                    512,                    # octree_resolution
                    -1.0,                   # guidance_scale (-1 = disabled)
                    10.5,                   # dual_guidance_scale
                    0.0,                    # eta (0 = deterministic)
                    -0.001953125,           # mc_level (isosurface)
                    400000,                 # num_chunks
                    seed,                   # seed
                ]
                payload = json.dumps({"data": pipeline_data}).encode()

                result = None
                for prefix in ["", "/gradio_api"]:
                    call_url = f"{part_url}{prefix}/call/run_pipeline"
                    body, status = _try_request(
                        call_url, data=payload,
                        headers=json_ct, method="POST", timeout=30,
                        soft_errors=(404, 405, 422, 500, 502, 503),
                    )
                    if status == 404:
                        print(f"[Part] {call_url} not found, trying next...")
                        continue
                    if status in (405, 422, 500, 502, 503):
                        snippet = (body or b"")[:500].decode("utf-8", errors="replace")
                        print(f"[Part] {call_url} -> HTTP {status}: {snippet}")
                        last_server_error = f"HTTP {status} from {call_url}: {snippet}"
                        continue

                    call_resp = json.loads(body.decode())
                    event_id = call_resp.get("event_id")
                    if not event_id:
                        print(f"[Part] No event_id from {call_url}: {call_resp}")
                        continue

                    print(f"[Part] Pipeline running via {call_url} "
                          f"(event_id={event_id}, may take 2-5 min)...")

                    sse_url = f"{call_url}/{event_id}"
                    sse_body, sse_status = _try_request(
                        sse_url, timeout=600,
                        soft_errors=(404,),
                    )
                    if sse_status == 404:
                        print(f"[Part] SSE {sse_url} returned 404")
                        continue

                    parsed = _parse_sse_result(sse_body)
                    if parsed is not None:
                        result = parsed
                        break

                if result is None:
                    detail = last_server_error or "run_pipeline endpoint not found"
                    raise RuntimeError(
                        f"Gradio run_pipeline failed. {detail}. "
                        "Check Hunyuan3D-Part server logs."
                    )

                # result = [assembled_glb, exploded_glb, bbox_glb, aabb_npy, status_md]
                outputs = result
                print(f"[Part] Pipeline done. {len(outputs)} outputs returned.")
                if len(outputs) >= 5 and isinstance(outputs[4], str):
                    print(f"[Part] Status: {outputs[4][:200]}")

                # ── Step 3: download assembled.glb (data[0]) ────────────
                if not outputs or outputs[0] is None:
                    raise RuntimeError("No assembled output returned from pipeline")

                out0 = outputs[0]
                print(f"[Part] Output[0] type: {type(out0).__name__} | value: {str(out0)[:120]}")

                if isinstance(out0, dict):
                    direct_url = out0.get("url") or out0.get("value")
                    remote_path_out = out0.get("path", "")
                    if direct_url and direct_url.startswith("http"):
                        dl_url = direct_url
                    elif remote_path_out:
                        dl_url = f"{part_url}/gradio_api/file={remote_path_out}"
                    else:
                        raise RuntimeError(f"Cannot extract download URL from: {out0}")
                elif isinstance(out0, str):
                    if out0.startswith("http"):
                        dl_url = out0
                    else:
                        dl_url = f"{part_url}/gradio_api/file={out0}"
                else:
                    raise RuntimeError(f"Unexpected output format: {out0}")

                # Try download; fall back to legacy /file= path
                print(f"[Part] Downloading from: {dl_url}")
                glb_data, dl_status = _try_request(dl_url, timeout=120,
                                                    soft_errors=(404,))
                if dl_status == 404 and "/gradio_api/file=" in dl_url:
                    legacy_dl = dl_url.replace("/gradio_api/file=", "/file=")
                    print(f"[Part] Retrying legacy path: {legacy_dl}")
                    glb_data, dl_status = _try_request(legacy_dl, timeout=120,
                                                        soft_errors=(404,))
                if dl_status == 404 or glb_data is None:
                    raise RuntimeError(f"Failed to download assembled GLB (HTTP {dl_status})")

                dl_path = captured['temp_dir'] / f"part_{token}.glb"
                with open(str(dl_path), 'wb') as f:
                    f.write(glb_data)
                print(f"[Part] Downloaded: {dl_path.name} ({len(glb_data) // 1024} KB)")

                captured['dl_path'] = dl_path
                captured['done']    = True

            except Exception as e:
                print(f"[Part] Pipeline error: {e}")
                import traceback; traceback.print_exc()
                captured['error'] = str(e)

        threading.Thread(target=_segment_thread, daemon=True).start()

        # ----------------------------------------------------------------
        # Timer: poll thread completion, then import
        # ----------------------------------------------------------------
        def _wait_and_import():
            if captured['error']:
                print(f"[Part] Segmentation failed: {captured['error']}")
                return None

            if not captured['done']:
                elapsed = time.time() - captured['start_time']
                if elapsed > 600:  # 10-minute hard timeout
                    print(f"[Part] Timed out after {elapsed:.0f}s")
                    return None
                return 2.0  # still running — check again in 2s

            # Thread done — import in main thread
            dl_path = captured['dl_path']
            _import_retries = [0]
            _MAX_RETRIES    = 20

            def _do_import():
                try:
                    if bpy.context.mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')

                    original_set = set(bpy.data.objects)
                    bpy.ops.import_scene.gltf(filepath=str(dl_path))
                    newly = [o for o in bpy.data.objects if o not in original_set]

                    if not newly:
                        print("[Part] Import succeeded but no new objects found")
                        return None

                    mesh_objs = [o for o in newly if o.type == 'MESH']
                    non_mesh  = [o for o in newly if o.type != 'MESH']

                    for mo in mesh_objs:
                        if mo.parent:
                            wm = mo.matrix_world.copy()
                            mo.parent = None
                            mo.matrix_world = wm
                    for nm in non_mesh:
                        bpy.data.objects.remove(nm, do_unlink=True)

                    if not mesh_objs:
                        print("[Part] No mesh objects after import")
                        return None

                    bpy.ops.object.select_all(action='DESELECT')
                    for mo in mesh_objs:
                        mo.select_set(True)
                    bpy.context.view_layer.objects.active = mesh_objs[0]
                    bpy.ops.object.transform_apply(
                        location=False, rotation=True, scale=True)

                    # Measure imported bbox
                    all_corners = []
                    for mo in mesh_objs:
                        all_corners += [mo.matrix_world @ Vector(c)
                                        for c in mo.bound_box]
                    ix = [c.x for c in all_corners]
                    iy = [c.y for c in all_corners]
                    iz = [c.z for c in all_corners]
                    imp_max_dim = max(max(ix)-min(ix),
                                     max(iy)-min(iy),
                                     max(iz)-min(iz), 0.001)
                    imp_center  = Vector((
                        (min(ix)+max(ix))/2,
                        (min(iy)+max(iy))/2,
                        (min(iz)+max(iz))/2,
                    ))

                    scale_factor = captured['proxy_max_dim'] / imp_max_dim
                    proxy_center = captured['proxy_center']
                    base_name    = f"Part_{captured['token']}"
                    for i, mo in enumerate(mesh_objs):
                        mo.name    = base_name if i == 0 else f"{base_name}_{i}"
                        mo.scale   = mo.scale * scale_factor
                        mo.location = (mo.location
                                       + (proxy_center - imp_center * scale_factor))

                    print(f"[Part] Scale: {scale_factor:.4f} "
                          f"(proxy {captured['proxy_max_dim']:.3f}m / "
                          f"imported {imp_max_dim:.3f}m)")

                    # Hide proxy (the original mesh is preserved, just hidden)
                    proxy = bpy.data.objects.get(captured['proxy_name'])
                    if proxy:
                        proxy.hide_set(True)

                    from . import workspace_setup as ws
                    ws.save_mesh_to_library(bpy.context, dl_path, mesh_type='mesh')

                    print(f"[Part] ============================================")
                    print(f"[Part] SEGMENTATION COMPLETE: {base_name}")
                    print(f"[Part] ============================================")

                except RuntimeError as e:
                    if ("drawing/rendering" in str(e)
                            or "can't modify blend data" in str(e)):
                        _import_retries[0] += 1
                        if _import_retries[0] <= _MAX_RETRIES:
                            print(f"[Part] Blend data busy, retry "
                                  f"{_import_retries[0]}/{_MAX_RETRIES}")
                            return 0.2
                        else:
                            print("[Part] ❌ Import abandoned after retries")
                    else:
                        print(f"[Part] Import error: {e}")
                        import traceback; traceback.print_exc()
                except Exception as e:
                    print(f"[Part] Import error: {e}")
                    import traceback; traceback.print_exc()
                return None

            bpy.app.timers.register(_do_import, first_interval=0.5)
            return None  # stop the outer wait timer

        bpy.app.timers.register(_wait_and_import, first_interval=2.0)
        return {'FINISHED'}


class WM_OT_OmniBBoxDebug(bpy.types.Operator):
    """Calculate and visualise the bounding box that would be sent to Hunyuan3D-Omni"""
    bl_idname = "style_engine.omni_bbox_debug"
    bl_label = "Calculate BBox"
    bl_description = "Print normalised Omni bbox to console and create a wireframe cube showing the actual bounding box"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def execute(self, context):
        from mathutils import Vector

        obj = context.active_object

        # --- World-space corners ---
        corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        zs = [c.z for c in corners]

        # Actual world dimensions
        w = max(xs) - min(xs)
        d = max(ys) - min(ys)
        h = max(zs) - min(zs)
        center = Vector(((min(xs)+max(xs))/2, (min(ys)+max(ys))/2, (min(zs)+max(zs))/2))

        # Normalised bbox (what Omni receives)
        max_dim = max(w, d, h, 0.001)
        hx = (w / max_dim) * 0.5
        hy = (d / max_dim) * 0.5
        hz = (h / max_dim) * 0.5
        norm_bbox = [-hx, -hy, -hz, hx, hy, hz]

        print(f"[BBox Debug] =============================================")
        print(f"[BBox Debug] Object: {obj.name}")
        print(f"[BBox Debug] World dimensions: W={w:.4f}  D={d:.4f}  H={h:.4f}")
        print(f"[BBox Debug] World center: ({center.x:.4f}, {center.y:.4f}, {center.z:.4f})")
        print(f"[BBox Debug] Largest dimension: {max_dim:.4f}")
        print(f"[BBox Debug] Normalised bbox sent to Omni:")
        print(f"[BBox Debug]   x_min={norm_bbox[0]:.4f}  y_min={norm_bbox[1]:.4f}  z_min={norm_bbox[2]:.4f}")
        print(f"[BBox Debug]   x_max={norm_bbox[3]:.4f}  y_max={norm_bbox[4]:.4f}  z_max={norm_bbox[5]:.4f}")
        print(f"[BBox Debug] =============================================")

        self.report({'INFO'}, f"BBox: [{', '.join(f'{v:.3f}' for v in norm_bbox)}]  — see console for details")

        # --- Create wireframe cube matching the actual world bbox ---
        cube_name = f"BBox_{obj.name}"
        # Remove existing debug cube for this object if present
        existing = bpy.data.objects.get(cube_name)
        if existing:
            bpy.data.objects.remove(existing, do_unlink=True)

        bpy.ops.mesh.primitive_cube_add(size=1, location=center)
        cube = context.active_object
        cube.name = cube_name
        cube.scale = (w, d, h)

        # Wireframe display — no fill, just edges
        cube.display_type = 'WIRE'

        # Make it non-renderable and non-selectable-in-viewport so it doesn't get in the way
        cube.hide_render = True
        cube.hide_select = True

        # Re-select original object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        print(f"[BBox Debug] Wireframe cube created: '{cube_name}' at {center}")
        return {'FINISHED'}


# ================================================================
# PATCH TEXTURE OPERATORS
# ================================================================

class WM_OT_TogglePatchCamera(bpy.types.Operator):
    """Toggle patch camera for fixing edge textures"""
    bl_idname = "style_engine.toggle_patch_camera"
    bl_label = "Toggle Patch Camera"
    bl_description = "Spawn/remove a patch camera to fix poorly projected edge textures"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        props = context.scene.style_engine_props
        
        if props.patch_mode_active:
            # ── TOGGLE OFF: Kill patch camera ──
            # Exit edit mode if active
            if context.object and context.object.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # Restore ai_camera BEFORE removing patch_camera
            # (removing first can leave scene.camera as None momentarily)
            ai_cam = bpy.data.objects.get("ai_camera")
            if ai_cam:
                context.scene.camera = ai_cam
            
            patch_cam = bpy.data.objects.get("patch_camera")
            if patch_cam:
                bpy.data.objects.remove(patch_cam, do_unlink=True)
                print(f"[Patch] Removed patch_camera")
            
            # Unlock camera from viewport
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.lock_camera = False
                            if space.region_3d.view_perspective == 'CAMERA':
                                space.region_3d.view_perspective = 'PERSP'
                            break
                    break
            
            props.patch_mode_active = False
            self.report({'INFO'}, "Patch mode disabled")
            
        else:
            # ── TOGGLE ON: Spawn patch camera at current view ──
            obj = context.active_object
            if not obj or obj.type != 'MESH':
                self.report({'ERROR'}, "Select a mesh with a projected texture first")
                return {'CANCELLED'}
            
            has_iteration = any(m and m.name.startswith('iteration_') for m in obj.data.materials)
            if not has_iteration:
                self.report({'ERROR'}, "No iteration material found. Project a texture first.")
                return {'CANCELLED'}
            
            # Remove old patch camera if it exists
            old_cam = bpy.data.objects.get("patch_camera")
            if old_cam:
                bpy.data.objects.remove(old_cam, do_unlink=True)
            
            # Create patch camera
            cam_data = bpy.data.cameras.new("patch_camera")
            patch_cam = bpy.data.objects.new("patch_camera", cam_data)
            context.collection.objects.link(patch_cam)
            
            # Copy lens from ai_camera for consistent FOV
            ai_cam = bpy.data.objects.get("ai_camera")
            if ai_cam:
                cam_data.lens = ai_cam.data.lens
            
            # Position at current viewport
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            rv3d = space.region_3d
                            patch_cam.matrix_world = rv3d.view_matrix.inverted()
                            break
                    break
            
            # Add TRACK_TO constraint targeting the mesh
            track = patch_cam.constraints.new(type='TRACK_TO')
            track.target = obj
            track.track_axis = 'TRACK_NEGATIVE_Z'
            track.up_axis = 'UP_Y'
            
            # Set as scene camera and lock viewport to it
            context.scene.camera = patch_cam
            
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.region_3d.view_perspective = 'CAMERA'
                            space.lock_camera = True
                            break
                    break
            
            # Enter edit mode with face selection
            context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')
            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.mesh.select_all(action='DESELECT')
            
            props.patch_mode_active = True
            self.report({'INFO'}, "Select faces to patch, then click Apply Patch")
            print(f"[Patch] patch_camera spawned, tracking {obj.name}, edit mode (face select)")
        
        return {'FINISHED'}


class WM_OT_ApplyPatch(bpy.types.Operator):
    """Generate and apply a texture patch from the current patch camera angle"""
    bl_idname = "style_engine.apply_patch"
    bl_label = "Apply Patch"
    bl_description = "Generate texture from patch camera angle and project onto uncovered faces"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import json
        import re
        import time
        from pathlib import Path
        from mathutils import Vector
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        from .runcomfy_server_client import extract_output_images
        
        props = context.scene.style_engine_props
        
        # Validate
        if not props.patch_mode_active:
            self.report({'ERROR'}, "Patch mode is not active")
            return {'CANCELLED'}
        
        patch_cam = bpy.data.objects.get("patch_camera")
        if not patch_cam:
            self.report({'ERROR'}, "Patch camera not found")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh selected")
            return {'CANCELLED'}
        
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Patch requires Server mode")
            return {'CANCELLED'}
        
        # Find the iteration material (for style reference)
        iteration_mat = None
        iter_num = "000"
        for mat in obj.data.materials:
            if mat and mat.name.startswith('iteration_'):
                m = re.match(r'iteration_(\d+)', mat.name)
                if m:
                    num = int(m.group(1))
                    iteration_mat = mat
                    iter_num = m.group(1)
        
        if not iteration_mat:
            self.report({'ERROR'}, "No iteration material found on object")
            return {'CANCELLED'}
        
        print(f"[Patch] ============================================")
        print(f"[Patch] APPLYING PATCH from patch_camera")
        print(f"[Patch] Object: {obj.name}, Iteration: {iteration_mat.name}")
        print(f"[Patch] ============================================")
        
        try:
            # 1. Capture selected faces while still in edit mode
            import bmesh
            
            selected_face_indices = []
            if obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(obj.data)
                selected_face_indices = [f.index for f in bm.faces if f.select]
                bm.free()
            
            if not selected_face_indices:
                self.report({'ERROR'}, "No faces selected. Select faces to patch first.")
                return {'CANCELLED'}
            
            print(f"[Patch] Captured {len(selected_face_indices)} selected faces")
            
            # Exit edit mode for rendering
            if obj.mode == 'EDIT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            # 2. Store patch camera matrix BEFORE killing it
            patch_cam_matrix = patch_cam.matrix_world.copy()
            obj_name = obj.name
            
            # Force constraint evaluation to get final world matrix
            context.view_layer.update()
            patch_cam_matrix = patch_cam.matrix_world.copy()
            
            # 3. Render solid from patch camera
            original_engine = context.scene.render.engine
            original_file_format = context.scene.render.image_settings.file_format
            original_scene_camera = context.scene.camera
            
            # Disable ai_camera background images
            ai_cam = bpy.data.objects.get("ai_camera")
            bg_states = []
            if ai_cam:
                for bg in ai_cam.data.background_images:
                    bg_states.append(bg.show_background_image)
                    bg.show_background_image = False
            
            context.scene.camera = patch_cam
            context.scene.render.engine = 'BLENDER_WORKBENCH'
            context.scene.display.shading.light = 'FLAT'
            context.scene.render.image_settings.file_format = 'PNG'
            
            temp_dir = workspace_setup.get_temp_directory(context)
            patch_render_path = temp_dir / f"patch_render_{iter_num}_{int(time.time())}.png"
            context.scene.render.filepath = str(patch_render_path)
            bpy.ops.render.render(write_still=True)
            
            print(f"[Patch] Rendered solid view: {patch_render_path.name}")
            
            # Restore render settings
            context.scene.render.engine = original_engine
            context.scene.render.image_settings.file_format = original_file_format
            if ai_cam:
                for i, bg in enumerate(ai_cam.data.background_images):
                    if i < len(bg_states):
                        bg.show_background_image = bg_states[i]
            
            # 3. Extract iteration texture as style reference
            ref_img_path = None
            for node in iteration_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    ref_img_path = temp_dir / f"patch_ref_{iter_num}_{int(time.time())}.png"
                    node.image.save_render(str(ref_img_path))
                    print(f"[Patch] Extracted style reference from {iteration_mat.name}")
                    break
            
            if not ref_img_path:
                ref_img_path = temp_dir / "current_ai.png"
                print(f"[Patch] Using current_ai.png as style reference")
            
            # 4. Upload both images
            server_client = runcomfy_deployment.get_server_client()
            
            upload_render = server_client.upload_image(str(patch_render_path), overwrite=True)
            uploaded_render = upload_render.get("name", "")
            print(f"[Patch] Uploaded render: {uploaded_render}")
            
            upload_ref = server_client.upload_image(str(ref_img_path), overwrite=True)
            uploaded_ref = upload_ref.get("name", "")
            print(f"[Patch] Uploaded reference: {uploaded_ref}")
            
            # 5. Load and patch objectPatch.json
            workflow_file = Path(__file__).parent / "workflows" / "Object" / "objectPatch.json"
            if not workflow_file.exists():
                self.report({'ERROR'}, "objectPatch.json not found")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            # Patch with session settings (same as Image.json patching in workspace_setup.py)
            workflow["15"]["inputs"]["image"] = uploaded_render
            workflow["138"]["inputs"]["image"] = uploaded_ref
            workflow["25"]["inputs"]["value"] = props.global_prompt
            workflow["7"]["inputs"]["text"] = props.negative_prompt or ""
            workflow["3"]["inputs"]["seed"] = props.seed_value
            workflow["40"]["inputs"]["value"] = props.silhouette_influence
            workflow["41"]["inputs"]["value"] = props.depth_influence
            
            # Denoise (same scaling as Image.json)
            influence_value = props.texture_influence
            scaled_influence = influence_value * 0.7
            denoise_value = 1.0 - scaled_influence
            workflow["135"]["inputs"]["value"] = denoise_value
            
            workflow["145"]["inputs"]["value"] = props.steps
            
            # LoRa patching (same logic as workspace_setup.py)
            if "136" in workflow:
                if props.lora_enabled and props.lora_name != 'NONE':
                    workflow["136"]["inputs"]["lora_name"] = props.lora_name
                    workflow["136"]["inputs"]["strength_model"] = props.lora_strength_model
                    workflow["136"]["inputs"]["strength_clip"] = props.lora_strength_model
                else:
                    workflow["136"]["inputs"]["strength_model"] = 0.0
                    workflow["136"]["inputs"]["strength_clip"] = 0.0
            
            if "34" in workflow:
                if props.lora2_enabled and props.lora2_name != 'NONE':
                    workflow["34"]["inputs"]["lora_name"] = props.lora2_name
                    workflow["34"]["inputs"]["strength_model"] = props.lora2_strength_model
                    workflow["34"]["inputs"]["strength_clip"] = props.lora2_strength_model
                else:
                    workflow["34"]["inputs"]["strength_model"] = 0.0
                    workflow["34"]["inputs"]["strength_clip"] = 0.0
            
            print(f"[Patch] Workflow patched with session settings")
            
            # 6. Submit
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Patch] Queued: {prompt_id[:8]}...")
            
            progress_bar.set_current_workflow(workflow)
            
            # 7. IMMEDIATELY kill patch camera and restore viewport
            bpy.ops.style_engine.toggle_patch_camera()
            
            # 8. Find next patch number
            patch_num = 0
            while f"patch_{patch_num:03d}_iteration_{iter_num}" in bpy.data.materials:
                patch_num += 1
            patch_name = f"patch_{patch_num:03d}_iteration_{iter_num}"
            
            # Capture variables for callback
            captured_patch_cam_matrix = patch_cam_matrix.copy()
            captured_obj_name = obj_name
            captured_patch_name = patch_name
            captured_iter_num = iter_num
            captured_face_indices = list(selected_face_indices)
            
            def on_patch_complete(success, result=None, error=None, workflow_type=None):
                """Callback when patch generation completes"""
                print(f"[Patch] ============================================")
                print(f"[Patch] PATCH GENERATION COMPLETE")
                print(f"[Patch] ============================================")
                
                if not success:
                    print(f"[Patch] Failed: {error}")
                    return
                
                try:
                    # Download the main image (blacklist pattern)
                    images = extract_output_images(result)
                    patch_img_path = None
                    
                    for img_info in images:
                        filename = img_info['filename']
                        if not filename.lower().startswith(('canny', 'depth')):
                            save_path = workspace_setup.get_temp_directory(bpy.context) / f"{captured_patch_name}.png"
                            server_client.download_image(filename, str(save_path), img_info.get('subfolder', ''))
                            patch_img_path = save_path
                            print(f"[Patch] Downloaded: {save_path.name}")
                            break
                    
                    if not patch_img_path:
                        print(f"[Patch] No output image found")
                        return
                    
                    # Schedule projection on main thread
                    def _do_patch_projection():
                        try:
                            import bmesh
                            
                            # Load image and create material
                            patch_img = bpy.data.images.load(str(patch_img_path))
                            patch_img.name = f"{captured_patch_name}.png"
                            patch_img.pack()
                            
                            mat = bpy.data.materials.new(name=captured_patch_name)
                            mat.use_nodes = True
                            nodes = mat.node_tree.nodes
                            nodes.clear()
                            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                            bsdf.location = (0, 0)
                            bsdf.inputs['Roughness'].default_value = 1.0
                            tex = nodes.new(type='ShaderNodeTexImage')
                            tex.location = (-300, 0)
                            tex.image = patch_img
                            output = nodes.new(type='ShaderNodeOutputMaterial')
                            output.location = (300, 0)
                            mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
                            mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                            
                            print(f"[Patch] Created material: {captured_patch_name}")
                            
                            # Get target object
                            target_obj = bpy.data.objects.get(captured_obj_name)
                            if not target_obj or target_obj.type != 'MESH':
                                print(f"[Patch] Object '{captured_obj_name}' not found")
                                return None
                            
                            # Append material to new slot
                            target_obj.data.materials.append(mat)
                            patch_slot = len(target_obj.data.materials) - 1
                            
                            # Enter edit mode for face assignment using captured selection
                            bpy.context.view_layer.objects.active = target_obj
                            target_obj.select_set(True)
                            bpy.ops.object.mode_set(mode='EDIT')
                            
                            import bmesh
                            bm = bmesh.from_edit_mesh(target_obj.data)
                            
                            # Assign user-selected faces to patch material slot
                            selected_set = set(captured_face_indices)
                            patch_count = 0
                            bpy.ops.mesh.select_all(action='DESELECT')
                            bm = bmesh.from_edit_mesh(target_obj.data)
                            for face in bm.faces:
                                if face.index in selected_set:
                                    face.material_index = patch_slot
                                    face.select = True
                                    patch_count += 1
                                else:
                                    face.select = False
                            
                            bmesh.update_edit_mesh(target_obj.data)
                            print(f"[Patch] Assigned {patch_count} user-selected faces to slot {patch_slot}")
                            
                            # Create temporary camera at saved position for projection
                            temp_cam_data = bpy.data.cameras.new("_patch_proj_cam")
                            ai_cam = bpy.data.objects.get("ai_camera")
                            if ai_cam:
                                temp_cam_data.lens = ai_cam.data.lens
                            temp_cam = bpy.data.objects.new("_patch_proj_cam", temp_cam_data)
                            bpy.context.collection.objects.link(temp_cam)
                            temp_cam.matrix_world = captured_patch_cam_matrix
                            
                            # Set as scene camera and project
                            original_cam = bpy.context.scene.camera
                            bpy.context.scene.camera = temp_cam
                            
                            space_3d = None
                            original_persp = None
                            for area in bpy.context.screen.areas:
                                if area.type == 'VIEW_3D':
                                    for space in area.spaces:
                                        if space.type == 'VIEW_3D':
                                            space_3d = space
                                            original_persp = space.region_3d.view_perspective
                                            break
                                    break
                            
                            if space_3d:
                                space_3d.region_3d.view_perspective = 'CAMERA'
                                _proj_img = bpy.data.images.get("current_ai.png")
                                _orig_rx = bpy.context.scene.render.resolution_x
                                _orig_ry = bpy.context.scene.render.resolution_y
                                if _proj_img and _proj_img.size[0] > 0 and _proj_img.size[1] > 0:
                                    bpy.context.scene.render.resolution_x = _proj_img.size[0]
                                    bpy.context.scene.render.resolution_y = _proj_img.size[1]
                                bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=False, scale_to_bounds=False)
                                bpy.context.scene.render.resolution_x = _orig_rx
                                bpy.context.scene.render.resolution_y = _orig_ry
                                space_3d.region_3d.view_perspective = original_persp
                                print(f"[Patch] Projected UVs from patch angle")
                            
                            # Cleanup temp camera
                            bpy.context.scene.camera = original_cam
                            bpy.data.objects.remove(temp_cam, do_unlink=True)
                            
                            bpy.ops.object.mode_set(mode='OBJECT')
                            
                            print(f"[Patch] ============================================")
                            print(f"[Patch] PATCH APPLIED: {captured_patch_name}")
                            print(f"[Patch]   Faces patched: {patch_count}")
                            print(f"[Patch]   Material slot: {patch_slot}")
                            print(f"[Patch] ============================================")
                            
                        except Exception as e:
                            print(f"[Patch] Projection error: {e}")
                            import traceback
                            traceback.print_exc()
                            try:
                                bpy.ops.object.mode_set(mode='OBJECT')
                            except:
                                pass
                        return None
                    
                    bpy.app.timers.register(_do_patch_projection, first_interval=0.1)
                    
                except Exception as e:
                    print(f"[Patch] Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Start polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_patch_complete,
                workflow_type='patch'
            )
            
            self.report({'INFO'}, f"Patch submitted! Generating texture...")
            print(f"[Patch] Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Patch failed: {str(e)}")
            print(f"[Patch] Error: {e}")
            import traceback
            traceback.print_exc()
            # Restore on error
            try:
                context.scene.render.engine = original_engine
                if ai_cam:
                    for i, bg in enumerate(ai_cam.data.background_images):
                        if i < len(bg_states):
                            bg.show_background_image = bg_states[i]
            except:
                pass
            return {'CANCELLED'}


# ================================================================
# MULTIVIEW PROJECTION OPERATOR
# ================================================================

class WM_OT_MultiviewFromProjected(bpy.types.Operator):
    """Generate back-left and back-right textures and project onto corresponding faces"""
    bl_idname = "style_engine.multiview_from_projected"
    bl_label = "Multiview from Projected"
    bl_description = "Enhance projection with back-left and back-right views for better coverage"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import json
        import re
        import math
        from pathlib import Path
        from mathutils import Matrix, Vector
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        from .runcomfy_server_client import extract_output_images
        
        # 1. Validate: find object with iteration_XXX material
        obj = context.active_object
        if not obj or obj.type != 'MESH' or not obj.data.materials:
            self.report({'ERROR'}, "Select a mesh with a projected iteration texture")
            return {'CANCELLED'}
        
        # Find the highest numbered iteration material
        best_num = -1
        iteration_mat = None
        for mat in obj.data.materials:
            if mat and mat.name.startswith('iteration_'):
                m = re.match(r'iteration_(\d+)', mat.name)
                if m:
                    num = int(m.group(1))
                    if num > best_num:
                        best_num = num
                        iteration_mat = mat
        
        if not iteration_mat or best_num < 0:
            self.report({'ERROR'}, "Selected object has no iteration_XXX material")
            return {'CANCELLED'}
        
        iter_num = f"{best_num:03d}"
        print(f"[Multiview] Starting multi-view projection for iteration_{iter_num}")
        
        # 2. Check server mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Multiview requires Server mode (GCS)")
            return {'CANCELLED'}
        
        # Check if ai_camera exists
        if "ai_camera" not in bpy.data.objects:
            self.report({'ERROR'}, "AI Camera not found")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects["ai_camera"]
        
        try:
            # 3. Store original camera transform and setup
            original_cam_matrix = ai_camera.matrix_world.copy()
            original_engine = context.scene.render.engine
            original_file_format = context.scene.render.image_settings.file_format
            original_scene_camera = context.scene.camera
            
            # Ensure ai_camera is the active scene camera for rendering
            context.scene.camera = ai_camera
            
            # Disable background images for solid renders
            bg_states = []
            for bg in ai_camera.data.background_images:
                bg_states.append(bg.show_background_image)
                bg.show_background_image = False
            
            # Calculate orbital camera positions around the target object
            # Camera orbits around the object's center at the same distance
            cam_loc = original_cam_matrix.to_translation()
            obj_center = obj.matrix_world.to_translation()
            
            # Vector from object to camera
            cam_offset = cam_loc - obj_center
            cam_distance = cam_offset.length
            
            print(f"[Multiview] Object center: {obj_center}")
            print(f"[Multiview] Camera distance: {cam_distance:.2f}")
            
            def orbit_camera(angle_degrees):
                """Move camera to orbital position and aim at object using TRACK_TO constraint."""
                rot_matrix = Matrix.Rotation(math.radians(angle_degrees), 4, 'Z')
                rotated_offset = rot_matrix @ cam_offset
                new_cam_loc = obj_center + rotated_offset
                
                # Move camera to new position
                ai_camera.location = new_cam_loc
                
                # Add temporary TRACK_TO constraint to aim at object
                track = ai_camera.constraints.new(type='TRACK_TO')
                track.name = '_multiview_track'
                track.target = obj
                track.track_axis = 'TRACK_NEGATIVE_Z'
                track.up_axis = 'UP_Y'
                
                # Force constraint evaluation
                bpy.context.view_layer.update()
                
                # Bake the constrained rotation, then remove constraint
                final_matrix = ai_camera.matrix_world.copy()
                ai_camera.constraints.remove(track)
                ai_camera.matrix_world = final_matrix
                
                print(f"[Multiview] Camera orbited {angle_degrees}° to {new_cam_loc}")
            
            # Setup render for solid views
            context.scene.render.engine = 'BLENDER_WORKBENCH'
            context.scene.display.shading.light = 'FLAT'
            context.scene.render.image_settings.file_format = 'PNG'
            temp_dir = workspace_setup.get_temp_directory(context)
            
            # 4. Generate left view (+120°)
            print(f"[Multiview] Generating back-left view (+120°)...")
            orbit_camera(120)
            
            combined_left_path = temp_dir / f"combined_left_{iter_num}.png"
            context.scene.render.filepath = str(combined_left_path)
            bpy.ops.render.render(write_still=True)
            print(f"[Multiview] Rendered left view: {combined_left_path.name}")
            
            # Upload and submit left
            server_client = runcomfy_deployment.get_server_client()
            upload_left = server_client.upload_image(str(combined_left_path), overwrite=True)
            uploaded_left = upload_left.get("name", "")
            
            # Load workflow (reuse Image or ImageRef logic)
            workflows_dir = Path(__file__).parent / "workflows" / "Image"
            use_ref = any(getattr(context.scene.style_engine_props, f"{slot}_image", None) for slot in ['st1', 'st2', 'st3', 'st4', 'st5', 'comp1', 'comp2', 'comp3', 'comp4', 'comp5'])
            workflow_file = workflows_dir / ("ImageRef.json" if use_ref else "Image.json")
            
            with open(workflow_file, 'r') as f:
                workflow_left = json.load(f)
            
            # Patch workflow with side render as input
            workflow_left["15"]["inputs"]["image"] = uploaded_left
            props = context.scene.style_engine_props
            workflow_left["25"]["inputs"]["value"] = props.global_prompt
            workflow_left["7"]["inputs"]["text"] = props.negative_prompt or ""
            workflow_left["4"]["inputs"]["seed"] = props.seed_value
            
            response_left = server_client.queue_prompt(workflow_left)
            prompt_id_left = response_left['prompt_id']
            print(f"[Multiview] Left view queued: {prompt_id_left[:8]}...")
            
            # 5. Generate right view (-120°)
            print(f"[Multiview] Generating back-right view (-120°)...")
            orbit_camera(-120)
            
            combined_right_path = temp_dir / f"combined_right_{iter_num}.png"
            context.scene.render.filepath = str(combined_right_path)
            bpy.ops.render.render(write_still=True)
            print(f"[Multiview] Rendered right view: {combined_right_path.name}")
            
            # Upload and submit right
            upload_right = server_client.upload_image(str(combined_right_path), overwrite=True)
            uploaded_right = upload_right.get("name", "")
            
            with open(workflow_file, 'r') as f:
                workflow_right = json.load(f)
            
            workflow_right["15"]["inputs"]["image"] = uploaded_right
            workflow_right["25"]["inputs"]["value"] = props.global_prompt
            workflow_right["7"]["inputs"]["text"] = props.negative_prompt or ""
            workflow_right["4"]["inputs"]["seed"] = props.seed_value
            
            response_right = server_client.queue_prompt(workflow_right)
            prompt_id_right = response_right['prompt_id']
            print(f"[Multiview] Right view queued: {prompt_id_right[:8]}...")
            
            # 6. Restore camera, engine, and settings
            ai_camera.matrix_world = original_cam_matrix
            context.scene.render.engine = original_engine
            context.scene.render.image_settings.file_format = original_file_format
            context.scene.camera = original_scene_camera
            for i, bg in enumerate(ai_camera.data.background_images):
                if i < len(bg_states):
                    bg.show_background_image = bg_states[i]
            
            print(f"[Multiview] Camera and render settings restored")
            
            # 7. Setup parallel completion tracking
            obj_name = obj.name
            completed_results = {'left': None, 'right': None}
            
            def check_and_process_multiview():
                """Check if both generations complete, then do projection"""
                if all(v is not None for v in completed_results.values()):
                    print(f"[Multiview] ============================================")
                    print(f"[Multiview] BOTH VIEWS COMPLETE - Starting projection")
                    print(f"[Multiview] ============================================")
                    
                    # Check both succeeded
                    left_success, left_result, left_error = completed_results['left']
                    right_success, right_result, right_error = completed_results['right']
                    
                    if not left_success or not right_success:
                        print(f"[Multiview] Failed: left={left_success}, right={right_success}")
                        return
                    
                    # Download both images
                    temp_dir = workspace_setup.get_temp_directory(bpy.context)
                    
                    # Extract left image
                    left_images = extract_output_images(left_result)
                    left_img_path = None
                    for img_info in left_images:
                        if not img_info['filename'].startswith(('canny', 'depth')):
                            save_path = temp_dir / f"left_iteration_{iter_num}.png"
                            server_client.download_image(img_info['filename'], str(save_path), img_info.get('subfolder', ''))
                            left_img_path = save_path
                            print(f"[Multiview] Downloaded left: {save_path.name}")
                            break
                    
                    # Extract right image
                    right_images = extract_output_images(right_result)
                    right_img_path = None
                    for img_info in right_images:
                        if not img_info['filename'].startswith(('canny', 'depth')):
                            save_path = temp_dir / f"right_iteration_{iter_num}.png"
                            server_client.download_image(img_info['filename'], str(save_path), img_info.get('subfolder', ''))
                            right_img_path = save_path
                            print(f"[Multiview] Downloaded right: {save_path.name}")
                            break
                    
                    if not left_img_path or not right_img_path:
                        print(f"[Multiview] Failed to download side images")
                        return
                    
                    # Create materials for left and right
                    import shutil
                    
                    # Load images into Blender
                    left_img = bpy.data.images.load(str(left_img_path))
                    left_img.name = f"left_iteration_{iter_num}.png"
                    left_img.pack()
                    
                    right_img = bpy.data.images.load(str(right_img_path))
                    right_img.name = f"right_iteration_{iter_num}.png"
                    right_img.pack()
                    
                    # Create left material
                    mat_left = bpy.data.materials.new(name=f"left_iteration_{iter_num}")
                    mat_left.use_nodes = True
                    nodes_left = mat_left.node_tree.nodes
                    nodes_left.clear()
                    bsdf_left = nodes_left.new(type='ShaderNodeBsdfPrincipled')
                    bsdf_left.location = (0, 0)
                    bsdf_left.inputs['Roughness'].default_value = 1.0
                    tex_left = nodes_left.new(type='ShaderNodeTexImage')
                    tex_left.location = (-300, 0)
                    tex_left.image = left_img
                    output_left = nodes_left.new(type='ShaderNodeOutputMaterial')
                    output_left.location = (300, 0)
                    mat_left.node_tree.links.new(tex_left.outputs['Color'], bsdf_left.inputs['Base Color'])
                    mat_left.node_tree.links.new(bsdf_left.outputs['BSDF'], output_left.inputs['Surface'])
                    
                    # Create right material
                    mat_right = bpy.data.materials.new(name=f"right_iteration_{iter_num}")
                    mat_right.use_nodes = True
                    nodes_right = mat_right.node_tree.nodes
                    nodes_right.clear()
                    bsdf_right = nodes_right.new(type='ShaderNodeBsdfPrincipled')
                    bsdf_right.location = (0, 0)
                    bsdf_right.inputs['Roughness'].default_value = 1.0
                    tex_right = nodes_right.new(type='ShaderNodeTexImage')
                    tex_right.location = (-300, 0)
                    tex_right.image = right_img
                    output_right = nodes_right.new(type='ShaderNodeOutputMaterial')
                    output_right.location = (300, 0)
                    mat_right.node_tree.links.new(tex_right.outputs['Color'], bsdf_right.inputs['Base Color'])
                    mat_right.node_tree.links.new(bsdf_right.outputs['BSDF'], output_right.inputs['Surface'])
                    
                    print(f"[Multiview] Created materials: {mat_left.name}, {mat_right.name}")
                    
                    # Get target object
                    target_obj = bpy.data.objects.get(obj_name)
                    if not target_obj or target_obj.type != 'MESH':
                        print(f"[Multiview] Object not found")
                        return
                    
                    # Add materials to object (append to slots)
                    target_obj.data.materials.append(mat_left)
                    target_obj.data.materials.append(mat_right)
                    slot_left = len(target_obj.data.materials) - 2
                    slot_right = len(target_obj.data.materials) - 1
                    
                    print(f"[Multiview] Added materials to slots {slot_left} and {slot_right}")
                    
                    # Enter edit mode for face assignment
                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.context.view_layer.objects.active = target_obj
                    target_obj.select_set(True)
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    import bmesh
                    bm = bmesh.from_edit_mesh(target_obj.data)
                    
                    # Calculate view directions (world space)
                    front_dir = (original_cam_matrix.to_quaternion() @ Vector((0, 0, -1))).normalized()
                    left_dir = (Matrix.Rotation(math.radians(120), 4, 'Z') @ Vector((front_dir.x, front_dir.y, front_dir.z, 0))).xyz.normalized()
                    right_dir = (Matrix.Rotation(math.radians(-120), 4, 'Z') @ Vector((front_dir.x, front_dir.y, front_dir.z, 0))).xyz.normalized()
                    
                    # Assign faces by normal direction
                    front_count = 0
                    left_count = 0
                    right_count = 0
                    
                    for face in bm.faces:
                        normal_world = (target_obj.matrix_world.to_3x3() @ face.normal).normalized()
                        
                        dot_front = normal_world.dot(front_dir)
                        dot_left = normal_world.dot(left_dir)
                        dot_right = normal_world.dot(right_dir)
                        
                        # Assign to slot with highest dot product
                        if dot_front > dot_left and dot_front > dot_right and dot_front > 0.3:
                            face.material_index = 0  # Front (existing iteration)
                            front_count += 1
                        elif dot_left > dot_right and dot_left > 0.3:
                            face.material_index = slot_left  # Left
                            left_count += 1
                        elif dot_right > 0.3:
                            face.material_index = slot_right  # Right
                            right_count += 1
                    
                    bmesh.update_edit_mesh(target_obj.data)
                    print(f"[Multiview] Face assignment: front={front_count}, left={left_count}, right={right_count}")
                    
                    # Project UVs for each angle
                    # Find 3D viewport and store its perspective
                    space_3d = None
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    space_3d = space
                                    break
                            break
                    
                    original_view_perspective = space_3d.region_3d.view_perspective if space_3d else None
                    
                    # Project front (re-select front faces and project to preserve priority)
                    for face in bm.faces:
                        face.select = (face.material_index == 0)
                    bmesh.update_edit_mesh(target_obj.data)
                    
                    ai_camera.matrix_world = original_cam_matrix
                    if space_3d:
                        space_3d.region_3d.view_perspective = 'CAMERA'
                    bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=False)
                    print(f"[Multiview] Projected front faces")
                    
                    # Project left
                    for face in bm.faces:
                        face.select = (face.material_index == slot_left)
                    bmesh.update_edit_mesh(target_obj.data)
                    
                    ai_camera.rotation_euler.z = original_cam_matrix.to_euler().z + math.radians(120)
                    bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=False)
                    print(f"[Multiview] Projected left faces")
                    
                    # Project right
                    for face in bm.faces:
                        face.select = (face.material_index == slot_right)
                    bmesh.update_edit_mesh(target_obj.data)
                    
                    ai_camera.rotation_euler.z = original_cam_matrix.to_euler().z + math.radians(-120)
                    bpy.ops.uv.project_from_view(camera_bounds=True, correct_aspect=False)
                    print(f"[Multiview] Projected right faces")
                    
                    # Restore viewport and camera
                    if space_3d and original_view_perspective:
                        space_3d.region_3d.view_perspective = original_view_perspective
                    ai_camera.matrix_world = original_cam_matrix
                    
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    print(f"[Multiview] ============================================")
                    print(f"[Multiview] MULTIVIEW PROJECTION COMPLETE")
                    print(f"[Multiview]   Front: iteration_{iter_num} (slot 0)")
                    print(f"[Multiview]   Left:  left_iteration_{iter_num} (slot {slot_left})")
                    print(f"[Multiview]   Right: right_iteration_{iter_num} (slot {slot_right})")
                    print(f"[Multiview] ============================================")
            
            def on_left_complete(success, result=None, error=None, workflow_type=None):
                completed_results['left'] = (success, result, error)
                check_and_process_multiview()
            
            def on_right_complete(success, result=None, error=None, workflow_type=None):
                completed_results['right'] = (success, result, error)
                check_and_process_multiview()
            
            # Start polling for both
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id_left,
                callback=on_left_complete,
                workflow_type='multiview_left'
            )
            
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id_right,
                callback=on_right_complete,
                workflow_type='multiview_right'
            )
            
            self.report({'INFO'}, f"Generating side views... (2x generation time)")
            print(f"[Multiview] Processing both views in parallel...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Multiview failed: {str(e)}")
            print(f"[Multiview] Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Restore camera on error
            try:
                ai_camera.matrix_world = original_cam_matrix
                context.scene.render.engine = original_engine
                context.scene.render.image_settings.file_format = original_file_format
                context.scene.camera = original_scene_camera
                for i, bg in enumerate(ai_camera.data.background_images):
                    if i < len(bg_states):
                        bg.show_background_image = bg_states[i]
            except:
                pass
            
            return {'CANCELLED'}


# ================================================================
# PBR FROM PROJECTED TEXTURE OPERATOR
# ================================================================

class WM_OT_PBRFromProjectedTexture(bpy.types.Operator):
    """Generate PBR material maps from a projected iteration texture using chord_v1"""
    bl_idname = "style_engine.pbr_from_projected"
    bl_label = "PBR from Projected Texture"
    bl_description = "Generate PBR maps (basecolor, normal, roughness, metalness) from the projected texture"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import json
        import re
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        from .runcomfy_server_client import extract_output_images
        
        # 1. Validate: active object must have an iteration material
        obj = context.active_object
        if not obj or obj.type != 'MESH' or not obj.data.materials:
            self.report({'ERROR'}, "Select a mesh with a projected iteration texture")
            return {'CANCELLED'}
        
        # Find the HIGHEST numbered iteration material on this object
        # This ensures we process newest first: iteration_002 before iteration_001
        best_slot = -1
        best_num = -1
        iteration_mat = None
        for slot_idx, mat in enumerate(obj.data.materials):
            if mat and mat.name.startswith('iteration_'):
                m = re.match(r'iteration_(\d+)', mat.name)
                if m:
                    num = int(m.group(1))
                    if num > best_num:
                        best_num = num
                        best_slot = slot_idx
                        iteration_mat = mat
        
        if not iteration_mat or best_slot < 0:
            self.report({'ERROR'}, "Selected object has no iteration_XXX material")
            return {'CANCELLED'}
        
        iter_num = f"{best_num:03d}"
        print(f"[PBR] Starting PBR generation for {iteration_mat.name} (iter {iter_num}, slot {best_slot})")
        
        # 2. Check server mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "PBR generation only works in Server mode (GCS)")
            return {'CANCELLED'}
        
        # 3. Extract the iteration texture directly from the material's node tree.
        # This is the single source of truth -- the packed image that was projected.
        # Disk files can be stale across sessions, so we never search disk paths.
        import time
        
        blender_img = None
        for node in iteration_mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                blender_img = node.image
                break
        
        if not blender_img:
            self.report({'ERROR'}, f"No image found in {iteration_mat.name} node tree")
            return {'CANCELLED'}
        
        # Save the packed image to a unique temp file for upload
        temp_dir = workspace_setup.get_temp_directory(context)
        timestamp = int(time.time())
        unique_name = f"pbr_input_{iter_num}_{timestamp}.png"
        iteration_image_path = temp_dir / unique_name
        blender_img.save_render(str(iteration_image_path))
        
        print(f"[PBR] Extracted from material node tree: {blender_img.name} -> {unique_name}")
        
        try:
            # 4. Upload texture to ComfyUI
            # File is already uniquely named (timestamped) to prevent ComfyUI cache issues
            server_client = runcomfy_deployment.get_server_client()
            
            print(f"[PBR] Uploading {unique_name} to ComfyUI...")
            upload_response = server_client.upload_image(str(iteration_image_path), overwrite=True)
            uploaded_filename = upload_response.get("name", "")
            
            if not uploaded_filename:
                self.report({'ERROR'}, "Failed to upload texture to server")
                return {'CANCELLED'}
            
            print(f"[PBR] Uploaded: {uploaded_filename}")
            
            # 5. Load and patch workflow
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Object" / "objectPBRproject.json"
            
            if not workflow_file.exists():
                self.report({'ERROR'}, "objectPBRproject.json not found")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            print(f"[PBR] Loaded workflow: {workflow_file.name}")
            
            # Patch Node 22 (LoadImage) with uploaded texture
            if "22" not in workflow:
                self.report({'ERROR'}, "Invalid workflow (node 22 missing)")
                return {'CANCELLED'}
            
            workflow["22"]["inputs"]["image"] = uploaded_filename
            print(f"[PBR] Patched node 22 with: {uploaded_filename}")
            
            # 6. Submit to ComfyUI
            print(f"[PBR] Submitting workflow...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[PBR] Queued (ID: {prompt_id[:8]}...)")
            
            # 7. Store workflow for progress bar
            progress_bar.set_current_workflow(workflow)
            
            # 8. Capture variables for callback
            obj_name = obj.name
            target_slot = best_slot
            pbr_name = f"pbrmaterial_{iter_num}"
            pbr_dir_name = f"pbr_{iter_num}"
            
            def on_pbr_complete(success, result=None, error=None, workflow_type=None):
                """Callback when PBR generation completes"""
                print(f"[PBR] ============================================")
                print(f"[PBR] PBR GENERATION COMPLETE")
                print(f"[PBR] ============================================")
                
                if not success:
                    print(f"[PBR] Failed: {error}")
                    return
                
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    
                    # Extract output images
                    images = extract_output_images(result)
                    print(f"[PBR] Found {len(images)} output images")
                    
                    if not images:
                        print(f"[PBR] No output images found")
                        return
                    
                    # Create PBR directory
                    pbr_save_dir = None
                    proj_lib = workspace_setup.get_project_library(bpy.context)
                    if proj_lib:
                        pbr_save_dir = proj_lib / "Textures" / pbr_dir_name
                    else:
                        temp = workspace_setup.get_temp_directory(bpy.context)
                        pbr_save_dir = temp / pbr_dir_name
                    
                    pbr_save_dir.mkdir(parents=True, exist_ok=True)
                    print(f"[PBR] Saving PBR maps to: {pbr_save_dir}")
                    
                    # Map prefix to PBR channel
                    pbr_prefixes = {
                        'basecolor': 'basecolor',
                        'normal': 'normal',
                        'roughness': 'roughness',
                        'metalness': 'metalness',
                        'height': 'height',
                    }
                    
                    # Download all maps in parallel
                    download_tasks = []
                    for img_info in images:
                        filename = img_info['filename']
                        subfolder = img_info.get('subfolder', '')
                        
                        # Match filename prefix to PBR channel
                        for prefix, channel in pbr_prefixes.items():
                            if filename.lower().startswith(prefix):
                                save_name = f"pbr_{iter_num}_{channel}.png"
                                save_path = pbr_save_dir / save_name
                                download_tasks.append({
                                    'filename': filename,
                                    'subfolder': subfolder,
                                    'save_path': save_path,
                                    'channel': channel,
                                })
                                break
                    
                    print(f"[PBR] Downloading {len(download_tasks)} PBR maps...")
                    
                    def download_one(task):
                        try:
                            server_client.download_image(
                                task['filename'],
                                str(task['save_path']),
                                subfolder=task['subfolder'],
                            )
                            print(f"[PBR] Downloaded: {task['channel']} -> {task['save_path'].name}")
                            return task
                        except Exception as e:
                            print(f"[PBR] Failed to download {task['channel']}: {e}")
                            return None
                    
                    downloaded = {}
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        results = list(executor.map(download_one, download_tasks))
                    
                    for task in results:
                        if task:
                            downloaded[task['channel']] = task['save_path']
                    
                    print(f"[PBR] Downloaded {len(downloaded)}/{len(download_tasks)} maps")
                    
                    # Check minimum required maps
                    required = ['basecolor', 'normal', 'roughness', 'metalness']
                    missing = [r for r in required if r not in downloaded]
                    if missing:
                        print(f"[PBR] Missing required maps: {missing}")
                        return
                    
                    # ================================================
                    # CREATE PBR MATERIAL
                    # ================================================
                    print(f"[PBR] Creating material: {pbr_name}")
                    
                    mat = bpy.data.materials.new(name=pbr_name)
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    nodes.clear()
                    
                    # -- Texture Coordinate --
                    tex_coord = nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = (-900, 0)
                    
                    # -- Mapping --
                    mapping = nodes.new(type='ShaderNodeMapping')
                    mapping.location = (-700, 0)
                    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
                    
                    # -- Base Color --
                    img_basecolor = bpy.data.images.load(str(downloaded['basecolor']))
                    img_basecolor.name = f"pbr_{iter_num}_basecolor"
                    tex_basecolor = nodes.new(type='ShaderNodeTexImage')
                    tex_basecolor.location = (-400, 300)
                    tex_basecolor.image = img_basecolor
                    tex_basecolor.label = "Base Color"
                    links.new(mapping.outputs['Vector'], tex_basecolor.inputs['Vector'])
                    
                    # -- Metalness --
                    img_metalness = bpy.data.images.load(str(downloaded['metalness']))
                    img_metalness.name = f"pbr_{iter_num}_metalness"
                    img_metalness.colorspace_settings.name = 'Non-Color'
                    tex_metalness = nodes.new(type='ShaderNodeTexImage')
                    tex_metalness.location = (-400, 0)
                    tex_metalness.image = img_metalness
                    tex_metalness.label = "Metalness"
                    links.new(mapping.outputs['Vector'], tex_metalness.inputs['Vector'])
                    
                    # -- Roughness --
                    img_roughness = bpy.data.images.load(str(downloaded['roughness']))
                    img_roughness.name = f"pbr_{iter_num}_roughness"
                    img_roughness.colorspace_settings.name = 'Non-Color'
                    tex_roughness = nodes.new(type='ShaderNodeTexImage')
                    tex_roughness.location = (-400, -300)
                    tex_roughness.image = img_roughness
                    tex_roughness.label = "Roughness"
                    links.new(mapping.outputs['Vector'], tex_roughness.inputs['Vector'])
                    
                    # -- Normal --
                    img_normal = bpy.data.images.load(str(downloaded['normal']))
                    img_normal.name = f"pbr_{iter_num}_normal"
                    img_normal.colorspace_settings.name = 'Non-Color'
                    tex_normal = nodes.new(type='ShaderNodeTexImage')
                    tex_normal.location = (-400, -600)
                    tex_normal.image = img_normal
                    tex_normal.label = "Normal"
                    links.new(mapping.outputs['Vector'], tex_normal.inputs['Vector'])
                    
                    # -- Normal Map node --
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    normal_map.location = (-100, -600)
                    normal_map.space = 'TANGENT'
                    normal_map.inputs['Strength'].default_value = 1.0
                    links.new(tex_normal.outputs['Color'], normal_map.inputs['Color'])
                    
                    # -- Principled BSDF --
                    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                    bsdf.location = (200, 0)
                    
                    links.new(tex_basecolor.outputs['Color'], bsdf.inputs['Base Color'])
                    links.new(tex_metalness.outputs['Color'], bsdf.inputs['Metallic'])
                    links.new(tex_roughness.outputs['Color'], bsdf.inputs['Roughness'])
                    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
                    
                    # -- Material Output --
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (500, 0)
                    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                    
                    # ================================================
                    # ASSIGN MATERIAL TO OBJECT (replace same slot)
                    # ================================================
                    target_obj = bpy.data.objects.get(obj_name)
                    if target_obj and target_obj.type == 'MESH':
                        # Replace the exact slot where iteration_XXX was
                        if target_obj.data.materials and target_slot < len(target_obj.data.materials):
                            target_obj.data.materials[target_slot] = mat
                            print(f"[PBR] Replaced slot {target_slot} on {target_obj.name} with {pbr_name}")
                        else:
                            target_obj.data.materials.append(mat)
                            print(f"[PBR] Appended {pbr_name} to {target_obj.name}")
                    else:
                        print(f"[PBR] Object '{obj_name}' not found, material created but not assigned")
                    
                    print(f"[PBR] ============================================")
                    print(f"[PBR] PBR MATERIAL CREATED: {pbr_name}")
                    print(f"[PBR]   Base Color: {downloaded['basecolor'].name}")
                    print(f"[PBR]   Metalness:  {downloaded['metalness'].name}")
                    print(f"[PBR]   Roughness:  {downloaded['roughness'].name}")
                    print(f"[PBR]   Normal:     {downloaded['normal'].name}")
                    if 'height' in downloaded:
                        print(f"[PBR]   Height:     {downloaded['height'].name} (saved, not used in shader)")
                    print(f"[PBR] ============================================")
                    
                except Exception as e:
                    print(f"[PBR] Error in callback: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_pbr_complete,
                workflow_type='pbr'
            )
            
            self.report({'INFO'}, f"Generating PBR maps for iteration_{iter_num}... (watch progress bar)")
            print(f"[PBR] Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"PBR generation failed: {str(e)}")
            print(f"[PBR] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


# ================================================================
# PBR FROM TEXT PROMPT OPERATOR
# ================================================================

class WM_OT_PBRFromText(bpy.types.Operator):
    """Generate a PBR material from a text prompt using chord_v1"""
    bl_idname = "style_engine.pbr_from_text"
    bl_label = "Generate PBR Material"
    bl_description = "Generate PBR maps (basecolor, normal, roughness, metalness) from a text description"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import json
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        from . import progress_bar
        from . import runcomfy_polling
        from . import utils
        from .runcomfy_server_client import extract_output_images
        
        # 1. Check server mode
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "PBR generation only works in Server mode (GCS)")
            return {'CANCELLED'}
        
        # 2. Read prompt from text editor — raw for Gemini, tag-parsed for SDXL
        props = context.scene.style_engine_props
        _is_gemini = getattr(props, 'ai_model', 'SDXL') == 'GEMINI'

        if _is_gemini:
            text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
            raw_prompt = text_block.as_string().strip() if text_block else ""
            if not raw_prompt:
                self.report({'ERROR'}, "No prompt found in STYLEENGINE_Prompt text block")
                return {'CANCELLED'}
            print(f"[PBR Text] Gemini mode — prompt: {raw_prompt[:80]}...")
        else:
            prompt_from_editor = utils.get_prompt_from_text_editor()
            if not prompt_from_editor:
                self.report({'ERROR'}, "No prompt found in STYLEENGINE_Prompt text block")
                return {'CANCELLED'}
            positive_prompt, negative_prompt = utils.process_prompt_builder(prompt_from_editor)
            if not positive_prompt:
                self.report({'ERROR'}, "No positive prompt found. Write a texture description in the <p> tag.")
                return {'CANCELLED'}
            print(f"[PBR Text] Positive: {positive_prompt[:80]}...")
            print(f"[PBR Text] Negative: {negative_prompt[:80]}..." if negative_prompt else "[PBR Text] Negative: (none)")

        try:
            server_client = runcomfy_deployment.get_server_client()

            # 3. Load and patch workflow — Gemini uses objectNanoPBRtext.json
            addon_dir = Path(__file__).parent
            if _is_gemini:
                workflow_file = addon_dir / "workflows" / "Object" / "objectNanoPBRtext.json"
            else:
                workflow_file = addon_dir / "workflows" / "Object" / "objectPBRtext.json"

            if not workflow_file.exists():
                self.report({'ERROR'}, f"{workflow_file.name} not found")
                return {'CANCELLED'}

            with open(workflow_file, 'r') as f:
                workflow = json.load(f)

            print(f"[PBR Text] Loaded workflow: {workflow_file.name}")

            if _is_gemini:
                # Patch Node 44 (Text Prompt) with raw prompt
                if "44" in workflow:
                    workflow["44"]["inputs"]["text"] = raw_prompt
                    print(f"[PBR Text] Patched node 44 (prompt): {raw_prompt[:60]}...")
                # Patch Node 41 (NanoBananaAIO) — temperature and image_size from Gemini prefs
                if "41" in workflow:
                    workflow["41"]["inputs"]["temperature"] = props.gemini_temperature
                    workflow["41"]["inputs"]["image_size"] = props.gemini_image_size
                    print(f"[PBR Text] Patched node 41: temperature={props.gemini_temperature}, size={props.gemini_image_size}")
            else:
                # Patch Node 38 (Text Multiline) with positive prompt
                if "38" in workflow:
                    workflow["38"]["inputs"]["text"] = positive_prompt
                    print(f"[PBR Text] Patched node 38 (prompt): {positive_prompt[:60]}...")
                # Patch Node 25 (CLIPTextEncode) with negative prompt
                if "25" in workflow:
                    workflow["25"]["inputs"]["text"] = negative_prompt or ""
                    print(f"[PBR Text] Patched node 25 (negative): {negative_prompt[:60]}..." if negative_prompt else "[PBR Text] Patched node 25 (negative): empty")
                # Patch seed (Node 26 - KSampler)
                seed = props.seed_value
                if "26" in workflow:
                    workflow["26"]["inputs"]["seed"] = seed
                    print(f"[PBR Text] Patched node 26 (seed): {seed}")
            
            # 4. Submit to ComfyUI
            print(f"[PBR Text] Submitting workflow...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[PBR Text] Queued (ID: {prompt_id[:8]}...)")
            
            # 5. Store workflow for progress bar
            progress_bar.set_current_workflow(workflow)
            
            # 6. Capture variables for callback
            obj_name = None
            obj = context.active_object
            if obj and obj.type == 'MESH':
                obj_name = obj.name
            
            def on_pbr_text_complete(success, result=None, error=None, workflow_type=None):
                """Callback when text-to-PBR generation completes"""
                print(f"[PBR Text] ============================================")
                print(f"[PBR Text] TEXT-TO-PBR GENERATION COMPLETE")
                print(f"[PBR Text] ============================================")
                
                if not success:
                    print(f"[PBR Text] Failed: {error}")
                    return
                
                try:
                    from concurrent.futures import ThreadPoolExecutor
                    
                    # Extract output images
                    images = extract_output_images(result)
                    print(f"[PBR Text] Found {len(images)} output images")
                    
                    if not images:
                        print(f"[PBR Text] No output images found")
                        return
                    
                    # Auto-increment naming: find next available pbr_text_XXX
                    pbr_num = 0
                    while f"pbrmaterial_text_{pbr_num:03d}" in bpy.data.materials:
                        pbr_num += 1
                    
                    iter_num = f"{pbr_num:03d}"
                    pbr_name = f"pbrmaterial_text_{iter_num}"
                    pbr_dir_name = f"pbr_text_{iter_num}"
                    
                    print(f"[PBR Text] Using name: {pbr_name}")
                    
                    # Create PBR directory
                    pbr_save_dir = None
                    proj_lib = workspace_setup.get_project_library(bpy.context)
                    if proj_lib:
                        pbr_save_dir = proj_lib / "Textures" / pbr_dir_name
                    else:
                        temp = workspace_setup.get_temp_directory(bpy.context)
                        pbr_save_dir = temp / pbr_dir_name
                    
                    pbr_save_dir.mkdir(parents=True, exist_ok=True)
                    print(f"[PBR Text] Saving PBR maps to: {pbr_save_dir}")
                    
                    # Map prefix to PBR channel
                    pbr_prefixes = {
                        'texture_image': 'texture_image',
                        'basecolor': 'basecolor',
                        'normal': 'normal',
                        'roughness': 'roughness',
                        'metalness': 'metalness',
                        'height': 'height',
                    }
                    
                    # Download all maps in parallel
                    download_tasks = []
                    for img_info in images:
                        filename = img_info['filename']
                        subfolder = img_info.get('subfolder', '')
                        
                        for prefix, channel in pbr_prefixes.items():
                            if filename.lower().startswith(prefix):
                                save_name = f"pbr_text_{iter_num}_{channel}.png"
                                save_path = pbr_save_dir / save_name
                                download_tasks.append({
                                    'filename': filename,
                                    'subfolder': subfolder,
                                    'save_path': save_path,
                                    'channel': channel,
                                })
                                break
                    
                    print(f"[PBR Text] Downloading {len(download_tasks)} maps...")
                    
                    def download_one(task):
                        try:
                            server_client.download_image(
                                task['filename'],
                                str(task['save_path']),
                                subfolder=task['subfolder'],
                            )
                            print(f"[PBR Text] Downloaded: {task['channel']} -> {task['save_path'].name}")
                            return task
                        except Exception as e:
                            print(f"[PBR Text] Failed to download {task['channel']}: {e}")
                            return None
                    
                    downloaded = {}
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        results = list(executor.map(download_one, download_tasks))
                    
                    for task in results:
                        if task:
                            downloaded[task['channel']] = task['save_path']
                    
                    print(f"[PBR Text] Downloaded {len(downloaded)}/{len(download_tasks)} maps")
                    
                    # Check minimum required maps
                    required = ['basecolor', 'normal', 'roughness', 'metalness']
                    missing = [r for r in required if r not in downloaded]
                    if missing:
                        print(f"[PBR Text] Missing required maps: {missing}")
                        return
                    
                    # ================================================
                    # CREATE PBR MATERIAL
                    # ================================================
                    print(f"[PBR Text] Creating material: {pbr_name}")
                    
                    mat = bpy.data.materials.new(name=pbr_name)
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    links = mat.node_tree.links
                    nodes.clear()
                    
                    # -- Texture Coordinate --
                    tex_coord = nodes.new(type='ShaderNodeTexCoord')
                    tex_coord.location = (-900, 0)
                    
                    # -- Mapping --
                    mapping = nodes.new(type='ShaderNodeMapping')
                    mapping.location = (-700, 0)
                    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
                    
                    # -- Base Color --
                    img_basecolor = bpy.data.images.load(str(downloaded['basecolor']))
                    img_basecolor.name = f"pbr_text_{iter_num}_basecolor"
                    tex_basecolor = nodes.new(type='ShaderNodeTexImage')
                    tex_basecolor.location = (-400, 300)
                    tex_basecolor.image = img_basecolor
                    tex_basecolor.label = "Base Color"
                    links.new(mapping.outputs['Vector'], tex_basecolor.inputs['Vector'])
                    
                    # -- Metalness --
                    img_metalness = bpy.data.images.load(str(downloaded['metalness']))
                    img_metalness.name = f"pbr_text_{iter_num}_metalness"
                    img_metalness.colorspace_settings.name = 'Non-Color'
                    tex_metalness = nodes.new(type='ShaderNodeTexImage')
                    tex_metalness.location = (-400, 0)
                    tex_metalness.image = img_metalness
                    tex_metalness.label = "Metalness"
                    links.new(mapping.outputs['Vector'], tex_metalness.inputs['Vector'])
                    
                    # -- Roughness --
                    img_roughness = bpy.data.images.load(str(downloaded['roughness']))
                    img_roughness.name = f"pbr_text_{iter_num}_roughness"
                    img_roughness.colorspace_settings.name = 'Non-Color'
                    tex_roughness = nodes.new(type='ShaderNodeTexImage')
                    tex_roughness.location = (-400, -300)
                    tex_roughness.image = img_roughness
                    tex_roughness.label = "Roughness"
                    links.new(mapping.outputs['Vector'], tex_roughness.inputs['Vector'])
                    
                    # -- Normal --
                    img_normal = bpy.data.images.load(str(downloaded['normal']))
                    img_normal.name = f"pbr_text_{iter_num}_normal"
                    img_normal.colorspace_settings.name = 'Non-Color'
                    tex_normal = nodes.new(type='ShaderNodeTexImage')
                    tex_normal.location = (-400, -600)
                    tex_normal.image = img_normal
                    tex_normal.label = "Normal"
                    links.new(mapping.outputs['Vector'], tex_normal.inputs['Vector'])
                    
                    # -- Normal Map node --
                    normal_map = nodes.new(type='ShaderNodeNormalMap')
                    normal_map.location = (-100, -600)
                    normal_map.space = 'TANGENT'
                    normal_map.inputs['Strength'].default_value = 1.0
                    links.new(tex_normal.outputs['Color'], normal_map.inputs['Color'])
                    
                    # -- Principled BSDF --
                    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                    bsdf.location = (200, 0)
                    
                    links.new(tex_basecolor.outputs['Color'], bsdf.inputs['Base Color'])
                    links.new(tex_metalness.outputs['Color'], bsdf.inputs['Metallic'])
                    links.new(tex_roughness.outputs['Color'], bsdf.inputs['Roughness'])
                    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
                    
                    # -- Material Output --
                    output = nodes.new(type='ShaderNodeOutputMaterial')
                    output.location = (500, 0)
                    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                    
                    # ================================================
                    # ASSIGN MATERIAL TO ACTIVE MESH (if any)
                    # ================================================
                    if obj_name:
                        target_obj = bpy.data.objects.get(obj_name)
                        if target_obj and target_obj.type == 'MESH':
                            if target_obj.data.materials:
                                target_obj.data.materials[0] = mat
                            else:
                                target_obj.data.materials.append(mat)
                            print(f"[PBR Text] Assigned {pbr_name} to {target_obj.name}")
                        else:
                            print(f"[PBR Text] Object '{obj_name}' not found, material created but not assigned")
                    else:
                        print(f"[PBR Text] No active mesh, material '{pbr_name}' created (assign manually)")
                    
                    print(f"[PBR Text] ============================================")
                    print(f"[PBR Text] PBR MATERIAL CREATED: {pbr_name}")
                    print(f"[PBR Text]   Base Color: {downloaded['basecolor'].name}")
                    print(f"[PBR Text]   Metalness:  {downloaded['metalness'].name}")
                    print(f"[PBR Text]   Roughness:  {downloaded['roughness'].name}")
                    print(f"[PBR Text]   Normal:     {downloaded['normal'].name}")
                    if 'height' in downloaded:
                        print(f"[PBR Text]   Height:     {downloaded['height'].name} (saved, not used in shader)")
                    if 'texture_image' in downloaded:
                        print(f"[PBR Text]   Texture:    {downloaded['texture_image'].name} (raw generated, saved)")
                    print(f"[PBR Text] ============================================")
                    
                except Exception as e:
                    print(f"[PBR Text] Error in callback: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_pbr_text_complete,
                workflow_type='pbr'
            )
            
            self.report({'INFO'}, f"Generating PBR material from text... (watch progress bar)")
            print(f"[PBR Text] Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"PBR text generation failed: {str(e)}")
            print(f"[PBR Text] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


# ================================================================
# REFERENCE IMAGE OPERATORS
# ================================================================

class WM_OT_UploadCurrentAI(bpy.types.Operator):
    """Upload a local image to use as the current AI generation (current_ai.png).
    The image is copied into temp_dir, registered in the generation history, and
    immediately displayed as the camera background."""
    bl_idname = "style_engine.upload_current_ai"
    bl_label = "Upload Image"
    bl_description = "Load a local image as current_ai.png — it will appear in the camera background and be saved to generation history"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    filter_image: bpy.props.BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_folder: bpy.props.BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

    # SDXL native resolutions, ordered from portrait-tallest to landscape-widest.
    _SDXL_RESOLUTIONS = [
        (640, 1536), (768, 1344), (832, 1216), (896, 1152), (1024, 1024),
        (1152, 896), (1216, 832), (1344, 768), (1536, 640),
    ]

    @staticmethod
    def _target_resolution(src_w, src_h, model):
        """
        Compute the target (w, h) for the uploaded image based on the active model.

        SDXL: snap to the SDXL native resolution whose aspect ratio is closest to
              the source image.  Minor stretching is acceptable.
        Gemini: preserve the original aspect ratio; cap the longest side at 1920 px.
        """
        if model == 'GEMINI':
            max_side = 1920
            if src_w <= max_side and src_h <= max_side:
                return src_w, src_h
            scale = max_side / max(src_w, src_h)
            return int(src_w * scale), int(src_h * scale)
        else:
            # SDXL: find the native resolution with the closest aspect ratio
            src_aspect = src_w / src_h
            best = min(
                WM_OT_UploadCurrentAI._SDXL_RESOLUTIONS,
                key=lambda r: abs(r[0] / r[1] - src_aspect)
            )
            return best

    def execute(self, context):
        import shutil
        from pathlib import Path
        from . import workspace_setup

        src = Path(bpy.path.abspath(self.filepath))
        if not src.exists():
            self.report({'ERROR'}, f"File not found: {src}")
            return {'CANCELLED'}

        suffix = src.suffix.lower()
        if suffix not in ('.png', '.jpg', '.jpeg', '.webp'):
            self.report({'ERROR'}, "Only PNG, JPEG and WEBP files are supported")
            return {'CANCELLED'}

        temp_dir = workspace_setup.get_temp_directory(context)
        temp_dir.mkdir(parents=True, exist_ok=True)
        current_ai_path = temp_dir / "current_ai.png"

        try:
            # Load image into Blender to read its size, convert format, and resize
            tmp_img = bpy.data.images.load(str(src), check_existing=False)
            src_w, src_h = tmp_img.size[0], tmp_img.size[1]

            # Determine target resolution based on the active AI model
            model = context.scene.style_engine_props.ai_model
            target_w, target_h = self._target_resolution(src_w, src_h, model)
            print(f"[Upload] Source: {src_w}x{src_h} → Target: {target_w}x{target_h} ({model})")

            # Scale if needed (operates in-place on the pixel buffer)
            if (src_w, src_h) != (target_w, target_h):
                tmp_img.scale(target_w, target_h)

            # Save as PNG to current_ai_path
            tmp_img.file_format = 'PNG'
            tmp_img.filepath_raw = str(current_ai_path)
            tmp_img.save()
            bpy.data.images.remove(tmp_img)

            print(f"[Upload] Saved '{src.name}' → current_ai.png ({target_w}x{target_h})")

            # Update render resolution to match the uploaded image
            context.scene.render.resolution_x = target_w
            context.scene.render.resolution_y = target_h
            print(f"[Style Engine] ✓ Resolution set to: {target_w}x{target_h} (uploaded)")

            # Also sync the ai_resolution enum when the target matches a SDXL entry
            key = f"{target_w}x{target_h}"
            sdxl_keys = {f"{w}x{h}" for w, h in self._SDXL_RESOLUTIONS}
            if key in sdxl_keys:
                # Direct dict write avoids triggering the update callback/resize
                context.scene.style_engine_props['ai_resolution'] = key

            # Save a timestamped copy to the Images/ library
            # (render resolution is now set, so save_generation_to_library
            # will embed the correct WxH in the filename)
            saved = workspace_setup.save_generation_to_library(
                context, current_ai_path, backend='uploaded'
            )
            if saved:
                print(f"[Upload] Saved to library: {saved.name}")

            # Refresh the camera background
            workspace_setup.refresh_ai_image()

            # Jump to the latest entry in history
            context.scene.style_engine_props.current_generation_index = -1

            self.report({'INFO'}, f"Uploaded: {src.name} ({target_w}x{target_h})")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Upload failed: {e}")
            print(f"[Upload] ❌ {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def _restore_generation_resolution(context, gen_path):
    """
    Parse the WxH embedded in gen_path's filename and apply it to the scene's
    render resolution.  Also syncs ai_resolution enum for SDXL-standard sizes.
    Falls back silently if no resolution token is present (older filenames).
    """
    import re
    m = re.search(r'_(\d+)x(\d+)\.png$', gen_path.name, re.IGNORECASE)
    if not m:
        return
    w, h = int(m.group(1)), int(m.group(2))
    context.scene.render.resolution_x = w
    context.scene.render.resolution_y = h
    # Also sync the SDXL enum when the resolution is a native SDXL entry
    sdxl_keys = {
        '640x1536', '768x1344', '832x1216', '896x1152', '1024x1024',
        '1152x896', '1216x832', '1344x768', '1536x640',
    }
    key = f"{w}x{h}"
    if key in sdxl_keys:
        context.scene.style_engine_props['ai_resolution'] = key
    print(f"[Style Engine] ✓ Resolution restored: {w}x{h}")


class WM_OT_PrevGeneration(bpy.types.Operator):
    """Navigate to the previous (older) AI generation"""
    bl_idname = "style_engine.prev_generation"
    bl_label = "Previous Generation"
    bl_description = "View the previous (older) AI generation"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import workspace_setup

        props = context.scene.style_engine_props
        generations = workspace_setup.get_generation_list(context)
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}

        n = len(generations)
        # -1 means "newest" (index n-1 in the list)
        current_idx = (n - 1) if props.current_generation_index == -1 else props.current_generation_index
        new_idx = current_idx - 1

        if new_idx < 0:
            self.report({'INFO'}, "Already at the oldest generation")
            return {'CANCELLED'}

        gen_path = generations[new_idx]
        workspace_setup.load_generation_to_current(context, gen_path)
        _restore_generation_resolution(context, gen_path)
        props.current_generation_index = new_idx

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class WM_OT_NextGeneration(bpy.types.Operator):
    """Navigate to the next (newer) AI generation"""
    bl_idname = "style_engine.next_generation"
    bl_label = "Next Generation"
    bl_description = "View the next (newer) AI generation"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import workspace_setup

        props = context.scene.style_engine_props
        generations = workspace_setup.get_generation_list(context)
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}

        n = len(generations)
        if props.current_generation_index == -1:
            self.report({'INFO'}, "Already at the newest generation")
            return {'CANCELLED'}

        new_idx = props.current_generation_index + 1
        gen_path = generations[new_idx]
        workspace_setup.load_generation_to_current(context, gen_path)
        _restore_generation_resolution(context, gen_path)

        # -1 signals "newest" once we reach the last entry
        props.current_generation_index = -1 if new_idx >= n - 1 else new_idx

        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class WM_OT_LoadReferenceImage(bpy.types.Operator):
    """Load a reference image into a slot"""
    bl_idname = "style_engine.load_reference"
    bl_label = "Load Reference Image"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    filter_image: bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    filter_folder: bpy.props.BoolProperty(
        default=True,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    slot: bpy.props.StringProperty(
        name="Slot",
        description="Which slot to load the image into (st1, comp2, sst3, etc.)",
        default=""
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
        
        if not self.slot:
            self.report({'ERROR'}, "No slot specified")
            return {'CANCELLED'}
        
        try:
            print(f"\n{'='*60}")
            print(f"[Reference Image Load] Starting load for slot: {self.slot}")
            print(f"[Reference Image Load] File path: {self.filepath}")
            
            # Load image into Blender's image library
            img = bpy.data.images.load(self.filepath, check_existing=True)
            print(f"[Reference Image Load] Image loaded: {img.name}")
            print(f"[Reference Image Load]   Size: {img.size[0]}x{img.size[1]}")
            print(f"[Reference Image Load]   Type: {img.type}")
            print(f"[Reference Image Load]   Source: {img.source}")
            print(f"[Reference Image Load]   Has data: {img.has_data}")
            print(f"[Reference Image Load]   Is dirty: {img.is_dirty}")
            
            # Pack the image to force Blender to load it and generate preview
            # This is needed for template_ID_preview() to show thumbnails
            if not img.packed_file:
                print(f"[Reference Image Load] Packing image...")
                img.pack()
                print(f"[Reference Image Load]   Packed file size: {img.packed_file.size if img.packed_file else 'None'}")
            else:
                print(f"[Reference Image Load] Image already packed")
            
            # Force pixels to load FIRST (needed before GL load)
            print(f"[Reference Image Load] Loading pixel data...")
            img.reload()
            pixels_len = len(img.pixels)
            print(f"[Reference Image Load]   Pixels loaded: {pixels_len} values")
            
            # Force GL texture load (requires pixels to be loaded)
            print(f"[Reference Image Load] Forcing GL texture load...")
            img.gl_load()
            print(f"[Reference Image Load]   GL loaded: {img.bindcode}")
            
            # CRITICAL: Generate preview icon for UI display
            print(f"[Reference Image Load] Generating preview icon...")
            img.preview_ensure()
            if img.preview:
                print(f"[Reference Image Load]   Preview icon ID: {img.preview.icon_id}")
                print(f"[Reference Image Load]   Preview size: {img.preview.image_size}")
            else:
                print(f"[Reference Image Load]   ⚠️ Preview is None!")
            
            # Force update
            img.update()
            print(f"[Reference Image Load] Image updated")
            
            # Assign to the specified slot
            props = context.scene.style_engine_props
            img_prop = f"{self.slot}_image"
            weight_prop = f"{self.slot}_weight"
            
            print(f"[Reference Image Load] Assigning to property: {img_prop}")
            setattr(props, img_prop, img)
            
            # Auto-enable by setting weight to 1.0 (SDXL slots only; Gemini slots have no weights)
            if hasattr(props, weight_prop):
                current_weight = getattr(props, weight_prop)
                if current_weight == 0.0:
                    setattr(props, weight_prop, 1.0)
                    print(f"[Reference Image Load] Weight set to 1.0")
                else:
                    print(f"[Reference Image Load] Weight already at {current_weight}")
            
            # Force UI redraw for thumbnail to appear
            print(f"[Reference Image Load] Forcing UI redraw...")
            for area in context.screen.areas:
                area.tag_redraw()
            
            print(f"[Reference Image Load] ✅ Complete!")
            print(f"{'='*60}\n")
            
            self.report({'INFO'}, f"Loaded {img.name} into {self.slot.upper()}")
            print(f"[Style Engine] ✓ Loaded reference image: {img.name} → {self.slot.upper()} (packed)")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to load image: {e}")
            print(f"[Style Engine] ❌ Error loading reference image: {e}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class WM_OT_ClearReferenceImage(bpy.types.Operator):
    """Clear a reference image slot"""
    bl_idname = "style_engine.clear_reference"
    bl_label = "Clear Reference Image"
    bl_options = {'REGISTER', 'UNDO'}
    
    slot: bpy.props.StringProperty(
        name="Slot",
        description="Which slot to clear (st1, comp2, sst3, etc.)",
        default=""
    )
    
    def execute(self, context):
        if not self.slot:
            self.report({'ERROR'}, "No slot specified")
            return {'CANCELLED'}
        
        try:
            props = context.scene.style_engine_props
            img_prop = f"{self.slot}_image"
            weight_prop = f"{self.slot}_weight"
            
            # Clear the image
            setattr(props, img_prop, None)
            
            # Reset weight to 0
            setattr(props, weight_prop, 0.0)
            
            self.report({'INFO'}, f"Cleared {self.slot.upper()}")
            print(f"[Style Engine] ✓ Cleared reference image: {self.slot.upper()}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to clear slot: {e}")
            print(f"[Style Engine] ❌ Error clearing reference slot: {e}")
            return {'CANCELLED'}


class WM_OT_ReloadReferenceImage(bpy.types.Operator):
    """Reload a reference image from disk"""
    bl_idname = "style_engine.reload_reference"
    bl_label = "Reload Reference Image"
    bl_options = {'REGISTER', 'UNDO'}
    
    slot: bpy.props.StringProperty(
        name="Slot",
        description="Which slot to reload (st1, comp2, sst3, etc.)",
        default=""
    )
    
    def execute(self, context):
        if not self.slot:
            self.report({'ERROR'}, "No slot specified")
            return {'CANCELLED'}
        
        try:
            props = context.scene.style_engine_props
            img_prop = f"{self.slot}_image"
            img = getattr(props, img_prop)
            
            if not img:
                self.report({'WARNING'}, f"No image in {self.slot.upper()}")
                return {'CANCELLED'}
            
            # Reload the image from disk
            img.reload()
            
            # Pack if not already packed (for preview generation)
            if not img.packed_file:
                img.pack()
            
            # Force GL load
            img.gl_load()
            
            # CRITICAL: Regenerate preview icon
            img.preview_ensure()
            
            # Force update
            img.update()
            
            # Force UI redraw for thumbnail to update
            for area in context.screen.areas:
                area.tag_redraw()
            
            self.report({'INFO'}, f"Reloaded {img.name}")
            print(f"[Style Engine] ✓ Reloaded reference image: {img.name}")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reload image: {e}")
            print(f"[Style Engine] ❌ Error reloading reference image: {e}")
            return {'CANCELLED'}


class WM_OT_CancelGeneration(bpy.types.Operator):
    """Cancel active RunComfy generation"""
    bl_idname = "style_engine.cancel_generation"
    bl_label = "Cancel Generation"
    bl_description = "Cancel the active cloud generation request"
    
    request_id: bpy.props.StringProperty()
    
    def execute(self, context):
        from . import runcomfy_polling
        
        if runcomfy_polling.RunComfyPoller.cancel_request(self.request_id):
            self.report({'INFO'}, f"Cancelled request {self.request_id[:8]}")
            print(f"[Style Engine] Cancelled request {self.request_id[:8]}")
        else:
            self.report({'WARNING'}, "Request not found or already completed")
        
        return {'FINISHED'}


class WM_OT_RefreshLoraList(bpy.types.Operator):
    """Refresh LoRa list from ComfyUI server"""
    bl_idname = "style_engine.refresh_lora_list"
    bl_label = "Refresh LoRa List"
    bl_description = "Fetch latest LoRa models from ComfyUI server (clears 5-min cache)"
    
    def execute(self, context):
        # Clear cache
        global _lora_cache
        _lora_cache['items'] = []
        _lora_cache['timestamp'] = 0
        
        # Trigger refresh by accessing the property
        props = context.scene.style_engine_props
        current = props.lora_name
        
        # Force UI update
        for area in context.screen.areas:
            area.tag_redraw()
        
        self.report({'INFO'}, "LoRa list refreshed from server")
        print("[Style Engine] LoRa cache cleared - will refresh on next dropdown open")
        
        return {'FINISHED'}


class WM_OT_LoadLoraKeywords(bpy.types.Operator):
    """Load trigger keywords for the selected LoRa into the <k> tag"""
    bl_idname = "style_engine.load_lora_keywords"
    bl_label = "Load Keywords"
    bl_description = "Load trigger keywords for the selected LoRa(s) into the <k> tag in the prompt editor"
    
    def execute(self, context):
        import re
        from pathlib import Path
        from . import workspace_setup
        
        props = context.scene.style_engine_props
        
        # 1. Load keywords.txt
        addon_dir = Path(__file__).parent
        keywords_file = addon_dir / "loras" / "keywords.txt"
        
        if not keywords_file.exists():
            self.report({'ERROR'}, "keywords.txt not found")
            print(f"[Load Keywords] ❌ File not found: {keywords_file}")
            return {'CANCELLED'}
        
        # Parse keywords.txt (format: "filename.safetensors: "keywords here"")
        keyword_map = {}
        with open(keywords_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Split on first colon
                if ':' in line:
                    parts = line.split(':', 1)
                    lora_name = parts[0].strip()
                    keywords_raw = parts[1].strip().strip('"').strip()
                    if lora_name and keywords_raw:
                        keyword_map[lora_name] = keywords_raw
        
        if not keyword_map:
            self.report({'ERROR'}, "keywords.txt is empty or has no valid entries")
            return {'CANCELLED'}
        
        print(f"[Load Keywords] Loaded {len(keyword_map)} keyword entries")
        
        # 2. Collect keywords from active LoRAs
        collected_keywords = []
        
        if props.lora_enabled and props.lora_name != 'NONE':
            if props.lora_name in keyword_map:
                collected_keywords.append(keyword_map[props.lora_name])
                print(f"[Load Keywords] LoRa 1 ({props.lora_name}): {keyword_map[props.lora_name]}")
            else:
                print(f"[Load Keywords] LoRa 1 ({props.lora_name}): No keywords found")
        
        if props.lora2_enabled and props.lora2_name != 'NONE':
            if props.lora2_name in keyword_map:
                collected_keywords.append(keyword_map[props.lora2_name])
                print(f"[Load Keywords] LoRa 2 ({props.lora2_name}): {keyword_map[props.lora2_name]}")
            else:
                print(f"[Load Keywords] LoRa 2 ({props.lora2_name}): No keywords found")
        
        if not collected_keywords:
            self.report({'WARNING'}, "No keywords found for selected LoRa(s)")
            return {'CANCELLED'}
        
        # 3. Get text editor
        text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
        if not text_block:
            self.report({'ERROR'}, "STYLEENGINE_Prompt text block not found")
            return {'CANCELLED'}
        
        # Save before snapshot
        workspace_setup.save_prompt_snapshot(context, prefix="before_keywords")
        
        # 4. Insert into <k> tag
        current_content = text_block.as_string()
        new_keywords = ', '.join(collected_keywords)
        
        k_match = re.search(r'<k>(.*?)</k>', current_content, re.DOTALL | re.IGNORECASE)
        if k_match:
            existing_k = k_match.group(1).strip()
            if existing_k:
                # Append to existing keywords
                final_keywords = existing_k + ', ' + new_keywords
            else:
                final_keywords = new_keywords
            new_content = re.sub(
                r'(<k>)(.*?)(</k>)',
                r'\1' + final_keywords + r'\3',
                current_content,
                flags=re.DOTALL | re.IGNORECASE
            )
        else:
            # No <k> tag, add one at the top
            new_content = f"<k>{new_keywords}</k>\n" + current_content
        
        text_block.clear()
        text_block.write(new_content)
        
        # Save after snapshot
        workspace_setup.save_prompt_snapshot(context, prefix="after_keywords")
        
        self.report({'INFO'}, f"Keywords loaded: {new_keywords[:60]}...")
        print(f"[Load Keywords] ✓ Inserted into <k> tag: {new_keywords}")
        return {'FINISHED'}


class WM_OT_TestCloudGeneration(bpy.types.Operator):
    """Test workflow with current settings (dev tool)"""
    bl_idname = "style_engine.test_cloud_generation"
    bl_label = "Test Workflow"
    bl_description = "Test the workflow JSON with current settings (development/debugging)"
    
    def execute(self, context):
        from . import workspace_setup
        
        try:
            workspace_setup.generate_ai_image_cloud(context)
            self.report({'INFO'}, "Test workflow started")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to start test: {e}")
            print(f"[Style Engine] Error: {e}")
        
        return {'FINISHED'}


# ----------------------------------------------------------------
# 3. UI PANEL
# ----------------------------------------------------------------
class VIEW3D_PT_StyleEngine(bpy.types.Panel):
    """The main UI panel for the Style Engine."""
    bl_label = "Style Engine"
    bl_idname = "VIEW3D_PT_style_engine"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Style Engine'

    def draw(self, context):
        layout = self.layout
        style_props = context.scene.style_engine_props

        # ================================================================
        # SERVER STATUS (Always visible, non-collapsible)
        # ================================================================
        from . import progress_bar
        
        status_box = layout.box()
        
        # Row 1: Connection status with colored indicators
        # Green = idle/ready, Yellow = processing, Red = offline
        row = status_box.row(align=True)
        connection = progress_bar.get_connection_status()
        progress = progress_bar.get_display_progress()
        display_status = progress_bar.get_display_status()
        progress_pct = int(progress * 100)
        
        if connection != "connected":
            # RED: Offline/Disconnected
            row.label(text="", icon='KEYTYPE_EXTREME_VEC')
            row.label(text="Server: Offline")
        elif display_status == "ready" and (progress == 0 or progress >= 1.0):
            # GREEN: Online and Idle (explicitly ready, or finished at 100%)
            row.label(text="", icon='KEYTYPE_JITTER_VEC')
            row.label(text="Server: Ready")
        elif display_status in ("processing", "finishing") or (0 < progress < 1.0):
            # YELLOW: Actively processing (status says so, or progress is between 0-100%)
            row.label(text="", icon='KEYTYPE_KEYFRAME_VEC')
            row.label(text="Server: Working...")
        else:
            # GREEN: Default to ready for any other case
            row.label(text="", icon='KEYTYPE_JITTER_VEC')
            row.label(text="Server: Ready")
        
        # Row 2: Progress bar using Unicode block characters (pure display, no property)
        row = status_box.row(align=True)
        bar_length = 15  # Reduced from 20 to fit panel width
        filled = int(bar_length * progress)
        empty = bar_length - filled
        bar_text = "▓" * filled + "░" * empty
        row.label(text=f"{bar_text} {progress_pct}%")
        
        # Row 3: Current node/status (only when processing)
        node_name = progress_bar.get_display_node()
        if node_name and node_name != "Idle" and progress > 0:
            row = status_box.row(align=True)
            row.scale_y = 0.8
            row.label(text=f"  {node_name}", icon='NODE')
        
        # Row 4: Queue (only show if > 0)
        last_status = progress_bar.get_last_status()
        queue = last_status.get('queue_remaining', 0) if last_status else 0
        if queue > 0:
            row = status_box.row(align=True)
            row.scale_y = 0.8
            row.label(text=f"Queue: {queue}", icon='LINENUMBERS_ON')

        # ================================================================
        # VIEW CATEGORY (Collapsible) — Q · visibility
        # ================================================================
        view_box = layout.box()
        view_header = view_box.row(align=True)
        view_icon = 'TRIA_DOWN' if style_props.show_view_settings else 'TRIA_RIGHT'
        view_header.prop(style_props, "show_view_settings", text="View", icon=view_icon, emboss=False, toggle=True)
        view_header.label(text="", icon='VIEW_CAMERA')

        if style_props.show_view_settings:
            # Visualization Type Buttons (SDXL only)
            if style_props.ai_model != 'GEMINI':
                col = view_box.column(align=True)
                col.label(text="Visualization:")
                row = col.row(align=True)
                row.scale_y = 1.3
                op = row.operator("style_engine.set_visualization", text="Combined", icon='IMAGE_DATA',
                                  depress=(style_props.visualization_type == 'COMBINED'))
                op.viz_type = 'COMBINED'
                op = row.operator("style_engine.set_visualization", text="Silhouette", icon='MESH_PLANE',
                                  depress=(style_props.visualization_type == 'CANNY'))
                op.viz_type = 'CANNY'
                op = row.operator("style_engine.set_visualization", text="Depth", icon='EMPTY_SINGLE_ARROW',
                                  depress=(style_props.visualization_type == 'DEPTH'))
                op.viz_type = 'DEPTH'

            # Background Opacity
            view_box.separator()
            col = view_box.column(align=True)
            col.label(text="Background Opacity:")
            col.prop(style_props, "background_opacity", text="", slider=True)

            # Generation Browser
            view_box.separator()
            col = view_box.column(align=True)
            col.label(text="Generation Browser:")
            from . import workspace_setup
            generations = workspace_setup.get_generation_list(context)
            if generations:
                row = col.row(align=True)
                row.scale_y = 1.2
                at_oldest = (style_props.current_generation_index == 0)
                at_latest = (style_props.current_generation_index == -1)
                prev_row = row.row(align=True)
                prev_row.enabled = not at_oldest
                prev_row.operator("style_engine.prev_generation", text="", icon='TRIA_LEFT')
                if at_latest:
                    current_text = f"Latest ({len(generations)})"
                else:
                    current_text = f"{style_props.current_generation_index + 1}/{len(generations)}"
                row.label(text=current_text)
                next_row = row.row(align=True)
                next_row.enabled = not at_latest
                next_row.operator("style_engine.next_generation", text="", icon='TRIA_RIGHT')
            else:
                col.label(text="No generations yet", icon='INFO')

        # ================================================================
        # FILE CATEGORY (Collapsible) — Q · workspace
        # ================================================================
        layout.separator()
        file_box = layout.box()
        file_header = file_box.row(align=True)
        icon = 'TRIA_DOWN' if style_props.show_file_settings else 'TRIA_RIGHT'
        file_header.prop(style_props, "show_file_settings", text="File", icon=icon, emboss=False, toggle=True)
        file_header.label(text="", icon='FILE_FOLDER')

        if style_props.show_file_settings:
            col = file_box.column(align=True)
            col.label(text="Output Path:")
            col.prop(style_props, "output_path", text="")

            # Resolution — hidden when Gemini is active (uses render resolution directly)
            if style_props.ai_model != 'GEMINI':
                file_box.separator()
                col = file_box.column(align=True)
                col.label(text="Resolution:")
                col.prop(style_props, "ai_resolution", text="")

            file_box.separator()
            row = file_box.row(align=True)
            row.prop(style_props, "seed_value", text="Seed")
            row.operator("style_engine.reroll_seed", text="", icon='FILE_REFRESH')

            file_box.separator()
            col = file_box.column(align=True)
            col.label(text="Model:")
            col.prop(style_props, "ai_model", text="")

        # ================================================================
        # IMAGE GENERATION CATEGORY (Collapsible) — Q · image
        # ================================================================
        layout.separator()
        img_gen_box = layout.box()
        img_gen_header = img_gen_box.row(align=True)
        img_gen_icon = 'TRIA_DOWN' if style_props.show_image_generation_main else 'TRIA_RIGHT'
        img_gen_header.prop(style_props, "show_image_generation_main", text="Image Generation", icon=img_gen_icon, emboss=False, toggle=True)
        img_gen_header.label(text="", icon='IMAGE_DATA')

        if style_props.show_image_generation_main:
            # Always-visible: Generate Image + Upload companion
            row = img_gen_box.row(align=True)
            row.scale_y = 2.0
            row.operator("style_engine.generate_ai_quick", text="Generate Image", icon='IMAGE_DATA')
            row.operator("style_engine.upload_current_ai", text="", icon='IMPORT')

            # Always-visible: Refine Current Image
            refine_row = img_gen_box.row(align=True)
            refine_row.scale_y = 1.3
            refine_row.operator("style_engine.refine_current_image", text="Refine Current Image", icon='IMAGE_REFERENCE')

            # ── Settings (collapsible) ──────────────────────────────────
            img_gen_box.separator()
            settings_box = img_gen_box.box()
            settings_header = settings_box.row(align=True)
            settings_icon = 'TRIA_DOWN' if style_props.show_influence else 'TRIA_RIGHT'
            settings_header.prop(style_props, "show_influence", text="Settings", icon=settings_icon, emboss=False, toggle=True)
            settings_header.label(text="", icon='PREFERENCES')

            if style_props.show_influence:
                if style_props.ai_model == 'GEMINI':
                    # ── Gemini controls ───────────────────────────────────────
                    col = settings_box.column(align=True)
                    col.prop(style_props, "gemini_temperature", text="Temperature", slider=True)
                    col.prop(style_props, "gemini_image_size", text="Size")
                    col.prop(style_props, "gemini_instructions", text="Instructions")

                    settings_box.separator()
                    row = settings_box.row(align=True)
                    row.scale_y = 1.3
                    row.prop(style_props, "gemini_alignment", text="Alignment", toggle=True, icon='CON_LOCLIKE')
                    row.prop(style_props, "gemini_remove_bg", text="Remove BG", toggle=True, icon='IMAGE_ALPHA')

                    w = context.scene.render.resolution_x
                    h = context.scene.render.resolution_y
                    settings_box.label(text=f"Aspect: {w}x{h}", icon='FULLSCREEN_ENTER')

                    # Gemini Reference Images
                    settings_box.separator()
                    gref_box = settings_box.box()
                    gref_header = gref_box.row(align=True)
                    gref_icon = 'TRIA_DOWN' if style_props.show_gemini_references else 'TRIA_RIGHT'
                    gref_header.prop(style_props, "show_gemini_references", text="Reference Images", icon=gref_icon, emboss=False, toggle=True)
                    gref_header.label(text="", icon='IMAGE_REFERENCE')

                    if style_props.show_gemini_references:
                        gemini_ref_slots = [
                            ("gemini_ref1", "gemini_ref1_image", "REF1"),
                            ("gemini_ref2", "gemini_ref2_image", "REF2"),
                            ("gemini_ref3", "gemini_ref3_image", "REF3"),
                            ("gemini_ref4", "gemini_ref4_image", "REF4"),
                            ("gemini_ref5", "gemini_ref5_image", "REF5"),
                        ]
                        gref_box.separator()
                        grid = gref_box.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
                        for slot_id, img_prop, label in gemini_ref_slots:
                            img = getattr(style_props, img_prop)
                            card = grid.box()
                            card.scale_y = 1.0
                            if img:
                                col = card.column(align=True)
                                preview_box = col.box()
                                preview_col = preview_box.column(align=True)
                                try:
                                    pcoll = preview_collections.get("ref_images")
                                    if pcoll is not None:
                                        thumb_key = f"{slot_id}_{img.name}"
                                        if thumb_key not in pcoll:
                                            if img.filepath:
                                                abs_path = bpy.path.abspath(img.filepath)
                                                try:
                                                    pcoll.load(thumb_key, abs_path, 'IMAGE')
                                                except Exception:
                                                    pass
                                        if thumb_key in pcoll and pcoll[thumb_key].icon_id > 0:
                                            preview_col.template_icon(icon_value=pcoll[thumb_key].icon_id, scale=5.0)
                                        else:
                                            preview_col.label(text="[Preview]", icon='IMAGE_DATA')
                                    else:
                                        preview_col.label(text="[No Collection]", icon='ERROR')
                                except Exception:
                                    preview_col.label(text="[Error]", icon='ERROR')
                                col.separator(factor=0.2)
                                info_col = col.column(align=True)
                                info_col.scale_y = 0.7
                                lbl_row = info_col.row()
                                lbl_row.alignment = 'CENTER'
                                lbl_row.label(text=label, icon='IMAGE_DATA')
                                name_row = info_col.row()
                                name_row.alignment = 'CENTER'
                                display_name = img.name[:10] + "..." if len(img.name) > 13 else img.name
                                name_row.label(text=display_name)
                                col.separator(factor=0.3)
                                btn_row = col.row(align=True)
                                btn_row.scale_y = 0.7
                                reload_op = btn_row.operator("style_engine.reload_reference", text="", icon='FILE_REFRESH')
                                reload_op.slot = slot_id
                                clear_op = btn_row.operator("style_engine.clear_reference", text="", icon='X')
                                clear_op.slot = slot_id
                            else:
                                col = card.column(align=True)
                                col.scale_y = 2.5
                                col.separator()
                                load_op = col.operator("style_engine.load_reference", text=f"{label}\n+", icon='ADD', emboss=True)
                                load_op.slot = slot_id
                                col.separator()

                else:
                    # ── SDXL controls ─────────────────────────────────────────
                    col = settings_box.column(align=True)
                    col.prop(style_props, "silhouette_influence", text="Silhouette", slider=True)
                    col.prop(style_props, "depth_influence", text="Depth", slider=True)
                    col.prop(style_props, "texture_influence", text="Viewport", slider=True)
                    settings_box.separator()
                    col = settings_box.column(align=True)
                    col.label(text="Steps:")
                    col.prop(style_props, "steps", text="", slider=True)

                    settings_box.separator()
                    rembg_row = settings_box.row(align=True)
                    rembg_row.scale_y = 1.3
                    rembg_row.prop(style_props, "sdxl_remove_bg", text="Remove BG", toggle=True, icon='IMAGE_ALPHA')

                    # Reference Images
                    settings_box.separator()
                    ref_box = settings_box.box()
                    ref_header = ref_box.row(align=True)
                    ref_icon = 'TRIA_DOWN' if style_props.show_reference_images else 'TRIA_RIGHT'
                    ref_header.prop(style_props, "show_reference_images", text="Reference Images", icon=ref_icon, emboss=False, toggle=True)
                    ref_header.label(text="", icon='IMAGE_REFERENCE')

                    if style_props.show_reference_images:
                        adv_row = ref_box.row(align=True)
                        adv_row.prop(style_props, "show_advanced_ref_controls", text="Advanced Control", toggle=True, icon='PREFERENCES')

                        def draw_reference_section(box, title, icon, show_prop, slots, strength_prop, show_weights=False):
                            section_box = box.box()
                            header = section_box.row(align=True)
                            icon_tri = 'TRIA_DOWN' if getattr(style_props, show_prop) else 'TRIA_RIGHT'
                            header.prop(style_props, show_prop, text=title, icon=icon_tri, emboss=False, toggle=True)
                            if getattr(style_props, show_prop):
                                section_box.separator()
                                strength_row = section_box.row()
                                strength_row.scale_y = 1.5
                                strength_row.prop(style_props, strength_prop, text="Global Strength", slider=True)
                                section_box.separator()
                                grid = section_box.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
                                for slot_id, img_prop, weight_prop, label in slots:
                                    img = getattr(style_props, img_prop)
                                    card = grid.box()
                                    card.scale_y = 1.0
                                    if img:
                                        col = card.column(align=True)
                                        preview_box = col.box()
                                        preview_col = preview_box.column(align=True)
                                        try:
                                            pcoll = preview_collections.get("ref_images")
                                            if pcoll is None:
                                                preview_col.label(text="[No Collection]", icon='ERROR')
                                            else:
                                                thumb_key = f"{slot_id}_{img.name}"
                                                if thumb_key not in pcoll:
                                                    if img.filepath:
                                                        abs_path = bpy.path.abspath(img.filepath)
                                                        try:
                                                            pcoll.load(thumb_key, abs_path, 'IMAGE')
                                                        except Exception as e:
                                                            print(f"[UI] Failed to load preview for {img.name}: {e}")
                                                if thumb_key in pcoll:
                                                    thumb = pcoll[thumb_key]
                                                    if thumb.icon_id > 0:
                                                        preview_col.template_icon(icon_value=thumb.icon_id, scale=5.0)
                                                    else:
                                                        preview_col.label(text="[Invalid Icon]", icon='IMAGE_DATA')
                                                else:
                                                    preview_col.label(text="[Not Loaded]", icon='IMAGE_DATA')
                                        except Exception as e:
                                            preview_col.label(text="[Error]", icon='ERROR')
                                        col.separator(factor=0.2)
                                        info_col = col.column(align=True)
                                        info_col.scale_y = 0.7
                                        label_row = info_col.row()
                                        label_row.alignment = 'CENTER'
                                        label_row.label(text=label, icon='IMAGE_DATA')
                                        name_row = info_col.row()
                                        name_row.alignment = 'CENTER'
                                        display_name = img.name[:10] + "..." if len(img.name) > 13 else img.name
                                        name_row.label(text=display_name)
                                        col.separator(factor=0.3)
                                        if show_weights:
                                            col.prop(style_props, weight_prop, text="", slider=True)
                                            col.separator(factor=0.2)
                                        btn_row = col.row(align=True)
                                        btn_row.scale_y = 0.7
                                        reload_op = btn_row.operator("style_engine.reload_reference", text="", icon='FILE_REFRESH')
                                        reload_op.slot = slot_id
                                        clear_op = btn_row.operator("style_engine.clear_reference", text="", icon='X')
                                        clear_op.slot = slot_id
                                    else:
                                        col = card.column(align=True)
                                        col.scale_y = 2.5
                                        col.separator()
                                        load_op = col.operator("style_engine.load_reference", text=f"{label}\n+", icon='ADD', emboss=True)
                                        load_op.slot = slot_id
                                        col.separator()

                        st_slots = [
                            ("st1", "st1_image", "st1_weight", "ST1"),
                            ("st2", "st2_image", "st2_weight", "ST2"),
                            ("st3", "st3_image", "st3_weight", "ST3"),
                            ("st4", "st4_image", "st4_weight", "ST4"),
                            ("st5", "st5_image", "st5_weight", "ST5"),
                        ]
                        draw_reference_section(ref_box, "Style", 'BRUSH_DATA',
                                               "show_style_transfer", st_slots, "style_transfer_strength",
                                               show_weights=style_props.show_advanced_ref_controls)

                        comp_slots = [
                            ("comp1", "comp1_image", "comp1_weight", "COMP1"),
                            ("comp2", "comp2_image", "comp2_weight", "COMP2"),
                            ("comp3", "comp3_image", "comp3_weight", "COMP3"),
                            ("comp4", "comp4_image", "comp4_weight", "COMP4"),
                            ("comp5", "comp5_image", "comp5_weight", "COMP5"),
                        ]
                        draw_reference_section(ref_box, "Composition", 'MESH_GRID',
                                               "show_composition", comp_slots, "composition_strength",
                                               show_weights=style_props.show_advanced_ref_controls)

                    # LoRas
                    settings_box.separator()
                    lora_box = settings_box.box()
                    lora_header = lora_box.row(align=True)
                    lora_icon = 'TRIA_DOWN' if style_props.show_loras else 'TRIA_RIGHT'
                    lora_header.prop(style_props, "show_loras", text="LoRas", icon=lora_icon, emboss=False, toggle=True)
                    lora_header.label(text="", icon='MODIFIER')

                    if style_props.show_loras:
                        lora_col = lora_box.column(align=False)
                        lora1_box = lora_col.box()
                        lora1_col = lora1_box.column(align=True)
                        row = lora1_col.row()
                        row.scale_y = 1.4
                        row.prop(style_props, "lora_enabled", text="Use LoRa", toggle=True, icon='MODIFIER')
                        if style_props.lora_enabled:
                            lora1_col.separator(factor=0.3)
                            refresh_row = lora1_col.row(align=True)
                            refresh_row.prop(style_props, "lora_name", text="")
                            refresh_row.operator("style_engine.refresh_lora_list", text="", icon='FILE_REFRESH')
                            lora1_col.prop(style_props, "lora_strength_model", text="Strength", slider=True)
                        lora2_box = lora_col.box()
                        lora2_col = lora2_box.column(align=True)
                        lora2_col.prop(style_props, "lora2_enabled", text="Use LoRa 2", toggle=True, icon='MODIFIER')
                        if style_props.lora2_enabled:
                            lora2_col.separator(factor=0.3)
                            lora2_col.prop(style_props, "lora2_name", text="")
                            lora2_col.prop(style_props, "lora2_strength_model", text="Strength", slider=True)
                        lora_col.separator(factor=0.3)
                        lora_col.operator("style_engine.load_lora_keywords", text="Load Keywords", icon='TEXT')
                        active_loras = []
                        if style_props.lora_enabled and style_props.lora_name != 'NONE':
                            active_loras.append(f"L1: {style_props.lora_name.replace('.safetensors', '')[:12]}")
                        if style_props.lora2_enabled and style_props.lora2_name != 'NONE':
                            active_loras.append(f"L2: {style_props.lora2_name.replace('.safetensors', '')[:12]}")
                        if active_loras:
                            info_row = lora_col.row()
                            info_row.scale_y = 0.7
                            info_row.label(text=", ".join(active_loras), icon='CHECKMARK')

            # ── Refine Image (collapsible) ─────────────────────────────────
            img_gen_box.separator()
            ri_box = img_gen_box.box()
            ri_header = ri_box.row(align=True)
            ri_icon = 'TRIA_DOWN' if style_props.show_refine_image else 'TRIA_RIGHT'
            ri_header.prop(style_props, "show_refine_image", text="Refine Image", icon=ri_icon, emboss=False, toggle=True)
            ri_header.label(text="", icon='TEXTURE')

            if style_props.show_refine_image:
                # ── Top action row ─────────────────────────────────────────
                top_row = ri_box.row(align=True)
                top_row.scale_y = 1.2
                top_row.operator("style_engine.refine_image_analyze_json", text="Analyze Image → JSON", icon='VIEWZOOM')
                top_row.operator("style_engine.refine_image_paste_json", text="", icon='PASTEDOWN')

                ri_box.separator()

                # ── Metadata ───────────────────────────────────────────────
                meta_box = ri_box.box()
                meta_col = meta_box.column(align=True)
                meta_row = meta_col.row()
                meta_row.label(text="Metadata", icon='INFO')
                meta_col.prop(style_props, "refine_meta_filename", text="Filename")
                meta_col.prop(style_props, "refine_meta_dimensions", text="Dimensions")
                meta_col.prop(style_props, "refine_meta_aspect", text="Aspect")

                # ── Visual Style ───────────────────────────────────────────
                vs_box = ri_box.box()
                vs_col = vs_box.column(align=True)
                vs_col.label(text="Visual Style", icon='BRUSH_DATA')
                vs_col.prop(style_props, "refine_style_art_style", text="Art Style")
                vs_col.prop(style_props, "refine_style_medium", text="Medium")
                vs_col.prop(style_props, "refine_style_lighting", text="Lighting")

                # ── Composition ────────────────────────────────────────────
                comp_box = ri_box.box()
                comp_col = comp_box.column(align=True)
                comp_col.label(text="Composition", icon='MESH_GRID')
                comp_col.prop(style_props, "refine_comp_perspective", text="Perspective")
                comp_col.prop(style_props, "refine_comp_focal_point", text="Focal Point")

                # ── Subjects (dynamic list) ────────────────────────────────
                subj_box = ri_box.box()
                subj_hdr = subj_box.row()
                subj_hdr.label(text="Subjects", icon='OBJECT_DATA')
                subj_hdr.operator("style_engine.refine_image_add_subject", text="", icon='ADD')

                for si, subj in enumerate(style_props.refine_subjects):
                    s_box = subj_box.box()
                    s_hdr = s_box.row(align=True)
                    exp_icon = 'TRIA_DOWN' if subj.show_expanded else 'TRIA_RIGHT'
                    s_hdr.prop(subj, "show_expanded", text="", icon=exp_icon, emboss=False)
                    s_hdr.prop(subj, "label", text="")
                    rem_subj_op = s_hdr.operator("style_engine.refine_image_remove_subject", text="", icon='X')
                    rem_subj_op.subject_index = si

                    if subj.show_expanded:
                        s_col = s_box.column(align=True)
                        s_col.prop(subj, "style", text="Style")
                        s_col.prop(subj, "scale", text="Scale")
                        s_col.prop(subj, "color", text="Color")
                        s_col.prop(subj, "material", text="Material")

                        feat_hdr = s_box.row()
                        feat_hdr.label(text="Features", icon='LINENUMBERS_ON')
                        add_feat_op = feat_hdr.operator("style_engine.refine_image_add_feature", text="", icon='ADD')
                        add_feat_op.subject_index = si

                        for fi, feat in enumerate(subj.features):
                            feat_row = s_box.row(align=True)
                            feat_row.prop(feat, "value", text="")
                            rem_feat_op = feat_row.operator("style_engine.refine_image_remove_feature", text="", icon='X')
                            rem_feat_op.subject_index = si
                            rem_feat_op.feature_index = fi

                # ── Thematic Tags ──────────────────────────────────────────
                tags_box = ri_box.box()
                tags_hdr = tags_box.row()
                tags_hdr.label(text="Thematic Tags", icon='BOOKMARKS')
                tags_hdr.operator("style_engine.refine_image_add_tag", text="", icon='ADD')

                for ti, tag in enumerate(style_props.refine_tags):
                    tag_row = tags_box.row(align=True)
                    tag_row.prop(tag, "value", text="")
                    rem_tag_op = tag_row.operator("style_engine.refine_image_remove_tag", text="", icon='X')
                    rem_tag_op.tag_index = ti

                # ── Submit ─────────────────────────────────────────────────
                ri_box.separator()
                struct_row = ri_box.row()
                struct_icon = 'CHECKBOX_HLT' if style_props.use_structured_editing else 'CHECKBOX_DEHLT'
                struct_row.prop(style_props, "use_structured_editing", text="Use structured editing", icon=struct_icon)
                submit_row = ri_box.row()
                submit_row.scale_y = 1.5
                submit_row.operator("style_engine.refine_image_submit", text="Refine with Agent", icon='RENDER_RESULT')

        # ================================================================
        # AGENT CATEGORY (Collapsible) — W
        # ================================================================
        layout.separator()
        agent_box = layout.box()
        agent_header = agent_box.row(align=True)
        agent_icon = 'TRIA_DOWN' if style_props.show_text_generation else 'TRIA_RIGHT'
        agent_header.prop(style_props, "show_text_generation", text="Agent", icon=agent_icon, emboss=False, toggle=True)
        agent_header.label(text="", icon='OUTLINER_OB_SPEAKER')

        if style_props.show_text_generation:
            agent_box.prop(style_props, "prompt_llm_profile", text="Agents")
            row = agent_box.row()
            row.scale_y = 2.0
            row.operator("style_engine.refine_prompt", text="Refine Prompt", icon='SORTALPHA')

            agent_box.separator()
            col = agent_box.column(align=True)
            col.scale_y = 1.2
            col.operator("style_engine.generate_image_description", text="Describe Current Image", icon='FILE_TEXT')
            col.operator("style_engine.generate_image_description_from_file", text="Describe Image from File", icon='FILEBROWSER')
            col.operator("style_engine.generate_image_description_from_viewport", text="Describe Viewport", icon='VIEW_CAMERA')

            # ── Scene Context (sent to AI as ground-truth metadata) ──────────
            agent_box.separator()
            ctx_box = agent_box.box()
            ctx_col = ctx_box.column(align=True)
            ctx_col.scale_y = 0.85
            ctx_col.label(text="Scene Context  (injected into Agent):", icon='INFO')

            scene  = context.scene
            render = scene.render
            w, h   = render.resolution_x, render.resolution_y

            from math import gcd as _gcd
            import bpy as _bpy
            g  = _gcd(w, h)
            ar = f"{w // g}:{h // g}"
            blend_name = _bpy.path.basename(_bpy.data.filepath).replace(".blend", "") if _bpy.data.is_saved else "unsaved"
            ctx_col.label(text=f"  File:    {blend_name}")
            ctx_col.label(text=f"  Render:  {w} × {h}  ({ar})")

            cam_obj = scene.camera
            if cam_obj and cam_obj.type == 'CAMERA':
                cam = cam_obj.data
                ctx_col.label(text=f"  Camera:  {cam_obj.name}  —  {round(cam.lens, 1)} mm")
                dof = cam.dof
                if dof.use_dof:
                    focus = dof.focus_object.name if dof.focus_object else f"{round(dof.focus_distance, 2)} m"
                    ctx_col.label(text=f"  DoF:     f/{round(dof.aperture_fstop, 1)}  focus={focus}")
                else:
                    ctx_col.label(text="  DoF:     off")
            else:
                ctx_col.label(text="  Camera:  (none active — no camera data sent)")

            # # Helper text box - COMMENTED OUT FOR MINIMAL UI
            # prompt_box.separator()
            # help_box = prompt_box.box()
            # help_box.scale_y = 0.8
            # col = help_box.column(align=True)
            # col.label(text="Available templates loaded in text editor:", icon='TEXT')
            # col.label(text="• STYLEENGINE_Cinematic_Scene")
            # col.label(text="• STYLEENGINE_Fantasy_Dragon")
            # col.label(text="• STYLEENGINE_Portrait_Photo")
            # col.label(text="• (+ your custom templates)")
            # col.separator()
            # col.label(text="Use tags in STYLEENGINE_Prompt:", icon='INFO')
            # col.label(text="<subject> <style> <details> <environment>")
            # col.label(text="<mood> <camera> <lighting> <negative_prompt>")

        # # --- Server Status Indicator (TOP) --- COMMENTED OUT
        # status_box = layout.box()
        # row = status_box.row()
        # row.label(text="Server:", icon='WORLD')
        # 
        # # Get server status from poller
        # try:
        #     from . import runcomfy_polling
        #     server_status = runcomfy_polling.RunComfyPoller.get_server_status()
        #     
        #     status_icons = {
        #         'Idle': 'CHECKMARK',
        #         'Queued': 'TIME',
        #         'Active': 'CHECKMARK',
        #         'Generating': 'RENDER_ANIMATION'
        #     }
        #     row.label(text=server_status, icon=status_icons.get(server_status, 'QUESTION'))
        #     
        #     # Show active requests details if any
        #     if runcomfy_polling.RunComfyPoller.active_requests:
        #         for request_id, state in runcomfy_polling.RunComfyPoller.active_requests.items():
        #             row = status_box.row()
        #             import time
        #             elapsed = int(time.time() - state.start_time)
        #             row.label(text=f"  {state.workflow_type}: {elapsed}s", icon='DOT')
        #             
        #             # Cancel button
        #             cancel_op = row.operator("style_engine.cancel_generation", text="", icon='X')
        #             cancel_op.request_id = request_id
        # except Exception as e:
        #     row.label(text="Error", icon='ERROR')
        
        # # --- Workspace Setup - COLLAPSIBLE --- COMMENTED OUT
        # layout.separator()
        # setup_box = layout.box()
        # header_row = setup_box.row(align=True)
        # icon = 'TRIA_DOWN' if style_props.show_workspace_setup else 'TRIA_RIGHT'
        # header_row.prop(style_props, "show_workspace_setup", text="Workspace Setup", icon=icon, emboss=False, toggle=True)
        # 
        # if style_props.show_workspace_setup:
        #     setup_box.operator("style_engine.setup_workspace", icon='WINDOW')
        #     
        #     # Show camera reposition button if AI camera exists
        #     prefs = context.preferences.addons['styleengine'].preferences
        #     camera_name = prefs.camera_name_override
        #     if camera_name in bpy.data.objects:
        #         setup_box.operator("style_engine.align_camera_to_view", 
        #                            text="Reposition AI Camera", 
        #                            icon='VIEW_CAMERA')
        #     
        #     # Resolution dropdown (moved up)
        #     setup_box.separator()
        #     setup_box.label(text="Set Resolution:")
        #     setup_box.prop(style_props, "ai_resolution", text="")
        #     
        #     # Background opacity slider
        #     setup_box.separator()
        #     setup_box.label(text="Background Opacity:")
        #     setup_box.prop(style_props, "background_opacity", slider=True, text="")
        #     
        #     # Background depth control buttons
        #     prefs = context.preferences.addons['styleengine'].preferences
        #     camera_name = prefs.camera_name_override
        #     if camera_name in bpy.data.objects:
        #         depth_row = setup_box.row(align=True)
        #         depth_row.operator("style_engine.bring_background_forward", icon='TRIA_UP')
        #         depth_row.operator("style_engine.send_background_back", icon='TRIA_DOWN')
        #     
        #     # Output path
        #     setup_box.separator()
        #     setup_box.label(text="Output Path:")
        #     setup_box.prop(style_props, "output_path", text="")
        #     
        #     # Save Iterations checkbox (moved to bottom)
        #     setup_box.separator()
        #     setup_box.prop(style_props, "save_iterations", icon='FILE_TICK')
        
        # # --- Image Generation - COLLAPSIBLE --- COMMENTED OUT
        # layout.separator()
        # gen_box = layout.box()
        # header_row = gen_box.row(align=True)
        # icon = 'TRIA_DOWN' if style_props.show_image_generation else 'TRIA_RIGHT'
        # header_row.prop(style_props, "show_image_generation", text="Image Generation", icon=icon, emboss=False, toggle=True)
        # 
        # if style_props.show_image_generation:
        #     # # Lookup - COMMENTED OUT
        #     # gen_box.separator()
        #     # col = gen_box.column(align=True)
        #     # col.label(text="Lookup:")
        #     # col.prop(style_props, "lookup", text="")
        #     
        #     # # Global Prompt - COMMENTED OUT (now using text editor)
        #     # gen_box.separator()
        #     # col = gen_box.column(align=True)
        #     # 
        #     # # Info: Text editor is in workspace layout (bottom-right)
        #     # info_row = col.row(align=True)
        #     # info_row.label(text="Prompt (auto-syncs from text editor below camera)", icon='INFO')
        #     # 
        #     # col.separator()
        #     # 
        #     # # Quick view/edit (read-only preview of what will be used)
        #     # col.label(text="Current Prompt:", icon='TEXT')
        #     # col.prop(style_props, "global_prompt", text="")
        #     
        #     # Steps
        #     gen_box.separator()
        #     col = gen_box.column(align=True)
        #     col.label(text="Steps:")
        #     col.prop(style_props, "steps", slider=True, text="")
        #     
        #     # Influence section
        #     gen_box.separator()
        #     influence_box = gen_box.box()
        #     influence_box.label(text="Influence", icon='SHADERFX')
        #     influence_box.prop(style_props, "depth_influence", slider=True)
        #     influence_box.prop(style_props, "silhouette_influence", slider=True)
        #     
        #     # Image Reference section - COLLAPSIBLE
        #     gen_box.separator()
        #     ipadapter_box = gen_box.box()
        #     header_row = ipadapter_box.row(align=True)
        #     icon = 'TRIA_DOWN' if style_props.show_ipadapter else 'TRIA_RIGHT'
        #     header_row.prop(style_props, "show_ipadapter", text="Image Reference", icon=icon, emboss=False, toggle=True)
        #     
        #     if style_props.show_ipadapter:
        #         # Enable checkbox
        #         ipadapter_box.prop(style_props, "use_ipadapter", icon='IMAGE_DATA')
        #         
        #         # Only show controls if enabled
        #         if style_props.use_ipadapter:
        #             ipadapter_box.separator()
        #             
        #             # Reference image file picker
        #             col = ipadapter_box.column(align=True)
        #             col.label(text="Reference Image:")
        #             col.prop(style_props, "ipadapter_reference_image", text="")
        #             
        #             # Show filename if set
        #             if style_props.ipadapter_reference_image:
        #                 import os
        #                 filename = os.path.basename(style_props.ipadapter_reference_image)
        #                 col.label(text=f"📷 {filename}", icon='NONE')
        #             
        #             ipadapter_box.separator()
        #             
        #             # Weight type dropdown
        #             ipadapter_box.label(text="Mode:")
        #             ipadapter_box.prop(style_props, "ipadapter_weight_type", text="")
        #             
        #             ipadapter_box.separator()
        #             
        #             # Strength slider
        #             ipadapter_box.label(text="Strength:")
        #             ipadapter_box.prop(style_props, "ipadapter_strength", slider=True, text="")
        #             col = ipadapter_box.column(align=True)
        #             col.scale_y = 0.7
        #             col.label(text="(0.0 = Off, 5.0 = Max)")
        #     
        #     # Project Texture button
        #     gen_box.separator()
        #     gen_box.operator("style_engine.project_texture", icon='UV')
        #     
        #     # Generate Image - ONE-SHOT BUTTON (large, on top)
        #     gen_box.separator()
        #     gen_box.separator()
        #     gen_row = gen_box.row()
        #     gen_row.scale_y = 2.5  # Make it BIG
        #     gen_row.operator("style_engine.generate_ai_quick", text="Generate Image", icon='IMAGE_DATA')
        #     
        #     # Autogenerate - CONTINUOUS TOGGLE (smaller, below)
        #     gen_box.separator()
        #     gen_row = gen_box.row()
        #     gen_row.scale_y = 1.5  # Smaller than main button
        #     gen_row.prop(style_props, "auto_generate", text="Autogenerate", icon='FILE_REFRESH', toggle=True)
        #     
        #     # # Groups section - COMMENTED OUT FOR NOW
        #     # gen_box.separator()
        #     # groups_box = gen_box.box()
        #     # row = groups_box.row(align=True)
        #     #
        #     # icon = 'TRIA_DOWN' if style_props.show_groups else 'TRIA_RIGHT'
        #     # row.prop(style_props, "show_groups", text="Groups", icon=icon, emboss=False)
        #     #
        #     # if style_props.show_groups:
        #     #     # Group controls
        #     #     control_row = groups_box.row(align=True)
        #     #     control_row.operator("style_engine.add_group", icon='ADD', text="Add")
        #     #     control_row.operator("style_engine.assign_group", icon='LINK_BLEND', text="Assign")
        #     #     control_row.operator("style_engine.rename_group", icon='GREASEPENCIL', text="Rename")
        #     #     control_row.operator("style_engine.delete_group", icon='TRASH', text="Delete")
        #     #     
        #     #     groups_box.separator()
        #     #     
        #     #     # Show message if no groups
        #     #     if len(style_props.object_groups) == 0:
        #     #         groups_box.label(text="No groups. Click 'Add' to create one.", icon='INFO')
        #     #     else:
        #     #         # Dynamic groups display
        #     #         header = groups_box.row()
        #     #         header.label(text="")  # Selection column
        #     #         header.label(text="Group Name")
        #     #         header.label(text="Keywords")
        #     #         
        #     #         # Display all groups dynamically
        #     #         for idx, group in enumerate(style_props.object_groups):
        #     #             row = groups_box.row(align=True)
        #     #             
        #     #             # Selection radio button
        #     #             selected = style_props.active_group_index == idx
        #     #             row.operator("style_engine.select_group", text="", icon='RADIOBUT_ON' if selected else 'RADIOBUT_OFF', emboss=False).group_index = idx
        #     #             
        #     #             # Group name
        #     #             row.label(text=group.name.upper())
        #     #             
        #     #             # Keywords input
        #     #             row.prop(group, "keywords", text="")
        
        # ================================================================
        # 3D GENERATION CATEGORY (Collapsible) — E
        # ================================================================
        layout.separator()
        gen3d_box = layout.box()
        gen3d_header = gen3d_box.row(align=True)
        gen3d_icon = 'TRIA_DOWN' if style_props.show_3d_generation else 'TRIA_RIGHT'
        gen3d_header.prop(style_props, "show_3d_generation", text="3D Generation", icon=gen3d_icon, emboss=False, toggle=True)
        gen3d_header.label(text="", icon='MESH_CUBE')

        if style_props.show_3d_generation:
            # Generate 3D — main button
            row = gen3d_box.row()
            row.scale_y = 2.0
            row.operator("style_engine.trellis_generate", text="Generate 3D", icon='MESH_UVSPHERE')

            gen3d_box.separator(factor=0.5)
            t_col = gen3d_box.column(align=True)
            t_col.prop(style_props, "trellis_quality", text="")
            t_col.prop(style_props, "trellis_texture_size", text="Texture")

            t_row = gen3d_box.row(align=True)
            t_row.prop(style_props, "trellis_steps",    text="Steps")
            t_row.prop(style_props, "trellis_guidance", text="Guidance")

            gen3d_box.prop(style_props, "trellis_decimation", text="Max Polygons")

            rembg_row = gen3d_box.row(align=True)
            rembg_row.scale_y = 1.2
            rembg_row.prop(style_props, "trellis_remove_bg", text="Remove BG", toggle=True, icon='IMAGE_ALPHA')

            # Retexture advanced params
            gen3d_box.separator(factor=0.5)
            rt_col = gen3d_box.column(align=True)
            rt_col.scale_y = 0.9
            rt_col.label(text="Retexture params:", icon='MATSHADERBALL')
            rt_col.prop(style_props, "trellis_tex_resolution", text="Res")
            rt_col.prop(style_props, "trellis_tex_steps",    text="Steps")
            rt_col.prop(style_props, "trellis_tex_guidance", text="Guidance")

            # Model Browser
            gen3d_box.separator()
            col = gen3d_box.column(align=True)
            col.label(text="Model Browser:", icon='FILE_3D')
            from . import workspace_setup as _ws_3d
            models = _ws_3d.get_model_list(context)
            if models:
                row = col.row(align=True)
                row.scale_y = 1.2
                at_oldest = (style_props.current_model_index == 0)
                at_latest = (style_props.current_model_index == -1)
                prev_row = row.row(align=True)
                prev_row.enabled = not at_oldest
                prev_row.operator("style_engine.prev_model", text="", icon='TRIA_LEFT')
                if at_latest:
                    current_text = f"Latest ({len(models)})"
                else:
                    current_text = f"{style_props.current_model_index + 1}/{len(models)}"
                row.label(text=current_text)
                next_row = row.row(align=True)
                next_row.enabled = not at_latest
                next_row.operator("style_engine.next_model", text="", icon='TRIA_RIGHT')
                col.separator()
                spawn_row = col.row(align=True)
                spawn_row.scale_y = 1.3
                spawn_row.operator("style_engine.spawn_model", text="Spawn Model", icon='IMPORT')
            else:
                col.label(text="No models yet", icon='INFO')

        # ================================================================
        # REFINEMENT CATEGORY (Collapsible) — R
        # ================================================================
        layout.separator()
        refine_box = layout.box()
        refine_header = refine_box.row(align=True)
        refine_icon = 'TRIA_DOWN' if style_props.show_3d_single_image else 'TRIA_RIGHT'
        refine_header.prop(style_props, "show_3d_single_image", text="Refinement", icon=refine_icon, emboss=False, toggle=True)
        refine_header.label(text="", icon='OUTLINER_OB_SURFACE')

        if style_props.show_3d_single_image:
            # ── Refine Mesh (Omni) ─────────────────────────────────────────
            omni_box = refine_box.box()
            omni_col = omni_box.column(align=True)
            omni_col.label(text="Refine Mesh", icon='MESH_CUBE')
            row = omni_col.row()
            row.scale_y = 1.8
            row.operator("style_engine.omni_generate", text="Refine Mesh", icon='MESH_CUBE')

            omni_col.separator(factor=0.3)
            ctrl_col = omni_col.column(align=True)
            ctrl_col.scale_y = 0.9
            ctrl_col.prop(style_props, "omni_control_type", text="")
            ctrl_col.prop(style_props, "omni_guidance_scale", text="Guidance", slider=True)
            if style_props.omni_control_type in ('POINT', 'VOXEL'):
                ctrl_col.prop(style_props, "omni_remesh_depth", text="Remesh Depth", slider=True)
                ctrl_col.prop(style_props, "omni_precenter", text="Pre-center", toggle=True)
            if style_props.omni_control_type == 'BBOX':
                omni_col.separator(factor=0.3)
                omni_col.operator("style_engine.omni_bbox_debug", text="Calculate BBox", icon='SNAP_VOLUME')

            refine_box.separator()

            # ── Part Segmentation ──────────────────────────────────────────
            seg_box = refine_box.box()
            seg_col = seg_box.column(align=True)
            seg_col.label(text="Part Segmentation", icon='OUTLINER_OB_SURFACE')
            row = seg_col.row()
            row.scale_y = 1.8
            row.operator("style_engine.segment_mesh", text="Segment Mesh", icon='OUTLINER_OB_SURFACE')
            seg_col.separator(factor=0.3)
            param_col = seg_col.column(align=True)
            param_col.scale_y = 0.9
            param_col.prop(style_props, "part_point_num",  text="Point Samples")
            param_col.prop(style_props, "part_prompt_num", text="Query Points")

        # ================================================================
        # TEXTURE CATEGORY (Collapsible) — T
        # ================================================================
        layout.separator()
        tex_box = layout.box()
        tex_header = tex_box.row(align=True)
        tex_icon = 'TRIA_DOWN' if style_props.show_3d_multiview else 'TRIA_RIGHT'
        tex_header.prop(style_props, "show_3d_multiview", text="Texture", icon=tex_icon, emboss=False, toggle=True)
        tex_header.label(text="", icon='MATSHADERBALL')

        if style_props.show_3d_multiview:
            # Project Texture — main action
            row = tex_box.row()
            row.scale_y = 1.5
            row.operator("style_engine.project_texture", text="Project Texture", icon='UV')

            # Conditional buttons (only when active mesh has iteration material)
            obj = context.active_object
            has_iteration_mat = (
                obj and obj.type == 'MESH' and obj.data.materials and
                any(m and m.name.startswith('iteration_') for m in obj.data.materials)
            )
            if has_iteration_mat:
                if style_props.patch_mode_active:
                    row = tex_box.row()
                    row.scale_y = 1.3
                    row.operator("style_engine.apply_patch", text="Apply Patch", icon='BRUSH_DATA')
                    row = tex_box.row()
                    row.operator("style_engine.toggle_patch_camera", text="Cancel Patch", icon='X')
                else:
                    row = tex_box.row()
                    row.scale_y = 1.2
                    row.operator("style_engine.toggle_patch_camera", text="Patch", icon='BRUSH_DATA')

                row = tex_box.row()
                row.scale_y = 1.2
                row.operator("style_engine.pbr_from_projected", text="PBR from Projected Texture", icon='MATSHADERBALL')

                already_multiview = (
                    obj.data and hasattr(obj.data, 'materials') and obj.data.materials and
                    any(m and (m.name.startswith('left_iteration_') or m.name.startswith('right_iteration_'))
                        for m in obj.data.materials)
                )
                if not already_multiview:
                    row = tex_box.row()
                    row.scale_y = 1.1
                    row.operator("style_engine.multiview_from_projected", text="Multiview from Projected", icon='VIEW_CAMERA')

            tex_box.separator()
            col = tex_box.column(align=True)
            col.scale_y = 1.2
            col.operator("style_engine.pbr_from_text", text="Generate PBR Layers", icon='MATSHADERBALL')
            col.operator("style_engine.trellis_retexture", text="Retexture Mesh", icon='SHADING_TEXTURE')


# ----------------------------------------------------------------
# 3.5 PROMPT REFINEMENT OPERATOR
# ----------------------------------------------------------------

def _prompt_llm_workflow_spec(props, role):
    """
    Map UI profile + logical role to workflow filename and node IDs to patch.

    role: 'refine' | 'image' | 'viewport'
    Returns dict with keys: file, text_node (or None), load_image_node (or None).
    """
    profile = getattr(props, "prompt_llm_profile", "DEFAULT") or "DEFAULT"
    if profile == "BLACKHAMSTER":
        if role == "refine":
            return {"file": "AgentTextRefine.json", "text_node": "9", "load_image_node": None}
        if role in ("image", "viewport"):
            return {"file": "AgentImageRefine.json", "text_node": None, "load_image_node": "11"}
    if role == "refine":
        return {"file": "TextRefine.json", "text_node": "7", "load_image_node": None}
    if role == "image":
        return {"file": "TextImage.json", "text_node": None, "load_image_node": "23"}
    if role == "viewport":
        return {"file": "TextViewport.json", "text_node": None, "load_image_node": "23"}
    return {"file": "TextRefine.json", "text_node": "7", "load_image_node": None}


def _extract_text_from_griptape_output(outputs):
    """
    Helper function to extract text from Griptape workflow outputs.
    Tries multiple node IDs and output formats.
    
    Returns:
        str: Extracted text or None if not found
    """
    refined_text = None
    
    # Try node 17 first (Griptape Run: Agent — TextRefine)
    if "17" in outputs:
        node_17_output = outputs["17"]
        if isinstance(node_17_output, dict) and "string" in node_17_output:
            refined_text = node_17_output["string"][0] if isinstance(node_17_output["string"], list) else node_17_output["string"]
        elif isinstance(node_17_output, list) and len(node_17_output) > 0:
            refined_text = node_17_output[0]
    
    # Node 2 — Griptape Run: Agent (AgentTextRefine)
    if not refined_text and "2" in outputs:
        node_2_output = outputs["2"]
        if isinstance(node_2_output, dict) and "string" in node_2_output:
            refined_text = node_2_output["string"][0] if isinstance(node_2_output["string"], list) else node_2_output["string"]
        elif isinstance(node_2_output, list) and len(node_2_output) > 0:
            refined_text = node_2_output[0]
    
    # Try node 19 if node 17 didn't work (Griptape Display: Text)
    if not refined_text and "19" in outputs:
        node_19_output = outputs["19"]
        if isinstance(node_19_output, dict):
            # Try common keys
            for key in ["string", "text", "STRING", "INPUT"]:
                if key in node_19_output:
                    val = node_19_output[key]
                    if isinstance(val, list) and len(val) > 0:
                        # Check if list of characters - join them
                        if all(isinstance(c, str) and len(c) <= 1 for c in val[:10]):
                            refined_text = ''.join(val)
                        else:
                            refined_text = val[0]
                    elif isinstance(val, str):
                        refined_text = val
                    if refined_text:
                        break
            # Try getting any string value
            if not refined_text:
                for key, value in node_19_output.items():
                    if isinstance(value, str) and len(value) > 10:
                        refined_text = value
                        break
                    elif isinstance(value, list) and len(value) > 0:
                        if all(isinstance(c, str) and len(c) <= 1 for c in value[:10]):
                            refined_text = ''.join(value)
                            break
                        elif isinstance(value[0], str):
                            refined_text = value[0]
                            break
        elif isinstance(node_19_output, list) and len(node_19_output) > 0:
            refined_text = node_19_output[0]
        elif isinstance(node_19_output, str):
            refined_text = node_19_output
    
    # Node 3 — Griptape Display: Text (AgentTextRefine / AgentImageRefine)
    if not refined_text and "3" in outputs:
        node_3_output = outputs["3"]
        if isinstance(node_3_output, dict):
            for key in ["string", "text", "STRING", "INPUT"]:
                if key in node_3_output:
                    val = node_3_output[key]
                    if isinstance(val, list) and len(val) > 0:
                        if all(isinstance(c, str) and len(c) <= 1 for c in val[:10]):
                            refined_text = ''.join(val)
                        else:
                            refined_text = val[0]
                    elif isinstance(val, str):
                        refined_text = val
                    if refined_text:
                        break
            if not refined_text:
                for key, value in node_3_output.items():
                    if isinstance(value, str) and len(value) > 10:
                        refined_text = value
                        break
                    elif isinstance(value, list) and len(value) > 0:
                        if all(isinstance(c, str) and len(c) <= 1 for c in value[:10]):
                            refined_text = ''.join(value)
                            break
                        elif isinstance(value[0], str):
                            refined_text = value[0]
                            break
        elif isinstance(node_3_output, list) and len(node_3_output) > 0:
            refined_text = node_3_output[0]
        elif isinstance(node_3_output, str):
            refined_text = node_3_output
    
    # Try node 20 (fallback — TextImage chain)
    if not refined_text and "20" in outputs:
        node_20_output = outputs["20"]
        if isinstance(node_20_output, dict) and "string" in node_20_output:
            refined_text = node_20_output["string"][0] if isinstance(node_20_output["string"], list) else node_20_output["string"]
        elif isinstance(node_20_output, str):
            refined_text = node_20_output
    
    # Node 10 — Griptape Run: Image Description (AgentImageRefine)
    if not refined_text and "10" in outputs:
        node_10_output = outputs["10"]
        if isinstance(node_10_output, dict) and "string" in node_10_output:
            refined_text = node_10_output["string"][0] if isinstance(node_10_output["string"], list) else node_10_output["string"]
        elif isinstance(node_10_output, str):
            refined_text = node_10_output
    
    return refined_text.strip() if refined_text else None


class WM_OT_RefinePrompt(bpy.types.Operator):
    """Use local LLM to refine the full prompt text in STYLEENGINE_Prompt"""
    bl_idname = "style_engine.refine_prompt"
    bl_label = "Refine Prompt (LLM)"
    bl_description = "Use local LLM to enhance the prompt text"

    def execute(self, context):
        import json
        from pathlib import Path
        from . import runcomfy_deployment

        # 1. Get text editor content
        text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
        if not text_block:
            self.report({'ERROR'}, "STYLEENGINE_Prompt text block not found")
            return {'CANCELLED'}

        original_prompt = text_block.as_string().strip()
        if not original_prompt:
            self.report({'ERROR'}, "Prompt is empty")
            print("[Refine Prompt] Prompt text block is empty")
            return {'CANCELLED'}

        print(f"[Refine Prompt] Original prompt: {original_prompt}")
        
        # Save "before" snapshot
        from . import workspace_setup
        workspace_setup.save_prompt_snapshot(context, prefix="before_refine")
        
        # 3. Check if in Server mode (GCS)
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Prompt refinement only works in Server mode (GCS)")
            print("[Refine Prompt] ❌ Not in Server mode - feature requires direct ComfyUI connection")
            return {'CANCELLED'}
        
        try:
            props = context.scene.style_engine_props
            spec = _prompt_llm_workflow_spec(props, "refine")
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Text" / spec["file"]
            
            if not workflow_file.exists():
                self.report({'ERROR'}, f"{spec['file']} not found")
                print(f"[Refine Prompt] ❌ Workflow not found: {workflow_file}")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            print(f"[Refine Prompt] ✓ Loaded workflow: {workflow_file.name} (profile={props.prompt_llm_profile})")
            
            text_node = spec["text_node"]
            if text_node not in workflow:
                self.report({'ERROR'}, f"Invalid workflow structure (node {text_node} missing)")
                print(f"[Refine Prompt] ❌ Node {text_node} not found in workflow")
                return {'CANCELLED'}
            
            workflow[text_node]["inputs"]["text"] = original_prompt
            print(f"[Refine Prompt] ✓ Patched node {text_node} with prompt text")
            
            # 6. Submit to ComfyUI server
            server_client = runcomfy_deployment.get_server_client()
            
            print(f"[Refine Prompt] Submitting to ComfyUI server...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Refine Prompt] ✓ Queued prompt refinement (ID: {prompt_id[:8]}...)")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow)
            
            # 7. Start NON-BLOCKING polling with callback
            from . import runcomfy_polling
            
            def on_refine_complete(success, result=None, error=None, workflow_type=None):
                """Callback when refinement completes"""
                print(f"[Refine Prompt] Callback triggered: success={success}")
                
                if not success:
                    print(f"[Refine Prompt] ❌ Failed: {error}")
                    return
                
                try:
                    # Extract outputs
                    outputs = result.get('outputs', {})
                    
                    # Extract refined text using helper
                    refined_text = _extract_text_from_griptape_output(outputs)
                    
                    if not refined_text:
                        print(f"[Refine Prompt] ❌ No text output found")
                        print(f"[Refine Prompt] Available outputs: {list(outputs.keys())}")
                        return
                    
                    print(f"[Refine Prompt] ✓ Refined prompt: {refined_text[:100]}...")

                    # Replace the entire prompt text block with the refined version
                    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
                    if not text_block:
                        print("[Refine Prompt] ❌ Text block not found")
                        return

                    text_block.clear()
                    text_block.write(refined_text)
                    
                    # Save "after" snapshot
                    workspace_setup.save_prompt_snapshot(bpy.context, prefix="after_refine")
                    
                    print(f"[Refine Prompt] ✓ Updated text editor with refined prompt")
                    
                except Exception as e:
                    print(f"[Refine Prompt] ❌ Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_refine_complete,
                workflow_type='text'
            )
            
            self.report({'INFO'}, "Refining prompt... (watch progress bar)")
            print(f"[Refine Prompt] ⏳ Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to refine prompt: {str(e)}")
            print(f"[Refine Prompt] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_GenerateImageDescription(bpy.types.Operator):
    """Generate description from current AI image using machine vision"""
    bl_idname = "style_engine.generate_image_description"
    bl_label = "Generate Image Description"
    bl_description = "Use AI machine vision to generate a text description from current_ai.png"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import re
        import json
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        
        # 1. Check if in Server mode (GCS)
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Image description only works in Server mode (GCS)")
            print("[Image Description] ❌ Not in Server mode - feature requires direct ComfyUI connection")
            return {'CANCELLED'}
        
        # 2. Locate current_ai.png (checks project temp then all fallback locations)
        image_path = workspace_setup.find_current_ai(context)
        print(f"[Image Description] Looking for current_ai.png → {image_path}")
        if image_path is None:
            canonical = workspace_setup.get_temp_directory(context) / "current_ai.png"
            self.report(
                {'ERROR'},
                f"current_ai.png not found anywhere — generate an image first "
                f"(expected: {canonical})"
            )
            print(
                f"[Image Description] ❌ Not found in canonical or fallback locations. "
                f"Canonical: {canonical}  |  .blend: {bpy.data.filepath!r}"
            )
            return {'CANCELLED'}

        print(f"[Image Description] Using image: {image_path}")
        
        # Save "before" snapshot
        workspace_setup.save_prompt_snapshot(context, prefix="before_vision")
        
        try:
            props = context.scene.style_engine_props
            spec = _prompt_llm_workflow_spec(props, "image")
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Text" / spec["file"]
            
            if not workflow_file.exists():
                self.report({'ERROR'}, f"{spec['file']} not found")
                print(f"[Image Description] ❌ Workflow not found: {workflow_file}")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            print(f"[Image Description] ✓ Loaded workflow: {workflow_file.name} (profile={props.prompt_llm_profile})")
            
            # 4. Upload image to ComfyUI server
            server_client = runcomfy_deployment.get_server_client()
            
            print(f"[Image Description] Uploading image to ComfyUI server...")
            upload_response = server_client.upload_image(str(image_path), overwrite=True)
            uploaded_filename = upload_response.get("name", "")
            
            if not uploaded_filename:
                self.report({'ERROR'}, "Failed to upload image to server")
                print(f"[Image Description] ❌ Upload failed: {upload_response}")
                return {'CANCELLED'}
            
            print(f"[Image Description] ✓ Uploaded image: {uploaded_filename}")
            
            load_nid = spec["load_image_node"]
            if load_nid not in workflow:
                self.report({'ERROR'}, f"Invalid workflow structure (node {load_nid} missing)")
                print(f"[Image Description] ❌ Node {load_nid} not found in workflow")
                return {'CANCELLED'}
            
            workflow[load_nid]["inputs"]["image"] = uploaded_filename
            print(f"[Image Description] ✓ Patched node {load_nid} with image: {uploaded_filename}")
            
            # 6. Submit to ComfyUI server
            print(f"[Image Description] Submitting to ComfyUI server...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Image Description] ✓ Queued image description (ID: {prompt_id[:8]}...)")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow)
            
            # 7. Start NON-BLOCKING polling with callback
            from . import runcomfy_polling
            
            def on_description_complete(success, result=None, error=None, workflow_type=None):
                """Callback when description completes"""
                print(f"[Image Description] Callback triggered: success={success}")
                
                if not success:
                    print(f"[Image Description] ❌ Failed: {error}")
                    return
                
                try:
                    # Extract outputs
                    outputs = result.get('outputs', {})
                    
                    # Extract description using helper
                    description_text = _extract_text_from_griptape_output(outputs)
                    
                    if not description_text:
                        print(f"[Image Description] ❌ No text output found")
                        return
                    
                    print(f"[Image Description] ✓ Generated: {description_text[:100]}...")
                    
                    # Update <v> tag in text editor
                    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
                    if not text_block:
                        print("[Image Description] ❌ Text block not found")
                        return
                    
                    current_content = text_block.as_string()
                    
                    # Check if <v> tag exists
                    if re.search(r'<v>.*?</v>', current_content, re.DOTALL | re.IGNORECASE):
                        # Replace existing <v> content
                        new_content = re.sub(
                            r'(<v>)(.*?)(</v>)',
                            r'\1' + description_text + r'\3',
                            current_content,
                            flags=re.DOTALL | re.IGNORECASE
                        )
                    else:
                        # Add <v> section at the end
                        new_content = current_content.rstrip() + "\n# Machine Vision\n<v>" + description_text + "</v>\n"
                    
                    # Update text block
                    text_block.clear()
                    text_block.write(new_content)
                    
                    # Save "after" snapshot
                    workspace_setup.save_prompt_snapshot(bpy.context, prefix="after_vision")
                    
                    print(f"[Image Description] ✓ Updated text editor with description")
                    
                except Exception as e:
                    print(f"[Image Description] ❌ Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_description_complete,
                workflow_type='text'
            )
            
            self.report({'INFO'}, "Generating image description... (watch progress bar)")
            print(f"[Image Description] ⏳ Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Image description failed: {str(e)}")
            print(f"[Image Description] ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_GenerateImageDescriptionFromFile(bpy.types.Operator):
    """Generate description from any image file using machine vision"""
    bl_idname = "style_engine.generate_image_description_from_file"
    bl_label = "Describe Image from File"
    bl_description = "Open file browser to select an image, then generate AI description and add to <v> tag"
    bl_options = {'REGISTER'}
    
    # File browser properties
    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.jpg;*.jpeg;*.png",
        options={'HIDDEN'}
    )
    
    def invoke(self, context, event):
        # Open file browser
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        import re
        import json
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        
        # Validate filepath
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
        
        image_path = Path(self.filepath)
        if not image_path.exists():
            self.report({'ERROR'}, f"File not found: {image_path}")
            return {'CANCELLED'}
        
        # Check file extension
        valid_extensions = {'.jpg', '.jpeg', '.png'}
        if image_path.suffix.lower() not in valid_extensions:
            self.report({'ERROR'}, f"Invalid file type. Use: {', '.join(valid_extensions)}")
            return {'CANCELLED'}
        
        # 1. Check if in Server mode (GCS)
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Image description only works in Server mode (GCS)")
            print("[Image Description] ❌ Not in Server mode - feature requires direct ComfyUI connection")
            return {'CANCELLED'}
        
        print(f"[Image Description from File] Using image: {image_path}")
        
        # Save "before" snapshot
        workspace_setup.save_prompt_snapshot(context, prefix="before_vision_file")
        
        try:
            props = context.scene.style_engine_props
            spec = _prompt_llm_workflow_spec(props, "image")
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Text" / spec["file"]
            
            if not workflow_file.exists():
                self.report({'ERROR'}, f"{spec['file']} not found")
                print(f"[Image Description from File] ❌ Workflow not found: {workflow_file}")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            print(f"[Image Description from File] ✓ Loaded workflow: {workflow_file.name} (profile={props.prompt_llm_profile})")
            
            # 3. Upload image to ComfyUI server
            server_client = runcomfy_deployment.get_server_client()
            
            print(f"[Image Description from File] Uploading image to ComfyUI server...")
            upload_response = server_client.upload_image(str(image_path), overwrite=True)
            uploaded_filename = upload_response.get("name", "")
            
            if not uploaded_filename:
                self.report({'ERROR'}, "Failed to upload image to server")
                print(f"[Image Description from File] ❌ Upload failed: {upload_response}")
                return {'CANCELLED'}
            
            print(f"[Image Description from File] ✓ Uploaded image: {uploaded_filename}")
            
            load_nid = spec["load_image_node"]
            if load_nid not in workflow:
                self.report({'ERROR'}, f"Invalid workflow structure (node {load_nid} missing)")
                print(f"[Image Description from File] ❌ Node {load_nid} not found in workflow")
                return {'CANCELLED'}
            
            workflow[load_nid]["inputs"]["image"] = uploaded_filename
            print(f"[Image Description from File] ✓ Patched node {load_nid} with image: {uploaded_filename}")
            
            # 5. Submit to ComfyUI server
            print(f"[Image Description from File] Submitting to ComfyUI server...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Image Description from File] ✓ Queued image description (ID: {prompt_id[:8]}...)")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow)
            
            # 6. Start NON-BLOCKING polling with callback
            from . import runcomfy_polling
            
            # Capture image_path.name for callback
            image_name = image_path.name
            
            def on_description_complete(success, result=None, error=None, workflow_type=None):
                """Callback when description completes"""
                print(f"[Image Description from File] Callback triggered: success={success}")
                
                if not success:
                    print(f"[Image Description from File] ❌ Failed: {error}")
                    return
                
                try:
                    # Extract outputs
                    outputs = result.get('outputs', {})
                    
                    # Extract description using helper
                    description_text = _extract_text_from_griptape_output(outputs)
                    
                    if not description_text:
                        print(f"[Image Description from File] ❌ No text output found")
                        return
                    
                    print(f"[Image Description from File] ✓ Generated: {description_text[:100]}...")
                    
                    # APPEND to <v> tag in text editor (not replace!)
                    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
                    if not text_block:
                        print("[Image Description from File] ❌ Text block not found")
                        return
                    
                    current_content = text_block.as_string()
                    
                    # Check if <v> tag exists
                    v_match = re.search(r'<v>(.*?)</v>', current_content, re.DOTALL | re.IGNORECASE)
                    if v_match:
                        existing_v = v_match.group(1).strip()
                        if existing_v:
                            # Append to existing content with separator
                            new_v_content = existing_v + ". " + description_text
                        else:
                            new_v_content = description_text
                        new_content = re.sub(
                            r'(<v>)(.*?)(</v>)',
                            r'\1' + new_v_content + r'\3',
                            current_content,
                            flags=re.DOTALL | re.IGNORECASE
                        )
                    else:
                        # Add <v> section at the end
                        new_content = current_content.rstrip() + "\n# Machine Vision\n<v>" + description_text + "</v>\n"
                    
                    # Update text block
                    text_block.clear()
                    text_block.write(new_content)
                    
                    # Save "after" snapshot
                    workspace_setup.save_prompt_snapshot(bpy.context, prefix="after_vision_file")
                    
                    print(f"[Image Description from File] ✓ Appended to <v> tag in text editor")
                    print(f"[Image Description from File] ✅ Description added from: {image_name}")
                    
                except Exception as e:
                    print(f"[Image Description from File] ❌ Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_description_complete,
                workflow_type='text'
            )
            
            self.report({'INFO'}, f"Generating description from: {image_path.name} (watch progress bar)")
            print(f"[Image Description from File] ⏳ Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Image description failed: {str(e)}")
            print(f"[Image Description from File] ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_GenerateImageDescriptionFromViewport(bpy.types.Operator):
    """Generate description from viewport camera view using machine vision"""
    bl_idname = "style_engine.generate_image_description_from_viewport"
    bl_label = "Describe Viewport"
    bl_description = "Render viewport from active camera, then generate AI description and add to <v> tag"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        import re
        import json
        from pathlib import Path
        from . import runcomfy_deployment
        from . import workspace_setup
        
        # 1. Check if in Server mode (GCS)
        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Image description only works in Server mode (GCS)")
            print("[Viewport Description] ❌ Not in Server mode - feature requires direct ComfyUI connection")
            return {'CANCELLED'}
        
        # 2. Get ai_camera
        prefs = context.preferences.addons['styleengine'].preferences
        camera_name = prefs.camera_name_override
        
        if camera_name not in bpy.data.objects:
            self.report({'ERROR'}, f"{camera_name} not found - run 'Setup Workspace' first")
            print(f"[Viewport Description] ❌ Camera not found: {camera_name}")
            return {'CANCELLED'}
        
        ai_camera = bpy.data.objects[camera_name]
        scene = context.scene
        props = scene.style_engine_props
        
        print(f"[Viewport Description] Rendering viewport from {camera_name}...")
        
        # Save "before" snapshot
        workspace_setup.save_prompt_snapshot(context, prefix="before_vision_viewport")
        
        try:
            # 3. Render viewport screenshot with fast/detailed setting
            temp_dir = workspace_setup.get_temp_directory(context)
            viewport_image_path = temp_dir / "viewport_description.jpg"
            
            # Store original settings
            original_engine = scene.render.engine
            original_format = scene.render.image_settings.file_format
            original_use_compositing = scene.render.use_compositing
            original_resolution_x = scene.render.resolution_x
            original_resolution_y = scene.render.resolution_y
            
            try:
                # Get render quality preference
                render_quality = props.render_quality if hasattr(props, 'render_quality') else 'FAST'
                
                # Configure render engine
                if render_quality == 'DETAILED':
                    scene.render.engine = workspace_setup.get_eevee_engine_name()
                    print(f"[Viewport Description] Using EEVEE (detailed quality)")
                else:
                    scene.render.engine = 'BLENDER_WORKBENCH'
                    print(f"[Viewport Description] Using Workbench (fast preview)")
                
                # Set to 512px max dimension (maintain aspect ratio)
                current_width = scene.render.resolution_x
                current_height = scene.render.resolution_y
                
                if current_width >= current_height:
                    # Landscape or square
                    scale_factor = 512.0 / current_width
                else:
                    # Portrait
                    scale_factor = 512.0 / current_height
                
                scene.render.resolution_x = int(current_width * scale_factor)
                scene.render.resolution_y = int(current_height * scale_factor)
                
                print(f"[Viewport Description] Scaled resolution: {scene.render.resolution_x}x{scene.render.resolution_y} (max 512px)")
                
                # Configure output
                scene.render.image_settings.file_format = 'JPEG'
                scene.render.image_settings.color_mode = 'RGB'
                scene.render.image_settings.quality = 85
                scene.render.use_compositing = False
                scene.render.filepath = str(viewport_image_path.with_suffix(''))
                
                # Render from ai_camera
                print(f"[Viewport Description] Rendering viewport screenshot...")
                workspace_setup.render_from_camera_safe(scene, ai_camera, prefs)
                
                # Verify output
                if not viewport_image_path.exists():
                    self.report({'ERROR'}, "Failed to render viewport screenshot")
                    print(f"[Viewport Description] ❌ Render output not found: {viewport_image_path}")
                    return {'CANCELLED'}
                
                print(f"[Viewport Description] ✓ Rendered: {viewport_image_path.name}")
                
            finally:
                # Restore original settings
                scene.render.engine = original_engine
                scene.render.image_settings.file_format = original_format
                scene.render.use_compositing = original_use_compositing
                scene.render.resolution_x = original_resolution_x
                scene.render.resolution_y = original_resolution_y
            
            # 4. Load TextViewport or AgentImageRefine (profile-dependent)
            props = context.scene.style_engine_props
            spec = _prompt_llm_workflow_spec(props, "viewport")
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Text" / spec["file"]
            
            if not workflow_file.exists():
                self.report({'ERROR'}, f"{spec['file']} not found")
                print(f"[Viewport Description] ❌ Workflow not found: {workflow_file}")
                return {'CANCELLED'}
            
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)
            
            print(f"[Viewport Description] ✓ Loaded workflow: {workflow_file.name} (profile={props.prompt_llm_profile})")
            
            # 5. Upload image to ComfyUI server
            server_client = runcomfy_deployment.get_server_client()
            
            print(f"[Viewport Description] Uploading viewport screenshot to ComfyUI server...")
            upload_response = server_client.upload_image(str(viewport_image_path), overwrite=True)
            uploaded_filename = upload_response.get("name", "")
            
            if not uploaded_filename:
                self.report({'ERROR'}, "Failed to upload image to server")
                print(f"[Viewport Description] ❌ Upload failed: {upload_response}")
                return {'CANCELLED'}
            
            print(f"[Viewport Description] ✓ Uploaded: {uploaded_filename}")
            
            load_nid = spec["load_image_node"]
            if load_nid not in workflow:
                self.report({'ERROR'}, f"Invalid workflow structure (node {load_nid} missing)")
                print(f"[Viewport Description] ❌ Node {load_nid} not found in workflow")
                return {'CANCELLED'}
            
            workflow[load_nid]["inputs"]["image"] = uploaded_filename
            print(f"[Viewport Description] ✓ Patched node {load_nid} with image")
            
            # 7. Submit to ComfyUI server
            print(f"[Viewport Description] Submitting to ComfyUI server...")
            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"[Viewport Description] ✓ Queued (ID: {prompt_id[:8]}...)")
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow)
            
            # 8. Start NON-BLOCKING polling with callback
            from . import runcomfy_polling
            
            def on_description_complete(success, result=None, error=None, workflow_type=None):
                """Callback when description completes"""
                print(f"[Viewport Description] Callback triggered: success={success}")
                
                if not success:
                    print(f"[Viewport Description] ❌ Failed: {error}")
                    return
                
                try:
                    # Extract outputs
                    outputs = result.get('outputs', {})
                    
                    # Extract description using helper
                    description_text = _extract_text_from_griptape_output(outputs)
                    
                    if not description_text:
                        print(f"[Viewport Description] ❌ No text output found")
                        return
                    
                    print(f"[Viewport Description] ✓ Generated: {description_text[:100]}...")
                    
                    # APPEND to <v> tag in text editor (not replace!)
                    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
                    if not text_block:
                        print("[Viewport Description] ❌ Text block not found")
                        return
                    
                    current_content = text_block.as_string()
                    
                    # Check if <v> tag exists
                    v_match = re.search(r'<v>(.*?)</v>', current_content, re.DOTALL | re.IGNORECASE)
                    if v_match:
                        existing_v = v_match.group(1).strip()
                        if existing_v:
                            # Append to existing content with separator
                            new_v_content = existing_v + ". " + description_text
                        else:
                            new_v_content = description_text
                        new_content = re.sub(
                            r'(<v>)(.*?)(</v>)',
                            r'\1' + new_v_content + r'\3',
                            current_content,
                            flags=re.DOTALL | re.IGNORECASE
                        )
                    else:
                        # Add <v> section at the end
                        new_content = current_content.rstrip() + "\n# Machine Vision\n<v>" + description_text + "</v>\n"
                    
                    # Update text block
                    text_block.clear()
                    text_block.write(new_content)
                    
                    # Save "after" snapshot
                    workspace_setup.save_prompt_snapshot(bpy.context, prefix="after_vision_viewport")
                    
                    print(f"[Viewport Description] ✓ Appended to <v> tag in text editor")
                    print(f"[Viewport Description] ✅ Viewport description added!")
                    
                except Exception as e:
                    print(f"[Viewport Description] ❌ Callback error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register for non-blocking polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_description_complete,
                workflow_type='text'
            )
            
            self.report({'INFO'}, "Generating viewport description... (watch progress bar)")
            print(f"[Viewport Description] ⏳ Processing in background...")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Viewport description failed: {str(e)}")
            print(f"[Viewport Description] ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_GenerateMeshMultiview(bpy.types.Operator):
    """Generate 3D mesh from multiple view images (Coming Soon)"""
    bl_idname = "style_engine.generate_mesh_multiview"
    bl_label = "Generate Mesh (Multiview)"
    bl_description = "Generate 3D mesh from multiple camera angles (Coming Soon)"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        self.report({'INFO'}, "Generate Mesh (Multiview) - Coming Soon")
        return {'FINISHED'}


class WM_OT_GenerateTexturedMeshMultiview(bpy.types.Operator):
    """Generate textured 3D mesh from multiple view images (Coming Soon)"""
    bl_idname = "style_engine.generate_textured_mesh_multiview"
    bl_label = "Generate Textured Mesh (Multiview)"
    bl_description = "Generate textured 3D mesh from multiple camera angles (Coming Soon)"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        self.report({'INFO'}, "Generate Textured Mesh (Multiview) - Coming Soon")
        return {'FINISHED'}


# ----------------------------------------------------------------
# Refine Image JSON Editor — Operators
# ----------------------------------------------------------------

class WM_OT_RefineImageAddSubject(bpy.types.Operator):
    """Add a new subject to the Refine Image subject list"""
    bl_idname = "style_engine.refine_image_add_subject"
    bl_label = "Add Subject"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.style_engine_props
        subj = props.refine_subjects.add()
        subj.label = f"object_{len(props.refine_subjects)}"
        subj.show_expanded = True
        return {'FINISHED'}


class WM_OT_RefineImageRemoveSubject(bpy.types.Operator):
    """Remove a subject from the Refine Image subject list"""
    bl_idname = "style_engine.refine_image_remove_subject"
    bl_label = "Remove Subject"
    bl_options = {'REGISTER', 'UNDO'}

    subject_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        props = context.scene.style_engine_props
        if 0 <= self.subject_index < len(props.refine_subjects):
            props.refine_subjects.remove(self.subject_index)
        return {'FINISHED'}


class WM_OT_RefineImageAddFeature(bpy.types.Operator):
    """Add a feature to a subject"""
    bl_idname = "style_engine.refine_image_add_feature"
    bl_label = "Add Feature"
    bl_options = {'REGISTER', 'UNDO'}

    subject_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        props = context.scene.style_engine_props
        if 0 <= self.subject_index < len(props.refine_subjects):
            props.refine_subjects[self.subject_index].features.add()
        return {'FINISHED'}


class WM_OT_RefineImageRemoveFeature(bpy.types.Operator):
    """Remove a feature from a subject"""
    bl_idname = "style_engine.refine_image_remove_feature"
    bl_label = "Remove Feature"
    bl_options = {'REGISTER', 'UNDO'}

    subject_index: bpy.props.IntProperty(default=0)
    feature_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        props = context.scene.style_engine_props
        si, fi = self.subject_index, self.feature_index
        if 0 <= si < len(props.refine_subjects):
            subj = props.refine_subjects[si]
            if 0 <= fi < len(subj.features):
                subj.features.remove(fi)
        return {'FINISHED'}


class WM_OT_RefineImageAddTag(bpy.types.Operator):
    """Add a thematic tag"""
    bl_idname = "style_engine.refine_image_add_tag"
    bl_label = "Add Tag"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.style_engine_props.refine_tags.add()
        return {'FINISHED'}


class WM_OT_RefineImageRemoveTag(bpy.types.Operator):
    """Remove a thematic tag"""
    bl_idname = "style_engine.refine_image_remove_tag"
    bl_label = "Remove Tag"
    bl_options = {'REGISTER', 'UNDO'}

    tag_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        props = context.scene.style_engine_props
        if 0 <= self.tag_index < len(props.refine_tags):
            props.refine_tags.remove(self.tag_index)
        return {'FINISHED'}


def _get_blender_scene_metadata(context, image_filename: str) -> dict:
    """
    Collect ground-truth metadata from Blender and return it as a plain dict.

    Uses scene.camera — the scene-level active camera set in Scene Properties
    (or via Ctrl+Numpad0). This is NOT the currently selected object; it is
    whatever camera Blender would use if you hit F12.

    Mandatory keys (always present):
        filename, dimensions, aspect_ratio

    Conditional keys (only when scene.camera is set):
        focal_length_mm
        depth_of_field  → sub-dict: enabled, aperture_fstop,
                          focus_distance_m (null when focus_object is set),
                          focus_object (null when using distance)
    """
    import json as _json
    from math import gcd

    scene  = context.scene
    render = scene.render
    w, h   = render.resolution_x, render.resolution_y

    g  = gcd(w, h)
    ar = f"{w // g}:{h // g}"

    # Use the .blend filename (without extension) as a meaningful project identifier.
    # The image on disk is always "current_ai.png", which carries no useful context.
    blend_name = Path(bpy.data.filepath).stem if bpy.data.is_saved else "unsaved"

    meta = {
        "filename":     blend_name,
        "dimensions":   f"{w}x{h}",
        "aspect_ratio": ar,
    }

    # scene.camera is the scene-level active camera — never the selected object
    cam_obj = scene.camera
    if cam_obj and cam_obj.type == 'CAMERA':
        cam = cam_obj.data
        meta["focal_length_mm"] = round(cam.lens, 1)

        dof = cam.dof
        if dof.use_dof:
            meta["depth_of_field"] = {
                "enabled":          True,
                "aperture_fstop":   round(dof.aperture_fstop, 2),
                "focus_distance_m": round(dof.focus_distance, 3) if dof.focus_object is None else None,
                "focus_object":     dof.focus_object.name if dof.focus_object else None,
            }
        else:
            meta["depth_of_field"] = {"enabled": False}

    return meta


def _build_agent_json_task_prompt(meta: dict) -> str:
    """
    Build the task STRING that is injected into node "10" (Griptape Run: Image Description)
    before the workflow is queued.

    The agent receives a *partially pre-filled* JSON skeleton whose metadata section
    is already populated with exact values from Blender.  The agent's only job is
    to observe the image and fill in the remaining visual fields — it must never
    change or re-derive the metadata keys.
    """
    import json as _json

    # Build the metadata sub-object exactly as it must appear in the output
    metadata_obj = {
        "filename":     meta["filename"],
        "dimensions":   meta["dimensions"],
        "aspect_ratio": meta["aspect_ratio"],
    }
    if "focal_length_mm" in meta:
        metadata_obj["focal_length_mm"] = meta["focal_length_mm"]
    if "depth_of_field" in meta:
        metadata_obj["depth_of_field"] = meta["depth_of_field"]

    metadata_json = _json.dumps(metadata_obj, indent=4)

    # Indent each line of the sub-object so it sits correctly inside the skeleton
    indented = "\n".join("    " + line for line in metadata_json.splitlines())

    task = (
        "Analyze the provided image and return a single valid JSON object.\n\n"
        "The metadata section below is ALREADY FILLED IN with exact values from "
        "Blender — copy it into your output unchanged. Do not infer, round, or "
        "replace any of these values. Focal length and depth_of_field are present "
        "only when a camera was active; if they appear here, include them verbatim.\n\n"
        "Pre-filled metadata (copy verbatim):\n"
        "```json\n"
        "{\n"
        f"  \"metadata\": {indented.strip()},\n"
        "  \"visual_style\":   { ... fill from image ... },\n"
        "  \"composition\":    { ... fill from image ... },\n"
        "  \"subject_matter\": [ ... fill from image ... ],\n"
        "  \"thematic_tags\":  [ ... fill from image ... ]\n"
        "}\n"
        "```\n\n"
        "Return only the completed JSON wrapped in ```json ... ``` fences."
    )
    return task


class WM_OT_RefineImageAnalyzeJSON(bpy.types.Operator):
    """Run AgentJSON on the current AI image and populate the Refine Image fields"""
    bl_idname = "style_engine.refine_image_analyze_json"
    bl_label = "Analyze Image → JSON"
    bl_description = "Use the AgentJSON workflow to dissect current_ai.png into structured fields"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import json, re
        from pathlib import Path
        from . import runcomfy_deployment, workspace_setup

        if not runcomfy_deployment.is_server_mode():
            self.report({'ERROR'}, "Analyze requires Server mode (GCS)")
            return {'CANCELLED'}

        image_path = workspace_setup.find_current_ai(context)
        print(f"[RefineJSON] Looking for current_ai.png → {image_path}")
        if image_path is None:
            canonical = workspace_setup.get_temp_directory(context) / "current_ai.png"
            self.report(
                {'ERROR'},
                f"current_ai.png not found anywhere — generate an image first "
                f"(expected: {canonical})"
            )
            print(
                f"[RefineJSON] ❌ Not found in canonical or fallback locations. "
                f"Canonical: {canonical}  |  .blend: {bpy.data.filepath!r}"
            )
            return {'CANCELLED'}

        try:
            addon_dir = Path(__file__).parent
            workflow_file = addon_dir / "workflows" / "Text" / "AgentJSON.json"
            if not workflow_file.exists():
                self.report({'ERROR'}, "AgentJSON.json workflow not found")
                return {'CANCELLED'}

            with open(workflow_file, 'r') as f:
                workflow = json.load(f)

            server_client = runcomfy_deployment.get_server_client()
            upload_response = server_client.upload_image(str(image_path), overwrite=True)
            uploaded_filename = upload_response.get("name", "")
            if not uploaded_filename:
                self.report({'ERROR'}, "Failed to upload image to server")
                return {'CANCELLED'}

            workflow["11"]["inputs"]["image"] = uploaded_filename
            print(f"[RefineJSON] Patched node 11 → {uploaded_filename}")

            # ── Pre-load the agent task (node 10) with real Blender metadata ──
            # scene.camera = scene-level active camera, NOT the selected object.
            meta       = _get_blender_scene_metadata(context, uploaded_filename)
            task_prompt = _build_agent_json_task_prompt(meta)
            task_node   = "10"
            if task_node in workflow:
                workflow[task_node]["inputs"]["STRING"] = task_prompt
                print(f"[RefineJSON] Pre-loaded task prompt with metadata: {meta}")
            else:
                print("[RefineJSON] ⚠ Node '10' not found — metadata not pre-loaded")

            response = server_client.queue_prompt(workflow)
            prompt_id = response['prompt_id']

            from . import runcomfy_polling, progress_bar
            progress_bar.set_current_workflow(workflow)

            def on_json_complete(success, result=None, error=None, workflow_type=None):
                if not success:
                    print(f"[RefineJSON] ❌ Failed: {error}")
                    return
                try:
                    outputs = result.get('outputs', {})
                    json_text = _extract_text_from_griptape_output(outputs)
                    if not json_text:
                        print(f"[RefineJSON] ❌ No text output. Keys: {list(outputs.keys())}")
                        return
                    # Strip markdown code fences
                    json_text = re.sub(r'^```(?:json)?\s*', '', json_text.strip())
                    json_text = re.sub(r'\s*```$', '', json_text.strip())
                    props = bpy.context.scene.style_engine_props
                    _populate_refine_from_json(props, json_text)
                    print("[RefineJSON] ✓ Refine Image fields populated from JSON output")
                except Exception as e:
                    print(f"[RefineJSON] ❌ Callback error: {e}")
                    import traceback; traceback.print_exc()

            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',
                request_id=prompt_id,
                callback=on_json_complete,
                workflow_type='text'
            )

            self.report({'INFO'}, "Analyzing image… fields will populate when done")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed: {str(e)}")
            import traceback; traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_RefineImagePasteJSON(bpy.types.Operator):
    """Parse JSON from the clipboard and fill in all Refine Image fields"""
    bl_idname = "style_engine.refine_image_paste_json"
    bl_label = "Paste JSON"
    bl_description = "Read JSON from the system clipboard and populate all Refine Image fields"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import re
        try:
            text = context.window_manager.clipboard.strip()
        except Exception:
            self.report({'ERROR'}, "Could not read clipboard")
            return {'CANCELLED'}

        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text.strip())

        try:
            _populate_refine_from_json(context.scene.style_engine_props, text)
            self.report({'INFO'}, "Refine Image fields populated from clipboard JSON")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"JSON parse error: {e}")
            return {'CANCELLED'}


class WM_OT_RefineImageSubmit(bpy.types.Operator):
    """Refine the current AI image using the structured JSON form as the prompt"""
    bl_idname = "style_engine.refine_image_submit"
    bl_label = "Refine Image"
    bl_description = (
        "Runs the same Refine Image workflow as the main button. "
        "If 'Use structured editing' is checked the JSON form is written to STYLEENGINE_Prompt "
        "before refining so the agent receives the structured modification instruction."
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        from pathlib import Path
        try:
            from . import workspace_setup
            td = workspace_setup.get_temp_directory(context)
            return (td / "current_ai.png").exists()
        except Exception:
            return False

    def execute(self, context):
        props = context.scene.style_engine_props
        from . import workspace_setup

        if props.use_structured_editing:
            json_body = _build_refine_json(props)
            instruction = "Edit this image based on the following JSON modifications:\n" + json_body

            # Write instruction into STYLEENGINE_Prompt so generate_ai_image_cloud picks it up
            text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
            if not text_block:
                text_block = bpy.data.texts.new("STYLEENGINE_Prompt")

            workspace_setup.save_prompt_snapshot(context, prefix="before_structured_refine")
            text_block.clear()
            text_block.write(instruction)
            print(f"[RefineImage] Wrote structured instruction to STYLEENGINE_Prompt "
                  f"({len(instruction)} chars)")

        try:
            workspace_setup.generate_ai_image_cloud(context, refine_mode=True)
            self.report({'INFO'}, "Refine Image started with structured JSON instruction")
        except Exception as e:
            self.report({'ERROR'}, f"Refine failed: {e}")
            import traceback; traceback.print_exc()
            return {'CANCELLED'}

        return {'FINISHED'}


# ----------------------------------------------------------------
# 4. REGISTRATION
# ----------------------------------------------------------------
classes = (
    ObjectGroup,
    RefineFeatureItem,
    RefineSubjectItem,
    RefineTagItem,
    StyleEngineProperties,
    WM_OT_RerollSeed,
    WM_OT_AlignAICameraToView,
    WM_OT_BringBackgroundForward,
    WM_OT_SendBackgroundBack,
    # Prompt editor operators removed - now automatic
    WM_OT_AddGroup,
    WM_OT_AssignGroup,
    WM_OT_RenameGroup,
    WM_OT_SelectGroup,
    WM_OT_DeleteGroup,
    WM_OT_ProjectTexture,
    WM_OT_NanoGenerate,
    WM_OT_Nano3DGenerate,
    WM_OT_TrellisGenerate,
    WM_OT_TrellisRetexture,
    WM_OT_SegmentMesh,
    WM_OT_OmniGenerate,
    WM_OT_OmniBBoxDebug,
    WM_OT_TogglePatchCamera,
    WM_OT_ApplyPatch,
    WM_OT_MultiviewFromProjected,
    WM_OT_PBRFromProjectedTexture,
    WM_OT_PBRFromText,
    WM_OT_UploadCurrentAI,
    WM_OT_PrevGeneration,
    WM_OT_NextGeneration,
    WM_OT_LoadReferenceImage,
    WM_OT_ClearReferenceImage,
    WM_OT_ReloadReferenceImage,
    WM_OT_CancelGeneration,
    WM_OT_RefreshLoraList,
    WM_OT_LoadLoraKeywords,
    WM_OT_TestCloudGeneration,
    WM_OT_RefinePrompt,
    WM_OT_GenerateImageDescription,
    WM_OT_GenerateImageDescriptionFromFile,
    WM_OT_GenerateImageDescriptionFromViewport,
    WM_OT_GenerateMeshMultiview,
    WM_OT_GenerateTexturedMeshMultiview,
    WM_OT_RefineImageAddSubject,
    WM_OT_RefineImageRemoveSubject,
    WM_OT_RefineImageAddFeature,
    WM_OT_RefineImageRemoveFeature,
    WM_OT_RefineImageAddTag,
    WM_OT_RefineImageRemoveTag,
    WM_OT_RefineImageAnalyzeJSON,
    WM_OT_RefineImagePasteJSON,
    WM_OT_RefineImageSubmit,
    VIEW3D_PT_StyleEngine,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.style_engine_props = bpy.props.PointerProperty(type=StyleEngineProperties)
    
    # Create persistent preview collection for reference image thumbnails
    pcoll = bpy.utils.previews.new()
    preview_collections["ref_images"] = pcoll

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.style_engine_props
    
    # Remove preview collections
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

if __name__ == "__main__":
    register()