# ================================================================
#    RunComfy Deployment Management
#    Handles deployment creation, validation, and lifecycle
#    Supports both Serverless and Server API modes
# ================================================================

import bpy
from .runcomfy_client import RunComfyClient, RunComfyError, RunComfyDeploymentError
from .runcomfy_server_client import ComfyUIServerClient, ServerAPIError


# ----------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------

def get_addon_prefs():
    """Get Style Engine addon preferences"""
    return bpy.context.preferences.addons['styleengine'].preferences


def get_runcomfy_client():
    """
    Create RunComfy client from preferences (for Serverless API).
    
    Returns:
        RunComfyClient: Configured client instance
    
    Raises:
        RunComfyError: If credentials not set
    """
    prefs = get_addon_prefs()
    
    # Get API credentials (prefer env vars if enabled)
    if prefs.use_env_vars:
        import os
        api_token = os.environ.get('RUNCOMFY_API_TOKEN', prefs.runcomfy_api_token)
        user_id = os.environ.get('RUNCOMFY_USER_ID', prefs.runcomfy_user_id)
    else:
        api_token = prefs.runcomfy_api_token
        user_id = prefs.runcomfy_user_id
    
    if not api_token or not user_id:
        raise RunComfyError("RunComfy credentials not configured. Please set API token and User ID in addon preferences.")
    
    return RunComfyClient(api_token, user_id, timeout=prefs.runcomfy_request_timeout)


def get_server_client():
    """
    Create ComfyUI Server client from preferences (for Server API mode).
    
    Returns:
        ComfyUIServerClient: Configured server client instance
    
    Raises:
        ServerAPIError: If server URL not set
    """
    prefs = get_addon_prefs()
    
    server_url = prefs.comfyui_server_url
    
    if not server_url:
        raise ServerAPIError("ComfyUI Server URL not configured. Please set the server URL in addon preferences.")
    
    return ComfyUIServerClient(server_url, timeout=prefs.runcomfy_request_timeout)


def is_server_mode():
    """
    Check if addon is in Server API mode.
    
    Returns:
        bool: True if Server API mode is enabled
    """
    prefs = get_addon_prefs()
    return prefs.use_server_api


# ----------------------------------------------------------------
# DEPLOYMENT MANAGER
# ----------------------------------------------------------------

