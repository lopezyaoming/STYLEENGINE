# Hunyuan3D-Part: Calling the Gradio Service via HTTP

The Gradio service exposes a standard HTTP API you can call from any language or tool — no browser required.

---

## Base URL

```
http://styleengine2:7860
```

---

## How Gradio's API Works

Every Gradio app auto-generates a REST API at `/api/predict`. Each component in the UI maps to a positional entry in the `data` array. File inputs are handled via a two-step process: **upload first, then predict**.

---

## Step 1 — Upload Your Mesh

```http
POST /upload
Content-Type: multipart/form-data
```

```bash
curl -X POST http://styleengine2:7860/upload \
  -F "files=@/path/to/your/mesh.obj" \
  | python3 -m json.tool
```

**Response:**
```json
["/tmp/gradio/abc123/mesh.obj"]
```

Save that path — you'll pass it as the file reference in the next step.

---

## Step 2 — Run the Pipeline

```http
POST /api/predict
Content-Type: application/json
```

```bash
curl -X POST http://styleengine2:7860/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {"path": "/tmp/gradio/abc123/mesh.obj", "orig_name": "mesh.obj"},
      50000,
      128,
      16,
      42
    ]
  }'
```

### `data` Array Layout

| Index | Parameter | Type | Default | Notes |
|-------|-----------|------|---------|-------|
| 0 | mesh file | object | — | `{"path": "...", "orig_name": "..."}` from upload |
| 1 | `point_num` | int | 50000 | P3-SAM surface samples. Max safe: 50000 on 40GB |
| 2 | `prompt_num` | int | 128 | P3-SAM query points. Max safe: 128 on 40GB |
| 3 | `prompt_bs` | int | 16 | P3-SAM batch size |
| 4 | `seed` | int | 42 | XPart reconstruction seed |

---

## Step 3 — Download the Output GLBs

The response contains file paths for each output:

```json
{
  "data": [
    {"path": "/tmp/gradio/xyz/assembled.glb", "orig_name": "assembled.glb"},
    {"path": "/tmp/gradio/xyz/exploded.glb",  "orig_name": "exploded.glb"},
    {"path": "/tmp/gradio/xyz/bbox.glb",       "orig_name": "bbox.glb"},
    "✅ Done! 3 parts reconstructed. Run ID: `a1b2c3d4`"
  ],
  "duration": 47.3
}
```

Download each file:

```bash
curl http://styleengine2:7860/file=/tmp/gradio/xyz/assembled.glb \
  -o assembled.glb
```

---

## Full Python Example

```python
import requests
import os

BASE = "http://styleengine2:7860"

def run_pipeline(mesh_path, point_num=50000, prompt_num=128, prompt_bs=16, seed=42):
    # 1. Upload
    with open(mesh_path, "rb") as f:
        upload_resp = requests.post(
            f"{BASE}/upload",
            files={"files": (os.path.basename(mesh_path), f)},
        )
    upload_resp.raise_for_status()
    remote_path = upload_resp.json()[0]

    # 2. Predict
    predict_resp = requests.post(
        f"{BASE}/api/predict",
        json={
            "data": [
                {"path": remote_path, "orig_name": os.path.basename(mesh_path)},
                point_num,
                prompt_num,
                prompt_bs,
                seed,
            ]
        },
        timeout=300,  # pipeline can take 2–5 min
    )
    predict_resp.raise_for_status()
    results = predict_resp.json()["data"]

    # 3. Download outputs
    output_files = {}
    labels = ["assembled", "exploded", "bbox"]
    for label, item in zip(labels, results[:3]):
        if item is None:
            continue
        file_path = item["path"] if isinstance(item, dict) else None
        if not file_path:
            continue
        dl = requests.get(f"{BASE}/file={file_path}")
        out_name = f"{label}.glb"
        with open(out_name, "wb") as f:
            f.write(dl.content)
        output_files[label] = out_name
        print(f"Saved {out_name}")

    print(results[3])  # status message
    return output_files


if __name__ == "__main__":
    run_pipeline("my_mesh.obj")
```

---

## Mesh Format Recommendations

### ✅ Best Formats to Upload

| Format | Why |
|--------|-----|
| `.obj` | Geometry only, no embedded textures, tiny file size |
| `.ply` | Compact binary format, no texture overhead |
| `.stl` | Geometry only, universally supported |

### ⚠️ Avoid `.glb` / `.gltf` with Textures

`.glb` files with PBR textures can be **10–100× larger** than the raw geometry warrants. The pipeline only uses vertex positions and face connectivity — textures are completely ignored during processing and just waste upload time.

**Quick size comparison for a typical column mesh:**

| Format | Size | Upload time (100Mbps LAN) |
|--------|------|--------------------------|
| `.glb` with 4K textures | ~45MB | ~4s |
| `.obj` geometry only | ~2MB | ~0.2s |
| `.ply` binary | ~1.5MB | ~0.15s |

### How to Strip Textures Before Uploading

**In Blender:**
1. Select your object
2. `File → Export → Wavefront (.obj)`
3. Uncheck *Material Groups* and *Write Materials*
4. Export — geometry only, no `.mtl` file

**Via Python (trimesh):**
```python
import trimesh
mesh = trimesh.load("textured.glb", force="mesh")
# trimesh.load with force="mesh" discards all texture/material data
mesh.export("clean.obj")
```

**Via Python (command line):**
```bash
python3 -c "
import trimesh, sys
mesh = trimesh.load(sys.argv[1], force='mesh')
mesh.export(sys.argv[2])
" input.glb output.obj
```

---

## Checking the API Schema

Gradio auto-documents its API. Visit in your browser:

```
http://styleengine2:7860/?view=api
```

Or fetch programmatically:

```bash
curl http://styleengine2:7860/info | python3 -m json.tool
```

---

## Timeouts

The pipeline is slow — budget generously:

| Stage | Typical Time |
|-------|-------------|
| P3-SAM segmentation | 10–30s |
| XPart model load | 20–40s (first run) |
| XPart reconstruction | 60–180s |
| **Total** | **~2–5 min** |

Set your HTTP client timeout to at least **300 seconds**.

