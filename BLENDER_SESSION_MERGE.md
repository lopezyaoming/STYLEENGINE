# A2A: Session Identity Refactor + Hub Session Merge

**From:** Hub Agent  
**To:** Blender Addon Agent  
**References:** Read `BLENDER_HUB_ADDON.md`, `BLENDER_SESSION_ROBUSTNESS.md`, and `BLENDER_CLOSE_LOOP.md` before implementing.

---

## Why this change

The hub now supports **hub-only sessions** — sessions created in the web UI without a Blender file. This breaks the assumption that `session_id = blend filename stem`. If the user creates a session called `apollo_project` on the web and later opens Blender, they need a way to *connect* that blend file to the existing cloud session.

The fix: **session identity moves into the blend file itself** via a custom scene property. The filename becomes just a display label. The session ID is what the file carries.

This also solves the ghost session problem: sessions are only created when the user explicitly clicks a button, never automatically from unsaved or unnamed files.

---

## Design overview

```
Old model:  session_id = stem(blend_path) + _machine_suffix   (auto, filename-derived)
New model:  session_id = bpy.context.scene["style_engine_session_id"]  (explicit, stored in file)
```

**Auto-registration** (`_delayed_hub_register`) still runs on file save/load — but **only when** `style_engine_session_id` is already set in the scene. It becomes a heartbeat for an established relationship, not a session creator.

**Session creation** happens through a new "Connect to Style Engine" UI button with two paths:
- **Create new** — mints a fresh session from the hub, stores ID in the blend file
- **Link existing** — user picks from a list of all hub sessions, stores chosen ID in the blend file

---

## Hub API surface (all already implemented — no hub changes needed)

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/sessions` | List all sessions (Blender + hub-only) |
| `POST` | `/api/sessions/create` | Mint a new named hub session |
| `POST` | `/api/blender/register` | Register/heartbeat a session |
| `GET` | `/api/blender/{sid}/peek` | Poll for results — **now includes `pending_import`** |
| `POST` | `/api/blender/{sid}/ack_import` | Clear the pending_import queue after processing |
| `GET` | `/api/sessions/{sid}/history/{gen_id}/download` | Proxy download (no CORS) |

### `GET /api/sessions` response shape
```json
[
  { "session_id": "apollo_b3cd0fb5", "blend_name": "Apollo", "hub_only": true,  "registered": false },
  { "session_id": "test13_53f4f5b8", "blend_name": "test13", "hub_only": false, "registered": true  },
  ...
]
```

### `GET /api/blender/{sid}/peek` — new field
```json
{
  "exists": true,
  "has_result": false,
  "result_ts": null,
  "pending_import": ["uuid-1", "uuid-2", "uuid-3"]
}
```
`pending_import` is non-empty only after a web UI "Push to Blender" action. Remains set until the addon calls `ack_import`.

### `POST /api/sessions/create` — request / response
```
POST /api/sessions/create
{ "name": "My Project" }

→ { "session_id": "my_project_a1b2c3d4", "blend_name": "My Project", "hub_only": true }
```

### When adopting a hub session via "Link existing"
Call `POST /api/blender/register` with the chosen session_id directly. **Do not send `prev_session_id`** — the GCS history is already in the right place. The hub will flip `hub_only` to `False` automatically once Blender registers.

---

## What the addon needs to implement

### Part 1 — Session identity stored in blend file

#### `hub_client.py` — new helpers

```python
SCENE_KEY = "style_engine_session_id"

def get_stored_session_id() -> str:
    """
    Read the session ID from the active scene's custom properties.
    Returns "" if not set. Always call from the main Blender thread.
    """
    import bpy
    return bpy.context.scene.get(SCENE_KEY, "")


def set_stored_session_id(session_id: str) -> None:
    """
    Write the session ID into the active scene's custom properties.
    The ID is saved with the blend file automatically.
    Always call from the main Blender thread.
    """
    import bpy
    bpy.context.scene[SCENE_KEY] = session_id
    print(f"[Hub Client] Session ID stored in blend file: {session_id}")


