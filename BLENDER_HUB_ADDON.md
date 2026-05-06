# A2A: Style Engine Addon — Hub Integration

**For the coding agent responsible for the Blender addon.**

This document specifies exactly what needs to be added to the `styleengine` Blender addon so that it connects to the Style Engine Hub (FastAPI on port 8000) for real-time image delivery.

---

## Context

The Style Engine Hub runs on a separate Linux machine accessible via Tailscale
(e.g. `http://style-engine:8000`). Blender typically runs on a **different machine**
(Windows/macOS). The hub cannot write files directly to Blender's disk.

When the web UI generates an image:
1. The hub stores the result image metadata (filename, subfolder, type).
2. Blender polls the hub, sees `has_result: true`, and **downloads the image itself**
   via `GET {hub_url}/api/comfy/view?filename=...`.
3. Blender writes the downloaded bytes to its own `current_ai_path` and reloads.

**Critical configuration:** The `hub_url` preference MUST be set to the hub's
Tailscale address, not `127.0.0.1`. Default: `http://style-engine:8000`.
The user sets this once in addon preferences → Hub URL.

No new Python dependencies are required. Everything uses `urllib.request` and `bpy.app.timers`.

---

## Hub API Contract

Base URL (configurable via new preference `hub_url`): `http://style-engine:8000` (Tailscale hostname, NOT 127.0.0.1)

### Overview of all endpoints used by the addon

| Direction | Method | Path | Purpose |
|---|---|---|---|
| Blender→Hub | POST | `/api/blender/register` | Register session on startup / file load / file save |
| Hub→Blender | GET | `/api/blender/{id}/peek` | Poll for pending hub-generated results (every 2 s) |
| Blender→Hub | POST | `/api/blender/{id}/ack` | Acknowledge image received |
| **Blender→Hub** | **POST** | **`/api/blender/{id}/push_result`** | **Push locally generated image (Step 1)** |
| **Blender→Hub** | **POST** | **`/api/sessions/{id}/history/{gen_id}/config`** | **Push generation metadata (Step 2)** |

### `POST /api/blender/register`

Call on addon startup, on `load_post` handler, and on `save_post` handler.

**Request body (JSON):**
```json
{
  "session_id":      "car",
  "blend_name":      "car",
  "blend_path":      "/home/user/projects/car.blend",
  "current_ai_path": "/home/user/projects/car_styleengine/temp/current_ai.png"
}
```

- `session_id` = `Path(bpy.data.filepath).stem` if the file is saved, else `"unsaved"`.
- `blend_path` = `bpy.data.filepath` (empty string `""` if unsaved).
- `current_ai_path` = result of `workspace_setup.get_active_ai_output_path(context)` — this already resolves the correct path for both Scene Mode and Asset Mode.

**Response:**
```json
{ "registered": "car" }
```

---

### `GET /api/blender/{session_id}/peek`

Poll this every 2 s from `bpy.app.timers`. Idempotent — no state is changed by calling it.

**Response:**
```json
{
  "exists":           true,
  "has_result":       false,
  "result_ts":        null,
  "result_filename":  "",
  "result_subfolder": "",
  "result_type":      "output"
}
```
or when a result is ready:
```json
{
  "exists":           true,
  "has_result":       true,
  "result_ts":        1746468231.4,
  "result_filename":  "depth_00927_.png",
  "result_subfolder": "",
  "result_type":      "output"
}
```

When `has_result` is `true` **and** `result_ts` is newer than the last acknowledged timestamp:
1. Build the download URL: `{hub_url}/api/comfy/view?filename={result_filename}&subfolder={result_subfolder}&type={result_type}`
2. Download the image bytes (urllib.request, 30 s timeout)
3. Write bytes to `current_ai_path`
4. Call `workspace_setup.reload_ai_image()`
5. Call `/ack`

---

### `POST /api/blender/{session_id}/ack`

Call after `reload_ai_image()` completes. No request body needed.

**Response:**
```json
{ "acked": "car" }
```

---

### `POST /api/blender/{session_id}/push_result` — Step 1 of 2

Send the raw PNG bytes immediately after generation completes.

**Request:**
```
Content-Type: image/png
X-Filename: current_ai.png
<raw PNG bytes>
```

**Response:**
```json
{ "ok": true, "generation_id": "550e8400-e29b-41d4-a716-446655440000" }
```

Store `generation_id` — you need it for Step 2.

