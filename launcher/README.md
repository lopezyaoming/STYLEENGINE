# Style Engine Launcher

FastAPI server that bridges communication between Blender's Style Engine addon and ComfyUI.

## Quick Start

### 1. Install Dependencies

```bash
# Navigate to the launcher directory
cd launcher

# Install required packages
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### 3. Open the Dashboard

Open your browser and go to:
- **Dashboard (Web UI)**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative docs**: http://localhost:8000/redoc

## Dashboard Features

The web dashboard provides a real-time view of:
- 📋 **Session Info** - Current session ID, status, resolution
- 🎨 **ComfyUI Status** - Connection status (coming soon)
- 💚 **Server Health** - Version, uptime, server status
- 🎯 **Object Groups** - All defined groups with keywords
- 📄 **Full Session Data** - Live JSON view
- 📝 **Activity Log** - Recent API calls and events

**Auto-refresh**: Updates every 2 seconds (toggle on/off)

## Available Endpoints

### Core Endpoints

- `GET /` - Web dashboard UI
- `GET /api` - API information
- `GET /health` - Server health check
- `GET /session` - Get current Blender session data
- `GET /session/status` - Quick session status check

### ComfyUI Integration (Coming Soon)

- `POST /comfy/generate` - Trigger ComfyUI generation
- `GET /comfy/status` - Check ComfyUI connection

### Debug & Testing

- `GET /debug/paths` - View file paths for troubleshooting
- `POST /debug/send_workflow` - Send DepthLCM.json workflow to ComfyUI (auto-copies output! ✨)
- `GET /debug/comfy_queue` - Check ComfyUI queue status
- `GET /debug/current_ai_status` - Check current_ai.png modification time and size

## How It Works

1. **Blender** (Style Engine addon) writes `session.json` with scene data and render passes
2. **This Server** reads `session.json` and exposes it via API
3. **This Server** sends requests to ComfyUI with dynamic data (prompt, depth, resolution)
4. **ComfyUI** generates images and saves to its output folder
5. **This Server** monitors ComfyUI and automatically copies output to `current_ai.png`
6. **Blender** auto-refreshes the viewport and displays the new AI-generated image

### Auto-Copy Feature ✨

When you send a workflow via `/debug/send_workflow`:
- The server immediately returns a response (non-blocking)
- A background task monitors ComfyUI's completion
- Once the image is ready, it's automatically copied to `current_ai.png`
- Blender's viewport refresh picks it up automatically
- Check the server console for real-time progress updates

## File Structure

```
launcher/
├── main.py              # Entry point - starts the server
├── server.py            # FastAPI application and endpoints
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Development

The server runs with auto-reload enabled during development. Any changes to `server.py` will automatically restart the server.

## Cyclical Auto-Generation ✨

The server now features **fully automated, cyclical AI generation**!

When enabled in Blender:
1. Blender renders passes every 5 seconds (Combined, Depth, AO)
2. Server detects combined pass updates
3. Auto-triggers ComfyUI workflow (Default: SDXLworkflow with dual ControlNet)
4. Auto-copies output to current_ai.png
5. Blender refreshes viewport
6. Repeat continuously!

**Default Workflow**: SDXLworkflow.json (high quality with depth + canny ControlNet)

**See**: [`AUTO_GENERATION_GUIDE.md`](AUTO_GENERATION_GUIDE.md) for complete setup and usage instructions.

---

## Next Steps

Completed:
- [x] ComfyUI API integration (send workflows)
- [x] Auto-copy output to current_ai.png
- [x] Background task monitoring
- [x] Dynamic data injection from session.json
- [x] **Cyclical auto-generation** (depth pass monitoring)
- [x] Auto-trigger workflows on render updates

Future functionality to be added:
- [ ] WebSocket support for real-time updates
- [ ] Image processing queue for multiple requests
- [ ] Enhanced error handling and retry logic
- [ ] Advanced logging system
- [ ] Adaptive timing based on ComfyUI speed

