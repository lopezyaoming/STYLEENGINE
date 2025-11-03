# ================================================================
#    Style Engine - Blender Add-on
#    Main initialization file
# ================================================================

bl_info = {
    "name": "Style Engine",
    "author": "Spiri Bros Co",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Style Engine",
    "description": "In-house AI Generation integration for Blender Workflows",
    "category": "3D View",
}

import bpy
import sys
import os

# Get addon directory - this MUST point to the styleengine folder
# __file__ should be: .../addons/styleengine/__init__.py
# addon_dir should be: .../addons/styleengine
addon_dir = os.path.dirname(os.path.abspath(__file__))

# DEBUG: Print paths to understand what's happening
print(f"[Style Engine] DEBUG: __file__ = {__file__}")
print(f"[Style Engine] DEBUG: os.path.abspath(__file__) = {os.path.abspath(__file__)}")
print(f"[Style Engine] DEBUG: addon_dir = {addon_dir}")

# Import modules with robust fallback for macOS Blender 4.5+
try:
    # Try standard relative imports first (works on most systems)
    from . import ui_panel
    from . import prefs
    from . import workspace_setup
    from . import runcomfy_client
    from . import runcomfy_deployment
    from . import runcomfy_polling
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
        raise RuntimeError(
            f"[Style Engine] Addon directory path is incorrect!\n"
            f"  Directory: {addon_dir}\n"
            f"  Missing files: {missing_files}\n"
            f"  This usually means the ZIP structure is wrong."
        )
    
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
    runcomfy_deployment = load_module("runcomfy_deployment")
    runcomfy_polling = load_module("runcomfy_polling")
    
    print(f"[Style Engine] All modules loaded successfully!")

# List of modules to register
modules = [
    prefs,
    workspace_setup,
    ui_panel,
]

def register():
    """Register all classes and properties."""
    for module in modules:
        module.register()

def unregister():
    """Unregister all classes and properties."""
    # Cleanup RunComfy poller
    runcomfy_polling.cleanup_poller()
    
    # Unregister modules
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()

