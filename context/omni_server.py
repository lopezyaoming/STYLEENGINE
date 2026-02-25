import os
import json
import uuid
import shutil
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
import requests

app = FastAPI()

# --- CONFIGURATION ---
WORKSPACE = Path("/home/Juan/hy3d/Hunyuan3D-Omni")
INPUT_DIR = WORKSPACE / "input_buffer"
OUTPUT_DIR = WORKSPACE / "omni_inference_results/3domni_bbox"
BRIDGE_URL = "http://localhost:8189/external_status"
VENV_PYTHON = "/home/Juan/hy3d/venv_omni/bin/python"

# Ensure directories exist
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory job tracking
jobs = {}

# --- HTML UI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Style Engine: Omni 3D</title>
    <style>
        body { font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }
        .card { background: #2a2a2a; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto; }
        input, button { width: 100%; margin: 10px 0; padding: 10px; border-radius: 4px; border: none; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button { background: #4CAF50; color: white; cursor: pointer; font-weight: bold; }
        #status { color: #aaa; text-align: center; margin-top: 20px; }
        .download-btn { background: #2196F3; display: none; text-align: center; text-decoration: none; display:block; padding: 10px; border-radius: 4px; color: white; margin-top: 10px;}
    </style>
</head>
<body>
    <div class="card">
        <h2>Omni 3D Generation</h2>
        <form id="genForm">
            <input type="file" name="image" required>
            <div class="grid">
                <input type="text" name="x_min" value="-0.5" placeholder="X Min">
                <input type="text" name="x_max" value="0.5" placeholder="X Max">
                <input type="text" name="y_min" value="-0.5" placeholder="Y Min">
                <input type="text" name="y_max" value="0.5" placeholder="Y Max">
                <input type="text" name="z_min" value="-0.5" placeholder="Z Min">
                <input type="text" name="z_max" value="0.5" placeholder="Z Max">
            </div>
            <button type="submit" id="submitBtn">GENERATE MESH</button>
        </form>
        <div id="status">Ready.</div>
        <div id="results"></div>
    </div>

    <script>
        const form = document.getElementById('genForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            document.getElementById('status').innerText = "Uploading...";
            const res = await fetch('/generate', { method: 'POST', body: formData });
            const { job_id } = await res.json();
            pollStatus(job_id);
        };

        async function pollStatus(job_id) {
            const res = await fetch(`/status/${job_id}`);
            const data = await res.json();
            document.getElementById('status').innerText = `Status: ${data.status} (${Math.round(data.progress * 100)}%)`;
            
            if (data.status === 'completed') {
                document.getElementById('results').innerHTML = `<a href="/download/${job_id}" class="download-btn">DOWNLOAD .GLB</a>`;
            } else if (data.status !== 'failed') {
                setTimeout(() => pollStatus(job_id), 2000);
            }
        }
    </script>
</body>
</html>
"""

import time

def run_inference(job_id, input_path, bbox_vals):
    jobs[job_id]["status"] = "processing"
    start_time = time.time()
    
    data_json = {
        "image": [str(input_path)],
        "bbox": [bbox_vals]
    }
    
    json_path = WORKSPACE / "demos/bbox/data.json"
    with open(json_path, "w") as f:
        json.dump(data_json, f)

    # --- GAP 1 FIX: Signal START ---
    try:
        requests.post(BRIDGE_URL, json={"status": "processing", "progress": 0.1, "node_name": "Omni: Loading"}, timeout=1)
    except: pass

    try:
        # THE CORE COMMAND (Run this only once)
        cmd = [VENV_PYTHON, "inference.py", "--control_type", "bbox"]
        subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
        
        # --- GAP 1 FIX: Signal EXPORTING (Inference is done) ---
        try:
            requests.post(BRIDGE_URL, json={"status": "processing", "progress": 0.9, "node_name": "Omni: Exporting"}, timeout=1)
        except: pass

        # Now, search for the file...
        search_root = WORKSPACE / "omni_inference_results"
        all_glbs = list(search_root.rglob("*.glb"))
        
        new_files = [f for f in all_glbs if os.path.getmtime(f) > start_time]
        new_files.sort(key=os.path.getmtime, reverse=True)
        
        if new_files:
            target_file = new_files[0]
            final_path = target_file.parent / f"{job_id}.glb"
            os.rename(target_file, final_path)
            
            jobs[job_id]["output_path"] = str(final_path)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 1.0

            # --- GAP 1 FIX: Signal READY ---
            try:
                requests.post(BRIDGE_URL, json={"status": "ready", "progress": 1.0, "node_name": "Omni: Finished"}, timeout=1)
            except: pass
            
            print(f"Caught the new mesh: {final_path.name}")
        else:
            jobs[job_id]["status"] = "failed"
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        print(f"Subprocess Error: {e}")

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    x_min: str = Form("-0.5"), x_max: str = Form("0.5"),
    y_min: str = Form("-0.5"), y_max: str = Form("0.5"),
    z_min: str = Form("-0.5"), z_max: str = Form("0.5")
):
    job_id = str(uuid.uuid4())
    input_path = INPUT_DIR / f"{job_id}.png"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    bbox_vals = [float(x_min), float(y_min), float(z_min), float(x_max), float(y_max), float(z_max)]
    jobs[job_id] = {"status": "queued", "progress": 0.0, "output_path": None}
    
    background_tasks.add_task(run_inference, job_id, input_path, bbox_vals)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"status": "not_found", "progress": 0})

@app.get("/download/{job_id}")
async def download(job_id: str):
    job = jobs.get(job_id)
    if job and job["output_path"]:
        return FileResponse(job["output_path"], filename=f"StyleEngine_{job_id[:4]}.glb")
    return {"error": "Not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8190)