**Note:** If the PNG being pushed was itself downloaded from a hub generation
(i.e., it has a `StyleEngine:config` chunk embedded), the hub will automatically
detect this and record the lineage as `refined_from`. No extra work needed from Blender.

---

### `POST /api/sessions/{session_id}/history/{generation_id}/config` — Step 2 of 2

Post the generation metadata. Call this immediately after Step 1 succeeds.

**Request body (JSON):**
```json
{
  "model":      "gemini",
  "workflow":   "ImageNanoAlignment.json",
  "blend_file": "C:/cockpit/test6.blend",
  "config": {
    "prompt":        "goo good oll",
    "temperature":   0.0,
    "imageSize":     "1K",
    "aspectRatio":   "16:9",
    "alignmentMode": true,
    "model":         "gemini-3-pro-image-preview"
  },
  "sources": [
    {
      "role":          "frame",
      "filename":      "combined.jpg",
      "sha256":        "a3f8c2d1e9b4...",
      "generation_id": null
    }
  ]
}
```

**Fields:**
- `model`: `"gemini"` or `"sdxl"` (required)
- `config`: all generation parameters (prompt, temperature, etc.)
- `sources`: array of input images used. Compute `sha256` of the raw bytes of each source file.
  - If a source image was itself a hub-generated PNG with `StyleEngine:config` embedded,
    extract its `id` field and use it as `generation_id`. Otherwise `null`.
- `blend_file`: full path to the blend file (optional, for context)

**Response:**
```json
{ "ok": true }
```

**In `hub_client.py` add:**
```python
def push_config(hub_url: str, session_id: str, generation_id: str, config: dict) -> None:
    """Post generation metadata after a push_result call. Silently swallows errors."""
    try:
        _post(f"{hub_url}/api/sessions/{session_id}/history/{generation_id}/config", config)
    except Exception as e:
        print(f"[Hub Client] push_config failed: {e}")
```

**SHA256 helper (add to `hub_client.py`):**
```python
import hashlib

def sha256_file(path: str) -> str:
    """Return hex SHA256 of a file's bytes."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
```

**Call site in the addon (after generation completes):**
```python
# In daemon thread that calls push_result:
import hub_client, json
from pathlib import Path

response = hub_client.push_result_raw(hub_url, session_id, png_bytes)
gen_id = response.get("generation_id")
if gen_id:
    config_payload = {
        "model":      "gemini",   # or "sdxl"
        "blend_file": bpy.data.filepath,
        "config": {
            "prompt":      prompt_text,
            "temperature": temperature,
            # ... other params ...
        },
        "sources": [
            {
                "role":          "frame",
                "filename":      "combined.jpg",
                "sha256":        hub_client.sha256_file(combined_jpg_path),
                "generation_id": None,
            }
        ]
    }
    hub_client.push_config(hub_url, session_id, gen_id, config_payload)
```

---

### `POST /api/sessions/{session_id}/history/import` — Library Sync

Idempotent endpoint for bulk-importing Blender's existing library to the hub.
Use this on registration (or on a manual sync) to bring the hub's history up to
date with images that were generated before the hub integration existed.

**Request:**
```
Content-Type: image/png
X-Filename: 20260505_152229_142_gcs_1920x1080.png   (optional, ignored by server)
<raw PNG bytes>
```

**Response:**
```json
{ "imported": true,  "generation_id": "uuid", "reason": null }
{ "imported": false, "generation_id": "uuid", "reason": "duplicate_id" }
{ "imported": false, "generation_id": null,   "reason": "duplicate_sha256" }
```

**Deduplication:** The server deduplicates by embedded `StyleEngine:config` id first,
then by sha256 of the raw bytes. Safe to call for the entire library on every
registration — the server will skip anything it already has.

**Add to `hub_client.py`:**
```python
def import_image(hub_url: str, session_id: str, png_bytes: bytes,
                 filename: str = "import.png") -> dict:
    """
    Import a single PNG into the hub's session history.
    Returns the server response dict.
    On network error returns {"imported": False, "reason": "network_error"}.
    """
    try:
        req = urllib.request.Request(
            f"{hub_url}/api/sessions/{session_id}/history/import",
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
```

