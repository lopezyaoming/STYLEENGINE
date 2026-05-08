"""
Hub polling — receives generated images from the Style Engine Hub.
Uses bpy.app.timers for non-blocking periodic polling.

Cross-machine design: the hub runs on a separate machine. Blender downloads
image bytes from the hub rather than the hub writing to Blender's disk.
"""
import math
import bpy
from pathlib import Path
from . import hub_client
from . import workspace_setup

POLL_INTERVAL = 2.0   # seconds


class HubPollerState:
    is_polling         = False
    last_result_ts     = None   # float — timestamp of last acknowledged result
    import_in_progress = False  # guard against dispatching the same batch twice
    _last_imported_ids: set = set()  # avoid reprocessing on ack_import failure

    @classmethod
    def reset(cls):
        cls.is_polling         = False
        cls.last_result_ts     = None
        cls.import_in_progress = False
        cls._last_imported_ids = set()


def _get_prefs():
    return bpy.context.preferences.addons["styleengine"].preferences


def _session_id() -> str:
    """Return the active session ID. Prefers stored scene property."""
    sid = hub_client.get_stored_session_id()
    if sid:
        return sid
    # Legacy fallback for files that pre-date the stored property
    if bpy.data.is_saved:
        return hub_client.get_session_id(bpy.data.filepath)
    return ""


def _poll_tick():
    """Timer callback — runs on Blender's main thread every POLL_INTERVAL seconds."""
    if not HubPollerState.is_polling:
        return None  # stop timer

    try:
        prefs      = _get_prefs()
        hub_url    = getattr(prefs, "hub_url", "http://127.0.0.1:8000").rstrip("/")
        session_id = _session_id()

        if not session_id:
            return POLL_INTERVAL  # no session connected yet — keep timer alive

        result = hub_client.peek_result(hub_url, session_id)

        # ── has_result: single image delivered by hub generate ────────────
        if result.get("has_result"):
            ts = result.get("result_ts")
            if ts != HubPollerState.last_result_ts:
                HubPollerState.last_result_ts = ts
                _on_result_ready(hub_url, session_id, result)
                hub_client.ack_result(hub_url, session_id)

        # ── pending_import: bulk hub→Blender push ─────────────────────────
        pending = result.get("pending_import", [])
        if pending and not HubPollerState.import_in_progress:
            new_ids = [g for g in pending
                       if g not in HubPollerState._last_imported_ids]
            if new_ids:
                _on_pending_import(hub_url, session_id, new_ids)

    except Exception as e:
        print(f"[Hub Polling] Tick error: {e}")

    return POLL_INTERVAL


def _parse_aspect_ratio(ratio_str: str):
    """
    Parse "W:H" strings such as "1:1", "16:9", "9:16", "4:3".
    Returns (w_parts, h_parts) as ints, or None if unparseable.
    """
    try:
        w, h = ratio_str.strip().split(":")
        return int(w), int(h)
    except Exception:
        return None


def _apply_aspect_ratio_to_camera(ratio_str: str) -> None:
    """
    Adjust scene render resolution to match ratio_str.

    Preserves total pixel area so render time is unchanged.
    Rounds to nearest 8 px for GPU alignment.
    Only touches resolution_x/y — no camera FOV, sensor, percentage, or other
    scene properties are modified.
    Silently skips if the ratio is missing, unparseable, or already correct.
    """
    parsed = _parse_aspect_ratio(ratio_str)
    if parsed is None:
        print(f"[Hub Polling] Unknown aspect ratio '{ratio_str}' — skipping camera adjust")
        return

    w_ratio, h_ratio = parsed
    scene  = bpy.context.scene
    cur_w  = scene.render.resolution_x
    cur_h  = scene.render.resolution_y
    area   = cur_w * cur_h

    new_h = int(math.sqrt(area * h_ratio / w_ratio))
    new_w = int(new_h * w_ratio / h_ratio)
    new_w = max(8, round(new_w / 8) * 8)
    new_h = max(8, round(new_h / 8) * 8)

    if new_w == cur_w and new_h == cur_h:
        return  # already correct

    scene.render.resolution_x = new_w
    scene.render.resolution_y = new_h
    print(f"[Hub Polling] Camera adjusted {cur_w}×{cur_h} → {new_w}×{new_h} ({ratio_str})")


