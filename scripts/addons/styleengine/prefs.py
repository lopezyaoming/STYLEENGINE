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
    
    # Unified Workflow ID (same for both SDXL and IPAdapter)
    runcomfy_workflow_id: StringProperty(
        name="Workflow ID",
        description="RunComfy workflow ID (provided by developer, used for both SDXL and IPAdapter)",
        default="f7ade856-0739-4fc8-8fa3-3b3857e2ebcb"
    )
    
    # Unified Deployment ID (same for both SDXL and IPAdapter)
    runcomfy_deployment_id: StringProperty(
        name="Deployment ID",
        description="Deployment ID (optional - auto-created if empty, used for both SDXL and IPAdapter)",
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
        description="How often to check status (generation takes ~26s, so 10s = 2-3 checks per gen)",
        default=10,
        min=5,
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
    
    # ----------------------------------------------------------------
    # ROBUSTNESS SETTINGS - Conflict Resolution
    # ----------------------------------------------------------------
    
    # Resource naming overrides
    camera_name_override: StringProperty(
        name="Camera Name",
        description="Custom camera name (change if conflicts with other addons like HEAVYPOLY)",
        default="ai_camera"
    )
    
    workspace_name_override: StringProperty(
        name="Workspace Name",
        description="Custom workspace name",
        default="StyleEngine_AI"
    )
    
    image_name_override: StringProperty(
        name="Image Name",
        description="Custom image name for AI output",
        default="STYLEENGINE_current_ai.png"
    )
    
    # Feature toggles for compatibility
    enable_heavypoly_compatibility: BoolProperty(
        name="Enable HEAVYPOLY Compatibility",
        description="Integrate with HEAVYPOLY workflow and hotkeys. Enhances Style Engine to work seamlessly with HEAVYPOLY's pie menus and shortcuts",
        default=False
    )
    
    enable_camera_switching: BoolProperty(
        name="Allow Camera Switching",
        description="Allow addon to temporarily change active camera during rendering (safe - restores immediately). Disable if using HEAVYPOLY or custom camera systems and experiencing issues",
        default=True
    )
    
    enable_workspace_creation: BoolProperty(
        name="Enable Workspace Creation",
        description="Create custom StyleEngine workspace. Disable if conflicts with UI addons like HEAVYPOLY",
        default=True
    )
    
    enable_viewport_split: BoolProperty(
        name="Enable Viewport Splitting",
        description="Automatically split viewport into dual view. Disable if conflicts with UI addons",
        default=True
    )
    
    enable_auto_render: BoolProperty(
        name="Enable Auto-Render Timer",
        description="DEPRECATED: Wasteful! Renders happen cyclically with generation instead. Keep this OFF.",
        default=False
    )
    
    # Debug settings
    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Enable verbose console logging for troubleshooting conflicts and issues",
        default=False
    )
    
    # ComfyUI Installation Path (for local version reference)
    comfy_path: StringProperty(
        name="ComfyUI Path",
        description="Path to your ComfyUI installation folder (cross-platform support)",
        default="",
        subtype='DIR_PATH'
    )

    # ----------------------------------------------------------------
    # SERVER API MODE SETTINGS (DISABLED/LATENT)
    # ----------------------------------------------------------------
    # NOTE: Server API mode is currently disabled/latent
    # The Machines API requires special access that may not be available to all accounts.
    # Serverless mode with min_instances=1 provides equivalent performance without maintenance.
    # Code kept for future use if API access becomes available.
    
    # use_server_api: BoolProperty(
    #     name="Use Server API",
    #     description="Use a dedicated ComfyUI server instead of serverless deployment. Provides faster generation but requires maintaining a running server instance",
    #     default=False
    # )
    
    # comfyui_server_url: StringProperty(
    #     name="ComfyUI Server URL",
    #     description="URL of your ComfyUI backend server (e.g., https://06ac297b-eab1-4e72-a327-db7dc5197cee-comfyui.runcomfy.com)",
    #     default=""
    # )
    
    # runcomfy_server_id: StringProperty(
    #     name="Server ID",
    #     description="RunComfy server ID (auto-populated when server is launched)",
    #     default=""
    # )
    
    # runcomfy_server_status: StringProperty(
    #     name="Server Status",
    #     description="Current status of the running server",
    #     default="Not Running"
    # )

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
        if self.show_api_keys:
            col.prop(self, "runcomfy_user_id", text="User ID")
        else:
            # Show masked version
            row = col.row(align=True)
            row.label(text="User ID:")
            if self.runcomfy_user_id or env_user_id:
                row.label(text="••••••••••••••••")
            else:
                row.label(text="(not set)")
        
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
            # Unified Workflow ID
            col = workflow_box.column(align=True)
            col.label(text="Workflow IDs (provided by developer):", icon='FILE_SCRIPT')
            col.prop(self, "runcomfy_workflow_id", text="Workflow ID")
            
            workflow_box.separator()
            
            # Unified Deployment ID
            col = workflow_box.column(align=True)
            col.label(text="Deployment IDs (optional - auto-created if empty):", icon='NETWORK_DRIVE')
            col.prop(self, "runcomfy_deployment_id", text="Deployment ID")
            
            workflow_box.separator()
            col = workflow_box.column(align=True)
            col.label(text="Note: Both SDXL and IPAdapter workflows use the same deployment.", icon='INFO')
        
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
            hardware_box.label(text="GPU Tier:", icon='SHADING_RENDERED')
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
            
            # ----------------------------------------------------------------
            # ROBUSTNESS SETTINGS - Conflict Resolution
            # ----------------------------------------------------------------
            advanced_box.separator()
            advanced_box.separator()
            advanced_box.label(text="Conflict Resolution (for HEAVYPOLY, etc.):", icon='ERROR')
            
            # Debug mode (prominent)
            col = advanced_box.column(align=True)
            col.prop(self, "debug_mode", text="🐛 Debug Mode (Verbose Logging)")
            
            advanced_box.separator()
            
            # Resource naming
            col = advanced_box.column(align=True)
            col.label(text="Resource Naming:", icon='FILE_TEXT')
            col.prop(self, "camera_name_override", text="Camera Name")
            col.prop(self, "workspace_name_override", text="Workspace Name")
            col.prop(self, "image_name_override", text="Image Name")
            
            advanced_box.separator()
            
            # Feature toggles
            col = advanced_box.column(align=True)
            col.label(text="Feature Toggles:", icon='PREFERENCES')
            
            # HEAVYPOLY Integration
            row = col.row(align=True)
            row.prop(self, "enable_heavypoly_compatibility")
            if self.enable_heavypoly_compatibility:
                row.label(text="", icon='CHECKMARK')
            
            col.separator()
            
            col.prop(self, "enable_camera_switching")
            col.prop(self, "enable_workspace_creation")
            col.prop(self, "enable_viewport_split")
            col.prop(self, "enable_auto_render")
            
            advanced_box.separator()
            col = advanced_box.column(align=True)
            col.label(text="Note: Disable features if conflicts occur with other addons.", icon='INFO')
            col.label(text="Camera switching is SURGICAL (temporary, instant restore).")
        
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
        col.label(text="  • Windows: C:\\ComfyUI or D:\\AI\\ComfyUI")
        col.label(text="  • macOS: /Applications/ComfyUI")
        col.label(text="  • Linux: /home/user/ComfyUI or ~/ComfyUI")
        
        # ----------------------------------------------------------------
        # SERVER API MODE (DISABLED/LATENT)
        # ----------------------------------------------------------------
        # NOTE: Server API mode commented out - Machines API requires special access.
        # Serverless mode with min_instances=1 provides equivalent performance.
        # Uncomment below if API access becomes available.
        
        # layout.separator()
        # server_box = layout.box()
        # server_box.label(text="Server API Mode", icon='NETWORK_DRIVE')
        # 
        # # Use Server API toggle
        # row = server_box.row()
        # row.prop(self, "use_server_api", text="Use Server API (instead of Serverless)")
        # 
        # if self.use_server_api:
        #     # Show warning about server maintenance
        #     server_box.separator()
        #     warning_col = server_box.column(align=True)
        #     warning_col.label(text="⚠ Server API Mode Active", icon='ERROR')
        #     warning_col.label(text="You are responsible for maintaining the server instance.")
        #     warning_col.label(text="Provides faster generation but requires a running ComfyUI backend.")
        #     
        #     server_box.separator()
        #     
        #     # Server URL field
        #     col = server_box.column(align=True)
        #     col.label(text="ComfyUI Backend Server URL:", icon='URL')
        #     col.prop(self, "comfyui_server_url", text="")
        #     
        #     # Show URL validation
        #     if self.comfyui_server_url:
        #         if "comfyui.runcomfy.com" in self.comfyui_server_url.lower() or "http" in self.comfyui_server_url.lower():
        #             row = server_box.row()
        #             row.label(text="✓ URL format looks valid", icon='CHECKMARK')
        #         else:
        #             row = server_box.row()
        #             row.label(text="⚠ Check URL format", icon='ERROR')
        #     else:
        #         row = server_box.row()
        #         row.label(text="⚠ Server URL not set", icon='ERROR')
        #     
        #     server_box.separator()
        #     col = server_box.column(align=True)
        #     col.label(text="Example URL:")
        #     col.label(text="  https://06ac297b-eab1-4e72-a327-db7dc5197cee-comfyui.runcomfy.com")
        #     
        #     # Server management buttons
        #     server_box.separator()
        #     
        #     # Show server status if we have a server_id
        #     if self.runcomfy_server_id:
        #         status_col = server_box.column(align=True)
        #         status_col.label(text=f"Server Status: {self.runcomfy_server_status.title()}", icon='INFO')
        #         status_col.label(text=f"Server ID: {self.runcomfy_server_id[:20]}...")
        #         server_box.separator()
        #     
        #     # Action buttons in a row
        #     btn_row = server_box.row(align=True)
        #     
        #     # Start Server button (if no server or server stopped)
        #     if not self.runcomfy_server_id or self.runcomfy_server_status in ('unknown', 'stopped', 'failed'):
        #         btn_row.operator("style_engine.start_server", icon='PLAY', text="Start New Server")
        #     
        #     # Test Connection button
        #     btn_row.operator("style_engine.test_server_connection", icon='PLUGIN', text="Test Connection")
        #     
        #     # Stop Server button (if we have an active server)
        #     if self.runcomfy_server_id and self.runcomfy_server_status not in ('unknown', 'stopped', 'failed'):
        #         btn_row.operator("style_engine.stop_server", icon='CANCEL', text="Stop Server")
        # else:
        #     # Show info about serverless mode
        #     server_box.separator()
        #     info_col = server_box.column(align=True)
        #     info_col.label(text="ℹ Serverless Mode Active (default)", icon='INFO')
        #     info_col.label(text="Uses RunComfy's managed serverless deployment.")
        #     info_col.label(text="No server maintenance required, automatic scaling.")
        
        # Instructions
        layout.separator()
        info_box = layout.box()
        info_box.label(text="How to use:", icon='INFO')
        col = info_box.column(align=True)
        col.label(text="• Set environment variables in your system for automatic detection")
        col.label(text="• Or manually enter credentials above")
        col.label(text="• Environment variables take priority if 'Prefer Environment Variables' is enabled")
        col.label(text="• Point ComfyUI Path to your ComfyUI installation folder")
        # col.label(text="• Enable 'Use Server API' if you have a dedicated ComfyUI backend server")  # Disabled - Server API latent


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
        
        # REAL API CONNECTION TEST
        try:
            from . import runcomfy_client
            
            self.report({'INFO'}, f"Testing connection with User ID: {user_id[:8]}...")
            print(f"[Style Engine] Testing RunComfy connection...")
            
            # Create client
            client = runcomfy_client.RunComfyClient(
                api_token=api_token,
                user_id=user_id,
                timeout=10  # Short timeout for test
            )
            
            # Test 1: List deployments (lightweight API call)
            print("[Style Engine] Fetching deployments...")
            deployments = client.list_deployments()
            
            # Success!
            deployment_count = len(deployments)
            self.report({'INFO'}, f"✅ Connection successful! Found {deployment_count} deployment(s)")
            print(f"[Style Engine] ✅ API connection verified!")
            print(f"  Active deployments: {deployment_count}")
            
            # Show deployment IDs if any
            if deployments:
                print("  Your deployments:")
                for dep in deployments[:3]:  # Show first 3
                    dep_id = dep.get('id', 'unknown')
                    dep_name = dep.get('name', 'unnamed')
                    print(f"    - {dep_name} ({dep_id[:8]}...)")
            
            return {'FINISHED'}
            
        except runcomfy_client.RunComfyError as e:
            # API error - credentials likely invalid
            error_msg = str(e)
            self.report({'ERROR'}, f"❌ Connection failed: {error_msg}")
            print(f"[Style Engine] ❌ Connection test failed: {error_msg}")
            return {'CANCELLED'}
            
        except Exception as e:
            # Unexpected error
            self.report({'ERROR'}, f"❌ Unexpected error: {e}")
            print(f"[Style Engine] ❌ Unexpected error during connection test: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
    
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


# NOTE: Server API operators commented out - Server API mode is latent
# Uncomment if Server API access becomes available
# 
# class WM_OT_StartServer(bpy.types.Operator):
#     """Start a new RunComfy server instance."""
#     bl_idname = "style_engine.start_server"
#     bl_label = "Start Server"
#     bl_description = "Launch a new ComfyUI server instance on RunComfy"
# 
#     def execute(self, context):
#         prefs = context.preferences.addons['styleengine'].preferences
#         
#         # Get API credentials
#         if prefs.use_env_vars:
#             import os
#             api_token = os.environ.get('RUNCOMFY_API_TOKEN', prefs.runcomfy_api_token)
#             user_id = os.environ.get('RUNCOMFY_USER_ID', prefs.runcomfy_user_id)
#         else:
#             api_token = prefs.runcomfy_api_token
#             user_id = prefs.runcomfy_user_id
#         
#         if not api_token or not user_id:
#             self.report({'ERROR'}, "RunComfy credentials not configured!")
#             return {'CANCELLED'}
#         
#         # Start server
#         try:
#             from . import runcomfy_server_manager
#             
#             self.report({'INFO'}, "Starting new ComfyUI server...")
#             print(f"[Server Manager] =========================================")
#             print(f"[Server Manager] LAUNCHING NEW COMFYUI SERVER")
#             print(f"[Server Manager] =========================================")
#             
#             # Create server manager
#             manager = runcomfy_server_manager.RunComfyServerManager(
#                 api_token=api_token,
#                 user_id=user_id
#             )
#             
#             # Create server
#             hardware = prefs.runcomfy_hardware_tier
#             workflow_id = prefs.runcomfy_workflow_id if prefs.runcomfy_workflow_id else None
#             
#             server_info = manager.create_server(
#                 workflow_id=workflow_id,
#                 hardware_tier=hardware,
#                 name='Style Engine ComfyUI Server'
#             )
#             
#             # Save server info to preferences
#             prefs.runcomfy_server_id = server_info['server_id']
#             prefs.comfyui_server_url = server_info['server_url']
#             prefs.runcomfy_server_status = server_info['status']
#             
#             self.report({'INFO'}, f"✅ Server created! Waiting for it to be ready...")
#             
#             # Wait for server to be ready
#             try:
#                 manager.wait_for_server_ready(server_info['server_id'], timeout=300)
#                 prefs.runcomfy_server_status = 'running'
#                 self.report({'INFO'}, f"✅ Server is ready! URL: {server_info['server_url']}")
#             except runcomfy_server_manager.ServerNotReadyError as e:
#                 prefs.runcomfy_server_status = 'starting'
#                 self.report({'WARNING'}, f"⚠ Server created but not yet ready: {e}")
#             
#             return {'FINISHED'}
#             
#         except runcomfy_server_manager.ServerLaunchError as e:
#             error_msg = str(e)
#             self.report({'ERROR'}, f"❌ Failed to start server: {error_msg}")
#             print(f"[Server Manager] ❌ Launch failed: {error_msg}")
#             return {'CANCELLED'}
#             
#         except Exception as e:
#             self.report({'ERROR'}, f"❌ Unexpected error: {e}")
#             print(f"[Server Manager] ❌ Unexpected error: {e}")
#             import traceback
#             traceback.print_exc()
#             return {'CANCELLED'}
# 
# 
# # class WM_OT_StopServer(bpy.types.Operator):
# #     """Stop the RunComfy server instance."""
# #     bl_idname = "style_engine.stop_server"
# #     bl_label = "Stop Server"
# #     bl_description = "Stop the running ComfyUI server instance"
# #
# #     def execute(self, context):
# #         prefs = context.preferences.addons['styleengine'].preferences
# #         
# #         if not prefs.runcomfy_server_id:
# #             self.report({'ERROR'}, "No active server to stop!")
# #             return {'CANCELLED'}
# #         
# #         # Get API credentials
# #         if prefs.use_env_vars:
# #             import os
# #             api_token = os.environ.get('RUNCOMFY_API_TOKEN', prefs.runcomfy_api_token)
# #             user_id = os.environ.get('RUNCOMFY_USER_ID', prefs.runcomfy_user_id)
# #         else:
# #             api_token = prefs.runcomfy_api_token
# #             user_id = prefs.runcomfy_user_id
# #         
# #         try:
# #             from . import runcomfy_server_manager
# #             
# #             manager = runcomfy_server_manager.RunComfyServerManager(
# #                 api_token=api_token,
# #                 user_id=user_id
# #             )
# #             
# #             manager.stop_server(prefs.runcomfy_server_id)
# #             
# #             prefs.runcomfy_server_status = 'stopped'
# #             self.report({'INFO'}, "✅ Server stopped")
# #             
# #             return {'FINISHED'}
# #             
# #         except Exception as e:
# #             self.report({'ERROR'}, f"❌ Failed to stop server: {e}")
# #             return {'CANCELLED'}
# 
# 
# # class WM_OT_TestServerConnection(bpy.types.Operator):
# #     """Test connection to ComfyUI Server API."""
# #     bl_idname = "style_engine.test_server_connection"
# #     bl_label = "Test Server Connection"
# #     bl_description = "Test connection to ComfyUI backend server with detailed diagnostics"
# #
# #     def execute(self, context):
# #         prefs = context.preferences.addons['styleengine'].preferences
# #         
# #         # Check if server URL is set
# #         server_url = prefs.comfyui_server_url
# #         
# #         if not server_url:
# #             self.report({'ERROR'}, "Server URL is not set!")
# #             print("[Server API] ❌ Test failed: Server URL not configured")
# #             return {'CANCELLED'}
# #         
# #         # Test connection
# #         try:
# #             from . import runcomfy_deployment
# #             from . import runcomfy_server_client
# #             
# #             self.report({'INFO'}, f"Testing connection to: {server_url[:50]}...")
# #             print(f"[Server API] =========================================")
# #             print(f"[Server API] MANUAL SERVER CONNECTION TEST")
# #             print(f"[Server API] =========================================")
# #             
# #             # Get server client
# #             server_client = runcomfy_deployment.get_server_client()
# #             
# #             # Perform comprehensive health check
# #             health = server_client.check_server_health()
# #             
# #             # Report results
# #             if health['healthy']:
# #                 # Update status
# #                 prefs.runcomfy_server_status = 'running'
# #                 self.report({'INFO'}, f"✅ Server is healthy and ready!")
# #                 print(f"[Server API]")
# #                 print(f"[Server API] ✅ TEST RESULT: SERVER IS HEALTHY")
# #                 print(f"[Server API] {health['details']}")
# #             elif health['connection']['reachable']:
# #                 prefs.runcomfy_server_status = 'starting'
# #                 self.report({'WARNING'}, f"⚠ Server is reachable but may not be fully ready")
# #                 print(f"[Server API]")
# #                 print(f"[Server API] ⚠ TEST RESULT: SERVER REACHABLE BUT WARNING")
# #                 print(f"[Server API] {health['details']}")
# #             else:
# #                 prefs.runcomfy_server_status = 'stopped'
# #                 error = health['connection'].get('error', 'Unknown error')
# #                 self.report({'ERROR'}, f"❌ Connection failed: {error}")
# #                 print(f"[Server API]")
# #                 print(f"[Server API] ❌ TEST RESULT: CONNECTION FAILED")
# #                 print(f"[Server API] Error: {error}")
# #             
# #             print(f"[Server API] =========================================")
# #             
# #             return {'FINISHED'}
# #             
# #         except runcomfy_server_client.ServerAPIError as e:
# #             error_msg = str(e)
# #             prefs.runcomfy_server_status = 'failed'
# #             self.report({'ERROR'}, f"❌ Server API error: {error_msg}")
# #             print(f"[Server API] ❌ Test failed: {error_msg}")
# #             return {'CANCELLED'}
# #             
# #         except Exception as e:
# #             prefs.runcomfy_server_status = 'failed'
# #             self.report({'ERROR'}, f"❌ Unexpected error: {e}")
# #             print(f"[Server API] ❌ Unexpected error during test: {e}")
# #             import traceback
# #             traceback.print_exc()
# #             return {'CANCELLED'}


# ----------------------------------------------------------------
# REGISTRATION
# ----------------------------------------------------------------
classes = (
    StyleEnginePreferences,
    WM_OT_TestConnection,
    # WM_OT_StartServer,  # Disabled - Server API latent
    # WM_OT_StopServer,  # Disabled - Server API latent
    # WM_OT_TestServerConnection,  # Disabled - Server API latent
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

