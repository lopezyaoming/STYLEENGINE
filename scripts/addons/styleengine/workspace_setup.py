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

def get_temp_directory(context=None):
    """
    Get the temp directory for storing AI vision data.
    Once determined, the path is locked for the entire session to prevent
    filepath issues when .blend file is saved mid-session.
    
    Priority:
    1. Use .blend file directory if file is saved (//temp/ai_vision/)
    2. Use output_path from preferences if set
    3. Fall back to system temp directory
    """
    global _session_temp_dir
    
    # If already determined, reuse it (prevents save-time path changes)
    if _session_temp_dir is not None:
        return _session_temp_dir
    
    # Determine temp directory (priority order)
    temp_dir = None
    
    # 1. Try .blend file directory if saved
    if bpy.data.is_saved:
        blend_dir = Path(bpy.path.abspath("//"))
        temp_dir = blend_dir / "temp" / "ai_vision"
    
    # 2. Try user's output_path setting
    elif context:
        try:
            props = context.scene.style_engine_props
            if hasattr(props, 'output_path') and props.output_path:
                output_path = Path(props.output_path)
                if output_path.exists():
                    temp_dir = output_path / "temp" / "ai_vision"
        except:
            pass
    
    # 3. Fall back to system temp
    if temp_dir is None:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "ai_vision"
    
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
            "reference_images": {
                # Global strengths
                "style_transfer_strength": round(props.style_transfer_strength, 3),
                "composition_strength": round(props.composition_strength, 3),
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
                "temp_dir": "//temp/ai_vision/",
                "preview_out": "//temp/ai_vision/current_ai.png",
                "passes_dir": "//temp/ai_vision/passes/",
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


def refresh_ai_image():
    """
    Reload current_ai.png in Blender when called.
    OPTIMIZED: Called only when new image arrives (on_generation_complete), not on a timer.
    This eliminates wasteful file system checks every 2 seconds.
    """
    try:
        # Get temp directory and image path
        temp_dir = get_temp_directory(bpy.context)
        img_path = temp_dir / "current_ai.png"
        
        # Check if file exists
        if not img_path.exists():
            print(f"[Style Engine] Warning: Image not found at {img_path}")
            return
        
        # Reload the image if it exists in Blender
        if "current_ai.png" in bpy.data.images:
            img = bpy.data.images["current_ai.png"]
            img.reload()
            
            # OPTIMIZED: Only redraw 3D viewports in current screen (not all windows!)
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            print(f"[Style Engine] ✓ Image reloaded: {os.path.basename(img_path)}")
        else:
            print(f"[Style Engine] Warning: Image 'current_ai.png' not in Blender data")
    
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
        
        # Configure render settings
        scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Blender 4.2+ uses EEVEE_NEXT
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
    
    from . import utils
    prompt_text = utils.get_or_create_prompt_text()
    
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
    
    # Create/get the prompt text block
    prompt_text = utils.get_or_create_prompt_text()
    
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
        
        # Position camera at current view
        self.align_camera_to_view(context, ai_camera)
        
        # Setup camera background image
        self.setup_camera_background(context, ai_camera)
        
        # Create the AI workspace (always from default Layout)
        workspace = self.create_ai_workspace(context)
        
        # Configure scene render engine to Workbench for performance
        self.setup_render_engine(context)
        
        # Skip compositor setup - not needed with Workbench (no render passes)
        # Compositor is disabled during rendering for performance anyway
        # self.setup_compositor(context)  # DEPRECATED - Workbench doesn't support Mist/AO passes
        
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
                
                # Create the prompt text block if it doesn't exist
                if "STYLEENGINE_Prompt" not in bpy.data.texts:
                    prompt_text = bpy.data.texts.new("STYLEENGINE_Prompt")
                    prompt_text.write("Enter your AI prompt here...")
                    print("[Style Engine] Created prompt text block: STYLEENGINE_Prompt")
                else:
                    prompt_text = bpy.data.texts["STYLEENGINE_Prompt"]
                
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
            
            # For HeavyPoly mode: Switch main 3D viewport to Edit mode (delayed, after layout setup)
            from . import utils
            if utils.is_heavypoly_compatible():
                bpy.app.timers.register(_switch_to_edit_mode_standalone, first_interval=0.5)  # After layout setup
            
            self.report({'INFO'}, "AI Vision workspace created successfully!")
        else:
            self.report({'WARNING'}, "Failed to create AI workspace.")
        
        return {'FINISHED'}
    
    def ensure_temp_directory(self, context):
        """Create the data/temp/ai_vision directory if it doesn't exist."""
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
    
    def setup_camera_background(self, context, camera):
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
        
        # Load or create the image
        if "current_ai.png" in bpy.data.images:
            img = bpy.data.images["current_ai.png"]
            img.filepath = str(img_path)
            img.reload()
        else:
            if img_path.exists():
                img = bpy.data.images.load(str(img_path))
                img.name = "current_ai.png"
            else:
                # Create a placeholder with correct resolution
                props = context.scene.style_engine_props
                res_str = props.ai_resolution
                width, height = map(int, res_str.split('x'))
                img = bpy.data.images.new("current_ai.png", width=width, height=height)
        
        # Setup background image properties
        bg_img.image = img
        
        # Get opacity from properties (default to 0.7 for better visibility)
        props = bpy.context.scene.style_engine_props
        bg_img.alpha = props.background_opacity if hasattr(props, 'background_opacity') else 0.7
        
        bg_img.display_depth = 'FRONT'  # Display in front (default - can be changed via UI)
        bg_img.frame_method = 'STRETCH'
        
        # Set render resolution based on user's ai_resolution setting
        props = context.scene.style_engine_props
        res_str = props.ai_resolution  # e.g., "1024x1024"
        render_width, render_height = map(int, res_str.split('x'))
        
        context.scene.render.resolution_x = render_width
        context.scene.render.resolution_y = render_height
        
        print(f"[Style Engine] Background image set: {img_path}")
        print(f"[Style Engine] Render resolution set to: {render_width}x{render_height} (from ai_resolution setting)")
    
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
        
        # Ensure render resolution is set correctly
        props = context.scene.style_engine_props
        res_str = props.ai_resolution
        width, height = map(int, res_str.split('x'))
        scene.render.resolution_x = width
        scene.render.resolution_y = height
        scene.render.resolution_percentage = 100  # Always 100% for SDXL native resolution
        
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
    Render combined pass from ai_camera using WORKBENCH (ultra-fast).
    OPTIMIZED: Workbench is 10-15x faster than EEVEE. Depth is generated by AI (DepthAnything).
    Uses SURGICAL approach - doesn't disturb user's active camera.
    """
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
        # Configure render settings - WORKBENCH for speed!
        scene.render.engine = 'BLENDER_WORKBENCH'  # Ultra-fast, no samples needed!
        scene.render.image_settings.file_format = 'JPEG'  # JPEG for smaller file size (faster upload)
        scene.render.image_settings.color_mode = 'RGB'  # JPEG doesn't support alpha
        scene.render.image_settings.quality = 85  # High quality, good compression
        scene.render.use_compositing = False  # Disable compositor for speed!
        # Resolution percentage kept at 100% to match SDXL native resolution exactly
        
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
        print(f"[Style Engine] 🎨 Rendering from {camera_name} (Workbench)...")
        
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

def generate_ai_image_cloud(context):
    """
    Cloud generation using RunComfy API.
    This function replaces the local FastAPI/ComfyUI workflow.
    """
    from . import runcomfy_polling
    from . import runcomfy_deployment
    from . import runcomfy_client
    from . import utils
    
    # 0. AUTO-SYNC: Load prompt from text editor (cyclical/automatic)
    prompt_from_editor = utils.get_prompt_from_text_editor()
    props = context.scene.style_engine_props
    
    if prompt_from_editor:
        # Check if Prompt Builder is enabled
        if props.use_prompt_builder:
            # Process through prompt builder
            positive_prompt, negative_prompt = utils.process_prompt_builder(prompt_from_editor)
            
            if positive_prompt:
                props.global_prompt = positive_prompt
                props.negative_prompt = negative_prompt  # Store negative prompt!
                print(f"[Style Engine] ✓ Prompt Builder: Built prompt from tags ({len(positive_prompt)} chars)")
                print(f"[Style Engine]   → Positive: {positive_prompt[:100]}...")
                if negative_prompt:
                    print(f"[Style Engine]   → Negative: {negative_prompt[:50]}...")
                else:
                    print(f"[Style Engine]   → Negative: (none - will use default)")
            else:
                # Fallback to raw text if builder failed
                props.global_prompt = prompt_from_editor
                props.negative_prompt = ""  # Clear negative prompt
                print(f"[Style Engine] ⚠️ Prompt Builder: No tags found, using raw text")
        else:
            # Normal mode: use raw text as-is
            props.global_prompt = prompt_from_editor
            props.negative_prompt = ""  # Clear negative prompt in normal mode
            print(f"[Style Engine] ✓ Auto-synced prompt from text editor ({len(prompt_from_editor)} chars)")
    
    # 1. Check if generation already in progress
    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[Style Engine] Generation already in progress, skipping")
        return
    
    # 2. Render passes (same as local)
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
    session_data['global_prompt'] = context.scene.style_engine_props.global_prompt
    print(f"[Style Engine] Using prompt: {session_data['global_prompt'][:50]}...")
    
    # 4. Encode combined image to base64
    # NOTE: Only combined pass is sent - depth is generated by DepthAnything AI on the server
    # JPEG format for smaller file size (faster upload)
    combined_path = temp_dir / "combined.jpg"
    
    if not combined_path.exists():
        print(f"[Style Engine] Combined pass not found at {combined_path}")
        return
    
    # Get file size for diagnostic
    file_size_kb = combined_path.stat().st_size / 1024
    print(f"[Style Engine] 📦 Image file: {file_size_kb:.1f} KB (JPEG)")
    
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
    
    # 6. Ensure deployment exists
    try:
        deployment_id = runcomfy_deployment.DeploymentManager.ensure_deployment(workflow_type)
    except runcomfy_client.RunComfyError as e:
        print(f"[Style Engine] Failed to ensure deployment: {e}")
        return
    
    # 7. Build overrides (depth not needed - AI generates it)
    # Pass context for reference image encoding
    overrides = build_runcomfy_overrides(
        context=context,
        session_data=session_data,
        combined_b64=combined_b64,
        workflow_type=workflow_type
    )
    
    # 8. Submit inference (Serverless or Server mode)
    try:
        import time
        
        # NOTE: Server API mode disabled/latent - always use serverless
        # if runcomfy_deployment.is_server_mode():
        #     # ================================================================
        #     # SERVER API MODE - Direct ComfyUI Backend submission
        #     # ================================================================
        #     from . import runcomfy_server_client
        #     
        #     print(f"[Style Engine] =========================================")
        #     print(f"[Style Engine] SERVER API MODE - Starting Generation")
        #     print(f"[Style Engine] =========================================")
        #     
        #     server_client = runcomfy_deployment.get_server_client()
        #     
        #     # Quick connection check before proceeding
        #     print(f"[Style Engine] Verifying server connection...")
        #     connected, conn_status = server_client.check_connection()
        #     if not connected:
        #         error = conn_status.get('error', 'Unknown error')
        #         print(f"[Style Engine] ❌ Server connection check failed: {error}")
        #         print(f"[Style Engine] Please use 'Test Server Connection' in preferences to diagnose.")
        #         return
        #     print(f"[Style Engine] ✓ Server connection verified")
        #     print(f"[Style Engine]")
        #     
        #     # Load workflow JSON file
        #     workflow_json = load_workflow_json_for_server(workflow_type)
        #     if not workflow_json:
        #         print("[Style Engine] Failed to load workflow JSON")
        #         return
        #     
        #     # Apply overrides to workflow
        #     runcomfy_server_client.apply_overrides_to_workflow(workflow_json, overrides)
        #     
        #     # Time the upload operation
        #     submit_start = time.time()
        #     
        #     # Queue prompt
        #     queue_response = server_client.queue_prompt(workflow_json)
        #     prompt_id = queue_response.get('prompt_id')
        #     
        #     submit_duration = time.time() - submit_start
        #     
        #     print(f"[Server API] ⏱️ Upload took {submit_duration:.3f}s")
        #     
        #     # Start polling
        #     runcomfy_polling.RunComfyPoller.start_polling(
        #         deployment_id='server',  # Special marker for server mode
        #         request_id=prompt_id,
        #         callback=lambda success, result=None, error=None, workflow_type=None: 
        #             on_generation_complete_server(context, success, result, error, workflow_type or 'sdxl', server_client),
        #         workflow_type=workflow_type
        #     )
        #     
        #     print(f"[Server API] 🖥️ Server generation started (prompt_id: {prompt_id[:8]}...)")
        #     
        # else:
        
        # Always use serverless mode
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
        # NOTE: Server API mode disabled - only serverless errors possible
        print(f"[Serverless API] Failed to submit inference: {e}")


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
        
        overrides = {
            "5": {"inputs": {"width": width, "height": height}},  # EmptyLatentImage
            "25": {"inputs": {"value": positive_prompt}},  # Positive Prompt (Node 25)
            "7": {"inputs": {"text": negative_prompt}},  # Negative Prompt (Node 7) - CRITICAL!
            "15": {"inputs": {"image": combined_b64}},  # Base image (AO)
            "40": {"inputs": {"value": session_data.get('silhouette_influence', 0.75)}},  # Canny
            "41": {"inputs": {"value": session_data.get('depth_influence', 0.5)}},  # Depth
            "42": {"inputs": {"value": session_data.get('steps', 15)}},  # Steps
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
        
        # Global strengths
        print(f"\n🎚️ GLOBAL STRENGTHS:")
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
            print("[Server API] No output images found in result")
            return
        
        # Download first image
        first_image = images[0]
        filename = first_image['filename']
        subfolder = first_image.get('subfolder', '')
        image_type = first_image.get('type', 'output')
        
        print(f"[Server API] Downloading image: {filename}")
        
        # Get temp directory
        temp_dir = get_temp_directory(context)
        ai_vision_dir = temp_dir / "ai_vision"
        ai_vision_dir.mkdir(parents=True, exist_ok=True)
        
        # Save path
        save_path = ai_vision_dir / "current_ai.png"
        
        # Download image from server
        if server_client.download_image(filename, str(save_path), subfolder, image_type):
            print(f"[Server API] ✅ Image downloaded: {save_path}")
            
            # Update camera background image (same as serverless)
            update_camera_background_image(context, save_path)
            
            # Save to data/generated with increment
            save_generated_image_with_increment(context, save_path)
            
            # Trigger next generation cycle if auto-generate is enabled
            if context.scene.style_engine.auto_generate:
                trigger_next_generation_cycle(context)
        else:
            print("[Server API] Failed to download image")
    
    except Exception as e:
        print(f"[Server API] Error in completion callback: {e}")
        import traceback
        traceback.print_exc()


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
        
        # Update camera background (on-demand refresh - only when new image arrives!)
        refresh_ai_image()
        print("[Style Engine] ✓ Camera background updated with new AI image")
        
        # Save to output_path if set
        props = context.scene.style_engine_props
        if hasattr(props, 'output_path') and props.output_path and os.path.exists(props.output_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(props.output_path) / "generated"
            output_dir.mkdir(exist_ok=True, parents=True)
            
            output_path = output_dir / f"{timestamp}_runcomfy.png"
            try:
                shutil.copy2(current_ai_path, output_path)
                print(f"[Style Engine] 💾 Saved to {output_path}")
            except Exception as e:
                print(f"[Style Engine] Failed to save to output_path: {e}")
        else:
            print("[Style Engine] Output path not set, skipping save")
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

