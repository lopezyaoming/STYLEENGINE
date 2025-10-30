# ================================================================
#    RunComfy Deployment Management
#    Handles deployment creation, validation, and lifecycle
# ================================================================

import bpy
from .runcomfy_client import RunComfyClient, RunComfyError, RunComfyDeploymentError


# ----------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------

def get_addon_prefs():
    """Get Style Engine addon preferences"""
    return bpy.context.preferences.addons['styleengine'].preferences


def get_runcomfy_client():
    """
    Create RunComfy client from preferences.
    
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


# ----------------------------------------------------------------
# DEPLOYMENT MANAGER
# ----------------------------------------------------------------

class DeploymentManager:
    """Manages RunComfy deployment lifecycle"""
    
    @staticmethod
    def ensure_deployment(workflow_type='sdxl'):
        """
        Ensure deployment exists for workflow type.
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
        
        # Determine which deployment to use
        if workflow_type == 'sdxl':
            deployment_id = prefs.runcomfy_deployment_id_sdxl
            workflow_id = prefs.runcomfy_workflow_id_sdxl
            deployment_name = "Style Engine - SDXL"
        elif workflow_type == 'ipadapter':
            deployment_id = prefs.runcomfy_deployment_id_ipadapter
            workflow_id = prefs.runcomfy_workflow_id_ipadapter
            deployment_name = "Style Engine - IPAdapter"
        else:
            raise RunComfyError(f"Unknown workflow type: {workflow_type}")
        
        # Check if workflow_id is set
        if not workflow_id:
            raise RunComfyError(
                f"{workflow_type.upper()} workflow ID not configured. "
                "Please set workflow ID in addon preferences."
            )
        
        # Try to use provided deployment_id
        if deployment_id:
            try:
                if DeploymentManager.validate_deployment(client, deployment_id):
                    print(f"[RunComfy] Using existing deployment: {deployment_id[:8]}...")
                    return deployment_id
                else:
                    print(f"[RunComfy] Deployment {deployment_id[:8]} is disabled or invalid")
            except RunComfyDeploymentError:
                print(f"[RunComfy] Deployment {deployment_id[:8]} not found")
        
        # Auto-create deployment
        print(f"[RunComfy] Auto-creating deployment for {workflow_type}...")
        new_deployment = DeploymentManager.create_deployment_for_workflow(
            client=client,
            workflow_id=workflow_id,
            name=deployment_name,
            hardware=prefs.runcomfy_hardware_tier
        )
        
        new_deployment_id = new_deployment['id']
        print(f"[RunComfy] Created deployment: {new_deployment_id[:8]}...")
        
        # Save deployment_id to preferences
        if workflow_type == 'sdxl':
            prefs.runcomfy_deployment_id_sdxl = new_deployment_id
        else:
            prefs.runcomfy_deployment_id_ipadapter = new_deployment_id
        
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

