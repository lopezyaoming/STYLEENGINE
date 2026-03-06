import os
import json
import uuid
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
import requests

app = FastAPI()

# --- CONFIGURATION ---
WORKSPACE = Path("/home/Juan/hy3d/Hunyuan3D-Omni")
INPUT_DIR = WORKSPACE / "input_buffer"
OUTPUT_DIR = WORKSPACE / "omni_inference_results"
BRIDGE_URL = "http://localhost:8189/external_status"
VENV_PYTHON = "/home/Juan/hy3d/venv_omni/bin/python"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

jobs = {}

# --- HTML UI TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Style Engine: Omni 3D</title>
    <style>
        body { font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }
        .card { background: #2a2a2a; padding: 20px; border-radius: 8px; max-width: 500px; margin: auto; }
        input, select, button { width: 100%; margin: 10px 0; padding: 10px; border-radius: 4px; border: none; box-sizing: border-box; }
        select { background: #444; color: white; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button { background: #4CAF50; color: white; cursor: pointer; font-weight: bold; }
        #status { color: #aaa; text-align: center; margin-top: 20px; }
        .download-btn { background: #2196F3; display: block; text-align: center; text-decoration: none; padding: 10px; border-radius: 4px; color: white; margin-top: 10px;}
        .section-label { margin-top: 10px; font-size: 0.9em; color: #888; }
        .slider-container { display: flex; align-items: center; gap: 10px; margin: 10px 0; }
        .slider-container input { flex-grow: 1; margin: 0; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Omni 3D Generation</h2>
        <form id="genForm">
            <div class="section-label">1. Reference Image (.png)</div>
            <input type="file" name="image" accept=".png,.jpg,.jpeg" required>
            
            <div class="section-label">2. Control Modality</div>
            <select name="control_type" id="controlType">
                <option value="bbox">Bounding Box</option>
                <option value="voxel">Voxel</option>
                <option value="point" selected>Point Cloud</option>
            </select>

            <div class="section-label">3. Mesh Quality (Density)</div>
            <select name="mc_res">
                <option value="256">Fast (~200k faces)</option>
                <option value="384">Balanced (~600k faces)</option>
                <option value="512" selected>High Detail (~1.5M faces)</option>
            </select>

            <div class="section-label">4. Relaxation Factor (Guidance Scale)</div>
            <div class="slider-container">
                <input type="range" name="guidance_scale" min="1.0" max="10.0" step="0.5" value="4.5" 
                       oninput="this.nextElementSibling.value = this.value">
                <output style="width: 30px; text-align: right;">4.5</output>
            </div>
            <div style="font-size: 0.75em; color: #666; margin-bottom: 10px;">
                Low (1.0-3.0): Smoother, less rigid. High (7.0+): Strict adherence, might be "chewed up".
            </div>

            <div id="bboxInputs" style="display: none;">
                <div class="section-label">Bounding Box Coordinates</div>
                <div class="grid">
                    <input type="text" name="x_min" value="-0.5">
                    <input type="text" name="x_max" value="0.5">
                    <input type="text" name="y_min" value="-0.5">
                    <input type="text" name="y_max" value="0.5">
                    <input type="text" name="z_min" value="-0.5">
                    <input type="text" name="z_max" value="0.5">
                </div>
            </div>

            <div id="fileInputs">
                <div class="section-label">3D Guide File (.obj, .ply)</div>
                <input type="file" name="guide_file" accept=".obj,.ply">
            </div>

            <div class="section-label">5. Inference Flags</div>
            <div style="display:flex; gap:20px; align-items:center; margin: 8px 0;">
                <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
                    <input type="checkbox" name="use_ema" value="true" checked style="width:auto; margin:0;">
                    EMA weights
                </label>
                <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
                    <input type="checkbox" name="flashvdm" value="true" checked style="width:auto; margin:0;">
                    FlashVDM
                </label>
            </div>

            <button type="submit" id="submitBtn">GENERATE MESH</button>
        </form>
        <div id="status">Ready.</div>
        <div id="results"></div>
    </div>

    <script>
        const form = document.getElementById('genForm');
        const controlType = document.getElementById('controlType');
        const bboxInputs = document.getElementById('bboxInputs');
        const fileInputs = document.getElementById('fileInputs');

        controlType.addEventListener('change', (e) => {
            if (e.target.value === 'bbox') {
                bboxInputs.style.display = 'block';
                fileInputs.style.display = 'none';
            } else {
                bboxInputs.style.display = 'none';
                fileInputs.style.display = 'block';
            }
        });

        form.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            document.getElementById('status').innerText = "In Queue...";
            try {
                const res = await fetch('/generate', { method: 'POST', body: formData });
                const { job_id } = await res.json();
                pollStatus(job_id);
            } catch (err) {
                document.getElementById('status').innerText = "Submission Failed.";
            }
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

def run_inference(job_id, input_path, control_type, guide_path, bbox_vals, mc_res, use_ema, flashvdm, guidance_scale):
    jobs[job_id]["status"] = "processing"
    search_start_time = time.time() - 30 
    
    # 1. Conditioning Logic - Injecting mc_res into JSON
    if control_type == "bbox":
        data_json = {"image": [str(input_path)], "bbox": [bbox_vals], "mc_res": mc_res}
        json_path = WORKSPACE / "demos/bbox/data.json"
    elif control_type == "voxel":
        data_json = {"image": [str(input_path)], "voxel": [str(guide_path)], "mc_res": mc_res}
        json_path = WORKSPACE / "demos/voxel/data.json"
    elif control_type == "point":
        data_json = {"image": [str(input_path)], "point": [str(guide_path)], "mc_res": mc_res}
        json_path = WORKSPACE / "demos/point/data.json"
    else:
        jobs[job_id]["status"] = "failed"
        return

    with open(json_path, "w") as f:
        json.dump(data_json, f)

    try:
        requests.post(BRIDGE_URL, json={"status": "processing", "progress": 0.1, "node_name": "Omni: Loading"}, timeout=1)
    except: pass

    try:
        # 2. RUN SUBPROCESS with NEW guidance_scale flag
        cmd = [
            VENV_PYTHON, "inference.py", 
            "--control_type", control_type,
            "--guidance_scale", str(guidance_scale)
        ]
        if use_ema: cmd.append("--use_ema")
        if flashvdm: cmd.append("--flashvdm")
        
        result = subprocess.run(cmd, cwd=str(WORKSPACE), capture_output=True, text=True)
        
        if result.stderr:
            print(f"Subprocess Log: {result.stderr}")

        try:
            requests.post(BRIDGE_URL, json={"status": "processing", "progress": 0.9, "node_name": "Omni: Exporting"}, timeout=1)
        except: pass

        all_glbs = list(WORKSPACE.rglob("*.glb"))
        new_files = [f for f in all_glbs if os.path.getmtime(f) > search_start_time]
        new_files.sort(key=os.path.getmtime, reverse=True)
        
        if new_files:
            target_file = new_files[0]
            final_path = OUTPUT_DIR / f"{job_id}.glb"
            shutil.copy2(str(target_file), str(final_path))
            
            jobs[job_id].update({"output_path": str(final_path), "status": "completed", "progress": 1.0})

            try:
                requests.post(BRIDGE_URL, json={"status": "ready", "progress": 1.0, "node_name": "Omni: Finished"}, timeout=1)
            except: pass
            print(f"SUCCESS: Captured {final_path.name}")
        else:
            jobs[job_id]["status"] = "failed"
            print(f"ERROR: No mesh found.")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        print(f"CRITICAL ERROR: {e}")

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    control_type: str = Form("bbox"),
    mc_res: str = Form("512"),
    guidance_scale: str = Form("4.5"), # New Form Field
    guide_file: Optional[UploadFile] = File(None),
    x_min: str = Form("-0.5"), x_max: str = Form("0.5"),
    y_min: str = Form("-0.5"), y_max: str = Form("0.5"),
    z_min: str = Form("-0.5"), z_max: str = Form("0.5"),
    use_ema: str = Form("false"),
    flashvdm: str = Form("false"),
):
    job_id = str(uuid.uuid4())
    input_path = INPUT_DIR / f"{job_id}.png"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    guide_path = None
    if control_type in ["voxel", "point"] and guide_file:
        guide_path = INPUT_DIR / f"{job_id}_{guide_file.filename}"
        with open(guide_path, "wb") as buffer:
            shutil.copyfileobj(guide_file.file, buffer)

    bbox_vals = [float(x_min), float(y_min), float(z_min), float(x_max), float(y_max), float(z_max)]
    jobs[job_id] = {"status": "queued", "progress": 0.0, "output_path": None}

    background_tasks.add_task(
        run_inference,
        job_id, input_path, control_type, guide_path, bbox_vals, int(mc_res),
        use_ema=(use_ema.lower() == "true"),
        flashvdm=(flashvdm.lower() == "true"),
        guidance_scale=float(guidance_scale) # Pass as float
    )
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