def _on_result_ready(hub_url: str, session_id: str, peek_data: dict):
    """
    Called on the main thread when the hub signals a new result.

    Step 1 — download the raw image via /api/comfy/view, write to current_ai.png.
    Step 1b — fetch the generation config and adjust render resolution to match
               the hub's aspectRatio so the viewport is never letterboxed.
    Step 2 — reload the Blender viewport.
    Step 3 — if result_generation_id is present and cloud sync is enabled,
              spawn a background thread to fetch the enriched PNG and save it
              to the local Images/ library.
    """
    try:
        ctx     = bpy.context
        ai_path = workspace_setup.get_active_ai_output_path(ctx)

        filename  = (peek_data.get("result_filename")
                     or peek_data.get("filename")
                     or peek_data.get("image_filename"))
        gen_id    = peek_data.get("result_generation_id", "")

        if filename:
            print(f"[Hub Polling] Downloading result: {filename}")
            ok = hub_client.download_result_image(hub_url, filename, str(ai_path))
            if not ok:
                print("[Hub Polling] ⚠ Download failed — will try refresh from existing disk file")
        else:
            print("[Hub Polling] No filename in peek response — refreshing from disk")

        # ── Step 1b: match render resolution to the hub generation's aspect ratio ──
        if gen_id:
            config    = hub_client.fetch_generation_config(hub_url, session_id, gen_id)
            ar        = config.get("aspectRatio", "")
            if ar:
                _apply_aspect_ratio_to_camera(ar)

        workspace_setup.refresh_ai_image()
        print("[Hub Polling] ✓ New image from hub — reloaded current_ai.png")

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        # ── Step 2: save enriched PNG to local Images/ library ───────────
        if gen_id:
            try:
                cloud_sync = getattr(
                    ctx.scene.style_engine_props, "hub_cloud_sync", True
                )
            except Exception:
                cloud_sync = True
            # Resolve library path on main thread — bpy.data not safe in thread
            library_dir = ""
            if cloud_sync:
                try:
                    lib = workspace_setup.get_project_library()
                    if lib is not None:
                        library_dir = str(lib / "Images")
                except Exception:
                    library_dir = ""
            if cloud_sync and library_dir:
                import threading
                threading.Thread(
                    target=_save_enriched_to_library,
                    args=(session_id, gen_id, library_dir),
                    daemon=True,
                ).start()

    except Exception as e:
        print(f"[Hub Polling] Reload error: {e}")
        import traceback
        traceback.print_exc()


def _save_enriched_to_library(session_id: str, gen_id: str,
                               library_dir: str) -> None:
    """
    Fetch the hub's metadata-embedded PNG and save it to the local Images/ folder.
    Skips silently if the file already exists.  Runs in a daemon thread.

    `library_dir` and `session_id` must be resolved on the main thread
    before this is called — no bpy.data access is performed here.
    """
    try:
        dest_dir = Path(library_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / f"{gen_id}.png"
        if dest.exists():
            return

        hub_client.download_enriched_png(session_id, gen_id, library_dir)
        print(f"[Hub Polling] ✓ Saved hub generation to library: {gen_id}.png")

    except Exception as e:
        print(f"[Hub Polling] _save_enriched_to_library error: {e}")


def _on_pending_import(hub_url: str, session_id: str,
                       gen_ids: list) -> None:
    """
    Main-thread entry point for a bulk hub→Blender import ("Push to Blender").

    Resolves all bpy paths here (safe), then hands off to a daemon thread.
    After the download, schedules a viewport refresh on the main thread.
    """
    import threading

    blend_path = bpy.data.filepath
    if not blend_path:
        print("[Hub Polling] pending_import skipped — file not saved")
        return

    # Resolve the Images/ folder next to the blend file — safe here on main thread
    images_dir = str(Path(blend_path).parent / "Images")
    HubPollerState.import_in_progress = True

    def _download_batch(sid: str, img_dir: str, ids: list):
        imported  = 0
        first_path = None
        for gen_id in ids:
            try:
                dest = hub_client.download_enriched_png(sid, gen_id, img_dir)
                HubPollerState._last_imported_ids.add(gen_id)
                if first_path is None:
                    first_path = dest
                imported += 1
            except Exception as e:
                print(f"[Hub Polling] Failed to import {gen_id}: {e}")

        print(f"[Hub Polling] Bulk import: {imported}/{len(ids)} downloaded")
        hub_client.ack_import(sid)
        HubPollerState.import_in_progress = False

        # Schedule optional auto-reload on the main thread
        if first_path:
            def _notify():
                try:
                    import bpy as _bpy
                    import shutil, os
                    current_ai = str(
                        workspace_setup.get_active_ai_output_path(_bpy.context)
                    )
                    os.makedirs(os.path.dirname(current_ai), exist_ok=True)
                    shutil.copy2(first_path, current_ai)
                    workspace_setup.refresh_ai_image()
                    print(f"[Hub Polling] Auto-loaded first imported image")
                except Exception as _e:
                    print(f"[Hub Polling] Auto-reload failed (non-fatal): {_e}")
                return None
            bpy.app.timers.register(_notify, first_interval=0.0)

    threading.Thread(
        target=_download_batch,
        args=(session_id, images_dir, list(gen_ids)),
        daemon=True,
    ).start()


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