def get_session_id(blend_filepath=None) -> str:
    """
    Single source of truth for the current session ID.
    Priority: stored scene property > legacy filename-derived fallback.
    blend_filepath is accepted for backwards-compatibility but ignored when
    a stored property is present.
    """
    stored = get_stored_session_id()
    if stored:
        return stored
    # Legacy fallback — remove once all files have been migrated
    if blend_filepath:
        return _legacy_session_id_from_path(blend_filepath)
    return ""
```

> **Note:** Keep `_legacy_session_id_from_path()` (the current `get_session_id` logic using stem + machine suffix) as a private helper during the migration period. It is no longer the primary path.

---

#### `workspace_setup.py` — guard auto-registration

In `on_blend_file_saved()` and `on_blend_file_loaded()`, wrap the hub registration call with a guard:

```python
# Only re-register if this file already has an established session
sid = hub_client.get_stored_session_id()
if sid:
    # existing registration call — use sid directly, no filename derivation
    hub_client.register_session(sid, blend_name=Path(bpy.data.filepath).stem)
```

This means opening or saving an unregistered file produces **no hub traffic and no ghost session**.

**Save As handling:** When `on_blend_file_saved()` detects the filename changed (compare `Path(bpy.data.filepath).stem` vs the previously registered blend_name), keep the stored `session_id` unchanged — the session follows the content, not the filename. Just re-register with the new `blend_name`. Do **not** send `prev_session_id` (no rename event, just a display label change).

---

### Part 2 — "Connect to Style Engine" UI button

Add to the Style Engine addon panel (wherever the hub URL pref is shown, or a new "Cloud" section).

#### State: what to show

```
blend file NOT saved → show: [ Save your file to connect a session ]  (disabled, grey)

blend file saved, no session stored → show: [ Connect to Style Engine ▾ ]  (active button)
                                             dropdown: Create new / Link existing

blend file saved, session stored → show: [ ● session_id  ·  Live / Offline ]
                                          [ Change Session ]  (small link below)
```

#### Operator: `style_engine.connect_session`

```python
class SE_OT_ConnectSession(bpy.types.Operator):
    bl_idname  = "style_engine.connect_session"
    bl_label   = "Connect to Style Engine"
    
    mode: bpy.props.EnumProperty(items=[
        ("CREATE", "Create new session", ""),
        ("LINK",   "Link existing session", ""),
    ])
    # Used only for LINK mode — populated dynamically
    chosen_session: bpy.props.StringProperty()

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'WARNING'}, "Save your file before connecting a session")
            return {'CANCELLED'}

        if self.mode == "CREATE":
            return self._create_new(context)
        else:
            return self._link_existing(context)

    def _create_new(self, context):
        import threading
        blend_name = Path(bpy.data.filepath).stem

        def _do():
            try:
                sid = hub_client.create_hub_session(blend_name)
                # Schedule storing on the main thread
                def _store():
                    hub_client.set_stored_session_id(sid)
                    hub_client.register_session(sid, blend_name=blend_name)
                    hub_polling.start_polling_for(sid)
                bpy.app.timers.register(_store, first_interval=0.0)
            except Exception as e:
                print(f"[Style Engine] create_hub_session failed: {e}")

        threading.Thread(target=_do, daemon=True).start()
        self.report({'INFO'}, "Creating session…")
        return {'FINISHED'}

    def _link_existing(self, context):
        if not self.chosen_session:
            # Open a search popup or invoke a menu — see below
            return context.window_manager.invoke_props_dialog(self, width=300)
        sid = self.chosen_session
        blend_name = Path(bpy.data.filepath).stem
        hub_client.set_stored_session_id(sid)
        hub_client.register_session(sid, blend_name=blend_name)
        hub_polling.start_polling_for(sid)
        self.report({'INFO'}, f"Linked to session: {sid}")
        return {'FINISHED'}
