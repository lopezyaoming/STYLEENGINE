# ================================================================
#    Progress Bar - Bridge Polling System
#    Polls HTTP bridge (port 8189) to get ComfyUI progress data
#    Uses bpy.app.timers for non-blocking polling
# ================================================================

import bpy
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse


# ----------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------

BRIDGE_PORT = 8189
POLL_INTERVAL = 2.0  # seconds


# ----------------------------------------------------------------
# POLLING STATE
# ----------------------------------------------------------------

class BridgePollerState:
    """Global state for the bridge polling system"""
    
    is_polling = False
    last_status = None
    connection_status = "disconnected"  # connected, disconnected
    error_count = 0
    permanently_offline = False  # Once offline, stay offline until Blender restart
    
    # Display state (what we actually show, may differ from bridge)
    display_progress = 0.0
    display_status = "ready"
    display_node = "Idle"
    
    # Track if we saw progress > 0 (job was running)
    saw_progress = False
    
    @classmethod
    def reset(cls):
        """Reset all state"""
        cls.is_polling = False
        cls.last_status = None
        cls.connection_status = "disconnected"
        cls.error_count = 0
        cls.permanently_offline = False
        cls.display_progress = 0.0
        cls.display_status = "ready"
        cls.display_node = "Idle"
        cls.saw_progress = False


# ----------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------

def get_bridge_url():
    """
    Build the bridge URL from addon preferences.
    Uses the server IP from settings with port 8189.
    
    Returns:
        str: Bridge URL (e.g., "http://34.19.119.45:8189")
        None: If no server address configured
    """
    try:
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        base_url = prefs.gcs_server_url
        
        if not base_url:
            return None
        
        # Parse the URL to extract just the host
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.path.split('/')[0].split(':')[0]
        scheme = parsed.scheme if parsed.scheme else 'http'
        
        # Build bridge URL with port 8189
        bridge_url = f"{scheme}://{host}:{BRIDGE_PORT}"
        return bridge_url
        
    except Exception as e:
        print(f"[Progress Bridge] Error getting bridge URL: {e}")
        return None


def _tag_redraw():
    """
    Force UI redraw so progress bar updates in the N-panel.
    Tags all VIEW_3D areas for redraw.
    """
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        pass  # Silently fail if context is unavailable


def fetch_bridge_status(bridge_url):
    """
    Fetch status from the bridge service.
    
    Args:
        bridge_url: Base URL of the bridge (e.g., "http://34.19.119.45:8189")
    
    Returns:
        dict: Parsed JSON status or None if failed
        
    Expected JSON Schema:
    {
        "status": "ready",           // ready, queuing, processing, disconnected
        "progress": 0.45,            // float 0.0 to 1.0
        "node_name": "Node 3",       // String indicating the active node
        "queue_remaining": 0,        // Int
        "last_msg_type": "progress"  // String for debugging
    }
    """
    try:
        url = f"{bridge_url}/status"
        
        # Create request with short timeout to prevent hanging
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'StyleEngine-Blender/1.0')
        
        # Short timeout (3 seconds) to prevent UI freeze
        with urllib.request.urlopen(req, timeout=3) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
            
    except urllib.error.URLError as e:
        # Network error (server down, unreachable, etc.)
        return None
        
    except urllib.error.HTTPError as e:
        # HTTP error (404, 500, etc.)
        print(f"[Progress Bridge] HTTP Error {e.code}: {e.reason}")
        return None
        
    except json.JSONDecodeError as e:
        print(f"[Progress Bridge] Invalid JSON response: {e}")
        return None
        
    except Exception as e:
        print(f"[Progress Bridge] Unexpected error: {e}")
        return None


# ----------------------------------------------------------------
# POLLING TIMER
# ----------------------------------------------------------------

def _has_active_requests():
    """
    Check if there are any active requests in the RunComfy polling system.
    This tells us if Blender is still waiting for a job to complete.
    
    Returns:
        bool: True if there are active requests being polled
    """
    try:
        from . import runcomfy_polling
        return len(runcomfy_polling.RunComfyPoller.active_requests) > 0
    except Exception:
        return False


