# ================================================================
#    Style Engine - Blender Add-on
#    Main initialization file
# ================================================================

bl_info = {
    "name": "Style Engine",
    "author": "Ian Worrel, Juan Jose Lopez",
    "version": (0, 6, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Style Engine",
    "description": "In-house AI Generation integration for Blender Workflows with LoRa and UV Texture support",
    "category": "3D View",
}

import bpy
import sys
import os

# Get addon directory - this MUST point to the styleengine folder
# ROBUST PATH DETECTION for macOS Blender 4.5+ installation quirks
addon_dir = os.path.dirname(os.path.abspath(__file__))

# CRITICAL: Ensure cross-platform path separators (always use os.path.join, never manual slashes)
print(f"[Style Engine] Initial path detection:")
print(f"  __file__ = {__file__}")
print(f"  addon_dir = {addon_dir}")

# During macOS installation, __file__ might resolve to the parent addons directory
# Check if we're actually in the styleengine directory by looking for our modules
utils_path = os.path.join(addon_dir, 'utils.py')
utils_exists = os.path.exists(utils_path)
print(f"  Checking: {utils_path} → {utils_exists}")

if not utils_exists:
    print(f"[Style Engine] ⚠️  Path correction needed - not in styleengine directory")
    
    # Strategy 1: Look for styleengine subdirectory
    potential_addon_dir = os.path.join(addon_dir, 'styleengine')
    potential_utils = os.path.join(potential_addon_dir, 'utils.py')
    print(f"  Strategy 1: Checking {potential_utils}")
    
    if os.path.exists(potential_utils):
        addon_dir = potential_addon_dir
        print(f"[Style Engine] ✓ Corrected to: {addon_dir}")
    else:
        # Strategy 2: Use __name__ to find the actual addon directory
        if __name__ != '__main__':
            addon_name = __name__.split('.')[0] if '.' in __name__ else __name__
            print(f"  Strategy 2: Using __name__ = '{__name__}' → addon_name = '{addon_name}'")
            
            potential_addon_dir = os.path.join(addon_dir, addon_name)
            potential_utils = os.path.join(potential_addon_dir, 'utils.py')
            print(f"  Checking: {potential_utils}")
            
            if os.path.exists(potential_utils):
                addon_dir = potential_addon_dir
                print(f"[Style Engine] ✓ Corrected using __name__: {addon_dir}")
        
        # Strategy 3: List directory contents to help debug
        if not os.path.exists(os.path.join(addon_dir, 'utils.py')):
            print(f"[Style Engine] ⚠️  Path correction failed!")
            print(f"  Final addon_dir: {addon_dir}")
            try:
                contents = os.listdir(addon_dir)
                print(f"  Directory contains: {contents[:10]}")  # First 10 items
            except:
                print(f"  (Could not list directory)")

# FINAL DEBUG OUTPUT
print(f"[Style Engine] Final addon_dir: {addon_dir}")
print(f"[Style Engine] utils.py exists: {os.path.exists(os.path.join(addon_dir, 'utils.py'))}")

# Import modules with robust fallback for macOS Blender 4.5+
try:
    # Try standard relative imports first (works on most systems)
    from . import ui_panel
    from . import prefs
    from . import workspace_setup
    from . import runcomfy_client
    from . import runcomfy_server_client
    from . import runcomfy_server_manager
    from . import runcomfy_deployment
    from . import runcomfy_polling
    from . import progress_bar
    from . import heavypoly_integration
    from . import pie_menu
    from . import trellis_client
    from . import asset_mode
    from . import hub_client   # noqa: F401 (no classes to register)
    from . import hub_polling
except (ImportError, ValueError) as e:
    # Fallback for strict import systems (macOS during installation)
    print(f"[Style Engine] Using fallback imports (macOS compatibility mode)")
    print(f"[Style Engine] Addon directory: {addon_dir}")
    print(f"[Style Engine] Import error: {e}")
    
    import importlib.util
    import types
    
    # Verify addon_dir is correct (should contain art_director.py, utils.py, etc.)
    expected_files = ['art_director.py', 'utils.py', 'ui_panel.py', 'prefs.py']
    missing_files = [f for f in expected_files if not os.path.exists(os.path.join(addon_dir, f))]
    
    if missing_files:
        # Create detailed error with troubleshooting
        error_msg = [
            "[Style Engine] ❌ Addon path verification failed!",
            "",
            f"Current directory: {addon_dir}",
            f"Missing files: {missing_files}",
            "",
            "Possible causes:",
            "1. OLD VERSION STILL INSTALLED - Most likely cause!",
            "   → Fully uninstall addon from Blender preferences",
            "   → Restart Blender",
            "   → Reinstall fresh styleengine.zip",
            "",
            "2. ZIP structure is incorrect",
            "   → ZIP should contain: styleengine/art_director.py, styleengine/utils.py, etc.",
            "   → Run: python validate_package.py styleengine.zip",
            "",
            "3. macOS/Blender installation quirk",
            "   → Path separators or permissions issue",
            "",
            "Debug info:",
            f"  __file__ = {__file__}",
            f"  __name__ = {__name__}",
            f"  addon_dir = {addon_dir}",
        ]
        
        try:
            contents = os.listdir(addon_dir)
            error_msg.append(f"  Directory contents (first 10): {contents[:10]}")
        except Exception as list_err:
            error_msg.append(f"  (Could not list directory: {list_err})")
        
        raise RuntimeError("\n".join(error_msg))
    
    # Create the package module if it doesn't exist
    if 'styleengine' not in sys.modules:
        pkg = types.ModuleType('styleengine')
        pkg.__package__ = 'styleengine'
        pkg.__path__ = [addon_dir]
        pkg.__file__ = __file__
        sys.modules['styleengine'] = pkg
        print(f"[Style Engine] Created package: styleengine")
    
    def load_module(module_name):
        """Load a module by its file path with full package context."""
        full_name = f"styleengine.{module_name}"
        file_path = os.path.join(addon_dir, f"{module_name}.py")
        
        print(f"[Style Engine] Loading module: {full_name} from {file_path}")
        
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"[Style Engine] Module file not found!\n"
                f"  Expected: {file_path}\n"
                f"  Addon directory: {addon_dir}\n"
                f"  Check ZIP structure: should have styleengine/ folder at root"
            )
        
        # Check if already loaded
        if full_name in sys.modules:
            print(f"[Style Engine] Module {full_name} already loaded")
            return sys.modules[full_name]
        
        spec = importlib.util.spec_from_file_location(full_name, file_path)
        module = importlib.util.module_from_spec(spec)
        
        # Register BEFORE executing to allow circular/relative imports
        sys.modules[full_name] = module
        
        try:
            spec.loader.exec_module(module)
            print(f"[Style Engine] Successfully loaded: {full_name}")
        except Exception as exec_error:
            # If execution fails, remove from sys.modules
            if full_name in sys.modules:
                del sys.modules[full_name]
            print(f"[Style Engine] Failed to load {full_name}: {exec_error}")
            raise
        
        return module
    
    # Load all required modules (utils must be loaded first as other modules import it)
    utils = load_module("utils")
    ui_panel = load_module("ui_panel")
    prefs = load_module("prefs")
    workspace_setup = load_module("workspace_setup")
    runcomfy_client = load_module("runcomfy_client")
    runcomfy_server_client = load_module("runcomfy_server_client")
    runcomfy_server_manager = load_module("runcomfy_server_manager")
    runcomfy_deployment = load_module("runcomfy_deployment")
    runcomfy_polling = load_module("runcomfy_polling")
    heavypoly_integration = load_module("heavypoly_integration")
    pie_menu = load_module("pie_menu")
    trellis_client = load_module("trellis_client")
    asset_mode = load_module("asset_mode")
    hub_client = load_module("hub_client")
    hub_polling = load_module("hub_polling")

    print(f"[Style Engine] All modules loaded successfully!")

