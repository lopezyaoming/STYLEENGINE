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
    
    # Credentials file path
    credentials_file_path: StringProperty(
        name="Credentials File",
        description="Path to credentials.txt file",
        default="",
        subtype='FILE_PATH'
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
    # API MODE CONFIGURATION
    # ----------------------------------------------------------------
    
    api_backend: EnumProperty(
        name="Backend",
        description="Choose which backend service to use for generation",
        items=[
            ('GCS', "Self-Hosted ComfyUI", "Connect directly to a self-hosted ComfyUI instance (GCS, AWS, or Localhost)"),
            ('RUNCOMFY', "RunComfy Cloud", "Use RunComfy serverless cloud API (Managed, requires API credentials)")
        ],
        default='GCS'
    )
    
    gcs_server_url: StringProperty(
        name="Server URL",
        description="URL of your ComfyUI instance (e.g., http://34.19.119.45:8188 or http://127.0.0.1:8188)",
        default="http://127.0.0.1:8188"
    )
    
    gcs_server_status: StringProperty(
        name="GCS Server Status",
        description="Connection status of the GCS server",
        default="Not Connected"
    )

    gcs_download_preview_images: BoolProperty(
        name="Download Preview Images",
        description="Download Canny and Depth preview images for visual feedback (stored in temp directory)",
        default=True
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
        
        # ================================================================
        # BASIC SETTINGS (always visible, minimal)
        # ================================================================
        basic_box = layout.box()
        basic_box.label(text="Basic Settings", icon='SETTINGS')
        
        # Backend selector
        basic_box.prop(self, "api_backend", text="Backend")
        basic_box.separator()
        
        # Self-Hosted ComfyUI (GCS) - minimal setup
        if self.api_backend == 'GCS':
            basic_box.prop(self, "gcs_server_url", text="Server URL")
        
            # Test button
            row = basic_box.row()
            row.scale_y = 1.3
            row.operator("style_engine.test_gcs_connection", text="Test Connection", icon='PLUGIN')
        
        # RunComfy Cloud - minimal credentials
        else:
            basic_box.prop(self, "credentials_file_path", text="Credentials File")
            row = basic_box.row()
            row.scale_y = 1.3
            row.operator("style_engine.import_credentials", text="Import Credentials", icon='IMPORT')
            
            basic_box.separator()
        
            # Manual credentials (compact)
            basic_box.prop(self, "show_api_keys", text="Show Credentials", toggle=True)
        if self.show_api_keys:
                basic_box.prop(self, "runcomfy_api_token", text="API Token")
                basic_box.prop(self, "runcomfy_user_id", text="User ID")
            
            # Test button
            row = basic_box.row()
            row.scale_y = 1.3
            row.operator("style_engine.test_connection", text="Test Connection", icon='PLUGIN')
            
        # ================================================================
        # ADVANCED SETTINGS (collapsible, hidden by default)
        # ================================================================
            layout.separator()
        advanced_box = layout.box()
        header_row = advanced_box.row(align=True)
        icon = 'TRIA_DOWN' if self.show_advanced_settings else 'TRIA_RIGHT'
        header_row.prop(self, "show_advanced_settings", text="Advanced Settings", 
                           icon=icon, emboss=False, toggle=True)
            
        if self.show_advanced_settings:
            
            # GCS: Preview images option
            if self.api_backend == 'GCS':
                advanced_box.separator()
                advanced_box.label(text="Preview Images", icon='IMAGE_DATA')
                advanced_box.prop(self, "gcs_download_preview_images", text="Download Canny & Depth")
            
            # RunComfy: Workflow & Hardware
            if self.api_backend == 'RUNCOMFY':
                advanced_box.separator()
                advanced_box.label(text="Workflow Configuration", icon='FILE_SCRIPT')
                advanced_box.prop(self, "runcomfy_workflow_id", text="Workflow ID")
                advanced_box.prop(self, "runcomfy_deployment_id", text="Deployment ID")
                
                advanced_box.separator()
                advanced_box.label(text="Hardware Settings", icon='SHADING_RENDERED')
                advanced_box.prop(self, "runcomfy_hardware_tier", text="GPU Tier")
                
                col = advanced_box.column(align=True)
                col.prop(self, "runcomfy_min_instances")
                col.prop(self, "runcomfy_max_instances")
                col.prop(self, "runcomfy_queue_size")
                col.prop(self, "runcomfy_keep_warm_seconds")
                
            # Timeout settings (both backends)
            advanced_box.separator()
            advanced_box.label(text="Timeout Configuration", icon='SORTTIME')
            col = advanced_box.column(align=True)
            col.prop(self, "runcomfy_request_timeout")
            col.prop(self, "runcomfy_poll_interval")
            
            # ComfyUI path
            advanced_box.separator()
            advanced_box.label(text="ComfyUI Installation", icon='FILE_FOLDER')
            advanced_box.prop(self, "comfy_path", text="Path")
            
            # Conflict resolution
            advanced_box.separator()
            advanced_box.label(text="Conflict Resolution", icon='ERROR')
            advanced_box.prop(self, "debug_mode", text="Debug Mode")
            
            col = advanced_box.column(align=True)
            col.prop(self, "camera_name_override", text="Camera Name")
            col.prop(self, "workspace_name_override", text="Workspace Name")
            col.prop(self, "image_name_override", text="Image Name")
            
            # Feature toggles
            advanced_box.separator()
            advanced_box.label(text="Feature Toggles", icon='PREFERENCES')
            col = advanced_box.column(align=True)
            col.prop(self, "enable_heavypoly_compatibility")
            col.prop(self, "enable_camera_switching")
            col.prop(self, "enable_workspace_creation")
            col.prop(self, "enable_viewport_split")
            col.prop(self, "enable_auto_render")


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


class WM_OT_TestGCSConnection(bpy.types.Operator):
    """Test connection to GCS ComfyUI Server"""
    bl_idname = "style_engine.test_gcs_connection"
    bl_label = "Test Server Connection"
    bl_description = "Test the connection to your self-hosted ComfyUI server"
    
    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        
        # Check if server URL is set
        server_url = prefs.gcs_server_url
        
        if not server_url:
            self.report({'ERROR'}, "Server URL is not set!")
            print("[GCS] ❌ Test failed: Server URL not configured")
            prefs.gcs_server_status = "Not Connected"
            return {'CANCELLED'}
        
        # Test connection
        try:
            from . import runcomfy_server_client
            
            self.report({'INFO'}, f"Testing connection to: {server_url}...")
            print(f"[GCS] =========================================")
            print(f"[GCS] CONNECTION TEST")
            print(f"[GCS] Target: {server_url}")
            print(f"[GCS] =========================================")
            
            # Create server client
            server_client = runcomfy_server_client.ComfyUIServerClient(server_url, timeout=10)
            
            # Perform health check
            health = server_client.check_server_health()
            
            # Report results
            if health['healthy']:
                prefs.gcs_server_status = "Connected"
                self.report({'INFO'}, f"✅ Server is healthy and ready!")
                print(f"[GCS] ✅ TEST RESULT: SERVER IS HEALTHY")
                print(f"[GCS] {health['details']}")
            elif health['connection']['reachable']:
                prefs.gcs_server_status = "Reachable (Warning)"
                self.report({'WARNING'}, f"⚠ Server is reachable but may not be fully ready")
                print(f"[GCS] ⚠ TEST RESULT: SERVER REACHABLE BUT WARNING")
                print(f"[GCS] {health['details']}")
            else:
                prefs.gcs_server_status = "Connection Failed"
                error = health['connection'].get('error', 'Unknown error')
                self.report({'ERROR'}, f"❌ Connection failed: {error}")
                print(f"[GCS] ❌ TEST RESULT: CONNECTION FAILED")
                print(f"[GCS] Error: {error}")
            
            print(f"[GCS] =========================================")
            
            return {'FINISHED'}
            
        except runcomfy_server_client.ServerAPIError as e:
            error_msg = str(e)
            prefs.gcs_server_status = "Connection Failed"
            self.report({'ERROR'}, f"❌ Server error: {error_msg}")
            print(f"[GCS] ❌ Test failed: {error_msg}")
            return {'CANCELLED'}
            
        except Exception as e:
            prefs.gcs_server_status = "Error"
            self.report({'ERROR'}, f"❌ Unexpected error: {e}")
            print(f"[GCS] ❌ Unexpected error during test: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class WM_OT_ImportCredentials(bpy.types.Operator):
    """Import credentials from credentials.txt file"""
    bl_idname = "style_engine.import_credentials"
    bl_label = "Import Credentials"
    bl_description = "Load API credentials from the selected credentials.txt file (or auto-search if path is empty)"
    
    def execute(self, context):
        prefs = context.preferences.addons['styleengine'].preferences
        
        # Import the parsing function from utils
        from . import utils
        
        # Get the file path from preferences
        file_path = prefs.credentials_file_path if prefs.credentials_file_path else None
        
        if file_path:
            self.report({'INFO'}, f"Loading credentials from: {file_path}")
            print(f"[Style Engine] Loading credentials from: {file_path}")
        else:
            self.report({'INFO'}, "Looking for credentials.txt in default locations...")
            print("[Style Engine] Searching for credentials.txt in default locations...")
        
        # Parse credentials file
        success, data, message = utils.parse_credentials_file(file_path)
        
        if not success:
            self.report({'ERROR'}, f"❌ {message}")
            print(f"[Style Engine] ❌ Import failed: {message}")
            return {'CANCELLED'}
        
        # Apply credentials to preferences
        if data.get('api_token'):
            prefs.runcomfy_api_token = data['api_token']
            print(f"  ✓ Imported API Token: {data['api_token'][:8]}...")
        
        if data.get('user_id'):
            prefs.runcomfy_user_id = data['user_id']
            print(f"  ✓ Imported User ID: {data['user_id'][:8]}...")
        
        if data.get('workflow_id'):
            prefs.runcomfy_workflow_id = data['workflow_id']
            print(f"  ✓ Imported Workflow ID: {data['workflow_id'][:8]}...")
        
        if data.get('deployment_id'):
            prefs.runcomfy_deployment_id = data['deployment_id']
            print(f"  ✓ Imported Deployment ID: {data['deployment_id'][:8]}...")
        
        # Success message
        self.report({'INFO'}, f"✅ {message}")
        print(f"[Style Engine] ✅ Credentials imported successfully!")
        
        # Show hint to test connection
        self.report({'INFO'}, "💡 Tip: Click 'Test Connection' to verify your credentials")
        
        return {'FINISHED'}


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
    WM_OT_TestGCSConnection,
    WM_OT_ImportCredentials,
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

