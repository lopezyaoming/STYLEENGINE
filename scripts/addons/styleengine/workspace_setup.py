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
from bpy.app.handlers import persistent

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


@persistent
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

    try:
        from . import hub_client
        prefs      = bpy.context.preferences.addons["styleengine"].preferences
        hub_url    = getattr(prefs, "hub_url", "http://127.0.0.1:8000").rstrip("/")
        session_id = hub_client.get_session_id(bpy.data.filepath)
        current_ai = str(get_active_ai_output_path(bpy.context))
        hub_client.register_session(hub_url, session_id, Path(bpy.data.filepath).stem, bpy.data.filepath, current_ai)
        print(f"[Style Engine] Hub re-registered session: {session_id!r}")
    except Exception as e:
        print(f"[Style Engine] Hub re-register on save failed: {e}")


# ================================================================
#    Generation Browser - Navigate Through Saved Generations
# ================================================================

def get_generation_list(context):
    """
    Get list of all saved generations, sorted chronologically (oldest to newest).

    In Asset Mode returns images from the active asset's Images/ folder so the
    generation browser navigates asset iterations rather than the scene library.

    Returns:
        list[Path]: List of generation image paths, sorted by timestamp
    """
    try:
        _props = context.scene.style_engine_props
        if getattr(_props, 'asset_mode', False):
            _comps = get_asset_path_components(_props)
            if _comps:
                _asset_dir = get_nested_asset_directory(context, _comps)
            else:
                _asset_dir = get_asset_directory(context, _props.current_asset_name)
            _images_dir = _asset_dir / "Images"
            if not _images_dir.exists():
                return []
            _gens = list(_images_dir.glob("*.png"))
            _gens.sort()
            return _gens
    except Exception as _e:
        print(f"[Style Engine] ⚠ get_generation_list asset-mode fallback: {_e}")

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

    In Asset Mode writes to the asset's own temp/current_ai.png and refreshes
    the asset camera background, so the scene's current_ai.png is never touched.
    In Scene Mode writes to the global temp/current_ai.png as before.

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

    # ── Asset Mode: write to the asset's own temp, refresh asset camera ──────
    try:
        _props = context.scene.style_engine_props
        if getattr(_props, 'asset_mode', False):
            _comps = get_asset_path_components(_props)
            if _comps:
                _asset_temp = get_nested_asset_directory(context, _comps) / "temp"
            else:
                _asset_temp = get_asset_temp_directory(
                    context, _props.current_asset_name)
            _asset_temp.mkdir(parents=True, exist_ok=True)
            _current_ai = _asset_temp / "current_ai.png"
            try:
                shutil.copy2(generation_path, _current_ai)
                print(f"[Style Engine] 📷 Loaded asset generation: {generation_path.name}")
            except Exception as _ce:
                print(f"[Style Engine] ❌ Failed to load asset generation: {_ce}")
                return False
            # Refresh the asset camera background (not the scene ai_camera)
            refresh_asset_camera_image(
                _comps[-1] if _comps else _props.current_asset_name,
                path_components=_comps if _comps else None,
            )
            # Restore sidecars (same logic as scene mode below, same sidecar files)
            _sidecar_txt = generation_path.with_suffix(".txt")
            if _sidecar_txt.exists():
                try:
                    tb = bpy.data.texts.get("STYLEENGINE_Prompt")
                    if not tb:
                        tb = bpy.data.texts.new("STYLEENGINE_Prompt")
                    tb.clear()
                    tb.write(_sidecar_txt.read_text(encoding='utf-8'))
                    print(f"[Style Engine] 📖 Restored asset prompt sidecar: "
                          f"{_sidecar_txt.name}")
                except Exception as _te:
                    print(f"[Style Engine] ⚠ Asset prompt sidecar error: {_te}")
            _sidecar_json = generation_path.with_suffix(".json")
            if _sidecar_json.exists():
                try:
                    import json as _j
                    _data = _j.loads(_sidecar_json.read_text(encoding='utf-8'))
                    from . import ui_panel as _up
                    _up._populate_refine_from_json(_props, _j.dumps(_data))
                    print(f"[Style Engine] 🔬 Restored asset JSON sidecar: "
                          f"{_sidecar_json.name}")
                except Exception as _je:
                    print(f"[Style Engine] ⚠ Asset JSON sidecar error: {_je}")
            return True
    except Exception as _am_e:
        print(f"[Style Engine] ⚠ load_generation_to_current asset branch error: {_am_e}")
        # Fall through to scene-mode path

    # ── Scene Mode: write to global temp, refresh ai_camera ──────────────────
    temp_dir = get_temp_directory(context)
    temp_dir.mkdir(parents=True, exist_ok=True)
    current_ai_path = temp_dir / "current_ai.png"

    try:
        shutil.copy2(generation_path, current_ai_path)
        refresh_ai_image()
        print(f"[Style Engine] 📷 Loaded generation: {generation_path.name}")
    except Exception as e:
        print(f"[Style Engine] ❌ Failed to load generation: {e}")
        return False

    # ── Restore linked prompt sidecar (.txt) ─────────────────────────────────
    # Each generation image has a companion .txt file (same stem) saved at
    # generation time.  Restore it so the text editor always matches the image.
    sidecar = generation_path.with_suffix(".txt")
    if sidecar.exists():
        try:
            text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
            if not text_block:
                text_block = bpy.data.texts.new("STYLEENGINE_Prompt")
            with open(sidecar, 'r', encoding='utf-8') as f:
                content = f.read()
            text_block.clear()
            text_block.write(content)
            print(f"[Style Engine] 📖 Restored prompt from sidecar: {sidecar.name}")
        except Exception as e:
            print(f"[Style Engine] ⚠ Could not restore prompt sidecar: {e}")
    else:
        print(f"[Style Engine] ℹ No .txt sidecar for {generation_path.name} (pre-dates linked history)")
    # ─────────────────────────────────────────────────────────────────────────

    # ── Restore linked JSON sidecar (.json) ───────────────────────────────────
    # Each generation also has a companion .json file capturing the full Refine
    # Image form state at generation time.  Restore it so the panel fields stay
    # in sync with the image shown in the viewport.
    json_sidecar = generation_path.with_suffix(".json")
    if json_sidecar.exists():
        try:
            import json as _json
            with open(json_sidecar, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            p = context.scene.style_engine_props

            meta = data.get("metadata", {})
            p.refine_meta_filename   = meta.get("filename", "")
            p.refine_meta_dimensions = meta.get("dimensions", "")
            p.refine_meta_aspect     = meta.get("aspect_ratio", "")

            vs = data.get("visual_style", {})
            p.refine_style_art_style = vs.get("art_style", "")
            p.refine_style_medium    = vs.get("medium", "")
            p.refine_style_lighting  = vs.get("lighting_condition", "")

            comp = data.get("composition", {})
            p.refine_comp_perspective = comp.get("perspective", "")
            p.refine_comp_focal_point = comp.get("focal_point", "")

            p.refine_subjects.clear()
            for subj_data in data.get("subject_matter", []):
                subj = p.refine_subjects.add()
                subj.label    = subj_data.get("label", "object")
                subj.style    = subj_data.get("style", "")
                subj.scale    = subj_data.get("scale", "")
                subj.color    = subj_data.get("color", "")
                subj.material = subj_data.get("material", "")
                subj.show_expanded = False
                for feat_str in subj_data.get("features", []):
                    feat = subj.features.add()
                    feat.value = feat_str

            p.refine_tags.clear()
            for tag_str in data.get("thematic_tags", []):
                tag = p.refine_tags.add()
                tag.value = tag_str

            print(f"[Style Engine] 🔬 Restored JSON form from sidecar: {json_sidecar.name}")
        except Exception as e:
            print(f"[Style Engine] ⚠ Could not restore JSON sidecar: {e}")
    else:
        print(f"[Style Engine] ℹ No .json sidecar for {generation_path.name} (pre-dates linked history)")
    # ─────────────────────────────────────────────────────────────────────────

    return True


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
    
    # Fall back to a stable global path (no session ID) so asset directories
    # remain reachable across addon reloads even when the .blend is unsaved.
    import tempfile
    models_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "Models"
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


# ================================================================
#    Asset Mode Directory System
# ================================================================

def get_asset_directory(context, object_name):
    """
    Return the root directory for a specific asset's data.

    Structure: <project_lib>/Models/<object_name>/
    Falls back to a session-temp path if the .blend file is unsaved.
    """
    models_dir = get_models_directory(context)
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in object_name)
    asset_dir = models_dir / safe_name
    return asset_dir


def ensure_asset_directory(context, object_name, path_components=None):
    """
    Create the full directory tree for an asset.

    <project_lib>/Models/<object_name>/
        ├── temp/       - current_ai.png and working images
        ├── Images/     - timestamped Gemini renders (PNG + sidecars)
        ├── 3D/         - timestamped mesh files (GLB + sidecars)
        └── Text/       - prompt history (kept for completeness)

    If *path_components* is provided it is used instead of *object_name* to
    resolve a nested path, e.g. ["facade", "window"].
    """
    if path_components:
        asset_dir = get_nested_asset_directory(context, path_components)
    else:
        asset_dir = get_asset_directory(context, object_name)
    for subdir in ("temp", "Images", "3D", "Text"):
        (asset_dir / subdir).mkdir(parents=True, exist_ok=True)
    return asset_dir


def get_asset_temp_directory(context, object_name, path_components=None):
    """Return the temp/ subdirectory for an asset (holds current_ai.png).

    If *path_components* is provided it overrides *object_name* for nested assets.
    """
    if path_components:
        asset_dir = get_nested_asset_directory(context, path_components)
        for subdir in ("temp", "Images", "3D", "Text"):
            (asset_dir / subdir).mkdir(parents=True, exist_ok=True)
    else:
        asset_dir = ensure_asset_directory(context, object_name)
    return asset_dir / "temp"


