# Auto-Launch Server Feature

**Date**: 2025-11-07  
**Status**: ✅ Implemented and Ready for Testing

## Overview

The Style Engine addon now supports **automatic server launching** when using Server API mode. This eliminates the need for manual server management through the RunComfy dashboard.

## How It Works

### Automatic Server Launch

When you enable "Use Server API" in preferences and attempt to generate an image:

1. **First Generation Attempt**
   - If no server URL is configured, the addon will automatically:
     - Launch a new ComfyUI server instance on RunComfy
     - Wait for the server to be ready (2-5 minutes)
     - Store the server URL and ID in preferences
     - Proceed with image generation

2. **Subsequent Generations**
   - Uses the stored server information
   - Validates server is still running
   - Proceeds directly to generation

### Manual Server Management

Users can also manually control servers through the preferences panel:

#### Start Server Button
- Launches a new ComfyUI server instance
- Displays status during launch and initialization
- Auto-populates server URL when ready

#### Test Connection Button
- Verifies server is reachable
- Performs health checks
- Updates server status display

#### Stop Server Button  
- Gracefully stops the running server
- Clears server URL and ID
- Frees up RunComfy resources

## User Interface

### Server Status Display

The preferences panel shows real-time server status:

```
Server Status: Running ✓
Server ID: 2b3d922d-f9b1-4353-b189...
```

Status indicators:
- **Running** ✓ - Server is healthy and ready
- **Starting** ⏱ - Server is launching (2-5 min)
- **Not Running** ✗ - No server active
- **Failed** ⚠ - Launch or connection failed

### Auto-Launch Flow

```
User clicks "Push to Generate"
    ↓
Is Server API mode enabled?
    ↓
Is server URL configured?
    ↓ (No)
Auto-launch new server
    ↓
Wait for server ready (console shows progress)
    ↓
Store server info in preferences
    ↓
Proceed with generation
```

## Configuration

### Required Settings

To use auto-launch, ensure these are configured in preferences:

1. **RunComfy Credentials**
   - API Token
   - User ID
   
2. **Server API Mode**
   - Enable "Use Server API" checkbox

3. **Hardware Tier** (optional)
   - Default: AMPERE_48
   - Can be changed in preferences

### Optional Settings

- **Workflow ID**: If you want to pre-load a specific workflow on server launch
- **Server Name**: Defaults to "Style Engine ComfyUI Server"

## Implementation Details

### Files Modified

1. **`runcomfy_server_manager.py`** (NEW)
   - `RunComfyServerManager` class
   - `create_server()` - Launch new server instance
   - `wait_for_server_ready()` - Poll until server is healthy
   - `get_server_status()` - Check current server state
   - `stop_server()` - Terminate server instance

2. **`prefs.py`**
   - Added server status properties:
     - `runcomfy_server_id` - Stores active server ID
     - `runcomfy_server_status` - Current status string
   - Added operators:
     - `WM_OT_StartServer` - Manual server launch
     - `WM_OT_StopServer` - Manual server stop
     - `WM_OT_TestServerConnection` - Health check (updated to update status)
   - Updated UI to show server status and control buttons

3. **`runcomfy_deployment.py`**
   - `_auto_launch_server()` - Auto-launch on first generation
   - `_ensure_server_connection()` - Validates server and triggers auto-launch if needed
   - Integration with `ensure_deployment()` for seamless mode switching

4. **`__init__.py`**
   - Import `runcomfy_server_manager` module
   - Include in fallback imports for macOS compatibility

### API Endpoints

