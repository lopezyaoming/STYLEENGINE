# ================================================================
#    Style Engine - Workspace Setup
#    Creates the AI Vision dual-workspace layout
# ================================================================

import bpy
import os
import json
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
import shutil

# Get the addon directory (works both in dev and when installed from ZIP)
ADDON_DIR = Path(__file__).parent


# ================================================================
#    BLENDER VERSION COMPATIBILITY
# ================================================================

def get_eevee_engine_name():
    """
    Get the correct EEVEE engine name for the current Blender version.
    
    Returns:
        str: 'BLENDER_EEVEE' for Blender 5.0.1+ (renamed from EEVEE_NEXT)
             'BLENDER_EEVEE_NEXT' for Blender 4.2-5.0
             'BLENDER_EEVEE' for Blender 4.1 and below (legacy)
    
    Blender 5.0.1+ renamed EEVEE_NEXT → EEVEE (legacy EEVEE was removed)
    Blender 4.2-5.0 uses EEVEE_NEXT
    Blender 4.1 and below uses legacy EEVEE
    """
    version = bpy.app.version
    
    # Blender 5.0.1+ uses 'BLENDER_EEVEE' (EEVEE_NEXT was renamed)
    if version >= (5, 0, 1):
        return 'BLENDER_EEVEE'
    
    # Blender 4.2+ uses 'BLENDER_EEVEE_NEXT'
    elif version >= (4, 2, 0):
        return 'BLENDER_EEVEE_NEXT'
    
    # Older versions use legacy 'BLENDER_EEVEE'
    else:
        return 'BLENDER_EEVEE'


# ================================================================
#    Session Management - Per-Project Library System
# ================================================================

# Global variables for session management
_session_temp_dir = None  # Legacy temp directory lock
_session_id = None  # Unique session identifier
_session_migrated = False  # Track if migration happened
_last_blend_path = None  # Track .blend path for "Save As" detection

def get_session_id():
    """
    Get or create a unique session ID.
    This ID stays consistent even if .blend file is saved mid-session.
    
    Format: YYYYMMDD_HHMMSS_random6
    Example: 20251121_143022_abc123
    
    Returns:
        str: Unique session identifier
    """
    global _session_id
    
    if _session_id is None:
        import random
        import string
        
        # Generate unique session ID: timestamp + random component
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        _session_id = f"{timestamp}_{random_suffix}"
        print(f"[Style Engine] 🆔 Session ID: {_session_id}")
    
    return _session_id


def get_project_library(context=None):
    """
    Get the project library path for the current .blend file.
    
    Returns:
        Path or None: Project library path if .blend is saved, None otherwise
    """
    if not bpy.data.is_saved:
        return None
    
    blend_path = Path(bpy.data.filepath)
    project_name = blend_path.stem
    project_lib = blend_path.parent / f"{project_name}_styleengine"
    
    return project_lib


def ensure_project_library(context):
    """
    Create project library directory structure.
    
    Structure:
        MyProject_styleengine/
        ├── Text/            - LLM/text generation outputs (future)
        ├── Images/          - All AI image generations (timestamped)
        ├── Textures/        - Projected texture snapshots
        ├── Models/          - 3D model outputs (future)
        ├── temp/            - Working files (canny, depth, current_ai.png)
        └── project_metadata.json - Generation history
    
    Returns:
        Path or None: Project library path if created, None if .blend not saved
    """
    project_lib = get_project_library(context)
    
    if project_lib is None:
        return None
    
    # Create directory structure (matching UI categories)
    (project_lib / "Text").mkdir(parents=True, exist_ok=True)
    (project_lib / "Images").mkdir(parents=True, exist_ok=True)
    (project_lib / "Textures").mkdir(parents=True, exist_ok=True)
    (project_lib / "Models").mkdir(parents=True, exist_ok=True)
    (project_lib / "temp").mkdir(parents=True, exist_ok=True)
    
    # project_lib path logged at debug level only
    
    return project_lib


def get_working_directory(context):
    """
    Get the working directory for storing AI image generations.
    
    Priority:
    1. Project library Images/ folder (if .blend saved)
    2. Session-based temp directory (if unsaved)
    
    Returns:
        Path: Directory for storing image generations
    """
    # Try project library first
    project_lib = get_project_library(context)
    if project_lib:
        ensure_project_library(context)
        return project_lib / "Images"
    
    # Fall back to session-based temp
    import tempfile
    session_id = get_session_id()
    temp_base = Path(tempfile.gettempdir()) / "blender_styleengine" / "sessions"
    session_dir = temp_base / session_id / "Images"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    return session_dir


def migrate_session_to_project(context):
    """
    Migrate session data from temp to project library.
    Called when .blend file is saved for the first time.
    
    This copies all images and textures from the temp session directory
    to the new project library, preserving all work.
    """
    global _session_migrated
    
    if _session_migrated:
        return  # Already migrated
    
    # Get paths
    project_lib = get_project_library(context)
    if not project_lib:
        return  # Can't migrate if not saved
    
    import tempfile
    session_id = get_session_id()
    temp_session = Path(tempfile.gettempdir()) / "blender_styleengine" / "sessions" / session_id
    
    if not temp_session.exists():
        _session_migrated = True  # Nothing to migrate, mark as done
        return
    
    print(f"[Style Engine] 🚚 Migrating session data to project library...")
    print(f"[Style Engine]    From: {temp_session}")
    print(f"[Style Engine]    To: {project_lib}")
    
    # Create project library structure
    ensure_project_library(context)
    
    migrated_count = 0
    
    # Copy all images (check both old "generations" and new "Images" folders for compatibility)
    for source_folder_name in ["Images", "generations"]:
        source_images = temp_session / source_folder_name
        if source_images.exists():
            for img_file in source_images.glob("*.png"):
                dest = project_lib / "Images" / img_file.name
                try:
                    shutil.copy2(img_file, dest)
                    print(f"[Style Engine]    ✓ Migrated: {img_file.name}")
                    migrated_count += 1
                except Exception as e:
                    print(f"[Style Engine]    ✗ Failed to migrate {img_file.name}: {e}")
    
    # Copy metadata if exists
    source_meta = temp_session / "project_metadata.json"
    if source_meta.exists():
        dest_meta = project_lib / "project_metadata.json"
        try:
            shutil.copy2(source_meta, dest_meta)
            print(f"[Style Engine]    ✓ Migrated: project_metadata.json")
        except Exception as e:
            print(f"[Style Engine]    ✗ Failed to migrate metadata: {e}")
    
    # Copy current_ai.png if exists
    source_current = temp_session / "current_ai.png"
    if source_current.exists():
        dest_current = project_lib / "current_ai.png"
        try:
            shutil.copy2(source_current, dest_current)
            print(f"[Style Engine]    ✓ Migrated: current_ai.png")
        except Exception as e:
            print(f"[Style Engine]    ✗ Failed to migrate current_ai.png: {e}")
    
    # Copy textures (check both old "iterations" and new "Textures" folders for compatibility)
    texture_count = 0
    for source_folder_name in ["Textures", "iterations"]:
        source_textures = temp_session / source_folder_name
        if source_textures.exists():
            for img_file in source_textures.glob("*.png"):
                dest = project_lib / "Textures" / img_file.name
                try:
                    shutil.copy2(img_file, dest)
                    print(f"[Style Engine]    ✓ Migrated texture: {img_file.name}")
                    texture_count += 1
                except Exception as e:
                    print(f"[Style Engine]    ✗ Failed to migrate {img_file.name}: {e}")
    
    if texture_count > 0:
        print(f"[Style Engine]    📦 Migrated {texture_count} textures")
    
    _session_migrated = True
    print(f"[Style Engine] ✅ Migration complete! ({migrated_count} images)")


def on_blend_file_saved(dummy):
    """
    Handler called after .blend file is saved.
    Triggers migration if this is the first save.
    """
    global _last_blend_path
    
    try:
        current_path = Path(bpy.data.filepath) if bpy.data.is_saved else None
        
        if current_path:
            # Check if this is a "Save As" (different path)
            if _last_blend_path and _last_blend_path != current_path:
                print(f"[Style Engine] 📝 'Save As' detected - keeping current project library")
                # Don't migrate again, user is creating a copy
            else:
                # First save or normal save - check if migration needed
                if not _session_migrated:
                    migrate_session_to_project(bpy.context)
            
            _last_blend_path = current_path
    
    except Exception as e:
        print(f"[Style Engine] Error in save handler: {e}")


# ================================================================
#    Generation Browser - Navigate Through Saved Generations
# ================================================================

def get_generation_list(context):
    """
    Get list of all saved generations, sorted chronologically (oldest to newest).
    
    Returns:
        list[Path]: List of generation image paths, sorted by timestamp
    """
    working_dir = get_working_directory(context)
    
    if not working_dir.exists():
        return []
    
    # Get all PNG files in generations folder
    generations = list(working_dir.glob("*.png"))
    
    # Sort by filename (which includes timestamp, so chronological)
    generations.sort()
    
    return generations


def load_generation_to_current(context, generation_path):
    """
    Load a specific generation to current_ai.png for viewing/projection.
    Writes exclusively to temp_dir/current_ai.png — the single canonical path
    that Blender's image datablock tracks.

    Args:
        context: Blender context
        generation_path: Path to the generation to load

    Returns:
        bool: True if successful
    """
    import shutil

    if not generation_path.exists():
        print(f"[Style Engine] ⚠️ Generation not found: {generation_path}")
        return False

    temp_dir = get_temp_directory(context)
    temp_dir.mkdir(parents=True, exist_ok=True)
    current_ai_path = temp_dir / "current_ai.png"

    try:
        shutil.copy2(generation_path, current_ai_path)
        refresh_ai_image()
        print(f"[Style Engine] 📷 Loaded generation: {generation_path.name}")
        return True

    except Exception as e:
        print(f"[Style Engine] ❌ Failed to load generation: {e}")
        return False


# ================================================================
#    Prompt History System
# ================================================================

def get_prompt_directory(context):
    """
    Get the Text directory for storing prompt history.
    
    Returns:
        Path: Directory for storing prompt snapshots
    """
    project_lib = get_project_library(context)
    if project_lib:
        ensure_project_library(context)
        return project_lib / "Text"
    
    # Fall back to session-based temp
    import tempfile
    session_id = get_session_id()
    temp_base = Path(tempfile.gettempdir()) / "blender_styleengine" / "sessions"
    text_dir = temp_base / session_id / "Text"
    text_dir.mkdir(parents=True, exist_ok=True)
    
    return text_dir


def get_prompt_list(context):
    """
    Get list of all saved prompt snapshots, sorted chronologically (oldest to newest).
    
    Returns:
        list[Path]: List of prompt text file paths, sorted by number
    """
    text_dir = get_prompt_directory(context)
    
    if not text_dir.exists():
        return []
    
    # Get all TXT files in Text folder
    prompts = list(text_dir.glob("*.txt"))
    
    # Sort by filename (numbered, so chronological)
    prompts.sort()
    
    return prompts


def save_prompt_snapshot(context, prefix="prompt"):
    """
    Save current STYLEENGINE_Prompt content to a numbered text file.
    
    Args:
        context: Blender context
        prefix: Prefix for filename (e.g., "before", "after")
    
    Returns:
        Path: Path to saved prompt file, or None if failed
    """
    import bpy
    
    # Get current prompt content
    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
    if not text_block:
        print("[Style Engine] ⚠️ STYLEENGINE_Prompt text block not found")
        return None
    
    content = text_block.as_string()
    if not content.strip():
        print("[Style Engine] ⚠️ Prompt is empty, skipping snapshot")
        return None
    
    # Get Text directory
    text_dir = get_prompt_directory(context)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next available number
    existing = list(text_dir.glob("*.txt"))
    next_num = len(existing)
    
    # Create filename with number and prefix
    filename = f"{next_num:03d}_{prefix}.txt"
    dest_path = text_dir / filename
    
    try:
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[Style Engine] 📝 Saved prompt snapshot: {filename}")
        return dest_path
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to save prompt snapshot: {e}")
        return None


def load_prompt_to_editor(context, prompt_path):
    """
    Load a saved prompt snapshot to STYLEENGINE_Prompt text editor.
    
    Args:
        context: Blender context
        prompt_path: Path to the prompt text file
    
    Returns:
        bool: True if successful
    """
    import bpy
    
    if not prompt_path.exists():
        print(f"[Style Engine] ⚠️ Prompt file not found: {prompt_path}")
        return False
    
    # Get or create the text block
    text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
    if not text_block:
        text_block = bpy.data.texts.new("STYLEENGINE_Prompt")
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update text block
        text_block.clear()
        text_block.write(content)
        
        print(f"[Style Engine] 📖 Loaded prompt: {prompt_path.name}")
        return True
    
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to load prompt: {e}")
        return False


# ================================================================
#    Mesh/Model Library System
# ================================================================

def get_models_directory(context):
    """
    Get the Models directory for storing 3D meshes.
    
    Returns:
        Path: Directory for storing .glb files
    """
    project_lib = get_project_library(context)
    if project_lib:
        ensure_project_library(context)
        return project_lib / "Models"
    
    # Fall back to session-based temp
    import tempfile
    session_id = get_session_id()
    temp_base = Path(tempfile.gettempdir()) / "blender_styleengine" / "sessions"
    models_dir = temp_base / session_id / "Models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    return models_dir


def get_model_list(context):
    """
    Get list of all saved models, sorted chronologically (oldest to newest).
    
    Returns:
        list[Path]: List of model file paths (.glb), sorted by timestamp
    """
    models_dir = get_models_directory(context)
    
    if not models_dir.exists():
        return []
    
    # Get all GLB files in Models folder
    models = list(models_dir.glob("*.glb"))
    
    # Sort by filename (which includes timestamp, so chronological)
    models.sort()
    
    return models


def spawn_model_from_library(context, model_path):
    """
    Import a saved model from the library into the scene.
    
    Args:
        context: Blender context
        model_path: Path to the .glb file
    
    Returns:
        bpy.types.Object or None: The imported object, or None if failed
    """
    import bpy
    
    if not model_path.exists():
        print(f"[Style Engine] ⚠️ Model not found: {model_path}")
        return None
    
    try:
        # Store original selection
        original_selected = list(bpy.context.selected_objects)
        
        # Import GLB
        bpy.ops.import_scene.gltf(filepath=str(model_path))
        
        # Get newly imported objects
        newly_imported = [o for o in bpy.context.selected_objects if o not in original_selected]
        
        if newly_imported:
            new_obj = newly_imported[0]
            # Name based on original filename (without timestamp prefix)
            base_name = model_path.stem  # e.g., "20260126_143022_001_textured"
            new_obj.name = f"Spawned_{base_name[-20:]}"  # Take last part
            new_obj.location = bpy.context.scene.cursor.location  # Spawn at 3D cursor
            
            print(f"[Style Engine] 🧊 Spawned model: {new_obj.name}")
            return new_obj
        else:
            print(f"[Style Engine] ⚠️ Model imported but no object found")
            return None
    
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to spawn model: {e}")
        return None


def save_mesh_to_library(context, source_mesh_path, mesh_type='mesh'):
    """
    Save a generated 3D mesh to the project library Models folder.
    
    Args:
        context: Blender context
        source_mesh_path: Path to the downloaded .glb file
        mesh_type: Type identifier ('mesh', 'textured', 'uv_textured')
    
    Returns:
        Path: Path to the saved mesh file, or None if failed
    """
    source_path = Path(source_mesh_path)
    
    if not source_path.exists():
        print(f"[Style Engine] ⚠️ Mesh file not found: {source_path}")
        return None
    
    # Get Models directory
    models_dir = get_models_directory(context)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    microseconds = datetime.now().microsecond // 1000
    filename = f"{timestamp}_{microseconds:03d}_{mesh_type}.glb"
    
    dest_path = models_dir / filename
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"[Style Engine] 🧊 Saved mesh: {filename}")
        return dest_path
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to save mesh: {e}")
        return None


def save_generation_to_library(context, source_image_path, backend='unknown'):
    """
    Save a generated image to the project library with proper organization.
    
    This function:
    1. Checks if .blend is saved and migrates session if needed
    2. Saves timestamped copy to generations folder
    3. Updates current_ai.png
    4. Optionally saves to output_path (legacy behavior)
    
    Args:
        context: Blender context
        source_image_path: Path to the generated image
        backend: 'GCS', 'RunComfy', or 'Local'
    
    Returns:
        Path: Path to the saved generation file
    """
    # Check if .blend was saved since last generation (trigger migration)
    if bpy.data.is_saved and not _session_migrated:
        migrate_session_to_project(context)
    
    # Get working directory (project library or session temp)
    working_dir = get_working_directory(context)
    working_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filename, embedding render resolution so history
    # navigation can restore the correct viewport format for each generation.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    microseconds = datetime.now().microsecond // 1000  # milliseconds for uniqueness
    try:
        w = context.scene.render.resolution_x
        h = context.scene.render.resolution_y
    except Exception:
        w, h = 1024, 1024
    filename = f"{timestamp}_{microseconds:03d}_{backend.lower()}_{w}x{h}.png"
    
    dest_path = working_dir / filename
    
    # Copy to generations folder
    try:
        shutil.copy2(source_image_path, dest_path)
        print(f"[Style Engine] 💾 Saved generation: {filename}")
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to save generation: {e}")
        return None

    # Note: current_ai.png is NOT duplicated here.
    # The download callback always writes directly to temp_dir/current_ai.png,
    # which is the single canonical path that Blender's datablock tracks.
    # Maintaining a second copy under project_lib/ or session_dir/ was the
    # source of stale-image bugs when filepath_raw pointed to temp_dir.
    
    # Also save to output_path if set (user-specified backup location)
    props = context.scene.style_engine_props
    if hasattr(props, 'output_path') and props.output_path and os.path.exists(props.output_path):
        output_dir = Path(props.output_path) / "Images"
        output_dir.mkdir(exist_ok=True, parents=True)
        
        output_path = output_dir / f"{timestamp}_{backend.lower()}_{w}x{h}.png"
        try:
            shutil.copy2(source_image_path, output_path)
            print(f"[Style Engine] 📤 Also saved to output_path: {output_path}")
        except Exception as e:
            print(f"[Style Engine] ⚠️ Failed to save to output_path: {e}")
    
    return dest_path


# ================================================================
#    Legacy Temp Directory System (Maintained for Compatibility)
# ================================================================

def get_temp_directory(context=None):
    """
    Get the temp directory for storing AI vision working files (canny, depth, current_ai.png).
    Once determined, the path is locked for the entire session to prevent
    filepath issues when .blend file is saved mid-session.
    
    Priority:
    1. Use project library temp folder if .blend is saved (ProjectName_styleengine/temp/)
    2. Use output_path temp folder if set
    3. Fall back to system temp directory
    """
    global _session_temp_dir
    
    # If already determined, reuse it (prevents save-time path changes)
    if _session_temp_dir is not None:
        return _session_temp_dir
    
    # Determine temp directory (priority order)
    temp_dir = None
    
    # 1. Try project library temp folder if .blend is saved
    if bpy.data.is_saved:
        project_lib = get_project_library(context)
        if project_lib:
            temp_dir = project_lib / "temp"
    
    # 2. Try user's output_path setting
    if temp_dir is None and context:
        try:
            props = context.scene.style_engine_props
            if hasattr(props, 'output_path') and props.output_path:
                output_path = Path(props.output_path)
                if output_path.exists():
                    temp_dir = output_path / "temp"
        except:
            pass
    
    # 3. Fall back to system temp
    if temp_dir is None:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "temp"
    
    # Lock it for this session
    _session_temp_dir = temp_dir
    print(f"[Style Engine] 🔒 Temp directory locked: {temp_dir}")
    
    return temp_dir