def _safe_label(label):
    """Sanitise an asset label so it is safe to use as a directory name."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in label)


def get_nested_asset_directory(context, path_components):
    """Resolve the directory for an asset given its full ancestry chain.

    Examples:
        ["facade"]           → Models/facade/
        ["facade", "window"] → Models/facade/Nested/window/
        ["facade", "window", "pane"] → Models/facade/Nested/window/Nested/pane/
    """
    models_dir = get_models_directory(context)
    path = models_dir / _safe_label(path_components[0])
    for label in path_components[1:]:
        path = path / "Nested" / _safe_label(label)
    return path


def ensure_nested_asset_directory(context, path_components):
    """Create the full directory tree for a (potentially nested) asset."""
    asset_dir = get_nested_asset_directory(context, path_components)
    for subdir in ("temp", "Images", "3D", "Text"):
        (asset_dir / subdir).mkdir(parents=True, exist_ok=True)
    return asset_dir


def _read_image_aspect_and_size(image_path):
    """
    Read a PNG/JPEG's pixel dimensions and return (aspect_ratio_str, image_size_str)
    suitable for the NanoBananaAIO node's aspect_ratio / image_size inputs.

    aspect_ratio_str — simplified ratio e.g. "16:9", "1:1", "4:3"
    image_size_str   — Gemini size token: "1K" (≤1080p), "2K" (≤1440p), "4K" (larger)

    Falls back to ("1:1", "1K") on any error.
    """
    import struct as _struct
    from math import gcd as _gcd

    try:
        path = Path(image_path)
        w, h = None, None

        if path.suffix.lower() == '.png':
            with open(path, 'rb') as f:
                sig = f.read(8)
                if sig == b'\x89PNG\r\n\x1a\n':
                    f.read(4)                          # IHDR length field
                    if f.read(4) == b'IHDR':
                        w = _struct.unpack('>I', f.read(4))[0]
                        h = _struct.unpack('>I', f.read(4))[0]

        elif path.suffix.lower() in ('.jpg', '.jpeg'):
            with open(path, 'rb') as f:
                data = f.read(65536)                   # read enough for SOF marker
            i = 0
            while i < len(data) - 9:
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                if marker in (0xC0, 0xC2):             # SOF0 / SOF2
                    h = _struct.unpack('>H', data[i + 5:i + 7])[0]
                    w = _struct.unpack('>H', data[i + 7:i + 9])[0]
                    break
                seg_len = _struct.unpack('>H', data[i + 2:i + 4])[0]
                i += 2 + seg_len

        if w and h:
            # Snap to the nearest ratio the NanoBananaAIO node actually accepts.
            _VALID = {
                '1:1':  1.0,
                '2:3':  2/3,
                '3:2':  1.5,
                '3:4':  0.75,
                '4:3':  4/3,
                '4:5':  0.8,
                '5:4':  1.25,
                '9:16': 9/16,
                '16:9': 16/9,
                '21:9': 21/9,
            }
            actual = w / h
            aspect_str = min(_VALID, key=lambda k: abs(_VALID[k] - actual))

            long_edge = max(w, h)
            if long_edge <= 1080:
                size_str = "1K"
            elif long_edge <= 1440:
                size_str = "2K"
            else:
                size_str = "4K"

            return aspect_str, size_str

    except Exception as _e:
        print(f"[Style Engine] ⚠ Could not read image dimensions from {image_path}: {_e}")

    return "1:1", "1K"


def get_asset_path_components(props):
    """Return the full ancestry chain including the current asset.

    Scene mode         → []
    Depth 1 (facade)   → ["facade"]
    Depth 2 (window)   → ["facade", "window"]
    """
    try:
        stack   = json.loads(getattr(props, 'asset_mode_stack', '[]') or '[]')
        parents = [entry["asset_name"] for entry in stack]
    except Exception:
        parents = []
    name = getattr(props, 'current_asset_name', '')
    return parents + [name] if name else parents


def get_asset_3d_generation_list(context, object_name):
    """
    Return a sorted list of 3D mesh files saved for the given asset.

    Returns:
        list[Path]: .glb paths sorted chronologically (oldest → newest)
    """
    asset_dir = get_asset_directory(context, object_name)
    gen_3d_dir = asset_dir / "3D"
    if not gen_3d_dir.exists():
        return []
    meshes = list(gen_3d_dir.glob("*.glb")) + list(gen_3d_dir.glob("*.obj"))
    meshes.sort()
    return meshes


# ================================================================
#    Asset History Manifest
# ================================================================

def read_asset_history(context, asset_label):
    """
    Load the asset_history.json manifest for *asset_label*.

    Returns a dict of the form::

        {
            "active_index": 1,
            "iterations": [
                {"index": 0, "object_name": "windmill",
                 "mesh_file": null, "image_file": null},
                {"index": 1, "object_name": "windmill.001",
                 "mesh_file": "3D/20260320_001.glb",
                 "image_file": "Images/20260320_001.png"},
            ]
        }

    Returns a fresh empty manifest if the file is absent or unreadable.
    """
    asset_dir = get_asset_directory(context, asset_label)
    hist_path = asset_dir / "asset_history.json"
    if hist_path.exists():
        try:
            with open(hist_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Asset History] ⚠ Could not read {hist_path.name}: {e}")
    return {"active_index": 0, "iterations": []}


def write_asset_history(context, asset_label, history):
    """Persist the history manifest to disk (atomic write via temp file)."""
    asset_dir = ensure_asset_directory(context, asset_label)
    hist_path = asset_dir / "asset_history.json"
    tmp_path  = hist_path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        tmp_path.replace(hist_path)
    except Exception as e:
        print(f"[Asset History] ⚠ Could not write history: {e}")
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def _get_scene_subjects_json_path(scene=None):
    """Return Path to scene_subjects.json, or None if the project dir is unknown.

    This is the persistent disk backup of the top-level scene subjects,
    independent of the .blend file and of image generation sidecars.
    File: <project>_styleengine/scene_subjects.json

    Returns None for unsaved files so we never accidentally read/write a shared
    temp-dir file and bleed subjects between different unsaved sessions.
    """
    try:
        import bpy as _bpy
        _blend = _bpy.data.filepath
        if not _blend:
            # Unsaved project — no disk fallback; avoid polluting the shared temp dir
            return None
        _base = Path(_blend).stem
        _proj_dir = Path(_blend).parent / f"{_base}_styleengine"
        _proj_dir.mkdir(parents=True, exist_ok=True)
        return _proj_dir / "scene_subjects.json"
    except Exception:
        return None


def save_scene_subjects_json(context, subjects_json_str):
    """Persist the serialized scene subjects JSON to disk.

    Called at key moments (image generation, JSON analysis, manual edits)
    so the scene subjects survive a file saved in asset mode or a crash.
    File: <project>_styleengine/scene_subjects.json
    """
    path = _get_scene_subjects_json_path()
    if path is None:
        return
    tmp = path.with_suffix(".json.tmp")
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(subjects_json_str)
        tmp.replace(path)
        print(f"[Scene JSON] 💾 scene_subjects.json saved → {path.parent.name}/")
    except Exception as e:
        print(f"[Scene JSON] ⚠ Could not save scene_subjects.json: {e}")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass


def load_scene_subjects_json():
    """Return the saved scene subjects JSON string, or None if absent."""
    path = _get_scene_subjects_json_path()
    if path and path.exists():
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[Scene JSON] ⚠ Could not read scene_subjects.json: {e}")
    return None


def save_asset_subjects_json(context, asset_label, subjects_json_str,
                             path_components=None):
    """Persist the serialized subjects JSON for this asset to disk.

    File: Models/<asset_label>/asset_subjects.json  (or nested equivalent)
    *path_components* overrides the directory for nested assets.
    """
    asset_dir = ensure_asset_directory(context, asset_label,
                                       path_components=path_components)
    subjects_path = asset_dir / "asset_subjects.json"
    tmp_path = subjects_path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(subjects_json_str)
        tmp_path.replace(subjects_path)
        print(f"[Asset JSON] Saved subjects for '{asset_label}' → {subjects_path.name}")
    except Exception as e:
        print(f"[Asset JSON] ⚠ Could not save subjects: {e}")
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def load_asset_subjects_json(context, asset_label, path_components=None):
    """Return the saved subjects JSON string for this asset, or None if absent.

    *path_components* overrides the directory for nested assets.
    """
    if path_components:
        asset_dir = get_nested_asset_directory(context, path_components)
    else:
        asset_dir = get_asset_directory(context, asset_label)
    subjects_path = asset_dir / "asset_subjects.json"
    if subjects_path.exists():
        try:
            return subjects_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[Asset JSON] ⚠ Could not read subjects: {e}")
    return None


def save_asset_iteration_subjects_json(context, asset_label, iteration_index,
                                       subjects_json_str):
    """Save a subjects JSON snapshot alongside a specific history iteration.

    File: Models/<asset_label>/iter_<N>_subjects.json
    This is used to restore the JSON panel when browsing iteration history.
    """
    asset_dir = ensure_asset_directory(context, asset_label)
    iter_path = asset_dir / f"iter_{iteration_index:04d}_subjects.json"
    try:
        iter_path.write_text(subjects_json_str, encoding='utf-8')
        print(f"[Asset JSON] Saved iteration subjects → {iter_path.name}")
    except Exception as e:
        print(f"[Asset JSON] ⚠ Could not save iteration subjects: {e}")


def load_asset_iteration_subjects_json(context, asset_label, iteration_index):
    """Return the subjects JSON snapshot for a specific iteration, or None."""
    asset_dir = get_asset_directory(context, asset_label)
    iter_path = asset_dir / f"iter_{iteration_index:04d}_subjects.json"
    if iter_path.exists():
        try:
            return iter_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[Asset JSON] ⚠ Could not read iteration subjects: {e}")
    return None


def append_asset_history_iteration(context, asset_label, object_name,
                                   mesh_path=None, image_path=None):
    """
    Add a new iteration entry to the manifest and set it as active.

    *mesh_path* and *image_path* are absolute Paths (or None).  They are stored
    as paths relative to the asset directory so the manifest is portable.

    Returns the new active_index (int).
    """
    history   = read_asset_history(context, asset_label)
    asset_dir = get_asset_directory(context, asset_label)

    def _rel(p):
        if p is None:
            return None
        try:
            return str(Path(p).relative_to(asset_dir))
        except Exception:
            return str(p)

    new_index = len(history["iterations"])
    history["iterations"].append({
        "index":       new_index,
        "object_name": object_name,
        "mesh_file":   _rel(mesh_path),
        "image_file":  _rel(image_path),
    })
    history["active_index"] = new_index
    write_asset_history(context, asset_label, history)

    # Snapshot the current subjects JSON alongside this iteration so that
    # browsing back to it restores the panel state that existed when this
    # mesh was generated.
    try:
        from . import ui_panel as _up
        _props = context.scene.style_engine_props
        _json_str = _up._build_refine_json(_props)
        save_asset_iteration_subjects_json(context, asset_label, new_index, _json_str)
    except Exception as _je:
        print(f"[Asset History] ⚠ Could not snapshot subjects for iter {new_index}: {_je}")

    print(f"[Asset History] ✚ Iteration {new_index}: '{object_name}' "
          f"mesh={_rel(mesh_path)} image={_rel(image_path)}")
    return new_index


def update_asset_history_image(context, asset_label, image_path):
    """
    Fill in the image_file for the currently active iteration.
    Called after an asset image download completes.
    """
    history   = read_asset_history(context, asset_label)
    asset_dir = get_asset_directory(context, asset_label)
    active    = history.get("active_index", 0)
    iters     = history.get("iterations", [])

    def _rel(p):
        try:
            return str(Path(p).relative_to(asset_dir))
        except Exception:
            return str(p)

    if 0 <= active < len(iters):
        iters[active]["image_file"] = _rel(image_path)
        write_asset_history(context, asset_label, history)
        print(f"[Asset History] 🖼 Updated image for iteration {active}: {_rel(image_path)}")
    else:
        print(f"[Asset History] ⚠ No iteration {active} to update image for")


def get_asset_iteration_count(context, asset_label):
    """Return the number of saved iterations for the given asset label."""
    return len(read_asset_history(context, asset_label).get("iterations", []))


def save_asset_mesh_to_3d(context, asset_label, source_glb):
    """
    Save *source_glb* to Models/[asset_label]/3D/ with a timestamped name.
    Mirrors save_mesh_to_library but scoped to the per-asset directory.

    Returns the destination Path, or None on failure.
    """
    source_path = Path(source_glb)
    if not source_path.exists():
        print(f"[Asset History] ⚠ Source GLB not found: {source_path}")
        return None

    asset_dir  = ensure_asset_directory(context, asset_label)
    dir_3d     = asset_dir / "3D"
    dir_3d.mkdir(parents=True, exist_ok=True)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    ms  = datetime.now().microsecond // 1000
    dst = dir_3d / f"{ts}_{ms:03d}.glb"
    try:
        shutil.copy2(source_path, dst)
        print(f"[Asset History] 🧊 Saved asset mesh: {dst.name}")
        return dst
    except Exception as e:
        print(f"[Asset History] ❌ Failed to save asset mesh: {e}")
        return None


def switch_asset_iteration(context, asset_label, new_index, subject_index=-1):
    """
    Switch the visible mesh to the iteration at *new_index*, update
    linked_object_name / asset_object_links, copy the iteration's image
    to asset temp/current_ai.png, and refresh the camera background.

    subject_index — the props.refine_subjects index of the subject whose
    arrows were clicked.  Pass -1 (default) to fall back to label lookup.

    Returns True on success.
    """
    history = read_asset_history(context, asset_label)
    iters   = history.get("iterations", [])
    if not (0 <= new_index < len(iters)):
        print(f"[Asset History] ⚠ Index {new_index} out of range ({len(iters)} iterations)")
        return False

    old_index = history.get("active_index", 0)
    old_entry = iters[old_index] if 0 <= old_index < len(iters) else None
    new_entry = iters[new_index]

    asset_dir = get_asset_directory(context, asset_label)

    # Hide old mesh, show new mesh
    if old_entry and old_entry["object_name"] != new_entry["object_name"]:
        old_obj = bpy.data.objects.get(old_entry["object_name"])
        if old_obj:
            old_obj.hide_viewport = True
            old_obj.hide_render   = True

    new_obj = bpy.data.objects.get(new_entry["object_name"])
    if new_obj:
        new_obj.hide_viewport = False
        new_obj.hide_render   = False
        try:
            bpy.context.view_layer.objects.active = new_obj
        except Exception:
            pass

    # Update Blender property links
    try:
        props = bpy.context.scene.style_engine_props
        # Prefer the explicitly passed subject_index; fall back to searching
        # by label so callers that don't have the index still work.
        si = subject_index
        if not (0 <= si < len(props.refine_subjects)):
            # label-based fallback
            si = next(
                (i for i, s in enumerate(props.refine_subjects)
                 if s.label == asset_label),
                -1
            )
        if 0 <= si < len(props.refine_subjects):
            props.refine_subjects[si].linked_object_name = new_entry["object_name"]
        try:
            lm = json.loads(props.asset_object_links or "{}")
        except Exception:
            lm = {}
        lm[asset_label] = new_entry["object_name"]
        props.asset_object_links = json.dumps(lm)
        props.asset_current_3d_index = new_index
    except Exception as _e:
        print(f"[Asset History] ⚠ Could not update props: {_e}")

    # Update asset camera background image
    img_rel  = new_entry.get("image_file")
    img_path = (asset_dir / img_rel) if img_rel else None
    # Use the full ancestry chain so nested assets write to the right directory.
    try:
        _hist_props = bpy.context.scene.style_engine_props
        _hist_comps = get_asset_path_components(_hist_props)
    except Exception:
        _hist_comps = [asset_label]
    if _hist_comps and len(_hist_comps) > 1:
        asset_temp = get_nested_asset_directory(context, _hist_comps) / "temp"
        asset_temp.mkdir(parents=True, exist_ok=True)
    else:
        asset_temp = get_asset_temp_directory(context, asset_label)
    current_ai = asset_temp / "current_ai.png"
    if img_path and img_path.exists():
        try:
            shutil.copy2(img_path, current_ai)
        except Exception as _e:
            print(f"[Asset History] ⚠ Could not copy image: {_e}")
    else:
        print(f"[Asset History] ℹ No image for iteration {new_index}")

    refresh_asset_camera_image(asset_label, path_components=_hist_comps)

    # Restore the subjects JSON that was snapshotted when this iteration was created.
    # ONLY do this when we are already inside asset mode — the snapshot contains the
    # asset's components, not the scene subject list.  Calling _populate_refine_from_json
    # from scene mode would wipe all scene subjects and then re-trigger sync.
    try:
        _props_check = bpy.context.scene.style_engine_props
        if getattr(_props_check, 'asset_mode', False):
            _iter_json = load_asset_iteration_subjects_json(context, asset_label, new_index)
            if _iter_json:
                from . import ui_panel as _up
                _up._populate_refine_from_json(_props_check, _iter_json)
                print(f"[Asset History] Restored subjects JSON for iteration {new_index}")
            else:
                _asset_json = load_asset_subjects_json(context, asset_label)
                if _asset_json:
                    from . import ui_panel as _up
                    _up._populate_refine_from_json(_props_check, _asset_json)
                    print(f"[Asset History] Restored asset subjects JSON (no iter snapshot)")
        else:
            print(f"[Asset History] Scene mode — skipping subjects JSON restore "
                  f"(mesh swap only) for iteration {new_index}")
    except Exception as _je:
        print(f"[Asset History] ⚠ Could not restore subjects JSON: {_je}")

    # Persist the new active_index
    history["active_index"] = new_index
    write_asset_history(context, asset_label, history)

    print(f"[Asset History] ◀▶ Switched to iteration {new_index}: '{new_entry['object_name']}'")
    return True


def save_asset_image_to_library(context, object_name, source_image_path):
    """
    Save a Gemini/AI image generated while in Asset Mode to the asset's
    Images/ folder (same sidecar pattern as save_generation_to_library).

    Returns:
        Path or None: Path to saved image, or None on failure.
    """
    asset_dir = ensure_asset_directory(context, object_name)
    images_dir = asset_dir / "Images"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ms = datetime.now().microsecond // 1000
    try:
        w = context.scene.render.resolution_x
        h = context.scene.render.resolution_y
    except Exception:
        w, h = 1024, 1024
    filename = f"{timestamp}_{ms:03d}_asset_{w}x{h}.png"
    dest_path = images_dir / filename

    try:
        shutil.copy2(source_image_path, dest_path)
        print(f"[Asset Mode] 💾 Saved asset image: {filename}")
    except Exception as e:
        print(f"[Asset Mode] ❌ Failed to save asset image: {e}")
        return None

    # Prompt sidecar (.txt)
    try:
        text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
        if text_block:
            content = text_block.as_string().strip()
            if content:
                with open(dest_path.with_suffix(".txt"), 'w', encoding='utf-8') as f:
                    f.write(content)
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not save prompt sidecar: {e}")

    # JSON form sidecar (.json)
    try:
        import json as _json
        p = context.scene.style_engine_props
        subjects = []
        for subj in p.refine_subjects:
            features = [feat.value for feat in subj.features if feat.value.strip()]
            subjects.append({
                "label": subj.label, "style": subj.style,
                "scale": subj.scale, "color": subj.color,
                "material": subj.material, "features": features,
            })
        tags = [t.value for t in p.refine_tags if t.value.strip()]
        refine_data = {
            "metadata": {
                "filename": p.refine_meta_filename,
                "dimensions": p.refine_meta_dimensions,
                "aspect_ratio": p.refine_meta_aspect,
            },
            "visual_style": {
                "art_style": p.refine_style_art_style,
                "medium": p.refine_style_medium,
                "lighting_condition": p.refine_style_lighting,
            },
            "composition": {
                "perspective": p.refine_comp_perspective,
                "focal_point": p.refine_comp_focal_point,
            },
            "subject_matter": subjects,
            "thematic_tags": tags,
        }
        has_content = any([
            p.refine_meta_filename, p.refine_style_art_style,
            p.refine_style_medium, p.refine_comp_perspective,
            subjects, tags,
        ])
        if has_content:
            with open(dest_path.with_suffix(".json"), 'w', encoding='utf-8') as f:
                _json.dump(refine_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not save JSON sidecar: {e}")

    return dest_path


def load_asset_generation_to_current(context, object_name, generation_path):
    """
    Load a specific asset 3D-generation's associated image into the asset's
    current_ai.png and restore the prompt + JSON sidecars.

    Isolation remains intact — does NOT unhide scene objects.

    Returns:
        bool: True if successful.
    """
    if not generation_path.exists():
        print(f"[Asset Mode] ⚠ Generation not found: {generation_path}")
        return False

    asset_temp = get_asset_temp_directory(context, object_name)
    asset_temp.mkdir(parents=True, exist_ok=True)
    current_ai_path = asset_temp / "current_ai.png"

    # Load image sidecar (same stem, .png extension in Images/)
    img_sidecar = generation_path.with_suffix(".png")
    if img_sidecar.exists():
        try:
            shutil.copy2(img_sidecar, current_ai_path)
            refresh_ai_image()
            print(f"[Asset Mode] 📷 Loaded asset image: {img_sidecar.name}")
        except Exception as e:
            print(f"[Asset Mode] ❌ Failed to load asset image: {e}")
    else:
        print(f"[Asset Mode] ℹ No image sidecar for {generation_path.name}")

    # Prompt sidecar (.txt)
    txt_sidecar = generation_path.with_suffix(".txt")
    if txt_sidecar.exists():
        try:
            text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
            if not text_block:
                text_block = bpy.data.texts.new("STYLEENGINE_Prompt")
            with open(txt_sidecar, 'r', encoding='utf-8') as f:
                text_block.clear()
                text_block.write(f.read())
            print(f"[Asset Mode] 📖 Restored prompt from sidecar")
        except Exception as e:
            print(f"[Asset Mode] ⚠ Could not restore prompt sidecar: {e}")

    # JSON form sidecar (.json)
    json_sidecar = generation_path.with_suffix(".json")
    if json_sidecar.exists():
        try:
            import json as _json
            with open(json_sidecar, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            p = context.scene.style_engine_props
            meta = data.get("metadata", {})
            p.refine_meta_filename   = meta.get("filename", "")
            p.refine_meta_dimensions = meta.get("dimensions", "")
            p.refine_meta_aspect     = meta.get("aspect_ratio", "")
            vs = data.get("visual_style", {})
            p.refine_style_art_style = vs.get("art_style", "")
            p.refine_style_medium    = vs.get("medium", "")
            p.refine_style_lighting  = vs.get("lighting_condition", "")
            comp = data.get("composition", {})
            p.refine_comp_perspective = comp.get("perspective", "")
            p.refine_comp_focal_point = comp.get("focal_point", "")
            p.refine_subjects.clear()
            for sd in data.get("subject_matter", []):
                subj = p.refine_subjects.add()
                subj.label = sd.get("label", "object")
                subj.style = sd.get("style", "")
                subj.scale = sd.get("scale", "")
                subj.color = sd.get("color", "")
                subj.material = sd.get("material", "")
                subj.show_expanded = False
                for feat_str in sd.get("features", []):
                    feat = subj.features.add()
                    feat.value = feat_str
            p.refine_tags.clear()
            for tag_str in data.get("thematic_tags", []):
                tag = p.refine_tags.add()
                tag.value = tag_str
            print(f"[Asset Mode] 🔬 Restored JSON form from sidecar")
        except Exception as e:
            print(f"[Asset Mode] ⚠ Could not restore JSON sidecar: {e}")

    return True


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
    Save a generated 3D mesh to the project library.

    In Asset Mode the mesh is saved to the asset's own 3D/ directory
    (Models/[asset_label]/3D/) instead of the global Models/ folder.
    Returns the destination Path, or None on failure.
    """
    source_path = Path(source_mesh_path)

    if not source_path.exists():
        print(f"[Style Engine] ⚠️ Mesh file not found: {source_path}")
        return None

    # Redirect to per-asset directory when in Asset Mode
    try:
        _props = bpy.context.scene.style_engine_props
        if _props.asset_mode and _props.current_asset_name:
            return save_asset_mesh_to_3d(context, _props.current_asset_name, source_path)
    except Exception:
        pass

    # Global fallback
    models_dir = get_models_directory(context)
    models_dir.mkdir(parents=True, exist_ok=True)

    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    microseconds = datetime.now().microsecond // 1000
    filename     = f"{timestamp}_{microseconds:03d}_{mesh_type}.glb"
    dest_path    = models_dir / filename

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
    # In Asset Mode, redirect saves to the asset's own Images/ folder so
    # the scene library stays clean and unaffected by asset iterations.
    try:
        _props = context.scene.style_engine_props
        if getattr(_props, 'asset_mode', False):
            asset_name = getattr(_props, 'current_asset_name', '')
            if asset_name:
                return save_asset_image_to_library(context, asset_name, source_image_path)
    except Exception as _e:
        print(f"[Style Engine] ⚠ Asset mode redirect check failed: {_e}")

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

    # ── Prompt sidecar (.txt) ────────────────────────────────────────────────
    # Save the current STYLEENGINE_Prompt alongside the image so that
    # navigating back to this generation via the Generation Browser will also
    # restore the exact prompt that was active at generation time.
    sidecar_path = dest_path.with_suffix(".txt")
    try:
        text_block = bpy.data.texts.get("STYLEENGINE_Prompt")
        if text_block:
            prompt_content = text_block.as_string().strip()
            if prompt_content:
                with open(sidecar_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_content)
                print(f"[Style Engine] 📝 Saved prompt sidecar: {sidecar_path.name}")
            else:
                print("[Style Engine] ⚠ Prompt empty — no .txt sidecar saved for this generation")
        else:
            print("[Style Engine] ⚠ STYLEENGINE_Prompt not found — no .txt sidecar saved")
    except Exception as e:
        print(f"[Style Engine] ⚠ Could not save prompt sidecar: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    # ── Refine Image JSON sidecar (.json) ────────────────────────────────────
    # Serialise every field of the Refine Image panel form so it can be
    # restored verbatim when the user navigates back to this generation.
    json_sidecar_path = dest_path.with_suffix(".json")
    try:
        import json as _json
        p = context.scene.style_engine_props
        subjects = []
        for subj in p.refine_subjects:
            features = [f.value for f in subj.features if f.value.strip()]
            subjects.append({
                "label":    subj.label,
                "style":    subj.style,
                "scale":    subj.scale,
                "color":    subj.color,
                "material": subj.material,
                "features": features,
            })
        tags = [t.value for t in p.refine_tags if t.value.strip()]
        refine_data = {
            "metadata": {
                "filename":    p.refine_meta_filename,
                "dimensions":  p.refine_meta_dimensions,
                "aspect_ratio": p.refine_meta_aspect,
            },
            "visual_style": {
                "art_style":         p.refine_style_art_style,
                "medium":            p.refine_style_medium,
                "lighting_condition": p.refine_style_lighting,
            },
            "composition": {
                "perspective": p.refine_comp_perspective,
                "focal_point": p.refine_comp_focal_point,
            },
            "subject_matter": subjects,
            "thematic_tags":  tags,
        }
        has_content = any([
            p.refine_meta_filename,
            p.refine_style_art_style,
            p.refine_style_medium,
            p.refine_comp_perspective,
            subjects,
            tags,
        ])
        if has_content:
            with open(json_sidecar_path, 'w', encoding='utf-8') as f:
                _json.dump(refine_data, f, indent=2, ensure_ascii=False)
            print(f"[Style Engine] 🔬 Saved JSON sidecar: {json_sidecar_path.name}")
            # Also update the standalone scene_subjects.json backup (scene mode only)
            if not getattr(context.scene.style_engine_props, 'asset_mode', False):
                try:
                    save_scene_subjects_json(context, _json.dumps(refine_data, indent=2))
                except Exception:
                    pass
        else:
            print("[Style Engine] ⚠ Refine Image form empty — no .json sidecar saved")
    except Exception as e:
        print(f"[Style Engine] ⚠ Could not save JSON sidecar: {e}")
    # ─────────────────────────────────────────────────────────────────────────

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

def get_active_ai_output_path(context=None):
    """
    Return the path where the CURRENT generation's output image should be written.

    In Asset Mode  → <project>/Models/<asset_name>/temp/current_ai.png
    Otherwise      → <scene_temp>/current_ai.png  (the global canonical path)

    Using this instead of get_temp_directory()/"current_ai.png" directly in the
    download callbacks ensures Asset Mode renders never touch the global image.
    """
    try:
        ctx   = context or bpy.context
        props = ctx.scene.style_engine_props
        if getattr(props, 'asset_mode', False):
            components = get_asset_path_components(props)
            if components:
                asset_temp = get_nested_asset_directory(ctx, components) / "temp"
                asset_temp.mkdir(parents=True, exist_ok=True)
                return asset_temp / "current_ai.png"
    except Exception as _e:
        print(f"[Style Engine] ⚠ get_active_ai_output_path fallback: {_e}")
    return get_temp_directory(context) / "current_ai.png"


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

    # If already locked, verify it still belongs to the current .blend file.
    # A mismatch means the user opened a different file without triggering load_post
    # (e.g. command-line, drag-and-drop edge cases).  Reset and migrate below.
    if _session_temp_dir is not None:
        if bpy.data.is_saved:
            current_project_lib = get_project_library(context)
            if current_project_lib:
                expected_temp = current_project_lib / "temp"
                if _session_temp_dir != expected_temp:
                    print(
                        f"[Style Engine] ⚠ Temp dir mismatch — resetting "
                        f"({_session_temp_dir} → {expected_temp})"
                    )
                    old_dir = _session_temp_dir
                    _session_temp_dir = None
                    # Migrate working files to the correct project location
                    try:
                        _migrate_working_files(old_dir, expected_temp)
                        _migrate_working_files(_get_system_temp_dir(), expected_temp)
                    except Exception:
                        pass
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
    Reset temp directory lock (called when setting up new workspace or loading a new file).
    Allows the path to be re-determined based on the current .blend save state.
    """
    global _session_temp_dir
    old_path = _session_temp_dir
    _session_temp_dir = None
    if old_path:
        print(f"[Style Engine] 🔓 Temp directory unlocked (was: {old_path})")


# Working files that live in the temp directory and must follow it when the
# project changes.  current_ai.png is the most critical — it is what all
# "Analyze / Describe / Refine" operators look for.
_WORKING_FILES = ["current_ai.png", "canny.png", "depth.png", "combined.jpg"]


def _migrate_working_files(source_dir, dest_dir):
    """
    Copy _WORKING_FILES from source_dir to dest_dir, but only when the source
    file is newer than (or absent from) the destination.  Safe to call even if
    source_dir does not exist.
    """
    if not source_dir:
        return
    source_dir = Path(source_dir)
    dest_dir   = Path(dest_dir)
    if not source_dir.exists():
        return
    dest_dir.mkdir(parents=True, exist_ok=True)

    import os
    moved = []
    for fname in _WORKING_FILES:
        src = source_dir / fname
        dst = dest_dir   / fname
        if not src.exists():
            continue
        try:
            if not dst.exists() or os.path.getmtime(src) > os.path.getmtime(dst):
                shutil.copy2(src, dst)
                moved.append(fname)
        except Exception as e:
            print(f"[Style Engine] ⚠ Could not migrate {fname}: {e}")

    if moved:
        print(f"[Style Engine] 📦 Migrated {moved}  {source_dir} → {dest_dir}")


def _get_system_temp_dir():
    """Return the legacy system-temp fallback path (never raises)."""
    import tempfile
    return Path(tempfile.gettempdir()) / "blender_styleengine" / "temp"


def find_current_ai(context):
    """
    Locate current_ai.png, trying the project temp first then all known fallbacks.
    If the file is found in a fallback location it is automatically copied to the
    canonical project temp so future lookups succeed.

    Returns:
        Path  — the resolved path where the file now exists
        None  — file could not be found anywhere
    """
    canonical_dir = get_temp_directory(context)
    canonical     = canonical_dir / "current_ai.png"

    if canonical.exists():
        return canonical

    # Search fallback locations
    candidates = [
        _get_system_temp_dir() / "current_ai.png",
    ]
    # Also check the project library root (old migration put it there)
    proj_lib = get_project_library(context)
    if proj_lib:
        candidates.append(proj_lib / "current_ai.png")

    for candidate in candidates:
        if candidate.exists():
            print(f"[Style Engine] 📎 current_ai.png found at fallback: {candidate}")
            try:
                canonical_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, canonical)
                print(f"[Style Engine] ✓ Copied to canonical path: {canonical}")
            except Exception as e:
                print(f"[Style Engine] ⚠ Could not copy to canonical path: {e}")
                return candidate   # Return fallback path if copy fails
            return canonical

    return None


@persistent
def on_blend_file_pre_save(dummy):
    """
    Handler called by bpy.app.handlers.save_pre immediately before every .blend
    write.  Ensures scene_subjects_json captures the correct subjects regardless
    of whether the user is saving from scene mode or asset mode.

    In scene mode  → build fresh from live refine_subjects collection.
    In asset mode  → use asset_prev_subjects (the scene-level snapshot saved on
                     asset-mode entry), because refine_subjects currently holds
                     the asset's components, not the scene subjects.
    """
    for scene in bpy.data.scenes:
        if not hasattr(scene, 'style_engine_props'):
            continue
        props = scene.style_engine_props
        try:
            from . import ui_panel as _up
            if getattr(props, 'asset_mode', False):
                # Saving while in asset mode — preserve the scene-level snapshot
                if getattr(props, 'asset_prev_subjects', ''):
                    props.scene_subjects_json = props.asset_prev_subjects
                    print("[Style Engine] 💾 pre-save: scene_subjects_json ← asset_prev_subjects")
            else:
                # Saving in scene mode — build from live collection
                if len(props.refine_subjects) > 0:
                    props.scene_subjects_json = _up._build_refine_json(props)
                    print("[Style Engine] 💾 pre-save: scene_subjects_json updated from live subjects")
        except Exception as _e:
            print(f"[Style Engine] ⚠ pre-save subjects snapshot failed: {_e}")


@persistent
def on_blend_file_loaded(dummy):
    """
    Handler called by bpy.app.handlers.load_post after every file load
    (File > Open, File > Recent, drag-and-drop, etc.).

    Decorated with @persistent so Blender does NOT clear it when a new
    file is opened — without this the handler would be removed before
    load_post fires and would never run.

    1. Saves the old temp-dir path before clearing the lock.
    2. Resets the lock so get_temp_directory() re-evaluates for the new file.
    3. Migrates working files (current_ai.png etc.) from the old location.
    4. Schedules a deferred asset-mode reset via a timer (bpy.context is not
       fully valid inside load_post on all Blender versions).
    """
    global _session_id, _session_temp_dir

    old_temp = _session_temp_dir        # remember before resetting
    reset_temp_directory()
    _session_id = None

    try:
        new_temp = get_temp_directory(bpy.context)

        # Migrate from wherever the old session wrote files
        if old_temp and Path(old_temp) != new_temp:
            _migrate_working_files(old_temp, new_temp)

        # Always also check the system-temp fallback — covers the case where
        # the session was locked there before the .blend file was first saved
        sys_temp = _get_system_temp_dir()
        if sys_temp != new_temp:
            _migrate_working_files(sys_temp, new_temp)

        # Delete any stale scene_subjects.json left in the global system-temp dir.
        # This file is now only written to project folders (never to sys_temp),
        # so any copy there is from an old version and would bleed into new sessions.
        _stale_ssj = sys_temp / "scene_subjects.json"
        try:
            if _stale_ssj.exists():
                _stale_ssj.unlink()
                print("[Style Engine] 🧹 Removed stale scene_subjects.json from temp dir")
        except Exception:
            pass

        print(f"[Style Engine] 🔄 File loaded — temp dir now: {new_temp}")
    except Exception as e:
        print(f"[Style Engine] ⚠ on_blend_file_loaded migration error: {e}")

    try:
        from . import hub_client
        prefs      = bpy.context.preferences.addons["styleengine"].preferences
        hub_url    = getattr(prefs, "hub_url", "http://127.0.0.1:8000").rstrip("/")
        session_id = hub_client.get_session_id(bpy.data.filepath if bpy.data.is_saved else None)
        blend_name = Path(bpy.data.filepath).stem if bpy.data.is_saved else session_id
        current_ai = str(get_active_ai_output_path(bpy.context))
        hub_client.register_session(hub_url, session_id, blend_name, bpy.data.filepath, current_ai)
        print(f"[Style Engine] Hub re-registered session on load: {session_id!r}")
    except Exception as e:
        print(f"[Style Engine] Hub re-register on load failed: {e}")

    # Defer the restore to the next main-loop tick.
    # bpy.context.scene is not guaranteed to be valid inside load_post on all
    # Blender 4.x builds; iterating bpy.data.scenes in a timer is always safe.
    # Because all asset-mode properties are now SKIP_SAVE, asset_mode is always
    # False on load — no mode-detection or complex branching is needed here.
    def _deferred_restore():
        try:
            from . import ui_panel as _up
            for scene in bpy.data.scenes:
                if not hasattr(scene, 'style_engine_props'):
                    continue
                props = scene.style_engine_props

                # ── 0. Unconditionally clear ALL mode-state properties.
                #    SKIP_SAVE prevents writing them, but old .blend files may still
                #    have the values saved from before the SKIP_SAVE fix was applied.
                #    We force-reset here so the N-panel always comes up in scene mode.

                # Restore render resolution FIRST, before clearing the saved values.
                # asset_prev_resolution_x/y are PERSISTENT (no SKIP_SAVE) so they
                # survive file saves — a non-zero value means the file was saved while
                # in asset mode and the scene resolution needs to be recovered.
                _rx = getattr(props, 'asset_prev_resolution_x', 0)
                _ry = getattr(props, 'asset_prev_resolution_y', 0)
                if _rx > 0 and _ry > 0:
                    scene.render.resolution_x = _rx
                    scene.render.resolution_y = _ry
                    print(f"[Style Engine] 📐 Restored render resolution → {_rx}×{_ry}")

                props.asset_mode              = False
                props.current_asset_name      = ""
                props.asset_mode_stack        = "[]"
                props.asset_mode_depth        = 0
                props.asset_prev_subjects     = ""
                props.asset_prev_camera       = ""
                props.asset_current_3d_index  = 0
                props.asset_prev_resolution_x = 0   # 0 = "nothing to restore"
                props.asset_prev_resolution_y = 0
                props.asset_prev_prompt       = ""
                props.asset_subject_index     = -1
                props.asset_subject_style     = ""
                props.asset_subject_scale     = ""
                props.asset_subject_color     = ""
                props.asset_subject_material  = ""
                try:
                    props.asset_subject_features.clear()
                except Exception:
                    pass

                # ── 1. Restore visibility if file was saved during asset isolation.
                #    asset_stored_visibility is PERSISTENT so it survives the save.
                vis_json = getattr(props, 'asset_stored_visibility', '')
                if vis_json:
                    try:
                        for obj_name, hv_hr in json.loads(vis_json).items():
                            obj = bpy.data.objects.get(obj_name)
                            if obj:
                                obj.hide_viewport, obj.hide_render = hv_hr
                    except Exception:
                        for obj in bpy.data.objects:
                            obj.hide_viewport = False
                            obj.hide_render   = False
                    props.asset_stored_visibility = ""  # consumed, clear it

                # ── 2. Restore active camera if an asset camera is currently active.
                if scene.camera and scene.camera.name.startswith("asset_camera_"):
                    ai_cam = bpy.data.objects.get("ai_camera")
                    if ai_cam:
                        scene.camera = ai_cam
                        print(f"[Style Engine] 📷 Restored active camera → 'ai_camera'")

                # ── 3. Hide all asset cameras from the viewport.
                for obj in bpy.data.objects:
                    if obj.type == 'CAMERA' and obj.name.startswith("asset_camera_"):
                        obj.hide_viewport = True

                # ── 4. Repopulate refine_subjects.
                #    Priority: scene_subjects_json (in .blend) → scene_subjects.json on disk.
                json_str = getattr(props, 'scene_subjects_json', '')
                if not json_str:
                    json_str = load_scene_subjects_json() or ''
                if json_str:
                    try:
                        _up._populate_refine_from_json(props, json_str)
                        print("[Style Engine] ✅ Scene subjects restored on file load")
                    except Exception as _pe:
                        print(f"[Style Engine] ⚠ Subject restore failed: {_pe}")
                else:
                    print("[Style Engine] ℹ No scene subjects found to restore")

        except Exception as _e:
            print(f"[Style Engine] ⚠ deferred restore failed: {_e}")
            import traceback as _tb; _tb.print_exc()
        return None  # unregister the timer

    bpy.app.timers.register(_deferred_restore, first_interval=0.2)

    # Ensure all asset cameras in this .blend are hidden from the viewport.
    # Cameras created before the hide_viewport fix will be corrected here.
    try:
        hidden = 0
        for obj in bpy.data.objects:
            if obj.type == 'CAMERA' and obj.name.startswith("asset_camera_"):
                if not obj.hide_viewport:
                    obj.hide_viewport = True
                    hidden += 1
        if hidden:
            print(f"[Style Engine] 🔒 Hidden {hidden} pre-existing asset camera(s) from viewport")
    except Exception as _ce:
        print(f"[Style Engine] ⚠ Could not hide asset cameras on load: {_ce}")

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
            "prompt_llm_profile": props.prompt_llm_profile if hasattr(props, "prompt_llm_profile") else "DEFAULT",
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
                "preview_out": str(get_active_ai_output_path(context)).replace("\\", "/"),
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


def _asset_datablock_name(name_or_components):
    """Unique Blender image-datablock name for an asset's camera background.

    Accepts either a plain string (leaf name) or a list of path components
    (full ancestry chain) so nested assets get distinct datablock names
    and never collide with siblings that share a leaf label.
    Keeps it distinct from the scene's 'current_ai.png' to prevent Blender
    auto-suffixing it '.001'.
    """
    if isinstance(name_or_components, list):
        raw = "_".join(name_or_components)
    else:
        raw = name_or_components
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)
    return f"current_ai_{safe}"


def create_asset_placeholder_image(context, object_name, path_components=None):
    """
    Create a fresh 1024×1024 black PNG at <asset_temp>/current_ai.png and
    load it as a named Blender image datablock.

    Called once when entering Asset Mode so the asset camera background slot
    always has a real on-disk file, exactly mirroring what the ai_camera
    setup does for the global current_ai.png.

    *path_components* is the full ancestry chain (e.g. ["gollum", "trinkets"]).
    When provided, the nested directory is used instead of the flat Models dir.

    Returns the Path to the created file.
    """
    if path_components and len(path_components) > 1:
        asset_temp = get_nested_asset_directory(context, path_components) / "temp"
        asset_temp.mkdir(parents=True, exist_ok=True)
    else:
        asset_temp = get_asset_temp_directory(context, object_name)
        asset_temp.mkdir(parents=True, exist_ok=True)
    img_path  = asset_temp / "current_ai.png"
    db_name   = _asset_datablock_name(path_components if path_components else object_name)

    # Remove stale datablock (name conflict or wrong filepath)
    if db_name in bpy.data.images:
        existing = bpy.data.images[db_name]
        try:
            bpy.data.images.remove(existing)
        except Exception:
            pass

    # Create fresh 1024×1024 black image and save to disk
    img = bpy.data.images.new(db_name, width=1024, height=1024)
    img.pixels = [0.0, 0.0, 0.0, 1.0] * (1024 * 1024)
    img.filepath_raw = str(img_path)
    img.file_format  = 'PNG'
    img.save()

    print(f"[Asset Mode] 🖤 Created asset placeholder: {img_path}")
    return img_path


def setup_asset_camera_background(context, object_name, cam_obj,
                                   path_components=None):
    """
    Set up (or refresh) the background image on an asset camera.

    Uses a unique datablock name (<current_ai_{safe_name}>) so the asset image
    never clashes with the scene's 'current_ai.png' datablock and Blender
    never auto-renames it '.001'.

    *path_components* is the full ancestry chain (e.g. ["gollum", "trinkets"]).
    When provided it is used for both the directory path and the datablock name
    so nested assets resolve to their own subdirectory and datablock.

    Expects create_asset_placeholder_image() to have been called first (during
    EnterAssetMode) so the file always exists on disk at entry time.
    """
    if path_components and len(path_components) > 1:
        asset_temp = get_nested_asset_directory(context, path_components) / "temp"
        asset_temp.mkdir(parents=True, exist_ok=True)
    else:
        asset_temp = get_asset_temp_directory(context, object_name)
        asset_temp.mkdir(parents=True, exist_ok=True)
    img_path  = asset_temp / "current_ai.png"
    canonical = str(img_path)
    db_name   = _asset_datablock_name(path_components if path_components else object_name)

    cam_data = cam_obj.data
    cam_data.show_background_images = True
    cam_data.passepartout_alpha      = 1.0

    if len(cam_data.background_images) > 0:
        bg = cam_data.background_images[0]
    else:
        bg = cam_data.background_images.new()

    # If the slot already holds this asset's datablock, just reload it.
    if bg.image is not None and bg.image.name == db_name:
        bg.image.filepath_raw = canonical
        bg.image.reload()
        bg.image.update()
        img = bg.image
    elif db_name in bpy.data.images:
        img = bpy.data.images[db_name]
        img.filepath_raw = canonical
        img.reload()
        img.update()
        bg.image = img
    else:
        # First call after entering asset mode — file was just created by
        # create_asset_placeholder_image(), load it with the unique name.
        if img_path.exists():
            img = bpy.data.images.load(canonical, check_existing=False)
            img.name = db_name
        else:
            # Fallback: create placeholder in-memory if file somehow missing
            img = bpy.data.images.new(db_name, width=1024, height=1024)
            img.pixels = [0.0, 0.0, 0.0, 1.0] * (1024 * 1024)
            img.filepath_raw = canonical
            img.file_format  = 'PNG'
            img.save()
        bg.image = img

    bg.alpha         = 1.0
    bg.display_depth = 'FRONT'
    bg.frame_method  = 'STRETCH'
    print(f"[Asset Mode] ✓ Asset camera background set: {db_name} → {img_path.name}")


def refresh_asset_camera_image(object_name, path_components=None):
    """
    Reload the asset camera background from the asset's own temp/current_ai.png.

    *path_components* is the full ancestry chain (e.g. ["gollum", "trinkets"]).
    When provided it is used to build the full camera name (e.g.
    asset_camera_gollum_trinkets) so nested cameras are found correctly.

    The download callbacks write directly to the asset temp via
    get_active_ai_output_path, so no copy from global temp is needed here.
    """
    try:
        ctx = bpy.context
        name_key = path_components if path_components else object_name
        if isinstance(name_key, list):
            safe = "".join(
                c if c.isalnum() or c in "-_" else "_"
                for c in "_".join(name_key)
            )
        else:
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name_key)
        cam_name = f"asset_camera_{safe}"
        cam_obj  = bpy.data.objects.get(cam_name)
        if cam_obj:
            setup_asset_camera_background(ctx, object_name, cam_obj,
                                          path_components=path_components)
        else:
            print(f"[Asset Mode] ⚠ Asset camera '{cam_name}' not found in scene")

    except Exception as e:
        print(f"[Asset Mode] ❌ refresh_asset_camera_image failed: {e}")


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

    In Asset Mode this function delegates entirely to refresh_asset_camera_image()
    so the global 'current_ai.png' datablock is NEVER touched by asset renders.

    Robust against:
    - filepath_raw drifting after a temp-dir move (re-asserts the canonical path)
    - datablock being lost after Undo or manual deletion (re-creates and re-attaches)
    - GPU texture not invalidating (calls img.update() after reload)
    """
    try:
        # ── Asset Mode: update only the asset camera, leave global image alone ──
        try:
            props = bpy.context.scene.style_engine_props
            if getattr(props, 'asset_mode', False):
                asset_name = getattr(props, 'current_asset_name', '')
                if asset_name:
                    _comps = get_asset_path_components(props)
                    refresh_asset_camera_image(asset_name,
                                               path_components=_comps if _comps else None)
                return  # global current_ai.png must not be touched
        except Exception as _ae:
            print(f"[Asset Mode] ⚠ asset camera refresh skipped: {_ae}")

        # ── Scene Mode: update the global current_ai.png datablock ──────────
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

            if img.source != 'FILE':
                # The placeholder was created with images.new() (source='GENERATED').
                # Changing source and calling reload() leaves the GPU in an uncertain
                # state. The only reliable path is: remove the generated datablock,
                # load fresh from disk (always FILE-sourced), and re-attach.
                print("[Style Engine] ↩ Placeholder was GENERATED — replacing with FILE datablock")
                bpy.data.images.remove(img)
                img = bpy.data.images.load(canonical, check_existing=False)
                img.name = "current_ai.png"
                img.filepath_raw = canonical
                img.update()
                _reattach_camera_background(img)
            else:
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

    # ── Asset Mode guard ────────────────────────────────────────────────────
    # In Asset Mode the scene camera is managed exclusively by EnterAssetMode /
    # ExitAssetMode.  Overriding it here would silently undo the camera switch.
    try:
        if getattr(context.scene.style_engine_props, 'asset_mode', False):
            print(f"[Gemini] ⏭ sync_ai_camera_from_scene skipped — Asset Mode active "
                  f"(scene.camera = {context.scene.camera.name if context.scene.camera else 'None'})")
            return False
    except Exception:
        pass
    # ────────────────────────────────────────────────────────────────────────

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
    original_camera = scene.camera
    print(f"[Render] render_from_camera_safe: render_cam='{camera.name}'  "
          f"scene.camera before='{original_camera.name if original_camera else 'None'}'")

    try:
        # Temporarily set camera ONLY for this render
        scene.camera = camera
        bpy.ops.render.render(write_still=True, use_viewport=False)

    finally:
        # IMMEDIATELY restore original camera (even if render failed)
        scene.camera = original_camera
        print(f"[Render] render_from_camera_safe: scene.camera restored → "
              f"'{original_camera.name if original_camera else 'None'}'")


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
    scene = context.scene

    # In Asset Mode render from the dedicated asset camera so the isolated
    # object (not the full scene) is what gets sent to Gemini as the input.
    _asset_props = getattr(scene, 'style_engine_props', None)
    _in_asset_mode = getattr(_asset_props, 'asset_mode', False)
    if _in_asset_mode:
        _asset_name = getattr(_asset_props, 'current_asset_name', '')
        _render_comps = get_asset_path_components(_asset_props)
        _render_key   = "_".join(_render_comps) if _render_comps else _asset_name
        _safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in _render_key)
        _asset_cam_name = f"asset_camera_{_safe}"
        ai_camera = bpy.data.objects.get(_asset_cam_name)
        if ai_camera is None:
            print(f"[Asset Mode] ⚠ Asset camera '{_asset_cam_name}' not found — falling back to {camera_name}")
            ai_camera = bpy.data.objects.get(camera_name)
        else:
            print(f"[Asset Mode] 🎥 Rendering from asset camera: {_asset_cam_name}")
    else:
        # Find the ai_camera
        if camera_name not in bpy.data.objects:
            print(f"[Style Engine] ERROR: {camera_name} not found! Run 'Setup Workspace' first.")
            raise RuntimeError(f"{camera_name} not found. Please run 'Setup Workspace' first.")
        ai_camera = bpy.data.objects[camera_name]
    
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