def _poll_bridge_tick():
    """
    Timer callback - polls the bridge service.
    
    Returns:
        float: Interval for next poll, or None to stop timer
    """
    try:
        # CRITICAL: If permanently offline, stop polling immediately
        if BridgePollerState.permanently_offline:
            print("[Progress Bridge] ⛔ PERMANENTLY OFFLINE - Stopped polling (restart Blender to reconnect)")
            BridgePollerState.is_polling = False
            return None
        
        # Check if polling should continue
        if not BridgePollerState.is_polling:
            print("[Progress Bridge] Polling stopped")
            BridgePollerState.connection_status = "disconnected"
            return None
        
        # Get bridge URL
        bridge_url = get_bridge_url()
        
        if not bridge_url:
            print("[Progress Bridge] ❌ No server address configured")
            BridgePollerState.connection_status = "disconnected"
            BridgePollerState.error_count += 1
            # Mark as permanently offline to prevent crash
            BridgePollerState.permanently_offline = True
            return None
        
        # Fetch status from bridge
        status = fetch_bridge_status(bridge_url)
        
        if status is None:
            # Connection failed - STOP POLLING PERMANENTLY
            BridgePollerState.error_count += 1
            BridgePollerState.connection_status = "disconnected"
            BridgePollerState.last_status = None
            BridgePollerState.permanently_offline = True
            BridgePollerState.is_polling = False
            
            print(f"[Progress Bridge] ❌ DISCONNECTED (error count: {BridgePollerState.error_count})")
            print(f"[Progress Bridge]    Target: {bridge_url}/status")
            print(f"[Progress Bridge] ⛔ Marked as PERMANENTLY OFFLINE - Restart Blender to reconnect")
            
            # STOP TIMER IMMEDIATELY
            return None
            
        else:
            # Success! Parse and print the status
            BridgePollerState.error_count = 0
            BridgePollerState.connection_status = "connected"
            BridgePollerState.last_status = status
            
            # Extract fields from JSON
            server_status = status.get('status', 'unknown')
            bridge_progress = status.get('progress', 0.0)
            node_name = status.get('node_name', '')
            queue_remaining = status.get('queue_remaining', 0)
            last_msg_type = status.get('last_msg_type', '')
            
            # Check if there are active requests in the polling system
            has_active_requests = _has_active_requests()
            
            # Track if we've seen progress (job was running)
            if bridge_progress > 0:
                BridgePollerState.saw_progress = True
            
            # Determine display progress with "hold at 100%" logic
            if bridge_progress > 0:
                # Job is actively running, show actual progress
                display_progress = bridge_progress
                display_node = node_name
                display_status = server_status
            elif BridgePollerState.saw_progress and has_active_requests:
                # Bridge says 0% but we have active requests and saw progress
                # Hold at 100% until request completes
                display_progress = 1.0
                display_node = "Downloading..."
                display_status = "finishing"
            else:
                # Truly idle - no active requests
                display_progress = 0.0
                display_node = "Idle"
                display_status = "ready"
                BridgePollerState.saw_progress = False  # Reset for next job
            
            # Update display state
            BridgePollerState.display_progress = display_progress
            BridgePollerState.display_status = display_status
            BridgePollerState.display_node = display_node
            
            # Force UI redraw so progress bar updates
            _tag_redraw()
            
            # Calculate percentage for display
            percent = int(display_progress * 100)
            
            # Print parsed JSON to console
            print(f"[Progress Bridge] ✓ CONNECTED")
            print(f"[Progress Bridge]    Status: {display_status}")
            print(f"[Progress Bridge]    Progress: {percent}% ({display_progress:.2f})")
            print(f"[Progress Bridge]    Node: {display_node}")
            print(f"[Progress Bridge]    Queue: {queue_remaining}")
            print(f"[Progress Bridge]    Active Requests: {has_active_requests}")
            print(f"[Progress Bridge]    ---")
            
            # Continue polling
            return POLL_INTERVAL
        
    except Exception as e:
        # CRITICAL ERROR - Stop polling to prevent crashes
        print(f"[Progress Bridge] ⚠️ CRITICAL ERROR in polling: {e}")
        BridgePollerState.permanently_offline = True
        BridgePollerState.connection_status = "disconnected"
        BridgePollerState.is_polling = False
        print("[Progress Bridge] ⛔ Marked as PERMANENTLY OFFLINE - Restart Blender to reconnect")
        return None


# ----------------------------------------------------------------
# PUBLIC API
# ----------------------------------------------------------------