**Library sync call site (in `__init__.py` or a background thread on registration):**
```python
def _sync_library_to_hub(hub_url: str, session_id: str) -> None:
    """
    Walk the session's generation library and import any images the hub doesn't have.
    Runs in a daemon thread — never blocks the main thread.
    """
    from pathlib import Path
    import bpy
    from . import hub_client, workspace_setup

    try:
        library_dir = Path(workspace_setup.get_project_library(bpy.context))
    except Exception:
        return

    if not library_dir.exists():
        return

    imported = skipped = 0
    for png in sorted(library_dir.glob("*.png")):
        try:
            data = png.read_bytes()
            result = hub_client.import_image(hub_url, session_id, data, png.name)
            if result.get("imported"):
                imported += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[Hub Client] Sync failed for {png.name}: {e}")

    print(f"[Hub Client] Library sync complete: {imported} imported, {skipped} skipped")
```

Call `_sync_library_to_hub` in a daemon thread inside `_do_hub_register()`:
```python
import threading
t = threading.Thread(
    target=_sync_library_to_hub,
    args=(hub_url, session_id),
    daemon=True,
)
t.start()
```

---

## Files to Create

### `scripts/addons/styleengine/hub_client.py`

Pure stdlib HTTP helpers. No `import bpy` in this file.

```python
"""
Minimal HTTP client for the Style Engine Hub (port 8000).
Uses only urllib.request — no third-party dependencies.
"""
import json
import urllib.request
import urllib.error

HUB_DEFAULT = "http://style-engine:8000"  # Tailscale hostname — override in prefs


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
    Returns the full peek dict including result_filename / subfolder / type.
    On network error returns a safe fallback so polling never crashes.
    """
    try:
        return _get(f"{hub_url}/api/blender/{session_id}/peek")
    except Exception:
        return {"exists": False, "has_result": False, "result_ts": None,
                "result_filename": "", "result_subfolder": "", "result_type": "output"}


def download_result_image(hub_url: str, filename: str,
                          subfolder: str = "", img_type: str = "output",
                          timeout: int = 30) -> bytes:
    """Download the generated image bytes from the hub."""
    import urllib.parse
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": img_type})
    req = urllib.request.Request(
        f"{hub_url}/api/comfy/view?{params}",
        headers={"User-Agent": "StyleEngine-Blender/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def ack_result(hub_url: str, session_id: str) -> None:
    """Acknowledge a delivered result. Silently swallows errors."""
    try:
        _post(f"{hub_url}/api/blender/{session_id}/ack", {})
    except Exception as e:
        print(f"[Hub Client] Ack failed: {e}")
```

---

### `scripts/addons/styleengine/hub_polling.py`

`bpy.app.timers`-based polling loop. Mirror the pattern in `progress_bar.py`.

```python
"""
Hub polling — receives generated images from the Style Engine Hub.
Uses bpy.app.timers for non-blocking periodic polling.

IMPORTANT — cross-machine design:
The hub runs on a separate Linux machine. It CANNOT write files to this
Blender machine's disk. When a result is ready, Blender downloads the image
bytes from the hub via /api/comfy/view and writes them to current_ai_path itself.
"""
import bpy
from pathlib import Path
from . import hub_client
from . import workspace_setup

POLL_INTERVAL = 2.0   # seconds

class HubPollerState:
    is_polling     = False
    last_result_ts = None   # float — timestamp of last acknowledged result

    @classmethod
    def reset(cls):
        cls.is_polling     = False
        cls.last_result_ts = None


def _get_prefs():
    return bpy.context.preferences.addons["styleengine"].preferences


def _session_id() -> str:
    if bpy.data.is_saved:
        return Path(bpy.data.filepath).stem
    return "unsaved"


def _poll_tick():
    """Timer callback — runs on Blender's main thread every POLL_INTERVAL seconds."""
    if not HubPollerState.is_polling:
        return None  # stop timer

    try:
        prefs = _get_prefs()
        hub_url    = getattr(prefs, "hub_url", "http://style-engine:8000").rstrip("/")
        session_id = _session_id()

        result = hub_client.peek_result(hub_url, session_id)

        if result.get("has_result"):
            ts = result.get("result_ts")
            # Guard against re-triggering the same delivery
            if ts != HubPollerState.last_result_ts:
                HubPollerState.last_result_ts = ts
                _on_result_ready(hub_url, session_id, result)
                hub_client.ack_result(hub_url, session_id)

    except Exception as e:
        print(f"[Hub Polling] Tick error: {e}")

    return POLL_INTERVAL


def _on_result_ready(hub_url: str, session_id: str, result: dict):
    """Download the generated image from the hub, write to disk, then reload in Blender."""
    try:
        filename  = result.get("result_filename", "")
        subfolder = result.get("result_subfolder", "")
        img_type  = result.get("result_type", "output")

        if not filename:
            print("[Hub Polling] Empty filename in result — skipping")
            return

        # Download image bytes from hub (cross-machine safe)
        data = hub_client.download_result_image(hub_url, filename, subfolder, img_type)

        # Resolve local current_ai_path and write
        ctx = bpy.context
        ai_path = workspace_setup.get_active_ai_output_path(ctx)
        Path(ai_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ai_path).write_bytes(data)

        # Reload the image datablock
        workspace_setup.reload_ai_image(ctx)
        print(f"[Hub Polling] ✓ New image from hub ({filename}) — reloaded current_ai.png")

        # Force viewport redraw
        for window in ctx.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except Exception as e:
        print(f"[Hub Polling] Reload error: {e}")


def start_polling():
    if HubPollerState.is_polling:
        return
    HubPollerState.is_polling = True
    if not bpy.app.timers.is_registered(_poll_tick):
        bpy.app.timers.register(_poll_tick, first_interval=1.0, persistent=True)
    print("[Hub Polling] Started")


def stop_polling():
    HubPollerState.is_polling = False
    if bpy.app.timers.is_registered(_poll_tick):
        bpy.app.timers.unregister(_poll_tick)
    HubPollerState.reset()
    print("[Hub Polling] Stopped")


def register():
    # Auto-start after a short delay so all addon modules are ready
    bpy.app.timers.register(
        lambda: (start_polling(), None)[1],
        first_interval=1.5,
    )
    print("[Hub Polling] Registered")


def unregister():
    stop_polling()
    print("[Hub Polling] Unregistered")
```

