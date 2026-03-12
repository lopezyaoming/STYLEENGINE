# ================================================================
#    Style Engine - HeavyPoly Integration
#    Paratrooper-style injection into HeavyPoly's pie menus
#    Self-contained, no HeavyPoly modifications required
# ================================================================

import bpy
from bpy.types import Menu, Operator


# ----------------------------------------------------------------
# Quick AI Operators for HeavyPoly Pies
# ----------------------------------------------------------------

class SE_OT_render_ai_passes_quick(Operator):
    """Render AI vision passes (depth + AO) from current view"""
    bl_idname = "style_engine.render_ai_passes_quick"
    bl_label = "Render AI Passes"
    bl_description = "Quick render combined pass for AI generation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # Import workspace_setup to access rendering
            from . import workspace_setup
            
            # Render the passes (combined pass using Workbench)
            workspace_setup.render_passes(context)
            
            self.report({'INFO'}, "AI pass rendered!")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Render failed: {e}")
            return {'CANCELLED'}


class SE_OT_generate_ai_quick(Operator):
    """Render passes and generate AI texture in one click"""
    bl_idname = "style_engine.generate_ai_quick"
    bl_label = "Generate AI"
    bl_description = "Render combined pass and generate AI texture from current view"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # Import workspace_setup
            from . import workspace_setup
            
            # Render combined pass first (using Workbench for speed)
            workspace_setup.render_passes(context)
            
            # Then trigger cloud generation (direct function call)
            workspace_setup.generate_ai_image_cloud(context)
            
            self.report({'INFO'}, "AI generation started!")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Generation failed: {e}")
            return {'CANCELLED'}


class SE_OT_refine_current_image(Operator):
    """Refine current_ai.png without re-rendering the 3D viewport"""
    bl_idname = "style_engine.refine_current_image"
    bl_label = "Refine Current Image"
    bl_description = (
        "Use the current AI image as input instead of re-rendering. "
        "Iteratively refine an existing generation or uploaded image."
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        from pathlib import Path
        import tempfile, os
        temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "temp"
        # Try to resolve via workspace_setup for robustness
        try:
            from . import workspace_setup
            td = workspace_setup.get_temp_directory(context)
            return (td / "current_ai.png").exists()
        except Exception:
            return (temp_dir / "current_ai.png").exists()

    def execute(self, context):
        try:
            from . import workspace_setup
            workspace_setup.generate_ai_image_cloud(context, refine_mode=True)
            self.report({'INFO'}, "Refine started!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Refine failed: {e}")
            return {'CANCELLED'}


# ----------------------------------------------------------------
# Paratrooper Injection into HeavyPoly's Z Pie (Shading)
# ----------------------------------------------------------------

def inject_into_heavypoly_shading(self, context):
    """
    PARATROOPER INJECTION into HP_MT_pie_shading (Z key).
    Adds Style Engine AI rendering to the RIGHT side of the pie.
    
    This function is dynamically appended to HeavyPoly's draw() method.
    Zero modifications to HeavyPoly's code required!
    """
    layout = self.layout
    
    # Add to the RIGHT side (currently shows as empty split in HeavyPoly)
    split = layout.split()
    col = split.column(align=True)
    
    # Get style engine properties for autogenerate toggle
    try:
        style_props = context.scene.style_engine
    except:
        style_props = None
    
    # 1. Generate Image - ONE-SHOT (large, on top)
    row = col.row(align=True)
    row.scale_y = 2.0  # Large button
    row.operator("style_engine.generate_ai_quick", 
                text="Generate Image", 
                icon='IMAGE_DATA')
    
    # 2. Autogenerate - CONTINUOUS TOGGLE (smaller, below)
    if style_props:
        row = col.row(align=True)
        row.scale_y = 1.2  # Smaller than main button
        row.prop(style_props, "auto_generate", 
                text="Autogenerate", 
                icon='FILE_REFRESH', 
                toggle=True)


# ----------------------------------------------------------------
# Registration
# ----------------------------------------------------------------

classes = (
    SE_OT_render_ai_passes_quick,
    SE_OT_generate_ai_quick,
    SE_OT_refine_current_image,
)

# Store draw handlers for clean unregister
_draw_handlers = []


def register():
    """
    Register operators and optionally integrate with HeavyPoly.
    Operators are ALWAYS registered (needed by pie menu).
    HeavyPoly pie injection only happens if enable_heavypoly_compatibility is ON.
    """
    # ALWAYS register our operators (pie_menu.py needs them!)
    print("[Style Engine] Registering quick operators...")
    
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            print(f"[Style Engine]   ✓ {cls.bl_idname}")
        except Exception as e:
            print(f"[Style Engine]   ✗ Failed to register {cls.bl_idname}: {e}")
    
    print("[Style Engine] Quick operators registered")
    
    # Check if HeavyPoly compatibility is enabled for pie injection
    try:
        from . import utils
        if not utils.is_heavypoly_compatible():
            return  # Skip HeavyPoly integration but operators are still registered
    except Exception as e:
        print(f"[Style Engine] Could not check HeavyPoly compatibility: {e}")
        return
    
    print("[Style Engine] 🪂 HeavyPoly integration mode activated")
    
    # PARATROOPER DROP: Inject into HeavyPoly's Z pie (Shading)
    try:
        if hasattr(bpy.types, 'HP_MT_pie_shading'):
            bpy.types.HP_MT_pie_shading.append(inject_into_heavypoly_shading)
            _draw_handlers.append(('HP_MT_pie_shading', inject_into_heavypoly_shading))
            print("[Style Engine] ✅ Infiltrated HeavyPoly's Z (Shading) pie")
        else:
            print("[Style Engine] ℹ️  HeavyPoly not detected, pie injection skipped")
    
    except Exception as e:
        print(f"[Style Engine] ⚠️  Could not inject into HeavyPoly pie: {e}")
    
    print("[Style Engine] 🎯 HeavyPoly integration ready!")


def unregister():
    """
    Clean unregister - removes HeavyPoly injection and unregisters operators.
    """
    from . import utils
    
    # Remove HeavyPoly pie injection if it was active
    if utils.is_heavypoly_compatible():
        print("[Style Engine] 🪂 Removing HeavyPoly integrations...")
        
        # Remove our draw handlers from HeavyPoly's pies
        for menu_name, handler in _draw_handlers:
            try:
                menu_class = getattr(bpy.types, menu_name, None)
                if menu_class:
                    menu_class.remove(handler)
                    print(f"[Style Engine] ✅ Removed from {menu_name}")
            except Exception as e:
                print(f"[Style Engine] ⚠️  Could not remove from {menu_name}: {e}")
        
        _draw_handlers.clear()
    
    # ALWAYS unregister our operators (they were always registered)
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass


if __name__ == "__main__":
    register()

