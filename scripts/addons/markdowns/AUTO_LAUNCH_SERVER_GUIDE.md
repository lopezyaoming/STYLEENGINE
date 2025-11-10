# Automatic Server Launch Guide
## Style Engine - RunComfy Server Auto-Launch Feature

**Date:** 2025-11-07  
**Feature:** Automatic ComfyUI server launching from Blender

---

## Overview

The Style Engine addon now supports **automatic server launching** when using Server API mode. When enabled, the addon will automatically create and start a new ComfyUI server instance on RunComfy if:

1. No server URL is configured
2. An existing server is not responding
3. RunComfy credentials (API token and User ID) are available

This eliminates the need to manually create servers via the RunComfy web interface.

---

## How It Works

### Automatic Launch Scenarios

**Scenario 1: No Server Configured**
- User enables "Use Server API" in preferences
- No server URL is set
- User clicks "Push to Generate"
- → Addon automatically launches a new server

**Scenario 2: Server Not Responding**
- Server URL is configured
- Server is stopped or unavailable
- User clicks "Push to Generate"
- → Addon attempts to auto-launch a new server

**Scenario 3: Manual Launch**
- User clicks "Start New Server" button in preferences
- → Server is created immediately

### Launch Process

```
1. Check server URL configured → No? → Launch new server
2. Attempt connection → Failed? → Launch new server
3. Create server instance via RunComfy API
4. Wait for server to be ready (up to 5 minutes)
5. Update preferences with server URL and ID
6. Continue with generation
```

---

## User Interface

### Preferences Panel (Server API Mode)

When "Use Server API" is enabled, the preferences panel shows:

```
☐ Use Server API
  ├─ ComfyUI Server URL: [________________]
  │  Example: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
  │
  ├─ Server Status (if server exists):
  │  Server Status: Running
  │  Server ID: 2b3d922d-f9b1-4353...
  │
  └─ Action Buttons:
     [▶ Start New Server] [🔌 Test Connection] [⏹ Stop Server]
```

### Button Behavior

| Button | When Visible | Action |
|--------|--------------|--------|
| **Start New Server** | No server OR server stopped/failed | Manually launch a new server |
| **Test Connection** | Always | Validate server connectivity and health |
| **Stop Server** | Server running/starting | Stop the current server instance |

---

## API Endpoints Used

The server manager attempts multiple endpoint patterns to ensure compatibility:

### Server Creation (POST)
```
/prod/v2/servers
/api/servers
/comfyui/{user_id}/servers
```

**Payload:**
```json
{
  "name": "Style Engine ComfyUI Server",
  "hardware": "AMPERE_48",
  "workflow_id": "optional-workflow-id"
}
```

### Server Status (GET)
```
/prod/v2/servers/{server_id}
/api/servers/{server_id}
/comfyui/{user_id}/servers/{server_id}
```

### Server Stop (DELETE)
```
/prod/v2/servers/{server_id}
/api/servers/{server_id}
/comfyui/{user_id}/servers/{server_id}
```

**Note:** If standard endpoints are unavailable, the addon provides clear instructions for manual server management via the RunComfy web interface.

---

## Console Output

### Successful Auto-Launch

```
[Server API] =========================================
[Server API] SERVER CONNECTION VALIDATION
[Server API] =========================================
[Server API] No server URL configured
[Server API] Attempting to auto-launch a new server...

[Server Manager] Auto-launching new ComfyUI server...
[Server Manager]   Hardware: AMPERE_48
[Server Manager]   Name: Style Engine ComfyUI Server (Auto-launched)
[Server Manager]   Trying endpoint: /prod/v2/servers
[Server Manager] ✓ Server created successfully!
[Server Manager]   Server ID: 2b3d922d-f9b1-4353-b189-bc62b0338189
[Server Manager]   Server URL: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
[Server Manager] Waiting for server to be ready (this may take a few minutes)...
[Server Manager]   Check #1: Status = starting
[Server Manager]   Check #2: Status = starting
[Server Manager]   Check #3: Status = running
[Server Manager] ✓ Server is ready!

[Server API] Target server: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
[Server API] Step 1: Testing basic connection...
[Server API] ✓ Basic connection successful
[Server API] Step 2: Checking server health...
[Server API] ✓ Server health check passed
[Server API] =========================================
[Server API] CONNECTION STATUS: ✓ CONNECTED
[Server API] Server URL: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
[Server API] Queue: 0 running, 0 pending
[Server API] Health: ✓ Healthy
[Server API] =========================================
```