def _apply_black_key(image_path, threshold=18):
    """Replace near-black pixels with full transparency in-place.

    Uses Blender's built-in bpy.data.images + numpy (both always available)
    so no external dependencies are required.

    threshold — any pixel with R, G, B all below this value (0-255) is made
    fully transparent.  Pure black background from Gemini sits at 0; even
    the darkest mortar joint on a brick wall has some colour, so 18 is safe
    without eroding real edges.
    """
    import numpy as _np
    from pathlib import Path as _Path

    path = _Path(image_path)
    img  = None
    try:
        img = bpy.data.images.load(str(path))
        w, h = img.size
        # pixels are stored as a flat RGBA float list (values 0.0–1.0)
        arr = _np.array(img.pixels[:], dtype=_np.float32).reshape(h, w, 4)
        t   = threshold / 255.0
        mask = (arr[:, :, 0] < t) & (arr[:, :, 1] < t) & (arr[:, :, 2] < t)
        arr[mask, 3] = 0.0
        img.pixels[:] = arr.flatten().tolist()
        img.filepath_raw = str(path)
        img.file_format  = 'PNG'
        img.save()
        n_keyed = int(mask.sum())
        print(f"[BlackKey] ✓ Keyed {n_keyed:,} px (threshold={threshold}): {path.name}")
        return True
    except Exception as _e:
        print(f"[BlackKey] ⚠ Could not apply black key to {path.name}: {_e}")
        import traceback as _tb; _tb.print_exc()
        return False
    finally:
        if img and img.name in bpy.data.images:
            bpy.data.images.remove(img)