The server manager uses the correct RunComfy Server API endpoints as per the [official documentation](https://comfyui-guides.runcomfy.com/api-reference):

```python
# Launch server
POST /prod/api/users/{user_id}/machines

# Get server status
GET /prod/api/users/{user_id}/machines/{server_id}

# Stop server
DELETE /prod/api/users/{user_id}/machines/{server_id}
```

All requests use `Authorization: Bearer {api_token}` header.

### Server Lifecycle

```
create_server()
    ↓
POST /prod/api/users/{user_id}/machines
    {
        "name": "Style Engine ComfyUI Server",
        "server_type": "large",  # Mapped from AMPERE_48
        "estimated_duration": 3600,  # 1 hour in seconds
        "version_id": "..." (optional)
    }
    ↓
Response:
    {
        "server_id": "server-id",
        "status": "Pending",
        "created_at": "..."
    }
    ↓
wait_for_server_ready()
    ↓
Poll GET /prod/api/users/{user_id}/machines/{server_id} every 15s
    ↓
Check response status field
    ↓
Status: "Ready" (capital R means fully operational)
    ↓
Extract main_service_url from response
```

**Hardware Tier Mapping:**
- `AMPERE_48` → `large`
- `AMPERE_80` → `extra-large`
- `ADA_24` → `2x-large`
- `H100` → `2xl-turbo`

### Error Handling

The system handles various error scenarios:

1. **Launch Fails**
   - Try multiple API endpoints
   - Show clear error message
   - Status: "Failed"

2. **Server Not Ready in Time**
   - Launch succeeds but server takes > 5 minutes
   - Status: "Starting (timeout)"
   - User can manually test connection later

3. **Connection Lost**
   - Existing server becomes unreachable
   - Show troubleshooting steps in console
   - Suggest checking RunComfy dashboard

4. **No Credentials**
   - Auto-launch requires API token and user ID
   - Clear error message directs user to preferences

## Console Output

### Successful Auto-Launch

```
[Server Manager] =========================================
[Server Manager] LAUNCHING NEW COMFYUI SERVER INSTANCE
[Server Manager] =========================================
[Server Manager] Configuration:
[Server Manager]   Name: Style Engine ComfyUI Server (Auto-launched)
[Server Manager]   Hardware: AMPERE_48
[Server Manager]
[Server Manager] Trying endpoint: POST /prod/v2/machines
[Server Manager]
[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL
[Server Manager] Server ID: 2b3d922d-f9b1-4353-b189...
[Server Manager] Server URL: https://2b3d922d-f9b1-4353-b189-comfyui.runcomfy.com
[Server Manager] Status: starting
[Server Manager] =========================================
[Server Manager] Waiting for server to be ready (this may take a few minutes)...
[Server Manager] =========================================
[Server Manager] WAITING FOR SERVER TO BE READY
[Server Manager] Server ID: 2b3d922d-f9b1-4353-b189...
[Server Manager] Timeout: 300s, Poll interval: 15s
[Server Manager] =========================================
[Server Manager] Attempt 1: Checking server status...
[Server Manager]   Status: starting
[Server Manager]   Ready: False
[Server Manager]   Server not ready yet, waiting 15s...
[Server Manager] Attempt 2: Checking server status...
[Server Manager]   Status: starting
[Server Manager]   Ready: False
[Server Manager]   Server not ready yet, waiting 15s...
...
[Server Manager] Attempt 8: Checking server status...
[Server Manager]   Status: running
[Server Manager]   Ready: True
[Server Manager]
[Server Manager] ✅ SERVER IS READY
[Server Manager] Server URL: https://2b3d922d-f9b1-4353-b189-comfyui.runcomfy.com
[Server Manager] Total wait time: 105.3s
[Server Manager] =========================================
```

### Connection Validation

```
[Server API] =========================================
[Server API] VALIDATING SERVER CONNECTION
[Server API] =========================================
[Server API] Server URL: https://2b3d922d-f9b1-4353-b189-comfyui.runcomfy.com
[Server API]
[Server API] Step 1: Testing basic connection...
[Server API] ✓ Basic connection successful
[Server API]
[Server API] Step 2: Checking server health...
[Server API] ✓ Server health check passed
[Server API]
[Server API] =========================================
[Server API] CONNECTION STATUS: ✓ CONNECTED
[Server API] Server URL: https://2b3d922d-f9b1-4353-b189-comfyui.runcomfy.com
[Server API] Queue: 0 running, 0 pending
[Server API] Health: ✓ Healthy
[Server API] =========================================
```

## User Workflow

### First-Time Setup

1. Install Style Engine addon
2. Open Preferences → Add-ons → Style Engine
3. Configure RunComfy credentials (API Token, User ID)
4. Enable "Use Server API"
5. Click "Push to Generate" in your workspace
6. Wait 2-5 minutes for auto-launch
7. Server URL auto-populates
8. Image generation proceeds

### Daily Use

1. Open Blender
2. Click "Push to Generate"
3. If server was stopped, it auto-launches
4. Generate images instantly once server is ready

### Manual Control

1. Open Preferences → Add-ons → Style Engine
2. Enable "Use Server API"
3. Click "Start Server" to launch manually
4. Wait for status to show "Running"
5. Click "Test Connection" to verify
6. Click "Stop Server" when done to free resources

## Cost Considerations

### Server Pricing

RunComfy servers consume resources even when idle:
- Charges based on runtime (by the minute)
- Hardware tier affects cost (AMPERE_48 vs higher tiers)

### Best Practices

1. **Stop servers when done**
   - Use "Stop Server" button
   - Prevents unnecessary charges

2. **Monitor server status**
   - Check RunComfy dashboard periodically
   - Ensure old servers are terminated

3. **Serverless vs Server mode**
   - **Serverless**: Pay per generation, no idle costs
   - **Server**: Pay for uptime, faster generation

## Troubleshooting

### "Auto-launch failed: HTTP 401"

**Cause**: Invalid API credentials  
**Solution**: 
1. Verify API Token and User ID in preferences
2. Check credentials in RunComfy dashboard
3. Re-save preferences after updating

### "Server launched but still not responding"

**Cause**: Server is still initializing  
**Solution**:
1. Wait 2-3 more minutes
2. Click "Test Connection" to retry
3. Check server logs in RunComfy dashboard

### "Server created but not yet ready: timeout"

**Cause**: Server launch took > 5 minutes  
**Solution**:
1. Check RunComfy dashboard - server may still be starting
2. Click "Test Connection" after a few minutes
3. If server never starts, click "Stop Server" and try again

### "No active server to stop"

**Cause**: Server was stopped externally  
**Solution**:
1. Clear server URL in preferences
2. Click "Start Server" to launch new instance

## Future Enhancements

Potential improvements for future versions:

1. **Auto-stop after idle**
   - Stop server after X minutes of inactivity
   - Save on RunComfy costs

2. **Server reuse**
   - Detect existing running servers
   - Connect to them instead of launching new

3. **Multi-server support**
   - Launch different servers for different workflows
   - Load balancing for batch operations

4. **Cost tracking**
   - Show estimated server runtime cost
   - Alert when approaching budget limits

5. **Persistent servers**
   - Option to keep server running between Blender sessions
   - Store server ID globally

## Testing Checklist

- [ ] Enable Server API mode
- [ ] Generate image without server configured (triggers auto-launch)
- [ ] Verify server status shows "Launching..."
- [ ] Wait for server ready (console output)
- [ ] Verify server status shows "Running"
- [ ] Verify server URL is populated
- [ ] Generate another image (uses existing server)
- [ ] Click "Test Connection" (should pass)
- [ ] Click "Stop Server"
- [ ] Verify server status shows "Stopped"
- [ ] Verify server URL is cleared
- [ ] Click "Start Server" manually
- [ ] Verify manual launch works same as auto-launch

## References

- `runcomfy_server_manager.py` - Server lifecycle management
- `runcomfy_deployment.py` - Integration with generation flow
- `prefs.py` - UI and operator implementation
- `SERVER_API_FEATURE_2025-11-07.md` - Original Server API documentation

