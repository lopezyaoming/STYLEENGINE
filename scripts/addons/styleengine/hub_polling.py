"""
Hub polling — receives generated images from the Style Engine Hub.
Uses bpy.app.timers for non-blocking periodic polling.
The hub writes the image directly to current_ai_path on disk;
this module just detects the signal and triggers the Blender reload.
"""
import bpy
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
    return hub_client.get_session_id(bpy.data.filepath if bpy.data.is_saved else None)


def _poll_tick():
    """Timer callback — runs on Blender's main thread every POLL_INTERVAL seconds."""
    if not HubPollerState.is_polling:
        return None  # stop timer

    try:
        prefs      = _get_prefs()
        hub_url    = getattr(prefs, "hub_url", "http://127.0.0.1:8000").rstrip("/")
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


def _on_result_ready(hub_url: str, session_id: str, peek_data: dict):
    """
    Called on the main thread when the hub signals a new result.

    Step 1 — download the raw image via /api/comfy/view, write to current_ai.png,
              and reload the Blender viewport.
    Step 2 — if a result_generation_id is present, spawn a background thread to
              fetch the hub's metadata-embedded PNG and save it to the local
              Images/ library (so it appears in the history panel).
    """
    try:
        ctx        = bpy.context
        ai_path    = workspace_setup.get_active_ai_output_path(ctx)

        filename  = (peek_data.get("result_filename")
                     or peek_data.get("filename")
                     or peek_data.get("image_filename"))
        subfolder = peek_data.get("result_subfolder", "")
        img_type  = peek_data.get("result_type", "output")
        gen_id    = peek_data.get("result_generation_id", "")

        if filename:
            print(f"[Hub Polling] Downloading result: {filename}")
            ok = hub_client.download_result_image(hub_url, filename, str(ai_path))
            if not ok:
                print("[Hub Polling] ⚠ Download failed — will try refresh from existing disk file")
        else:
            print("[Hub Polling] No filename in peek response — refreshing from disk")

        workspace_setup.refresh_ai_image()
        print("[Hub Polling] ✓ New image from hub — reloaded current_ai.png")

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        # ── Step 2: save enriched PNG to local Images/ library ───────────
        # Check cloud sync toggle before spawning the thread
        if gen_id:
            try:
                cloud_sync = getattr(
                    ctx.scene.style_engine_props, "hub_cloud_sync", True
                )
            except Exception:
                cloud_sync = True
            if cloud_sync:
                import threading
                threading.Thread(
                    target=_save_enriched_to_library,
                    args=(hub_url, session_id, gen_id),
                    daemon=True,
                ).start()

    except Exception as e:
        print(f"[Hub Polling] Reload error: {e}")
        import traceback
        traceback.print_exc()


def _save_enriched_to_library(hub_url: str, session_id: str, gen_id: str) -> None:
    """
    Fetch the hub's metadata-embedded PNG and save it to the local Images/ folder.
    Skips silently if the file already exists.  Runs in a daemon thread.
    """
    try:
        import bpy as _bpy
        from pathlib import Path as _Path
        from . import workspace_setup as _ws

        library_dir = _Path(_ws.get_project_library()) / "Images"
        library_dir.mkdir(parents=True, exist_ok=True)

        dest = library_dir / f"{gen_id}.png"
        if dest.exists():
            return

        png_bytes = hub_client.download_enriched_png(hub_url, session_id, gen_id)
        if not png_bytes:
            return

        dest.write_bytes(png_bytes)
        print(f"[Hub Polling] ✓ Saved hub generation to library: {dest.name}")

    except Exception as e:
        print(f"[Hub Polling] _save_enriched_to_library error: {e}")


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
