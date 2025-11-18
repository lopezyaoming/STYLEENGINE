# ================================================================
#    Style Engine - Main Pie Menu
#    Alt+Shift+E hotkey for quick access to all Style Engine features
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
    bl_label = "Project in Scene"
    bl_description = "Project current_ai.png from camera perspective onto scene geometry"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Use the existing project_texture operator which does camera projection
        bpy.ops.style_engine.project_texture()
        return {'FINISHED'}


# ----------------------------------------------------------------
# MAIN PIE MENU
# ----------------------------------------------------------------

class STYLEENGINE_MT_pie_main(Menu):
    """Style Engine Main Pie Menu - Alt+Shift+E"""
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
        col.operator("style_engine.project_texture_uv", 
                     text="Project in Object UV", 
                     icon='UV')
        col.operator("style_engine.project_texture_scene", 
                     text="Project in Scene", 
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
                          text="Texture", slider=True)
        
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
        
        # ═══════════════════════════════════════════════════
        # Position 3: RIGHT (EAST) - Reference Image
        # ═══════════════════════════════════════════════════
        box = pie.box()
        col = box.column(align=True)
        col.scale_y = 1.1
        
        # Header
        row = col.row()
        row.label(text="Reference Image", icon='IMAGE_REFERENCE')
        col.separator()
        
        # Enable/disable IPAdapter
        row = col.row()
        row.scale_y = 1.3
        row.prop(style_props, "use_ipadapter", 
                 text="Use Reference Image", 
                 toggle=True,
                 icon='CHECKMARK' if style_props.use_ipadapter else 'CHECKBOX_DEHLT')
        
        col.separator()
        
        # Only show settings if enabled
        if style_props.use_ipadapter:
            # File picker
            col.label(text="Image File")
            col.prop(style_props, "ipadapter_reference_image", text="")
            
            col.separator()
            
            # Type dropdown
            col.label(text="Mode")
            col.prop(style_props, "ipadapter_weight_type", text="")
            
            col.separator()
            
            # Strength slider
            col.label(text="Strength")
            col.prop(style_props, "ipadapter_strength", text="", slider=True)
        else:
            # Show message when disabled
            col.label(text="Enable to configure", icon='INFO')


# ----------------------------------------------------------------
# Registration
# ----------------------------------------------------------------

classes = (
    WM_OT_ProjectTextureUV,
    WM_OT_ProjectTextureScene,
    STYLEENGINE_MT_pie_main,
)

addon_keymaps = []


def register():
    """Register pie menu and Alt+Shift+E hotkey"""
    
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
        kmi = km.keymap_items.new('wm.call_menu_pie', 'E', 'PRESS', alt=True, shift=True)
        kmi.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km, kmi))
        
        # ALSO register for Mesh (Edit Mode) - conflict-free with Blender & HEAVYPOLY
        # Blender uses Shift+E (Extrude Menu), HEAVYPOLY uses E and Ctrl+Shift+E
        # Our Alt+Shift+E is completely free
        km_mesh = kc.keymaps.new(name='Mesh', space_type='VIEW_3D')
        kmi_mesh = km_mesh.keymap_items.new('wm.call_menu_pie', 'E', 'PRESS', alt=True, shift=True)
        kmi_mesh.properties.name = "STYLEENGINE_MT_pie_main"
        addon_keymaps.append((km_mesh, kmi_mesh))
        
        # Also register for other edit modes (Curve, Armature, etc.)
        for mode_name in ['Curve', 'Armature', 'Pose', 'Sculpt']:
            km_mode = kc.keymaps.new(name=mode_name, space_type='VIEW_3D')
            kmi_mode = km_mode.keymap_items.new('wm.call_menu_pie', 'E', 'PRESS', alt=True, shift=True)
            kmi_mode.properties.name = "STYLEENGINE_MT_pie_main"
            addon_keymaps.append((km_mode, kmi_mode))
        
        print("[Style Engine] ✅ Pie menu registered (Alt+Shift+E) for all modes - macOS/Windows/Linux compatible")


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