def reset_temp_directory():
    """
    Reset temp directory lock (called when setting up new workspace).
    Allows the path to be re-determined based on current .blend save state.
    """
    global _session_temp_dir
    old_path = _session_temp_dir
    _session_temp_dir = None
    if old_path:
        print(f"[Style Engine] 🔓 Temp directory unlocked (was: {old_path})")

# Global variable to track last modification time
_last_image_mtime = 0

# Global variable for render interval
RENDER_INTERVAL = 5.0  # seconds

# Global variable to lock temp directory for session consistency
_session_temp_dir = None


def write_session_json(context):
    """
    Write session.json with current workspace state.
    Called whenever UI properties change.
    """
    try:
        props = context.scene.style_engine_props
        scene = context.scene
        
        # Get ComfyUI path from preferences
        prefs = context.preferences.addons['styleengine'].preferences
        comfy_path = prefs.comfy_path if hasattr(prefs, 'comfy_path') else ""
        
        # Parse resolution
        res_str = props.ai_resolution  # e.g., "1024x1024"
        width, height = map(int, res_str.split('x'))
        
        # Build session data
        session_data = {
            "session_id": props.library_id,
            "version": "0.1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "scene_ref": {
                "blend_path": bpy.data.filepath if bpy.data.filepath else "//",
                "scene_name": scene.name,
                "camera_name": "ai_camera"
            },
            "agent_id": "agent.comfy.local.v1",  # Placeholder for now
            "resolution": {
                "preset": f"native_{width}" if width == height else res_str,
                "width": width,
                "height": height
            },
            "lookup": props.lookup,
            "global_prompt": props.global_prompt,
            "negative_prompt": props.negative_prompt if hasattr(props, 'negative_prompt') else "",
            "depth_influence": round(props.depth_influence, 3),
            "silhouette_influence": round(props.silhouette_influence, 3),
            "texture_influence": round(props.texture_influence, 3),
            "steps": props.steps,
            "ipadapter": {
                "enabled": props.use_ipadapter if hasattr(props, 'use_ipadapter') else False,
                "reference_image": props.ipadapter_reference_image if hasattr(props, 'ipadapter_reference_image') else "",
                "weight_type": props.ipadapter_weight_type if hasattr(props, 'ipadapter_weight_type') else "style transfer",
                "strength": round(props.ipadapter_strength, 2) if hasattr(props, 'ipadapter_strength') else 0.75
            },
            "lora": {
                "enabled": props.lora_enabled if hasattr(props, 'lora_enabled') else False,
                "name": props.lora_name if hasattr(props, 'lora_name') else "NONE",
                "strength_model": round(props.lora_strength_model, 3) if hasattr(props, 'lora_strength_model') else 0.8,
                "strength_clip": round(props.lora_strength_model, 3) if hasattr(props, 'lora_strength_model') else 0.8
            },
            "lora2": {
                "enabled": props.lora2_enabled if hasattr(props, 'lora2_enabled') else False,
                "name": props.lora2_name if hasattr(props, 'lora2_name') else "NONE",
                "strength_model": round(props.lora2_strength_model, 3) if hasattr(props, 'lora2_strength_model') else 0.8,
                "strength_clip": round(props.lora2_strength_model, 3) if hasattr(props, 'lora2_strength_model') else 0.8
            },
            "reference_images": {
                # Global strengths (UI: 0.0-1.0, multiplied by 1.5 for workflow: 0.0-1.5)
                "style_transfer_strength": round(props.style_transfer_strength * 1.5, 3),
                "composition_strength": round(props.composition_strength * 1.5, 3),
                "force_transfer_strength": round(props.force_transfer_strength, 3),
                # Individual weights
                "st1_weight": round(props.st1_weight, 3),
                "st2_weight": round(props.st2_weight, 3),
                "st3_weight": round(props.st3_weight, 3),
                "st4_weight": round(props.st4_weight, 3),
                "st5_weight": round(props.st5_weight, 3),
                "comp1_weight": round(props.comp1_weight, 3),
                "comp2_weight": round(props.comp2_weight, 3),
                "comp3_weight": round(props.comp3_weight, 3),
                "comp4_weight": round(props.comp4_weight, 3),
                "comp5_weight": round(props.comp5_weight, 3),
                "sst1_weight": round(props.sst1_weight, 3),
                "sst2_weight": round(props.sst2_weight, 3),
                "sst3_weight": round(props.sst3_weight, 3),
                "sst4_weight": round(props.sst4_weight, 3),
                "sst5_weight": round(props.sst5_weight, 3),
                # Image paths (stored as filenames for ComfyUI)
                "st1_path": os.path.basename(props.st1_image.filepath) if props.st1_image else "",
                "st2_path": os.path.basename(props.st2_image.filepath) if props.st2_image else "",
                "st3_path": os.path.basename(props.st3_image.filepath) if props.st3_image else "",
                "st4_path": os.path.basename(props.st4_image.filepath) if props.st4_image else "",
                "st5_path": os.path.basename(props.st5_image.filepath) if props.st5_image else "",
                "comp1_path": os.path.basename(props.comp1_image.filepath) if props.comp1_image else "",
                "comp2_path": os.path.basename(props.comp2_image.filepath) if props.comp2_image else "",
                "comp3_path": os.path.basename(props.comp3_image.filepath) if props.comp3_image else "",
                "comp4_path": os.path.basename(props.comp4_image.filepath) if props.comp4_image else "",
                "comp5_path": os.path.basename(props.comp5_image.filepath) if props.comp5_image else "",
                "sst1_path": os.path.basename(props.sst1_image.filepath) if props.sst1_image else "",
                "sst2_path": os.path.basename(props.sst2_image.filepath) if props.sst2_image else "",
                "sst3_path": os.path.basename(props.sst3_image.filepath) if props.sst3_image else "",
                "sst4_path": os.path.basename(props.sst4_image.filepath) if props.sst4_image else "",
                "sst5_path": os.path.basename(props.sst5_image.filepath) if props.sst5_image else "",
            },
            "objects": [
                {
                    "group_id": f"grp-{group.name.lower().replace(' ', '-')}-{str(idx+1).zfill(3)}",
                    "label": group.name.lower(),
                    "object_ids": [obj_id.strip() for obj_id in group.object_ids.split(',') if obj_id.strip()],
                    "pass_index": group.pass_index,
                    "keywords": [kw.strip() for kw in group.keywords.split(',') if kw.strip()],
                    "mask": {
                        "export": True,
                        "type": "object_index",
                        "path": f"//temp/ai_vision/passes/id_{group.pass_index}.png"
                    }
                }
                for idx, group in enumerate(props.object_groups)
            ],
            "routing": {
                "temp_dir": str(get_temp_directory(context)).replace("\\", "/") + "/",
                "preview_out": str(get_temp_directory(context) / "current_ai.png").replace("\\", "/"),
                "passes_dir": str(get_temp_directory(context) / "passes").replace("\\", "/") + "/",
                "commits_dir": props.output_path.replace("\\", "/") + "/",
                "comfy_path": comfy_path.replace("\\", "/") if comfy_path else ""
            },
            "flags": {
                "live_preview": props.refresh_viewport,
                "auto_generate": props.auto_generate,
                "autosave_every_sec": RENDER_INTERVAL
            }
        }
        
        # Write to temp file then rename (atomic write)
        temp_dir = get_temp_directory(context)
        session_path = temp_dir / "session.json"
        
        # Ensure directory exists
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        session_tmp = str(session_path) + ".tmp"
        
        with open(session_tmp, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Atomic replace
        os.replace(session_tmp, str(session_path))
        
    except Exception as e:
        print(f"[Style Engine] Error writing session.json: {e}")


def compress_image_for_upload(image_path, max_side=1920):
    """
    Downscale an image if either dimension exceeds max_side, preserving aspect ratio.
    Saves as JPEG quality 90 to a temp file. Returns the (possibly new) path.
    """
    from pathlib import Path
    try:
        img = bpy.data.images.load(str(image_path), check_existing=False)
        w, h = img.size[0], img.size[1]
        if w <= max_side and h <= max_side:
            bpy.data.images.remove(img)
            return Path(image_path)

        scale = max_side / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img.scale(new_w, new_h)

        temp_dir = get_temp_directory(bpy.context)
        out_path = temp_dir / f"ref_compressed_{Path(image_path).stem}.jpg"
        img.filepath_raw = str(out_path)
        img.file_format = 'JPEG'
        img.save()
        bpy.data.images.remove(img)

        print(f"[Compress] {w}x{h} -> {new_w}x{new_h}: {out_path.name}")
        return out_path
    except Exception as e:
        print(f"[Compress] Failed, using original: {e}")
        return Path(image_path)


def _reattach_camera_background(img):
    """
    Attach a Blender image datablock to the ai_camera background slot.
    Called when the 'current_ai.png' datablock was lost and had to be re-created.
    """
    try:
        ai_camera_obj = bpy.data.objects.get("ai_camera")
        if ai_camera_obj is None:
            return
        cam_data = ai_camera_obj.data
        cam_data.show_background_images = True
        if len(cam_data.background_images) > 0:
            bg = cam_data.background_images[0]
        else:
            bg = cam_data.background_images.new()
        bg.image = img
        bg.display_depth = 'FRONT'
        bg.frame_method = 'STRETCH'
        print("[Style Engine] ✓ Re-attached current_ai.png to ai_camera background")
    except Exception as e:
        print(f"[Style Engine] Warning: Could not re-attach camera background: {e}")


def refresh_ai_image():
    """
    Reload current_ai.png in Blender's image datablock so the camera background
    shows the latest generation.

    Robust against:
    - filepath_raw drifting after a temp-dir move (re-asserts the canonical path)
    - datablock being lost after Undo or manual deletion (re-creates and re-attaches)
    - GPU texture not invalidating (calls img.update() after reload)
    """
    try:
        # Always read from the locked temp_dir — this is the one canonical location
        temp_dir = get_temp_directory(bpy.context)
        img_path = temp_dir / "current_ai.png"

        if not img_path.exists():
            print(f"[Style Engine] Warning: current_ai.png not found at {img_path}")
            return

        canonical = str(img_path)

        if "current_ai.png" in bpy.data.images:
            img = bpy.data.images["current_ai.png"]

            # Re-assert the path in case it drifted (e.g. after a workspace reset
            # that moved the temp directory to a new location)
            if img.filepath_raw != canonical:
                print(f"[Style Engine] ↩ filepath_raw updated: {img.filepath_raw} → {canonical}")
                img.filepath_raw = canonical

            img.reload()
            img.update()  # ensures GPU texture is invalidated
        else:
            # Datablock was lost (Undo, user deleted it, etc.) — recover it
            print("[Style Engine] ⚠ current_ai.png datablock lost — re-loading from disk")
            img = bpy.data.images.load(canonical, check_existing=False)
            img.name = "current_ai.png"
            img.filepath_raw = canonical
            img.update()
            _reattach_camera_background(img)

        # Tag all 3-D viewports for redraw across every window
        try:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        except Exception:
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

        print(f"[Style Engine] ✓ Image reloaded: {os.path.basename(img_path)}")

    except Exception as e:
        print(f"[Style Engine] Error reloading image: {e}")


def copy_reference_images_to_comfyui(context):
    """
    Copy reference images to ComfyUI's input directory so they can be used in the workflow.
    Returns True if successful, False otherwise.
    """
    try:
        # Get ComfyUI path from preferences
        prefs = context.preferences.addons['styleengine'].preferences
        comfy_path = prefs.comfy_path if hasattr(prefs, 'comfy_path') else ""
        
        if not comfy_path or not os.path.exists(comfy_path):
            print(f"[Style Engine] Warning: ComfyUI path not set or invalid")
            print(f"[Style Engine] Reference images will not be copied automatically")
            return False
        
        # ComfyUI input directory
        input_dir = Path(comfy_path) / "input"
        if not input_dir.exists():
            print(f"[Style Engine] Warning: ComfyUI input directory not found: {input_dir}")
            return False
        
        props = context.scene.style_engine_props
        copied_count = 0
        
        # List of all reference image properties
        ref_images = [
            ('st1_image', 'ST1'), ('st2_image', 'ST2'), ('st3_image', 'ST3'), 
            ('st4_image', 'ST4'), ('st5_image', 'ST5'),
            ('comp1_image', 'COMP1'), ('comp2_image', 'COMP2'), ('comp3_image', 'COMP3'),
            ('comp4_image', 'COMP4'), ('comp5_image', 'COMP5'),
            ('sst1_image', 'SST1'), ('sst2_image', 'SST2'), ('sst3_image', 'SST3'),
            ('sst4_image', 'SST4'), ('sst5_image', 'SST5'),
        ]
        
        for prop_name, label in ref_images:
            img = getattr(props, prop_name)
            if img and img.filepath:
                src_path = bpy.path.abspath(img.filepath)
                if os.path.exists(src_path):
                    filename = os.path.basename(src_path)
                    dest_path = input_dir / filename
                    
                    # Copy file
                    shutil.copy2(src_path, dest_path)
                    copied_count += 1
                    print(f"[Style Engine] Copied {label}: {filename} → ComfyUI/input/")
                else:
                    print(f"[Style Engine] Warning: {label} source file not found: {src_path}")
        
        if copied_count > 0:
            print(f"[Style Engine] ✓ Copied {copied_count} reference images to ComfyUI")
            return True
        else:
            print(f"[Style Engine] No reference images to copy")
            return False
            
    except Exception as e:
        print(f"[Style Engine] Error copying reference images: {e}")
        import traceback
        traceback.print_exc()
        return False


def auto_render_passes():
    """
    Auto-render timer with SURGICAL camera handling.
    DEPRECATED: Rendering should only happen when needed (cyclical with generation).
    This timer is kept for compatibility but should remain disabled.
    """
    try:
        # Check if refresh is still enabled
        props = bpy.context.scene.style_engine_props
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        
        if not props.refresh_viewport:
            # Stop the timer if refresh is disabled
            return None
        
        # ⚠️ ALWAYS SKIP timer-based rendering - wasteful!
        # Rendering happens cyclically with generation instead:
        # 1. Render on setup (initial)
        # 2. Render before sending to AI (in generate_ai_image_cloud)
        # 3. After receiving AI result, render for next iteration
        if prefs.debug_mode:
            print("[Style Engine] Skipping timer-based render (wasteful - use cyclical generation instead)")
        return RENDER_INTERVAL  # Keep timer alive but never render
        
        camera_name = prefs.camera_name_override
        
        # Find the ai_camera
        if camera_name not in bpy.data.objects:
            print(f"[Style Engine] {camera_name} not found, skipping render")
            return RENDER_INTERVAL
        
        ai_camera = bpy.data.objects[camera_name]
        scene = bpy.context.scene
        
        # Store original settings
        original_engine = scene.render.engine
        original_samples = scene.eevee.taa_render_samples
        original_file_format = scene.render.image_settings.file_format
        
        # Configure render settings (version-compatible)
        scene.render.engine = get_eevee_engine_name()
        scene.eevee.taa_render_samples = 16
        scene.render.image_settings.file_format = 'PNG'  # Force PNG
        
        # Set output path for the main render
        temp_dir = get_temp_directory(bpy.context)
        passes_dir = temp_dir.parent / "passes"
        passes_dir.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(passes_dir / "combined")
        
        # SURGICAL: Render from ai_camera without changing active camera
        print(f"[Style Engine] Auto-rendering from {camera_name}...")
        render_from_camera_safe(scene, ai_camera, prefs)
        
        # Restore original settings
        scene.render.engine = original_engine
        scene.eevee.taa_render_samples = original_samples
        scene.render.image_settings.file_format = original_file_format
        
        print(f"[Style Engine] Auto-render complete")
        
    except Exception as e:
        print(f"[Style Engine] Error in auto-render: {e}")
    
    # Continue running every RENDER_INTERVAL seconds
    return RENDER_INTERVAL


# ----------------------------------------------------------------
# STANDALONE HELPER FOR DELAYED WORKSPACE SPLIT
# ----------------------------------------------------------------

def _delayed_horizontal_split_standalone(camera, original_area):
    """
    Second delayed callback for horizontal split (text editor).
    Called after vertical split has had time to calculate layout.
    """
    context = bpy.context
    prefs = context.preferences.addons['styleengine'].preferences
    _ai_model = getattr(context.scene.style_engine_props, 'ai_model', 'SDXL') if hasattr(context, 'scene') and context.scene else 'SDXL'

    from . import utils
    prompt_text = utils.get_or_create_prompt_text(model=_ai_model)

    # Find the right area (should be sized now)
    view3d_areas = [a for a in context.screen.areas if a.type == 'VIEW_3D']
    
    right_area = None
    for a in view3d_areas:
        if a != original_area:
            right_area = a
            break
    
    if not right_area:
        right_area = view3d_areas[-1] if len(view3d_areas) > 0 else None
    
    if not right_area:
        print("[Style Engine] ERROR: Could not find right area for horizontal split")
        return
    
    print(f"[Style Engine] DEBUG: Right area NOW: {right_area.width}x{right_area.height} at ({right_area.x}, {right_area.y})")
    
    # Check if area is sized now
    if right_area.width == 0 or right_area.height == 0:
        print(f"[Style Engine] ERROR: Area still 0x0 after delay - cannot split")
        print("[Style Engine] Please manually split the camera view and add text editor")
        return
    
    # Split horizontally
    print(f"[Style Engine] DEBUG: Attempting horizontal split on sized area...")
    
    try:
        override = {'area': right_area, 'region': right_area.regions[-1]}
        with context.temp_override(**override):
            result = bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.33)  # JUST USE 0.33
        
        print(f"[Style Engine] DEBUG: Horizontal split returned: {result}")
        
        if result != {'FINISHED'}:
            print(f"[Style Engine] WARNING: Horizontal split failed: {result}")
            return
        
        # Check if new area was created
        view3d_after = [a for a in context.screen.areas if a.type == 'VIEW_3D']
        
        if len(view3d_after) < 3:
            print(f"[Style Engine] WARNING: Horizontal split didn't create new area (still {len(view3d_after)} areas)")
            return
        
        print("[Style Engine] ✓ Horizontal split successful")
        
        # Find and convert bottom area to text editor
        right_areas = [a for a in view3d_after if a != original_area]
        
        if len(right_areas) >= 2:
            # Bottom area has LOWER Y position (closer to 0), top area has HIGHER Y
            bottom_area = min(right_areas, key=lambda a: a.y)
            top_area = max(right_areas, key=lambda a: a.y)
            
            # Re-apply clean UI settings to top area (camera view) after split
            if top_area.type == 'VIEW_3D':
                for space in top_area.spaces:
                    if space.type == 'VIEW_3D':
                        space.show_region_toolbar = False  # Hide T panel
                        space.show_region_ui = False  # Hide N panel
                        space.show_region_header = True  # Keep header
                print("[Style Engine] ✓ Camera view: Clean UI maintained after split")
            
            print(f"[Style Engine] DEBUG: Converting area {bottom_area.width}x{bottom_area.height} to text editor")
            
            bottom_area.type = 'TEXT_EDITOR'
            
            if bottom_area.type == 'TEXT_EDITOR':
                bottom_area.spaces.active.text = prompt_text
                bottom_area.spaces.active.show_line_numbers = False  # Clean look
                bottom_area.spaces.active.show_syntax_highlight = False  # No syntax coloring
                bottom_area.spaces.active.show_word_wrap = True  # Wrap long prompts
                bottom_area.spaces.active.show_region_header = True  # Keep header for text editor
                print("[Style Engine] ✓ Text editor configured (bottom)")
            else:
                print(f"[Style Engine] ERROR: Failed to convert to text editor")
        else:
            print(f"[Style Engine] WARNING: Could not find bottom area")
        
        # Set camera as active
        if camera:
            context.view_layer.objects.active = camera
        
        # Redraw
        for area in context.screen.areas:
            area.tag_redraw()
        
        print("[Style Engine] ✓ Workspace layout complete: Modeling | Camera + Prompt")
        
    except Exception as e:
        print(f"[Style Engine] ERROR: Horizontal split exception: {e}")
        import traceback
        traceback.print_exc()


