"""
Minimal HTTP client for the Style Engine Hub (port 8000).
Uses only urllib.request — no third-party dependencies.
"""
import hashlib
import json
import os
import platform
import random
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

HUB_DEFAULT = "http://style-engine:8000"

# ── Scene property key ────────────────────────────────────────────────────────
# The session ID is stored in the blend file as a custom scene property so it
# survives Save As and is independent of the filename.

SCENE_KEY = "style_engine_session_id"

# ── Private helpers ───────────────────────────────────────────────────────────

def _hub_url() -> str:
    """Return the hub URL from addon preferences. Lazily imports bpy."""
    try:
        import bpy
        prefs = bpy.context.preferences.addons["styleengine"].preferences
        return getattr(prefs, "hub_url", HUB_DEFAULT).rstrip("/")
    except Exception:
        return HUB_DEFAULT


def _machine_suffix() -> str:
    """
    Stable 8-char hex suffix unique to this machine/user.
    Derived from hostname + login name so it survives Blender restarts.
    """
    try:
        raw = f"{platform.node()}-{os.getlogin()}"
    except Exception:
        raw = platform.node()
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


_EPHEMERAL_SESSION_ID: str | None = None


def _ephemeral_session_id() -> str:
    """
    Per-process ephemeral session ID used when no .blend file is saved.
    Generated once on first call and reused for the lifetime of this process.
    Format: unsaved_<8hex>  — the hub groups these under the 'unsaved' bucket.
    """
    global _EPHEMERAL_SESSION_ID
    if _EPHEMERAL_SESSION_ID is None:
        raw = f"{platform.node()}-{time.time()}-{random.random()}"
        _EPHEMERAL_SESSION_ID = "unsaved_" + hashlib.sha256(raw.encode()).hexdigest()[:8]
    return _EPHEMERAL_SESSION_ID


def _legacy_session_id_from_path(blend_filepath: str) -> str:
    """
    Legacy filename-derived session ID: stem_8hex.
    Kept during migration period for files that don't yet have a stored ID.
    """
    return f"{Path(blend_filepath).stem}_{_machine_suffix()}"


# ── Session identity (new model) ──────────────────────────────────────────────

def get_stored_session_id() -> str:
    """
    Read the session ID from the active scene's custom properties.
    Returns "" if not set. Always call from the main Blender thread.
    """
    try:
        import bpy
        return bpy.context.scene.get(SCENE_KEY, "")
    except Exception:
        return ""


def set_stored_session_id(session_id: str) -> None:
    """
    Write the session ID into the active scene's custom properties.
    The ID is persisted with the blend file automatically.
    Always call from the main Blender thread.
    """
    try:
        import bpy
        bpy.context.scene[SCENE_KEY] = session_id
        print(f"[Hub Client] Session ID stored in blend file: {session_id}")
    except Exception as e:
        print(f"[Hub Client] set_stored_session_id failed: {e}")


def get_session_id(blend_filepath: str | None = None) -> str:
    """
    Single source of truth for the current session ID.

    Priority:
      1. Stored scene property (set via Connect button or link operation)
      2. Legacy filename-derived fallback (stem_machine_suffix) for files
         that pre-date the new model
      3. Empty string if the file is not saved and no property is set

    `blend_filepath` is accepted for backwards-compatibility but is only
    used when no stored property is present.
    """
    stored = get_stored_session_id()
    if stored:
        return stored
    if blend_filepath:
        return _legacy_session_id_from_path(blend_filepath)
    return ""


# ── Last-registered tracker ───────────────────────────────────────────────────
# Kept to detect renames within a single Blender session, but prev_session_id
# is no longer sent to the hub (session follows content, not filename).

_last_registered_session_id: str | None = None


# ── Utilities ─────────────────────────────────────────────────────────────────

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


# ── Hub API functions ─────────────────────────────────────────────────────────