def _on_arch_isolation_complete(context, server_client,
                                 success, result=None, error=None, workflow_type=None):
    """Callback for architectural asset isolation (no rembg).

    Downloads the raw Gemini output, applies a pure-black chroma key in
    Python to produce clean transparency, then saves to library and refreshes
    the asset camera background — identical end-state to the normal flow.
    """
    from . import runcomfy_server_client as _rsc
    if not success:
        print(f"[ArchKey] ❌ Isolation failed: {error}")
        return
    try:
        images = _rsc.extract_output_images(result)
        if not images:
            print("[ArchKey] No output images in result")
            return

        # First non-preview image is the main Gemini output
        main_img = next(
            (i for i in images
             if not i['filename'].lower().startswith(('canny', 'depth'))),
            None
        )
        if not main_img:
            print("[ArchKey] No main output image found")
            return

        dest_path = get_active_ai_output_path(context)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path  = str(dest_path) + '.tmp'

        ok = server_client.download_image(
            main_img['filename'], tmp_path,
            main_img.get('subfolder', ''), main_img.get('type', 'output'),
        )
        if ok and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
            os.replace(tmp_path, str(dest_path))
            print(f"[ArchKey] ✓ Downloaded: {dest_path.name}")
        else:
            print("[ArchKey] ❌ Download failed or file too small")
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return

        def _deferred():
            try:
                _ctx  = bpy.context
                _path = get_active_ai_output_path(_ctx)
                # Apply black-key BEFORE saving to library so the
                # transparent version is what gets archived.
                _apply_black_key(_path)
                # Save timestamped copy to project library
                saved = save_generation_to_library(_ctx, _path, backend='GCS')
                if saved:
                    print(f"[ArchKey] ✓ Saved to library: {Path(saved).name}")
                # Refresh camera background
                _p = _ctx.scene.style_engine_props
                if getattr(_p, 'asset_mode', False):
                    _comps = get_asset_path_components(_p)
                    refresh_asset_camera_image(
                        _p.current_asset_name,
                        path_components=_comps if _comps else None,
                    )
                else:
                    refresh_ai_image()
                print("[ArchKey] ✓ Camera background refreshed")
            except Exception as _e:
                print(f"[ArchKey] ⚠ Deferred error: {_e}")
                import traceback as _tb; _tb.print_exc()
            return None

        bpy.app.timers.register(_deferred, first_interval=0.05)

    except Exception as _e:
        print(f"[ArchKey] ❌ Callback error: {_e}")
        import traceback as _tb; _tb.print_exc()


