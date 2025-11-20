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
        default=True
    )
    
    show_image_generation: bpy.props.BoolProperty(
        name="Show Image Generation",
        description="Expand or collapse the image generation section",
        default=True
    )
    
    show_settings: bpy.props.BoolProperty(
        name="Show Settings",
        description="Expand or collapse the settings section",
        default=False
    )
    
    show_groups: bpy.props.BoolProperty(
        name="Groups",
        description="Expand or collapse the groups section",
        default=True
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
        default=0.75,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    texture_influence: bpy.props.FloatProperty(
        name="Texture Influence",
        description="Controls denoise strength in img2img workflow (GCS mode). 0.0 = keep 100% of render, 1.0 = full AI generation ignoring render",
        default=0.0,
        min=0.0,
        max=1.0,
        update=update_session_json
    )
    
    steps: bpy.props.IntProperty(
        name="Steps",
        description="Number of sampling steps for AI generation (15-30)",
        default=15,
        min=15,
        max=30,
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
        description="Use template-based prompt building with structured tags (subject, style, mood, etc.)",
        default=False,
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
        default=0.7,
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
    
    # Global strength sliders
    style_transfer_strength: bpy.props.FloatProperty(
        name="Style Transfer Strength",
        description="Global strength for all Style Transfer images (0.0 to 5.0)",
        default=0.0,
        min=0.0,
        max=5.0,
        update=update_session_json
    )
    
    composition_strength: bpy.props.FloatProperty(
        name="Composition Strength",
        description="Global strength for all Composition images (0.0 to 5.0)",
        default=0.0,
        min=0.0,
        max=5.0,
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


# ----------------------------------------------------------------
# 2. OPERATORS
# ----------------------------------------------------------------
# Legacy operators removed - no longer needed


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
    """Project AI texture onto all objects from camera view."""
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
        
        # Make sure we're in object mode
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Get all mesh objects
        mesh_objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects found in scene")
            return {'CANCELLED'}
        
        # Create or get the shared material
        mat_name = "projected_material"
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
            # Update the image in existing material
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    node.image = img
        else:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            
            # Clear default nodes
            nodes.clear()
            
            # Create Principled BSDF
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)
            
            # Create Image Texture node
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (-300, 0)
            tex_node.image = img
            
            # Create Material Output
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (300, 0)
            
            # Connect nodes
            links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
            links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        # Set ai_camera as the scene camera temporarily
        context.scene.camera = ai_camera
        
        projected_count = 0
        
        for obj in mesh_objects:
            try:
                # Assign material to object
                if len(obj.data.materials) == 0:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat
                
                # Deselect all
                for o in context.selected_objects:
                    o.select_set(False)
                
                # Select and activate this object
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                # Enter edit mode for this specific object
                bpy.ops.object.mode_set(mode='EDIT')
                
                # Select all faces
                bpy.ops.mesh.select_all(action='SELECT')
                
                # Project from camera view
                bpy.ops.uv.project_from_view(
                    camera_bounds=True,
                    correct_aspect=True,
                    scale_to_bounds=False
                )
                
                # Return to object mode
                bpy.ops.object.mode_set(mode='OBJECT')
                
                projected_count += 1
                print(f"[Style Engine] ✓ Projected texture on {obj.name}")
                
            except Exception as e:
                print(f"[Style Engine] ✗ Error projecting texture on {obj.name}: {e}")
                # Make sure we're back in object mode
                if context.object and context.object.mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode='OBJECT')
                    except:
                        pass
                continue
        
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
        
        self.report({'INFO'}, f"Projected texture onto {projected_count} objects from AI camera")
        print(f"[Style Engine] 🎨 Projected texture onto {projected_count} objects")
        
        # Create iteration snapshot
        self.create_iteration_snapshot(context, mesh_objects)
        
        return {'FINISHED'}
    
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
# REFERENCE IMAGE OPERATORS
# ================================================================

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
            
            # Auto-enable by setting weight to 1.0 (user can adjust)
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
# PROMPT BUILDER TEMPLATE OPERATORS
# ----------------------------------------------------------------

class WM_OT_LoadTemplates(bpy.types.Operator):
    """Load all prompt templates into text editor"""
    bl_idname = "style_engine.load_templates"
    bl_label = "Load Templates"
    bl_description = "Load all prompt templates from templates folder into Blender's text editor"
    
    def execute(self, context):
        from . import utils
        
        count, message = utils.load_all_templates()
        
        if count > 0:
            self.report({'INFO'}, message)
            print(f"[Style Engine] {message}")
        else:
            self.report({'WARNING'}, message)
            print(f"[Style Engine] {message}")
        
        return {'FINISHED'}


class WM_OT_SavePromptAsTemplate(bpy.types.Operator):
    """Save currently active text editor content as a template"""
    bl_idname = "style_engine.save_prompt_as_template"
    bl_label = "Save as Template"
    bl_description = "Save the currently open text editor content as a reusable template"
    
    template_name: bpy.props.StringProperty(
        name="Template Name",
        description="Name for the new template (will be prefixed with STYLEENGINE_)",
        default="My_Template"
    )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        
        # Show which text block will be saved
        active_text_name = None
        for area in context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                for space in area.spaces:
                    if space.type == 'TEXT_EDITOR' and space.text:
                        active_text_name = space.text.name
                        break
                if active_text_name:
                    break
        
        if not active_text_name:
            active_text_name = "STYLEENGINE_Prompt (fallback)"
        
        info_box = layout.box()
        info_box.label(text=f"Source: {active_text_name}", icon='TEXT')
        
        layout.separator()
        layout.prop(self, "template_name")
        layout.label(text="Will be saved as: STYLEENGINE_{name}.txt", icon='DISK_DRIVE')
    
    def execute(self, context):
        from . import utils
        
        success, message = utils.save_current_prompt_as_template(self.template_name)
        
        if success:
            self.report({'INFO'}, message)
            print(f"[Style Engine] {message}")
        else:
            self.report({'ERROR'}, message)
            print(f"[Style Engine] {message}")
        
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

        # --- Output Path (VISIBLE) ---
        output_box = layout.box()
        output_box.label(text="Output Path:", icon='FILE_FOLDER')
        output_box.prop(style_props, "output_path", text="")

        # --- Generation Status (MINIMAL) ---
        try:
            from . import runcomfy_polling
            from . import runcomfy_deployment
            
            # Only show status if using GCS mode
            prefs = context.preferences.addons['styleengine'].preferences
            if hasattr(prefs, 'api_backend') and prefs.api_backend == 'GCS':
                status = runcomfy_polling.RunComfyPoller.get_status_summary()
                
                # Only show box if generating or if we have last generation time
                if status['is_generating'] or status['last_generation_time'] > 0:
                    layout.separator()
                    status_box = layout.box()
                    row = status_box.row()
                    
                    if status['is_generating']:
                        # Show current generation status
                        icon = 'RENDER_ANIMATION' if status['status_text'] == 'Generating' else 'TIME'
                        row.label(text=f"{status['status_text']}: {status['elapsed']}s", icon=icon)
                    else:
                        # Show idle status with last generation time
                        row.label(text="Ready", icon='CHECKMARK')
                    
                    # Show last generation time if available
                    if status['last_generation_time'] > 0:
                        row = status_box.row()
                        row.scale_y = 0.8
                        row.label(text=f"Previous: {status['last_generation_time']}s", icon='SORTTIME')
        except Exception as e:
            # Silently fail if status unavailable
            pass

        # --- Prompt Builder (VISIBLE) ---
        layout.separator()
        prompt_box = layout.box()
        prompt_box.label(text="Prompt Settings:", icon='TEXT')
        
        # Prompt Builder checkbox
        row = prompt_box.row()
        row.prop(style_props, "use_prompt_builder", icon='SYNTAX_ON' if style_props.use_prompt_builder else 'SYNTAX_OFF')
        
        # Show template controls when enabled
        if style_props.use_prompt_builder:
            # Template management buttons
            prompt_box.separator()
            template_row = prompt_box.row(align=True)
            template_row.operator("style_engine.load_templates", icon='IMPORT', text="Load Templates")
            template_row.operator("style_engine.save_prompt_as_template", icon='FILE_TICK', text="Save Template")
            
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
        
        # --- Reference Images - COLLAPSIBLE ---
        layout.separator()
        ref_box = layout.box()
        header_row = ref_box.row(align=True)
        header_row.label(text="Reference Images", icon='IMAGE_DATA')
            
        # Helper function to draw a reference image section
        def draw_reference_section(box, title, icon, show_prop, slots, strength_prop):
            """Draw a collapsible reference image section with grid layout"""
            section_box = box.box()
            header = section_box.row(align=True)
            icon_tri = 'TRIA_DOWN' if getattr(style_props, show_prop) else 'TRIA_RIGHT'
            header.prop(style_props, show_prop, text=title, icon=icon_tri, emboss=False, toggle=True)
        
            if getattr(style_props, show_prop):
                # Global strength slider
                section_box.separator()
                strength_row = section_box.row()
                strength_row.scale_y = 1.5
                strength_row.prop(style_props, strength_prop, text="Global Strength", slider=True)
                
                section_box.separator()
                
                # Grid layout for images (3 columns)
                grid = section_box.grid_flow(
                    row_major=True,
                    columns=3,
                    even_columns=True,
                    even_rows=True,
                    align=True
                )
                
                # Draw each slot
                for slot_id, img_prop, weight_prop, label in slots:
                    img = getattr(style_props, img_prop)
            
                    # Card for each slot
                    card = grid.box()
                    card.scale_y = 1.0
                    
                    if img:
                        # Image exists - show preview and controls
                        col = card.column(align=True)
            
                        # Image thumbnail using template_icon
                        # This displays the actual image content as an icon
                        preview_box = col.box()
                        preview_col = preview_box.column(align=True)
                        
                        # Display image thumbnail using preview collection (Poliigon method)
                        try:
                            # Get the persistent preview collection
                            pcoll = preview_collections.get("ref_images")
                            
                            if pcoll is None:
                                preview_col.label(text="[No Collection]", icon='ERROR')
                            else:
                                # Generate unique key for this image
                                thumb_key = f"{slot_id}_{img.name}"
                                
                                # Load thumbnail into preview collection if not already loaded
                                if thumb_key not in pcoll:
                                    if img.filepath:
                                        abs_path = bpy.path.abspath(img.filepath)
                                        try:
                                            pcoll.load(thumb_key, abs_path, 'IMAGE')
                                        except Exception as e:
                                            print(f"[UI] Failed to load preview for {img.name}: {e}")
                                
                                # Display the thumbnail using template_icon
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
                            print(f"[UI] Error displaying thumbnail for {img.name}: {e}")
                        
                        col.separator(factor=0.2)
                    
                        # Slot label and image name
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
                    
                        # Weight slider
                        col.prop(style_props, weight_prop, text="", slider=True)
                        
                        col.separator(factor=0.2)
                    
                        # Action buttons (reload and clear)
                        btn_row = col.row(align=True)
                        btn_row.scale_y = 0.7
                        reload_op = btn_row.operator("style_engine.reload_reference", text="", icon='FILE_REFRESH')
                        reload_op.slot = slot_id
                        clear_op = btn_row.operator("style_engine.clear_reference", text="", icon='X')
                        clear_op.slot = slot_id
                    else:
                        # Empty slot - show add button
                        col = card.column(align=True)
                        col.scale_y = 2.5
                        col.separator()
                        load_op = col.operator("style_engine.load_reference", 
                                             text=f"{label}\n+", 
                                             icon='ADD',
                                             emboss=True)
                        load_op.slot = slot_id
                        col.separator()
        
        # Style Transfer section
        st_slots = [
            ("st1", "st1_image", "st1_weight", "ST1"),
            ("st2", "st2_image", "st2_weight", "ST2"),
            ("st3", "st3_image", "st3_weight", "ST3"),
            ("st4", "st4_image", "st4_weight", "ST4"),
            ("st5", "st5_image", "st5_weight", "ST5"),
        ]
        draw_reference_section(ref_box, "Style", 'BRUSH_DATA', 
                             "show_style_transfer", st_slots, "style_transfer_strength")
        
        # Composition section
        comp_slots = [
            ("comp1", "comp1_image", "comp1_weight", "COMP1"),
            ("comp2", "comp2_image", "comp2_weight", "COMP2"),
            ("comp3", "comp3_image", "comp3_weight", "COMP3"),
            ("comp4", "comp4_image", "comp4_weight", "COMP4"),
            ("comp5", "comp5_image", "comp5_weight", "COMP5"),
        ]
        draw_reference_section(ref_box, "Composition", 'MESH_GRID', 
                             "show_composition", comp_slots, "composition_strength")
        
        # Transfer section (Force Style Transfer)
        sst_slots = [
            ("sst1", "sst1_image", "sst1_weight", "SST1"),
            ("sst2", "sst2_image", "sst2_weight", "SST2"),
            ("sst3", "sst3_image", "sst3_weight", "SST3"),
            ("sst4", "sst4_image", "sst4_weight", "SST4"),
            ("sst5", "sst5_image", "sst5_weight", "SST5"),
        ]
        draw_reference_section(ref_box, "Transfer", 'FORCE_FORCE', 
                             "show_force_transfer", sst_slots, "force_transfer_strength")
        
        # # --- Settings - COLLAPSIBLE --- COMMENTED OUT
        # layout.separator()
        # settings_box = layout.box()
        # header_row = settings_box.row(align=True)
        # icon = 'TRIA_DOWN' if style_props.show_settings else 'TRIA_RIGHT'
        # header_row.prop(style_props, "show_settings", text="Settings", icon=icon, emboss=False, toggle=True)
        # 
        # if style_props.show_settings:
        #     # Test Workflow button (formerly Generate Cloud, moved from Image Generation)
        #     settings_box.operator("style_engine.test_cloud_generation", text="Test Workflow", icon='EXPERIMENTAL')
        #     
        #     settings_box.separator()
        #     settings_box.label(text="(Advanced settings in addon preferences)", icon='INFO')

        # Legacy action buttons removed (Visualize, Create 3D, Render)


# ----------------------------------------------------------------
# 4. REGISTRATION
# ----------------------------------------------------------------
classes = (
    ObjectGroup,
    StyleEngineProperties,
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
    WM_OT_LoadReferenceImage,
    WM_OT_ClearReferenceImage,
    WM_OT_ReloadReferenceImage,
    WM_OT_CancelGeneration,
    WM_OT_TestCloudGeneration,
    WM_OT_LoadTemplates,
    WM_OT_SavePromptAsTemplate,
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