def register_session(hub_url: str, session_id: str, blend_name: str,
                     blend_path: str, current_ai_path: str) -> bool:
    """
    Register this Blender instance with the hub.

    With the new session-identity model, session_id is always the stored scene
    property value — Save As renames only update blend_name, not session_id,
    so prev_session_id is never sent.

    Returns True on success.
    """
    global _last_registered_session_id
    try:
        payload = {
            "session_id":      session_id,
            "blend_name":      blend_name,
            "blend_path":      blend_path,
            "current_ai_path": current_ai_path,
        }
        _post(f"{hub_url}/api/blender/register", payload)
        _last_registered_session_id = session_id
        return True
    except Exception as e:
        print(f"[Hub Client] Register failed: {e}")
        return False


def peek_result(hub_url: str, session_id: str) -> dict:
    """
    Poll for a pending result.
    Returns the full peek dict including has_result, pending_import, etc.
    On network error returns a safe fallback so polling never crashes.
    """
    try:
        return _get(f"{hub_url}/api/blender/{session_id}/peek")
    except Exception:
        return {"exists": False, "has_result": False, "result_ts": None,
                "pending_import": []}


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


def import_image(hub_url: str, session_id: str, png_bytes: bytes,
                 filename: str = "import.png") -> dict:
    """
    Import a single PNG into the hub's session history.

    The hub deduplicates by embedded `id` and `sha256` — safe to call
    repeatedly with the same file.

    Returns the server response dict, or {"imported": False, "reason": "network_error"}
    on any failure.
    """
    try:
        url = f"{hub_url}/api/sessions/{session_id}/history/import"
        req = urllib.request.Request(
            url,
            data=png_bytes,
            headers={
                "Content-Type": "image/png",
                "X-Filename":   filename,
                "User-Agent":   "StyleEngine-Blender/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[Hub Client] import_image failed for {filename}: {e}")
        return {"imported": False, "reason": "network_error"}


def download_enriched_png(session_id: str, gen_id: str,
                          images_dir: str, timeout: int = 60) -> str:
    """
    Download the hub's metadata-embedded PNG via the proxy endpoint and save
    it to images_dir.

    Endpoint: GET /api/sessions/{session_id}/history/{gen_id}/download
    The endpoint is a direct proxy (no CORS redirect) that includes a
    Content-Disposition header with the original filename.

    Returns the local file path on success.  Raises on error (caller handles).
    """
    hub = _hub_url()
    url = f"{hub}/api/sessions/{session_id}/history/{gen_id}/download"
    req = urllib.request.Request(
        url, headers={"User-Agent": "StyleEngine-Blender/1.0"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        cd   = resp.headers.get("Content-Disposition", "")

    filename = gen_id[:8] + ".png"
    if 'filename="' in cd:
        filename = cd.split('filename="')[1].rstrip('"')

    Path(images_dir).mkdir(parents=True, exist_ok=True)
    dest = str(Path(images_dir) / filename)
    with open(dest, "wb") as f:
        f.write(data)
    print(f"[Hub Client] Imported {filename} → {images_dir}")
    return dest


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


def ack_import(session_id: str) -> None:
    """
    Tell the hub we have processed all pending_import IDs.
    Uses _hub_url() internally — no hub_url parameter needed.
    Silently swallows errors (non-fatal).
    """
    hub = _hub_url()
    url = f"{hub}/api/blender/{session_id}/ack_import"
    req = urllib.request.Request(
        url, data=b"", method="POST",
        headers={"User-Agent": "StyleEngine-Blender/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
        print(f"[Hub Client] ack_import sent for session {session_id}")
    except Exception as e:
        print(f"[Hub Client] ack_import failed (non-fatal): {e}")


def create_hub_session(name: str) -> str:
    """
    Ask the hub to mint a new named session.
    Returns the new session_id string.
    Raises on network error (caller should wrap in try/except).
    """
    hub  = _hub_url()
    url  = f"{hub}/api/sessions/create"
    body = json.dumps({"name": name}).encode()
    req  = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent":   "StyleEngine-Blender/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    session_id = data["session_id"]
    print(f"[Hub Client] Created hub session: {session_id!r}")
    return session_id


def fetch_all_sessions() -> list:
    """
    Return the full session list from the hub.
    Each item: { session_id, blend_name, hub_only, registered }
    Returns [] on any error.
    """
    try:
        hub = _hub_url()
        req = urllib.request.Request(
            f"{hub}/api/sessions",
            headers={"User-Agent": "StyleEngine-Blender/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[Hub Client] fetch_all_sessions failed: {e}")
        return []