# List of modules to register
modules = [
    prefs,
    workspace_setup,
    ui_panel,
    asset_mode,       # Asset Mode / Scene Mode system
    progress_bar,     # Progress bridge polling system
    heavypoly_integration,  # HeavyPoly Z pie injection (paratrooper mode!)
    pie_menu,         # Main Style Engine pie menus
    hub_polling,      # Hub image delivery polling
]

def _sync_library_to_hub(hub_url: str, session_id: str) -> None:
    """
    Walk the session's local Images/ library and upload any PNGs the hub
    doesn't already have.  The hub deduplicates by embedded id and sha256,
    so this is safe to call unconditionally on every registration.

    The library path is resolved on the main thread before the daemon thread
    is spawned — bpy.data must never be accessed inside the thread.
    """
    import threading
    from pathlib import Path as _Path
    from . import hub_client as _hc, workspace_setup as _ws

    # ── Resolve path on the main thread ──────────────────────────────────
    try:
        lib = _ws.get_project_library()
        if lib is None:
            return
        library_dir = _Path(lib) / "Images"
    except Exception:
        return

    def _run(library_dir: _Path):
        if not library_dir.exists():
            return

        imported = skipped = errors = 0
        for png in sorted(library_dir.glob("*.png")):
            try:
                data   = png.read_bytes()
                result = _hc.import_image(hub_url, session_id, data, png.name)
                if result.get("imported"):
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"[Hub Sync] Failed for {png.name}: {e}")

        print(f"[Hub Sync] Library sync complete: {imported} imported, "
              f"{skipped} skipped, {errors} errors")

    threading.Thread(target=_run, args=(library_dir,), daemon=True).start()