### Failed Auto-Launch (API Not Available)

```
[Server Manager] Creating new ComfyUI server instance...
[Server Manager]   Hardware: AMPERE_48
[Server Manager]   Name: Style Engine Server
[Server Manager]   Trying endpoint: /prod/v2/servers
[Server Manager]   Failed: HTTP 404: Not Found
[Server Manager]   Trying endpoint: /api/servers
[Server Manager]   Failed: HTTP 404: Not Found
[Server Manager]   Trying endpoint: /comfyui/{user_id}/servers
[Server Manager]   Failed: HTTP 404: Not Found
[Server Manager] ❌ Failed to create server. Last error: HTTP 404

[Server Manager] Note: RunComfy Server Management API may not be available
[Server Manager] via standard API endpoints. You may need to:
[Server Manager]   1. Create server manually via RunComfy web interface
[Server Manager]   2. Copy the server URL to addon preferences
```

---

## Manual Server Management

If auto-launch is not available, you can manually manage servers:

### Creating a Server Manually

1. Visit https://www.runcomfy.com
2. Navigate to your project
3. Click "Servers" → "Create Server"
4. Select hardware tier (e.g., AMPERE_48)
5. Optionally select a workflow
6. Click "Create"
7. Wait for server to start
8. Copy the server URL (format: `https://{server-id}-comfyui.runcomfy.com`)
9. Paste into "ComfyUI Server URL" in addon preferences
10. Click "Test Connection" to verify

### Stopping a Server Manually

**Via Addon (Recommended):**
- Click "Stop Server" button in preferences

**Via RunComfy Web:**
1. Visit https://www.runcomfy.com
2. Navigate to "Servers"
3. Find your server
4. Click "Stop" or "Delete"

---

## Server Lifecycle

### Server States

| State | Description | Auto-Launch Behavior |
|-------|-------------|---------------------|
| `unknown` | No server configured | Will auto-launch |
| `starting` | Server is booting up | Will wait, not launch new |
| `running` | Server is operational | No action needed |
| `stopped` | Server is stopped | Will auto-launch |
| `failed` | Server failed to start | Will auto-launch |

### Server Startup Time

Typical server startup takes:
- **1-2 minutes:** Basic server initialization
- **3-5 minutes:** Full ComfyUI initialization with models
- **Timeout:** 5 minutes (300 seconds)

If server is not ready within timeout:
- Server is still created and URL is saved
- Status is set to `starting`
- User can retry connection manually

---

## Configuration Options

### Hardware Tiers

Available in preferences → "Hardware Tier":
- `AMPERE_48` (default) - NVIDIA A40/A100 GPUs
- `AMPERE_24` - NVIDIA A10/RTX A5000
- Additional tiers as supported by RunComfy

### Workflow Pre-loading

Optionally set "Workflow ID" in preferences to:
- Pre-load specific custom nodes
- Pre-configure server environment
- Reduce first-run initialization time

---

## Troubleshooting

### Server Not Launching

**Problem:** Auto-launch fails with "credentials not configured"

**Solution:**
- Check "RunComfy API Token" is set in preferences
- Check "User ID" is set in preferences
- Ensure "Test Connection" (serverless) passes

---

**Problem:** Auto-launch fails with HTTP 404 or endpoint errors

**Solution:**
- RunComfy Server Management API may not be available yet
- Use manual server creation (see "Manual Server Management" above)
- Contact RunComfy support for API access

---

**Problem:** Server created but not responding

**Solution:**
- Wait 3-5 minutes for full initialization
- Check server status in RunComfy web dashboard
- Use "Test Connection" button to retry
- Check server logs in RunComfy for errors

---

### Server Connection Issues

**Problem:** `[Errno 11001] getaddrinfo failed`

**Solution:**
- DNS resolution failure
- Verify server URL is correct
- Check if server exists in RunComfy dashboard
- Server may have been deleted - create a new one

