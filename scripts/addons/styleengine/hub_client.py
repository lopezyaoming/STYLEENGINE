"""
Minimal HTTP client for the Style Engine Hub (port 8000).
Uses only urllib.request — no third-party dependencies.
"""
import hashlib
import json
import urllib.request
import urllib.error
import urllib.parse

HUB_DEFAULT = "http://style-engine:8000"


def sha256_file(path: str) -> str:
    """Return the hex SHA-256 digest of a file's bytes."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _post(url: str, payload: dict, timeout: int = 4) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "StyleEngine-Blender/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _get(url: str, timeout: int = 4) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": "StyleEngine-Blender/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def register_session(hub_url: str, session_id: str, blend_name: str,
                     blend_path: str, current_ai_path: str) -> bool:
    """Register this Blender instance with the hub. Returns True on success."""
    try:
        _post(f"{hub_url}/api/blender/register", {
            "session_id":      session_id,
            "blend_name":      blend_name,
            "blend_path":      blend_path,
            "current_ai_path": current_ai_path,
        })
        return True
    except Exception as e:
        print(f"[Hub Client] Register failed: {e}")
        return False


def peek_result(hub_url: str, session_id: str) -> dict:
    """
    Poll for a pending result.
    Returns {"exists": bool, "has_result": bool, "result_ts": float|None}.
    On network error returns {"exists": False, "has_result": False, "result_ts": None}.
    """
    try:
        return _get(f"{hub_url}/api/blender/{session_id}/peek")
    except Exception:
        return {"exists": False, "has_result": False, "result_ts": None}


def ack_result(hub_url: str, session_id: str) -> None:
    """Acknowledge a delivered result. Silently swallows errors."""
    try:
        _post(f"{hub_url}/api/blender/{session_id}/ack", {})
    except Exception as e:
        print(f"[Hub Client] Ack failed: {e}")


def push_result_image(hub_url: str, session_id: str, image_path: str,
                      timeout: int = 30) -> dict:
    """
    Upload a Blender-generated image to the hub so the web UI stays in sync.

    Sends a raw PNG body to POST /api/blender/{session_id}/push_result with:
      Content-Type: image/png
      X-Filename: <basename of image_path>

    Returns the parsed JSON response dict (includes 'generation_id') on success,
    or an empty dict on any error.
    """
    try:
        import os
        url      = f"{hub_url}/api/blender/{session_id}/push_result"
        filename = os.path.basename(image_path)
        with open(image_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "image/png",
                "X-Filename":   filename,
                "User-Agent":   "StyleEngine-Blender/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
        result = json.loads(body) if body else {}
        gen_id = result.get("generation_id", "?")
        print(f"[Hub Client] Pushed {filename} to hub ({len(data)//1024} KB) — gen_id={gen_id}")
        return result
    except Exception as e:
        print(f"[Hub Client] Push failed ({image_path}): {e}")
        return {}


def push_config(hub_url: str, session_id: str, generation_id: str,
                config: dict) -> None:
    """
    Post generation metadata (Step 2) after a successful push_result_image call.

    Endpoint: POST /api/sessions/{session_id}/history/{generation_id}/config

    config dict shape:
      {
        "model":      "gemini" | "sdxl",
        "workflow":   "<filename>.json",
        "blend_file": "<full path>.blend",
        "config": { "prompt": "...", "temperature": 0.0, ... },
        "sources": [
          { "role": "frame", "filename": "combined.jpg",
            "sha256": "a3f8...", "generation_id": null }
        ]
      }

    Silently swallows all errors so generation flow is never interrupted.
    """
    try:
        _post(
            f"{hub_url}/api/sessions/{session_id}/history/{generation_id}/config",
            config,
            timeout=8,
        )
        print(f"[Hub Client] Config pushed for gen_id={generation_id}")
    except Exception as e:
        print(f"[Hub Client] push_config failed (gen_id={generation_id}): {e}")


def download_result_image(hub_url: str, filename: str, save_path: str,
                          timeout: int = 30) -> bool:
    """
    Download a generated image from the hub's ComfyUI view proxy and write it
    to save_path on the local filesystem.

    The hub exposes the image at GET /api/comfy/view?filename=<name>.
    Returns True on success, False on any error.
    """
    try:
        url = f"{hub_url}/api/comfy/view?filename={urllib.parse.quote(filename)}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "StyleEngine-Blender/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        with open(save_path, "wb") as f:
            f.write(data)
        print(f"[Hub Client] Downloaded {filename} → {save_path} ({len(data)//1024} KB)")
        return True
    except Exception as e:
        print(f"[Hub Client] Download failed ({filename}): {e}")
        return False