def _delayed_split_setup_standalone(camera):
    """
    Standalone function for delayed workspace split setup with text editor integration.
    Creates: Left 75% = modeling view, Right 25% = camera (top 2/3) + text editor (bottom 1/3)
    
    TIMING: This does the vertical split, then schedules a second callback for horizontal split.
    """
    context = bpy.context
    prefs = context.preferences.addons['styleengine'].preferences
    
    if not prefs.enable_viewport_split:
        if prefs.debug_mode:
            print("[Style Engine] Viewport split disabled in preferences")
        return
    
    # Import utils for text editor functions
    from . import utils
    _ai_model = getattr(context.scene.style_engine_props, 'ai_model', 'SDXL') if hasattr(context, 'scene') and context.scene else 'SDXL'

    # Create/get the prompt text block
    prompt_text = utils.get_or_create_prompt_text(model=_ai_model)

    # Find the 3D viewport in the current workspace
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            original_area = area
            break
    else:
        print("[Style Engine] ERROR: No 3D viewport found")
        return
    
    # STEP 1: Split vertically (left 75% / right 25%)
    try:
        override = {'area': original_area, 'region': original_area.regions[-1]}
        with context.temp_override(**override):
            result = bpy.ops.screen.area_split(direction='VERTICAL', factor=0.75)
        
        if result != {'FINISHED'}:
            print(f"[Style Engine] ERROR: Vertical split failed: {result}")
            return
        
        print("[Style Engine] ✓ Vertical split successful")
        
    except Exception as e:
        print(f"[Style Engine] ERROR: Vertical split exception: {e}")
        return
    
    # STEP 2: Find the right area (the newly created one)
    view3d_areas = [a for a in context.screen.areas if a.type == 'VIEW_3D']
    if len(view3d_areas) < 2:
        print(f"[Style Engine] ERROR: Expected 2 VIEW_3D areas after split, but got {len(view3d_areas)}")
        return
    
    # The right area is the one that's NOT the original
    right_area = None
    for a in view3d_areas:
        if a != original_area:
            right_area = a
            break
    
    if not right_area:
        # Fallback: use the last one
        right_area = view3d_areas[-1]
    
    if prefs.debug_mode:
        print(f"[Style Engine] Right area found: {right_area.width}x{right_area.height} at position ({right_area.x}, {right_area.y})")
    
    # STEP 3: Configure left area (modeling view) - Show N panel for Style Engine
    for space in original_area.spaces:
        if space.type == 'VIEW_3D':
            space.show_region_ui = True  # Show N panel (right sidebar) with Style Engine panel
    
    print("[Style Engine] ✓ Modeling view: N panel visible")
    
    # STEP 4: Configure right area as camera view - Hide unnecessary UI for clean preview
    for space in right_area.spaces:
        if space.type == 'VIEW_3D':
            space.region_3d.view_perspective = 'CAMERA'
            space.lock_camera = True
            space.shading.type = 'SOLID'
            space.overlay.show_extras = True
            
            # 📐 FIT CAMERA FRAME TO VIEWPORT (auto-fit regardless of screen size)
            space.region_3d.view_camera_zoom = 0
            
            # Hide UI elements for clean AI preview
            space.show_region_toolbar = False  # Hide T panel (left toolbar: select, move, etc.)
            space.show_region_ui = False  # Hide N panel (right sidebar)
            space.show_region_header = True  # Keep header (camera name, etc.)
    
    print("[Style Engine] ✓ Camera view configured (clean UI, no toolbars)")
    
    # STEP 4: Schedule delayed horizontal split (needs time for layout to calculate)
    # The area is currently 0x0, so we can't split it immediately
    # Use a timer callback like we did for the initial vertical split
    print(f"[Style Engine] Scheduling horizontal split (0.2s delay for layout calculation)...")
    
    def delayed_horizontal_split():
        _delayed_horizontal_split_standalone(camera, original_area)
        return None  # Don't repeat
    
    bpy.app.timers.register(delayed_horizontal_split, first_interval=0.2)
    
    # Set the active object to the camera
    if camera:
        context.view_layer.objects.active = camera
    
    # Force redraw all areas
    for area in context.screen.areas:
        area.tag_redraw()


# NOTE: HeavyPoly hijacking disabled - function kept latent
# def _hijack_heavypoly_areas_standalone(screen, camera):
#     """
#     STANDALONE function to hijack HeavyPoly areas.
#     Must be standalone (not a method) because it's called from a timer after the operator is destroyed.
#     
#     Transformations:
#     - Image Editor → 3D View (camera locked for AI output)
#     - Split camera area horizontally (80% camera / 20% prompt) → Add Text Editor below
#     - Use timer delay to ensure Blender processes the split before configuring prompt area
#     - Leave HeavyPoly's original text editor untouched
#     
#     Args:
#         screen: Blender screen with areas to hijack
#         camera: AI camera to lock view to
#     """
#     from . import utils
#     
#     print("[Style Engine] 🔧 Hijacking HeavyPoly window areas...")
#     
#     # Track what we found
#     found_image_editor = False
#     camera_area = None
#     
#     # STEP 1: Find and convert Image Editor to camera view
#     for area in screen.areas:
#         if area.type == 'IMAGE_EDITOR':
#             print(f"[Style Engine]   📷 Found Image Editor at ({area.x}, {area.y})")
#             camera_area = area
#             
#             # Change to 3D View
#             area.type = 'VIEW_3D'
#             
#             # Configure the 3D View
#             for space in area.spaces:
#                 if space.type == 'VIEW_3D':
#                     # Lock to camera
#                     space.region_3d.view_perspective = 'CAMERA'
#                     space.camera = camera
#                     
#                     # 📐 FIT CAMERA FRAME TO VIEWPORT (auto-fit regardless of screen size)
#                     space.region_3d.view_camera_zoom = 0
#                     
#                     # Set shading to solid with textures
#                     space.shading.type = 'SOLID'
#                     space.shading.light = 'FLAT'
#                     space.shading.color_type = 'TEXTURE'
#                     
#                     # Show camera background image
#                     space.overlay.show_extras = True
#                     
#                     # Clean UI
#                     space.show_region_toolbar = False
#                     space.show_region_ui = False
#                     space.show_region_header = True
#                     
#                     print("[Style Engine]   ✅ Converted to camera-locked 3D View")
#                     found_image_editor = True
#                     break
#             
#             break  # Only process first Image Editor
#     
#     if not found_image_editor:
#         print("[Style Engine] ⚠️  No Image Editor found (cannot create prompt area)")
#         for area in screen.areas:
#             area.tag_redraw()
#         return
#     
#     # STEP 2: Split the camera area horizontally to add text editor below
#     print("[Style Engine]   📝 Creating Style Engine prompt area below AI camera...")
#     
#     try:
#         # Need to use temp_override for the split operation
#         context = bpy.context
#         override = {'area': camera_area, 'region': camera_area.regions[-1]}
#         
#         with context.temp_override(**override):
#             # Split horizontally: Top 20% (camera), Bottom 80% (prompt)
#             result = bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.2)
#         
#         if result == {'FINISHED'}:
#             print("[Style Engine]   ✅ Split camera area (80% camera / 20% prompt)")
#             
#             # Schedule delayed configuration (Blender needs time to process split)
#             camera_x = camera_area.x
#             camera_y = camera_area.y
#             
#             def delayed_prompt_setup():
#                 # Debug: Print all VIEW_3D areas
#                 print(f"[Style Engine]   🔍 Looking for bottom area (camera was at x={camera_x}, y={camera_y})...")
#                 view3d_areas = [a for a in screen.areas if a.type == 'VIEW_3D']
#                 print(f"[Style Engine]   Found {len(view3d_areas)} VIEW_3D areas:")
#                 for i, area in enumerate(view3d_areas):
#                     print(f"[Style Engine]     Area {i}: x={area.x}, y={area.y}, width={area.width}, height={area.height}")
#                 
#                 # Find the newly created bottom area
#                 # It should be a VIEW_3D area at the same X position but lower Y
#                 bottom_area = None
#                 
#                 # Look for VIEW_3D areas at same X position
#                 candidates = [a for a in screen.areas if a.type == 'VIEW_3D' and a.x == camera_x]
#                 print(f"[Style Engine]   Candidates at x={camera_x}: {len(candidates)}")
#                 
#                 # Sort by Y position (lower Y = bottom)
#                 if len(candidates) >= 2:
#                     candidates.sort(key=lambda a: a.y)
#                     bottom_area = candidates[0]  # Lowest Y = bottom area
#                     print(f"[Style Engine]   Selected bottom area: x={bottom_area.x}, y={bottom_area.y}")
#                 
#                 if bottom_area:
#                     # Convert bottom area to Text Editor
#                     bottom_area.type = 'TEXT_EDITOR'
#                     
#                     # Load our prompt
#                     prompt_text = utils.get_or_create_prompt_text()
#                     
#                     for space in bottom_area.spaces:
#                         if space.type == 'TEXT_EDITOR':
#                             space.text = prompt_text
#                             space.show_line_numbers = False  # Line numbers OFF
#                             space.show_syntax_highlight = False  # Syntax highlight OFF
#                             space.show_line_highlight = False  # Highlight line OFF
#                             space.show_word_wrap = True  # Word wrap ON
#                             space.show_region_header = True
#                             
#                             print("[Style Engine]   ✅ Style Engine prompt loaded below AI camera")
#                             break
#                     
#                     print("[Style Engine] 🎉 HeavyPoly workspace hijacked! (Camera + Prompt added, HeavyPoly text untouched)")
#                 else:
#                     print("[Style Engine] ⚠️  Could not find bottom area after split")
#                     print("[Style Engine] ℹ️  Prompt available in Text Editor menu → STYLEENGINE_Prompt")
#                 
#                 # Force redraw
#                 for area in screen.areas:
#                     area.tag_redraw()
#                 
#                 return None  # Don't repeat
#             
#             # Wait 0.3 seconds for Blender to process the split (increased from 0.1)
#             bpy.app.timers.register(delayed_prompt_setup, first_interval=0.3)
#             
#         else:
#             print(f"[Style Engine] ⚠️  Split failed: {result}")
#             print("[Style Engine] ℹ️  Prompt available in Text Editor menu")
#     
#     except Exception as e:
#         print(f"[Style Engine] ⚠️  Could not split area: {e}")
#         import traceback
#         traceback.print_exc()
#         print("[Style Engine] ℹ️  Prompt available in Text Editor menu")
#     
#     # Force redraw all areas
#     for area in screen.areas:
#         area.tag_redraw()


