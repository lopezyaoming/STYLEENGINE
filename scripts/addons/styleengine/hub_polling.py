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

    The hub stores the image server-side and Blender must download it via
    GET /api/comfy/view?filename=<name> before reloading the datablock.

    peek_data may contain 'filename' (or 'result_filename') with the name of
    the generated image on the hub's ComfyUI output directory.
    Falls back to a plain disk-reload if no filename is provided (e.g. the hub
    wrote directly to current_ai_path as per the original spec).
    """
    try:
        # Resolve the local path where current_ai.png lives
        ctx        = bpy.context
        ai_path    = workspace_setup.get_active_ai_output_path(ctx)

        # Look for the filename in common field names the hub might use
        filename = (peek_data.get("filename")
                    or peek_data.get("result_filename")
                    or peek_data.get("image_filename"))

        if filename:
            print(f"[Hub Polling] Downloading result: {filename}")
            ok = hub_client.download_result_image(hub_url, filename, str(ai_path))
            if not ok:
                print("[Hub Polling] ⚠ Download failed — will try refresh from existing disk file")
        else:
            # Hub wrote directly to disk (original spec fallback)
            print("[Hub Polling] No filename in peek response — refreshing from disk")

        workspace_setup.refresh_ai_image()
        print("[Hub Polling] ✓ New image from hub — reloaded current_ai.png")

        # Belt-and-suspenders redraw (refresh_ai_image already tags viewports)
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

    except Exception as e:
        print(f"[Hub Polling] Reload error: {e}")
        import traceback
        traceback.print_exc()


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
