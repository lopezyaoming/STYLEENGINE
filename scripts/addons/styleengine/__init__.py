# ================================================================
#    Style Engine - Blender Add-on
#    Main initialization file
# ================================================================

bl_info = {
    "name": "Style Engine",
    "author": "Spiri Bros Co",
    "version": (0, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Style Engine",
    "description": "In-house AI Generation integration for Blender Workflows",
    "category": "3D View",
}

import bpy

# Import modules
from . import ui_panel
from . import prefs
from . import workspace_setup

# Import RunComfy modules (no registration needed, just make them available)
from . import runcomfy_client
from . import runcomfy_deployment
from . import runcomfy_polling

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

