# A2A: Closing the Sync Loop — Web→Blender Library & Blender→Hub Bulk Import

**Document type:** Agent-to-Agent (A2A) specification  
**Audience:** The Blender addon coding agent  
**Related docs:** `BLENDER_HUB_ADDON.md`, `BLENDER_SESSION_ROBUSTNESS.md`

---

## What this document covers

Two complementary sync directions that are not yet implemented in the addon:

| Direction | Mechanism | Status |
|---|---|---|
| Blender → Hub/GCS | `_sync_library_to_hub()` — bulk import on registration | **Not yet implemented** |
| Hub/GCS → Blender local `Images/` | Save enriched PNG after hub-generated image delivery | **Not yet implemented** |

Implementing both makes every generation — regardless of where it originated — appear in both the hub's web history reel **and** Blender's local generation history panel.

---

## Part 1 — Blender → Hub: Library Sync on Registration

### Goal

When Blender opens a project (or re-registers after a hub restart), walk the session's local `Images/` folder and upload any PNG the hub doesn't already have. The hub deduplicates by embedded `id` and `sha256`, so this is safe to call unconditionally on every registration.

### New endpoint (already live on hub)

```
POST /api/sessions/{session_id}/history/import
Content-Type: image/png
X-Filename: <original filename>
<raw PNG bytes>
```

**Response:**
```json
{ "imported": true,  "generation_id": "uuid", "reason": null }
{ "imported": false, "generation_id": "uuid", "reason": "duplicate_id" }
{ "imported": false, "generation_id": null,   "reason": "duplicate_sha256" }
```

### Add to `hub_client.py`

```python
def import_image(hub_url: str, session_id: str, png_bytes: bytes,
                 filename: str = "import.png") -> dict:
    """
    Import a single PNG into the hub's session history.
    The hub deduplicates by embedded id and sha256 — safe to call repeatedly.
    Returns the server response dict, or {"imported": False, "reason": "network_error"} on failure.
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
```

### Add to `__init__.py` — `_sync_library_to_hub()`

```python
def _sync_library_to_hub(hub_url: str, session_id: str) -> None:
    """
    Walk the session's local Images/ library and import any PNGs the hub
    doesn't already have.  Runs in a daemon thread — never blocks Blender.
    """
    import threading
    from pathlib import Path
    import bpy as _bpy
    from . import hub_client, workspace_setup

    def _run():
        try:
            ctx         = _bpy.context
            library_dir = Path(workspace_setup.get_project_library(ctx)) / "Images"
        except Exception:
            return

        if not library_dir.exists():
            return

        imported = skipped = errors = 0
        for png in sorted(library_dir.glob("*.png")):
            try:
                data   = png.read_bytes()
                result = hub_client.import_image(hub_url, session_id, data, png.name)
                if result.get("imported"):
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"[Hub Client] Sync failed for {png.name}: {e}")

        print(f"[Hub Client] Library sync: {imported} imported, {skipped} skipped, {errors} errors")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
```

### Call site — inside `_do_hub_register()` in `__init__.py`

After the `hub_client.register_session(...)` call, add:

```python
# Kick off background library sync so the hub's history reel stays in sync
# with any images generated while the hub was offline.
if hub_url and not session_id.startswith("unsaved"):
    _sync_library_to_hub(hub_url, session_id)
```

> **Note:** Skip sync for `unsaved_*` sessions — they have no persistent library yet.

---

## Part 2 — Hub → Blender: Save enriched PNG to local `Images/`

### Goal

When the hub delivers a web-generated image to Blender (via the peek/ack polling loop), also save the **hub's metadata-embedded version** of that PNG to Blender's local `Images/` folder. This makes web-generated images appear in Blender's generation history panel.

### How it works

The hub now includes `result_generation_id` in every `peek` response when a result is ready:

