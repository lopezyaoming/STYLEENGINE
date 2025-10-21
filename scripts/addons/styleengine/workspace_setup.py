# ================================================================
#    Style Engine - Workspace Setup
#    Creates the AI Vision dual-workspace layout
# ================================================================

import bpy
import os
from pathlib import Path

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


def refresh_ai_image():
    """
    Auto-refresh timer function that checks if current_ai.png has been updated
    and reloads it in Blender if necessary.
    """
    global _last_image_mtime
    
    try:
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
        bg_img.alpha = 1.0  # 100% opacity
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
        # We need to use the operator method since workspaces can't be created directly
        layout_workspace = bpy.data.workspaces.get("Layout")
        
        if not layout_workspace:
            # If no Layout workspace, use the current one
            layout_workspace = context.workspace
        
        # Set the current workspace as the one to duplicate
        original_workspace = context.workspace
        context.window.workspace = layout_workspace
        
        # Duplicate the workspace using operator
        bpy.ops.workspace.duplicate()
        
        # The duplicated workspace will be the current one now
        duplicated_workspace = context.workspace
        duplicated_workspace.name = "AI"
        
        print(f"[Style Engine] Created new AI workspace from {layout_workspace.name}")
        return duplicated_workspace
    
    def setup_workspace_layout(self, workspace, camera):
        """Setup the split layout for the AI workspace."""
        print("[Style Engine] Configuring workspace layout...")
        
        # The actual split needs to happen after switching to the workspace
        # We'll use a timer to do this
        bpy.app.timers.register(
            lambda: self.delayed_split_setup(camera),
            first_interval=0.1
        )
        
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
                                space.region_3d.view_perspective = 'CAMERA'
                                space.lock_camera = True
                                
                                # Show background images in viewport
                                space.shading.type = 'SOLID'
                                
                                print("[Style Engine] Right viewport configured as locked camera view")
                        
                        # Force redraw
                        for area in context.screen.areas:
                            area.tag_redraw()
                    
                    break
                except Exception as e:
                    print(f"[Style Engine] Error splitting viewport: {e}")
                    print("[Style Engine] Please split viewport manually: drag from top-right corner")
        
        # Don't repeat this timer
        return None
    
    def start_image_refresh_timer(self):
        """Start a timer to auto-refresh the AI image when it changes."""
        if not bpy.app.timers.is_registered(refresh_ai_image):
            bpy.app.timers.register(refresh_ai_image, first_interval=1.0, persistent=True)
            print("[Style Engine] Auto-refresh timer started")
    
    def setup_compositor(self, context):
        """Setup the compositor nodes for render passes output."""
        scene = context.scene
        
        # Enable required render passes FIRST
        view_layer = context.view_layer
        view_layer.use_pass_z = True  # Depth (Z)
        view_layer.use_pass_ambient_occlusion = True  # AO
        
        # Enable compositor
        scene.use_nodes = True
        scene.render.use_compositing = True
        
        # Clear existing nodes
        nodes = scene.node_tree.nodes
        nodes.clear()
        
        # Create Render Layers node
        render_layers = nodes.new(type='CompositorNodeRLayers')
        render_layers.location = (0, 0)
        
        # Create Normalize node for depth
        normalize = nodes.new(type='CompositorNodeNormalize')
        normalize.location = (300, -200)
        
        # Create Color Ramp node (flips the depth mapping)
        color_ramp = nodes.new(type='CompositorNodeValToRGB')
        color_ramp.location = (500, -200)
        
        # Configure color ramp to flip depth (white to black)
        color_ramp.color_ramp.elements[0].position = 0.0
        color_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)  # White at start
        color_ramp.color_ramp.elements[1].position = 1.0
        color_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)  # Black at end
        
        # Create File Output node
        file_output = nodes.new(type='CompositorNodeOutputFile')
        file_output.location = (800, 0)
        
        # Set base path to passes/ folder (relative to blend file or project root)
        passes_path = os.path.join(ADDON_ROOT, "data", "temp", "passes")
        os.makedirs(passes_path, exist_ok=True)
        file_output.base_path = "//..\\data\\temp\\passes\\"
        
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
        
        # Connect Render Layers -> Normalize -> Color Ramp -> File Output (depth)
        links.new(render_layers.outputs['Depth'], normalize.inputs['Value'])
        links.new(normalize.outputs['Value'], color_ramp.inputs['Fac'])
        links.new(color_ramp.outputs['Image'], file_output.inputs['depth'])
        
        # Connect other passes
        links.new(render_layers.outputs['Image'], file_output.inputs['combined'])
        links.new(render_layers.outputs['AO'], file_output.inputs['ao'])
        
        print(f"[Style Engine] Compositor setup complete")
        print(f"[Style Engine] Render passes output to: {passes_path}")
        print(f"[Style Engine] Enabled passes: Combined, Depth (Z), AO")


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
    # Stop the timer if it's running
    if bpy.app.timers.is_registered(refresh_ai_image):
        bpy.app.timers.unregister(refresh_ai_image)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

