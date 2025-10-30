# ================================================================
#    Style Engine Preferences
#    Manages addon preferences including API keys and settings
# ================================================================

import bpy
import os
from bpy.types import AddonPreferences
from bpy.props import StringProperty, BoolProperty, EnumProperty, IntProperty


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
    
    # ----------------------------------------------------------------
    # WORKFLOW CONFIGURATION
    # ----------------------------------------------------------------
    
    # Workflow IDs (user will provide these)
    runcomfy_workflow_id_sdxl: StringProperty(
        name="SDXL Workflow ID",
        description="RunComfy workflow ID for SDXL generation (provided by developer)",
        default=""  # USER WILL SET THIS WHEN WORKFLOWS ARE READY
    )
    
    runcomfy_workflow_id_ipadapter: StringProperty(
        name="IPAdapter Workflow ID",
        description="RunComfy workflow ID for IPAdapter generation (provided by developer)",
        default=""  # USER WILL SET THIS WHEN WORKFLOWS ARE READY
    )
    
    # Deployment IDs (optional - auto-created if not set)
    runcomfy_deployment_id_sdxl: StringProperty(
        name="SDXL Deployment ID",
        description="Deployment ID for SDXL workflow (auto-created if empty)",
        default="1c6fa9a6-f60a-4e89-863d-40b03ad2564e"
    )
    
    runcomfy_deployment_id_ipadapter: StringProperty(
        name="IPAdapter Deployment ID",
        description="Deployment ID for IPAdapter workflow (auto-created if empty)",
        default="1c6fa9a6-f60a-4e89-863d-40b03ad2564e"
    )
    
    # ----------------------------------------------------------------
    # HARDWARE SETTINGS
    # ----------------------------------------------------------------
    
    runcomfy_hardware_tier: EnumProperty(
        name="Hardware Tier",
        description="GPU hardware tier for cloud generation",
        items=[
            ('AMPERE_16', 'A4000 16GB - $1.00/hr', 'NVIDIA A4000 16GB VRAM'),
            ('AMPERE_24', 'A5000 24GB - $1.50/hr', 'NVIDIA A5000 24GB VRAM'),
            ('AMPERE_48', 'A6000 48GB - $2.50/hr', 'NVIDIA A6000 48GB VRAM (Recommended)'),
            ('ADA_24', 'RTX 4090 24GB - $2.00/hr', 'NVIDIA RTX 4090 24GB VRAM'),
        ],
        default='AMPERE_48'
    )
    
    # ----------------------------------------------------------------
    # SCALING SETTINGS
    # ----------------------------------------------------------------
    
    runcomfy_min_instances: IntProperty(
        name="Min Instances",
        description="Minimum running instances (0 = scale to zero when idle)",
        default=0,
        min=0,
        max=5
    )
    
    runcomfy_max_instances: IntProperty(
        name="Max Instances",
        description="Maximum running instances",
        default=1,
        min=1,
        max=10
    )
    
    runcomfy_queue_size: IntProperty(
        name="Queue Size",
        description="Maximum queued requests per instance",
        default=1,
        min=1,
        max=10
    )
    
    runcomfy_keep_warm_seconds: IntProperty(
        name="Keep Warm (seconds)",
        description="Keep instance alive after last request",
        default=60,
        min=0,
        max=600
    )
    
    # ----------------------------------------------------------------
    # TIMEOUT SETTINGS
    # ----------------------------------------------------------------
    
    runcomfy_request_timeout: IntProperty(
        name="Request Timeout (seconds)",
        description="Max time to wait for generation",
        default=600,
        min=60,
        max=1800
    )
    
    runcomfy_poll_interval: IntProperty(
        name="Poll Interval (seconds)",
        description="How often to check status",
        default=5,
        min=2,
        max=30
    )
    
    # ----------------------------------------------------------------
    # UI STATE
    # ----------------------------------------------------------------
    
    show_workflow_config: BoolProperty(
        name="Show Workflow Configuration",
        description="Expand or collapse workflow configuration section",
        default=False
    )
    
    show_hardware_settings: BoolProperty(
        name="Show Hardware Settings",
        description="Expand or collapse hardware settings section",
        default=False
    )
    
    show_advanced_settings: BoolProperty(
        name="Show Advanced Settings",
        description="Expand or collapse advanced settings section",
        default=False
    )
    
    # ComfyUI Installation Path (for local version reference)
    comfy_path: StringProperty(
        name="ComfyUI Path",
        description="Path to your ComfyUI installation folder (e.g., C:\\ComfyUI or C:\\ComfyUI_windows_portable\\ComfyUI)",
        default="",
        subtype='DIR_PATH'
    )

    def draw(self, context):
        layout = self.layout
        
        # ----------------------------------------------------------------
        # API CREDENTIALS
        # ----------------------------------------------------------------
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
        
        # Test connection button
        runcomfy_box.separator()
        row = runcomfy_box.row()
        row.operator("style_engine.test_connection", icon='PLUGIN')
        
        # ----------------------------------------------------------------
        # WORKFLOW CONFIGURATION
        # ----------------------------------------------------------------
        layout.separator()
        workflow_box = layout.box()
        header_row = workflow_box.row(align=True)
        icon = 'TRIA_DOWN' if self.show_workflow_config else 'TRIA_RIGHT'
        header_row.prop(self, "show_workflow_config", text="Workflow Configuration", 
                       icon=icon, emboss=False, toggle=True)
        
        if self.show_workflow_config:
            # Workflow IDs
            col = workflow_box.column(align=True)
            col.label(text="Workflow IDs (provided by developer):", icon='FILE_SCRIPT')
            col.prop(self, "runcomfy_workflow_id_sdxl", text="SDXL")
            col.prop(self, "runcomfy_workflow_id_ipadapter", text="IPAdapter")
            
            workflow_box.separator()
            
            # Deployment IDs
            col = workflow_box.column(align=True)
            col.label(text="Deployment IDs (optional - auto-created if empty):", icon='NETWORK_DRIVE')
            col.prop(self, "runcomfy_deployment_id_sdxl", text="SDXL")
            col.prop(self, "runcomfy_deployment_id_ipadapter", text="IPAdapter")
            
            workflow_box.separator()
            col = workflow_box.column(align=True)
            col.label(text="Note: Deployments are automatically created if IDs are not set.", icon='INFO')
        
        # ----------------------------------------------------------------
        # HARDWARE SETTINGS
        # ----------------------------------------------------------------
        layout.separator()
        hardware_box = layout.box()
        header_row = hardware_box.row(align=True)
        icon = 'TRIA_DOWN' if self.show_hardware_settings else 'TRIA_RIGHT'
        header_row.prop(self, "show_hardware_settings", text="Hardware Settings", 
                       icon=icon, emboss=False, toggle=True)
        
        if self.show_hardware_settings:
            # Hardware tier
            hardware_box.label(text="GPU Tier:", icon='GPU')
            hardware_box.prop(self, "runcomfy_hardware_tier", text="")
            
            hardware_box.separator()
            
            # Scaling settings
            hardware_box.label(text="Scaling Configuration:", icon='MOD_ARRAY')
            col = hardware_box.column(align=True)
            col.prop(self, "runcomfy_min_instances")
            col.prop(self, "runcomfy_max_instances")
            col.prop(self, "runcomfy_queue_size")
            
            hardware_box.separator()
            
            # Keep warm
            hardware_box.label(text="Instance Management:", icon='TIME')
            hardware_box.prop(self, "runcomfy_keep_warm_seconds")
            
            hardware_box.separator()
            col = hardware_box.column(align=True)
            col.label(text="Note: Min instances = 0 means scale to zero when idle.", icon='INFO')
            col.label(text="Higher queue size allows more parallel requests.")
        
        # ----------------------------------------------------------------
        # ADVANCED SETTINGS
        # ----------------------------------------------------------------
        layout.separator()
        advanced_box = layout.box()
        header_row = advanced_box.row(align=True)
        icon = 'TRIA_DOWN' if self.show_advanced_settings else 'TRIA_RIGHT'
        header_row.prop(self, "show_advanced_settings", text="Advanced Settings", 
                       icon=icon, emboss=False, toggle=True)
        
        if self.show_advanced_settings:
            # Timeout settings
            advanced_box.label(text="Timeout Configuration:", icon='SORTTIME')
            col = advanced_box.column(align=True)
            col.prop(self, "runcomfy_request_timeout")
            col.prop(self, "runcomfy_poll_interval")
            
            advanced_box.separator()
            col = advanced_box.column(align=True)
            col.label(text="Note: Higher timeout allows longer generations.", icon='INFO')
            col.label(text="Lower poll interval provides faster status updates.")
        
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