def queue_asset_isolation_workflow(context, object_name):
    """
    Queue AssetNanoAlignmentRB.json to extract a single asset from the current
    scene's current_ai.png.

    Flow:
      1. Upload the SCENE's current_ai.png to the server (NOT the asset placeholder).
      2. Patch node 69 (ASSET_NAME) with object_name.
      3. Patch node 71 (Load Image) with the uploaded filename.
      4. Queue and start polling; the download callback writes the result to the
         asset's own temp/current_ai.png because asset_mode is True at fire-time.
    """
    import time as _time
    from . import runcomfy_deployment, runcomfy_polling, runcomfy_server_client

    # ── Server client ────────────────────────────────────────────────────────
    try:
        server_client = runcomfy_deployment.get_server_client()
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not get server client: {e}")
        return

    # ── Guard: don't stack generations ──────────────────────────────────────
    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[Asset Mode] Generation already in progress — skipping isolation render")
        return

    # ── Source current_ai.png ────────────────────────────────────────────────
    # At depth 1 use the global scene temp image.
    # At depth 2+ use the PARENT asset's current_ai so the nested asset is
    # extracted from its parent's render, not the full scene.
    try:
        _nprops = context.scene.style_engine_props
        _depth  = getattr(_nprops, 'asset_mode_depth', 0)
        if _depth > 1:
            _parent_components = get_asset_path_components(_nprops)[:-1]
            scene_current_ai = (get_nested_asset_directory(context, _parent_components)
                                / "temp" / "current_ai.png")
            print(f"[Asset Mode] Nested depth {_depth} — using parent image: {scene_current_ai}")
        else:
            scene_current_ai = get_temp_directory(context) / "current_ai.png"
    except Exception as _se:
        scene_current_ai = get_temp_directory(context) / "current_ai.png"
        print(f"[Asset Mode] ⚠ Could not resolve source image for depth: {_se}")

    if not scene_current_ai.exists():
        print(f"[Asset Mode] ⚠ Source current_ai.png not found at {scene_current_ai} — cannot isolate asset")
        return

    # ── Upload scene image ───────────────────────────────────────────────────
    print(f"[Asset Mode] Uploading scene current_ai.png for isolation …")
    try:
        upload_start = _time.time()
        upload_response = server_client.upload_image(str(scene_current_ai))
        uploaded_filename = upload_response['name']
        print(f"[Asset Mode] ✓ Uploaded: {uploaded_filename} ({_time.time() - upload_start:.2f}s)")
    except Exception as e:
        print(f"[Asset Mode] ⚠ Upload failed: {e}")
        return

    # ── Load & patch workflow ────────────────────────────────────────────────
    addon_dir = Path(__file__).parent
    wf_path = addon_dir / "workflows" / "Image" / "AssetNanoAlignmentRB.json"
    if not wf_path.exists():
        print(f"[Asset Mode] ⚠ AssetNanoAlignmentRB.json not found at {wf_path}")
        return

    with open(wf_path, 'r') as f:
        workflow_json = json.load(f)

    # Architectural/background keyword sets used to detect planar subjects that
    # benefit from an isometric camera angle rather than a perspective product shot.
    _ARCH_LABEL_KEYWORDS = {
        "facade", "wall", "floor", "ceiling", "pavement", "sidewalk", "road",
        "street", "building", "elevation", "structure", "roof", "ground",
        "terrain", "brick", "concrete", "tile", "slab", "panel", "surface",
        "column", "pillar", "arch", "gate", "doorway", "window", "balcony",
        "railing", "stair", "step", "path", "cobble", "cobblestone", "alley",
        "alleyway", "courtyard", "parapet", "buttress", "cladding", "masonry",
    }
    _ARCH_MATERIAL_KEYWORDS = {
        "concrete", "brick", "stone", "asphalt", "plaster", "mortar",
        "cement", "stucco", "tile", "wood_panel", "cladding", "masonry",
        "cobblestone", "sandstone", "limestone", "marble", "granite",
    }
    _ARCH_FEATURE_KEYWORDS = {
        "facade", "wall", "building", "elevation", "structural", "background",
    }

    # Node 69: asset descriptor — plain name plus any subject properties that are known,
    # so Gemini understands the specific look of the object to extract.
    descriptor    = object_name
    is_arch       = False   # will flip to True for architectural/planar subjects

    # Label-based detection is always run — object_name is always available
    # regardless of whether a valid subject entry exists in the list.
    _label_words = set(object_name.lower().replace("_", " ").split())
    if _label_words & _ARCH_LABEL_KEYWORDS:
        is_arch = True
        print(f"[Asset Mode] Arch detected via label words: {_label_words & _ARCH_LABEL_KEYWORDS}")

    try:
        _props = context.scene.style_engine_props
        _si    = _props.asset_subject_index
        if 0 <= _si < len(_props.refine_subjects):
            _subj = _props.refine_subjects[_si]
            _parts = []
            if _subj.style:    _parts.append(_subj.style)
            if _subj.material: _parts.append(_subj.material)
            if _subj.color:    _parts.append(_subj.color)
            if _subj.scale:    _parts.append(f"{_subj.scale} scale")
            if _parts:
                descriptor = f"{object_name} ({', '.join(_parts)})"

            # Material-based detection (supplements the label check above)
            if not is_arch and _subj.material and any(
                    k in _subj.material.lower() for k in _ARCH_MATERIAL_KEYWORDS):
                is_arch = True
                print(f"[Asset Mode] Arch detected via material: '{_subj.material}'")
    except Exception as _de:
        print(f"[Asset Mode] Could not build subject descriptor: {_de}")

    workflow_json["69"]["inputs"]["text"] = descriptor

    # Node 63 + Node 70: for architectural/planar subjects force an explicit
    # axonometric/isometric perspective — the generic prompt is not strong enough
    # to prevent rembg from treating a facade or wall as background.
    if is_arch:
        workflow_json["63"]["inputs"]["text"] = (
            "From the current scene, extract the following architectural asset:"
        )
        workflow_json["70"]["inputs"]["text"] = (
            ". This is the PRIMARY FOREGROUND SUBJECT — a planar architectural "
            "or structural element. It must NEVER be treated as background. "
            "YOU MUST USE AN AXONOMETRIC OR ISOMETRIC PERSPECTIVE — render it as "
            "a clean architectural elevation or isometric three-quarter projection "
            "so that all major surfaces are clearly visible and the element reads "
            "as a self-contained panel or tile, completely separate from any "
            "surrounding scene. The entire object must read as a single, unified, "
            "self-contained element: every part belongs to it. "
            "Render it on a pure black (#000000) background with a subtle rim "
            "light or soft specular highlight along its silhouette edges so every "
            "boundary of the object is clearly distinguishable from the background. "
            "Capture the whole object fully within the frame with clear visible "
            "edges on all sides. Preserve every specific detail, surface texture, "
            "distinctive markings and characteristic feature exactly as they appear "
            "in the source image — do not invent, generalise or substitute. "
            "Retain the medium, style and color palette of the original scene."
        )
        print(f"[Asset Mode] Architectural subject detected — forcing axonometric/isometric view")
    # else: leave node 63 and node 70 at their default text

    print(f"[Asset Mode] Node 69 descriptor: '{descriptor}' (arch={is_arch})")

    # For architectural assets bypass InspyrenetRembg entirely:
    # rewire SaveImage (64) to read directly from NanoBananaAIO (50) and
    # delete the rembg node.  The black-key is applied in Python instead,
    # where it is reliable because we know the background colour exactly.
    if is_arch and "64" in workflow_json and "67" in workflow_json:
        workflow_json["64"]["inputs"]["images"] = ["50", 0]
        del workflow_json["67"]
        print("[Asset Mode] Arch asset — rembg node removed, black-key will run in Python")

    # Node 71: scene image input
    workflow_json["71"]["inputs"]["image"] = uploaded_filename

    # Node 50: always 1K, 1:1 for assets
    workflow_json["50"]["inputs"]["image_size"] = "1K"
    workflow_json["50"]["inputs"]["aspect_ratio"] = "1:1"

    print(f"[Asset Mode] Patched AssetNanoAlignmentRB — asset='{descriptor}' image='{uploaded_filename}'")

    # ── Queue ────────────────────────────────────────────────────────────────
    from . import progress_bar
    try:
        queue_response = server_client.queue_prompt(workflow_json)
        prompt_id = queue_response.get('prompt_id')
        progress_bar.set_current_workflow(workflow_json)
        print(f"[Asset Mode] 🎨 Isolation queued (ID: {prompt_id[:8]}…)")
    except Exception as e:
        print(f"[Asset Mode] ⚠ queue_prompt failed: {e}")
        return

    # ── Poll ─────────────────────────────────────────────────────────────────
    if is_arch:
        # Arch assets: use the black-key callback (rembg was stripped above)
        _arch_cb = lambda success, result=None, error=None, workflow_type=None: \
            _on_arch_isolation_complete(context, server_client,
                                         success, result, error, workflow_type)
        runcomfy_polling.RunComfyPoller.start_polling(
            deployment_id='server',
            request_id=prompt_id,
            callback=_arch_cb,
            workflow_type='gemini',
        )
    else:
        runcomfy_polling.RunComfyPoller.start_polling(
            deployment_id='server',
            request_id=prompt_id,
            callback=lambda success, result=None, error=None, workflow_type=None:
                on_generation_complete_server(
                    context, success, result, error,
                    workflow_type or 'gemini', server_client
                ),
            workflow_type='gemini',
        )
    print("[Asset Mode] 🎨 Isolation render started!")


