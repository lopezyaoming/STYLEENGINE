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
from runcomfy_test import get_tester

# Global state for auto-generation monitoring
_auto_gen_task = None
_last_depth_mtime = 0
_active_workflow = "SDXLworkflow.json"  # Default workflow
_generation_in_progress = False
_last_generation_complete_time = 0


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


def get_available_workflows(project_root: Path) -> list:
    """Scan workflows directory and return list of available workflow files."""
    workflows_dir = project_root / "ComfyUI" / "workflows"
    
    if not workflows_dir.exists():
        return []
    
    # Get all .json files in workflows directory
    workflows = [f.name for f in workflows_dir.glob("*.json")]
    workflows.sort()  # Sort alphabetically
    
    return workflows


def inject_workflow_data(workflow: dict, session_data: dict) -> dict:
    """
    Inject dynamic data into workflow based on session.json.
    Handles different workflow structures intelligently.
    """
    global_prompt = session_data.get("global_prompt", "")
    width = session_data.get("resolution", {}).get("width", 1024)
    height = session_data.get("resolution", {}).get("height", 1024)
    depth_influence = session_data.get("depth_influence", 1.0)
    silhouette_influence = session_data.get("silhouette_influence", 1.0)
    steps = session_data.get("steps", 15)
    
    # Node 15: LoadImage - Set combined pass
    if "15" in workflow and "inputs" in workflow["15"]:
        workflow["15"]["inputs"]["image"] = "combined0001.png"
    
    # Node 25: PrimitiveString - Set prompt
    if "25" in workflow and "inputs" in workflow["25"]:
        workflow["25"]["inputs"]["value"] = global_prompt
    
    # Node 5: EmptyLatentImage - Set resolution
    if "5" in workflow and "inputs" in workflow["5"]:
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
    
    # Node 9: SaveImage - Set output prefix
    if "9" in workflow and "inputs" in workflow["9"]:
        workflow["9"]["inputs"]["filename_prefix"] = "style_engine_output"
    
    # Node 40: PrimitiveFloat (cannyStrength) - Set silhouette influence
    if "40" in workflow and "inputs" in workflow["40"]:
        workflow["40"]["inputs"]["value"] = silhouette_influence
    
    # Node 41: PrimitiveFloat (depthStrength) - Set depth influence
    if "41" in workflow and "inputs" in workflow["41"]:
        workflow["41"]["inputs"]["value"] = depth_influence
    
    # Node 42: PrimitiveInt (Steps) - Set steps
    if "42" in workflow and "inputs" in workflow["42"]:
        workflow["42"]["inputs"]["value"] = steps
    
    return workflow


async def send_workflow_internal(project_root: Path, depth_image_path: Path, session_data: dict, comfy_root: Path, comfy_input_dir: Path, comfy_output_dir: Path, current_ai_path: Path):
    """
    Internal function to send workflow to ComfyUI (used by both manual and auto-trigger).
    Returns (success: bool, prompt_id: str, message: str)
    """
    global _active_workflow, _generation_in_progress
    workflow_path = project_root / "ComfyUI" / "workflows" / _active_workflow
    
    try:
        # Step 1: Copy combined pass to ComfyUI input folder
        comfy_combined_path = comfy_input_dir / "combined0001.png"
        shutil.copy2(depth_image_path, comfy_combined_path)
        
        # Step 2: Read the workflow
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        # Step 3: Inject dynamic data into workflow
        workflow = inject_workflow_data(workflow, session_data)
        
        # Step 4: Generate unique client ID and prepare payload
        client_id = str(uuid.uuid4())
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
                
                # Mark generation as in progress
                _generation_in_progress = True
                
                # Start monitoring in background
                asyncio.create_task(wait_for_comfy_completion(prompt_id, comfy_output_dir, current_ai_path))
                
                print(f"[Style Engine] 🎨 Workflow sent to ComfyUI (ID: {prompt_id})")
                print(f"[Style Engine] 🔒 Generation in progress, blocking new renders...")
                return True, prompt_id, "Success"
            else:
                return False, None, f"ComfyUI returned status {response.status_code}"
                
    except httpx.ConnectError:
        return False, None, "Cannot connect to ComfyUI"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


