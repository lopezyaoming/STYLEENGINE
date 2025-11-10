# Testing Guide - Auto-Launch Server Feature

**Date**: 2025-11-07  
**Package**: `styleengine.zip`  
**Status**: Ready for testing

## Quick Start

### 1. Install/Update Addon

1. Open Blender 4.2+
2. Go to Edit → Preferences → Add-ons
3. If you have Style Engine installed:
   - Disable it
   - Remove it completely
   - **Restart Blender** (important!)
4. Click "Install from Disk"
5. Select `scripts/addons/styleengine.zip`
6. Enable "Style Engine"

### 2. Configure Credentials

1. In Preferences → Add-ons → Style Engine
2. Enter your RunComfy credentials:
   - **API Token** (from RunComfy profile)
   - **User ID** (from RunComfy dashboard URL)
   - **Workflow ID** (your workflow, e.g., `f7ade856-4ab5-4e14-8d4f-e5c6d7e8f9a0`)

### 3. Enable Server API Mode

1. Scroll to "Server API Mode" section
2. Check: **"Use Server API (instead of Serverless)"**
3. Leave Server URL blank (for auto-launch)

### 4. Test Auto-Launch

1. Open HeavyPoly workspace (or create your own)
2. Click **"Push to Generate"** button
3. Watch console for server launch progress:
   ```
   [Server Manager] LAUNCHING NEW COMFYUI SERVER INSTANCE
   [Server Manager] Configuration:
   [Server Manager]   Name: Style Engine ComfyUI Server (Auto-launched)
   [Server Manager]   Hardware: AMPERE_48
   [Server Manager]   User ID: YOUR-USER-ID
   [Server Manager]
   [Server Manager] Calling: POST /prod/api/users/.../machines
   [Server Manager] Server type: large
   ```
4. Wait 2-5 minutes for "✅ SERVER IS READY"
5. Image generation should proceed automatically
6. Check preferences - Server URL should be populated

### 5. Test Manual Controls

Back in Preferences → Style Engine:

1. **Test Connection** - Should show "✅ Server is healthy"
2. Generate another image - Should use existing server (instant)
3. **Stop Server** - Should clear URL and status
4. **Start Server** - Should launch new server manually

## Expected Console Output

### Successful Auto-Launch

```
[Server Manager] =========================================
[Server Manager] LAUNCHING NEW COMFYUI SERVER INSTANCE
[Server Manager] =========================================
[Server Manager] Configuration:
[Server Manager]   Name: Style Engine ComfyUI Server (Auto-launched)
[Server Manager]   Hardware: AMPERE_48
[Server Manager]   User ID: 0cb54d51-f01e-48e1-ae7b-28d1c21bc947
[Server Manager]
[Server Manager] Calling: POST /prod/api/users/0cb54d51-f01e-48e1-ae7b-28d1c21bc947/machines
[Server Manager] Server type: large
[Server Manager]
[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL
[Server Manager] Server ID: 2b3d922d-f9b1-4353-b189-bc62b0338189
[Server Manager] Server URL: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
[Server Manager] Status: Pending
[Server Manager] =========================================
[Server Manager] Waiting for server to be ready (this may take a few minutes)...
[Server Manager] =========================================
[Server Manager] WAITING FOR SERVER TO BE READY
[Server Manager] Server ID: 2b3d922d-f9b1-4353-b189...
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
[Server Manager] Attempt 3: Checking server status...
[Server Manager]   Status: Ready
[Server Manager]   Ready: True
[Server Manager]
[Server Manager] ✅ SERVER IS READY
[Server Manager] Server URL: https://2b3d922d-f9b1-4353-b189-bc62b0338189-comfyui.runcomfy.com
[Server Manager] Total wait time: 32.1s
[Server Manager] =========================================
```

## Troubleshooting

### "HTTP 403" Error
- Check your API Token and User ID are correct
- Verify you copied them from RunComfy profile (not workflow page)
- Try regenerating API token

### "Server created but not yet ready: timeout"
- Server is still starting (can take 5+ minutes sometimes)
- Wait a few more minutes
- Click "Test Connection" to check status
- Check RunComfy dashboard for server status

### "No module named 'runcomfy_server_manager'"
- You have an old version installed
- **Fully uninstall** the addon
- **Restart Blender**
- Reinstall fresh `styleengine.zip`

### Server URL Not Populated
- Check console for error messages
- Verify credentials are correct
- Try manual launch with "Start Server" button
- Check RunComfy dashboard for account issues

### Image Not Generating After Server Ready
- Check console for error messages
- Verify workflow ID is correct
- Test with "Test Connection" button
- Try stopping and restarting server

## What to Report

If you encounter issues, please provide:

1. **Console output** (all of it, copy from Blender console window)
2. **Blender version** (Help → About Blender)
3. **Operating system** (Windows/macOS/Linux)
4. **Steps to reproduce**
5. **Screenshot of preferences** (with credentials hidden)
6. **RunComfy dashboard status** (what does it show?)

## Success Indicators

✅ Server launches without errors  
✅ Status shows progression: Pending → Creating → Ready  
✅ Server URL auto-populates in preferences  
✅ Test Connection passes  
✅ Image generates successfully  
✅ Console shows "✅ SERVER IS READY"  
✅ Preferences show "Running ✓" status  

## Clean Up After Testing

**Important**: Don't forget to stop your server to avoid charges!

1. In Preferences → Style Engine
2. Click **"Stop Server"**
3. Or go to [RunComfy Dashboard](https://www.runcomfy.com/comfyui-api/machines)
4. Manually stop any running machines

## Next Tests

After basic functionality works:

1. Test serverless mode still works (disable "Use Server API")
2. Test switching between modes
3. Test stopping and restarting servers
4. Test with different workflows
5. Test with different hardware tiers
6. Test error recovery (invalid credentials, network issues, etc.)

## Documentation References

- **Feature Overview**: `AUTO_LAUNCH_SERVER_FEATURE.md`
- **API Fix Details**: `SERVER_API_FIX_2025-11-07.md`
- **Implementation Summary**: `IMPLEMENTATION_COMPLETE_2025-11-07.md`
- **RunComfy API Docs**: https://comfyui-guides.runcomfy.com/api-reference

---

**Happy Testing!** 🚀

If everything works, you now have a fully automated ComfyUI server management system integrated directly into Blender!