class WM_OT_SetupWorkspace(bpy.types.Operator):
    """Setup the AI Vision workspace with dual 3D views and AI camera."""
    bl_idname = "style_engine.setup_workspace"
    bl_label = "Setup Workspace"
    bl_description = "Create AI Vision workspace with split view and AI camera"
    
    def execute(self, context):
        # Reset temp directory lock (allows re-determination if .blend was saved)
        reset_temp_directory()
        
        # Create temp directory for AI images
        self.ensure_temp_directory(context)
        
        # Create or get the AI camera
        ai_camera = self.create_ai_camera(context)

        # In Gemini mode, sync from scene camera if one exists; otherwise align to view
        _props = context.scene.style_engine_props
        _gemini_synced = False
        if getattr(_props, 'ai_model', 'SDXL') == 'GEMINI':
            _gemini_synced = sync_ai_camera_from_scene(context)
        if not _gemini_synced:
            self.align_camera_to_view(context, ai_camera)

        # Setup camera background image (resolution override skipped in Gemini sync mode)
        self.setup_camera_background(context, ai_camera, skip_resolution_override=_gemini_synced)
        
        # Create the AI workspace (always from default Layout)
        workspace = self.create_ai_workspace(context)
        
        # NOTE: Render engine is NOT changed by Style Engine
        # Users can choose Fast (Workbench) or Detailed (EEVEE) via pie menu
        # This respects the user's existing render setup
        
        # Skip compositor setup - not needed (compositor disabled during rendering anyway)
        # self.setup_compositor(context)  # DEPRECATED
        
        # Clear groups at session start
        self.clear_groups(context)
        
        # Write initial session.json
        write_session_json(context)
        
        # Setup the workspace layout
        if workspace:
            # ONLY configure layout if template didn't load properly
            # (Template should already have the perfect layout)
            if len(workspace.screens[0].areas) <= 2:
                # Template failed or has minimal areas - needs configuration
                print("[Style Engine] Template has minimal layout, configuring splits...")
                self.setup_workspace_layout(workspace, ai_camera)
            else:
                # Template loaded successfully with full layout
                print("[Style Engine] ✓ Using template layout as-is (no splitting needed)")
                
                # Create/get the prompt text block with template
                from . import utils
                _ai_model = getattr(context.scene.style_engine_props, 'ai_model', 'SDXL') if hasattr(context, 'scene') and context.scene else 'SDXL'
                prompt_text = utils.get_or_create_prompt_text(model=_ai_model)

                # Configure all text editors in the workspace
                for area in workspace.screens[0].areas:
                    if area.type == 'TEXT_EDITOR':
                        # Set the text to STYLEENGINE_Prompt
                        for space in area.spaces:
                            if space.type == 'TEXT_EDITOR':
                                space.text = prompt_text
                                space.show_line_numbers = False  # No line numbers
                                space.show_syntax_highlight = True  # Syntax highlight ON
                                space.show_word_wrap = True  # Word wrap ON
                                space.show_line_highlight = False  # No line highlight
                                space.show_region_header = True  # Keep header
                                print(f"[Style Engine] ✓ Configured text editor: STYLEENGINE_Prompt (no line numbers, syntax ON, word wrap ON)")
                                break
            
            # Switch to the workspace
            context.window.workspace = workspace
            
            # Initialize seed with a random value
            import random
            context.scene.style_engine_props.seed_value = random.randint(0, 2147483647)
            
            # For HeavyPoly mode: Switch main 3D viewport to Edit mode (delayed, after layout setup)
            from . import utils
            if utils.is_heavypoly_compatible():
                bpy.app.timers.register(_switch_to_edit_mode_standalone, first_interval=0.5)  # After layout setup
            
            self.report({'INFO'}, "AI Vision workspace created successfully!")
        else:
            self.report({'WARNING'}, "Failed to create AI workspace.")
        
        return {'FINISHED'}
    
    def ensure_temp_directory(self, context):
        """Create the temp directory for working files (canny, depth, current_ai.png)."""
        # Get temp directory using the new helper function
        temp_path = get_temp_directory(context)
        temp_path.mkdir(parents=True, exist_ok=True)
        
        print(f"[Style Engine] Temp directory: {temp_path}")
        
        # Create a placeholder image if it doesn't exist
        placeholder_path = temp_path / "current_ai.png"
        if not placeholder_path.exists():
            self.create_placeholder_image(str(placeholder_path))
        
        return temp_path
    
    def create_placeholder_image(self, path):
        """Create a placeholder image for testing."""
        # Get resolution from user's settings
        props = bpy.context.scene.style_engine_props
        res_str = props.ai_resolution  # e.g., "1024x1024"
        width, height = map(int, res_str.split('x'))
        
        # Create a simple colored image in Blender
        img = bpy.data.images.new("ai_placeholder", width=width, height=height)
        
        # Fill with a gradient or pattern (optional visual feedback)
        pixels = [0.1, 0.1, 0.2, 1.0] * (width * height)  # Dark blue
        img.pixels = pixels
        
        # Save it
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        
        print(f"[Style Engine] Created placeholder image: {path} ({width}x{height})")
    
    def create_ai_camera(self, context):
        """Create or get the AI camera object."""
        # Check if ai_camera already exists
        if "ai_camera" in bpy.data.objects:
            ai_camera = bpy.data.objects["ai_camera"]
            print("[Style Engine] Using existing ai_camera")
        else:
            # Create new camera
            cam_data = bpy.data.cameras.new("ai_camera")
            ai_camera = bpy.data.objects.new("ai_camera", cam_data)
            context.scene.collection.objects.link(ai_camera)
            print("[Style Engine] Created new ai_camera")
        
        return ai_camera
    
    def align_camera_to_view(self, context, camera):
        """Align the camera to the current 3D view (like Ctrl+Alt+0)."""
        # Find the 3D viewport
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # Get the current view matrix
                        view_matrix = space.region_3d.view_matrix.inverted()
                        
                        # Set camera location and rotation
                        camera.matrix_world = view_matrix
                        
                        # Set as active camera
                        context.scene.camera = camera
                        
                        print(f"[Style Engine] Camera aligned to view at {camera.location}")
                        return
        
        # Fallback: position at origin looking down -Y
        camera.location = (0, -10, 5)
        camera.rotation_euler = (1.1, 0, 0)
        context.scene.camera = camera
    
    def setup_camera_background(self, context, camera, skip_resolution_override=False):
        """Setup the background image for the camera."""
        cam_data = camera.data

        # Set passepartout to fully opaque (1.0)
        cam_data.passepartout_alpha = 1.0

        # Clear existing background images
        cam_data.show_background_images = True

        # Get or create background image
        if len(cam_data.background_images) > 0:
            bg_img = cam_data.background_images[0]
        else:
            bg_img = cam_data.background_images.new()

        # Get temp directory and image path
        temp_dir = get_temp_directory(context)
        img_path = temp_dir / "current_ai.png"

        # Placeholder resolution: use scene render res when synced from a scene camera,
        # otherwise use the ai_resolution dropdown
        props = context.scene.style_engine_props
        if skip_resolution_override:
            width = context.scene.render.resolution_x
            height = context.scene.render.resolution_y
        else:
            res_str = props.ai_resolution
            width, height = map(int, res_str.split('x'))

        # Remove old image if exists
        if "current_ai.png" in bpy.data.images:
            bpy.data.images.remove(bpy.data.images["current_ai.png"])

        # Create fresh black placeholder
        img = bpy.data.images.new("current_ai.png", width=width, height=height)

        # Fill with black (0, 0, 0, 1)
        pixels = [0.0, 0.0, 0.0, 1.0] * (width * height)
        img.pixels = pixels

        # Save to disk
        img.filepath_raw = str(img_path)
        img.file_format = 'PNG'
        img.save()

        print(f"[Style Engine] 🖤 Created fresh black placeholder: {width}x{height}")

        # Setup background image properties
        bg_img.image = img

        # Get opacity from properties (default to 0.7 for better visibility)
        props = bpy.context.scene.style_engine_props
        bg_img.alpha = props.background_opacity if hasattr(props, 'background_opacity') else 0.7

        bg_img.display_depth = 'FRONT'  # Display in front (default - can be changed via UI)
        bg_img.frame_method = 'STRETCH'

        _is_gemini = getattr(props, 'ai_model', 'SDXL') == 'GEMINI'
        if not skip_resolution_override and not _is_gemini:
            res_str = props.ai_resolution
            render_width, render_height = map(int, res_str.split('x'))
            context.scene.render.resolution_x = render_width
            context.scene.render.resolution_y = render_height
            print(f"[Style Engine] Background image set: {img_path}")
            print(f"[Style Engine] Render resolution set to: {render_width}x{render_height} (from ai_resolution setting)")
        else:
            _reason = "Gemini mode" if _is_gemini else "Gemini sync from scene camera"
            print(f"[Style Engine] Background image set: {img_path}")
            print(f"[Style Engine] Render resolution preserved: {width}x{height} ({_reason})")
    
    # NOTE: HeavyPoly hijacking disabled - now using standard Layout workspace
    # Code kept latent for future reference
    # 
    # def hijack_heavypoly_workspace(self, context, camera):
    #     """
    #     HEAVYPOLY HIJACKING MODE:
    #     Duplicate HeavyPoly's 'Modelling' workspace and reconfigure its existing windows.
    #     This preserves their perfect layout while injecting Style Engine functionality.
    #     
    #     Only runs when enable_heavypoly_compatibility is ON.
    #     
    #     Args:
    #         context: Blender context
    #         camera: AI camera object
    #         
    #     Returns:
    #         bpy.types.Workspace: The hijacked AI workspace, or None if failed
    #     """
    #     from . import utils
    #     
    #     # Double-check compatibility mode is enabled
    #     if not utils.is_heavypoly_compatible():
    #         print("[Style Engine] HeavyPoly compatibility not enabled")
    #         return None
    #     
    #     # Find HeavyPoly's Modeling workspace (check both US and UK spellings)
    #     modelling_ws = None
    #     for ws in bpy.data.workspaces:
    #         if ws.name in ["Modeling", "Modelling"]:
    #             modelling_ws = ws
    #             break
    #     
    #     if not modelling_ws:
    #         print("[Style Engine] WARNING: HeavyPoly 'Modeling' workspace not found")
    #         print("[Style Engine] Falling back to standard workspace creation")
    #         return None
    #     
    #     print(f"[Style Engine] 🎯 HEAVYPOLY MODE: Found '{modelling_ws.name}' workspace")
    #     
    #     # Check if AI workspace already exists
    #     ai_workspace = bpy.data.workspaces.get("AI")
    #     if ai_workspace:
    #         print("[Style Engine] AI workspace already exists, will reconfigure...")
    #         context.window.workspace = ai_workspace
    #         
    #         # Reconfigure the areas
    #         def delayed_reconfig():
    #             _hijack_heavypoly_areas_standalone(context.screen, camera)
    #             return None
    #         bpy.app.timers.register(delayed_reconfig, first_interval=0.1)
    #         
    #         return ai_workspace
    #     
    #     # Switch to Modelling workspace (required for duplication)
    #     context.window.workspace = modelling_ws
    #     
    #     # Duplicate it
    #     workspaces_before = set(bpy.data.workspaces)
    #     bpy.ops.workspace.duplicate()
    #     
    #     # Find the new workspace
    #     workspaces_after = set(bpy.data.workspaces)
    #     new_workspaces = workspaces_after - workspaces_before
    #     
    #     if new_workspaces:
    #         ai_workspace = list(new_workspaces)[0]
    #         ai_workspace.name = "AI"
    #         print(f"[Style Engine] ✅ Duplicated Modelling → AI workspace")
    #     else:
    #         print("[Style Engine] ERROR: Failed to duplicate workspace")
    #         return None
    #     
    #     # Switch to the new AI workspace
    #     context.window.workspace = ai_workspace
    #     
    #     # Schedule the hijacking of areas
    #     def delayed_hijack():
    #         _hijack_heavypoly_areas_standalone(context.screen, camera)
    #         return None  # Don't repeat
    #     
    #     bpy.app.timers.register(delayed_hijack, first_interval=0.1)
    #     
    #     return ai_workspace
    
    def create_ai_workspace(self, context):
        """
        Create AI workspace by loading from template.blend.
        
        Uses pre-designed workspace template for consistent, clean layout.
        For HeavyPoly mode, the only difference is switching to Edit mode in the 3D viewport.
        """
        # Check if workspace already exists - if so, DELETE it and start fresh
        if "AI" in bpy.data.workspaces:
            print("[Style Engine] AI workspace already exists - deleting and recreating...")
            old_ai = bpy.data.workspaces["AI"]
            # Switch away from it first
            for ws in bpy.data.workspaces:
                if ws.name != "AI":
                    context.window.workspace = ws
                    break
            # Now delete it
            bpy.data.workspaces.remove(old_ai)
            print("[Style Engine] ✓ Deleted old AI workspace")
        
        # Load workspace from template.blend
        import os
        addon_dir = os.path.dirname(__file__)
        template_path = os.path.join(addon_dir, "template.blend")
        
        print(f"[Style Engine] Loading workspace from template: {template_path}")
        
        if not os.path.exists(template_path):
            print(f"[Style Engine] ⚠ Template file not found: {template_path}")
            print(f"[Style Engine] ⚠ Falling back to duplicating current workspace")
            # Fallback: just duplicate current workspace
            bpy.ops.workspace.duplicate()
            ai_workspace = context.workspace
            ai_workspace.name = "AI"
            return ai_workspace
        
        try:
            # Load the workspace from template
            with bpy.data.libraries.load(template_path, link=False) as (data_from, data_to):
                # Find the template workspace
                template_name = "Style_Engine_Template"
                if template_name in data_from.workspaces:
                    data_to.workspaces = [template_name]
                    print(f"[Style Engine] ✓ Found '{template_name}' in template file")
                else:
                    print(f"[Style Engine] ⚠ Available workspaces in template: {data_from.workspaces}")
                    # Load first workspace if template name not found
                    if data_from.workspaces:
                        data_to.workspaces = [data_from.workspaces[0]]
                        print(f"[Style Engine] ⚠ Using first available: '{data_from.workspaces[0]}'")
            
            # Check if workspace was loaded
            if data_to.workspaces:
                ai_workspace = data_to.workspaces[0]
                ai_workspace.name = "AI"
                context.window.workspace = ai_workspace
                
                print(f"[Style Engine] ✓ Loaded workspace template successfully")
                print(f"[Style Engine] ✓ Workspace has {len(ai_workspace.screens[0].areas)} areas:")
                for i, area in enumerate(ai_workspace.screens[0].areas):
                    print(f"[Style Engine]     Area {i}: {area.type} at ({area.x}, {area.y})")
                
                return ai_workspace
            else:
                raise Exception("No workspace was loaded from template")
                
        except Exception as e:
            print(f"[Style Engine] ❌ Failed to load template: {e}")
            import traceback
            traceback.print_exc()
            print(f"[Style Engine] ⚠ Falling back to duplicating current workspace")
            # Fallback: just duplicate current workspace
            bpy.ops.workspace.duplicate()
            ai_workspace = context.workspace
            ai_workspace.name = "AI"
            return ai_workspace
    
    def _create_standard_workspace(self, context):
        """
        Internal helper: Create standard workspace (used as fallback if HeavyPoly hijack fails).
        This is the original workspace creation logic without HeavyPoly checks.
        """
        # Check if workspace already exists
        if "AI" in bpy.data.workspaces:
            print("[Style Engine] AI workspace already exists, using it")
            return bpy.data.workspaces["AI"]
        
        # Store current workspace to avoid messing it up
        original_workspace = context.workspace
        original_name = original_workspace.name
        
        # Switch to the default "Layout" workspace if it exists (guaranteed clean)
        layout_workspace = bpy.data.workspaces.get("Layout")
        
        if layout_workspace:
            print("[Style Engine] Using clean 'Layout' workspace as base")
            context.window.workspace = layout_workspace
            base_workspace = layout_workspace
        else:
            # If no Layout workspace exists, use General (another default)
            general_workspace = bpy.data.workspaces.get("General")
            if general_workspace:
                print("[Style Engine] Using 'General' workspace as base")
                context.window.workspace = general_workspace
                base_workspace = general_workspace
            else:
                print("[Style Engine] Using current workspace as base")
                base_workspace = original_workspace
        
        # Store the base workspace name to restore it later
        base_name = base_workspace.name
        
        # Count workspaces before duplication
        workspaces_before = set(bpy.data.workspaces)
        
        # Duplicate to create AI workspace
        bpy.ops.workspace.duplicate()
        
        # Find the NEW workspace (the one that wasn't there before)
        workspaces_after = set(bpy.data.workspaces)
        new_workspaces = workspaces_after - workspaces_before
        
        if new_workspaces:
            new_workspace = list(new_workspaces)[0]
            # Rename it to "AI" immediately
            new_workspace.name = "AI"
            
            # Make sure the base workspace keeps its original name
            if base_workspace.name != base_name:
                base_workspace.name = base_name
            
            print(f"[Style Engine] Created fresh AI workspace from clean {base_name} layout")
            return new_workspace
        else:
            # Fallback: just rename current workspace
            context.workspace.name = "AI"
            print(f"[Style Engine] Created AI workspace (fallback)")
            return context.workspace
    
    def setup_workspace_layout(self, workspace, camera):
        """Setup the split layout for the AI workspace."""
        print("[Style Engine] Configuring workspace layout...")
        
        # The actual split needs to happen after switching to the workspace
        # Use a standalone function to avoid operator lifetime issues
        def delayed_setup():
            _delayed_split_setup_standalone(camera)
            return None  # Don't repeat timer
        
        bpy.app.timers.register(delayed_setup, first_interval=0.1)
        
        # Start the optimized auto-refresh timer for the background image
        self.start_image_refresh_timer()
    
    def setup_render_engine(self, context):
        """
        Configure scene render engine to Workbench for fast, optimized rendering.
        Sets this as the SCENE DEFAULT so all renders use these settings.
        Enhanced with cavity, specular, and form-describing capabilities.
        """
        scene = context.scene
        prefs = context.preferences.addons['styleengine'].preferences
        
        # Set Workbench as default render engine
        scene.render.engine = 'BLENDER_WORKBENCH'
        
        # === WORKBENCH SHADING SETTINGS FOR FORM DESCRIPTION ===
        shading = scene.display.shading
        
        # Lighting: Studio lighting for consistent form description
        shading.light = 'STUDIO'  # Options: 'STUDIO', 'MATCAP', 'FLAT'
        
        # Color: Material colors for realistic appearance
        shading.color_type = 'MATERIAL'  # Options: 'MATERIAL', 'OBJECT', 'VERTEX', 'TEXTURE', 'RANDOM'
        
        # Enable Specular Lighting for better form description
        shading.show_specular_highlight = True
        
        # Enable Cavity for enhanced depth perception (ridge + valley)
        shading.show_cavity = True
        if hasattr(shading, 'cavity_type'):
            shading.cavity_type = 'BOTH'  # Options: 'WORLD', 'SCREEN', 'BOTH'
        
        # Cavity strength settings
        if hasattr(shading, 'cavity_ridge_factor'):
            shading.cavity_ridge_factor = 1.0  # Ridge detection (raised edges)
        if hasattr(shading, 'cavity_valley_factor'):
            shading.cavity_valley_factor = 1.0  # Valley detection (recessed areas)
        
        # Shadow for better depth
        shading.show_shadows = True
        if hasattr(shading, 'shadow_intensity'):
            shading.shadow_intensity = 0.5  # Moderate shadows
        
        print(f"[Style Engine] 🎨 Workbench shading configured:")
        print(f"  - Lighting: {shading.light}")
        print(f"  - Color: {shading.color_type}")
        print(f"  - Specular: {shading.show_specular_highlight}")
        print(f"  - Cavity: {shading.show_cavity} (ridge={shading.cavity_ridge_factor if hasattr(shading, 'cavity_ridge_factor') else 'N/A'}, valley={shading.cavity_valley_factor if hasattr(shading, 'cavity_valley_factor') else 'N/A'})")
        print(f"  - Shadows: {shading.show_shadows}")
        
        # Disable anti-aliasing for Workbench (faster rendering)
        # In Blender 4.x, Workbench AA is controlled via display settings
        if hasattr(scene.display, 'render_aa'):
            scene.display.render_aa = 'OFF'  # Options: 'OFF', 'FXAA', '5', '8', '11', '16', '32'
        
        # Disable viewport denoising (not used in Workbench anyway)
        if hasattr(scene.display, 'viewport_aa'):
            scene.display.viewport_aa = 'OFF'
        
        # Ensure render resolution is set correctly.
        # In Gemini mode the resolution is owned by the scene camera sync and the
        # Gemini aspect-ratio detection — never override it from the ai_resolution dropdown.
        props = context.scene.style_engine_props
        if getattr(props, 'ai_model', 'SDXL') != 'GEMINI':
            res_str = props.ai_resolution
            width, height = map(int, res_str.split('x'))
            scene.render.resolution_x = width
            scene.render.resolution_y = height
        scene.render.resolution_percentage = 100
        
        # Set output format - JPEG for smaller file size (faster upload)
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.color_mode = 'RGB'  # JPEG doesn't support alpha
        scene.render.image_settings.quality = 85  # JPEG quality (0-100, 85 is high quality + good compression)
        
        if prefs.debug_mode:
            print("[Style Engine] ✓ Render engine: BLENDER_WORKBENCH (scene default)")
            print(f"[Style Engine] ✓ Anti-aliasing: OFF (fast rendering)")
            print(f"[Style Engine] ✓ Resolution: {width}x{height} @ 100%")
            print(f"[Style Engine] ✓ Output format: JPEG @ 85% quality (optimized for upload)")
        else:
            print(f"[Style Engine] Scene configured: Workbench render @ {width}x{height}")
    
    def clear_groups(self, context):
        """Clear all groups at session start."""
        props = context.scene.style_engine_props
        props.object_groups.clear()
        props.active_group_index = 0
        props.group_counter = 1
        print("[Style Engine] Groups cleared for new session")
    
    def start_image_refresh_timer(self):
        """
        Image refresh is now ON-DEMAND only (no timer).
        The image refreshes automatically when generation completes (on_generation_complete).
        This eliminates wasteful file system checks and is more efficient.
        """
        # No timer needed - refresh happens in on_generation_complete callback
        print("[Style Engine] Image refresh: on-demand (no timer - refreshes when generation completes)")
        
        # DO NOT start auto-render timer - it's wasteful!
        # Rendering happens cyclically with generation:
        # - Initial render on setup (below)
        # - Render before each AI generation
        # - Render after receiving result (for next iteration)
        # No need for continuous 5-second renders!
    

def _switch_to_edit_mode_standalone():
    """
    STANDALONE function to switch main 3D viewport to Edit mode (for HeavyPoly compatibility).
    
    Must be standalone because it's called from a timer after the operator is destroyed.
    
    This is the only difference between HeavyPoly and standard mode:
    - Standard: Object mode (default)
    - HeavyPoly: Edit mode (for modeling workflow)
    """
    context = bpy.context
    print("[Style Engine] HeavyPoly mode: Switching main 3D viewport to Edit mode...")
        
    # Find the main 3D viewport (left side, not the camera viewport)
    # The camera viewport is typically the rightmost one
    view3d_areas = [a for a in context.screen.areas if a.type == 'VIEW_3D']
    
    if not view3d_areas:
        print("[Style Engine] ⚠ No 3D viewport found, cannot switch to Edit mode")
        return None
    
    # Use the first (leftmost) 3D viewport as the main one
    main_area = view3d_areas[0]
    
    # Find a mesh object in the scene
    mesh_object = None
    
    # First, check if active object is a mesh
    if context.active_object and context.active_object.type == 'MESH':
        mesh_object = context.active_object
    else:
        # Find the first mesh object in the scene
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                mesh_object = obj
                break
    
    if mesh_object is None:
        print("[Style Engine] ⚠ No mesh objects in scene, skipping Edit mode")
        print("[Style Engine] ℹ️  Add a mesh object (Shift+A → Mesh) to use Edit mode")
        return None
    
    # Switch to Edit mode
    try:
        # Make sure we're in OBJECT mode first
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Select and activate the mesh object
        bpy.ops.object.select_all(action='DESELECT')
        mesh_object.select_set(True)
        context.view_layer.objects.active = mesh_object
        
        # Temporarily override context to use the main area
        override = context.copy()
        override['area'] = main_area
        override['region'] = main_area.regions[0]
        
        with context.temp_override(**override):
            # Switch to Edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            print(f"[Style Engine] ✓ Switched to Edit mode in main 3D viewport (object: {mesh_object.name})")
    except Exception as e:
        print(f"[Style Engine] ⚠ Failed to switch to Edit mode: {e}")
        import traceback
        traceback.print_exc()
    
    return None  # Don't repeat timer


# Note: The WM_OT_SetupWorkspace class is defined earlier in this file (line 659)
# All methods (clear_groups, setup_render_engine, etc.) are already defined inside that class
# The orphaned duplicate code below has been removed


class WM_OT_PopulateAssets(bpy.types.Operator):
    """Create essential Style Engine assets (ai_camera, prompt text) without changing workspace."""
    bl_idname = "style_engine.populate_assets"
    bl_label = "Populate Assets"
    bl_description = "Create ai_camera and STYLEENGINE_Prompt without switching workspace layout"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import utils
        
        # Reset temp directory lock (allows re-determination if .blend was saved)
        reset_temp_directory()
        
        # Create temp directory for AI images
        temp_path = get_temp_directory(context)
        temp_path.mkdir(parents=True, exist_ok=True)
        print(f"[Style Engine] Temp directory: {temp_path}")
        
        # Create placeholder image if needed
        placeholder_path = temp_path / "current_ai.png"
        if not placeholder_path.exists():
            self._create_placeholder_image(context, str(placeholder_path))
        
        # Create or get the AI camera
        ai_camera = self._ensure_ai_camera(context)

        # In Gemini mode, sync from scene camera if one exists; otherwise align to view
        _gemini_synced = False
        if getattr(context.scene.style_engine_props, 'ai_model', 'SDXL') == 'GEMINI':
            _gemini_synced = sync_ai_camera_from_scene(context)
        if not _gemini_synced:
            self._align_camera_to_view(context, ai_camera)

        # Setup camera background image (resolution override skipped in Gemini sync mode)
        self._setup_camera_background(context, ai_camera, skip_resolution_override=_gemini_synced)
        
        # Create/get the prompt text block
        _ai_model = getattr(context.scene.style_engine_props, 'ai_model', 'SDXL')
        prompt_text = utils.get_or_create_prompt_text(model=_ai_model)
        print(f"[Style Engine] ✓ Prompt text block ready: {prompt_text.name}")
        
        # Write session.json
        write_session_json(context)
        
        self.report({'INFO'}, "Assets populated: ai_camera + STYLEENGINE_Prompt")
        return {'FINISHED'}
    
    def _create_placeholder_image(self, context, path):
        """Create a placeholder image."""
        props = context.scene.style_engine_props
        res_str = props.ai_resolution
        width, height = map(int, res_str.split('x'))
        
        img = bpy.data.images.new("ai_placeholder", width=width, height=height)
        pixels = [0.0, 0.0, 0.0, 1.0] * (width * height)  # Black
        img.pixels = pixels
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        print(f"[Style Engine] 🖤 Created placeholder: {width}x{height}")
    
    def _ensure_ai_camera(self, context):
        """Create or get the AI camera."""
        if "ai_camera" in bpy.data.objects:
            ai_camera = bpy.data.objects["ai_camera"]
            print("[Style Engine] Using existing ai_camera")
        else:
            cam_data = bpy.data.cameras.new("ai_camera")
            ai_camera = bpy.data.objects.new("ai_camera", cam_data)
            context.scene.collection.objects.link(ai_camera)
            print("[Style Engine] ✓ Created new ai_camera")
        return ai_camera
    
    def _align_camera_to_view(self, context, camera):
        """Align camera to current 3D view."""
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        view_matrix = space.region_3d.view_matrix.inverted()
                        camera.matrix_world = view_matrix
                        context.scene.camera = camera
                        print(f"[Style Engine] ✓ Camera aligned to view at {camera.location}")
                        return
        print("[Style Engine] ⚠️ No 3D viewport found for camera alignment")
    
    def _setup_camera_background(self, context, camera, skip_resolution_override=False):
        """Setup the background image for the camera."""
        cam_data = camera.data
        cam_data.passepartout_alpha = 1.0
        cam_data.show_background_images = True

        if len(cam_data.background_images) > 0:
            bg_img = cam_data.background_images[0]
        else:
            bg_img = cam_data.background_images.new()

        temp_dir = get_temp_directory(context)
        img_path = temp_dir / "current_ai.png"

        # Load or get the image
        if "current_ai.png" in bpy.data.images:
            img = bpy.data.images["current_ai.png"]
        else:
            img = bpy.data.images.load(str(img_path))
            img.name = "current_ai.png"

        bg_img.image = img
        props = context.scene.style_engine_props
        bg_img.alpha = props.background_opacity if hasattr(props, 'background_opacity') else 0.7
        bg_img.display_depth = 'FRONT'
        bg_img.frame_method = 'STRETCH'

        print(f"[Style Engine] ✓ Camera background configured")