def start_polling():
    """
    Start polling the bridge service.
    Safe to call multiple times (won't duplicate timers).
    """
    if BridgePollerState.is_polling:
        print("[Progress Bridge] Already polling")
        return
    
    bridge_url = get_bridge_url()
    if not bridge_url:
        print("[Progress Bridge] ❌ Cannot start: No server address configured")
        return
    
    BridgePollerState.is_polling = True
    BridgePollerState.error_count = 0
    
    print(f"[Progress Bridge] =========================================")
    print(f"[Progress Bridge] Starting bridge polling")
    print(f"[Progress Bridge] Target: {bridge_url}/status")
    print(f"[Progress Bridge] Interval: {POLL_INTERVAL}s")
    print(f"[Progress Bridge] =========================================")
    
    # Register timer if not already registered
    if not bpy.app.timers.is_registered(_poll_bridge_tick):
        bpy.app.timers.register(_poll_bridge_tick, first_interval=0.1, persistent=True)


def stop_polling():
    """
    Stop polling the bridge service.
    """
    BridgePollerState.is_polling = False
    
    # Unregister timer if registered
    if bpy.app.timers.is_registered(_poll_bridge_tick):
        bpy.app.timers.unregister(_poll_bridge_tick)
    
    BridgePollerState.reset()
    print("[Progress Bridge] Polling stopped and state reset")


def is_polling():
    """Check if currently polling"""
    return BridgePollerState.is_polling


def get_last_status():
    """Get the last received status (or None)"""
    return BridgePollerState.last_status


def get_connection_status():
    """Get connection status: 'connected' or 'disconnected'"""
    return BridgePollerState.connection_status


def get_display_progress():
    """
    Get the display progress value (0.0 to 1.0).
    This may differ from the bridge value when holding at 100%.
    """
    return BridgePollerState.display_progress


def get_display_status():
    """Get the display status string"""
    return BridgePollerState.display_status


def get_display_node():
    """Get the display node name"""
    return BridgePollerState.display_node


# ----------------------------------------------------------------
# OPERATORS
# ----------------------------------------------------------------

class WM_OT_ConnectProgressBridge(bpy.types.Operator):
    """Connect to the progress bridge service"""
    bl_idname = "style_engine.connect_progress_bridge"
    bl_label = "Connect Progress Bridge"
    bl_description = "Start polling the progress bridge for real-time status updates"
    
    def execute(self, context):
        if is_polling():
            self.report({'INFO'}, "Already connected to progress bridge")
        else:
            start_polling()
            self.report({'INFO'}, "Connected to progress bridge")
        return {'FINISHED'}


class WM_OT_DisconnectProgressBridge(bpy.types.Operator):
    """Disconnect from the progress bridge service"""
    bl_idname = "style_engine.disconnect_progress_bridge"
    bl_label = "Disconnect Progress Bridge"
    bl_description = "Stop polling the progress bridge"
    
    def execute(self, context):
        stop_polling()
        self.report({'INFO'}, "Disconnected from progress bridge")
        return {'FINISHED'}


# ----------------------------------------------------------------
# REGISTRATION
# ----------------------------------------------------------------

classes = (
    WM_OT_ConnectProgressBridge,
    WM_OT_DisconnectProgressBridge,
)


def _delayed_start_polling():
    """
    Delayed start of polling to ensure addon is fully loaded.
    Called via bpy.app.timers after registration.
    """
    # Only start if server URL is configured
    bridge_url = get_bridge_url()
    if bridge_url:
        start_polling()
        print("[Progress Bridge] Auto-started polling on addon load")
    else:
        print("[Progress Bridge] Skipped auto-start: No server address configured")
    return None  # Don't repeat


def register():
    """Register progress bar classes and auto-start polling"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Auto-start polling after a short delay (0.5s) to ensure everything is loaded
    bpy.app.timers.register(_delayed_start_polling, first_interval=0.5)
    
    print("[Progress Bridge] Registered")


def unregister():
    """Unregister progress bar classes and cleanup"""
    # Stop polling if active
    stop_polling()
    
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("[Progress Bridge] Unregistered")


# ----------------------------------------------------------------
# CLEANUP
# ----------------------------------------------------------------

def cleanup():
    """Cleanup function called when addon is disabled"""
    stop_polling()
