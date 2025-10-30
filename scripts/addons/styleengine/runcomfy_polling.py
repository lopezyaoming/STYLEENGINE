# ================================================================
#    RunComfy Polling System
#    Non-blocking status polling using Blender timers
# ================================================================

import bpy
import time
from .runcomfy_deployment import get_runcomfy_client, get_addon_prefs
from .runcomfy_client import RunComfyError


# ----------------------------------------------------------------
# REQUEST STATE
# ----------------------------------------------------------------

class RequestState:
    """Tracks state of an active RunComfy request"""
    
    def __init__(self, deployment_id, request_id, callback, workflow_type):
        """
        Initialize request state.
        
        Args:
            deployment_id: RunComfy deployment ID
            request_id: Request ID from submit_inference
            callback: Callback function(success, result=None, error=None)
            workflow_type: 'sdxl' or 'ipadapter'
        """
        self.deployment_id = deployment_id
        self.request_id = request_id
        self.status = "in_queue"
        self.callback = callback
        self.workflow_type = workflow_type
        self.start_time = time.time()
        self.last_poll = 0
        self.error_count = 0


# ----------------------------------------------------------------
# POLLER
# ----------------------------------------------------------------

class RunComfyPoller:
    """Manages background polling of RunComfy requests"""
    
    # Class-level state (persists across calls)
    active_requests = {}  # request_id -> RequestState
    
    @classmethod
    def start_polling(cls, deployment_id, request_id, callback, workflow_type):
        """
        Start polling for a request.
        
        Args:
            deployment_id: Deployment ID
            request_id: Request ID
            callback: Callback function(success, result=None, error=None)
            workflow_type: 'sdxl' or 'ipadapter'
        """
        # Register request
        cls.active_requests[request_id] = RequestState(
            deployment_id=deployment_id,
            request_id=request_id,
            callback=callback,
            workflow_type=workflow_type
        )
        
        print(f"[RunComfy] Started polling for request {request_id[:8]}...")
        
        # Register timer if not already running
        if not bpy.app.timers.is_registered(cls._poll_tick):
            prefs = get_addon_prefs()
            interval = prefs.runcomfy_poll_interval
            bpy.app.timers.register(cls._poll_tick, first_interval=interval, persistent=True)
            print(f"[RunComfy] Polling timer started (interval: {interval}s)")
    
    @classmethod
    def _poll_tick(cls):
        """
        Timer callback - poll all active requests.
        
        Returns:
            float: Interval for next poll, or None to stop timer
        """
        if not cls.active_requests:
            print("[RunComfy] No active requests, stopping timer")
            return None
        
        try:
            prefs = get_addon_prefs()
            client = get_runcomfy_client()
        except RunComfyError as e:
            print(f"[RunComfy] Failed to get client: {e}")
            # Stop timer if can't get client
            return None
        
        completed = []
        current_time = time.time()
        
        for request_id, state in cls.active_requests.items():
            try:
                # Check timeout
                elapsed = current_time - state.start_time
                if elapsed > prefs.runcomfy_request_timeout:
                    print(f"[RunComfy] Request {request_id[:8]} timed out after {elapsed:.0f}s")
                    state.callback(success=False, error=f"Timeout after {elapsed:.0f}s")
                    completed.append(request_id)
                    continue
                
                # Poll status
                status_data = client.check_status(state.deployment_id, request_id)
                new_status = status_data.get('status', 'unknown')
                
                # Log status changes
                if new_status != state.status:
                    print(f"[RunComfy] Request {request_id[:8]}: {state.status} → {new_status}")
                    state.status = new_status
                
                # Handle completion
                if state.status == 'completed':
                    result = client.get_result(state.deployment_id, request_id)
                    state.callback(success=True, result=result)
                    completed.append(request_id)
                    print(f"[RunComfy] Request {request_id[:8]} completed!")
                
                # Handle failure
                elif state.status == 'failed':
                    result = client.get_result(state.deployment_id, request_id)
                    error_msg = result.get('error', 'Unknown error')
                    state.callback(success=False, error=error_msg)
                    completed.append(request_id)
                    print(f"[RunComfy] Request {request_id[:8]} failed: {error_msg}")
                
                # Reset error count on successful poll
                state.error_count = 0
                state.last_poll = current_time
                
            except RunComfyError as e:
                # Handle polling errors
                state.error_count += 1
                print(f"[RunComfy] Error polling {request_id[:8]}: {e} (count: {state.error_count})")
                
                # Give up after 5 consecutive errors
                if state.error_count >= 5:
                    print(f"[RunComfy] Too many errors for {request_id[:8]}, giving up")
                    state.callback(success=False, error=f"Too many polling errors: {e}")
                    completed.append(request_id)
        
        # Clean up completed requests
        for req_id in completed:
            del cls.active_requests[req_id]
            print(f"[RunComfy] Cleaned up request {req_id[:8]}")
        
        # Return interval or None to stop timer
        if cls.active_requests:
            return prefs.runcomfy_poll_interval
        else:
            print("[RunComfy] All requests complete, stopping timer")
            return None
    
    @classmethod
    def cancel_request(cls, request_id):
        """
        Cancel an active request.
        
        Args:
            request_id: Request ID to cancel
        
        Returns:
            bool: True if cancelled, False if not found
        """
        if request_id not in cls.active_requests:
            return False
        
        state = cls.active_requests[request_id]
        
        try:
            client = get_runcomfy_client()
            client.cancel_request(state.deployment_id, request_id)
            print(f"[RunComfy] Cancelled request {request_id[:8]}")
        except RunComfyError as e:
            print(f"[RunComfy] Failed to cancel request: {e}")
        
        # Remove from active requests
        state.callback(success=False, error="Cancelled by user")
        del cls.active_requests[request_id]
        
        return True
    
    @classmethod
    def cancel_all(cls):
        """Cancel all active requests"""
        for request_id in list(cls.active_requests.keys()):
            cls.cancel_request(request_id)
    
    @classmethod
    def get_server_status(cls):
        """
        Get server status for UI display.
        
        Returns:
            str: Status string ("Disconnected", "Connecting", "Active", "Running Workflow")
        """
        if not cls.active_requests:
            return "Disconnected"
        
        statuses = [state.status for state in cls.active_requests.values()]
        
        if any(s == 'in_progress' for s in statuses):
            return "Running Workflow"
        elif any(s == 'in_queue' for s in statuses):
            return "Connecting"
        else:
            return "Active"
    
    @classmethod
    def get_active_request_info(cls):
        """
        Get information about active requests.
        
        Returns:
            list: List of dicts with request info
        """
        current_time = time.time()
        info = []
        
        for request_id, state in cls.active_requests.items():
            elapsed = int(current_time - state.start_time)
            info.append({
                'request_id': request_id,
                'workflow_type': state.workflow_type,
                'status': state.status,
                'elapsed': elapsed
            })
        
        return info


# ----------------------------------------------------------------
# CLEANUP
# ----------------------------------------------------------------

def cleanup_poller():
    """Cleanup function called when addon is disabled"""
    if bpy.app.timers.is_registered(RunComfyPoller._poll_tick):
        bpy.app.timers.unregister(RunComfyPoller._poll_tick)
        print("[RunComfy] Polling timer unregistered")
    
    RunComfyPoller.active_requests.clear()
    print("[RunComfy] Active requests cleared")