class WM_OT_SetCamera(bpy.types.Operator):
    """Copy camera transforms and properties from selected or active camera to ai_camera."""
    bl_idname = "style_engine.set_camera"
    bl_label = "Set Camera"
    bl_description = "Copy transforms and properties from selected/active camera to ai_camera (resolution unchanged)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find source camera (selected camera or scene active camera)
        source_camera = None
        
        # First, check if active object is a camera
        if context.active_object and context.active_object.type == 'CAMERA':
            source_camera = context.active_object
            print(f"[Style Engine] Using selected camera: {source_camera.name}")
        # Otherwise, use scene's active camera
        elif context.scene.camera and context.scene.camera.type == 'CAMERA':
            source_camera = context.scene.camera
            print(f"[Style Engine] Using scene active camera: {source_camera.name}")
        else:
            self.report({'ERROR'}, "No camera found. Select a camera or set an active camera.")
            return {'CANCELLED'}
        
        # Ensure ai_camera exists
        if "ai_camera" in bpy.data.objects:
            ai_camera = bpy.data.objects["ai_camera"]
            print(f"[Style Engine] Updating existing ai_camera")
        else:
            # Create new ai_camera
            cam_data = bpy.data.cameras.new("ai_camera")
            ai_camera = bpy.data.objects.new("ai_camera", cam_data)
            context.scene.collection.objects.link(ai_camera)
            print(f"[Style Engine] Created new ai_camera")
        
        # Copy object transforms (location, rotation, scale)
        ai_camera.location = source_camera.location.copy()
        ai_camera.rotation_euler = source_camera.rotation_euler.copy()
        ai_camera.rotation_quaternion = source_camera.rotation_quaternion.copy()
        ai_camera.rotation_axis_angle = source_camera.rotation_axis_angle[:]
        ai_camera.rotation_mode = source_camera.rotation_mode
        ai_camera.scale = source_camera.scale.copy()
        
        # Copy the full transformation matrix for accuracy
        ai_camera.matrix_world = source_camera.matrix_world.copy()
        
        # Get source and destination camera data
        src_cam = source_camera.data
        dst_cam = ai_camera.data
        
        # Copy camera type (PERSP, ORTHO, PANO)
        dst_cam.type = src_cam.type
        
        # Copy lens properties
        dst_cam.lens = src_cam.lens  # Focal length (mm)
        dst_cam.lens_unit = src_cam.lens_unit  # MILLIMETERS or FOV
        dst_cam.angle = src_cam.angle  # Field of view (radians)
        
        # Copy orthographic scale (for ORTHO cameras)
        dst_cam.ortho_scale = src_cam.ortho_scale
        
        # Copy shift (for architectural/tilt-shift)
        dst_cam.shift_x = src_cam.shift_x
        dst_cam.shift_y = src_cam.shift_y
        
        # Copy clip distances
        dst_cam.clip_start = src_cam.clip_start
        dst_cam.clip_end = src_cam.clip_end
        
        # Copy sensor properties
        dst_cam.sensor_fit = src_cam.sensor_fit
        dst_cam.sensor_width = src_cam.sensor_width
        dst_cam.sensor_height = src_cam.sensor_height
        
        # Copy depth of field settings
        dst_cam.dof.use_dof = src_cam.dof.use_dof
        dst_cam.dof.focus_distance = src_cam.dof.focus_distance
        dst_cam.dof.aperture_fstop = src_cam.dof.aperture_fstop
        dst_cam.dof.aperture_blades = src_cam.dof.aperture_blades
        dst_cam.dof.aperture_rotation = src_cam.dof.aperture_rotation
        dst_cam.dof.aperture_ratio = src_cam.dof.aperture_ratio
        # Note: focus_object is not copied (could reference deleted objects)
        
        # Copy passepartout settings (but keep our alpha)
        dst_cam.show_passepartout = src_cam.show_passepartout
        # Keep passepartout_alpha at 1.0 for Style Engine
        dst_cam.passepartout_alpha = 1.0
        
        # Set ai_camera as scene camera
        context.scene.camera = ai_camera
        
        self.report({'INFO'}, f"ai_camera set from: {source_camera.name}")
        print(f"[Style Engine] ✓ Copied transforms and properties from {source_camera.name}")
        print(f"[Style Engine]   Type: {dst_cam.type}, Lens: {dst_cam.lens}mm, Clip: {dst_cam.clip_start}-{dst_cam.clip_end}")
        
        return {'FINISHED'}


def sync_ai_camera_from_scene(context):
    """
    When Gemini mode is active and a non-ai_camera camera exists in the scene,
    copy its transform and lens properties to ai_camera, and preserve the scene's
    current render resolution instead of overriding it with ai_resolution.

    Returns True if a source camera was found and synced, False otherwise.
    """
    import bpy as _bpy

    # Find a source camera (active scene camera that is NOT ai_camera)
    source_camera = None
    if context.scene.camera and context.scene.camera.name != 'ai_camera' and context.scene.camera.type == 'CAMERA':
        source_camera = context.scene.camera
    else:
        for obj in context.scene.objects:
            if obj.type == 'CAMERA' and obj.name != 'ai_camera':
                source_camera = obj
                break

    if source_camera is None:
        return False

    if 'ai_camera' not in _bpy.data.objects:
        return False

    ai_camera = _bpy.data.objects['ai_camera']

    # Copy full world transform
    ai_camera.matrix_world = source_camera.matrix_world.copy()

    # Copy lens / camera data properties
    src = source_camera.data
    dst = ai_camera.data
    dst.type = src.type
    dst.lens = src.lens
    dst.lens_unit = src.lens_unit
    dst.angle = src.angle
    dst.ortho_scale = src.ortho_scale
    dst.shift_x = src.shift_x
    dst.shift_y = src.shift_y
    dst.clip_start = src.clip_start
    dst.clip_end = src.clip_end
    dst.sensor_fit = src.sensor_fit
    dst.sensor_width = src.sensor_width
    dst.sensor_height = src.sensor_height

    # Set ai_camera as scene camera so viewport/render uses it
    context.scene.camera = ai_camera

    print(f"[Gemini] Synced ai_camera from '{source_camera.name}': "
          f"lens={dst.lens:.1f}mm, res={context.scene.render.resolution_x}x{context.scene.render.resolution_y}")
    return True


class WM_OT_StopAutoRefresh(bpy.types.Operator):
    """Stop the auto-refresh timer for AI images."""
    bl_idname = "style_engine.stop_auto_refresh"
    bl_label = "Stop Auto-Refresh"
    bl_description = "Stop automatically reloading AI images"
    
    def execute(self, context):
        if bpy.app.timers.is_registered(refresh_ai_image):
            bpy.app.timers.unregister(refresh_ai_image)
            self.report({'INFO'}, "Auto-refresh stopped")
            print("[Style Engine] Auto-refresh timer stopped")
        else:
            self.report({'INFO'}, "Auto-refresh is not running")
        return {'FINISHED'}


class WM_OT_StartAutoRefresh(bpy.types.Operator):
    """Start the auto-refresh timer for AI images."""
    bl_idname = "style_engine.start_auto_refresh"
    bl_label = "Start Auto-Refresh"
    bl_description = "Start automatically reloading AI images when they change"
    
    def execute(self, context):
        if not bpy.app.timers.is_registered(refresh_ai_image):
            bpy.app.timers.register(refresh_ai_image, first_interval=1.0, persistent=True)
            self.report({'INFO'}, "Auto-refresh started")
            print("[Style Engine] Auto-refresh timer started")
        else:
            self.report({'INFO'}, "Auto-refresh is already running")
        return {'FINISHED'}


# ----------------------------------------------------------------
# RENDER PASSES
# ----------------------------------------------------------------

def render_from_camera_safe(scene, camera, prefs):
    """
    Render from specific camera without permanently changing scene.camera.
    This is SURGICAL - only affects the render operation itself.
    """
    if prefs.debug_mode:
        print(f"[Style Engine] Rendering from camera: {camera.name}")
        print(f"[Style Engine] Current scene camera: {scene.camera.name if scene.camera else 'None'}")
    
    # Save original camera
    original_camera = scene.camera
    
    try:
        # Temporarily set camera ONLY for this render
        scene.camera = camera
        
        if prefs.debug_mode:
            print(f"[Style Engine] → Switched to: {camera.name} (temporary)")
        
        # Render
        bpy.ops.render.render(write_still=True, use_viewport=False)
        
    finally:
        # IMMEDIATELY restore original camera (even if render failed)
        scene.camera = original_camera
        
        if prefs.debug_mode:
            print(f"[Style Engine] → Restored to: {original_camera.name if original_camera else 'None'}")


def render_passes(context):
    """
    Render combined pass from ai_camera using WORKBENCH (fast) or EEVEE (detailed).
    Quality is controlled by render_quality property:
    - FAST: Workbench (10-15x faster, good for quick iterations)
    - DETAILED: EEVEE (high quality, better for img2img with low texture_influence)
    Depth is generated by AI (DepthAnything).
    Uses SURGICAL approach - doesn't disturb user's active camera.
    """
    props = context.scene.style_engine_props
    render_quality = props.render_quality if hasattr(props, 'render_quality') else 'FAST'
    
    if render_quality == 'DETAILED':
        print("[Style Engine] Rendering combined pass (EEVEE Next - detailed!)...")
    else:
        print("[Style Engine] Rendering combined pass (Workbench - fast!)...")
    
    prefs = context.preferences.addons['styleengine'].preferences
    camera_name = prefs.camera_name_override
    
    # Find the ai_camera
    if camera_name not in bpy.data.objects:
        print(f"[Style Engine] ERROR: {camera_name} not found! Run 'Setup Workspace' first.")
        raise RuntimeError(f"{camera_name} not found. Please run 'Setup Workspace' first.")
    
    ai_camera = bpy.data.objects[camera_name]
    scene = context.scene
    
    # Store original settings (but NOT camera - we'll handle that surgically)
    original_engine = scene.render.engine
    original_file_format = scene.render.image_settings.file_format
    original_use_compositing = scene.render.use_compositing
    
    try:
        # Configure render settings based on quality
        if render_quality == 'DETAILED':
            # EEVEE for high quality (version-compatible)
            scene.render.engine = get_eevee_engine_name()
            # EEVEE settings for quality (using only properties that exist)
            if hasattr(scene.eevee, 'taa_render_samples'):
                scene.eevee.taa_render_samples = 64  # Good quality, reasonable speed
            if hasattr(scene.eevee, 'use_gtao'):
                scene.eevee.use_gtao = True  # Ambient occlusion
            if hasattr(scene.eevee, 'use_ssr'):
                scene.eevee.use_ssr = True  # Screen space reflections
            if hasattr(scene.eevee, 'use_ssr_refraction'):
                scene.eevee.use_ssr_refraction = True  # Refractions
            # Note: use_bloom removed in EEVEE Next - bloom is now always available but controlled differently
            engine_version = "EEVEE" if bpy.app.version >= (5, 0, 1) else "EEVEE Next"
            print(f"[Style Engine] {engine_version} configured: 64 samples, AO, SSR")
        else:
            # WORKBENCH for speed
            scene.render.engine = 'BLENDER_WORKBENCH'
            # === WORKBENCH SHADING FOR FORM DESCRIPTION ===
            shading = scene.display.shading
            shading.light = 'STUDIO'  # Studio lighting
            shading.color_type = 'MATERIAL'  # Material colors
            shading.show_specular_highlight = True  # Specular for form
            shading.show_cavity = True  # Cavity for depth
            if hasattr(shading, 'cavity_type'):
                shading.cavity_type = 'BOTH'  # Ridge + valley
            if hasattr(shading, 'cavity_ridge_factor'):
                shading.cavity_ridge_factor = 1.0  # Full ridge
            if hasattr(shading, 'cavity_valley_factor'):
                shading.cavity_valley_factor = 1.0  # Full valley
            shading.show_shadows = True  # Shadows for depth
            if hasattr(shading, 'shadow_intensity'):
                shading.shadow_intensity = 0.5  # Moderate shadows
        
        # Common settings for both engines
        scene.render.image_settings.file_format = 'JPEG'  # JPEG for smaller file size (faster upload)
        scene.render.image_settings.color_mode = 'RGB'  # JPEG doesn't support alpha
        scene.render.image_settings.quality = 85  # High quality, good compression
        scene.render.use_compositing = False  # Disable compositor for speed!
        # Resolution percentage kept at 100% to match SDXL native resolution exactly
        
        # Set output filepath BEFORE rendering
        temp_dir = get_temp_directory(context)
        
        # Since compositor is disabled, Blender saves to "combined.jpg" (no frame number)
        # JPEG format for smaller file size = faster upload to RunComfy
        combined_path = temp_dir / "combined.jpg"
        
        # Delete old render if exists (force fresh render)
        if combined_path.exists():
            import os
            try:
                os.remove(str(combined_path))
                print(f"[Style Engine] Deleted old combined pass to force fresh render")
            except Exception as e:
                print(f"[Style Engine] Warning: Could not delete old file: {e}")
        
        scene.render.filepath = str(temp_dir / "combined")
        
        # Diagnostic: Check scene objects visibility
        visible_objects = [obj for obj in scene.objects if not obj.hide_render and obj.type == 'MESH']
        print(f"[Style Engine] 🔍 Scene has {len(visible_objects)} visible mesh objects for rendering")
        
        if len(visible_objects) == 0:
            print(f"[Style Engine] ⚠️ WARNING: No visible mesh objects! Render will be empty!")
            print(f"[Style Engine] Total objects: {len([o for o in scene.objects if o.type == 'MESH'])}")
            print(f"[Style Engine] Check: Are objects hidden from render? (hide_render property)")
        
        if prefs.debug_mode:
            print(f"[Style Engine] Original camera: {scene.camera.name if scene.camera else 'None'}")
            print(f"[Style Engine] Compositor disabled for speed")
            print(f"[Style Engine] Render path: {scene.render.filepath}")
            print(f"[Style Engine] Expected output: {combined_path}")
        
        # SURGICAL: Render from ai_camera without permanently changing scene.camera
        if render_quality == 'DETAILED':
            engine_name = "EEVEE" if bpy.app.version >= (5, 0, 1) else "EEVEE Next"
        else:
            engine_name = "Workbench"
        print(f"[Style Engine] 🎨 Rendering from {camera_name} ({engine_name})...")
        
        # Store timestamp before render
        import time
        render_start = time.time()
        
        render_from_camera_safe(scene, ai_camera, prefs)
        
        render_duration = time.time() - render_start
        print(f"[Style Engine] Render took {render_duration:.2f}s")
        
        # Verify combined output exists AND was just created
        if not combined_path.exists():
            print(f"[Style Engine] ❌ ERROR: Combined pass not found at {combined_path}")
            print(f"[Style Engine] Render may have failed silently!")
            # List what files ARE in the temp directory
            import os
            temp_files = list(temp_dir.glob("*"))
            print(f"[Style Engine] Files in temp dir: {[f.name for f in temp_files]}")
        else:
            # Check file modification time to ensure it's fresh
            file_age = time.time() - combined_path.stat().st_mtime
            if file_age > 10:  # If file is older than 10 seconds
                print(f"[Style Engine] ⚠️ WARNING: combined.png is {file_age:.1f}s old - may be cached!")
            else:
                print(f"[Style Engine] ✓ Combined pass: {combined_path} (fresh, {file_age:.1f}s old, {combined_path.stat().st_size} bytes)")
        
        # NOTE: Depth pass is NO LONGER RENDERED
        # The workflow uses DepthAnything AI to generate depth from the combined image
        # This is 10-15x faster and produces better depth maps anyway!
        
        print(f"[Style Engine] ✓ Render complete! (depth generated by AI)")
        
    finally:
        # Restore original settings (camera was already restored in render_from_camera_safe)
        scene.render.engine = original_engine
        scene.render.image_settings.file_format = original_file_format
        scene.render.use_compositing = original_use_compositing


# ----------------------------------------------------------------
# CLOUD GENERATION (RunComfy)
# ----------------------------------------------------------------