# ----------------------------------------------------------------

def queue_sam3_isolate_workflow(context, asset_name):
    """
    Queue SAM3Rembg.json to isolate a named asset from the active current_ai.png
    using SAM3 segmentation.

    The asset_name string is passed to node 4 (PrimitiveString / ASSET_NAME).
    The source image is always the ACTIVE current_ai for the current mode:
      - Scene mode  → global temp/current_ai.png
      - Asset mode  → asset's temp/current_ai.png
    Result is saved as a history entry and becomes the new current_ai.
    """
    import time as _time
    from . import runcomfy_deployment, runcomfy_polling

    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[SAM3] Generation already in progress — skipping")
        return

    try:
        server_client = runcomfy_deployment.get_server_client()
    except Exception as e:
        print(f"[SAM3] ⚠ Could not get server client: {e}")
        return

    # Source image = active current_ai for whichever mode is active
    source_image = get_active_ai_output_path(context)
    if not source_image.exists():
        print(f"[SAM3] ⚠ Source image not found: {source_image}")
        return

    print(f"[SAM3] Uploading source image: {source_image.name}")
    try:
        upload_response = server_client.upload_image(str(source_image))
        uploaded_filename = upload_response['name']
        print(f"[SAM3] ✓ Uploaded: {uploaded_filename}")
    except Exception as e:
        print(f"[SAM3] ⚠ Upload failed: {e}")
        return

    addon_dir = Path(__file__).parent
    wf_path = addon_dir / "workflows" / "Image" / "SAM3Rembg.json"
    if not wf_path.exists():
        print(f"[SAM3] ⚠ SAM3Rembg.json not found at {wf_path}")
        return

    with open(wf_path, 'r') as f:
        workflow = json.load(f)

    # Patch node 4 (ASSET_NAME) with the active asset name
    workflow["4"]["inputs"]["value"] = asset_name
    # Patch node 1 (Load Image) with the uploaded filename
    workflow["1"]["inputs"]["image"] = uploaded_filename

    print(f"[SAM3] Patched workflow — asset_name='{asset_name}' image='{uploaded_filename}'")

    from . import progress_bar
    try:
        queue_response = server_client.queue_prompt(workflow)
        prompt_id = queue_response.get('prompt_id')
        progress_bar.set_current_workflow(workflow)
        print(f"[SAM3] 🎨 Queued (ID: {prompt_id[:8]}…)")
    except Exception as e:
        print(f"[SAM3] ⚠ queue_prompt failed: {e}")
        return

    runcomfy_polling.RunComfyPoller.start_polling(
        deployment_id='server',
        request_id=prompt_id,
        callback=lambda success, result=None, error=None, workflow_type=None:
            on_generation_complete_server(
                context, success, result, error,
                workflow_type or 'gemini', server_client
            ),
        workflow_type='gemini',
    )
    print("[SAM3] 🎨 SAM3 isolation started!")


