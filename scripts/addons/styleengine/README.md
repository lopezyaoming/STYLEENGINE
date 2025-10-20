# Style Engine - Developer Reference

## Quick Start

```python
from . import utils

# Get API credentials
api_token = utils.get_runcomfy_api_token()
user_id = utils.get_runcomfy_user_id()

# Validate credentials before API call
is_valid, error_msg = utils.validate_runcomfy_credentials()
if not is_valid:
    print(f"Error: {error_msg}")
    return

# Get headers for API requests
headers = utils.get_api_headers()
```

## Module Structure

```
styleengine/
├── __init__.py          # Main addon registration
├── prefs.py            # Addon preferences and API configuration
├── ui_panel.py         # Main UI panel and operators
├── utils.py            # Helper functions for API access
└── README.md           # This file
```

## API Credentials Access

### From any operator:

```python
from . import utils

class MyOperator(bpy.types.Operator):
    def execute(self, context):
        # Validate first
        is_valid, error_msg = utils.validate_runcomfy_credentials()
        if not is_valid:
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        # Access credentials
        token = utils.get_runcomfy_api_token()
        user_id = utils.get_runcomfy_user_id()
        
        # Make API call
        # ...
        
        return {'FINISHED'}
```

## Preferences Access

```python
# Get preferences object
prefs = bpy.context.preferences.addons['styleengine'].preferences

# Access preference properties
show_keys = prefs.show_api_keys
use_env = prefs.use_env_vars
```

## Adding New API Services

To add credentials for a new service:

1. **Update `prefs.py`:**

```python
# Add new properties
new_service_api_key: StringProperty(
    name="New Service API Key",
    description="API key for New Service",
    default="",
    subtype='PASSWORD'
)
```

2. **Update the preference UI in `prefs.py`:**

```python
def draw(self, context):
    # ... existing code ...
    
    # Add new service box
    service_box = box.box()
    service_box.label(text="New Service Settings", icon='NETWORK_DRIVE')
    service_box.prop(self, "new_service_api_key")
```

3. **Add utility functions in `utils.py`:**

```python
def get_new_service_api_key():
    """Get the New Service API key."""
    prefs = get_preferences()
    if prefs.use_env_vars:
        env_key = os.environ.get('NEW_SERVICE_API_KEY', '')
        if env_key:
            return env_key
    return prefs.new_service_api_key
```

## Environment Variables

The addon automatically checks for these environment variables:
- `RUNCOMFY_API_TOKEN`
- `RUNCOMFY_USER_ID`

Priority:
1. If "Prefer Environment Variables" is enabled → Use env vars if available
2. Otherwise → Use manually entered values from preferences

## UI Properties

Access scene properties from any operator:

```python
def execute(self, context):
    props = context.scene.style_engine_props
    
    # Access properties
    library_id = props.library_id
    description = props.scene_description
    keywords = props.scene_keywords
    depth = props.depth_influence
    silhouette = props.silhouette
```

## Available Operators

- `style_engine.visualize` - Visualize operation
- `style_engine.create_3d` - Create 3D asset
- `style_engine.render` - Render image
- `style_engine.test_connection` - Test API connection

## Testing

Test your changes:
1. Save your Python files
2. In Blender: Press `F3` → type "Reload Scripts"
3. Or disable/enable the addon in preferences

## Console Output

View debug output:
- **Windows:** Window → Toggle System Console
- **Mac/Linux:** Launch Blender from terminal

```python
print("[Style Engine] Your debug message")
```

## Error Handling Best Practices

```python
def execute(self, context):
    try:
        # Your operation
        result = some_api_call()
        
        if result:
            self.report({'INFO'}, "Operation successful!")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Operation completed with warnings")
            return {'FINISHED'}
            
    except Exception as e:
        self.report({'ERROR'}, f"Operation failed: {str(e)}")
        print(f"[Style Engine] Error details: {e}")
        return {'CANCELLED'}
```

## Useful Blender API References

- Properties: `bpy.props`
- UI Layout: `layout.prop()`, `layout.operator()`, `layout.box()`
- Operators: `bpy.types.Operator`
- Panels: `bpy.types.Panel`
- Preferences: `bpy.types.AddonPreferences`


