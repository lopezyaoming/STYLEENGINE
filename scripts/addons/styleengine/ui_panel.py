# ================================================================
#    Style Engine UI Panel. Blender Python Script
# ================================================================

import bpy
from . import utils

# ----------------------------------------------------------------
# 1. PROPERTY GROUP
# ----------------------------------------------------------------
class StyleEngineProperties(bpy.types.PropertyGroup):
    """Stores all the properties for the Style Engine panel."""

    library_id: bpy.props.StringProperty(
        name="Library ID",
        description="The ID for the style library",
        default="0001"
    )

    scene_description: bpy.props.StringProperty(
        name="Scene Description",
        description="A high-level description for the scene",
        default="This is scene 1"
    )

    scene_keywords: bpy.props.StringProperty(
        name="Scene Keywords",
        description="General guidelines for the scene",
        default="Gotham, Hamster, Dark"
    )
    
    show_object_keywords: bpy.props.BoolProperty(
        name="Object Keywords",
        description="Expand or collapse the object keywords section",
        default=True
    )

    building_keywords: bpy.props.StringProperty(name="", default="Noir, Metal, Moody")
    tunnel_keywords: bpy.props.StringProperty(name="", default="Plastic, Hamster, Colorful")
    ground_keywords: bpy.props.StringProperty(name="", default="Pavement, puddles, damp")

    # NEW: Properties for the percentage sliders
    depth_influence: bpy.props.FloatProperty(
        name="Depth Influence",
        description="Controls the influence of depth",
        subtype='PERCENTAGE',
        default=50.0,
        min=0.0,
        max=100.0
    )

    silhouette: bpy.props.FloatProperty(
        name="Silhouette",
        description="Controls the strength of the silhouette",
        subtype='PERCENTAGE',
        default=75.0,
        min=0.0,
        max=100.0
    )


# ----------------------------------------------------------------
# 2. OPERATORS
# ----------------------------------------------------------------
class WM_OT_Visualize(bpy.types.Operator):
    """Activates automatic projection of image."""
    bl_idname = "style_engine.visualize"
    bl_label = "Visualize (30s)"

    def execute(self, context):
        # Validate API credentials
        is_valid, error_msg = utils.validate_runcomfy_credentials()
        if not is_valid:
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        props = context.scene.style_engine_props
        api_token = utils.get_runcomfy_api_token()
        user_id = utils.get_runcomfy_user_id()
        
        print(f"[Style Engine] Visualize Operation")
        print(f"  User ID: {user_id}")
        print(f"  API Token: {'*' * min(len(api_token), 20)}")
        print(f"  Depth: {props.depth_influence:.0f}%")
        print(f"  Silhouette: {props.silhouette:.0f}%")
        
        # TODO: Implement actual API call to RunComfy
        
        self.report({'INFO'}, "Visualize operation started!")
        return {'FINISHED'}

class WM_OT_Create3D(bpy.types.Operator):
    """Creates a specific asset."""
    bl_idname = "style_engine.create_3d"
    bl_label = "Create 3D"

    def execute(self, context):
        props = context.scene.style_engine_props
        print(f"Create 3D Clicked: Depth={props.depth_influence:.0f}%, Silhouette={props.silhouette:.0f}%")
        self.report({'INFO'}, "Create 3D Operator Executed!")
        return {'FINISHED'}

class WM_OT_Render(bpy.types.Operator):
    """Renders the image."""
    bl_idname = "style_engine.render"
    bl_label = "Render"

    def execute(self, context):
        props = context.scene.style_engine_props
        print(f"Render Clicked: Depth={props.depth_influence:.0f}%, Silhouette={props.silhouette:.0f}%")
        self.report({'INFO'}, "Render Operator Executed!")
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

        main_box = layout.box()

        row = main_box.row(align=True)
        row.label(text="LIBRARY ID")
        row.prop(style_props, "library_id", text="")
        
        main_box.separator()
        main_box.label(text="USER CAN TYPE HERE:")
        main_box.prop(style_props, "scene_description", text="")
        
        main_box.separator()
        col = main_box.column(align=True)
        col.label(text="SCENE KEYWORDS")
        col.prop(style_props, "scene_keywords", text="")
        
        main_box.separator()
        obj_box = main_box.box()
        row = obj_box.row(align=True)

        icon = 'TRIA_DOWN' if style_props.show_object_keywords else 'TRIA_RIGHT'
        row.prop(style_props, "show_object_keywords", text="OBJECT KEYWORDS", icon=icon, emboss=False)

        if style_props.show_object_keywords:
            header = obj_box.row()
            header.label(text="Group Name")
            header.label(text="Keyword")
            
            row1 = obj_box.row(align=True)
            row1.label(text="BUILDINGS")
            row1.prop(style_props, "building_keywords")

            row2 = obj_box.row(align=True)
            row2.label(text="TUNNELS")
            row2.prop(style_props, "tunnel_keywords")

            row3 = obj_box.row(align=True)
            row3.label(text="GROUND")
            row3.prop(style_props, "ground_keywords")
        
        # --- NEW: Sliders Section ---
        layout.separator()
        # Using a box to group the sliders visually
        slider_box = layout.box()
        slider_box.prop(style_props, "depth_influence")
        slider_box.prop(style_props, "silhouette")

        # --- Workspace Setup ---
        layout.separator()
        setup_box = layout.box()
        setup_box.label(text="AI Vision Setup", icon='WORKSPACE')
        setup_box.operator("style_engine.setup_workspace", icon='WINDOW')
        
        # Auto-refresh controls
        row = setup_box.row(align=True)
        row.operator("style_engine.start_auto_refresh", text="Start Refresh", icon='PLAY')
        row.operator("style_engine.stop_auto_refresh", text="Stop Refresh", icon='PAUSE')
        
        # --- Action Buttons ---
        layout.separator()
        button_row = layout.row(align=True)
        button_row.operator("style_engine.visualize")
        button_row.operator("style_engine.create_3d")
        button_row.operator("style_engine.render")


# ----------------------------------------------------------------
# 4. REGISTRATION
# ----------------------------------------------------------------
classes = (
    StyleEngineProperties,
    WM_OT_Visualize,
    WM_OT_Create3D,
    WM_OT_Render,
    VIEW3D_PT_StyleEngine,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.style_engine_props = bpy.props.PointerProperty(type=StyleEngineProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.style_engine_props

if __name__ == "__main__":
    register()