# ----------------------------------------------------------------

def queue_explode_workflow(context):
    """
    Queue ImageExplode.json to generate an exploded-view diagram of the
    active current_ai.png using Gemini.

    Gemini physically separates every component of the asset along a
    sequential axis, completes any cropped geometry, and sharpens
    unresolved textures.  Output is 4K 1:1 with U2Net background removed.

    The source image is always the ACTIVE current_ai for the current mode
    (scene or asset), so it works correctly in both contexts.
    """
    import time as _time
    from . import runcomfy_deployment, runcomfy_polling

    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[Explode] Generation already in progress — skipping")
        return

    try:
        server_client = runcomfy_deployment.get_server_client()
    except Exception as e:
        print(f"[Explode] ⚠ Could not get server client: {e}")
        return

    source_image = get_active_ai_output_path(context)
    if not source_image.exists():
        print(f"[Explode] ⚠ Source image not found: {source_image}")
        return

    print(f"[Explode] Uploading source image: {source_image.name}")
    try:
        upload_response = server_client.upload_image(str(source_image))
        uploaded_filename = upload_response['name']
        print(f"[Explode] ✓ Uploaded: {uploaded_filename}")
    except Exception as e:
        print(f"[Explode] ⚠ Upload failed: {e}")
        return

    addon_dir = Path(__file__).parent
    wf_path = addon_dir / "workflows" / "Image" / "ImageExplode.json"
    if not wf_path.exists():
        print(f"[Explode] ⚠ ImageExplode.json not found at {wf_path}")
        return

    with open(wf_path, 'r') as f:
        workflow = json.load(f)

    # Patch node 4 (Load Image) with the uploaded source image
    workflow["4"]["inputs"]["image"] = uploaded_filename

    print(f"[Explode] Patched workflow — image='{uploaded_filename}'")

    from . import progress_bar
    try:
        queue_response = server_client.queue_prompt(workflow)
        prompt_id = queue_response.get('prompt_id')
        progress_bar.set_current_workflow(workflow)
        print(f"[Explode] 🎨 Queued (ID: {prompt_id[:8]}…)")
    except Exception as e:
        print(f"[Explode] ⚠ queue_prompt failed: {e}")
        return

    runcomfy_polling.RunComfyPoller.start_polling(
        deployment_id='server',
        request_id=prompt_id,
        callback=lambda success, result=None, error=None, workflow_type=None:
            on_generation_complete_server(
                context, success, result, error,
                workflow_type or 'gemini', server_client
            ),
        workflow_type='gemini',
    )
    print("[Explode] 🎨 Explode generation started!")


def queue_u2net_isolate_workflow(context):
    """
    Queue u2netrembg.json to remove the background from the active current_ai.png
    using the U2Net model.  No subject string required.

    The source image is always the ACTIVE current_ai for the current mode.
    Result is saved as a history entry and becomes the new current_ai.
    """
    import time as _time
    from . import runcomfy_deployment, runcomfy_polling

    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[U2Net] Generation already in progress — skipping")
        return

    try:
        server_client = runcomfy_deployment.get_server_client()
    except Exception as e:
        print(f"[U2Net] ⚠ Could not get server client: {e}")
        return

    source_image = get_active_ai_output_path(context)
    if not source_image.exists():
        print(f"[U2Net] ⚠ Source image not found: {source_image}")
        return

    print(f"[U2Net] Uploading source image: {source_image.name}")
    try:
        upload_response = server_client.upload_image(str(source_image))
        uploaded_filename = upload_response['name']
        print(f"[U2Net] ✓ Uploaded: {uploaded_filename}")
    except Exception as e:
        print(f"[U2Net] ⚠ Upload failed: {e}")
        return

    addon_dir = Path(__file__).parent
    wf_path = addon_dir / "workflows" / "Image" / "u2netrembg.json"
    if not wf_path.exists():
        print(f"[U2Net] ⚠ u2netrembg.json not found at {wf_path}")
        return

    with open(wf_path, 'r') as f:
        workflow = json.load(f)

    # Patch node 1 (Load Image) with the uploaded filename
    workflow["1"]["inputs"]["image"] = uploaded_filename

    print(f"[U2Net] Patched workflow — image='{uploaded_filename}'")

    from . import progress_bar
    try:
        queue_response = server_client.queue_prompt(workflow)
        prompt_id = queue_response.get('prompt_id')
        progress_bar.set_current_workflow(workflow)
        print(f"[U2Net] 🎨 Queued (ID: {prompt_id[:8]}…)")
    except Exception as e:
        print(f"[U2Net] ⚠ queue_prompt failed: {e}")
        return

    runcomfy_polling.RunComfyPoller.start_polling(
        deployment_id='server',
        request_id=prompt_id,
        callback=lambda success, result=None, error=None, workflow_type=None:
            on_generation_complete_server(
                context, success, result, error,
                workflow_type or 'gemini', server_client
            ),
        workflow_type='gemini',
    )
    print("[U2Net] 🎨 U2Net isolation started!")


# ----------------------------------------------------------------

