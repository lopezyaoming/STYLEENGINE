# ================================================================
#    Style Engine Preferences
#    Manages addon preferences including API keys and settings
# ================================================================

import bpy
import os
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty


class StyleEnginePreferences(AddonPreferences):
    """Preferences panel for Style Engine addon."""
    bl_idname = "styleengine"

    # RunComfy API Settings
    runcomfy_api_token: StringProperty(
        name="RunComfy API Token",
        description="API token for RunComfy service. Can also be set via RUNCOMFY_API_TOKEN environment variable",
        default="",
        subtype='PASSWORD'
    )

    runcomfy_user_id: StringProperty(
        name="RunComfy User ID",
        description="User ID for RunComfy service. Can also be set via RUNCOMFY_USER_ID environment variable",
        default=""
    )

    # Toggle to show/hide API keys (for security)
    show_api_keys: BoolProperty(
        name="Show API Keys",
        description="Toggle visibility of API key fields",
        default=False
    )

    # Option to prefer environment variables
    use_env_vars: BoolProperty(
        name="Prefer Environment Variables",
        description="Use environment variables if available, otherwise use manually entered values",
        default=True
    )
    
    # ComfyUI Installation Path
    comfy_path: StringProperty(
        name="ComfyUI Path",
        description="Path to your ComfyUI installation folder (e.g., C:\\ComfyUI or C:\\ComfyUI_windows_portable\\ComfyUI)",
        default="",
        subtype='DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        
        # Main settings box
        box = layout.box()
        box.label(text="API Configuration", icon='KEYINGSET')
        
        # Environment variable preference
        box.prop(self, "use_env_vars")
        box.separator()
        
        # Check for environment variables
        env_token = os.environ.get('RUNCOMFY_API_TOKEN', '')
        env_user_id = os.environ.get('RUNCOMFY_USER_ID', '')
        
        # RunComfy Settings
        runcomfy_box = box.box()
        runcomfy_box.label(text="RunComfy API Settings", icon='NETWORK_DRIVE')
        
        # Show environment variable status
        if env_token:
            row = runcomfy_box.row()
            row.label(text="✓ RUNCOMFY_API_TOKEN found in environment", icon='CHECKMARK')
        else:
            row = runcomfy_box.row()
            row.label(text="⚠ RUNCOMFY_API_TOKEN not found in environment", icon='ERROR')
        
        if env_user_id:
            row = runcomfy_box.row()
            row.label(text="✓ RUNCOMFY_USER_ID found in environment", icon='CHECKMARK')
        else:
            row = runcomfy_box.row()
            row.label(text="⚠ RUNCOMFY_USER_ID not found in environment", icon='ERROR')
        
        runcomfy_box.separator()
        
        # Toggle to show/hide sensitive data
        runcomfy_box.prop(self, "show_api_keys", icon='HIDE_OFF' if self.show_api_keys else 'HIDE_ON')
        
        # API Token field
        col = runcomfy_box.column(align=True)
        if self.show_api_keys:
            col.prop(self, "runcomfy_api_token", text="API Token")
        else:
            # Show masked version
            row = col.row(align=True)
            row.label(text="API Token:")
            if self.runcomfy_api_token or env_token:
                row.label(text="••••••••••••••••")
            else:
                row.label(text="(not set)")
        
        # User ID field
        col.prop(self, "runcomfy_user_id", text="User ID")
        
        # Test connection button (placeholder for future implementation)
        runcomfy_box.separator()
        row = runcomfy_box.row()
        row.operator("style_engine.test_connection", icon='PLUGIN')
        
        # ComfyUI Path Settings
        layout.separator()
        comfy_box = layout.box()
        comfy_box.label(text="ComfyUI Installation", icon='FILE_FOLDER')
        
        # ComfyUI path field
        col = comfy_box.column(align=True)
        col.prop(self, "comfy_path", text="ComfyUI Path")
        
        # Show status
        if self.comfy_path:
            comfy_exists = os.path.exists(self.comfy_path)
            input_exists = os.path.exists(os.path.join(self.comfy_path, "input"))
            output_exists = os.path.exists(os.path.join(self.comfy_path, "output"))
            
            row = comfy_box.row()
            if comfy_exists:
                row.label(text="✓ ComfyUI folder found", icon='CHECKMARK')
            else:
                row.label(text="✗ ComfyUI folder not found", icon='ERROR')
            
            if input_exists:
                row = comfy_box.row()
                row.label(text="✓ Input folder found", icon='CHECKMARK')
            else:
                row = comfy_box.row()
                row.label(text="✗ Input folder not found", icon='ERROR')
                
            if output_exists:
                row = comfy_box.row()
                row.label(text="✓ Output folder found", icon='CHECKMARK')
            else:
                row = comfy_box.row()
                row.label(text="✗ Output folder not found", icon='ERROR')
        else:
            row = comfy_box.row()
            row.label(text="⚠ ComfyUI path not set", icon='ERROR')
        
        comfy_box.separator()
        col = comfy_box.column(align=True)
        col.label(text="Example paths:")
        col.label(text="  • C:\\ComfyUI")
        col.label(text="  • C:\\ComfyUI_windows_portable\\ComfyUI")
        col.label(text="  • D:\\AI\\ComfyUI")
        
        # Instructions
        layout.separator()
        info_box = layout.box()
        info_box.label(text="How to use:", icon='INFO')
        col = info_box.column(align=True)
        col.label(text="• Set environment variables in your system for automatic detection")
        col.label(text="• Or manually enter credentials above")
        col.label(text="• Environment variables take priority if 'Prefer Environment Variables' is enabled")
        col.label(text="• Point ComfyUI Path to your ComfyUI installation folder")


class WM_OT_TestConnection(bpy.types.Operator):
    """Test connection to RunComfy API."""
    bl_idname = "style_engine.test_connection"
    bl_label = "Test Connection"
    bl_description = "Test the connection to RunComfy API with current credentials"

    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        
        # Get the active API token (env var or manual)
        api_token = self.get_api_token(prefs)
        user_id = self.get_user_id(prefs)
        
        if not api_token:
            self.report({'ERROR'}, "RunComfy API Token is not set!")
            return {'CANCELLED'}
        
        if not user_id:
            self.report({'ERROR'}, "RunComfy User ID is not set!")
            return {'CANCELLED'}
        
        # TODO: Implement actual API connection test
        self.report({'INFO'}, f"Testing connection with User ID: {user_id[:8]}...")
        print(f"[Style Engine] Testing RunComfy connection...")
        print(f"  User ID: {user_id}")
        print(f"  API Token: {'*' * len(api_token)}")
        
        # Placeholder success message
        self.report({'INFO'}, "Connection test successful! (placeholder)")
        
        return {'FINISHED'}
    
    @staticmethod
    def get_api_token(prefs):
        """Get API token from environment or preferences."""
        if prefs.use_env_vars:
            env_token = os.environ.get('RUNCOMFY_API_TOKEN', '')
            if env_token:
                return env_token
        return prefs.runcomfy_api_token
    
    @staticmethod
    def get_user_id(prefs):
        """Get User ID from environment or preferences."""
        if prefs.use_env_vars:
            env_user_id = os.environ.get('RUNCOMFY_USER_ID', '')
            if env_user_id:
                return env_user_id
        return prefs.runcomfy_user_id


# ----------------------------------------------------------------
# REGISTRATION
# ----------------------------------------------------------------
classes = (
    StyleEnginePreferences,
    WM_OT_TestConnection,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