```json
{
  "exists":               true,
  "has_result":           true,
  "result_ts":            1746468231.4,
  "result_filename":      "ComfyUI_03431_.png",
  "result_subfolder":     "",
  "result_type":          "output",
  "result_generation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

`result_generation_id` is the UUID of the hub's GCS record — the PNG at that path has `StyleEngine:config` fully embedded (model, prompt, sources, lineage, sha256, etc.).

### New endpoint to use

```
GET /api/sessions/{session_id}/history/{generation_id}/image
→ 307 redirect to a GCS signed URL for the full-res enriched PNG
```

`urllib.request` follows 307 redirects automatically — no extra code needed.

### Add to `hub_client.py`

```python
def download_enriched_png(hub_url: str, session_id: str,
                           generation_id: str, timeout: int = 30) -> bytes:
    """
    Download the hub's metadata-embedded PNG for a generation.
    The PNG contains a StyleEngine:config iTXt chunk with full lineage.
    Returns raw bytes, or b'' on any error.
    """
    try:
        url = f"{hub_url}/api/sessions/{session_id}/history/{generation_id}/image"
        req = urllib.request.Request(
            url, headers={"User-Agent": "StyleEngine-Blender/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"[Hub Client] download_enriched_png failed ({generation_id}): {e}")
        return b""
```

### Modify `hub_polling.py` — `_on_result_ready()`

After writing `current_ai.png` and reloading the image, add a background thread that saves the enriched PNG to the local library:

```python
def _on_result_ready(hub_url: str, session_id: str, result: dict):
    """Download the generated image from the hub, write to disk, then reload in Blender."""
    try:
        filename  = result.get("result_filename", "")
        subfolder = result.get("result_subfolder", "")
        img_type  = result.get("result_type", "output")
        gen_id    = result.get("result_generation_id", "")

        if not filename:
            print("[Hub Polling] Empty filename in result — skipping")
            return

        # ── Step 1: write current_ai.png (existing behaviour, unchanged) ──
        data = hub_client.download_result_image(hub_url, filename, subfolder, img_type)
        ctx = bpy.context
        ai_path = workspace_setup.get_active_ai_output_path(ctx)
        Path(ai_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ai_path).write_bytes(data)
        workspace_setup.reload_ai_image(ctx)

        print(f"[Hub Polling] ✓ New image from hub ({filename}) — reloaded current_ai.png")

        for window in ctx.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        # ── Step 2: save enriched PNG to local Images/ library ──────────
        if gen_id:
            import threading
            def _save_to_library():
                _save_enriched_to_library(hub_url, session_id, gen_id)
            threading.Thread(target=_save_to_library, daemon=True).start()

    except Exception as e:
        print(f"[Hub Polling] Reload error: {e}")


def _save_enriched_to_library(hub_url: str, session_id: str, gen_id: str) -> None:
    """
    Fetch the hub's metadata-embedded PNG and save it to the local Images/ folder.
    Skips silently if the file already exists or if the library path is unavailable.
    """
    try:
        import bpy as _bpy
        from . import workspace_setup, hub_client
        from pathlib import Path

        # Resolve the project library Images/ folder
        ctx         = _bpy.context
        library_dir = Path(workspace_setup.get_project_library(ctx)) / "Images"
        library_dir.mkdir(parents=True, exist_ok=True)

        dest = library_dir / f"{gen_id}.png"
        if dest.exists():
            return   # already saved (e.g. from a previous run)

        png_bytes = hub_client.download_enriched_png(hub_url, session_id, gen_id)
        if not png_bytes:
            return

        dest.write_bytes(png_bytes)
        print(f"[Hub Polling] ✓ Saved hub generation to library: {dest.name}")

    except Exception as e:
        print(f"[Hub Polling] _save_enriched_to_library error: {e}")
```

> **Why a daemon thread?** `urllib.request` is blocking. Running it inside the timer callback would freeze Blender's UI for the duration of the download. The `bpy.context` snapshot is taken on the main thread before handing off; `workspace_setup.get_project_library` only needs the context to resolve the path and is safe to call before the thread starts.

---

## Summary of required addon changes

| File | Change |
|---|---|
| `hub_client.py` | Add `import_image()` and `download_enriched_png()` |
| `__init__.py` | Add `_sync_library_to_hub()`, call it inside `_do_hub_register()` after registration |
| `hub_polling.py` | In `_on_result_ready()`, after current_ai reload, spawn thread calling `_save_enriched_to_library()` |

---

## Hub-side changes already implemented (FYI)

These are done — the addon only needs the above:

| Component | Change |
|---|---|
| `blender_sessions.py` | `notify_result()` now accepts `generation_id` param; `peek()` now returns `result_generation_id` |
| `main.py` | GCS save is now done **before** `notify_result()` so `gen_id` is always populated when Blender polls |

---

## End-to-end flow after these changes

```
Web UI generates image
  → Hub saves enriched PNG to GCS  (gen_id = "abc-123")
  → Hub calls notify_result(..., generation_id="abc-123")
  → Blender polls peek()  → { has_result: true, result_generation_id: "abc-123" }
  → Blender downloads raw PNG via /api/comfy/view  → writes temp/current_ai.png
  → Blender reloads viewport  (immediate feedback)
  → Background thread: GET /api/sessions/{id}/history/abc-123/image
      → 307 → GCS signed URL → enriched PNG bytes
      → Written to Images/abc-123.png
  → Image now appears in Blender's local generation history panel  ✓

Blender opens old project / hub restarts
  → _do_hub_register() called
  → _sync_library_to_hub() walks Images/*.png
      → POST /api/sessions/{id}/history/import for each PNG
      → Hub deduplicates by id/sha256  (no duplicates ever created)
  → Hub history reel is fully in sync with local library  ✓
```
