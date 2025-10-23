"""
Style Engine FastAPI Server
Handles communication between Blender addon and ComfyUI.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from pathlib import Path
from datetime import datetime
import httpx
import uuid
import shutil
import os
import asyncio
import time


# Initialize FastAPI app
app = FastAPI(
    title="Style Engine Bridge",
    description="API server for communicating between Blender and ComfyUI",
    version="0.1.0"
)

# ComfyUI Configuration
COMFY_URL = "http://127.0.0.1:8188"
COMFY_API_PROMPT = f"{COMFY_URL}/prompt"
COMFY_API_QUEUE = f"{COMFY_URL}/queue"
COMFY_API_HISTORY = f"{COMFY_URL}/history"

def get_comfy_paths_from_session(session_data: dict) -> tuple:
    """
    Get ComfyUI paths from session.json.
    Returns (comfy_root, input_dir, output_dir)
    """
    # Get ComfyUI path from session JSON
    comfy_path_str = session_data.get("routing", {}).get("comfy_path", "")
    
    if not comfy_path_str:
        return None, None, None
    
    comfy_path = Path(comfy_path_str)
    input_dir = comfy_path / "input"
    output_dir = comfy_path / "output"
    
    return comfy_path, input_dir, output_dir


async def wait_for_comfy_completion(prompt_id: str, comfy_output_dir: Path, current_ai_path: Path, max_wait: int = 120):
    """
    Wait for ComfyUI to complete processing and automatically copy output to current_ai.png.
    
    Args:
        prompt_id: The ComfyUI prompt ID to monitor
        comfy_output_dir: Path to ComfyUI's output folder
        current_ai_path: Path to current_ai.png destination
        max_wait: Maximum seconds to wait (default 120)
    """
    print(f"[Style Engine] Monitoring ComfyUI job: {prompt_id}")
    start_time = time.time()
    check_interval = 2  # Check every 2 seconds
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            while time.time() - start_time < max_wait:
                try:
                    # Check ComfyUI history API
                    response = await client.get(f"{COMFY_API_HISTORY}/{prompt_id}")
                    
                    if response.status_code == 200:
                        history = response.json()
                        
                        # Check if our prompt is in the history (means it's complete)
                        if prompt_id in history:
                            print(f"[Style Engine] ✅ ComfyUI job complete!")
                            
                            # Find the newest file in output folder with our prefix
                            output_files = list(comfy_output_dir.glob("style_engine_output_*.png"))
                            
                            if output_files:
                                # Sort by modification time, get newest
                                newest_file = max(output_files, key=lambda p: p.stat().st_mtime)
                                
                                # Copy to current_ai.png
                                shutil.copy2(newest_file, current_ai_path)
                                print(f"[Style Engine] 📸 Copied output to current_ai.png")
                                print(f"   Source: {newest_file}")
                                print(f"   Dest: {current_ai_path}")
                                
                                return True
                            else:
                                print(f"[Style Engine] ⚠️ Job complete but no output files found")
                                return False
                    
                except Exception as e:
                    print(f"[Style Engine] Error checking ComfyUI status: {e}")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
            
            print(f"[Style Engine] ⏱️ Timeout waiting for ComfyUI (max {max_wait}s)")
            return False
            
    except Exception as e:
        print(f"[Style Engine] Error in wait_for_comfy_completion: {e}")
        return False

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Data Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str


class SessionStatus(BaseModel):
    """Session status information."""
    session_id: str
    active: bool
    last_update: Optional[str] = None


# ============================================================================
# UI Dashboard
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the web dashboard UI."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    
    if not html_path.exists():
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Please ensure templates/index.html exists.</p>",
            status_code=404
        )
    
    with open(html_path, 'r', encoding='utf-8') as f:
        return HTMLResponse(content=f.read())


@app.get("/api", response_model=Dict[str, str])
async def api_info():
    """API information endpoint."""
    return {
        "message": "Style Engine Bridge API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "dashboard": "/"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns server status and basic info.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version="0.1.0"
    )


@app.get("/session", response_model=Dict[str, Any])
async def get_session():
    """
    Get current session data from session.json.
    This reads the JSON file that Blender writes.
    """
    # Path to session.json (adjust if needed)
    session_path = Path(__file__).parent.parent / "data" / "temp" / "session.json"
    
    if not session_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Session file not found. Please set up workspace in Blender first."
        )
    
    try:
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        return session_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading session file: {str(e)}"
        )


@app.get("/session/status", response_model=SessionStatus)
async def get_session_status():
    """
    Get session status (lightweight check).
    """
    session_path = Path(__file__).parent.parent / "data" / "temp" / "session.json"
    
    if not session_path.exists():
        return SessionStatus(
            session_id="none",
            active=False,
            last_update=None
        )
    
    try:
        with open(session_path, 'r') as f:
            session_data = json.load(f)
        
        return SessionStatus(
            session_id=session_data.get("session_id", "unknown"),
            active=True,
            last_update=session_data.get("timestamp")
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading session: {str(e)}"
        )


@app.post("/comfy/generate")
async def trigger_comfy_generation(payload: Optional[Dict[str, Any]] = None):
    """
    Trigger ComfyUI generation.
    Placeholder endpoint - will be implemented later.
    """
    return {
        "status": "placeholder",
        "message": "ComfyUI integration coming soon",
        "received_payload": payload
    }


@app.get("/comfy/status")
async def check_comfy_status():
    """
    Check if ComfyUI is reachable.
    Tests connection to ComfyUI server.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to get the queue status from ComfyUI
            response = await client.get(COMFY_API_QUEUE)
            
            if response.status_code == 200:
                queue_data = response.json()
                return {
                    "status": "online",
                    "message": "ComfyUI is reachable",
                    "comfy_reachable": True,
                    "comfy_url": COMFY_URL,
                    "queue_running": len(queue_data.get("queue_running", [])),
                    "queue_pending": len(queue_data.get("queue_pending", []))
                }
            else:
                return {
                    "status": "error",
                    "message": f"ComfyUI returned status {response.status_code}",
                    "comfy_reachable": False,
                    "comfy_url": COMFY_URL
                }
    except httpx.ConnectError:
        return {
            "status": "offline",
            "message": "Cannot connect to ComfyUI. Is it running?",
            "comfy_reachable": False,
            "comfy_url": COMFY_URL
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking ComfyUI: {str(e)}",
            "comfy_reachable": False,
            "comfy_url": COMFY_URL
        }


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on server startup."""
    print("\n[Style Engine] Server started successfully!")
    print("[Style Engine] Dashboard: http://localhost:8000")
    print("[Style Engine] API Docs: http://localhost:8000/docs")
    print("[Style Engine] Monitoring session.json for updates...")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on server shutdown."""
    print("\n[Style Engine] Server shutting down...")