---

## Files to Modify

### `prefs.py` — add `hub_url` preference

Inside the `StyleEnginePreferences` class (next to the existing `gcs_server_url` property):

```python
hub_url: bpy.props.StringProperty(
    name="Hub URL",
    description="Style Engine Hub address — use the Tailscale hostname, NOT localhost",
    default="http://style-engine:8000",
)
```

Draw it in the `draw()` method, in the same `basic_box` that shows `gcs_server_url`:

```python
basic_box.prop(self, "hub_url", text="Hub URL")
```

---

### `__init__.py` — import and register the new modules

1. Add the import with the other module imports:
   ```python
   from . import hub_client   # noqa: F401 (no classes to register)
   from . import hub_polling
   ```

2. Add `hub_polling` to the `modules` list so `register()` / `unregister()` are called:
   ```python
   modules = [
       prefs,
       workspace_setup,
       ui_panel,
       asset_mode,
       progress_bar,
       heavypoly_integration,
       pie_menu,
       hub_polling,   # <-- add here
   ]
   ```

3. In the `register()` function, after all modules are registered, call the first registration with the hub:
   ```python
   bpy.app.timers.register(_delayed_hub_register, first_interval=2.0)
   ```
   
   Add this helper above `register()`:
   ```python
   def _delayed_hub_register():
       """Register with hub after Blender is fully loaded."""
       try:
           _do_hub_register()
       except Exception as e:
           print(f"[Style Engine] Hub register failed: {e}")
       return None  # don't repeat
   
   def _do_hub_register():
       from pathlib import Path
       import bpy
       from . import hub_client, workspace_setup
       prefs      = bpy.context.preferences.addons["styleengine"].preferences
       hub_url    = getattr(prefs, "hub_url", "http://style-engine:8000").rstrip("/")
       session_id = Path(bpy.data.filepath).stem if bpy.data.is_saved else "unsaved"
       blend_name = session_id
       blend_path = bpy.data.filepath
       try:
           ctx          = bpy.context
           current_ai   = str(workspace_setup.get_active_ai_output_path(ctx))
       except Exception:
           current_ai   = ""
       ok = hub_client.register_session(hub_url, session_id, blend_name, blend_path, current_ai)
       print(f"[Style Engine] Hub register → {hub_url}  session={session_id!r}  ok={ok}")
   ```

---

### `workspace_setup.py` — re-register on file load and save

The existing `on_blend_file_saved` and `on_blend_file_loaded` handlers already run on `save_post` and `load_post`. Add a hub re-registration call at the **end** of each:

```python
# At the end of on_blend_file_saved():
try:
    from . import hub_client
    from pathlib import Path
    prefs      = bpy.context.preferences.addons["styleengine"].preferences
    hub_url    = getattr(prefs, "hub_url", "http://style-engine:8000").rstrip("/")
    session_id = Path(bpy.data.filepath).stem
    current_ai = str(get_active_ai_output_path(bpy.context))
    hub_client.register_session(hub_url, session_id, session_id, bpy.data.filepath, current_ai)
    print(f"[Style Engine] Hub re-registered session: {session_id!r}")
except Exception as e:
    print(f"[Style Engine] Hub re-register on save failed: {e}")
```