async def monitor_depth_changes():
    """
    Background task that monitors combined0001.png for changes.
    When it changes and auto_generate is enabled, automatically trigger ComfyUI workflow.
    """
    global _last_depth_mtime
    
    project_root = Path(__file__).parent.parent
    session_path = project_root / "data" / "temp" / "session.json"
    depth_image_path = project_root / "data" / "temp" / "passes" / "combined0001.png"
    current_ai_path = project_root / "data" / "temp" / "ai_vision" / "current_ai.png"
    
    print("[Style Engine] 🔄 Auto-generation monitor started")
    
    while True:
        try:
            # Check if session.json exists and auto_generate is enabled
            if not session_path.exists():
                await asyncio.sleep(5)
                continue
            
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            
            auto_generate = session_data.get("flags", {}).get("auto_generate", False)
            
            if not auto_generate:
                # Auto-generate is disabled, just wait
                await asyncio.sleep(5)
                continue
            
            # Check if generation is already in progress
            if _generation_in_progress:
                # Don't send new workflow if previous one is still processing
                await asyncio.sleep(3)
                continue
            
            # Check if depth image exists and has been updated
            if not depth_image_path.exists():
                await asyncio.sleep(5)
                continue
            
            current_mtime = depth_image_path.stat().st_mtime
            
            # If this is the first check or file has changed
            if _last_depth_mtime == 0:
                _last_depth_mtime = current_mtime
                await asyncio.sleep(5)
                continue
            
            if current_mtime > _last_depth_mtime:
                # Depth pass has been updated!
                _last_depth_mtime = current_mtime
                
                print(f"[Style Engine] 🆕 New combined pass detected!")
                print(f"[Style Engine] 🚀 Auto-triggering ComfyUI workflow...")
                
                # Get ComfyUI paths from session
                comfy_root, comfy_input_dir, comfy_output_dir = get_comfy_paths_from_session(session_data)
                
                if comfy_root and comfy_root.exists():
                    # Send the workflow
                    success, prompt_id, message = await send_workflow_internal(
                        project_root,
                        depth_image_path,
                        session_data,
                        comfy_root,
                        comfy_input_dir,
                        comfy_output_dir,
                        current_ai_path
                    )
                    
                    if success:
                        print(f"[Style Engine] ✅ Auto-workflow sent (Prompt ID: {prompt_id})")
                    else:
                        print(f"[Style Engine] ❌ Auto-workflow failed: {message}")
                else:
                    print(f"[Style Engine] ⚠️ ComfyUI path not configured, skipping auto-generation")
            
            # Wait before next check
            await asyncio.sleep(3)  # Check every 3 seconds
            
        except Exception as e:
            print(f"[Style Engine] Error in auto-generation monitor: {e}")
            await asyncio.sleep(5)


async def wait_for_comfy_completion(prompt_id: str, comfy_output_dir: Path, current_ai_path: Path, max_wait: int = 120):
    """
    Wait for ComfyUI to complete processing and automatically copy output to current_ai.png.
    Sets _generation_in_progress flag to coordinate with render timing.
    
    Args:
        prompt_id: The ComfyUI prompt ID to monitor
        comfy_output_dir: Path to ComfyUI's output folder
        current_ai_path: Path to current_ai.png destination
        max_wait: Maximum seconds to wait (default 120)
    """
    global _generation_in_progress, _last_generation_complete_time
    
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
                                
                                # Mark generation as complete
                                _generation_in_progress = False
                                _last_generation_complete_time = time.time()
                                print(f"[Style Engine] ✅ Generation complete, ready for next render")
                                
                                return True
                            else:
                                print(f"[Style Engine] ⚠️ Job complete but no output files found")
                                _generation_in_progress = False
                                return False
                    
                except Exception as e:
                    print(f"[Style Engine] Error checking ComfyUI status: {e}")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
            
            print(f"[Style Engine] ⏱️ Timeout waiting for ComfyUI (max {max_wait}s)")
            _generation_in_progress = False
            return False
            
    except Exception as e:
        print(f"[Style Engine] Error in wait_for_comfy_completion: {e}")
        _generation_in_progress = False
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


