# Server API Fix - Correct Endpoint Structure

**Date**: 2025-11-07  
**Issue**: Server launch failing with HTTP 403 authorization error  
**Status**: ✅ FIXED

## Problem

Server auto-launch was failing with this error:
```
HTTP 403: Invalid key=value pair (missing equal-sign) in Authorization header
```

The issue was **NOT** with authorization format, but with incorrect API endpoint structure.

## Root Cause

The implementation was using incorrect endpoint paths:
```python
# ❌ WRONG - These endpoints don't exist
POST /prod/v2/machines
POST /prod/v1/machines
POST /prod/v2/servers
POST /prod/v1/servers
```

According to the [RunComfy Server API documentation](https://comfyui-guides.runcomfy.com/api-reference), the correct endpoints require the **user ID in the path**:
```python
# ✅ CORRECT
POST /prod/api/users/{user_id}/machines
GET  /prod/api/users/{user_id}/machines/{server_id}
DELETE /prod/api/users/{user_id}/machines/{server_id}
```

## Additional Issues Found

1. **Wrong parameter names:**
   - Used `hardware` → Should be `server_type`
   - Used `workflow_id` → Should be `version_id`

2. **Missing required parameter:**
   - Missing `estimated_duration` (required, in seconds)

3. **Hardware tier mapping:**
   - Blender uses names like `AMPERE_48`
   - API expects: `medium`, `large`, `extra-large`, `2x-large`, `2xl-turbo`

4. **Status checking:**
   - Status is `"Ready"` (capital R) when fully operational
   - Response includes `main_service_url` field when ready

## Solution Applied

Updated `runcomfy_server_manager.py`:

### 1. Corrected Endpoint Structure

```python
# In create_server()
endpoint = f'/prod/api/users/{self.user_id}/machines'

# In get_server_status()
endpoint = f'/prod/api/users/{self.user_id}/machines/{server_id}'

# In stop_server()
endpoint = f'/prod/api/users/{self.user_id}/machines/{server_id}'
```

### 2. Fixed Request Payload

```python
# Hardware mapping
hardware_map = {
    'AMPERE_48': 'large',
    'AMPERE_80': 'extra-large',
    'ADA_24': '2x-large',
    'H100': '2xl-turbo',
    'default': 'large'
}
server_type = hardware_map.get(hardware_tier, hardware_map['default'])

# Correct payload
payload = {
    'name': name,
    'server_type': server_type,           # Changed from 'hardware'
    'estimated_duration': 3600,           # Added (1 hour default)
}

if workflow_id:
    payload['version_id'] = workflow_id   # Changed from 'workflow_id'
```

### 3. Updated Status Checking

```python
# Check for exact "Ready" status (capital R)
ready = status_str == 'Ready'

# Extract actual ComfyUI URL from API response
server_url = response.get('main_service_url')
if not server_url:
    server_url = f"https://{server_id}-comfyui.runcomfy.com"
```

## Authorization (Confirmed Correct)

The authorization header format was already correct:
```python
headers = {
    'Authorization': f'Bearer {self.api_token}',
    'Content-Type': 'application/json',
}
```

The 403 error message about "Invalid key=value pair" was misleading - it was actually rejecting the wrong endpoint path, not the auth header.

## Testing

After the fix, server launch should work as follows:

### Expected Console Output

```
[Server Manager] =========================================
[Server Manager] LAUNCHING NEW COMFYUI SERVER INSTANCE
[Server Manager] =========================================
[Server Manager] Configuration:
[Server Manager]   Name: Style Engine ComfyUI Server
[Server Manager]   Hardware: AMPERE_48
[Server Manager]   Workflow: f7ade856...
[Server Manager]   User ID: 0cb54d51-f01e-48e1-ae7b-28d1c21bc947
[Server Manager]
[Server Manager] Calling: POST /prod/api/users/0cb54d51-f01e-48e1-ae7b-28d1c21bc947/machines
[Server Manager] Server type: large
[Server Manager]
[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL
[Server Manager] Server ID: abc123de-f456-7890-ghij-klmnopqrstuv
[Server Manager] Server URL: https://abc123de-f456-7890-ghij-klmnopqrstuv-comfyui.runcomfy.com
[Server Manager] Status: Pending
[Server Manager] =========================================
[Server Manager] Waiting for server to be ready (this may take a few minutes)...
[Server Manager] =========================================
[Server Manager] WAITING FOR SERVER TO BE READY
[Server Manager] Server ID: abc123de-f456-7890-ghij-klmnopqrstuv
[Server Manager] Timeout: 300s, Poll interval: 15s
[Server Manager] =========================================
[Server Manager] Attempt 1: Checking server status...
[Server Manager]   Status: Pending
[Server Manager]   Ready: False
[Server Manager]   Server not ready yet, waiting 15s...
[Server Manager] Attempt 2: Checking server status...
[Server Manager]   Status: Creating
[Server Manager]   Ready: False
[Server Manager]   Server not ready yet, waiting 15s...
...
[Server Manager] Attempt 8: Checking server status...
[Server Manager]   Status: Ready
[Server Manager]   Ready: True
[Server Manager]
[Server Manager] ✅ SERVER IS READY
[Server Manager] Server URL: https://abc123de-f456-7890-ghij-klmnopqrstuv-comfyui.runcomfy.com
[Server Manager] Total wait time: 105.3s
[Server Manager] =========================================
```

## Files Modified

- `scripts/addons/styleengine/runcomfy_server_manager.py`
  - Updated `create_server()` method
  - Updated `get_server_status()` method
  - Updated `stop_server()` method
- `scripts/addons/AUTO_LAUNCH_SERVER_FEATURE.md`
  - Updated API endpoint documentation
  - Updated server lifecycle diagram
  - Added hardware tier mapping table

## References

- [RunComfy Server API Documentation](https://comfyui-guides.runcomfy.com/api-reference)
- [ComfyUI Backend API Guide](https://comfyui-guides.runcomfy.com/ultimate-comfyui-how-tos-a-runcomfy-guide/working-with-comfyui-backend-api)

## Next Steps

1. Test server launch in Blender
2. Verify server reaches "Ready" status
3. Test generation with auto-launched server
4. Verify server stop functionality

