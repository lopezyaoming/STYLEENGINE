import bpy
import gpu
import blf
import math
from gpu_extras.batch import batch_for_shader

# =============================================================
# VERSION-SAFE HELPERS (FIXED FOR 4.5/5.1)
# =============================================================

def get_builtin_shader():
    # Blender 4.3 consolidated shader names. 
    # 4.5 and 5.1 now use 'UNIFORM_COLOR'
    if bpy.app.version >= (4, 3, 0):
        return 'UNIFORM_COLOR'
    return '2D_UNIFORM_COLOR'

def get_tri_type():
    # Blender 4.3+ consolidated primitive names.
    # 'TRIANGLES' -> 'TRIS'
    if bpy.app.version >= (4, 3, 0):
        return 'TRIS'
    return 'TRIANGLES'

# =============================================================
# MULTI-REGION COSMETICS
# =============================================================

PALETTE = [
    (0.1, 1.0, 0.5), # Green
    (0.1, 0.6, 1.0), # Blue
    (1.0, 0.8, 0.1), # Yellow
    (0.8, 0.2, 1.0), # Purple
    (1.0, 0.5, 0.1), # Orange
]

def get_region_color(obj_id, is_positive=True):
    base = PALETTE[obj_id % len(PALETTE)]
    if is_positive:
        return (*base, 0.9)
    # Relation: 0.5 Value, 0.75 Saturation (approx via direct RGB scale)
    return (base[0]*0.4, base[1]*0.4, base[2]*0.4, 0.9)

# =============================================================
# GPU DRAWING UTILITIES
# =============================================================

def draw_point_shape(shader, x, y, obj_id, radius=8):
    segments = 16
    coords = [(x, y)]
    for i in range(segments + 1):
        angle = i * 2 * math.pi / segments
        coords.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
    
    batch = batch_for_shader(shader, 'TRI_FAN', {"pos": coords})
    shader.bind()
    shader.uniform_float("color", get_region_color(obj_id, True))
    batch.draw(shader)

def draw_x_mark_shape(shader, x, y, obj_id, size=8, t=2):
    s = size
    # Rect 1
    bar1 = [(x-s, y+s-t), (x-s+t, y+s), (x+s, y-s+t), (x-s, y+s-t), (x+s, y-s+t), (x+s-t, y-s)]
    # Rect 2
    bar2 = [(x+s-t, y+s), (x+s, y+s-t), (x-s+t, y-s), (x+s-t, y+s), (x-s, y-s+t), (x-s+t, y-s)]
    
    batch = batch_for_shader(shader, get_tri_type(), {"pos": bar1 + bar2})
    shader.bind()
    shader.uniform_float("color", get_region_color(obj_id, False))
    batch.draw(shader)

def draw_callback_px(op, context):
    shader = gpu.shader.from_builtin(get_builtin_shader())
    gpu.state.blend_set('ALPHA')
    
    for obj_id, points in op.regions.items():
        for pt in points:
            if pt['label'] == 1:
                draw_point_shape(shader, pt['x'], pt['y'], obj_id)
            else:
                draw_x_mark_shape(shader, pt['x'], pt['y'], obj_id)

    # HUD
    blf.size(0, 20)
    blf.color(0, 1, 1, 1, 1)
    blf.position(0, 30, 95, 0)
    blf.draw(0, f"STYLE ENGINE | ACTIVE ID: {op.active_id}")
    
    blf.size(0, 14)
    blf.position(0, 30, 70, 0)
    blf.draw(0, f"Points in group: {len(op.regions[op.active_id])} | B: {bpy.app.version_string}")
    blf.position(0, 30, 50, 0)
    blf.draw(0, "0-9: Set ID | UP/DOWN: Cycle ID | LMB: Add | RMB: Sub")
    blf.position(0, 30, 30, 0)
    blf.draw(0, "BACK_SPACE: Undo | ENTER: Export JSON | ESC: Exit")

# =============================================================
# MODAL OPERATOR
# =============================================================