```

#### `hub_client.py` — new `create_hub_session()` function

```python
def create_hub_session(name: str) -> str:
    """
    Ask the hub to mint a new named session.
    Returns the new session_id string.
    Raises on network error.
    """
    import json
    hub  = _hub_url()
    url  = f"{hub}/api/sessions/create"
    body = json.dumps({"name": name}).encode()
    req  = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "User-Agent": "StyleEngine-Blender/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["session_id"]
```

#### `hub_client.py` — new `fetch_all_sessions()` function

Used to populate the "Link existing" dropdown:

```python
def fetch_all_sessions() -> list:
    """
    Return the full session list from the hub.
    Each item: { session_id, blend_name, hub_only, registered }
    Returns [] on error.
    """
    import json
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
```

#### "Link existing" session picker UI

Use a dynamic `EnumProperty` populated from `fetch_all_sessions()`, or a simple `invoke_props_dialog` with a `StringProperty` for the session ID. The simplest approach that avoids threading complexity:

```python
# In the panel draw:
sessions = hub_client.fetch_all_sessions()   # called on draw — acceptable for a button click
for s in sessions:
    label = f"{s['blend_name']}  ({'hub only' if s['hub_only'] else 'blender'})"
    op = layout.operator("style_engine.connect_session", text=label)
    op.mode = "LINK"
    op.chosen_session = s["session_id"]
```

Wrap this in a collapsible sub-panel or popover to keep the panel tidy.

---

### Part 3 — Handle `pending_import` in the polling loop

#### `hub_polling.py` — extend `_poll_tick()`

```python
def _poll_tick() -> Optional[float]:
    state = peek_result()   # existing call

    # ── Existing has_result handling ─────────────────────────────────
    if state.get("has_result") and state.get("result_ts") != HubPollerState.last_result_ts:
        HubPollerState.last_result_ts = state["result_ts"]
        _on_result_ready(state)

    # ── NEW: bulk import triggered by hub "Push to Blender" ──────────
    pending = state.get("pending_import", [])
    if pending and not HubPollerState.import_in_progress:
        _on_pending_import(pending)

    return POLL_INTERVAL
```

Add `import_in_progress: bool = False` to `HubPollerState` to prevent the same batch from being dispatched twice while the daemon thread is still running.

#### `hub_polling.py` — add `_on_pending_import()`

```python
def _on_pending_import(generation_ids: list) -> None:
    """
    Main-thread entry point for a bulk hub→Blender import.
    Resolves bpy paths here (safe), then hands off to a daemon thread.
    """
    import bpy, threading
    from . import hub_client

    blend_path = bpy.data.filepath
    if not blend_path:
        print("[Hub Polling] pending_import skipped — file not saved")
        return

    session_id = hub_client.get_session_id(blend_path)
    if not session_id:
        print("[Hub Polling] pending_import skipped — no session registered")
        return

    images_dir = str(Path(blend_path).parent / "Images")
    HubPollerState.import_in_progress = True

    def _download_batch(sid, img_dir, gen_ids):
        imported = 0
        first_path = None
        for gen_id in gen_ids:
            try:
                dest = hub_client.download_enriched_png(sid, gen_id, img_dir)
                if first_path is None:
                    first_path = dest
                imported += 1
            except Exception as e:
                print(f"[Hub Polling] Failed to import {gen_id}: {e}")

        print(f"[Hub Polling] Bulk import: {imported}/{len(gen_ids)} downloaded")
        hub_client.ack_import(sid)
        HubPollerState.import_in_progress = False

        # Show info message and optionally reload current_ai — schedule on main thread
        def _notify():
            import bpy
            bpy.ops.info.reports_display_update()   # refresh info area
            # If no generation is currently active, load the first imported image
            if first_path and not HubPollerState.last_result_ts:
                import shutil, os
                current_ai = str(Path(bpy.data.filepath).parent / "temp" / "current_ai.png")
                try:
                    os.makedirs(os.path.dirname(current_ai), exist_ok=True)
                    shutil.copy2(first_path, current_ai)
                    workspace_setup.reload_ai_image()
                except Exception as e:
                    print(f"[Hub Polling] Auto-reload failed (non-fatal): {e}")
        bpy.app.timers.register(_notify, first_interval=0.0)

    t = threading.Thread(
        target=_download_batch,
        args=(session_id, images_dir, list(generation_ids)),
        daemon=True,
    )
    t.start()
