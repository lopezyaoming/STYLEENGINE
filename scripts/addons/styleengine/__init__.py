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
from pathlib import Path

# Ensure addon directory is in path (helps with macOS compatibility)
addon_dir = Path(__file__).parent
if str(addon_dir) not in sys.path:
    sys.path.insert(0, str(addon_dir))

# Import modules with fallback for macOS/cross-platform compatibility
try:
    from . import ui_panel
    from . import prefs
    from . import workspace_setup
    from . import runcomfy_client
    from . import runcomfy_deployment
    from . import runcomfy_polling
except ImportError as e:
    # Fallback for stricter import systems (macOS Blender 4.4+)
    import importlib
    ui_panel = importlib.import_module(".ui_panel", package=__name__)
    prefs = importlib.import_module(".prefs", package=__name__)
    workspace_setup = importlib.import_module(".workspace_setup", package=__name__)
    runcomfy_client = importlib.import_module(".runcomfy_client", package=__name__)
    runcomfy_deployment = importlib.import_module(".runcomfy_deployment", package=__name__)
    runcomfy_polling = importlib.import_module(".runcomfy_polling", package=__name__)

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

