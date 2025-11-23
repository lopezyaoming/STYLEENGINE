# ================================================================
#    Style Engine - Main Pie Menu
#    Alt+W hotkey for quick access to all Style Engine features
# ================================================================

import bpy
from bpy.types import Menu, Operator


# ----------------------------------------------------------------
# PLACEHOLDER OPERATORS (To be implemented later)
# ----------------------------------------------------------------

class WM_OT_ProjectTextureUV(Operator):
    """Project AI texture onto selected objects using UV mapping"""
    bl_idname = "style_engine.project_texture_uv"
    bl_label = "Project in Object UV"
    bl_description = "Project current_ai.png onto selected objects using UV coordinates"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "UV projection not yet implemented - placeholder")
        # TODO: Implement UV-based texture projection
        return {'FINISHED'}


class WM_OT_ProjectTextureScene(Operator):
    """Project AI texture onto selected objects from camera view"""
    bl_idname = "style_engine.project_texture_scene"
    bl_label = "Project on Object"
    bl_description = "Project current_ai.png from camera perspective onto selected objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Use the existing project_texture operator which does camera projection
        bpy.ops.style_engine.project_texture()
        return {'FINISHED'}


class WM_OT_SetVisualization(Operator):
    """Switch camera background visualization type"""
    bl_idname = "style_engine.set_visualization"
    bl_label = "Set Visualization"
    bl_description = "Switch between Combined, Silhouette (Canny), and Depth visualizations"
    bl_options = {'REGISTER', 'UNDO'}
    
    viz_type: bpy.props.EnumProperty(
        name="Visualization Type",
        items=[
            ('COMBINED', "Combined", "Final generated image"),
            ('CANNY', "Silhouette", "Canny edge detection"),
            ('DEPTH', "Depth", "Depth map"),
        ],
        default='COMBINED'
    )
    
    def execute(self, context):
        style_props = context.scene.style_engine_props
        style_props.visualization_type = self.viz_type
        return {'FINISHED'}


class WM_OT_SetRenderQuality(Operator):
    """Set render quality for AI generation"""
    bl_idname = "style_engine.set_render_quality"
    bl_label = "Set Render Quality"
    bl_description = "Choose between Fast (Workbench) or Detailed (EEVEE) render quality"
    bl_options = {'REGISTER', 'UNDO'}
    
    quality: bpy.props.EnumProperty(
        name="Quality",
        items=[
            ('FAST', "Fast", "Workbench render - fast preview quality"),
            ('DETAILED', "Detailed", "EEVEE render - high quality for img2img"),
        ],
        default='FAST'
    )
    
    def execute(self, context):
        style_props = context.scene.style_engine_props
        style_props.render_quality = self.quality
        
        if self.quality == 'FAST':
            self.report({'INFO'}, "Render Quality: Fast (Workbench)")
        else:
            self.report({'INFO'}, "Render Quality: Detailed (EEVEE)")
        
        return {'FINISHED'}


