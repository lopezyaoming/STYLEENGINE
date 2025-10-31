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

# Get the project root directory (C:\Coding\STYLEENGINE)
# __file__ = .../scripts/addons/styleengine/workspace_setup.py
# Go up 4 levels: styleengine -> addons -> scripts -> STYLEENGINE
file_dir = os.path.abspath(__file__)  # workspace_setup.py
addon_dir = os.path.dirname(file_dir)  # styleengine/
addons_dir = os.path.dirname(addon_dir)  # addons/
scripts_dir = os.path.dirname(addons_dir)  # scripts/
ADDON_ROOT = os.path.dirname(scripts_dir)  # STYLEENGINE/

# Global variable to track last modification time
_last_image_mtime = 0

# Global variable for render interval
RENDER_INTERVAL = 5.0  # seconds


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
            "steps": props.steps,
            "ipadapter": {
                "enabled": props.use_ipadapter if hasattr(props, 'use_ipadapter') else False,
                "reference_image": props.ipadapter_reference_image if hasattr(props, 'ipadapter_reference_image') else "",
                "weight_type": props.ipadapter_weight_type if hasattr(props, 'ipadapter_weight_type') else "style transfer",
                "strength": round(props.ipadapter_strength, 2) if hasattr(props, 'ipadapter_strength') else 0.75
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
        session_path = os.path.join(ADDON_ROOT, "data", "temp", "ai_vision", "session.json")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(session_path), exist_ok=True)
        
        session_tmp = session_path + ".tmp"
        
        with open(session_tmp, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Atomic replace
        os.replace(session_tmp, session_path)
        
    except Exception as e:
        print(f"[Style Engine] Error writing session.json: {e}")


def refresh_ai_image():
    """
    Auto-refresh timer function that checks if current_ai.png has been updated
    and reloads it in Blender if necessary.
    """
    global _last_image_mtime
    
    try:
        # Check if refresh is still enabled
        props = bpy.context.scene.style_engine_props
        if not props.refresh_viewport:
            # Stop the timer if refresh is disabled
            if bpy.app.timers.is_registered(refresh_ai_image):
                return None  # Don't repeat
            
        # Use the addon's installation directory
        img_path = os.path.join(ADDON_ROOT, "data", "temp", "ai_vision", "current_ai.png")
        
        # Check if file exists
        if not os.path.exists(img_path):
            return 1.0  # Check again in 1 second
        
        # Get current modification time
        current_mtime = os.path.getmtime(img_path)
        
        # If the file has been modified since last check
        if current_mtime != _last_image_mtime:
            _last_image_mtime = current_mtime
            
            # Reload the image if it exists in Blender
            if "current_ai.png" in bpy.data.images:
                img = bpy.data.images["current_ai.png"]
                img.reload()
                
                # Force viewport redraw
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
                
                print(f"[Style Engine] Image reloaded: {os.path.basename(img_path)}")
    
    except Exception as e:
        print(f"[Style Engine] Error in refresh timer: {e}")
    
    # Continue running every 1 second
    return 1.0


def auto_render_passes():
    """
    Auto-render timer that renders ai_camera every X seconds with all passes.
    IMPORTANT: This timer is DISABLED when auto_generate is enabled.
    Auto-generate uses its own cyclical system (render → generate → download → repeat).
    """
    try:
        # Check if refresh is still enabled
        props = bpy.context.scene.style_engine_props
        if not props.refresh_viewport:
            # Stop the timer if refresh is disabled
            return None
        
        # ⚠️ DISABLE timer-based rendering when auto-generate is enabled
        # Auto-generate uses cyclical system instead
        if hasattr(props, 'auto_generate') and props.auto_generate:
            print("[Style Engine] Auto-generate is active, skipping timer-based render")
            return RENDER_INTERVAL  # Keep timer alive but skip rendering
        
        # Find the ai_camera
        if "ai_camera" not in bpy.data.objects:
            print("[Style Engine] ai_camera not found, skipping render")
            return RENDER_INTERVAL
        
        ai_camera = bpy.data.objects["ai_camera"]
        scene = bpy.context.scene
        
        # Store original settings
        original_camera = scene.camera
        original_engine = scene.render.engine
        original_samples = scene.eevee.taa_render_samples
        
        # Configure render settings
        scene.camera = ai_camera
        scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Blender 4.2+ uses EEVEE_NEXT
        scene.eevee.taa_render_samples = 16
        
        # Set output path for the main render
        passes_path = os.path.join(ADDON_ROOT, "data", "temp", "passes")
        scene.render.filepath = os.path.join(passes_path, "combined")
        
        # Render
        print(f"[Style Engine] Auto-rendering from ai_camera...")
        bpy.ops.render.render(write_still=True)
        
        # Restore original settings
        scene.camera = original_camera
        scene.render.engine = original_engine
        scene.eevee.taa_render_samples = original_samples
        
        print(f"[Style Engine] Render complete - saved to: {passes_path}")
        
    except Exception as e:
        print(f"[Style Engine] Error in auto-render: {e}")
    
    # Continue running every RENDER_INTERVAL seconds
    return RENDER_INTERVAL


# ----------------------------------------------------------------
# STANDALONE HELPER FOR DELAYED WORKSPACE SPLIT
# ----------------------------------------------------------------

def _delayed_split_setup_standalone(camera):
    """
    Standalone function for delayed workspace split setup.
    Used to avoid operator lifetime issues with timer callbacks.
    """
    context = bpy.context
    
    # Find the 3D viewport in the current workspace
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            # Split the area vertically (left/right)
            override = {'area': area, 'region': area.regions[-1]}
            
            try:
                with context.temp_override(**override):
                    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
                
                # Configure the viewports
                view3d_areas = [a for a in context.screen.areas if a.type == 'VIEW_3D']
                
                if len(view3d_areas) >= 2:
                    # Right area (the new one): camera view
                    right_area = view3d_areas[-1]
                    
                    for space in right_area.spaces:
                        if space.type == 'VIEW_3D':
                            # Switch to camera view (like pressing Numpad 0)
                            space.region_3d.view_perspective = 'CAMERA'
                            space.lock_camera = True
                            
                            # Show background images in viewport
                            space.shading.type = 'SOLID'
                            
                            # Ensure camera is visible in viewport
                            space.overlay.show_extras = True
                            
                            print("[Style Engine] Right viewport configured as locked camera view")
                    
                    # Set the active object to the camera
                    if camera:
                        context.view_layer.objects.active = camera
                    
                    # Force redraw all areas
                    for area in context.screen.areas:
                        area.tag_redraw()
                
                break
            except Exception as e:
                print(f"[Style Engine] Error splitting viewport: {e}")
                print("[Style Engine] Please split viewport manually: drag from top-right corner")


class WM_OT_SetupWorkspace(bpy.types.Operator):
    """Setup the AI Vision workspace with dual 3D views and AI camera."""
    bl_idname = "style_engine.setup_workspace"
    bl_label = "Setup Workspace"
    bl_description = "Create AI Vision workspace with split view and AI camera"
    
    def execute(self, context):
        # Create temp directory for AI images
        self.ensure_temp_directory()
        
        # Create or get the AI camera
        ai_camera = self.create_ai_camera(context)
        
        # Position camera at current view
        self.align_camera_to_view(context, ai_camera)
        
        # Setup camera background image
        self.setup_camera_background(ai_camera)
        
        # Create the AI workspace
        workspace = self.create_ai_workspace(context)
        
        # Setup compositor
        self.setup_compositor(context)
        
        # Clear groups at session start
        self.clear_groups(context)
        
        # Write initial session.json
        write_session_json(context)
        
        # Setup the workspace layout
        if workspace:
            self.setup_workspace_layout(workspace, ai_camera)
            
            # Switch to the new workspace
            context.window.workspace = workspace
            
            self.report({'INFO'}, "AI Vision workspace created successfully!")
        else:
            self.report({'WARNING'}, "AI workspace already exists. Using existing workspace.")
        
        return {'FINISHED'}
    
    def ensure_temp_directory(self):
        """Create the data/temp/ai_vision directory if it doesn't exist."""
        # Use the addon's installation directory
        temp_path = os.path.join(ADDON_ROOT, "data", "temp", "ai_vision")
        os.makedirs(temp_path, exist_ok=True)
        
        print(f"[Style Engine] Temp directory: {temp_path}")
        
        # Create a placeholder image if it doesn't exist
        placeholder_path = os.path.join(temp_path, "current_ai.png")
        if not os.path.exists(placeholder_path):
            self.create_placeholder_image(placeholder_path)
        
        return temp_path
    
    def create_placeholder_image(self, path):
        """Create a placeholder image for testing."""
        # Create a simple colored image in Blender
        img = bpy.data.images.new("ai_placeholder", width=1920, height=1080)
        
        # Fill with a gradient or pattern (optional visual feedback)
        pixels = [0.1, 0.1, 0.2, 1.0] * (1920 * 1080)  # Dark blue
        img.pixels = pixels
        
        # Save it
        img.filepath_raw = path
        img.file_format = 'PNG'
        img.save()
        
        print(f"[Style Engine] Created placeholder image: {path}")
    
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
    
    def setup_camera_background(self, camera):
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
        
        # Use the addon's installation directory
        img_path = os.path.join(ADDON_ROOT, "data", "temp", "ai_vision", "current_ai.png")
        
        # Load or create the image
        if "current_ai.png" in bpy.data.images:
            img = bpy.data.images["current_ai.png"]
            img.filepath = img_path
            img.reload()
        else:
            if os.path.exists(img_path):
                img = bpy.data.images.load(img_path)
                img.name = "current_ai.png"
            else:
                # Create a placeholder
                img = bpy.data.images.new("current_ai.png", width=1920, height=1080)
        
        # Setup background image properties
        bg_img.image = img
        
        # Get opacity from properties (default to 1.0)
        props = bpy.context.scene.style_engine_props
        bg_img.alpha = props.background_opacity if hasattr(props, 'background_opacity') else 1.0
        
        bg_img.display_depth = 'FRONT'  # Display in front
        bg_img.frame_method = 'STRETCH'
        
        # Set render resolution to match image resolution
        img_width, img_height = img.size
        bpy.context.scene.render.resolution_x = img_width
        bpy.context.scene.render.resolution_y = img_height
        
        print(f"[Style Engine] Background image set: {img_path}")
        print(f"[Style Engine] Camera resolution set to: {img_width}x{img_height}")
    
    def create_ai_workspace(self, context):
        """Create the AI workspace or return existing one."""
        # Check if workspace already exists
        if "AI" in bpy.data.workspaces:
            print("[Style Engine] AI workspace already exists")
            return bpy.data.workspaces["AI"]
        
        # Duplicate the Layout workspace to create AI workspace
        layout_workspace = bpy.data.workspaces.get("Layout")
        
        if not layout_workspace:
            # If no Layout workspace, use the current one
            layout_workspace = context.workspace
        
        # Store the original name
        original_name = layout_workspace.name
        
        # Switch to Layout workspace
        context.window.workspace = layout_workspace
        
        # Duplicate the workspace using operator
        bpy.ops.workspace.duplicate()
        
        # After duplication, the ORIGINAL gets renamed to "Layout.001"
        # and the CURRENT workspace is still "Layout"
        # We need to swap their names
        
        # Current workspace is the original (now named something like "Layout")
        current_ws = context.workspace
        
        # Find the duplicate (should be named something like "Layout.001")
        duplicated_ws = None
        for ws in bpy.data.workspaces:
            if ws != current_ws and ws.name.startswith(original_name):
                duplicated_ws = ws
                break
        
        if duplicated_ws:
            # Rename duplicate to "AI"
            duplicated_ws.name = "AI"
            # Restore original name to the original workspace
            current_ws.name = original_name
            
            print(f"[Style Engine] Created new AI workspace from {original_name}")
            return duplicated_ws
        else:
            # Fallback if we couldn't find the duplicate
            current_ws.name = "AI"
            print(f"[Style Engine] Created AI workspace")
            return current_ws
    
    def setup_workspace_layout(self, workspace, camera):
        """Setup the split layout for the AI workspace."""
        print("[Style Engine] Configuring workspace layout...")
        
        # The actual split needs to happen after switching to the workspace
        # Use a standalone function to avoid operator lifetime issues
        def delayed_setup():
            _delayed_split_setup_standalone(camera)
            return None  # Don't repeat timer
        
        bpy.app.timers.register(delayed_setup, first_interval=0.1)
        
        # Start the auto-refresh timer for the background image
        self.start_image_refresh_timer()
    
    def delayed_split_setup(self, camera):
        """Delayed setup of the workspace split (called via timer)."""
        context = bpy.context
        
        # Find the 3D viewport in the current workspace
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                # Split the area vertically (left/right)
                override = {'area': area, 'region': area.regions[-1]}
                
                try:
                    with context.temp_override(**override):
                        bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
                    
                    # Configure the viewports
                    view3d_areas = [a for a in context.screen.areas if a.type == 'VIEW_3D']
                    
                    if len(view3d_areas) >= 2:
                        # Right area (the new one): camera view
                        right_area = view3d_areas[-1]
                        
                        for space in right_area.spaces:
                            if space.type == 'VIEW_3D':
                                # Switch to camera view (like pressing Numpad 0)
                                space.region_3d.view_perspective = 'CAMERA'
                                space.lock_camera = True
                                
                                # Show background images in viewport
                                space.shading.type = 'SOLID'
                                
                                # Ensure camera is visible in viewport
                                space.overlay.show_extras = True
                                
                                print("[Style Engine] Right viewport configured as locked camera view")
                        
                        # Set the active object to the camera
                        if camera:
                            context.view_layer.objects.active = camera
                        
                        # Force redraw all areas
                        for area in context.screen.areas:
                            area.tag_redraw()
                    
                    break
                except Exception as e:
                    print(f"[Style Engine] Error splitting viewport: {e}")
                    print("[Style Engine] Please split viewport manually: drag from top-right corner")
        
        # Don't repeat this timer
        return None
    
    def clear_groups(self, context):
        """Clear all groups at session start."""
        props = context.scene.style_engine_props
        props.object_groups.clear()
        props.active_group_index = 0
        props.group_counter = 1
        print("[Style Engine] Groups cleared for new session")
    
    def start_image_refresh_timer(self):
        """Start timers for auto-refresh and auto-render."""
        # Check if refresh_viewport is enabled
        props = bpy.context.scene.style_engine_props
        
        if props.refresh_viewport:
            # Start image refresh timer (checks for file changes)
            if not bpy.app.timers.is_registered(refresh_ai_image):
                bpy.app.timers.register(refresh_ai_image, first_interval=1.0, persistent=True)
                print("[Style Engine] Auto-refresh timer started")
            
            # Start auto-render timer (renders passes every X seconds)
            if not bpy.app.timers.is_registered(auto_render_passes):
                bpy.app.timers.register(auto_render_passes, first_interval=RENDER_INTERVAL, persistent=True)
                print(f"[Style Engine] Auto-render timer started (every {RENDER_INTERVAL}s)")
    
    def setup_compositor(self, context):
        """Setup the compositor nodes for render passes output."""
        scene = context.scene
        
        # Enable required render passes FIRST
        view_layer = context.view_layer
        view_layer.use_pass_mist = True  # Mist pass (instead of Z)
        view_layer.use_pass_ambient_occlusion = True  # AO
        
        # Configure Mist settings for better control
        scene.world.mist_settings.start = 0.0
        scene.world.mist_settings.depth = 100.0  # Adjust based on scene scale
        scene.world.mist_settings.falloff = 'LINEAR'
        
        # Enable compositor
        scene.use_nodes = True
        scene.render.use_compositing = True
        
        # Clear existing nodes
        nodes = scene.node_tree.nodes
        nodes.clear()
        
        # Create Render Layers node
        render_layers = nodes.new(type='CompositorNodeRLayers')
        render_layers.location = (0, 0)
        
        # Create Color Ramp node (inverts mist with tight range)
        color_ramp = nodes.new(type='CompositorNodeValToRGB')
        color_ramp.location = (400, -200)
        
        # Configure color ramp with inverted colors and tight range
        # Color stop 0: position 0.000, white (near)
        color_ramp.color_ramp.elements[0].position = 0.000
        color_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)  # White
        
        # Color stop 1: position 0.010, black (far)
        color_ramp.color_ramp.elements[1].position = 0.010
        color_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)  # Black
        
        # Create File Output node
        file_output = nodes.new(type='CompositorNodeOutputFile')
        file_output.location = (800, 0)
        
        # Set base path to ai_vision/ folder (absolute path from addon root)
        passes_path = os.path.join(ADDON_ROOT, "data", "temp", "ai_vision")
        os.makedirs(passes_path, exist_ok=True)
        # Use absolute path with forward slashes (Blender compatible)
        file_output.base_path = passes_path.replace("\\", "/") + "/"
        
        # Set format and overwrite settings
        file_output.format.file_format = 'PNG'
        file_output.format.color_mode = 'RGB'
        file_output.format.color_depth = '8'
        
        # Enable overwrite
        scene.render.use_overwrite = True
        scene.render.use_file_extension = True
        
        # Clear default inputs and add custom ones
        file_output.file_slots.clear()
        
        # Add output slots
        file_output.file_slots.new("combined")
        file_output.file_slots.new("depth")
        file_output.file_slots.new("id")
        file_output.file_slots.new("ao")
        file_output.file_slots.new("canny")
        
        # Create links
        links = scene.node_tree.links
        
        # Connect Render Layers Mist -> Color Ramp -> File Output (depth)
        links.new(render_layers.outputs['Mist'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Image'], file_output.inputs['depth'])
        
        # Connect other passes
        links.new(render_layers.outputs['Image'], file_output.inputs['combined'])
        links.new(render_layers.outputs['AO'], file_output.inputs['ao'])
        
        print(f"[Style Engine] Compositor setup complete")
        print(f"[Style Engine] Render passes output to: {passes_path}")
        print(f"[Style Engine] Enabled passes: Combined, Mist (depth), AO")
        print(f"[Style Engine] Mist range: 0.0 - 100.0, Color ramp: 0.000 (white) to 0.010 (black)")


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

def render_passes(context):
    """
    Render combined and depth passes from ai_camera.
    Outputs to data/temp/ai_vision/ folder for cloud generation.
    """
    print("[Style Engine] Rendering passes for cloud generation...")
    
    # Find the ai_camera
    if "ai_camera" not in bpy.data.objects:
        print("[Style Engine] ERROR: ai_camera not found! Run 'Setup Workspace' first.")
        raise RuntimeError("ai_camera not found. Please run 'Setup Workspace' first.")
    
    ai_camera = bpy.data.objects["ai_camera"]
    scene = context.scene
    
    # Store original settings
    original_camera = scene.camera
    original_engine = scene.render.engine
    original_samples = scene.eevee.taa_render_samples
    
    try:
        # Configure render settings
        scene.camera = ai_camera
        scene.render.engine = 'BLENDER_EEVEE_NEXT'  # Blender 4.2+ uses EEVEE_NEXT
        scene.eevee.taa_render_samples = 16
        
        # Set output path - compositor will handle the actual file outputs
        # The compositor nodes are configured to save:
        #   - combined0001.png (Combined pass)
        #   - depth0001.png (Depth pass - inverted)
        # to data/temp/ai_vision/
        
        # Render
        print(f"[Style Engine] Rendering from ai_camera...")
        bpy.ops.render.render(write_still=True, use_viewport=False)
        
        # Verify outputs exist
        addon_root = Path(ADDON_ROOT)
        combined_path = addon_root / "data" / "temp" / "ai_vision" / "combined0001.png"
        depth_path = addon_root / "data" / "temp" / "ai_vision" / "depth0001.png"
        
        if not combined_path.exists():
            print(f"[Style Engine] WARNING: Combined pass not found at {combined_path}")
        else:
            print(f"[Style Engine] ✓ Combined pass: {combined_path}")
        
        if not depth_path.exists():
            print(f"[Style Engine] WARNING: Depth pass not found at {depth_path}")
        else:
            print(f"[Style Engine] ✓ Depth pass: {depth_path}")
        
        print(f"[Style Engine] Render passes complete!")
        
    finally:
        # Restore original settings
        scene.camera = original_camera
        scene.render.engine = original_engine
        scene.eevee.taa_render_samples = original_samples


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
    
    # 1. Check if generation already in progress
    if runcomfy_polling.RunComfyPoller.active_requests:
        print("[Style Engine] Generation already in progress, skipping")
        return
    
    # 2. Render passes (same as local)
    render_passes(context)
    
    # 3. Read session data (create if doesn't exist)
    session_json_path = Path(ADDON_ROOT) / "data" / "temp" / "ai_vision" / "session.json"
    
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
    
    # 4. Encode images to base64
    addon_root = Path(ADDON_ROOT)
    combined_path = addon_root / "data" / "temp" / "ai_vision" / "combined0001.png"
    depth_path = addon_root / "data" / "temp" / "ai_vision" / "depth0001.png"
    
    if not combined_path.exists() or not depth_path.exists():
        print("[Style Engine] Render passes not found")
        return
    
    try:
        combined_b64 = runcomfy_client.encode_image_to_base64(str(combined_path))
        depth_b64 = runcomfy_client.encode_image_to_base64(str(depth_path))
    except runcomfy_client.RunComfyError as e:
        print(f"[Style Engine] Failed to encode images: {e}")
        return
    
    # 5. Determine workflow type
    use_ipadapter = session_data.get('ipadapter', {}).get('enabled', False)
    has_reference = session_data.get('ipadapter', {}).get('reference_image', '')
    workflow_type = 'ipadapter' if (use_ipadapter and has_reference) else 'sdxl'
    
    print(f"[Style Engine] Using workflow: {workflow_type}")
    
    # 6. Ensure deployment exists
    try:
        deployment_id = runcomfy_deployment.DeploymentManager.ensure_deployment(workflow_type)
    except runcomfy_client.RunComfyError as e:
        print(f"[Style Engine] Failed to ensure deployment: {e}")
        return
    
    # 7. Build overrides
    overrides = build_runcomfy_overrides(
        session_data=session_data,
        combined_b64=combined_b64,
        depth_b64=depth_b64,
        workflow_type=workflow_type
    )
    
    # 8. Submit inference
    try:
        client = runcomfy_deployment.get_runcomfy_client()
        response = client.submit_inference(deployment_id, overrides)
        request_id = response.get('request_id')
        
        # 9. Start polling
        runcomfy_polling.RunComfyPoller.start_polling(
            deployment_id=deployment_id,
            request_id=request_id,
            callback=lambda success, result=None, error=None, workflow_type=None: 
                on_generation_complete(context, success, result, error, workflow_type or 'sdxl'),
            workflow_type=workflow_type
        )
        
        print(f"[Style Engine] ☁️ Cloud generation started (request_id: {request_id[:8]}...)")
        
    except runcomfy_client.RunComfyError as e:
        print(f"[Style Engine] Failed to submit inference: {e}")


def build_runcomfy_overrides(session_data, combined_b64, depth_b64, workflow_type):
    """
    Build overrides dict for RunComfy API submission.
    
    Args:
        session_data: Session JSON data
        combined_b64: Base64 encoded combined pass
        depth_b64: Base64 encoded depth pass
        workflow_type: 'sdxl' or 'ipadapter'
    
    Returns:
        dict: Overrides for workflow nodes
    """
    from . import runcomfy_client
    
    if workflow_type == 'sdxl':
        # Map to SDXLworkflow.json nodes
        return {
            "25": {"inputs": {"value": session_data.get('global_prompt', '')}},  # Prompt
            "15": {"inputs": {"image": combined_b64}},  # Combined pass
            "40": {"inputs": {"value": session_data.get('silhouette_influence', 0.75)}},  # Canny
            "41": {"inputs": {"value": session_data.get('depth_influence', 0.5)}},  # Depth
            "42": {"inputs": {"value": session_data.get('steps', 15)}},  # Steps
        }
    else:  # ipadapter
        # Encode reference image
        ref_image_path = session_data['ipadapter']['reference_image']
        
        try:
            ref_image_b64 = runcomfy_client.encode_image_to_base64(ref_image_path)
        except Exception as e:
            print(f"[Style Engine] Failed to encode reference image: {e}")
            # Fall back to SDXL workflow
            return build_runcomfy_overrides(session_data, combined_b64, depth_b64, 'sdxl')
        
        # Map to IPAdapterworkflow.json nodes
        return {
            "25": {"inputs": {"value": session_data.get('global_prompt', '')}},
            "15": {"inputs": {"image": combined_b64}},
            "40": {"inputs": {"value": session_data.get('silhouette_influence', 0.75)}},
            "41": {"inputs": {"value": session_data.get('depth_influence', 0.5)}},
            "42": {"inputs": {"value": session_data.get('steps', 15)}},
            "43": {"inputs": {"image": ref_image_b64}},  # IPAdapter reference
            "52": {"inputs": {"value": session_data['ipadapter']['strength']}},
            # Note: Node 49 (IPAdapterEmbeds) weight_type cannot be overridden due to upstream connections
            # It uses the hardcoded value from the deployed workflow: "style transfer"
        }


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
    
    # Workflow-specific output node priority
    if workflow_type == 'ipadapter':
        # IPAdapter: Try Node 9 first (SaveImage - final output)
        if '9' in outputs and 'images' in outputs['9'] and outputs['9']['images']:
            image_url = outputs['9']['images'][0].get('url')
            print("[Style Engine] ✅ Using output from Node 9 (IPAdapter final SaveImage)")
        else:
            print("[Style Engine] ⚠️ Node 9 not found in IPAdapter mode, checking fallback...")
    else:
        # SDXL: Try Node 53 first (easy imageSave - final output)
        if '53' in outputs and 'images' in outputs['53'] and outputs['53']['images']:
            image_url = outputs['53']['images'][0].get('url')
            print("[Style Engine] ✅ Using output from Node 53 (SDXL final SaveImage)")
        else:
            print("[Style Engine] ⚠️ Node 53 not found in SDXL mode, checking fallback...")
    
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
    addon_root = Path(ADDON_ROOT)
    current_ai_path = addon_root / "data" / "temp" / "ai_vision" / "current_ai.png"
    
    print(f"[Style Engine] Downloading result from: {image_url[:50]}...")
    
    if runcomfy_client.download_image_from_url(image_url, str(current_ai_path)):
        print("[Style Engine] ✅ Downloaded to temp")
        
        # Update camera background
        refresh_ai_image()
        
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
    """
    try:
        props = bpy.context.scene.style_engine_props
        
        # Only continue if auto-generate is still enabled
        if hasattr(props, 'auto_generate') and props.auto_generate:
            print("[Style Engine] 🔄 Auto-generate enabled, starting next cycle...")
            # Small delay to prevent overwhelming the system
            bpy.app.timers.register(lambda: start_generation_cycle(), first_interval=1.0)
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
    # Stop the timers if they're running
    if bpy.app.timers.is_registered(refresh_ai_image):
        bpy.app.timers.unregister(refresh_ai_image)
    
    if bpy.app.timers.is_registered(auto_render_passes):
        bpy.app.timers.unregister(auto_render_passes)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