def generate_ai_image_cloud(context, refine_mode=False):
    """
    Cloud generation using RunComfy API.
    This function replaces the local FastAPI/ComfyUI workflow.

    When refine_mode=True the scene is NOT re-rendered; current_ai.png is used
    directly as the conditioning image instead of combined.jpg.  This lets the
    user iteratively refine an already-generated (or uploaded) image without
    having the 3-D viewport re-composited on top of it.
    """
    from . import runcomfy_polling
    from . import runcomfy_deployment
    from . import runcomfy_client
    from . import utils
    
    # 0. AUTO-SYNC: Load prompt from text editor (cyclical/automatic)
    prompt_from_editor = utils.get_prompt_from_text_editor()
    props = context.scene.style_engine_props
    
    if prompt_from_editor:
        # Always process through prompt builder (auto-detects tags, falls back to raw text)
        positive_prompt, negative_prompt = utils.process_prompt_builder(prompt_from_editor)
        
        if positive_prompt:
            props.global_prompt = positive_prompt
            props.negative_prompt = negative_prompt  # Store negative prompt!
            
            # Check if tags were used (has negative prompt or comma in positive)
            if negative_prompt or ', ' in positive_prompt:
                print(f"[Style Engine] ✓ Prompt Builder: Built prompt from tags ({len(positive_prompt)} chars)")
                print(f"[Style Engine]   → Positive: {positive_prompt[:100]}...")
                if negative_prompt:
                    print(f"[Style Engine]   → Negative: {negative_prompt[:50]}...")
                else:
                    print(f"[Style Engine]   → Negative: (none - will use default)")
            else:
                # Raw text was used (no tags detected)
                print(f"[Style Engine] ✓ Using raw text as prompt ({len(positive_prompt)} chars)")
                print(f"[Style Engine]   → Prompt: {positive_prompt[:100]}...")
    
    # 1. Check if generation already in progress
    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[Style Engine] Generation already in progress, skipping")
        return
    
    # 2. Render passes (same as local) — skipped in refine mode
    if refine_mode:
        print("[Style Engine] Refine mode: skipping render, using current_ai.png as input")
    else:
        render_passes(context)
    
    # 3. Read session data (create if doesn't exist)
    temp_dir = get_temp_directory(context)
    session_json_path = temp_dir / "session.json"
    
    # Ensure session.json exists
    if not session_json_path.exists():
        print("[Style Engine] session.json not found, creating it...")
        write_session_json(context)
    
    try:
        with open(session_json_path, 'r') as f:
            session_data = json.load(f)
    except Exception as e:
        print(f"[Style Engine] Failed to read session.json: {e}")
        return
    
    # 3.5. Update session_data with the freshly synced prompt from text editor
    # This ensures the current prompt is used, not the old one from session.json
    props = context.scene.style_engine_props
    session_data['global_prompt'] = props.global_prompt
    session_data['negative_prompt'] = props.negative_prompt if hasattr(props, 'negative_prompt') else ""
    print(f"[Style Engine] Using prompt: {session_data['global_prompt'][:50]}...")
    if session_data['negative_prompt']:
        print(f"[Style Engine] Using negative: {session_data['negative_prompt'][:50]}...")
    
    # 4. Encode combined image to base64
    # In refine mode we use current_ai.png; otherwise the just-rendered combined.jpg.
    if refine_mode:
        combined_path = temp_dir / "current_ai.png"
        if not combined_path.exists():
            print(f"[Style Engine] Refine mode: current_ai.png not found at {combined_path}")
            return
        print(f"[Style Engine] Refine mode: using current_ai.png as conditioning input")
    else:
        combined_path = temp_dir / "combined.jpg"
        if not combined_path.exists():
            print(f"[Style Engine] Combined pass not found at {combined_path}")
            return
    
    # Get file size for diagnostic
    file_size_kb = combined_path.stat().st_size / 1024
    print(f"[Style Engine] 📦 Image file: {file_size_kb:.1f} KB ({'PNG' if refine_mode else 'JPEG'})")
    
    try:
        # Time the encoding operation
        import time
        encode_start = time.time()
        
        combined_b64 = runcomfy_client.encode_image_to_base64(str(combined_path))
        
        encode_duration = time.time() - encode_start
        print(f"[Style Engine] ⏱️ Encoding took {encode_duration:.3f}s ({len(combined_b64)} chars)")
    except runcomfy_client.RunComfyError as e:
        print(f"[Style Engine] Failed to encode combined image: {e}")
        return
    
    # 5. ALWAYS use SDXLREF workflow (with weights at 0 when no images)
    workflow_type = 'sdxlref'
    # props already defined at top of function
    
    # Count active reference images
    ref_count = sum([
        1 if img else 0 for img in [
            props.st1_image, props.st2_image, props.st3_image, props.st4_image, props.st5_image,
            props.comp1_image, props.comp2_image, props.comp3_image, props.comp4_image, props.comp5_image,
            props.sst1_image, props.sst2_image, props.sst3_image, props.sst4_image, props.sst5_image
        ]
    ])
    
    if ref_count > 0:
        print(f"[Style Engine] Using SDXLREF workflow ({ref_count} reference images active)")
        print(f"[Style Engine] Reference images will be encoded to base64 for serverless submission")
    else:
        print(f"[Style Engine] Using SDXLREF workflow (0 reference images - pure SDXL mode)")
    
    # 6. Ensure deployment exists (ONLY for RunComfy serverless mode)
    deployment_id = None
    overrides = None
    
    if not runcomfy_deployment.is_server_mode():
        # RunComfy serverless mode - ensure deployment and build overrides
        try:
            deployment_id = runcomfy_deployment.DeploymentManager.ensure_deployment(workflow_type)
        except runcomfy_client.RunComfyError as e:
            print(f"[Serverless API] Failed to ensure deployment: {e}")
            return
        
        # 7. Build overrides (depth not needed - AI generates it)
        # Pass context for reference image encoding
        overrides = build_runcomfy_overrides(
            context=context,
            session_data=session_data,
            combined_b64=combined_b64,
            workflow_type=workflow_type
        )
    
    # 8. Submit inference (GCS/Server or Serverless mode)
    try:
        import time
        
        if runcomfy_deployment.is_server_mode():
            # ================================================================
            # GCS/SERVER MODE - Direct ComfyUI Backend submission
            # ================================================================
            from . import runcomfy_server_client
            
            print(f"[GCS] =========================================")
            print(f"[GCS] DIRECT COMFYUI CONNECTION MODE")
            print(f"[GCS] =========================================")
            
            server_client = runcomfy_deployment.get_server_client()
            
            # Quick connection check before proceeding
            print(f"[GCS] Verifying server connection...")
            connected, conn_status = server_client.check_connection()
            if not connected:
                error = conn_status.get('error', 'Unknown error')
                print(f"[GCS] ❌ Server connection check failed: {error}")
                print(f"[GCS] Please use 'Test Server Connection' in preferences to diagnose.")
                return
            print(f"[GCS] ✓ Server connection verified")
            print(f"[GCS]")
            
            # UPLOAD IMAGES TO SERVER (key difference from RunComfy)
            # GCS needs the actual files, not Base64
            
            # Upload conditioning image (combined.jpg normally, current_ai.png in refine mode)
            _upload_label = "current_ai.png (refine)" if refine_mode else "combined.jpg"
            print(f"[GCS] Uploading {_upload_label} to server...")
            upload_start = time.time()
            upload_response = server_client.upload_image(str(combined_path))
            uploaded_filename = upload_response['name']
            upload_duration = time.time() - upload_start
            print(f"[GCS] ✓ Conditioning image uploaded: {uploaded_filename} ({upload_duration:.3f}s)")
            
            # ============================================================
            # GEMINI PATH (short-circuit if Gemini model selected)
            # ============================================================
            props = context.scene.style_engine_props
            if props.ai_model == 'GEMINI':
                print(f"[GCS] Using Gemini 3 Pro (nano-banana) model")
                
                from pathlib import Path
                addon_dir = Path(__file__).parent
                workflows_dir = addon_dir / "workflows" / "Image"

                # Ensure blank.png exists on the server so that Reference workflow
                # LoadImage nodes that are left at their default ("blank.png") always
                # pass ComfyUI validation, even if the slot-disconnect logic misses
                # an edge case. We upload once per generation from the bundled copy
                # in templates/ so the path is always relative to the addon directory.
                _blank_src = addon_dir / "templates" / "blank.png"
                if _blank_src.exists():
                    try:
                        server_client.upload_image(str(_blank_src), overwrite=True)
                        print(f"[GCS] ✓ blank.png uploaded to server")
                    except Exception as _be:
                        print(f"[GCS] ⚠️ blank.png upload failed (non-critical): {_be}")
                else:
                    print(f"[GCS] ⚠️ blank.png not found at {_blank_src}")

                # Select workflow based on references, alignment, and remove-bg toggles
                remove_bg = getattr(props, 'gemini_remove_bg', False)
                def _gemini_ref_has_valid_file(img):
                    if not img:
                        return False
                    fp = img.filepath
                    if not fp:
                        return False
                    abs_fp = bpy.path.abspath(fp)
                    return bool(abs_fp) and os.path.isfile(abs_fp)

                has_gemini_refs = any(
                    _gemini_ref_has_valid_file(getattr(props, f'gemini_ref{i}_image', None))
                    for i in range(1, 6)
                )

                if has_gemini_refs:
                    wf_name = "ImageNanoReferenceRB.json" if remove_bg else "ImageNanoReference.json"
                elif props.gemini_alignment:
                    wf_name = "ImageNanoAlignmentRB.json" if remove_bg else "ImageNanoAlignment.json"
                else:
                    wf_name = "ImageNanoTextRB.json" if remove_bg else "ImageNanoText.json"
                gemini_wf_path = workflows_dir / wf_name
                ref_label = f", Refs={'ON' if has_gemini_refs else 'OFF'}" if has_gemini_refs else ""
                print(f"[GCS] Alignment {'ON' if props.gemini_alignment else 'OFF'}, RemoveBG {'ON' if remove_bg else 'OFF'}{ref_label} - using {wf_name}")
                
                if not gemini_wf_path.exists():
                    print(f"[GCS] {gemini_wf_path.name} not found")
                    return
                
                with open(gemini_wf_path, 'r') as f:
                    workflow_json = json.load(f)
                
                # Raw prompt from STYLEENGINE_Prompt (no tag parsing for Gemini)
                text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
                raw_prompt = text_block.as_string().strip() if text_block else ""
                workflow_json["63"]["inputs"]["text"] = raw_prompt
                
                # Instructions from STYLEENGINE_Instructions text block
                instr_block = bpy.data.texts.get("STYLEENGINE_Instructions")
                instr_text = instr_block.as_string().strip() if instr_block else ""
                workflow_json["65"]["inputs"]["value"] = instr_text
                
                # Alignment-specific patching (also active for reference workflows which include Node 56)
                if props.gemini_alignment or has_gemini_refs:
                    workflow_json["56"]["inputs"]["image"] = uploaded_filename
                    # Load spatial alignment text
                    alignment_file = addon_dir / "templates" / "spatial_alignment.txt"
                    alignment_text = ""
                    if alignment_file.exists():
                        alignment_text = alignment_file.read_text(encoding='utf-8').strip()
                    workflow_json["66"]["inputs"]["value"] = alignment_text
                    print(f"[GCS]   - Alignment image: {uploaded_filename}")
                
                # Gemini-specific params
                workflow_json["50"]["inputs"]["temperature"] = props.gemini_temperature
                workflow_json["50"]["inputs"]["image_size"] = props.gemini_image_size
                
                # Auto-detect aspect ratio from render resolution
                _GEMINI_RATIOS = [
                    (1, 1, '1:1'), (2, 3, '2:3'), (3, 2, '3:2'), (3, 4, '3:4'),
                    (4, 3, '4:3'), (4, 5, '4:5'), (5, 4, '5:4'),
                    (9, 16, '9:16'), (16, 9, '16:9'), (21, 9, '21:9'),
                ]
                rw = context.scene.render.resolution_x
                rh = context.scene.render.resolution_y
                render_ratio = rw / max(rh, 1)
                best_ratio = min(_GEMINI_RATIOS, key=lambda r: abs((r[0]/r[1]) - render_ratio))
                computed_aspect = best_ratio[2]
                workflow_json["50"]["inputs"]["aspect_ratio"] = computed_aspect
                
                # Upload Gemini reference images.
                # Nodes 67-71 are LoadImage ref slots ONLY in ImageNanoReference[RB].json.
                # In all other workflows (Text, Alignment, their RB variants) node 67 is
                # InspyrenetRembg or simply absent — patching those IDs would corrupt or
                # crash them. Guard this entire block with has_gemini_refs so it only
                # runs when the Reference workflow was actually loaded.
                gemini_ref_count = 0
                if has_gemini_refs:
                    ref_node_map = [
                        ('gemini_ref1_image', '67'),
                        ('gemini_ref2_image', '68'),
                        ('gemini_ref3_image', '69'),
                        ('gemini_ref4_image', '70'),
                        ('gemini_ref5_image', '71'),
                    ]
                    for prop_name, node_id in ref_node_map:
                        img = getattr(props, prop_name, None)
                        abs_path = bpy.path.abspath(img.filepath) if (img and img.filepath) else ""
                        if abs_path and os.path.isfile(abs_path):
                            try:
                                compressed = compress_image_for_upload(abs_path)
                                resp = server_client.upload_image(str(compressed))
                                workflow_json[node_id]["inputs"]["image"] = resp['name']
                                gemini_ref_count += 1
                                print(f"[GCS]   - Ref {prop_name}: {resp['name']}")
                            except Exception as _e:
                                print(f"[GCS]   - Ref {prop_name}: upload failed ({_e}), using blank.png")
                                workflow_json[node_id]["inputs"]["image"] = "blank.png"
                        else:
                            # Slot is empty — reset to blank.png (valid, exists on server)
                            workflow_json[node_id]["inputs"]["image"] = "blank.png"
                            print(f"[GCS]   - Ref {prop_name}: empty → blank.png")

                print(f"[GCS] Patched Gemini workflow:")
                print(f"[GCS]   - Prompt: {raw_prompt[:60]}...")
                print(f"[GCS]   - Instructions: {instr_text[:40]}..." if instr_text else "[GCS]   - Instructions: (none)")
                print(f"[GCS]   - Temperature: {props.gemini_temperature}")
                print(f"[GCS]   - Size: {props.gemini_image_size}")
                print(f"[GCS]   - Aspect: {computed_aspect} (from {rw}x{rh})")
                if gemini_ref_count > 0:
                    print(f"[GCS]   - Reference images: {gemini_ref_count}")
                
                from . import progress_bar
                
                queue_response = server_client.queue_prompt(workflow_json)
                prompt_id = queue_response.get('prompt_id')
                progress_bar.set_current_workflow(workflow_json)
                
                print(f"[GCS] Gemini queued (ID: {prompt_id[:8]}...)")
                
                runcomfy_polling.RunComfyPoller.start_polling(
                    deployment_id='server',
                    request_id=prompt_id,
                    callback=lambda success, result=None, error=None, workflow_type=None: 
                        on_generation_complete_server(context, success, result, error, workflow_type or 'gemini', server_client),
                    workflow_type='gemini'
                )
                
                print(f"[GCS] Gemini generation started!")
                return
            
            # ============================================================
            # SDXL PATH (default)
            # ============================================================
            # Upload reference images (ST, COMP, SST) if they exist
            ref_image_props = [
                (props.st1_image, 'st1_path', 'ST1'),
                (props.st2_image, 'st2_path', 'ST2'),
                (props.st3_image, 'st3_path', 'ST3'),
                (props.st4_image, 'st4_path', 'ST4'),
                (props.st5_image, 'st5_path', 'ST5'),
                (props.comp1_image, 'comp1_path', 'COMP1'),
                (props.comp2_image, 'comp2_path', 'COMP2'),
                (props.comp3_image, 'comp3_path', 'COMP3'),
                (props.comp4_image, 'comp4_path', 'COMP4'),
                (props.comp5_image, 'comp5_path', 'COMP5'),
                (props.sst1_image, 'sst1_path', 'SST1'),
                (props.sst2_image, 'sst2_path', 'SST2'),
                (props.sst3_image, 'sst3_path', 'SST3'),
                (props.sst4_image, 'sst4_path', 'SST4'),
                (props.sst5_image, 'sst5_path', 'SST5'),
            ]
            
            uploaded_ref_images = {}
            ref_upload_count = 0
            
            for img, path_key, label in ref_image_props:
                if img and img.filepath:
                    try:
                        # Get absolute path to the image
                        img_path = bpy.path.abspath(img.filepath)
                        if os.path.exists(img_path):
                            # Upload to server
                            upload_resp = server_client.upload_image(img_path)
                            uploaded_name = upload_resp['name']
                            uploaded_ref_images[path_key] = uploaded_name
                            ref_upload_count += 1
                            print(f"[GCS]   ✓ {label}: {uploaded_name}")
                        else:
                            print(f"[GCS]   ⚠ {label}: File not found at {img_path}")
                    except Exception as e:
                        print(f"[GCS]   ✗ {label}: Upload failed - {e}")
            
            # Determine if we should use reference image workflow
            use_ref_images = ref_upload_count > 0
            sdxl_remove_bg = getattr(props, 'sdxl_remove_bg', False)

            if ref_upload_count > 0:
                print(f"[GCS] ✓ Uploaded {ref_upload_count} reference images")
                print(f"[GCS] Using ImageRef workflow (with IPAdapter), RemoveBG={'ON' if sdxl_remove_bg else 'OFF'}")
            else:
                print(f"[GCS] No reference images - using basic Image workflow, RemoveBG={'ON' if sdxl_remove_bg else 'OFF'}")
            print(f"[GCS]")

            # Load appropriate workflow JSON
            workflow_json = load_workflow_json_for_gcs(use_ref_images=use_ref_images, remove_bg=sdxl_remove_bg)
            if not workflow_json:
                print("[GCS] Failed to load workflow JSON")
                return
            
            print(f"[GCS] Patching workflow with session parameters...")
            
            # ============================================================
            # CORE PARAMETERS
            # ============================================================
            
            # Combined pass image (Node 15 - LoadImage "AO")
            workflow_json["15"]["inputs"]["image"] = uploaded_filename
            
            # Prompt (Node 25 - PrimitiveString)
            workflow_json["25"]["inputs"]["value"] = session_data['global_prompt']
            
            # Negative Prompt (Node 7 - CLIPTextEncode)
            negative_prompt = session_data.get('negative_prompt', '')
            if not negative_prompt:
                negative_prompt = "text, watermark, blurry, deformed, ugly, bad anatomy, worst quality, low quality"
            workflow_json["7"]["inputs"]["text"] = negative_prompt
            print(f"[GCS]   - Negative prompt: {negative_prompt[:60]}...")
            
            # Steps (Node 42 - PrimitiveInt)
            workflow_json["42"]["inputs"]["value"] = session_data.get('steps', 15)
            
            # ControlNet strengths (Nodes 40, 41 - PrimitiveFloat)
            workflow_json["40"]["inputs"]["value"] = session_data.get('silhouette_influence', 1.0)  # Canny
            workflow_json["41"]["inputs"]["value"] = session_data.get('depth_influence', 1.0)  # Depth
            
            # Influence / Denoise Control (Node 135 - easy float)
            # UI shows: 1.0 = keep render, 0.0 = full AI
            # But workflow needs: denoise where 0.0 = keep render, 1.0 = full AI
            # UI slider is 0-1 but actual working range is 0-0.7, so we scale
            influence_value = session_data.get('texture_influence', 1.0)  # UI value 0-1
            scaled_influence = influence_value * 0.7  # Scale to 0-0.7 for workflow
            denoise_value = 1.0 - scaled_influence  # Flip for workflow
            workflow_json["135"]["inputs"]["value"] = denoise_value
            
            # Seed (Node 4 - KSampler) - unified seed from UI
            seed = context.scene.style_engine_props.seed_value
            workflow_json["4"]["inputs"]["seed"] = seed
            
            # ============================================================
            # LORA (Node 136 - LoRa 1, Node 34 - LoRa 2)
            # Chain: Base Model → Node 136 (LoRa 1) → Node 34 (LoRa 2) → ...
            # ============================================================
            lora_config = session_data.get('lora', {})
            lora2_config = session_data.get('lora2', {})
            
            # LoRa 1 (Node 136 - first in chain, if node exists)
            if "136" in workflow_json:
                if lora_config.get('enabled', False) and lora_config.get('name') != 'NONE':
                    workflow_json["136"]["inputs"]["lora_name"] = lora_config['name']
                    workflow_json["136"]["inputs"]["strength_model"] = lora_config.get('strength_model', 0.8)
                    workflow_json["136"]["inputs"]["strength_clip"] = lora_config.get('strength_clip', 0.8)
                    print(f"[GCS] 🎨 LoRa 1 enabled: {lora_config['name']}")
                    print(f"[GCS]    Strength 1: {lora_config.get('strength_model', 0.8):.2f}")
                else:
                    # Disable LoRa 1 by setting strength to 0
                    workflow_json["136"]["inputs"]["strength_model"] = 0.0
                    workflow_json["136"]["inputs"]["strength_clip"] = 0.0
                    print(f"[GCS] LoRa 1 disabled")
            else:
                # Fallback: Single-LoRa workflow uses Node 34 for LoRa 1
                if lora_config.get('enabled', False) and lora_config.get('name') != 'NONE':
                    workflow_json["34"]["inputs"]["lora_name"] = lora_config['name']
                    workflow_json["34"]["inputs"]["strength_model"] = lora_config.get('strength_model', 0.8)
                    workflow_json["34"]["inputs"]["strength_clip"] = lora_config.get('strength_clip', 0.8)
                    print(f"[GCS] 🎨 LoRa 1 enabled: {lora_config['name']}")
                    print(f"[GCS]    Strength 1: {lora_config.get('strength_model', 0.8):.2f}")
                else:
                    workflow_json["34"]["inputs"]["strength_model"] = 0.0
                    workflow_json["34"]["inputs"]["strength_clip"] = 0.0
                    print(f"[GCS] LoRa 1 disabled")
            
            # LoRa 2 (Node 34 - second in chain, only if workflow has dual LoRa)
            if "136" in workflow_json:
                if lora2_config.get('enabled', False) and lora2_config.get('name') != 'NONE':
                    workflow_json["34"]["inputs"]["lora_name"] = lora2_config['name']
                    workflow_json["34"]["inputs"]["strength_model"] = lora2_config.get('strength_model', 0.8)
                    workflow_json["34"]["inputs"]["strength_clip"] = lora2_config.get('strength_clip', 0.8)
                    print(f"[GCS] 🎨 LoRa 2 enabled: {lora2_config['name']}")
                    print(f"[GCS]    Strength 2: {lora2_config.get('strength_model', 0.8):.2f}")
                else:
                    # Disable LoRa 2 by setting strength to 0
                    workflow_json["34"]["inputs"]["strength_model"] = 0.0
                    workflow_json["34"]["inputs"]["strength_clip"] = 0.0
                    print(f"[GCS] LoRa 2 disabled")
            elif lora2_config.get('enabled', False):
                print(f"[GCS] ⚠️ LoRa 2 enabled but workflow only has single LoRa node - skipping")
            
            # ============================================================
            # RESOLUTION (Node 5 - EmptyLatentImage)
            # ============================================================
            resolution = session_data.get('resolution', {})
            workflow_json["5"]["inputs"]["width"] = resolution.get('width', 1024)
            workflow_json["5"]["inputs"]["height"] = resolution.get('height', 1024)
            
            # ============================================================
            # IPADAPTER REFERENCE IMAGES (only for ImageRef.json workflow)
            # ============================================================
            if use_ref_images:
                ref_images = session_data.get('reference_images', {})
                
                # Global IPAdapter Strengths
                workflow_json["52"]["inputs"]["value"] = ref_images.get('style_transfer_strength', 0.0)   # Style Transfer
                workflow_json["90"]["inputs"]["value"] = ref_images.get('composition_strength', 1.0)      # Composition
                workflow_json["91"]["inputs"]["value"] = ref_images.get('force_transfer_strength', 0.0)   # Force Transfer
                
                # Style Transfer (ST) - Individual Weights
                workflow_json["129"]["inputs"]["value"] = ref_images.get('st1_weight', 1.0)  # ST1W
                workflow_json["126"]["inputs"]["value"] = ref_images.get('st2_weight', 1.0)  # ST2W
                workflow_json["125"]["inputs"]["value"] = ref_images.get('st3_weight', 0.0)  # ST3W
                workflow_json["124"]["inputs"]["value"] = ref_images.get('st4_weight', 0.0)  # ST4W
                workflow_json["123"]["inputs"]["value"] = ref_images.get('st5_weight', 0.0)  # ST5W
                
                # Composition (COMP) - Individual Weights
                workflow_json["122"]["inputs"]["value"] = ref_images.get('comp1_weight', 1.0)  # COMP1W
                workflow_json["121"]["inputs"]["value"] = ref_images.get('comp2_weight', 1.0)  # COMP2W
                workflow_json["120"]["inputs"]["value"] = ref_images.get('comp3_weight', 1.0)  # COMP3W
                workflow_json["119"]["inputs"]["value"] = ref_images.get('comp4_weight', 1.0)  # COMP4W
                workflow_json["118"]["inputs"]["value"] = ref_images.get('comp5_weight', 1.0)  # COMP5W
                
                # Strong Style Transfer (SST) - Individual Weights
                workflow_json["117"]["inputs"]["value"] = ref_images.get('sst1_weight', 1.0)  # SST1W
                workflow_json["116"]["inputs"]["value"] = ref_images.get('sst2_weight', 1.0)  # SST2W
                workflow_json["115"]["inputs"]["value"] = ref_images.get('sst3_weight', 1.0)  # SST3W
                workflow_json["114"]["inputs"]["value"] = ref_images.get('sst4_weight', 1.0)  # SST4W
                workflow_json["113"]["inputs"]["value"] = ref_images.get('sst5_weight', 1.0)  # SST5W
                
                # Reference Image Paths (LoadImage nodes)
                # Style Transfer images
                workflow_json["65"]["inputs"]["image"] = uploaded_ref_images.get('st1_path', 'blank.png')  # ST1
                workflow_json["63"]["inputs"]["image"] = uploaded_ref_images.get('st2_path', 'blank.png')  # ST2
                workflow_json["64"]["inputs"]["image"] = uploaded_ref_images.get('st3_path', 'blank.png')  # ST3
                workflow_json["94"]["inputs"]["image"] = uploaded_ref_images.get('st4_path', 'blank.png')  # ST4
                workflow_json["97"]["inputs"]["image"] = uploaded_ref_images.get('st5_path', 'blank.png')  # ST5
                
                # Composition images
                workflow_json["78"]["inputs"]["image"] = uploaded_ref_images.get('comp1_path', 'blank.png')  # COMP1
                workflow_json["77"]["inputs"]["image"] = uploaded_ref_images.get('comp2_path', 'blank.png')  # COMP2
                workflow_json["76"]["inputs"]["image"] = uploaded_ref_images.get('comp3_path', 'blank.png')  # COMP3
                workflow_json["100"]["inputs"]["image"] = uploaded_ref_images.get('comp4_path', 'blank.png')  # COMP4
                workflow_json["103"]["inputs"]["image"] = uploaded_ref_images.get('comp5_path', 'blank.png')  # COMP5
                
                # Strong Style Transfer images
                workflow_json["89"]["inputs"]["image"] = uploaded_ref_images.get('sst1_path', 'blank.png')  # SST1
                workflow_json["88"]["inputs"]["image"] = uploaded_ref_images.get('sst2_path', 'blank.png')  # SST2
                workflow_json["87"]["inputs"]["image"] = uploaded_ref_images.get('sst3_path', 'blank.png')  # SST3
                workflow_json["106"]["inputs"]["image"] = uploaded_ref_images.get('sst4_path', 'blank.png')  # SST4
                workflow_json["109"]["inputs"]["image"] = uploaded_ref_images.get('sst5_path', 'blank.png')  # SST5
                
                print(f"[GCS]   - IPAdapter: ST={ref_images.get('style_transfer_strength', 0.0):.2f}, Comp={ref_images.get('composition_strength', 1.0):.2f}, Force={ref_images.get('force_transfer_strength', 0.0):.2f}")
            
            print(f"[GCS] ✓ Workflow patched successfully")
            print(f"[GCS]   - Resolution: {resolution.get('width', 1024)}x{resolution.get('height', 1024)}")
            print(f"[GCS]   - Steps: {session_data.get('steps', 15)}")
            print(f"[GCS]   - ControlNet: Canny={session_data.get('silhouette_influence', 1.0):.2f}, Depth={session_data.get('depth_influence', 1.0):.2f}")
            print(f"[GCS]   - Influence: {influence_value:.2f} (1.0=keep render, 0.0=full AI) → denoise={denoise_value:.2f}")
            
            # Time the submission operation
            submit_start = time.time()
            
            # Queue prompt
            queue_response = server_client.queue_prompt(workflow_json)
            prompt_id = queue_response.get('prompt_id')
            
            # Store workflow for progress bar node name lookup
            from . import progress_bar
            progress_bar.set_current_workflow(workflow_json)
            
            submit_duration = time.time() - submit_start
            
            print(f"[GCS] ⏱️ Submission took {submit_duration:.3f}s")
            
            # Start polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id='server',  # Special marker for server mode
                request_id=prompt_id,
                callback=lambda success, result=None, error=None, workflow_type=None: 
                    on_generation_complete_server(context, success, result, error, workflow_type or 'sdxl', server_client),
                workflow_type=workflow_type
            )
            
            print(f"[GCS] 🖥️ GCS generation started (prompt_id: {prompt_id[:8]}...)")
            
        else:
            # ================================================================
            # SERVERLESS API MODE - RunComfy deployment submission
            # ================================================================
            client = runcomfy_deployment.get_runcomfy_client()
            
            # Time the upload operation
            submit_start = time.time()
            response = client.submit_inference(deployment_id, overrides)
            submit_duration = time.time() - submit_start
            
            request_id = response.get('request_id')
            
            print(f"[Serverless API] ⏱️ Upload took {submit_duration:.3f}s")
            
            # Start polling
            runcomfy_polling.RunComfyPoller.start_polling(
                deployment_id=deployment_id,
                request_id=request_id,
                callback=lambda success, result=None, error=None, workflow_type=None: 
                    on_generation_complete(context, success, result, error, workflow_type or 'sdxl'),
                workflow_type=workflow_type
            )
            
            print(f"[Serverless API] ☁️ Cloud generation started (request_id: {request_id[:8]}...)")
        
    except runcomfy_client.RunComfyError as e:
        print(f"[Serverless API] Failed to submit inference: {e}")
    except runcomfy_server_client.ServerAPIError as e:
        print(f"[GCS] Failed to submit to server: {e}")