def queue_apply_to_parent_workflow(context, child_label, prompt_str):
    """
    Queue ImageNanoAlignmentRef.json to visually update the parent's current_ai.png
    so it reflects the modified child asset shown in the second image slot.

    image_1 (node 56) = parent's current_ai.png  — the scene / parent level to edit
    image_2 (node 67) = child's  current_ai.png  — the modified asset as visual ref

    The result is saved directly to the parent's current_ai.png path, never to the
    active asset path (get_active_ai_output_path), so asset-mode isolation is
    preserved while the parent level is still updated.
    """
    import time as _time
    from . import runcomfy_deployment, runcomfy_polling

    # ── Guard: don't stack generations ──────────────────────────────────────
    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[ApplyToParent] Generation already in progress — skipping visual cascade")
        return

    # ── Server client ────────────────────────────────────────────────────────
    try:
        server_client = runcomfy_deployment.get_server_client()
    except Exception as e:
        print(f"[ApplyToParent] ⚠ Could not get server client: {e}")
        return

    # ── Resolve image paths ──────────────────────────────────────────────────
    props = context.scene.style_engine_props

    # Child = active asset's current render
    child_image_path = get_active_ai_output_path(context)

    # Parent = one level up the stack
    try:
        _stack = json.loads(getattr(props, 'asset_mode_stack', '[]') or '[]')
        if not _stack:
            # Parent is the scene itself
            parent_image_path = get_temp_directory(context) / "current_ai.png"
            parent_components = None
        else:
            parent_components = [e["asset_name"] for e in _stack]
            parent_image_path = (get_nested_asset_directory(context, parent_components)
                                 / "temp" / "current_ai.png")
    except Exception as _pe:
        print(f"[ApplyToParent] ⚠ Could not resolve parent image path: {_pe}")
        return

    if not child_image_path.exists():
        print(f"[ApplyToParent] ⚠ Child current_ai not found: {child_image_path}")
        return
    if not parent_image_path.exists():
        print(f"[ApplyToParent] ⚠ Parent current_ai not found: {parent_image_path}")
        return

    # ── Upload both images ───────────────────────────────────────────────────
    print(f"[ApplyToParent] Uploading parent image: {parent_image_path}")
    try:
        parent_upload   = server_client.upload_image(str(parent_image_path))
        parent_filename = parent_upload['name']
        print(f"[ApplyToParent] ✓ Parent uploaded: {parent_filename}")
    except Exception as e:
        print(f"[ApplyToParent] ⚠ Parent upload failed: {e}")
        return

    print(f"[ApplyToParent] Uploading child image: {child_image_path}")
    try:
        child_upload   = server_client.upload_image(str(child_image_path))
        child_filename = child_upload['name']
        print(f"[ApplyToParent] ✓ Child uploaded: {child_filename}")
    except Exception as e:
        print(f"[ApplyToParent] ⚠ Child upload failed: {e}")
        return

    # ── Load & patch workflow ────────────────────────────────────────────────
    # Use the RB variant when the parent is itself an asset (isolated subject
    # with no background), keep the plain variant when the parent is the scene
    # (background must be preserved).
    addon_dir  = Path(__file__).parent
    wf_name    = "ImageNanoAlignmentRefRB.json" if parent_components else "ImageNanoAlignmentRef.json"
    wf_path    = addon_dir / "workflows" / "Image" / wf_name
    if not wf_path.exists():
        print(f"[ApplyToParent] ⚠ {wf_name} not found: {wf_path}")
        return
    print(f"[ApplyToParent] Using workflow: {wf_name}")

    with open(wf_path, 'r') as f:
        workflow_json = json.load(f)

    # Node 56 (image_1): parent scene — provides spatial context for in-painting
    workflow_json["56"]["inputs"]["image"] = parent_filename
    # Node 67 (image_2): modified child asset — provides the visual target
    workflow_json["67"]["inputs"]["image"] = child_filename
    # Node 63: instruction prompt
    workflow_json["63"]["inputs"]["text"] = prompt_str
    # Node 65: instructions (blank — prompt is self-contained)
    workflow_json["65"]["inputs"]["value"] = ""
    # Node 66: spatial alignment text (blank — parent image IS the spatial ref)
    workflow_json["66"]["inputs"]["value"] = ""

    # Node 50: match the parent image's own dimensions so the output never
    # changes the aspect ratio or resolution of the parent level.
    _parent_aspect, _parent_size = _read_image_aspect_and_size(parent_image_path)
    workflow_json["50"]["inputs"]["aspect_ratio"] = _parent_aspect
    workflow_json["50"]["inputs"]["image_size"]   = _parent_size

    print(f"[ApplyToParent] Patched workflow — "
          f"parent='{parent_filename}' child='{child_filename}'")

    # ── Queue ────────────────────────────────────────────────────────────────
    from . import progress_bar
    try:
        queue_response = server_client.queue_prompt(workflow_json)
        prompt_id = queue_response.get('prompt_id')
        progress_bar.set_current_workflow(workflow_json)
        print(f"[ApplyToParent] 🎨 Visual cascade queued (ID: {prompt_id[:8]}…)")
    except Exception as e:
        print(f"[ApplyToParent] ⚠ queue_prompt failed: {e}")
        return

    # ── Custom completion callback ───────────────────────────────────────────
    # Deliberately does NOT use on_generation_complete_server because that
    # function always saves to get_active_ai_output_path() (the child path).
    # Here we write explicitly to the parent path.
    _parent_image_path = parent_image_path     # capture for closure
    _parent_components = parent_components

    def _on_apply_to_parent_complete(success, result=None, error=None,
                                     workflow_type=None):
        if not success:
            print(f"[ApplyToParent] ❌ Visual cascade failed: {error}")
            return
        try:
            from . import runcomfy_server_client
            images = runcomfy_server_client.extract_output_images(result)
            if not images:
                print("[ApplyToParent] No output images in result")
                return

            for img_info in images:
                # Skip canny / depth previews
                fname_lower = img_info['filename'].lower()
                if fname_lower.startswith('canny') or fname_lower.startswith('depth'):
                    continue

                tmp_path = str(_parent_image_path) + '.tmp'
                ok = server_client.download_image(
                    img_info['filename'], tmp_path,
                    img_info.get('subfolder', ''),
                    img_info.get('type', 'output'),
                )
                if ok and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 1024:
                    os.replace(tmp_path, str(_parent_image_path))
                    print(f"[ApplyToParent] ✅ Parent current_ai updated: "
                          f"{_parent_image_path}")

                    def _deferred_refresh():
                        try:
                            _ctx = bpy.context
                            # Save a timestamped library entry so the generation
                            # browser can see and navigate to this result.
                            saved = save_generation_to_library(
                                _ctx, _parent_image_path, backend='GCS'
                            )
                            if saved:
                                print(f"[ApplyToParent] ✓ Saved to library: "
                                      f"{Path(saved).name}")

                            # Refresh the parent camera background
                            if _parent_components:
                                refresh_asset_camera_image(
                                    _parent_components[-1],
                                    path_components=_parent_components,
                                )
                            else:
                                refresh_ai_image()
                            print("[ApplyToParent] ✓ Parent camera background refreshed")
                        except Exception as _re:
                            print(f"[ApplyToParent] ⚠ Refresh error: {_re}")
                            import traceback
                            traceback.print_exc()
                        return None

                    bpy.app.timers.register(_deferred_refresh, first_interval=0.1)
                else:
                    print(f"[ApplyToParent] ❌ Download failed or file too small")

                break  # only the first main-output image is needed

        except Exception as _ce:
            print(f"[ApplyToParent] ❌ Completion callback error: {_ce}")
            import traceback
            traceback.print_exc()

    runcomfy_polling.RunComfyPoller.start_polling(
        deployment_id='server',
        request_id=prompt_id,
        callback=_on_apply_to_parent_complete,
        workflow_type='gemini',
    )
    print(f"[ApplyToParent] 🎨 Visual cascade started — '{child_label}' → parent")


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
    # In Asset Mode this resolves to the asset's own temp/current_ai.png so that
    # refinement is based on the asset render rather than the scene image.
    if refine_mode:
        combined_path = get_active_ai_output_path(context)
        if not combined_path.exists():
            print(f"[Style Engine] Refine mode: current_ai.png not found at {combined_path}")
            return
        print(f"[Style Engine] Refine mode: using {combined_path} as conditioning input")
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
        _show_generation_error_popup(error)
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

            # In Asset Mode redirect the main output away from global temp so
            # the scene's current_ai.png is never overwritten by asset renders.
            if save_name == 'current_ai.png':
                save_path = str(get_active_ai_output_path(context))
            else:
                save_path = str(temp_dir / save_name)

            downloads_to_perform.append({
                'filename': filename,
                'save_name': save_name,
                'save_path': save_path,
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
            # _current_ai_path is re-evaluated inside the callback (not closed
            # over) so it correctly resolves to asset temp when in asset mode.

            def _deferred_post_download():
                try:
                    _ctx = bpy.context  # fresh, safe context at timer-fire time
                    # Re-evaluate the correct output path at callback time so
                    # asset mode is respected even when the download happened
                    # on a background thread.
                    _current_ai_path = get_active_ai_output_path(_ctx)

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

                    # Push result + metadata to hub (two-step protocol)
                    try:
                        from . import hub_client as _hc
                        _prefs   = _ctx.preferences.addons["styleengine"].preferences
                        _hub_url = getattr(_prefs, "hub_url", "").rstrip("/")
                        _sid     = _hc.get_session_id(bpy.data.filepath if bpy.data.is_saved else None)
                        if _hub_url and not _sid.startswith("unsaved"):
                            # ── Snapshot all Blender-side data on the main thread ──
                            _props = _ctx.scene.style_engine_props

                            _prompt = ""
                            try:
                                _tb = bpy.data.texts.get("STYLEENGINE_Prompt")
                                _prompt = _tb.as_string().strip() if _tb else ""
                            except Exception:
                                pass

                            _hub_config = {
                                "prompt":         _prompt,
                                "temperature":    getattr(_props, "gemini_temperature", 1.0),
                                "imageSize":      getattr(_props, "gemini_image_size", "1K"),
                                "aspectRatio":    getattr(_props, "refine_meta_aspect", ""),
                                "alignmentMode":  getattr(_props, "gemini_alignment", False),
                                "model":          "gemini" if getattr(_props, "ai_model", "SDXL") == "GEMINI" else "sdxl",
                            }

                            # Collect source images and their hashes
                            _sources = []
                            for _role, _fname in [("frame", "combined.jpg"),
                                                  ("canny", "canny.png"),
                                                  ("depth", "depth.png")]:
                                _src_path = str(_current_ai_path.parent / _fname)
                                try:
                                    import os as _os
                                    if _os.path.isfile(_src_path):
                                        _sources.append({
                                            "role":          _role,
                                            "filename":      _fname,
                                            "sha256":        _hc.sha256_file(_src_path),
                                            "generation_id": None,
                                        })
                                except Exception:
                                    pass

                            _wf_name = ""
                            try:
                                from . import progress_bar as _pb
                                _wf = _pb.BridgePollerState.current_workflow
                                if _wf and isinstance(_wf, dict):
                                    # Workflow JSON stored as dict; name not always present.
                                    # Fall back gracefully.
                                    _wf_name = _wf.get("_filename", "")
                            except Exception:
                                pass

                            _step2_payload = {
                                "model":      _hub_config["model"],
                                "workflow":   _wf_name,
                                "blend_file": bpy.data.filepath,
                                "config":     _hub_config,
                                "sources":    _sources,
                            }
                            _ai_path_str = str(_current_ai_path)

                            def _push_to_hub(_url, _session, _img, _payload):
                                resp = _hc.push_result_image(_url, _session, _img)
                                gen_id = resp.get("generation_id")
                                if gen_id:
                                    _hc.push_config(_url, _session, gen_id, _payload)

                            import threading as _t
                            _t.Thread(
                                target=_push_to_hub,
                                args=(_hub_url, _sid, _ai_path_str, _step2_payload),
                                daemon=True,
                            ).start()
                    except Exception as _he:
                        print(f"[GCS] Hub push error: {_he}")

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
    
    # In Asset Mode write directly to the asset's temp so the global
    # current_ai.png is never overwritten by asset renders.
    current_ai_path = get_active_ai_output_path(context)

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


def _show_generation_error_popup(error_str):
    """
    Show a Blender popup dialog with a human-readable explanation of a
    ComfyUI/Gemini generation failure.

    Currently handles:
      - IMAGE_RECITATION  — Gemini copyright/IP filter
      - Generic fallback  — show the raw error string
    """
    error_str = str(error_str or "")

    if "IMAGE_RECITATION" in error_str.upper():
        title   = "Gemini: Image Refused (Copyright Filter)"
        lines   = [
            "Gemini refused to generate this image because it detected",
            "the input too closely resembles copyrighted material",
            "(FinishReason: IMAGE_RECITATION).",
            "",
            "Suggestions:",
            "  • Rephrase your prompt more descriptively",
            "    e.g. 'helmet at three-quarter angle' instead of",
            "    'give me a 3/4 view of this helmet'",
            "  • Turn Alignment OFF to use text-only generation",
            "    (bypasses the input-image recitation check)",
            "  • Stylise the image first, then use it as alignment input",
        ]
        icon = 'ERROR'
    else:
        title = "Generation Failed"
        lines = [f"Error: {error_str[:200]}"]
        icon  = 'CANCEL'

    def _draw_popup(self, context):
        col = self.layout.column(align=True)
        for line in lines:
            col.label(text=line)

    def _show():
        try:
            bpy.context.window_manager.popup_menu(
                _draw_popup, title=title, icon=icon
            )
        except Exception as _pe:
            print(f"[Style Engine] ⚠ Could not show error popup: {_pe}")

    # popup_menu must run on the main thread; schedule via timer if we're
    # inside a polling callback (which runs on a background thread).
    bpy.app.timers.register(_show, first_interval=0.05)


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