@app.get("/runcomfy", response_class=HTMLResponse)
async def runcomfy_test_ui():
    """Serve the RunComfy test UI."""
    html_path = Path(__file__).parent / "templates" / "runcomfy_test.html"
    
    if not html_path.exists():
        return HTMLResponse(
            content="<h1>RunComfy Test UI not found</h1><p>Please ensure templates/runcomfy_test.html exists.</p>",
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
    global _auto_gen_task
    print("\n[Style Engine] Server started successfully!")
    print("[Style Engine] Dashboard: http://localhost:8000")
    print("[Style Engine] API Docs: http://localhost:8000/docs")
    print("[Style Engine] Monitoring session.json for updates...")
    
    # Start auto-generation monitor
    _auto_gen_task = asyncio.create_task(monitor_depth_changes())
    print("[Style Engine] Auto-generation monitor initialized")


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


@app.get("/auto_generate/status")
async def get_auto_generate_status():
    """Get the status of auto-generation feature."""
    project_root = Path(__file__).parent.parent
    session_path = project_root / "data" / "temp" / "session.json"
    depth_path = project_root / "data" / "temp" / "passes" / "combined0001.png"
    
    status = {
        "monitor_running": _auto_gen_task is not None and not _auto_gen_task.done(),
        "auto_generate_enabled": False,
        "last_depth_mtime": _last_depth_mtime,
        "depth_exists": depth_path.exists(),
        "session_exists": session_path.exists(),
        "generation_in_progress": _generation_in_progress,
        "ready_for_render": not _generation_in_progress
    }
    
    if session_path.exists():
        try:
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            status["auto_generate_enabled"] = session_data.get("flags", {}).get("auto_generate", False)
        except:
            pass
    
    return status


@app.get("/render/ready")
async def check_render_ready():
    """Check if it's safe to render (no generation in progress)."""
    return {
        "ready": not _generation_in_progress,
        "generation_in_progress": _generation_in_progress,
        "last_complete_time": _last_generation_complete_time,
        "seconds_since_complete": time.time() - _last_generation_complete_time if _last_generation_complete_time > 0 else None
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


@app.get("/workflows")
async def get_workflows():
    """Get list of available workflow files."""
    project_root = Path(__file__).parent.parent
    workflows = get_available_workflows(project_root)
    
    return {
        "workflows": workflows,
        "active": _active_workflow,
        "count": len(workflows)
    }


@app.get("/workflows/active")
async def get_active_workflow():
    """Get the currently active workflow."""
    return {
        "active_workflow": _active_workflow
    }


@app.post("/workflows/set/{workflow_name}")
async def set_active_workflow(workflow_name: str):
    """Set the active workflow."""
    global _active_workflow
    
    project_root = Path(__file__).parent.parent
    available_workflows = get_available_workflows(project_root)
    
    if workflow_name not in available_workflows:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found. Available: {', '.join(available_workflows)}"
        )
    
    _active_workflow = workflow_name
    print(f"[Style Engine] 🔄 Switched to workflow: {workflow_name}")
    
    return {
        "status": "success",
        "active_workflow": _active_workflow,
        "message": f"Switched to {workflow_name}"
    }


# ============================================
# RUNCOMFY CLOUD API ENDPOINTS (TEST)
# ============================================

@app.post("/runcomfy/create_deployment")
async def runcomfy_create_deployment():
    """Create a new RunComfy deployment"""
    # Read credentials from session.json
    project_root = Path(__file__).parent.parent
    session_path = project_root / "data" / "temp" / "session.json"
    
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="Session file not found. Please set up workspace in Blender first.")
    
    with open(session_path, "r") as f:
        session_data = json.load(f)
    
    # Get API credentials (assuming they're in the session or we need to read from preferences)
    # For now, we'll expect them to be passed or configured
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found. Please set RUNCOMFY_API_TOKEN and RUNCOMFY_USER_ID environment variables.")
    
    tester = get_tester(api_token, user_id)
    result = await tester.create_deployment(name="StyleEngine_Cloud_Test")
    
    if result["success"]:
        # Send an initial warm-up request
        deployment_id = result["deployment_id"]
        print(f"[RunComfy] ✅ Deployment created: {deployment_id}")
        print(f"[RunComfy] 🔄 Sending warm-up request to load models...")
        
        # Send a test workflow to warm up the instance
        warm_up_result = await tester.send_workflow(
            deployment_id=deployment_id,
            prompt="A test image to warm up the deployment",
            width=1024,
            height=1024,
            steps=15
        )
        
        return {
            "success": True,
            "deployment": result,
            "warmup_request": warm_up_result
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@app.get("/runcomfy/deployments")
async def runcomfy_list_deployments():
    """List all RunComfy deployments"""
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found")
    
    tester = get_tester(api_token, user_id)
    result = await tester.list_deployments()
    
    if result["success"]:
        return result["deployments"]
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@app.delete("/runcomfy/deployment/{deployment_id}")
async def runcomfy_delete_deployment(deployment_id: str):
    """Delete a RunComfy deployment"""
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found")
    
    tester = get_tester(api_token, user_id)
    result = await tester.delete_deployment(deployment_id)
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@app.post("/runcomfy/send_workflow")
async def runcomfy_send_workflow(
    deployment_id: str,
    prompt: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    depth_strength: Optional[float] = None,
    canny_strength: Optional[float] = None,
    steps: Optional[int] = None
):
    """Send a workflow to RunComfy deployment"""
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found")
    
    # Read from session.json if parameters not provided
    project_root = Path(__file__).parent.parent
    session_path = project_root / "data" / "temp" / "session.json"
    
    if session_path.exists():
        with open(session_path, "r") as f:
            session_data = json.load(f)
        
        if prompt is None:
            prompt = session_data.get("global_prompt", "A beautiful landscape")
        if width is None:
            width = session_data.get("resolution", {}).get("width", 1024)
        if height is None:
            height = session_data.get("resolution", {}).get("height", 1024)
        if depth_strength is None:
            depth_strength = session_data.get("depth_influence", 1.0)
        if canny_strength is None:
            canny_strength = session_data.get("silhouette_influence", 1.0)
        if steps is None:
            steps = session_data.get("steps", 15)
    
    tester = get_tester(api_token, user_id)
    result = await tester.send_workflow(
        deployment_id=deployment_id,
        prompt=prompt or "A beautiful landscape",
        width=width or 1024,
        height=height or 1024,
        depth_strength=depth_strength or 1.0,
        canny_strength=canny_strength or 1.0,
        steps=steps or 15
    )
    
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@app.get("/runcomfy/status/{deployment_id}/{request_id}")
async def runcomfy_check_status(deployment_id: str, request_id: str):
    """Check status of a RunComfy request"""
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found")
    
    tester = get_tester(api_token, user_id)
    result = await tester.check_status(deployment_id, request_id)
    
    if result["success"]:
        return result["data"]
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


@app.get("/runcomfy/result/{deployment_id}/{request_id}")
async def runcomfy_get_result(deployment_id: str, request_id: str):
    """Get result of a completed RunComfy request"""
    api_token = os.environ.get("RUNCOMFY_API_TOKEN")
    user_id = os.environ.get("RUNCOMFY_USER_ID")
    
    if not api_token or not user_id:
        raise HTTPException(status_code=401, detail="RunComfy API credentials not found")
    
    tester = get_tester(api_token, user_id)
    result = await tester.get_result(deployment_id, request_id)
    
    if result["success"]:
        return result["data"]
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))