def encode_blender_image_to_base64(img, max_size=1536):
    """
    Encode a Blender Image datablock to base64 using Blender's native API.
    Resizes if necessary to stay under 10MB RunComfy limit.
    
    Args:
        img: bpy.types.Image datablock
        max_size: Maximum dimension (width or height) in pixels
    
    Returns:
        str: Base64 data URI (data:image/jpeg;base64,...)
    """
    import bpy
    import base64
    import tempfile
    from pathlib import Path
    
    # Get original size
    original_size = (img.size[0], img.size[1])
    needs_resize = max(original_size) > max_size
    
    # Create a temp copy of the image for processing
    temp_img = img.copy()
    
    try:
        if needs_resize:
            # Calculate new size maintaining aspect ratio
            if original_size[0] > original_size[1]:
                new_width = max_size
                new_height = int(original_size[1] * (max_size / original_size[0]))
            else:
                new_height = max_size
                new_width = int(original_size[0] * (max_size / original_size[1]))
            
            # Resize using Blender's scale
            temp_img.scale(new_width, new_height)
            print(f"[Style Engine] Resized: {original_size} → {(new_width, new_height)}")
        
        # Save to temporary file as JPEG (compressed)
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"styleengine_ref_{id(img)}.jpg"
        
        # Configure file format settings for JPEG
        scene_settings = bpy.context.scene.render.image_settings
        old_format = scene_settings.file_format
        old_quality = scene_settings.quality
        old_color_mode = scene_settings.color_mode
        
        try:
            scene_settings.file_format = 'JPEG'
            scene_settings.quality = 90
            scene_settings.color_mode = 'RGB'
            
            # Save the temp image
            temp_img.save_render(str(temp_path))
            
            # Read and encode
            with open(temp_path, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Clean up temp file
            temp_path.unlink(missing_ok=True)
            
            return f"data:image/jpeg;base64,{img_data}"
            
        finally:
            # Restore original settings
            scene_settings.file_format = old_format
            scene_settings.quality = old_quality
            scene_settings.color_mode = old_color_mode
            
    finally:
        # Clean up temp image
        bpy.data.images.remove(temp_img)


def build_runcomfy_overrides(context, session_data, combined_b64, workflow_type):
    """
    Build overrides dict for RunComfy API submission.
    
    Args:
        context: Blender context (to access image pointers for encoding)
        session_data: Session JSON data
        combined_b64: Base64 encoded combined pass
        workflow_type: Should always be 'sdxlref'
    
    Returns:
        dict: Overrides for workflow nodes
    
    Note: Depth is NOT sent - the workflow uses DepthAnything AI to generate it from combined pass
    """
    from . import runcomfy_client
    import bpy
    
    # Extract resolution from session data (CRITICAL for SDXL native resolutions)
    resolution = session_data.get('resolution', {})
    width = resolution.get('width', 1024)
    height = resolution.get('height', 1024)
    
    print(f"[Style Engine] 📐 Workflow resolution override: {width}x{height}")
    print(f"[Style Engine] Note: Depth generated by DepthAnything AI (not sent from Blender)")
    
    # ALWAYS use SDXLREF workflow (only one workflow type)
    if workflow_type == 'sdxlref':
        # Map to SDXLREF.json nodes (with reference images)
        ref_data = session_data.get('reference_images', {})
        
        # Prompts
        positive_prompt = session_data.get('global_prompt', '')
        
        # Use negative prompt from Prompt Builder if available, otherwise use default
        custom_negative = session_data.get('negative_prompt', '')
        if custom_negative:
            negative_prompt = custom_negative
            print(f"[Style Engine] 📝 POSITIVE PROMPT: {positive_prompt}")
            print(f"[Style Engine] 🚫 NEGATIVE PROMPT (custom): {negative_prompt}")
        else:
            # Default negative prompt (good general purpose)
            negative_prompt = "text, watermark, blurry, deformed, ugly, bad anatomy, worst quality, low quality"
            print(f"[Style Engine] 📝 POSITIVE PROMPT: {positive_prompt}")
            print(f"[Style Engine] 🚫 NEGATIVE PROMPT (default): {negative_prompt}")
        
        # Viewport influence: UI is 0-1, scale to 0-0.7 for workflow, then flip for denoise
        influence_value = session_data.get('texture_influence', 1.0)
        scaled_influence = influence_value * 0.7  # Scale to 0-0.7
        denoise_value = 1.0 - scaled_influence  # Flip: 0=keep render, 1=full AI
        
        overrides = {
            "5": {"inputs": {"width": width, "height": height}},  # EmptyLatentImage
            "25": {"inputs": {"value": positive_prompt}},  # Positive Prompt (Node 25)
            "7": {"inputs": {"text": negative_prompt}},  # Negative Prompt (Node 7) - CRITICAL!
            "15": {"inputs": {"image": combined_b64}},  # Base image (AO)
            "40": {"inputs": {"value": session_data.get('silhouette_influence', 0.75)}},  # Canny
            "41": {"inputs": {"value": session_data.get('depth_influence', 0.5)}},  # Depth
            "42": {"inputs": {"value": session_data.get('steps', 15)}},  # Steps
            "135": {"inputs": {"value": denoise_value}},  # Viewport influence (denoise)
            # Global strengths
            "52": {"inputs": {"value": ref_data.get('style_transfer_strength', 0.0)}},
            "90": {"inputs": {"value": ref_data.get('composition_strength', 1.0)}},
            "91": {"inputs": {"value": ref_data.get('force_transfer_strength', 0.0)}},
        }
        
        # Add reference image overrides (weights)
        # Style Transfer weights (ST1-ST5)
        st_weight_nodes = ["129", "126", "125", "124", "123"]
        st_keys = ['st1_weight', 'st2_weight', 'st3_weight', 'st4_weight', 'st5_weight']
        for node, key in zip(st_weight_nodes, st_keys):
            overrides[node] = {"inputs": {"value": ref_data.get(key, 0.0)}}
        
        # Composition weights (COMP1-COMP5)
        comp_weight_nodes = ["122", "121", "120", "119", "118"]
        comp_keys = ['comp1_weight', 'comp2_weight', 'comp3_weight', 'comp4_weight', 'comp5_weight']
        for node, key in zip(comp_weight_nodes, comp_keys):
            overrides[node] = {"inputs": {"value": ref_data.get(key, 0.0)}}
        
        # Force Style Transfer weights (SST1-SST5)
        sst_weight_nodes = ["117", "116", "115", "114", "113"]
        sst_keys = ['sst1_weight', 'sst2_weight', 'sst3_weight', 'sst4_weight', 'sst5_weight']
        for node, key in zip(sst_weight_nodes, sst_keys):
            overrides[node] = {"inputs": {"value": ref_data.get(key, 0.0)}}
        
        # Add reference images (encode to base64 for RunComfy serverless)
        # Get props to access actual image pointers
        props = context.scene.style_engine_props
        
        # Style Transfer images (ST1-ST5): nodes 65, 63, 64, 94, 97
        st_image_nodes = ["65", "63", "64", "94", "97"]
        st_images = [props.st1_image, props.st2_image, props.st3_image, props.st4_image, props.st5_image]
        st_labels = ['ST1', 'ST2', 'ST3', 'ST4', 'ST5']
        
        for node, img, label in zip(st_image_nodes, st_images, st_labels):
            if img and img.filepath:
                try:
                    # Use Blender-native resize and encode
                    img_b64 = encode_blender_image_to_base64(img, max_size=1536)
                    overrides[node] = {"inputs": {"image": img_b64}}
                    size_kb = len(img_b64) / 1024
                    print(f"[Style Engine] ✓ Encoded {label}: {img.name} ({size_kb:.1f} KB)")
                except Exception as e:
                    print(f"[Style Engine] ⚠️ Failed to encode {label}: {e}")
        
        # Composition images (COMP1-COMP5): nodes 78, 77, 76, 100, 103
        comp_image_nodes = ["78", "77", "76", "100", "103"]
        comp_images = [props.comp1_image, props.comp2_image, props.comp3_image, props.comp4_image, props.comp5_image]
        comp_labels = ['COMP1', 'COMP2', 'COMP3', 'COMP4', 'COMP5']
        
        for node, img, label in zip(comp_image_nodes, comp_images, comp_labels):
            if img and img.filepath:
                try:
                    # Use Blender-native resize and encode
                    img_b64 = encode_blender_image_to_base64(img, max_size=1536)
                    overrides[node] = {"inputs": {"image": img_b64}}
                    size_kb = len(img_b64) / 1024
                    print(f"[Style Engine] ✓ Encoded {label}: {img.name} ({size_kb:.1f} KB)")
                except Exception as e:
                    print(f"[Style Engine] ⚠️ Failed to encode {label}: {e}")
        
        # Force Style Transfer images (SST1-SST5): nodes 89, 88, 87, 106, 109
        sst_image_nodes = ["89", "88", "87", "106", "109"]
        sst_images = [props.sst1_image, props.sst2_image, props.sst3_image, props.sst4_image, props.sst5_image]
        sst_labels = ['SST1', 'SST2', 'SST3', 'SST4', 'SST5']
        
        for node, img, label in zip(sst_image_nodes, sst_images, sst_labels):
            if img and img.filepath:
                try:
                    # Use Blender-native resize and encode
                    img_b64 = encode_blender_image_to_base64(img, max_size=1536)
                    overrides[node] = {"inputs": {"image": img_b64}}
                    size_kb = len(img_b64) / 1024
                    print(f"[Style Engine] ✓ Encoded {label}: {img.name} ({size_kb:.1f} KB)")
                except Exception as e:
                    print(f"[Style Engine] ⚠️ Failed to encode {label}: {e}")
        
        # ========== EXHAUSTIVE DEBUG LOGGING ==========
        print(f"\n{'='*70}")
        print(f"[Style Engine] 🔍 EXHAUSTIVE SDXLREF WORKFLOW DEBUG")
        print(f"{'='*70}")
        
        # Basic parameters
        print(f"\n📐 BASIC PARAMETERS:")
        print(f"  Resolution: {width}x{height}")
        print(f"  Steps: {session_data.get('steps', 15)}")
        print(f"  Canny Influence: {session_data.get('silhouette_influence', 0.75)}")
        print(f"  Depth Influence: {session_data.get('depth_influence', 0.5)}")
        
        # Global strengths (UI 0.0-1.0 scaled to 0.0-1.5 for workflow)
        print(f"\n🎚️ GLOBAL STRENGTHS (scaled 1.5x for workflow):")
        print(f"  Style Transfer Strength (Node 52): {ref_data.get('style_transfer_strength', 0.0)}")
        print(f"  Composition Strength (Node 90): {ref_data.get('composition_strength', 1.0)}")
        print(f"  Force Transfer Strength (Node 91): {ref_data.get('force_transfer_strength', 0.0)}")
        
        # Style Transfer weights and images
        print(f"\n🎨 STYLE TRANSFER (ST1-ST5):")
        for i, (node, key, img_node, img, label) in enumerate(zip(
            st_weight_nodes, st_keys, st_image_nodes, st_images, st_labels), 1):
            weight = ref_data.get(key, 0.0)
            img_name = img.name if img else ""
            has_image = bool(img and img.filepath)
            status = "✓ ACTIVE (encoded)" if (weight > 0 and has_image) else "✗ INACTIVE"
            print(f"  ST{i}: Weight={weight:.3f} (Node {node}), Image='{img_name}' (Node {img_node}) {status}")
        
        # Composition weights and images
        print(f"\n📐 COMPOSITION (COMP1-COMP5):")
        for i, (node, key, img_node, img, label) in enumerate(zip(
            comp_weight_nodes, comp_keys, comp_image_nodes, comp_images, comp_labels), 1):
            weight = ref_data.get(key, 0.0)
            img_name = img.name if img else ""
            has_image = bool(img and img.filepath)
            status = "✓ ACTIVE (encoded)" if (weight > 0 and has_image) else "✗ INACTIVE"
            print(f"  COMP{i}: Weight={weight:.3f} (Node {node}), Image='{img_name}' (Node {img_node}) {status}")
        
        # Force Style Transfer weights and images
        print(f"\n💪 FORCE STYLE TRANSFER (SST1-SST5):")
        for i, (node, key, img_node, img, label) in enumerate(zip(
            sst_weight_nodes, sst_keys, sst_image_nodes, sst_images, sst_labels), 1):
            weight = ref_data.get(key, 0.0)
            img_name = img.name if img else ""
            has_image = bool(img and img.filepath)
            status = "✓ ACTIVE (encoded)" if (weight > 0 and has_image) else "✗ INACTIVE"
            print(f"  SST{i}: Weight={weight:.3f} (Node {node}), Image='{img_name}' (Node {img_node}) {status}")
        
        # Summary
        active_count = sum([
            1 for key in st_keys + comp_keys + sst_keys 
            if ref_data.get(key, 0.0) > 0
        ])
        
        # Estimate total payload size
        import json
        overrides_json = json.dumps(overrides)
        payload_size_mb = len(overrides_json) / (1024 * 1024)
        
        print(f"\n📊 SUMMARY:")
        print(f"  Total overrides: {len(overrides)} nodes")
        print(f"  Active reference images: {active_count}")
        print(f"  Base image size: {len(combined_b64) / 1024:.1f} KB")
        print(f"  Estimated payload size: {payload_size_mb:.2f} MB")
        
        # Warn if approaching 10MB limit
        if payload_size_mb > 8:
            print(f"  ⚠️ WARNING: Payload is large ({payload_size_mb:.2f} MB), close to 10MB limit!")
        elif payload_size_mb > 9.5:
            print(f"  ❌ ERROR: Payload too large ({payload_size_mb:.2f} MB), will exceed 10MB limit!")
        
        print(f"{'='*70}\n")
        
        return overrides
    else:
        # Should never reach here - we always use sdxlref
        print(f"[Style Engine] ❌ ERROR: Invalid workflow_type '{workflow_type}' - should always be 'sdxlref'")
        return {}


# ================================================================
# SERVER API HELPERS
# ================================================================

def load_workflow_json_for_server(workflow_type):
    """
    Load workflow JSON file for Server API mode.
    ALWAYS loads SDXLREF.json (single unified workflow).
    
    Args:
        workflow_type: Should always be 'sdxlref'
    
    Returns:
        dict: Workflow JSON or None if failed
    """
    import json
    from pathlib import Path
    
    # Determine workflow file path
    addon_dir = Path(__file__).parent.parent.parent.parent  # Go up to STYLEENGINE root
    workflows_dir = addon_dir / "ComfyUI" / "runcomfyWorkflows"
    
    # ALWAYS use SDXLREF.json
    workflow_file = workflows_dir / "SDXLREF.json"
    
    if workflow_type != 'sdxlref':
        print(f"[Server API] ⚠️ WARNING: workflow_type '{workflow_type}' ignored - always using SDXLREF.json")
    
    try:
        with open(workflow_file, 'r') as f:
            workflow_json = json.load(f)
        print(f"[Server API] Loaded workflow: {workflow_file.name}")
        return workflow_json
    except Exception as e:
        print(f"[Server API] Failed to load workflow {workflow_file}: {e}")
        return None


def load_workflow_json_for_gcs(use_ref_images=False, remove_bg=False):
    """
    Load workflow JSON file for GCS mode (self-hosted ComfyUI).
    
    Selects the appropriate workflow based on whether reference images are used
    and whether background removal is requested:
    - Image/Image.json:       Basic workflow (no refs, no rembg)
    - Image/ImageRB.json:     Basic workflow + InspyrenetRembg
    - Image/ImageRef.json:    IPAdapter reference images (no rembg)
    - Image/ImageRefRB.json:  IPAdapter reference images + InspyrenetRembg

    Args:
        use_ref_images: If True, use the ImageRef variant (with IPAdapter).
        remove_bg:      If True, use the RB variant (adds rembg node).

    Returns:
        dict: Workflow JSON or None if failed
    """
    import json
    from pathlib import Path

    # Determine workflow file path - workflows folder is inside the addon directory
    addon_dir = Path(__file__).parent  # This is scripts/addons/styleengine/
    workflows_dir = addon_dir / "workflows" / "Image"

    # Select workflow based on reference image usage and remove-bg flag
    if use_ref_images and remove_bg:
        workflow_file = workflows_dir / "ImageRefRB.json"
        workflow_desc = "ImageRefRB.json (IPAdapter + rembg)"
    elif use_ref_images:
        workflow_file = workflows_dir / "ImageRef.json"
        workflow_desc = "ImageRef.json (with IPAdapter reference images)"
    elif remove_bg:
        workflow_file = workflows_dir / "ImageRB.json"
        workflow_desc = "ImageRB.json (basic + rembg)"
    else:
        workflow_file = workflows_dir / "Image.json"
        workflow_desc = "Image.json (basic, faster)"
    
    try:
        with open(workflow_file, 'r') as f:
            workflow_json = json.load(f)
        print(f"[GCS] ✓ Loaded workflow: {workflow_desc}")
        return workflow_json
    except Exception as e:
        print(f"[GCS] ❌ Failed to load workflow {workflow_file}: {e}")
        print(f"[GCS] Make sure {workflow_file.name} exists at: {workflow_file}")
        return None


def on_generation_complete_server(context, success, result, error, workflow_type, server_client):
    """
    Callback for Server API generation completion.
    Downloads images from server and updates UI.
    
    Args:
        context: Blender context
        success: True if generation succeeded
        result: Server API result (prompt_data from history)
        error: Error message if failed
        workflow_type: 'sdxl' or 'ipadapter'
        server_client: ComfyUIServerClient instance
    """
    from . import runcomfy_server_client
    from pathlib import Path
    
    if not success:
        print(f"[Server API] ❌ Generation failed: {error}")
        return
    
    try:
        # Extract output images from result
        images = runcomfy_server_client.extract_output_images(result)
        
        if not images:
            print("[GCS] No output images found in result")
            trigger_next_generation_cycle(context)
            return
        
        # Get temp directory (already includes ai_vision)
        temp_dir = get_temp_directory(context)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if preview images should be downloaded
        prefs = context.preferences.addons['styleengine'].preferences
        download_previews = prefs.gcs_download_preview_images
        
        print(f"[GCS] Found {len(images)} output images")
        if download_previews:
            print(f"[GCS] Preview images enabled - downloading all images")
        
        # Build list of downloads to perform
        # Note: Node IDs in Image.json/ImageRef.json (133=canny, 134=depth)
        # but filename_prefix values remain the same, so detection still works
        downloads_to_perform = []
        
        for img_info in images:
            filename = img_info['filename']
            subfolder = img_info.get('subfolder', '')
            image_type = img_info.get('type', 'output')
            
            # Determine save name based on filename prefix
            # Uses blacklist approach: canny/depth are preview images,
            # everything else is treated as the main output (current_ai.png).
            # This is resilient to workflow prefix changes.
            filename_lower = filename.lower()
            if filename_lower.startswith('canny'):
                if not download_previews:
                    continue  # Skip preview images if disabled
                save_name = 'canny.png'
            elif filename_lower.startswith('depth'):
                if not download_previews:
                    continue  # Skip preview images if disabled
                save_name = 'depth.png'
            else:
                # Any non-preview image is the main AI output
                save_name = 'current_ai.png'
            
            downloads_to_perform.append({
                'filename': filename,
                'save_name': save_name,
                'save_path': str(temp_dir / save_name),
                'subfolder': subfolder,
                'image_type': image_type
            })
        
        # Download images in parallel using ThreadPoolExecutor
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def download_single_image(task, max_retries=2):
            """Download a single image with retry and atomic write."""
            start = time.time()
            save_path = task['save_path']
            tmp_path = save_path + '.tmp'
            
            for attempt in range(max_retries + 1):
                try:
                    # Download to temp file first (atomic write)
                    success = server_client.download_image(
                        task['filename'], 
                        tmp_path, 
                        task['subfolder'], 
                        task['image_type']
                    )
                    
                    if success and os.path.exists(tmp_path):
                        # Verify file has valid content (> 1KB)
                        file_size = os.path.getsize(tmp_path)
                        if file_size > 1024:
                            # Atomic rename to final path
                            os.replace(tmp_path, save_path)
                            duration = time.time() - start
                            return {
                                'save_name': task['save_name'],
                                'success': True,
                                'duration': duration
                            }
                        else:
                            print(f"[GCS] ⚠️ {task['save_name']}: file too small ({file_size}B), retry {attempt + 1}/{max_retries + 1}")
                except Exception as e:
                    print(f"[GCS] ⚠️ {task['save_name']}: download error (attempt {attempt + 1}): {e}")
                
                # Brief pause before retry
                if attempt < max_retries:
                    time.sleep(0.5)
            
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            
            duration = time.time() - start
            return {
                'save_name': task['save_name'],
                'success': False,
                'duration': duration
            }
        
        main_image_downloaded = False
        
        if downloads_to_perform:
            download_start = time.time()
            print(f"[GCS] Starting parallel download of {len(downloads_to_perform)} images...")
            
            # Use ThreadPoolExecutor for parallel downloads
            with ThreadPoolExecutor(max_workers=min(len(downloads_to_perform), 4)) as executor:
                futures = {executor.submit(download_single_image, task): task for task in downloads_to_perform}
                
                for future in as_completed(futures):
                    result = future.result()
                    if result['success']:
                        print(f"[GCS] ✅ {result['save_name']} ({result['duration']:.3f}s)")
                        if result['save_name'] == 'current_ai.png':
                            main_image_downloaded = True
                    else:
                        print(f"[GCS] ❌ Failed: {result['save_name']}")
            
            total_duration = time.time() - download_start
            print(f"[GCS] ⏱️ All downloads completed in {total_duration:.3f}s (parallel)")
        
        # Update camera background if main image was downloaded
        if main_image_downloaded:
            # Defer all ID-data writes to the next safe main-loop tick.
            # - 'context' captured by closure may be stale/restricted by the time
            #   the timer fires, so we use bpy.context inside the callback instead.
            # - _current_ai_path is a plain Path value (safe to close over).
            _current_ai_path = temp_dir / "current_ai.png"

            def _deferred_post_download():
                try:
                    _ctx = bpy.context  # fresh, safe context at timer-fire time
                    # Reset visualization to COMBINED (final image) after generation
                    _props = _ctx.scene.style_engine_props
                    if hasattr(_props, 'visualization_type'):
                        _props.visualization_type = 'COMBINED'

                    # Save timestamped copy to project library
                    saved_path = save_generation_to_library(_ctx, _current_ai_path, backend='GCS')
                    if saved_path:
                        print(f"[GCS] ✅ Generation saved to library")

                    # Refresh camera background
                    refresh_ai_image()
                    print(f"[GCS] ✓ Camera background updated with new AI image")

                    # Trigger next generation cycle if auto-generate is enabled
                    trigger_next_generation_cycle(_ctx)
                except Exception as _e:
                    print(f"[GCS] Error in deferred post-download: {_e}")
                    import traceback
                    traceback.print_exc()
                    trigger_next_generation_cycle(bpy.context)
                return None

            bpy.app.timers.register(_deferred_post_download, first_interval=0.05)
        else:
            # No main image — still trigger next cycle
            trigger_next_generation_cycle(context)
    
    except Exception as e:
        print(f"[GCS] Error in completion callback: {e}")
        import traceback
        traceback.print_exc()
        # Still trigger next cycle even on error
        trigger_next_generation_cycle(context)


def on_generation_complete(context, success, result, error, workflow_type='sdxl'):
    """
    Callback when RunComfy generation finishes.
    
    Args:
        context: Blender context
        success: bool
        result: Result dict if successful
        error: Error message if failed
        workflow_type: 'sdxl' or 'ipadapter' (determines which output node to check)
    """
    from . import runcomfy_client
    import shutil
    
    print(f"[Style Engine] 🔍 Processing result for workflow: {workflow_type}")
    
    if not success:
        print(f"[Style Engine] ❌ Generation failed: {error}")
        # Even on failure, trigger next cycle if auto-generate is enabled
        trigger_next_generation_cycle(context)
        return
    
    # Extract image URL from result
    outputs = result.get('outputs', {})
    image_url = None
    
    # Debug: Show all available output nodes
    print(f"[Style Engine] DEBUG: Received {len(outputs)} output nodes")
    for node_id in outputs.keys():
        has_images = 'images' in outputs[node_id] and outputs[node_id]['images']
        print(f"[Style Engine] DEBUG:   Node {node_id}: {'✓ has images' if has_images else '✗ no images'}")
    
    # ALWAYS use SDXLREF workflow - Try Node 53 first (easy imageSave - final output)
    if '53' in outputs and 'images' in outputs['53'] and outputs['53']['images']:
        image_url = outputs['53']['images'][0].get('url')
        print(f"[Style Engine] ✅ Using output from Node 53 (SDXLREF final SaveImage)")
    else:
        print(f"[Style Engine] ⚠️ Node 53 not found, checking fallback...")
    
    # Fallback: find any SaveImage output
    # Priority: 'output' type images > 'temp' type images (last one wins)
    if not image_url:
        print("[Style Engine] Searching all nodes for images...")
        
        # First pass: Look for 'output' type images (final SaveImage nodes)
        for node_id, node_output in outputs.items():
            if 'images' in node_output and node_output['images']:
                img_type = node_output['images'][0].get('type', '')
                if img_type == 'output':
                    image_url = node_output['images'][0].get('url')
                    print(f"[Style Engine] ✅ Found 'output' type image in Node {node_id}")
                    break
        
        # Second pass: Accept any image if no 'output' found (last one wins)
        if not image_url:
            for node_id, node_output in outputs.items():
                if 'images' in node_output and node_output['images']:
                    image_url = node_output['images'][0].get('url')
                    img_type = node_output['images'][0].get('type', 'unknown')
                    print(f"[Style Engine] ⚠️ Using '{img_type}' image from Node {node_id}")
                    # Don't break - keep iterating to get the LAST one
    
    if not image_url:
        print("[Style Engine] No image found in result")
        trigger_next_generation_cycle(context)
        return
    
    # Download to temp (always)
    temp_dir = get_temp_directory(context)
    current_ai_path = temp_dir / "current_ai.png"
    
    print(f"[Style Engine] Downloading result from: {image_url[:50]}...")
    
    if runcomfy_client.download_image_from_url(image_url, str(current_ai_path)):
        print("[Style Engine] ✅ Downloaded to temp")
        
        # Save to project library with new system
        saved_path = save_generation_to_library(context, current_ai_path, backend='RunComfy')
        
        if saved_path:
            print(f"[Style Engine] ✅ Generation saved to library")
        
        # Update camera background (on-demand refresh - only when new image arrives!)
        refresh_ai_image()
        print("[Style Engine] ✓ Camera background updated with new AI image")
    else:
        print("[Style Engine] ❌ Download failed")
    
    # ✅ CYCLICAL AUTO-GENERATION: Trigger next cycle if auto-generate is enabled
    trigger_next_generation_cycle(context)


def trigger_next_generation_cycle(context):
    """
    Trigger the next generation cycle if auto-generate is enabled.
    This creates the cyclical loop: render → generate → download → repeat
    OPTIMIZED: Uses actual generation timing (~26s) for smart scheduling.
    """
    try:
        props = bpy.context.scene.style_engine_props
        
        # Only continue if auto-generate is still enabled
        if hasattr(props, 'auto_generate') and props.auto_generate:
            # Generation takes ~26s on average
            # Wait a bit before starting next cycle to give system breathing room
            delay = 3.0  # 3 second breather between cycles
            print(f"[Style Engine] 🔄 Next cycle in {delay}s...")
            bpy.app.timers.register(lambda: start_generation_cycle(), first_interval=delay)
        else:
            print("[Style Engine] Auto-generate disabled, stopping cycle")
    except Exception as e:
        print(f"[Style Engine] Error in trigger_next_generation_cycle: {e}")


def start_generation_cycle():
    """
    Start a single generation cycle: render → submit to RunComfy
    This is called when auto-generate is enabled.
    """
    try:
        # Get context from window manager
        context = bpy.context
        
        print("[Style Engine] 🎬 Starting generation cycle...")
        generate_ai_image_cloud(context)
        
    except Exception as e:
        print(f"[Style Engine] Error in generation cycle: {e}")
        import traceback
        traceback.print_exc()


# ----------------------------------------------------------------
# REGISTRATION
# ----------------------------------------------------------------
classes = (
    WM_OT_SetupWorkspace,
    WM_OT_PopulateAssets,
    WM_OT_SetCamera,
    WM_OT_StopAutoRefresh,
    WM_OT_StartAutoRefresh,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    """Unregister classes."""
    # Note: refresh_ai_image is now on-demand (no timer to unregister)
    # auto_render_passes is deprecated (no longer used)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