class STYLE_ENGINE_OT_VisionPicker(bpy.types.Operator):
    bl_idname = "style_engine.vision_picker"
    bl_label = "SAM3 Multi-Region Picker"
    
    _handle = None

    def modal(self, context, event):
        if context.area: context.area.tag_redraw()

        if event.value == 'PRESS':
            if event.type == 'LEFTMOUSE':
                self.regions[self.active_id].append({'x': event.mouse_region_x, 'y': event.mouse_region_y, 'label': 1})
                return {'RUNNING_MODAL'}
            elif event.type == 'RIGHTMOUSE':
                self.regions[self.active_id].append({'x': event.mouse_region_x, 'y': event.mouse_region_y, 'label': 0})
                return {'RUNNING_MODAL'}
            
            # Undo Logic (Fixed for BACK_SPACE)
            elif event.type in {'BACK_SPACE', 'DEL'}:
                if self.regions[self.active_id]:
                    self.regions[self.active_id].pop()
                return {'RUNNING_MODAL'}
            
            # Key mappings for numeric row
            key_map = {'ZERO':0, 'ONE':1, 'TWO':2, 'THREE':3, 'FOUR':4, 'FIVE':5, 'SIX':6, 'SEVEN':7, 'EIGHT':8, 'NINE':9}
            if event.type in key_map:
                self.active_id = key_map[event.type]
                if self.active_id not in self.regions: self.regions[self.active_id] = []
                return {'RUNNING_MODAL'}
            
            elif event.type == 'UP_ARROW':
                self.active_id += 1
                if self.active_id not in self.regions: self.regions[self.active_id] = []
                return {'RUNNING_MODAL'}
            elif event.type == 'DOWN_ARROW':
                self.active_id = max(0, self.active_id - 1)
                return {'RUNNING_MODAL'}

            elif event.type in {'RET', 'NUMPAD_ENTER'}:
                self.export_payload(context)
                self.cleanup(context)
                return {'FINISHED'}
            elif event.type == 'ESC':
                self.cleanup(context)
                return {'CANCELLED'}

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def export_payload(self, context):
        w, h = context.region.width, context.region.height
        final_json = []
        for obj_id, pts in self.regions.items():
            if not pts: continue
            region_data = {"id": obj_id, "positive_points": {"points": [], "labels": []}, "negative_points": {"points": [], "labels": []}, "positive_boxes": {"boxes": [], "labels": []}, "negative_boxes": {"boxes": [], "labels": []}}
            for p in pts:
                norm_coord = [p['x']/w, 1.0-(p['y']/h)]
                if p['label'] == 1:
                    region_data["positive_points"]["points"].append(norm_coord)
                    region_data["positive_points"]["labels"].append(1)
                else:
                    region_data["negative_points"]["points"].append(norm_coord)
                    region_data["negative_points"]["labels"].append(0)
            final_json.append(region_data)
        import json
        print("\n--- STYLE ENGINE UNIVERSAL PAYLOAD ---\n", json.dumps(final_json, indent=4))

    def cleanup(self, context):
        if STYLE_ENGINE_OT_VisionPicker._handle:
            bpy.types.SpaceView3D.draw_handler_remove(STYLE_ENGINE_OT_VisionPicker._handle, 'WINDOW')
            STYLE_ENGINE_OT_VisionPicker._handle = None

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            self.regions = {0: []}
            self.active_id = 0
            args = (self, context)
            STYLE_ENGINE_OT_VisionPicker._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

class STYLE_ENGINE_PT_Main(bpy.types.Panel):
    bl_label = "Style Engine Universal"
    bl_idname = "STYLE_ENGINE_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Style Engine'
    def draw(self, context):
        self.layout.operator("style_engine.vision_picker", icon='VIEW_CAMERA', text="Start Multi-Region Picker")

def register():
    # Force clean registration
    if hasattr(bpy.types, "STYLE_ENGINE_OT_VisionPicker"):
        bpy.utils.unregister_class(STYLE_ENGINE_OT_VisionPicker)
    bpy.utils.register_class(STYLE_ENGINE_OT_VisionPicker)
    bpy.utils.register_class(STYLE_ENGINE_PT_Main)

def unregister():
    bpy.utils.unregister_class(STYLE_ENGINE_OT_VisionPicker)
    bpy.utils.unregister_class(STYLE_ENGINE_PT_Main)

if __name__ == "__main__":
    register()