# ============================================================================
# Development/Debug Endpoints
# ============================================================================

@app.get("/debug/paths")
async def debug_paths():
    """
    Debug endpoint to check file paths.
    Useful for troubleshooting.
    """
    launcher_dir = Path(__file__).parent
    project_root = launcher_dir.parent
    session_path = project_root / "data" / "temp" / "session.json"
    workflow_path = project_root / "ComfyUI" / "workflows" / "BasicLCM.json"
    
    return {
        "launcher_dir": str(launcher_dir),
        "project_root": str(project_root),
        "session_path": str(session_path),
        "session_exists": session_path.exists(),
        "workflow_path": str(workflow_path),
        "workflow_exists": workflow_path.exists()
    }


@app.get("/debug/current_ai_status")
async def get_current_ai_status():
    """Check if current_ai.png exists and when it was last modified."""
    project_root = Path(__file__).parent.parent
    current_ai_path = project_root / "data" / "temp" / "ai_vision" / "current_ai.png"
    
    if current_ai_path.exists():
        stat = current_ai_path.stat()
        return {
            "exists": True,
            "path": str(current_ai_path),
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "age_seconds": time.time() - stat.st_mtime
        }
    else:
        return {
            "exists": False,
            "path": str(current_ai_path)
        }


@app.post("/debug/send_workflow")
async def debug_send_workflow(background_tasks: BackgroundTasks):
    """
    Send workflow to ComfyUI with dynamic data from session.json and render passes.
    Automatically monitors completion and copies output to current_ai.png.
    
    Workflow:
    1. Read session.json for prompt, resolution, and ComfyUI path
    2. Copy depth0001.png to ComfyUI input folder
    3. Inject dynamic data into workflow
    4. Send to ComfyUI
    5. Monitor for output and copy to current_ai.png (background task)
    """
    project_root = Path(__file__).parent.parent
    workflow_path = project_root / "ComfyUI" / "workflows" / "BasicLCM.json"
    session_path = project_root / "data" / "temp" / "session.json"
    depth_image_path = project_root / "data" / "temp" / "passes" / "depth0001.png"
    current_ai_path = project_root / "data" / "temp" / "ai_vision" / "current_ai.png"
    
    # Check if required files exist
    if not workflow_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Workflow file not found at {workflow_path}"
        )
    
    if not session_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Session file not found. Please set up workspace in Blender first."
        )
    
    # Read session to get ComfyUI path
    try:
        with open(session_path, 'r') as f:
            session_data = json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading session file: {str(e)}"
        )
    
    # Get ComfyUI paths from session
    comfy_root, comfy_input_dir, comfy_output_dir = get_comfy_paths_from_session(session_data)
    
    if not comfy_root or not comfy_input_dir:
        raise HTTPException(
            status_code=404,
            detail="ComfyUI path not set in Blender preferences. Please go to Edit → Preferences → Add-ons → Style Engine and set your ComfyUI installation path."
        )
    
    if not comfy_root.exists():
        raise HTTPException(
            status_code=404,
            detail=f"ComfyUI folder not found at {comfy_root}. Please check the path in Blender preferences."
        )
    
    if not comfy_input_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"ComfyUI input folder not found at {comfy_input_dir}. Please verify your ComfyUI installation."
        )
    
    if not depth_image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Depth pass not found at {depth_image_path}. Make sure 'Refresh Viewport' is enabled in Blender."
        )
    
    try:
        # Step 1: Copy depth image to ComfyUI input folder
        comfy_depth_path = comfy_input_dir / "depth0001.png"
        shutil.copy2(depth_image_path, comfy_depth_path)
        
        # Step 2: Read the workflow (session_data already loaded above)
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        # Step 3: Extract data from session
        global_prompt = session_data.get("global_prompt", "")
        width = session_data.get("resolution", {}).get("width", 1024)
        height = session_data.get("resolution", {}).get("height", 1024)
        
        # Step 4: Modify workflow nodes with dynamic data
        
        # Node 15: LoadImage - Set depth image
        if "15" in workflow:
            workflow["15"]["inputs"]["image"] = "depth0001.png"
        
        # Node 25: PrimitiveString - Set prompt from session
        if "25" in workflow:
            workflow["25"]["inputs"]["value"] = global_prompt
        
        # Node 5: EmptyLatentImage - Set resolution from session
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height
        
        # Node 9: SaveImage - Set output to a predictable filename
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = "style_engine_output"
        
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        
        # Prepare payload
        payload = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        # Step 5: Send to ComfyUI
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(COMFY_API_PROMPT, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                prompt_id = result.get("prompt_id")
                
                # Add background task to monitor completion and auto-copy output
                background_tasks.add_task(
                    wait_for_comfy_completion,
                    prompt_id,
                    comfy_output_dir,
                    current_ai_path
                )
                
                return {
                    "status": "success",
                    "message": "Workflow sent! Monitoring for completion...",
                    "comfy_response": result,
                    "prompt_id": prompt_id,
                    "client_id": client_id,
                    "monitoring": True,
                    "injected_data": {
                        "prompt": global_prompt,
                        "resolution": f"{width}x{height}",
                        "depth_image": "depth0001.png (copied to ComfyUI input)",
                        "comfy_path": str(comfy_root),
                        "output": "Will auto-copy to current_ai.png when ready ✨"
                    },
                    "next_steps": [
                        "1. ComfyUI is processing your workflow...",
                        f"2. Server is monitoring: {comfy_output_dir}",
                        "3. Output will automatically copy to current_ai.png",
                        "4. Blender will auto-refresh the viewport",
                        "5. Check the server console for progress updates"
                    ]
                }
            else:
                return {
                    "status": "error",
                    "message": f"ComfyUI returned status {response.status_code}",
                    "response_text": response.text
                }
                
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to ComfyUI. Make sure it's running at http://127.0.0.1:8188"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error sending workflow: {str(e)}"
        )


@app.get("/debug/comfy_queue")
async def debug_comfy_queue():
    """
    Debug endpoint to check ComfyUI queue status.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(COMFY_API_QUEUE)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "queue_data": response.json()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Status code: {response.status_code}",
                    "response": response.text
                }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error checking queue: {str(e)}"
        )

