# Blender Addon — Session Robustness Fixes

**Document type:** Agent-to-Agent (A2A) specification  
**Audience:** The Blender addon coding agent  
**Hub counterpart changes:** Already implemented in `backend/blender_sessions.py`, `backend/gcs_store.py`, `backend/generation_store.py`, `backend/main.py`

---

## Background

The hub's robustness analysis identified three addon-side issues that cause
session collisions, lost history, and broken continuity.  This document
specifies the exact changes needed.

---

## Issue 1 — Session ID collisions between users or machines

### Problem

`session_id` is currently the bare `.blend` stem (e.g. `test`, `car`).
If two different users both work on a file called `test.blend` they write to
the **same** GCS prefix (`sessions/test/`), silently clobbering each other's
history.

### Fix — stable machine-scoped suffix

Append an 8-character hex suffix derived from a **stable machine identifier**
to every `session_id`.  The suffix must be:

* Deterministic for the same machine/user across Blender restarts (not
  a random UUID generated each run).
* Short and lowercase so URLs remain readable.

**Recommended derivation:**

```python
import hashlib, platform, os

def _machine_suffix() -> str:
    """Stable 8-char hex suffix unique to this machine/user."""
    raw = f"{platform.node()}-{os.getlogin()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]
```

**`hub_client.py` — update `get_session_id()` (or equivalent)**

```python
def get_session_id(blend_filepath: str | None) -> str:
    """
    Return the session ID for the current .blend file.
    Falls back to an ephemeral per-launch ID for unsaved files (see Issue 3).
    """
    if not blend_filepath:
        return _ephemeral_session_id()          # see Issue 3

    stem = Path(blend_filepath).stem            # e.g. "car"
    suffix = _machine_suffix()                  # e.g. "3a9f12bc"
    return f"{stem}_{suffix}"                   # e.g. "car_3a9f12bc"
```

**Where to apply:** Every place the addon currently computes
`Path(bpy.data.filepath).stem` for the session ID — specifically in
`workspace_setup.on_blend_file_saved()`, `on_blend_file_loaded()`, and the
`_delayed_hub_register()` helper.

> **Note:** Existing GCS data under bare `test` / `car` prefixes will not be
> auto-migrated; those are discoverable in the hub's history browser as
> separate (dormant) sessions.

---

## Issue 2 — "unsaved" sessions share one GCS prefix

### Problem

Before a `.blend` file is saved for the first time, every Blender instance
(potentially on different machines) sends `session_id = "unsaved"`.  They all
write to `sessions/unsaved/` and clobber each other.

### Fix — per-launch ephemeral ID

Generate a unique ephemeral ID on addon **load** (not on each registration
call) and reuse it for the lifetime of that Blender process.

```python
import hashlib, time, random, platform

_EPHEMERAL_SESSION_ID: str | None = None

def _ephemeral_session_id() -> str:
    """
    Stable-for-this-process ephemeral session ID used when no .blend is saved.
    Format: unsaved_<8hex>  so the hub browser groups it under 'unsaved'.
    """
    global _EPHEMERAL_SESSION_ID
    if _EPHEMERAL_SESSION_ID is None:
        raw = f"{platform.node()}-{time.time()}-{random.random()}"
        _EPHEMERAL_SESSION_ID = "unsaved_" + hashlib.sha256(raw.encode()).hexdigest()[:8]
    return _EPHEMERAL_SESSION_ID
```

Call `_ephemeral_session_id()` (instead of `"unsaved"`) whenever
`bpy.data.filepath` is empty.

**Effect:** Each Blender process gets its own isolated `sessions/unsaved_XXXX/`
prefix in GCS.  After the file is saved, `get_session_id()` returns the proper
`stem_suffix` ID and the ephemeral prefix is abandoned (it remains in GCS for
history browsing).

---

## Issue 3 — "Save As" loses history continuity

### Problem

When the user does **File → Save As** (renaming `old_name.blend` to
`new_name.blend`) the session ID changes from `old_name_<suffix>` to
`new_name_<suffix>`.  The browser history reel for the new session starts
empty, even though all the old work is still in GCS under the old prefix.

### Fix — send `prev_session_id` in the registration payload

Detect the rename in the addon and include `prev_session_id` in the
`POST /api/blender/register` body.  The hub will use this to redirect history
lookups (hub-side logic already handles an unknown `prev_session_id`
gracefully — it's simply ignored if it doesn't exist).

#### Detection logic

Track the **previous** session ID in module-level state:

```python
# hub_client.py
_last_registered_session_id: str | None = None

def register_session(session_id: str, blend_name: str,
                     blend_path: str, current_ai_path: str) -> None:
    global _last_registered_session_id

    prev_id = _last_registered_session_id
    # Only send prev_session_id when there was a genuine rename —
    # not on first launch and not on a plain re-save.
    payload = {
        "session_id":      session_id,
        "blend_name":      blend_name,
        "blend_path":      blend_path,
        "current_ai_path": current_ai_path,
    }
    if prev_id and prev_id != session_id:
        payload["prev_session_id"] = prev_id

    # ... existing urllib POST logic ...

    _last_registered_session_id = session_id
```

#### Hub endpoint change (already merged)

The hub's `POST /api/blender/register` handler now reads `prev_session_id`
from the body.  When present, it calls
`generation_store.link_prev_session(session_id, prev_session_id)` which
copies the old `index.json` entries into the new session prefix so the history
reel appears continuous.

> **Note:** `generation_store.link_prev_session()` only copies index metadata —
> image blobs are **not** duplicated (both sessions reference the same GCS
> objects via their blob paths).

---

## Summary of required addon changes

| File | Change |
|---|---|
| `hub_client.py` | Add `_machine_suffix()`, `_ephemeral_session_id()`, update `get_session_id()`, add `prev_session_id` logic to `register_session()` |
| `workspace_setup.py` | Replace bare `Path(bpy.data.filepath).stem` with `hub_client.get_session_id(bpy.data.filepath)` in all three registration call sites |
| `__init__.py` (or `prefs.py`) | No changes needed |

---

## Hub-side changes already implemented (FYI)

These are done — the addon only needs the above changes:

| Component | Change |
|---|---|
| `gcs_store.py` | `upload_atomic` / `upload_atomic_json` with GCS `if_generation_match` preconditions to prevent concurrent `index.json` clobbers |
| `generation_store.py` | `_write_index()` now uses `upload_atomic_json`; `save_current_ai()` sets `Cache-Control: no-store, max-age=0` |
| `blender_sessions.py` | `register()` saves a lightweight manifest to `sessions/_registry.json` in GCS; `load_registry()` restores it on hub startup |
| `main.py` | `@app.on_event("startup")` calls `blender_sessions.load_registry()` so the browser dropdown is pre-populated after a hub restart |
