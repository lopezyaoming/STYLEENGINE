# Authorization Format Auto-Detection Update

**Date**: 2025-11-07  
**Issue**: HTTP 403 "missing equal-sign" error persists with correct endpoint  
**Solution**: Multi-format authorization fallback system

## Problem

Even after fixing the API endpoint structure to `/prod/api/users/{user_id}/machines`, the server launch still fails with:
```
HTTP 403: Invalid key=value pair (missing equal-sign) in Authorization header
```

This suggests the Machines API may use a **different authorization format** than the standard Serverless API.

## Solution Implemented

Updated `runcomfy_server_manager.py` to **automatically try multiple authorization formats** until one succeeds:

### Authorization Formats Tried (in order):

1. **Bearer Token** (standard):
   ```
   Authorization: Bearer {api_token}
   ```

2. **API Key format** (key=value):
   ```
   Authorization: api_key={api_token}
   ```

3. **Custom Headers**:
   ```
   X-API-Key: {api_token}
   X-User-ID: {user_id}
   ```

### How It Works

```python
auth_formats = [
    ('Bearer Token', {'Authorization': f'Bearer {self.api_token}'}),
    ('API Key', {'Authorization': f'api_key={self.api_token}'}),
    ('X-API-Key', {'X-API-Key': self.api_token, 'X-User-ID': self.user_id}),
]

for auth_name, auth_headers in auth_formats:
    try:
        # Attempt request with this auth format
        response = make_request(auth_headers)
        
        # If successful, log which format worked
        print(f"[Server Manager] ✓ Auth successful with: {auth_name}")
        return response
        
    except HTTP403Error:
        # Try next format
        print(f"[Server Manager] Auth format '{auth_name}' failed, trying next...")
        continue
```

## Expected Console Output

When testing the updated addon, you'll see:

### If First Format Works:
```
[Server Manager] Calling: POST /prod/api/users/.../machines
[Server Manager] Server type: large
[Server Manager] ✓ Auth successful with: Bearer Token
[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL
```

### If Fallback Needed:
```
[Server Manager] Calling: POST /prod/api/users/.../machines
[Server Manager] Server type: large
[Server Manager] Auth format 'Bearer Token' failed, trying next...
[Server Manager] ✓ Auth successful with: API Key
[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL
```

### If All Formats Fail:
```
[Server Manager] Auth format 'Bearer Token' failed, trying next...
[Server Manager] Auth format 'API Key' failed, trying next...
[Server Manager] Auth format 'X-API-Key' failed, trying next...
[Server Manager] ❌ SERVER LAUNCH FAILED
[Server Manager] Error: All authorization formats failed
```

## Testing Instructions

1. **Uninstall** old version completely
2. **Restart Blender**
3. **Install** updated `styleengine.zip`
4. Configure credentials
5. Enable "Use Server API"
6. Click "Start Server"
7. **Watch console** to see which auth format works

## What This Tells Us

The console output will reveal which authorization format the RunComfy Machines API actually expects. This is important because:

- The official docs say use `Bearer {token}`
- But the error suggests it wants `key=value` format
- Or possibly custom headers entirely

Once we know which format works, we can optimize the code to use that format directly.

## Fallback Strategy Benefits

1. **Automatic discovery** - No need to guess the correct format
2. **Future-proof** - Works if API changes auth format
3. **Debugging** - Clear console logs show what's happening
4. **Compatibility** - Handles edge cases and API variations

## Files Modified

- `scripts/addons/styleengine/runcomfy_server_manager.py`
  - Updated `_request()` method with multi-format fallback
  - Added debug logging for auth success
  - Handles 403 errors gracefully with retry

## Next Steps

After testing:

1. Note which auth format succeeds in console
2. Report back with console output
3. Optimize code to use correct format directly
4. Update documentation with correct format

## Potential Outcomes

### Outcome 1: Bearer Token Works
- Standard format is correct
- Something else was wrong (network, credentials, etc.)

### Outcome 2: API Key Format Works
- Machines API uses different format than Serverless API
- We'll update code to use `api_key={token}` for machines endpoints

### Outcome 3: Custom Headers Work
- API expects headers like `X-API-Key` and `X-User-ID`
- We'll document this as the correct format

### Outcome 4: All Fail
- Credentials are invalid
- Or there's another issue (rate limiting, account status, etc.)
- Need to check RunComfy dashboard and account

---

**Package Updated**: `scripts/addons/styleengine.zip`  
**Ready for Testing**: Yes  
**Please report console output** so we can determine the correct auth format!