class WM_OT_PrevGeneration(Operator):
    """Navigate to previous generation"""
    bl_idname = "style_engine.prev_generation"
    bl_label = "Previous Generation"
    bl_description = "Load previous generation to current_ai.png"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of generations
        generations = workspace_setup.get_generation_list(context)
        
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_generation_index == -1:
            # Currently at latest, go to second-to-last
            new_index = len(generations) - 2
        else:
            # Go one step back (older)
            new_index = style_props.current_generation_index - 1
        
        # Clamp to valid range
        new_index = max(0, min(new_index, len(generations) - 1))
        
        # Load the generation
        if workspace_setup.load_generation_to_current(context, generations[new_index]):
            style_props.current_generation_index = new_index
            self.report({'INFO'}, f"Generation {new_index + 1}/{len(generations)}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "Failed to load generation")
            return {'CANCELLED'}


class WM_OT_NextGeneration(Operator):
    """Navigate to next generation"""
    bl_idname = "style_engine.next_generation"
    bl_label = "Next Generation"
    bl_description = "Load next generation to current_ai.png"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import workspace_setup
        
        style_props = context.scene.style_engine_props
        
        # Get list of generations
        generations = workspace_setup.get_generation_list(context)
        
        if not generations:
            self.report({'WARNING'}, "No generations found")
            return {'CANCELLED'}
        
        # Handle index (-1 means latest/newest)
        if style_props.current_generation_index == -1:
            # Already at latest
            self.report({'INFO'}, f"Already at latest generation")
            return {'CANCELLED'}
        
        # Go one step forward (newer)
        new_index = style_props.current_generation_index + 1
        
        # Check if we've reached the latest
        if new_index >= len(generations) - 1:
            new_index = -1  # Back to "latest" mode
        
        # Load the generation
        if new_index == -1:
            # Load the latest generation
            if workspace_setup.load_generation_to_current(context, generations[-1]):
                style_props.current_generation_index = -1
                self.report({'INFO'}, f"Latest generation")
                return {'FINISHED'}
        else:
            if workspace_setup.load_generation_to_current(context, generations[new_index]):
                style_props.current_generation_index = new_index
                self.report({'INFO'}, f"Generation {new_index + 1}/{len(generations)}")
                return {'FINISHED'}
        
        self.report({'ERROR'}, "Failed to load generation")
        return {'CANCELLED'}


# ----------------------------------------------------------------
# MAIN PIE MENU
# ----------------------------------------------------------------

class STYLEENGINE_MT_pie_main(Menu):
    """Style Engine Main Pie Menu - Alt+W"""
    bl_label = "Style Engine"
    bl_idname = "STYLEENGINE_MT_pie_main"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        style_props = context.scene.style_engine_props
        
        # ═══════════════════════════════════════════════════
        # Position 0: TOP (NORTH) - Project Texture
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        col.scale_y = 1.1
        
        # Header
        row = col.row()
        row.label(text="Project Texture", icon='TEXTURE')
        col.separator()
        
        # Buttons
        # UV projection - commented out for now
        # col.operator("style_engine.project_texture_uv", 
        #              text="Project in Object UV", 
        #              icon='UV')
        col.operator("style_engine.project_texture_scene", 
                     text="Project on Object", 
                     icon='CAMERA_DATA')
        
        # ═══════════════════════════════════════════════════
        # Position 1: LEFT (WEST) - Setup Workspace
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        col.scale_y = 1.1
        
        # Header
        row = col.row()
        row.label(text="Setup Workspace", icon='WORKSPACE')
        col.separator()
        
        # Setup button
        row = col.row()
        row.scale_y = 1.5
        row.operator("style_engine.setup_workspace", 
                     text="Setup Workspace", 
                     icon='PLAY')
        col.separator()
        
        # Background opacity
        col.label(text="Background Opacity")
        col.prop(style_props, "background_opacity", text="", slider=True)
        col.separator()
        
        # Resolution
        col.label(text="Resolution")
        col.prop(style_props, "ai_resolution", text="")
        
        # ═══════════════════════════════════════════════════
        # Position 2: BOTTOM (SOUTH) - Generate Image
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        
        # Big generate button
        row = col.row()
        row.scale_y = 2.5
        row.operator("style_engine.generate_ai_quick", 
                     text="Generate Image", 
                     icon='IMAGE_DATA')
        
        col.separator()
        
        # Influence sliders section
        influence_box = col.box()
        influence_col = influence_box.column(align=True)
        influence_col.label(text="Influences", icon='SMOOTHCURVE')
        
        influence_col.prop(style_props, "silhouette_influence", 
                          text="Silhouette", slider=True)
        influence_col.prop(style_props, "depth_influence", 
                          text="Depth", slider=True)
        influence_col.prop(style_props, "texture_influence", 
                          text="Influence", slider=True)
        
        col.separator()
        
        # Steps
        col.label(text="Steps", icon='SORTTIME')
        col.prop(style_props, "steps", text="", slider=True)
        
        col.separator()
        
        # Autogenerate toggle
        row = col.row()
        row.scale_y = 1.5
        row.prop(style_props, "auto_generate", 
                 text="Autogenerate", 
                 toggle=True, 
                 icon='FILE_REFRESH')
        
        col.separator()
        
        # Render Quality selector
        quality_box = col.box()
        quality_col = quality_box.column(align=True)
        quality_col.label(text="Render Quality", icon='SHADING_RENDERED')
        
        # Two buttons: Fast (Workbench) and Detailed (EEVEE)
        row = quality_col.row(align=True)
        row.scale_y = 1.3
        
        # Fast button
        op = row.operator("style_engine.set_render_quality", 
                         text="Fast", 
                         icon='SHADING_WIRE',
                         depress=(style_props.render_quality == 'FAST'))
        op.quality = 'FAST'
        
        # Detailed button
        op = row.operator("style_engine.set_render_quality", 
                         text="Detailed", 
                         icon='SHADING_RENDERED',
                         depress=(style_props.render_quality == 'DETAILED'))
        op.quality = 'DETAILED'
        
        quality_col.separator(factor=0.5)
        
        # Show description based on current selection
        if style_props.render_quality == 'FAST':
            quality_col.label(text="Workbench - Quick iterations", icon='INFO')
        else:
            quality_col.label(text="EEVEE - Better for img2img", icon='INFO')
        
        # ═══════════════════════════════════════════════════
        # Position 3: RIGHT (EAST) - Visualization Type
        # ═══════════════════════════════════════════════════
        # Check if preview images are enabled
        prefs = context.preferences.addons.get('styleengine')
        show_visualization = (prefs and 
                             prefs.preferences.api_backend == 'GCS' and 
                             prefs.preferences.gcs_download_preview_images)
        
        if show_visualization:
            # Show Visualization Type switcher
            box = pie.box()
            col = box.column(align=True)
            col.scale_y = 1.1
            
            # Header
            row = col.row()
            row.label(text="Visualization", icon='VIEW_CAMERA')
            col.separator()
            
            # Visualization type buttons
            row = col.row(align=True)
            row.scale_y = 1.5
            
            # Combined button
            op = row.operator("style_engine.set_visualization", 
                             text="Combined", 
                             icon='IMAGE_DATA',
                             depress=(style_props.visualization_type == 'COMBINED'))
            op.viz_type = 'COMBINED'
            
            # Silhouette button
            op = row.operator("style_engine.set_visualization", 
                             text="Silhouette", 
                             icon='MESH_PLANE',
                             depress=(style_props.visualization_type == 'CANNY'))
            op.viz_type = 'CANNY'
            
            # Depth button
            op = row.operator("style_engine.set_visualization", 
                             text="Depth", 
                             icon='EMPTY_SINGLE_ARROW',
                             depress=(style_props.visualization_type == 'DEPTH'))
            op.viz_type = 'DEPTH'
            
            col.separator()
            
            # Show current visualization
            col.label(text=f"Current: {style_props.visualization_type.title()}", icon='INFO')
            
            # ═══════════════════════════════════════════════════
            # Generation Browser - Navigate Through Saved Generations
            # ═══════════════════════════════════════════════════
            col.separator()
            col.label(text="Generation Browser", icon='RENDERLAYERS')
            
            # Get generation info
            from . import workspace_setup
            generations = workspace_setup.get_generation_list(context)
            
            if generations:
                # Navigation buttons
                row = col.row(align=True)
                row.scale_y = 1.3
                
                # Check if at boundaries
                at_oldest = (style_props.current_generation_index == 0)
                at_latest = (style_props.current_generation_index == -1)
                
                # Previous button (go to older)
                prev_row = row.row(align=True)
                prev_row.enabled = not at_oldest  # Disable if at oldest
                prev_row.operator("style_engine.prev_generation", 
                                 text="", 
                                 icon='TRIA_LEFT')
                
                # Current generation indicator
                if at_latest:
                    current_text = f"Latest ({len(generations)})"
                else:
                    current_text = f"{style_props.current_generation_index + 1}/{len(generations)}"
                
                row.label(text=current_text)
                
                # Next button (go to newer)
                next_row = row.row(align=True)
                next_row.enabled = not at_latest  # Disable if at latest
                next_row.operator("style_engine.next_generation", 
                                 text="", 
                                 icon='TRIA_RIGHT')
            else:
                col.label(text="No generations yet", icon='INFO')
        
        else:
            # Fallback: empty box or placeholder
            box = pie.box()
            col = box.column(align=True)
            col.scale_y = 1.1
            
            row = col.row()
            row.label(text="Visualization", icon='VIEW_CAMERA')
            col.separator()
            
            col.label(text="Enable 'Download Preview", icon='INFO')
            col.label(text="Images' in GCS settings")
            col.label(text="to use this feature")


# ----------------------------------------------------------------
# Registration
# ----------------------------------------------------------------

classes = (
    WM_OT_ProjectTextureUV,
    WM_OT_ProjectTextureScene,
    WM_OT_SetVisualization,
    WM_OT_SetRenderQuality,
    WM_OT_PrevGeneration,
    WM_OT_NextGeneration,
    STYLEENGINE_MT_pie_main,
)

addon_keymaps = []


def register():
    """Register pie menu and Alt+W hotkey"""
    
    # Register classes
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass  # Already registered
    
    # Register keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        # Register for 3D View (works in Object Mode, Sculpt, etc.)
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
        kmi.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km, kmi))
        
        # ALSO register for Mesh (Edit Mode) - conflict-free with Blender & HEAVYPOLY
        # Blender uses W alone (Select menu), HEAVYPOLY doesn't use Alt+W
        # Our Alt+W is completely free and ergonomic (W = Workflow!)
        km_mesh = kc.keymaps.new(name='Mesh', space_type='VIEW_3D')
        kmi_mesh = km_mesh.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
        kmi_mesh.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km_mesh, kmi_mesh))
        
        # Also register for other edit modes (Curve, Armature, etc.)
        for mode_name in ['Curve', 'Armature', 'Pose', 'Sculpt']:
            km_mode = kc.keymaps.new(name=mode_name, space_type='VIEW_3D')
            kmi_mode = km_mode.keymap_items.new('wm.call_menu_pie', 'W', 'PRESS', alt=True)
            kmi_mode.properties.name = "STYLEENGINE_MT_pie_main"
            addon_keymaps.append((km_mode, kmi_mode))
        
        print("[Style Engine] ✅ Pie menu registered (Alt+W) for all modes - macOS/Windows/Linux compatible")


def unregister():
    """Unregister pie menu and hotkey"""
    
    # Unregister keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Unregister classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
    
    print("[Style Engine] ✅ Pie menu unregistered")


if __name__ == "__main__":
    register()