def _do_hub_register():
    """
    Register this Blender session with the Hub.

    With the new session-identity model, registration is a heartbeat for an
    already-established session — it only fires when a stored session ID is
    present in the blend file. Opening or saving an unregistered file produces
    no hub traffic.
    """
    from pathlib import Path
    import bpy as _bpy
    from . import hub_client, workspace_setup

    sid = hub_client.get_stored_session_id()
    if not sid:
        # No session connected to this file yet — nothing to do
        return

    prefs      = _bpy.context.preferences.addons["styleengine"].preferences
    hub_url    = getattr(prefs, "hub_url", "http://127.0.0.1:8000").rstrip("/")
    blend_path = _bpy.data.filepath
    blend_name = Path(blend_path).stem if _bpy.data.is_saved else sid
    try:
        ctx        = _bpy.context
        current_ai = str(workspace_setup.get_active_ai_output_path(ctx))
    except Exception:
        current_ai = ""
    hub_client.register_session(hub_url, sid, blend_name, blend_path, current_ai)

    # Kick off background library sync when cloud sync is enabled
    if hub_url:
        try:
            cloud_sync = getattr(
                _bpy.context.scene.style_engine_props, "hub_cloud_sync", True
            )
        except Exception:
            cloud_sync = True
        if cloud_sync:
            _sync_library_to_hub(hub_url, sid)


def _delayed_hub_register():
    """Register with hub after Blender is fully loaded."""
    try:
        _do_hub_register()
    except Exception as e:
        print(f"[Style Engine] Hub register failed: {e}")
    return None  # don't repeat


def register():
    """Register all classes and properties."""
    for module in modules:
        module.register()

    # Save handler — session migration when .blend is first saved
    if workspace_setup.on_blend_file_saved not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(workspace_setup.on_blend_file_saved)
        print("[Style Engine] ✓ Save handler registered for session migration")

    # Pre-save handler — snapshots scene_subjects_json before the .blend is written
    if workspace_setup.on_blend_file_pre_save not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(workspace_setup.on_blend_file_pre_save)
        print("[Style Engine] ✓ Pre-save handler registered for subjects snapshot")

    # Load handler — reset temp-dir lock whenever a new file is opened
    if workspace_setup.on_blend_file_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(workspace_setup.on_blend_file_loaded)
        print("[Style Engine] ✓ Load handler registered for temp-dir reset")

    # Hub registration — deferred so prefs and workspace are fully ready
    bpy.app.timers.register(_delayed_hub_register, first_interval=2.0)

def unregister():
    """Unregister all classes and properties."""
    # Cleanup RunComfy poller
    runcomfy_polling.cleanup_poller()

    # Unregister save handler
    if workspace_setup.on_blend_file_saved in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(workspace_setup.on_blend_file_saved)
        print("[Style Engine] ✓ Save handler unregistered")

    # Unregister pre-save handler
    if workspace_setup.on_blend_file_pre_save in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(workspace_setup.on_blend_file_pre_save)
        print("[Style Engine] ✓ Pre-save handler unregistered")

    # Unregister load handler
    if workspace_setup.on_blend_file_loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(workspace_setup.on_blend_file_loaded)
        print("[Style Engine] ✓ Load handler unregistered")
    
    # Unregister modules
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()