# ============================================
# DEBUG ENDPOINTS
# ============================================

@app.post("/debug/send_workflow")
async def debug_send_workflow(background_tasks: BackgroundTasks):
    """
    Send workflow to ComfyUI with dynamic data from session.json and render passes.
    Automatically monitors completion and copies output to current_ai.png.
    
    Workflow:
    1. Read session.json for prompt, resolution, and ComfyUI path
    2. Copy combined0001.png to ComfyUI input folder
    3. Inject dynamic data into workflow (DepthLCM with DepthAnything preprocessor)
    4. Send to ComfyUI
    5. Monitor for output and copy to current_ai.png (background task)
    """
    project_root = Path(__file__).parent.parent
    workflow_path = project_root / "ComfyUI" / "workflows" / "DepthLCM.json"
    session_path = project_root / "data" / "temp" / "session.json"
    depth_image_path = project_root / "data" / "temp" / "passes" / "combined0001.png"
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
            detail=f"Combined pass not found at {depth_image_path}. Make sure 'Refresh Viewport' is enabled in Blender."
        )
    
    # Use the internal function to send workflow
    success, prompt_id, message = await send_workflow_internal(
        project_root,
        depth_image_path,
        session_data,
        comfy_root,
        comfy_input_dir,
        comfy_output_dir,
        current_ai_path
    )
    
    if success:
        # Extract data for response
        global_prompt = session_data.get("global_prompt", "")
        width = session_data.get("resolution", {}).get("width", 1024)
        height = session_data.get("resolution", {}).get("height", 1024)
        depth_influence = session_data.get("depth_influence", 1.0)
        silhouette_influence = session_data.get("silhouette_influence", 1.0)
        steps = session_data.get("steps", 15)
        
        return {
            "status": "success",
            "message": "Workflow sent! Monitoring for completion...",
            "prompt_id": prompt_id,
            "monitoring": True,
            "injected_data": {
                "workflow": _active_workflow,
                "prompt": global_prompt,
                "resolution": f"{width}x{height}",
                "combined_pass": "combined0001.png (copied to ComfyUI input)",
                "depth_influence": depth_influence,
                "silhouette_influence": silhouette_influence,
                "steps": steps,
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
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send workflow: {message}"
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