class DeploymentManager:
    """Manages RunComfy deployment lifecycle (Serverless and Server modes)"""
    
    @staticmethod
    def ensure_deployment(workflow_type='sdxl'):
        """
        Ensure deployment/server is ready for workflow execution.
        
        In Serverless mode: Ensures deployment exists (auto-creates if needed)
        In Server mode: Validates server connection
        
        Args:
            workflow_type: 'sdxl' or 'ipadapter'
        
        Returns:
            str: deployment_id (serverless) or 'server' (server mode)
        
        Raises:
            RunComfyError/ServerAPIError: If setup cannot be ensured
        """
        if is_server_mode():
            # Server API mode - verify server connection
            print(f"[Server API] Validating ComfyUI server connection...")
            return DeploymentManager._ensure_server_connection()
        else:
            # Serverless mode - ensure deployment exists
            print(f"[Serverless API] Ensuring deployment for {workflow_type}...")
            return DeploymentManager._ensure_serverless_deployment(workflow_type)
    
    @staticmethod
    def _ensure_server_connection():
        """
        Validate connection to ComfyUI server (Server API mode) with detailed diagnostics.
        
        Returns:
            str: 'server' to indicate server mode
        
        Raises:
            ServerAPIError: If server is not reachable or not healthy
        """
        print(f"[Server API] =========================================")
        print(f"[Server API] SERVER CONNECTION VALIDATION")
        print(f"[Server API] =========================================")
        
        try:
            server_client = get_server_client()
            server_url = server_client.server_url
            
            print(f"[Server API] Target server: {server_url}")
            print(f"[Server API]")
            
            # Step 1: Check connection
            print(f"[Server API] Step 1: Testing basic connection...")
            connected, conn_status = server_client.check_connection()
            
            if not connected:
                error_msg = conn_status.get('error', 'Unknown connection error')
                print(f"[Server API]")
                print(f"[Server API] ❌ CONNECTION FAILED")
                print(f"[Server API] Error: {error_msg}")
                print(f"[Server API]")
                print(f"[Server API] Troubleshooting:")
                print(f"[Server API]   1. Verify server URL is correct: {server_url}")
                print(f"[Server API]   2. Check if server is running (visit URL in browser)")
                print(f"[Server API]   3. Verify network connectivity")
                print(f"[Server API]   4. Check if server requires authentication")
                print(f"[Server API]")
                
                raise ServerAPIError(
                    f"Cannot connect to ComfyUI server at {server_url}. "
                    f"Error: {error_msg}. "
                    "Please ensure the server is running and the URL is correct."
                )
            
            print(f"[Server API] ✓ Basic connection successful")
            print(f"[Server API]")
            
            # Step 2: Check server health
            print(f"[Server API] Step 2: Checking server health...")
            health = server_client.check_server_health()
            
            if not health['healthy']:
                print(f"[Server API]")
                print(f"[Server API] ⚠ SERVER HEALTH WARNING")
                print(f"[Server API] Details: {health['details']}")
                print(f"[Server API]")
                print(f"[Server API] Server is reachable but may not be fully ready.")
                print(f"[Server API] You can try generating, but errors may occur.")
                print(f"[Server API]")
            else:
                print(f"[Server API] ✓ Server health check passed")
                print(f"[Server API]")
            
            # Summary
            print(f"[Server API] =========================================")
            print(f"[Server API] CONNECTION STATUS: ✓ CONNECTED")
            print(f"[Server API] Server URL: {server_url}")
            if health.get('connection', {}).get('queue_info'):
                queue_info = health['connection']['queue_info']
                running = len(queue_info.get('queue_running', []))
                pending = len(queue_info.get('queue_pending', []))
                print(f"[Server API] Queue: {running} running, {pending} pending")
            print(f"[Server API] Health: {'✓ Healthy' if health['healthy'] else '⚠ Warning'}")
            print(f"[Server API] =========================================")
            print(f"[Server API]")
            
            return 'server'
            
        except ServerAPIError as e:
            print(f"[Server API]")
            print(f"[Server API] ❌ SERVER CONNECTION VALIDATION FAILED")
            print(f"[Server API] =========================================")
            raise ServerAPIError(f"Server connection failed: {e}")
        except Exception as e:
            print(f"[Server API]")
            print(f"[Server API] ❌ UNEXPECTED ERROR DURING VALIDATION")
            print(f"[Server API] Error: {e}")
            print(f"[Server API] =========================================")
            import traceback
            traceback.print_exc()
            raise ServerAPIError(f"Unexpected error during server validation: {e}")
    
    @staticmethod
    def _ensure_serverless_deployment(workflow_type):
        """
        Ensure deployment exists for workflow type (Serverless mode).
        Hybrid approach: Try provided deployment_id, auto-create if needed.
        
        Args:
            workflow_type: 'sdxl' or 'ipadapter'
        
        Returns:
            str: deployment_id
        
        Raises:
            RunComfyError: If deployment cannot be ensured
        """
        prefs = get_addon_prefs()
        client = get_runcomfy_client()
        
        # Use unified deployment (same for both SDXL and IPAdapter)
        deployment_id = prefs.runcomfy_deployment_id
        workflow_id = prefs.runcomfy_workflow_id
        deployment_name = f"Style Engine - {workflow_type.upper()}"
        
        # Check if workflow_id is set
        if not workflow_id:
            raise RunComfyError(
                f"Workflow ID not configured. "
                "Please set workflow ID in addon preferences."
            )
        
        # Try to use provided deployment_id
        if deployment_id:
            try:
                if DeploymentManager.validate_deployment(client, deployment_id):
                    print(f"[Serverless API] Using existing deployment: {deployment_id[:8]}...")
                    return deployment_id
                else:
                    print(f"[Serverless API] Deployment {deployment_id[:8]} is disabled or invalid")
            except RunComfyDeploymentError:
                print(f"[Serverless API] Deployment {deployment_id[:8]} not found")
        
        # Auto-create deployment
        print(f"[Serverless API] Auto-creating deployment for {workflow_type}...")
        new_deployment = DeploymentManager.create_deployment_for_workflow(
            client=client,
            workflow_id=workflow_id,
            name=deployment_name,
            hardware=prefs.runcomfy_hardware_tier
        )
        
        new_deployment_id = new_deployment['id']
        print(f"[Serverless API] Created deployment: {new_deployment_id[:8]}...")
        
        # Save deployment_id to preferences (unified for both workflows)
        prefs.runcomfy_deployment_id = new_deployment_id
        
        return new_deployment_id
    
    @staticmethod
    def create_deployment_for_workflow(client, workflow_id, name, hardware):
        """
        Create deployment with hardware configuration from preferences.
        
        Args:
            client: RunComfyClient instance
            workflow_id: Workflow ID to deploy
            name: Deployment name
            hardware: Hardware tier (e.g., 'AMPERE_48')
        
        Returns:
            dict: Created deployment details
        """
        prefs = get_addon_prefs()
        
        # Build deployment config
        config = {
            'scaling': {
                'min_instances': prefs.runcomfy_min_instances,
                'max_instances': prefs.runcomfy_max_instances,
                'queue_size': prefs.runcomfy_queue_size,
            },
            'keep_warm_seconds': prefs.runcomfy_keep_warm_seconds,
        }
        
        try:
            deployment = client.create_deployment(
                workflow_id=workflow_id,
                name=name,
                hardware=hardware,
                config=config
            )
            return deployment
        except RunComfyError as e:
            raise RunComfyError(f"Failed to create deployment: {e}")
    
    @staticmethod
    def validate_deployment(client, deployment_id):
        """
        Check if deployment exists and is enabled.
        
        Args:
            client: RunComfyClient instance
            deployment_id: Deployment ID to validate
        
        Returns:
            bool: True if deployment is valid and enabled
        """
        try:
            deployment = client.get_deployment(deployment_id)
            return deployment.get('is_enabled', False)
        except RunComfyDeploymentError:
            return False
    
    @staticmethod
    def list_user_deployments():
        """
        List all deployments for the user.
        
        Returns:
            list: List of deployment dicts
        """
        try:
            client = get_runcomfy_client()
            return client.list_deployments()
        except RunComfyError as e:
            print(f"[RunComfy] Failed to list deployments: {e}")
            return []
    
    @staticmethod
    def get_deployment_info(deployment_id):
        """
        Get deployment information.
        
        Args:
            deployment_id: Deployment ID
        
        Returns:
            dict: Deployment details or None if not found
        """
        try:
            client = get_runcomfy_client()
            return client.get_deployment(deployment_id)
        except RunComfyError as e:
            print(f"[RunComfy] Failed to get deployment info: {e}")
            return None