---

**Problem:** Server health check warnings

**Solution:**
- Server is booting but not fully ready
- Wait a few minutes and retry
- ComfyUI may still be loading models
- Check `/object_info` endpoint manually

---

### Performance Issues

**Problem:** Slow server creation

**Solution:**
- RunComfy infrastructure may be busy
- Try different hardware tier
- Consider manual creation during off-peak hours

---

**Problem:** Server stops unexpectedly

**Solution:**
- Check RunComfy dashboard for errors
- Verify server limits haven't been exceeded
- Review server logs
- May need to recreate server

---

## Best Practices

### When to Use Auto-Launch

✅ **Good Use Cases:**
- First-time setup
- Quick testing
- Occasional generation tasks
- Development and experimentation

❌ **Not Recommended:**
- Production workflows
- Batch processing (server may restart)
- When you need persistent server state
- If you need custom server configuration

### Server Management Tips

1. **Monitor Server Status:** Use "Test Connection" regularly
2. **Stop When Not Needed:** Save costs by stopping inactive servers
3. **Reuse Servers:** Don't create multiple servers unnecessarily
4. **Check Console:** Always review console output for issues
5. **Manual Fallback:** Be prepared to manage servers manually if API unavailable

### Cost Optimization

- **Stop servers** when not actively generating
- Use **lower hardware tiers** for testing
- Consider **serverless mode** for occasional use
- Use **server mode** for frequent, repeated generations

---

## Implementation Details

### New Files

**`runcomfy_server_manager.py`**
- `RunComfyServerManager` class
- `create_server()` - Create new server instance
- `get_server_status()` - Check server state
- `wait_for_server_ready()` - Poll until ready
- `stop_server()` - Terminate server
- `list_servers()` - Get all user servers

### Modified Files

**`prefs.py`**
- Added `runcomfy_server_id` property
- Added `runcomfy_server_status` property
- Created `WM_OT_StartServer` operator
- Created `WM_OT_StopServer` operator
- Updated UI with server management buttons
- Updated `WM_OT_TestServerConnection` to update status

**`runcomfy_deployment.py`**
- Added `_auto_launch_server()` method
- Modified `_ensure_server_connection()` to check and auto-launch
- Integrated server manager

**`__init__.py`**
- Import `runcomfy_server_manager` module

---

## Future Enhancements

### Potential Features
- [ ] List and select from existing servers
- [ ] Server metrics and monitoring
- [ ] Automatic server scaling
- [ ] Server templates/presets
- [ ] Cost estimation and tracking
- [ ] Server logs viewer in Blender
- [ ] Multi-server load balancing

### API Improvements Needed
- Standardized server management endpoints
- Webhook notifications for server status
- Better error messages from RunComfy API
- Server capability querying

---

## API Compatibility Notes

**Current Implementation:**
- Tries multiple endpoint patterns for compatibility
- Gracefully falls back to manual instructions
- No breaking changes to existing functionality

**RunComfy API Status:**
- Server management endpoints may be in development
- Endpoint patterns based on inference from serverless API
- May require updates as RunComfy API evolves

**Backward Compatibility:**
- Serverless mode unchanged
- Manual server URL entry still works
- Auto-launch is additive, not required

---

## Support

If auto-launch is not working:

1. **Check console output** for detailed error messages
2. **Verify credentials** are correct (test serverless mode)
3. **Try manual server creation** via RunComfy web
4. **Use "Test Connection"** to validate setup
5. **Contact RunComfy support** for API access questions

---

## Summary

The auto-launch feature streamlines Server API usage by:
- ✅ Eliminating manual server creation steps
- ✅ Automatically handling server lifecycle
- ✅ Providing clear status and diagnostics
- ✅ Gracefully falling back when needed
- ✅ Maintaining full backward compatibility

Users can now focus on creative work while the addon handles infrastructure management.

---

**Related Docs:**
- `SERVER_API_FEATURE_2025-11-07.md` - Server API mode overview
- `RUNCOMFY_IMPLEMENTATION_STATUS.md` - RunComfy integration status
- Addon preferences - In-Blender configuration

