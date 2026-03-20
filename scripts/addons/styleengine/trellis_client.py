# ================================================================
#    Style Engine - TRELLIS2 HTTP Client
#    Pure-stdlib (urllib) client for the TRELLIS2 generation service.
#    Host: same server as ComfyUI, port 8195.
#    API: multipart/form-data for submit; JSON for status/download.
# ================================================================

import json
import urllib.request
import urllib.error
from pathlib import Path

TRELLIS_PORT = 8195
_BOUNDARY = "----BlenderTRELLIS2"


# ----------------------------------------------------------------
# URL helper (mirrors _get_omni_url pattern)
# ----------------------------------------------------------------

def get_trellis_url():
    """Return the TRELLIS2 base URL derived from addon preferences.
    Reuses gcs_server_url host, port 8195."""
    from urllib.parse import urlparse
    try:
        import bpy
        prefs = bpy.context.preferences.addons['styleengine'].preferences
        base_url = prefs.gcs_server_url
        if not base_url:
            return None
        parsed = urlparse(base_url)
        host = parsed.hostname or parsed.path.split('/')[0].split(':')[0]
        scheme = parsed.scheme if parsed.scheme else 'http'
        return f"{scheme}://{host}:{TRELLIS_PORT}"
    except Exception:
        return None


# ----------------------------------------------------------------
# Low-level multipart builder
# ----------------------------------------------------------------

def _field(name, value):
    """Encode a plain text form field."""
    return (
        f"--{_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode()


def _file_field(name, filename, data, content_type="application/octet-stream"):
    """Encode a binary file form field."""
    header = (
        f"--{_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode()
    return header + data + b"\r\n"


def _build_body(*parts):
    """Concatenate multipart parts and close the boundary."""
    body = b"".join(parts)
    body += f"--{_BOUNDARY}--\r\n".encode()
    return body


# ----------------------------------------------------------------
# Public API functions
# ----------------------------------------------------------------

def health(base_url):
    """GET /health — check pipeline readiness and VRAM.
    Returns dict: {pipeline_loaded, tex_pipeline_loaded, queue_depth,
                   vram_used_gb, vram_total_gb, ...}
    Raises urllib.error.URLError on network failure."""
    url = f"{base_url}/health"
    req = urllib.request.Request(url, headers={"User-Agent": "StyleEngine-Blender/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def submit_generate(base_url, image_path,
                    pipeline_type="1024_cascade",
                    seed=42,
                    steps=12,
                    guidance=7.5,
                    num_samples=1,
                    max_num_tokens=49152,
                    texture_size=4096,
                    decimation_target=1000000,
                    remesh=True,
                    remesh_band=1.0,
                    remesh_project=0.0):
    """POST /generate — submit an image-to-3D job.
    image_path: local path to RGBA PNG (background already removed).
    Returns job_id string."""
    with open(image_path, "rb") as f:
        img_data = f.read()

    body = _build_body(
        _file_field("image", "input.png", img_data, "image/png"),
        _field("pipeline_type", pipeline_type),
        _field("seed", seed),
        _field("steps", steps),
        _field("guidance", guidance),
        _field("num_samples", num_samples),
        _field("max_num_tokens", max_num_tokens),
        _field("texture_size", texture_size),
        _field("decimation_target", decimation_target),
        _field("remesh", "true" if remesh else "false"),
        _field("remesh_band", remesh_band),
        _field("remesh_project", remesh_project),
    )

    req = urllib.request.Request(
        f"{base_url}/generate",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={_BOUNDARY}",
            "User-Agent": "StyleEngine-Blender/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
    return result["job_id"]


def submit_retexture(base_url, image_path, mesh_path,
                     seed=0,
                     tex_resolution=1024,
                     texture_size=2048,
                     tex_steps=12,
                     tex_guidance=1.0,
                     tex_guidance_rescale=0.0,
                     tex_rescale_t=3.0):
    """POST /retexture — retexture an existing mesh with a reference image.
    image_path: reference RGBA PNG.
    mesh_path:  local path to .glb / .ply / .obj / .gltf.
    Returns job_id string."""
    with open(image_path, "rb") as f:
        img_data = f.read()
    with open(mesh_path, "rb") as f:
        mesh_data = f.read()

    mesh_filename = Path(mesh_path).name
    body = _build_body(
        _file_field("image", "reference.png", img_data, "image/png"),
        _file_field("mesh", mesh_filename, mesh_data, "model/gltf-binary"),
        _field("seed", seed),
        _field("tex_resolution", tex_resolution),
        _field("texture_size", texture_size),
        _field("tex_steps", tex_steps),
        _field("tex_guidance", tex_guidance),
        _field("tex_guidance_rescale", tex_guidance_rescale),
        _field("tex_rescale_t", tex_rescale_t),
    )

    req = urllib.request.Request(
        f"{base_url}/retexture",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={_BOUNDARY}",
            "User-Agent": "StyleEngine-Blender/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
    return result["job_id"]


def poll_status(base_url, job_id):
    """GET /status/{job_id}.
    Returns dict: {status, progress, message, gen_time, num_outputs, error, ...}
    status one of: 'queued' | 'processing' | 'done' | 'failed'"""
    url = f"{base_url}/status/{job_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "StyleEngine-Blender/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def download_glb(base_url, job_id, output_path, index=0):
    """GET /download/{job_id}/{index} — save binary GLB to output_path."""
    url = f"{base_url}/download/{job_id}/{index}"
    req = urllib.request.Request(url, headers={"User-Agent": "StyleEngine-Blender/1.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return len(data)
