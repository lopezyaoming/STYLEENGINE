# ================================================================
#    Style Engine - Blender Add-on
#    Main initialization file
# ================================================================

bl_info = {
    "name": "Style Engine",
    "author": "Ian Worrel, Juan Jose Lopez",
    "version": (0, 3, 5),
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
    from . import heavypoly_integration
    from . import pie_menu
except (ImportError, ValueError) as e:
    # Fallback for strict import systems (macOS during installation)
    print(f"[Style Engine] Using fallback imports (macOS compatibility mode)")
    print(f"[Style Engine] Addon directory: {addon_dir}")
    print(f"[Style Engine] Import error: {e}")
    
    import importlib.util
    import types
    
    # Verify addon_dir is correct (should contain __init__.py, utils.py, etc.)
    expected_files = ['__init__.py', 'utils.py', 'ui_panel.py', 'prefs.py']
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
            "   → ZIP should contain: styleengine/__init__.py, styleengine/utils.py, etc.",
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
    
    print(f"[Style Engine] All modules loaded successfully!")

# List of modules to register
modules = [
    prefs,
    workspace_setup,
    ui_panel,
    heavypoly_integration,  # HeavyPoly Z pie injection (paratrooper mode!)
    pie_menu,  # Main Style Engine pie menu (Shift+E)
]

def register():
    """Register all classes and properties."""
    for module in modules:
        module.register()
    
    # Register save handler for automatic session migration
    if workspace_setup.on_blend_file_saved not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(workspace_setup.on_blend_file_saved)
        print("[Style Engine] ✓ Save handler registered for session migration")

def unregister():
    """Unregister all classes and properties."""
    # Cleanup RunComfy poller
    runcomfy_polling.cleanup_poller()
    
    # Unregister save handler
    if workspace_setup.on_blend_file_saved in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(workspace_setup.on_blend_file_saved)
        print("[Style Engine] ✓ Save handler unregistered")
    
    # Unregister modules
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()