```python
# At the end of on_blend_file_loaded():
try:
    from . import hub_client
    from pathlib import Path
    prefs      = bpy.context.preferences.addons["styleengine"].preferences
    hub_url    = getattr(prefs, "hub_url", "http://style-engine:8000").rstrip("/")
    session_id = Path(bpy.data.filepath).stem if bpy.data.is_saved else "unsaved"
    current_ai = str(get_active_ai_output_path(bpy.context))
    hub_client.register_session(hub_url, session_id, session_id, bpy.data.filepath, current_ai)
    print(f"[Style Engine] Hub re-registered session on load: {session_id!r}")
except Exception as e:
    print(f"[Style Engine] Hub re-register on load failed: {e}")
```

---

## Integration Checklist

- [ ] `hub_client.py` created (no bpy imports, pure stdlib)
- [ ] `hub_polling.py` created (mirrors `progress_bar.py` timer pattern)
- [ ] `prefs.py` — `hub_url` StringProperty added and drawn in basic_box
- [ ] `__init__.py` — `hub_client` and `hub_polling` imported
- [ ] `__init__.py` — `hub_polling` added to `modules` list
- [ ] `__init__.py` — `_delayed_hub_register` timer registered in `register()`
- [ ] `workspace_setup.py` — hub re-registration added to `on_blend_file_saved`
- [ ] `workspace_setup.py` — hub re-registration added to `on_blend_file_loaded`

---

## Verification

With the hub running (`uvicorn main:app --host 0.0.0.0 --port 8000 --reload`) and Blender open on the Windows machine:

1. **Check hub URL in prefs:** Blender → Edit → Preferences → Add-ons → Style Engine → Hub URL. It must be `http://style-engine:8000` (or the Tailscale IP/hostname of the Linux hub machine). If it shows `127.0.0.1`, registration will always fail silently.
2. **Force re-register (without a file reload):** In Blender's Python console: `import bpy; bpy.ops.wm.save_mainfile()` — this triggers `on_blend_file_saved` which re-registers.
3. **Check hub sessions:** From the Linux machine: `curl http://localhost:8000/api/sessions` — should show the registered session with the blend name.
4. In the web UI, select the session in the session dropdown and generate an image.
5. Watch Blender's **System Console** (Window → Toggle System Console) for lines like:
   - `[Style Engine] Hub register → http://style-engine:8000  session='test3'  ok=True`
   - `[Hub Polling] ✓ New image from hub (depth_00927_.png) — reloaded current_ai.png`
6. The AI Vision camera background in Blender should update automatically within ~2 s of the image completing.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Sessions list empty, Blender shows `ok=False` | `hub_url` points to `127.0.0.1` on the Windows machine | Change Hub URL pref to `http://style-engine:8000` |
| `[Hub Client] Register failed: <urlopen error ...>` | Hub not reachable from Blender's machine | Verify Tailscale is active; ping `style-engine` from Windows |
| Session appears, then disappears after 2 min | Blender lost network / addon crashed | Hub evicts sessions idle >120 s; check System Console for polling errors |
| `[Hub Polling] Reload error: ...` | `get_active_ai_output_path` raised on unsaved file | Save the blend file before generating |
| Image delivered to hub but Blender doesn't update | `result_filename` empty in peek response | Check hub log — likely `notify_result` not called; ensure `session_id` was passed in the generate request |

---

## Notes for the Agent

- `workspace_setup.get_active_ai_output_path(context)` already handles both Scene Mode and Asset Mode correctly. Use it — do not recompute the path manually.
- `workspace_setup.reload_ai_image(context)` already handles both modes and the `bpy.data.images` datablock reload. Use it.
- All hub calls are fire-and-forget with a short timeout (4 s). A hub that is offline must never crash or freeze Blender — always wrap in `try/except`.
- The `hub_client.py` module has no Blender imports, which makes it trivially testable outside Blender.
- `hub_polling.py` must never call `bpy` from outside the timer callback (which runs on the main thread). Do not spawn threads.
- The hub **never writes files directly to disk**. Blender downloads the image bytes itself via `/api/comfy/view`. This is intentional — it works cross-machine.
