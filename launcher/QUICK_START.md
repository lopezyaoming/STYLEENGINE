# Style Engine Launcher - Quick Start Guide

## Prerequisites

✅ **Python 3.8+** installed on your system  
✅ **Blender** with Style Engine addon installed  
✅ **Internet connection** (for installing dependencies)

## Step-by-Step Setup

### 1️⃣ Install Python

If you don't have Python installed:

**Windows:**
1. Download from [python.org](https://www.python.org/downloads/)
2. Run installer
3. ✅ **CHECK** "Add Python to PATH" during installation
4. Click "Install Now"

**Verify installation:**
```powershell
python --version
```

### 2️⃣ Install Dependencies

Open PowerShell and navigate to the launcher folder:

```powershell
cd C:\Coding\STYLEENGINE\launcher
```

Install required packages:

```powershell
pip install -r requirements.txt
```

You should see output like:
```
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 ...
```

### 3️⃣ Start the Server

```powershell
python main.py
```

You should see:
```
============================================================
Style Engine - AI Generation Bridge Server
============================================================

[INFO] Starting server on http://localhost:8000
[INFO] API documentation available at http://localhost:8000/docs
[INFO] Press CTRL+C to stop the server

[Style Engine] Server started successfully!
[Style Engine] Dashboard: http://localhost:8000
[Style Engine] API Docs: http://localhost:8000/docs
```

### 4️⃣ Open the Dashboard

Open your web browser and go to:

**http://localhost:8000**

You should see the Style Engine Bridge Dashboard! 🎉

### 5️⃣ Test with Blender

1. Open Blender
2. Enable the Style Engine addon
3. Open the Style Engine panel (press `N` in 3D view)
4. Click **"Setup Workspace"**
5. Watch the dashboard update in real-time! ⚡

## What You'll See in the Dashboard

### 📋 Session Info Card
- **Session ID**: Your current session identifier
- **Status**: Active/Inactive based on refresh setting
- **Last Update**: Timestamp of last session.json update
- **Resolution**: Current AI generation resolution

### 🎨 ComfyUI Status Card
- Connection status (coming soon)
- Queue information (coming soon)
- Manual generation trigger

### 💚 Server Health Card
- Server version
- Uptime counter
- Link to API documentation

### 🎯 Object Groups
- Lists all groups you've created in Blender
- Shows keywords for each group
- Displays pass index and object count

### 📄 Full Session Data
- Live view of the entire session.json file
- Updates automatically every 2 seconds
- Color-coded JSON syntax

### 📝 Activity Log
- Recent API calls
- Server events
- Error messages

## Testing the Dashboard

### Test 1: Check Server Health
1. Click the **"Refresh"** button in the Server Health card
2. You should see version "0.1.0"
3. Watch the uptime counter increment

### Test 2: View Session Data
1. In Blender, make sure you've clicked "Setup Workspace"
2. On the dashboard, click **"Refresh"** in Session Info
3. You should see your session ID and resolution
4. The "Full Session Data" section should show valid JSON

### Test 3: Create Groups in Blender
1. In Blender, go to the "Image Generation" section
2. Click **"Add Group"**, name it "Buildings"
3. Add keywords like "tall, modern, glass"
4. Watch the dashboard update automatically!
5. The Object Groups section should show your new group

### Test 4: Auto-Refresh
1. Toggle the "Auto-refresh" switch OFF
2. Notice the dashboard stops updating
3. Toggle it back ON
4. Dashboard resumes updating every 2 seconds

## Troubleshooting

### ❌ "Command 'python' not found"

**Solution**: Python is not in your PATH.
- Reinstall Python with "Add to PATH" checked
- Or use `py` instead: `py main.py`

### ❌ "No module named 'fastapi'"

**Solution**: Dependencies not installed.
```powershell
pip install -r requirements.txt
```

### ❌ "Session file not found"

**Solution**: You haven't set up the workspace in Blender yet.
1. Open Blender
2. Open Style Engine panel
3. Click "Setup Workspace"

### ❌ Dashboard shows "No session data"

**Solution**: Check the session.json path.
1. Visit http://localhost:8000/debug/paths
2. Verify "session_exists" is `true`
3. Check that the path matches your project location

### ❌ Port 8000 already in use

**Solution**: Another application is using port 8000.
- Stop the other application
- Or edit `main.py` to use a different port (e.g., 8001)

## Next Steps

Now that your server is running:

1. ✅ **Create a Session** in Blender
2. ✅ **Add Object Groups** with keywords
3. ✅ **Watch the Dashboard** update in real-time
4. 🔄 **Next**: Integrate ComfyUI for actual AI generation
5. 🔄 **Next**: Add file watching for automatic triggers
6. 🔄 **Next**: WebSocket support for instant updates

## Keyboard Shortcuts

- **CTRL+C** in PowerShell terminal - Stop the server
- **CTRL+R** in browser - Manually refresh dashboard
- **F12** in browser - Open developer console for debugging

## API Exploration

Want to explore the API programmatically?

Visit: **http://localhost:8000/docs**

This gives you:
- Interactive API documentation
- Try out endpoints directly in the browser
- See request/response formats
- Copy code snippets for integration

## Development Mode

The server runs with **auto-reload** enabled. This means:
- Edit `server.py` → Server restarts automatically
- Edit `templates/index.html` → Refresh browser to see changes
- No need to manually restart the server!

## Support

If you encounter issues:
1. Check the PowerShell console for error messages
2. Check the browser console (F12) for JavaScript errors
3. Visit `/debug/paths` to verify file locations
4. Check that Blender has written `session.json`

---

**Ready to build AI-powered 3D workflows!** 🚀