```

#### `hub_client.py` — add `download_enriched_png()` and `ack_import()`

```python
def download_enriched_png(session_id: str, gen_id: str, images_dir: str) -> str:
    """
    Download the hub-enriched PNG via the proxy endpoint and save to images_dir.
    Returns the local file path. Raises on error.
    """
    from pathlib import Path
    hub = _hub_url()
    url = f"{hub}/api/sessions/{session_id}/history/{gen_id}/download"
    req = urllib.request.Request(url, headers={"User-Agent": "StyleEngine-Blender/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
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


def ack_import(session_id: str) -> None:
    """Tell the hub we've processed all pending_import IDs."""
    hub = _hub_url()
    url = f"{hub}/api/blender/{session_id}/ack_import"
    req = urllib.request.Request(
        url, data=b"", method="POST",
        headers={"User-Agent": "StyleEngine-Blender/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[Hub Client] ack_import failed (non-fatal): {e}")
```

---

## Edge cases

| Case | Behaviour |
|---|---|
| File not saved, user clicks "Connect" | Operator shows warning, returns CANCELLED |
| File not saved when `pending_import` arrives | `_on_pending_import` skips silently; hub retains the list until Blender reconnects |
| "Link existing" chosen session is hub-only | Register normally — hub flips `hub_only=False` automatically |
| "Link existing" chosen session already has a different Blender file attached | Hub history is merged (additive, deduped by ID). No data lost |
| Save As after connecting | `get_stored_session_id()` still returns the same ID from the scene property. Just re-register with new `blend_name`. Do **not** send `prev_session_id` |
| `ack_import` fails | Non-fatal. `import_in_progress` is cleared regardless. Hub retains the list; next tick will skip because `import_in_progress` is False again — use a `_last_imported_ids` set to avoid reprocessing the same batch |
| Hub restarts while `pending_import` is queued | `pending_import` is in-memory only on the hub — it will be lost on restart. This is acceptable; the history itself is safely in GCS |

---

## Testing the full flow

### Flow A — Create from Blender, generate on hub, return to Blender

1. Open Blender, save a `.blend` file.
2. In the Style Engine panel, click **Connect to Style Engine → Create new session**.
3. Confirm the panel updates to show the new session ID.
4. In the web UI (`/image`), switch to that session, generate an image.
5. Within 2 seconds, Blender should receive the image via the existing `has_result` path.

### Flow B — Create on hub, pull into Blender

1. In the web UI (`/library`), click **+** → name a session → create it.
2. Generate images under that session.
3. Open Blender, save a `.blend` file.
4. In the panel, click **Connect → Link existing session** → select the hub session.
5. Confirm the panel shows the session ID.
6. In `/library`, hover that session → click **→** (Push to Blender) → confirm.
7. Within 2 seconds, Blender's `Images/` folder fills with the downloaded PNGs and the info bar shows the import count.

### Flow C — Save As

1. With a connected session open, do File → Save As → new filename.
2. Confirm the Style Engine panel still shows the **same session ID**.
3. Confirm a hub re-registration fires with the new `blend_name` but the same `session_id`.

---

## Summary of all changes

| File | Change |
|---|---|
| `hub_client.py` | Add `get_stored_session_id()`, `set_stored_session_id()`, update `get_session_id()`, add `create_hub_session()`, `fetch_all_sessions()`, `download_enriched_png()`, `ack_import()` |
| `workspace_setup.py` | Guard auto-registration behind `get_stored_session_id()` check; fix Save As to not send `prev_session_id` |
| `hub_polling.py` | Add `import_in_progress` to state; add `pending_import` block in `_poll_tick()`; add `_on_pending_import()` |
| `ui_panel.py` | Add "Connect to Style Engine" section with Create / Link paths; show current session status |
| `__init__.py` | Register `SE_OT_ConnectSession` operator |
