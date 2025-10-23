# ================================================================
#    Style Engine UI Panel. Blender Python Script
# ================================================================

import bpy
from . import utils
from . import workspace_setup

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
        description="Local directory to store renders and outputs",
        default="C:\\output",
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
        default="This is scene 1. Gotham, Hamster, Dark",
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
    
    # Workspace settings
    def update_refresh_viewport(self, context):
        """Start or stop the refresh and render timers based on checkbox state."""
        if self.refresh_viewport:
            # Start image refresh timer if not already running
            if not bpy.app.timers.is_registered(workspace_setup.refresh_ai_image):
                bpy.app.timers.register(workspace_setup.refresh_ai_image, first_interval=1.0, persistent=True)
                print("[Style Engine] Auto-refresh enabled")
            
            # Start auto-render timer if not already running
            if not bpy.app.timers.is_registered(workspace_setup.auto_render_passes):
                bpy.app.timers.register(workspace_setup.auto_render_passes, first_interval=workspace_setup.RENDER_INTERVAL, persistent=True)
                print(f"[Style Engine] Auto-render enabled (every {workspace_setup.RENDER_INTERVAL}s)")
        else:
            # Stop refresh timer if running
            if bpy.app.timers.is_registered(workspace_setup.refresh_ai_image):
                bpy.app.timers.unregister(workspace_setup.refresh_ai_image)
                print("[Style Engine] Auto-refresh disabled")
            
            # Stop render timer if running
            if bpy.app.timers.is_registered(workspace_setup.auto_render_passes):
                bpy.app.timers.unregister(workspace_setup.auto_render_passes)
                print("[Style Engine] Auto-render disabled")
    
    refresh_viewport: bpy.props.BoolProperty(
        name="Refresh Viewport",
        description="Automatically refresh AI image when it changes",
        default=True,
        update=update_refresh_viewport
    )
    
    auto_generate: bpy.props.BoolProperty(
        name="Auto-Generate AI",
        description="Automatically send workflow to ComfyUI when render passes update",
        default=False,
        update=update_session_json
    )
    
    ai_resolution: bpy.props.EnumProperty(
        name="AI Resolution",
        description="Resolution for AI generation",
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
        update=update_session_json
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
        print(f"  Depth Influence: {props.depth_influence:.2f}")
        print(f"  Silhouette Influence: {props.silhouette_influence:.2f}")
        
        # TODO: Implement actual API call to RunComfy
        
        self.report({'INFO'}, "Visualize operation started!")
        return {'FINISHED'}

class WM_OT_Create3D(bpy.types.Operator):
    """Creates a specific asset."""
    bl_idname = "style_engine.create_3d"
    bl_label = "Create 3D"

    def execute(self, context):
        props = context.scene.style_engine_props
        print(f"Create 3D Clicked: Depth={props.depth_influence:.2f}, Silhouette={props.silhouette_influence:.2f}")
        self.report({'INFO'}, "Create 3D Operator Executed!")
        return {'FINISHED'}

class WM_OT_Render(bpy.types.Operator):
    """Renders the image."""
    bl_idname = "style_engine.render"
    bl_label = "Render"

    def execute(self, context):
        props = context.scene.style_engine_props
        print(f"Render Clicked: Depth={props.depth_influence:.2f}, Silhouette={props.silhouette_influence:.2f}")
        self.report({'INFO'}, "Render Operator Executed!")
        return {'FINISHED'}


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

        # --- Workspace Setup (TOP) - COLLAPSIBLE ---
        setup_box = layout.box()
        row = setup_box.row(align=True)
        icon = 'TRIA_DOWN' if style_props.show_workspace_setup else 'TRIA_RIGHT'
        row.prop(style_props, "show_workspace_setup", text="Workspace Setup", icon=icon, emboss=False)
        
        if style_props.show_workspace_setup:
            # Session ID
            row = setup_box.row(align=True)
            row.label(text="Session ID:")
            row.prop(style_props, "library_id", text="")
            
            setup_box.separator()
            setup_box.operator("style_engine.setup_workspace", icon='WINDOW')
            
            # Auto-refresh checkbox
            setup_box.prop(style_props, "refresh_viewport", icon='FILE_REFRESH')
            
            # Auto-generate AI checkbox
            setup_box.prop(style_props, "auto_generate", icon='PLAY')
            
            # Resolution dropdown
            setup_box.separator()
            setup_box.label(text="Set Resolution:")
            setup_box.prop(style_props, "ai_resolution", text="")
            
            # Output path
            setup_box.separator()
            setup_box.label(text="Output Path:")
            setup_box.prop(style_props, "output_path", text="")
        
        # --- Image Generation - COLLAPSIBLE ---
        layout.separator()
        gen_box = layout.box()
        row = gen_box.row(align=True)
        icon = 'TRIA_DOWN' if style_props.show_image_generation else 'TRIA_RIGHT'
        row.prop(style_props, "show_image_generation", text="Image Generation", icon=icon, emboss=False)
        
        if style_props.show_image_generation:
            # Lookup
            gen_box.separator()
            col = gen_box.column(align=True)
            col.label(text="Lookup:")
            col.prop(style_props, "lookup", text="")
            
            # Global Prompt
            gen_box.separator()
            col = gen_box.column(align=True)
            col.label(text="Global Prompt:")
            col.prop(style_props, "global_prompt", text="")
            
            # Influence section
            gen_box.separator()
            influence_box = gen_box.box()
            influence_box.label(text="Influence", icon='SHADERFX')
            influence_box.prop(style_props, "depth_influence", slider=True)
            influence_box.prop(style_props, "silhouette_influence", slider=True)
            
            # Groups section
            gen_box.separator()
            groups_box = gen_box.box()
            row = groups_box.row(align=True)

            icon = 'TRIA_DOWN' if style_props.show_groups else 'TRIA_RIGHT'
            row.prop(style_props, "show_groups", text="Groups", icon=icon, emboss=False)

            if style_props.show_groups:
                # Group controls
                control_row = groups_box.row(align=True)
                control_row.operator("style_engine.add_group", icon='ADD', text="Add")
                control_row.operator("style_engine.assign_group", icon='LINK_BLEND', text="Assign")
                control_row.operator("style_engine.rename_group", icon='GREASEPENCIL', text="Rename")
                control_row.operator("style_engine.delete_group", icon='TRASH', text="Delete")
                
                groups_box.separator()
                
                # Show message if no groups
                if len(style_props.object_groups) == 0:
                    groups_box.label(text="No groups. Click 'Add' to create one.", icon='INFO')
                else:
                    # Dynamic groups display
                    header = groups_box.row()
                    header.label(text="")  # Selection column
                    header.label(text="Group Name")
                    header.label(text="Keywords")
                    
                    # Display all groups dynamically
                    for idx, group in enumerate(style_props.object_groups):
                        row = groups_box.row(align=True)
                        
                        # Selection radio button
                        selected = style_props.active_group_index == idx
                        row.operator("style_engine.select_group", text="", icon='RADIOBUT_ON' if selected else 'RADIOBUT_OFF', emboss=False).group_index = idx
                        
                        # Group name
                        row.label(text=group.name.upper())
                        
                        # Keywords input
                        row.prop(group, "keywords", text="")
        
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
    ObjectGroup,
    StyleEngineProperties,
    WM_OT_Visualize,
    WM_OT_Create3D,
    WM_OT_Render,
    WM_OT_AddGroup,
    WM_OT_AssignGroup,
    WM_OT_RenameGroup,
    WM_OT_SelectGroup,
    WM_OT_DeleteGroup,
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