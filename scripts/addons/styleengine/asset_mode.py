# ================================================================
#    Style Engine — Asset Mode
#
#    Implements the two-state Asset Mode / Scene Mode system.
#    Asset Mode is a nested "mini Style Engine" scoped to one mesh
#    object: its own camera, isolated viewport, directory hierarchy,
#    and 3D-generation-driven history browser.
# ================================================================

import bpy
import json
import shutil
from pathlib import Path
from mathutils import Vector, Matrix


# ----------------------------------------------------------------
# Module-level state
# ----------------------------------------------------------------

_overlay_handle = None   # SpaceView3D draw handler for the ASSET MODE label
_asset_panel_registered = False  # whether VIEW3D_PT_AssetMode is currently live



# ================================================================
#    Viewport Overlay  —  "ASSET MODE — <object>" text
# ================================================================

def _draw_asset_mode_overlay():
    """Draw the ASSET MODE watermark in the bottom-left of every 3D viewport."""
    try:
        props = bpy.context.scene.style_engine_props
    except Exception:
        return
    if not props.asset_mode:
        return

    import blf
    font_id = 0
    blf.position(font_id, 20, 20, 0)
    blf.size(font_id, 28)
    blf.color(font_id, 1.0, 1.0, 1.0, 0.85)
    try:
        _ov_stack = json.loads(props.asset_mode_stack or "[]")
        _ov_chain = [e["asset_name"] for e in _ov_stack] + [props.current_asset_name]
    except Exception:
        _ov_chain = [props.current_asset_name]
    blf.draw(font_id, f"ASSET MODE  —  {' / '.join(_ov_chain)}")


# ================================================================
#    Helpers
# ================================================================


def _get_asset_camera_name(object_name):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in object_name)
    return f"asset_camera_{safe}"


def _apply_viewport_camera_view(perspective: str):
    """
    Immediate implementation — called from a timer so the operator has already
    returned and Blender has committed the scene.camera change.
    Returns None so the timer does not repeat.
    """
    try:
        scene_cam = bpy.context.scene.camera
        print(f"[Asset Mode] 🎥 _apply_viewport_camera_view: perspective={perspective}  "
              f"scene.camera='{scene_cam.name if scene_cam else 'None'}'")

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    region = next(
                        (r for r in area.regions if r.type == 'WINDOW'), None
                    )
                    if region is None:
                        continue
                    with bpy.context.temp_override(
                        window=window, area=area, region=region
                    ):
                        space = area.spaces[0]
                        prev = space.region_3d.view_perspective
                        space.region_3d.view_perspective = perspective
                        print(f"[Asset Mode]   ↳ area '{area.type}' {prev} → {perspective}")
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not switch viewport perspective: {e}")
        import traceback; traceback.print_exc()
    return None  # non-repeating timer


def _set_viewport_camera_view(perspective: str = 'CAMERA'):
    """
    Defer the viewport switch to the next Blender main-loop tick via a timer.

    When an operator is invoked from a pie menu or N-panel button the drawing
    context is still partially active during execute().  Calling
    region_3d.view_perspective inside that context has no visible effect because
    Blender hasn't finished committing scene.camera yet.  Scheduling through
    bpy.app.timers ensures the switch happens after the operator fully returns.
    """
    bpy.app.timers.register(
        lambda: _apply_viewport_camera_view(perspective),
        first_interval=0.05,
    )


def _compute_object_centroid_and_radius(obj):
    """
    Return (world-space centroid, bounding-sphere radius) for the given object.

    For MESH objects, the real bounding box is used.
    For EMPTY (placeholder) objects, which have no bound_box, the world-space
    location is used as the centroid with a fixed 0.5 m radius so the camera
    still frames them at a reasonable viewing distance.
    """
    if obj.type == 'EMPTY':
        centroid = obj.matrix_world.translation.copy()
        return centroid, 0.5  # sensible default framing for an Empty placeholder

    corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    centroid = sum(corners, Vector()) / 8
    radius = max((c - centroid).length for c in corners)
    radius = max(radius, 0.1)  # guard against degenerate zero-size objects
    return centroid, radius


def _frame_camera_on_object(cam_obj, target_obj):
    """
    Position and orient *cam_obj* so the *target_obj* fills the frame.
    Camera is placed directly in front (+Y axis from centroid in world space).
    EMPTY objects are framed with a fixed 0.5 m bounding radius (see above).
    """
    centroid, radius = _compute_object_centroid_and_radius(target_obj)

    # Derive required distance from focal length and sensor
    cam_data = cam_obj.data
    focal_mm = cam_data.lens          # e.g. 50 mm
    sensor_mm = cam_data.sensor_width  # e.g. 36 mm
    import math
    fov_rad = 2.0 * math.atan(sensor_mm * 0.5 / focal_mm)
    distance = (radius / math.tan(fov_rad * 0.5)) * 1.6  # 1.6× padding

    # Place camera at centroid + (0, -distance, 0), look toward centroid
    cam_position = centroid + Vector((0.0, -distance, 0.0))
    direction = (centroid - cam_position).normalized()

    # Build rotation: camera local -Z looks along direction, local +Y is world +Z
    rot_quat = direction.to_track_quat('-Z', 'Y')
    rot_mat  = rot_quat.to_matrix().to_4x4()
    rot_mat.translation = cam_position
    cam_obj.matrix_world = rot_mat


def _get_or_create_asset_camera(object_name):
    """
    Return the asset camera for *object_name*, creating it if necessary.

    The camera is linked to the scene root collection and then parented to the
    asset's Empty anchor (same name as object_name) so the entire asset hierarchy
    lives under one outliner entry.  No separate asset_cameras collection is used.
    """
    cam_name = _get_asset_camera_name(object_name)
    cam_obj  = bpy.data.objects.get(cam_name)
    if cam_obj is None:
        cam_data      = bpy.data.cameras.new(cam_name)
        cam_data.lens = 50.0
        cam_obj       = bpy.data.objects.new(cam_name, cam_data)

        # Link to scene root so it exists in the scene
        bpy.context.scene.collection.objects.link(cam_obj)

        # Hide from viewport by default — still works as active render/scene camera
        cam_obj.hide_viewport = True

        # Parent to the asset Empty anchor so it sits under it in the outliner
        anchor = bpy.data.objects.get(object_name)
        if anchor and anchor.type == 'EMPTY':
            cam_obj.parent = anchor
            cam_obj.matrix_parent_inverse = anchor.matrix_world.inverted()

        print(f"[Asset Mode] Created asset camera: {cam_name} "
              f"(parent={anchor.name if anchor else 'none'})")
    return cam_obj


def _register_asset_panel():
    """Register VIEW3D_PT_AssetMode if not already registered."""
    global _asset_panel_registered
    if _asset_panel_registered:
        return
    try:
        bpy.utils.register_class(VIEW3D_PT_AssetMode)
        _asset_panel_registered = True
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not register asset panel: {e}")


def _unregister_asset_panel():
    """Unregister VIEW3D_PT_AssetMode if it is currently registered."""
    global _asset_panel_registered
    if not _asset_panel_registered:
        return
    try:
        bpy.utils.unregister_class(VIEW3D_PT_AssetMode)
        _asset_panel_registered = False
    except Exception as e:
        print(f"[Asset Mode] ⚠ Could not unregister asset panel: {e}")


# ================================================================
#    Operators
# ================================================================

class STYLEENGINE_OT_EnterAssetMode(bpy.types.Operator):
    """Enter Asset Mode for the active mesh object"""
    bl_idname  = "style_engine.enter_asset_mode"
    bl_label   = "Enter Asset Mode"
    bl_description = (
        "Enter Asset Mode for the selected mesh: isolates the object, "
        "assigns a dedicated camera, and starts the asset editing workflow"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Accept MESH (real asset) or EMPTY (placeholder created by EditAsset).
        # asset_mode may already be True when entering a nested asset — that is fine.
        return (
            context.active_object is not None
            and context.active_object.type in {'MESH', 'EMPTY'}
        )

    def execute(self, context):
        obj = context.active_object
        object_name = obj.name
        scene = context.scene
        props = scene.style_engine_props

        # Derive the asset label (base concept name): strip Blender's ".001" suffix so
        # all iterations of the same asset share one camera, one directory, one subject.
        _parts = object_name.rsplit('.', 1)
        asset_label = _parts[0] if (len(_parts) == 2 and _parts[1].isdigit()) else object_name

        # ── 0. If already in Asset Mode, push the current level onto the stack ──
        # This enables arbitrary nesting (Asset Mode within Asset Mode).
        if props.asset_mode_depth > 0:
            try:
                _stack = json.loads(props.asset_mode_stack or "[]")
                _snapshot = {
                    "asset_name":             props.current_asset_name,
                    "prev_camera":            props.asset_prev_camera,
                    "prev_prompt":            props.asset_prev_prompt,
                    "prev_subjects":          props.asset_prev_subjects,
                    "prev_resolution_x":      props.asset_prev_resolution_x,
                    "prev_resolution_y":      props.asset_prev_resolution_y,
                    "stored_visibility":      props.asset_stored_visibility,
                    "asset_subject_index":    props.asset_subject_index,
                    "asset_object_links":     props.asset_object_links,
                    "asset_current_3d_index": props.asset_current_3d_index,
                }
                _stack.append(_snapshot)
                props.asset_mode_stack = json.dumps(_stack)
                print(f"[Asset Mode] Pushed depth {props.asset_mode_depth} — "
                      f"stack size now {len(_stack)}")
            except Exception as _pe:
                print(f"[Asset Mode] ⚠ Could not push stack: {_pe}")

        # ── 1. Store current scene camera so we can restore it on exit ───
        props.asset_prev_camera = scene.camera.name if scene.camera else ""

        # ── 2. Store visibility of every scene object ─────────────────────
        vis_dict = {
            o.name: [o.hide_viewport, o.hide_render]
            for o in scene.objects
        }
        props.asset_stored_visibility = json.dumps(vis_dict)

        # ── 3. Hide everything except the active object ────────────────────
        # Also keep the asset camera (keyed to asset_label) visible.
        for o in scene.objects:
            if o == obj:
                continue
            if o.type == 'CAMERA' and o.name == _get_asset_camera_name(asset_label):
                continue
            o.hide_viewport = True
            o.hide_render   = True

        # ── 4. Create / retrieve the dedicated asset camera (by concept label) ──
        cam_obj = _get_or_create_asset_camera(asset_label)
        # Unhide while this asset is active so the background image (current_ai.png)
        # is visible in camera view. Re-hidden on ExitAssetMode.
        cam_obj.hide_viewport = False
        cam_obj.hide_render   = False

        # ── 5. Frame the camera on the object ─────────────────────────────
        _frame_camera_on_object(cam_obj, obj)

        # ── 6. Set asset camera as active scene camera ────────────────────
        scene.camera = cam_obj

        # ── 6b. Save render resolution and snap to 1024×1024 ─────────────
        props.asset_prev_resolution_x = scene.render.resolution_x
        props.asset_prev_resolution_y = scene.render.resolution_y
        scene.render.resolution_x = 1024
        scene.render.resolution_y = 1024

        # ── 6c. Create black placeholder + set up camera background ──────
        # All asset_label iterations share the same directory/camera.
        # For nested assets the directory lives under the parent's path.
        try:
            from . import workspace_setup as _ws
            # Build the new nested path components BEFORE updating current_asset_name
            _pending_stack  = json.loads(props.asset_mode_stack or "[]")
            _pending_parents = [e["asset_name"] for e in _pending_stack]
            _nested_components = _pending_parents + [asset_label]
            _ws.ensure_asset_directory(context, asset_label,
                                       path_components=_nested_components
                                       if len(_nested_components) > 1 else None)
            _ws.create_asset_placeholder_image(context, asset_label)
            _ws.setup_asset_camera_background(context, asset_label, cam_obj)
        except Exception as _e:
            print(f"[Asset Mode] ⚠ Could not set up camera background: {_e}")

        # ── 7. Update state props — current_asset_name is the LABEL, not obj.name ──
        props.asset_mode         = True
        props.current_asset_name = asset_label   # key fix: concept, not mesh iteration
        props.asset_current_3d_index = 0

        # ── 8. Find or create the matching Refine-Image subject ──────────────
        #
        # Four-tier lookup (most → least specific):
        #   Tier 1  Direct index hit  — asset_subject_index already points here
        #   Tier 2  linked_object_name == object_name (exact mesh binding)
        #   Tier 3  label == asset_label OR label == object_name (concept match)
        #   Tier 4  Create new subject
        subject_idx = -1

        # Tier 1
        prev_idx = props.asset_subject_index
        if 0 <= prev_idx < len(props.refine_subjects):
            s = props.refine_subjects[prev_idx]
            if s.linked_object_name == object_name or s.label == asset_label:
                subject_idx = prev_idx
                print(f"[Asset Mode] 🔗 Subject found via direct index [{prev_idx}]")

        # Tier 2
        if subject_idx == -1:
            for i, s in enumerate(props.refine_subjects):
                if s.linked_object_name == object_name:
                    subject_idx = i
                    print(f"[Asset Mode] 🔗 Subject found via linked_object_name [{i}] '{s.label}'")
                    break

        # Tier 3 — label match (concept OR exact object name)
        if subject_idx == -1:
            for i, s in enumerate(props.refine_subjects):
                if s.label in (asset_label, object_name):
                    subject_idx = i
                    print(f"[Asset Mode] 🔗 Subject found via label match [{i}] '{s.label}'")
                    break

        # Tier 4 — create, keyed to asset_label (NOT raw object_name)
        if subject_idx == -1:
            subj = props.refine_subjects.add()
            subject_idx = len(props.refine_subjects) - 1
            subj.label = asset_label
            subj.show_expanded = False
            if obj.material_slots and obj.material_slots[0].material:
                subj.material = obj.material_slots[0].material.name
            print(f"[Asset Mode] ➕ Created new subject [{subject_idx}] '{asset_label}'")

        # Always stamp the two-way link so every tier ends up with a permanent bond.
        subj = props.refine_subjects[subject_idx]
        # Ensure label is the concept name (in case an old entry had the raw obj name)
        if subj.label == object_name and object_name != asset_label:
            subj.label = asset_label
        subj.linked_object_name = object_name
        props.asset_subject_index = subject_idx

        # Keep the persistent label→object map up to date.
        try:
            _link_map = json.loads(props.asset_object_links or "{}")
        except Exception:
            _link_map = {}
        _link_map[asset_label] = object_name
        props.asset_object_links = json.dumps(_link_map)

        # ── 9. Swap N-panels ──────────────────────────────────────────────
        _register_asset_panel()

        # ── 10. Restore active iteration if history exists ───────────────
        # If this asset already has mesh iterations, show the active one instead
        # of triggering a new isolation render.
        try:
            from . import workspace_setup as _ws
            history = _ws.read_asset_history(context, asset_label)
            iters   = history.get("iterations", [])
            if iters:
                active_i   = history.get("active_index", 0)
                active_entry = iters[min(active_i, len(iters) - 1)]
                active_obj   = bpy.data.objects.get(active_entry.get("object_name", ""))
                if active_obj and active_obj.name != obj.name:
                    # Show the historically-active mesh instead of the current selection
                    for o in scene.objects:
                        if o == cam_obj:
                            continue
                        _parts2 = o.name.rsplit('.', 1)
                        _base2  = _parts2[0] if (len(_parts2) == 2 and _parts2[1].isdigit()) else o.name
                        if _base2 == asset_label:
                            o.hide_viewport = (o.name != active_obj.name)
                            o.hide_render   = (o.name != active_obj.name)
                    # Update link to point at the active iteration's mesh
                    subj.linked_object_name = active_obj.name
                    try:
                        _lm2 = json.loads(props.asset_object_links or "{}")
                    except Exception:
                        _lm2 = {}
                    _lm2[asset_label] = active_obj.name
                    props.asset_object_links = json.dumps(_lm2)
                print(f"[Asset Mode] 📖 Restored iteration {active_i+1}/{len(iters)}: "
                      f"'{active_entry.get('object_name')}'")
        except Exception as _he:
            print(f"[Asset Mode] ⚠ History restore skipped: {_he}")

        # ── 11. Swap subjects JSON ───────────────────────────────────────────
        # Serialize the current scene subjects, then load the asset-specific
        # subjects from disk (or start fresh for a brand-new asset).
        try:
            from . import workspace_setup as _ws
            from . import ui_panel as _up
            # Save scene subjects to the snapshot property
            props.asset_prev_subjects = _up._build_refine_json(props)

            # Determine nested path for loading this asset's subjects
            _pending_stack_11   = json.loads(props.asset_mode_stack or "[]")
            _pending_parents_11 = [e["asset_name"] for e in _pending_stack_11]
            _nested_comps_11    = _pending_parents_11 + [asset_label]
            _pc_arg             = _nested_comps_11 if len(_nested_comps_11) > 1 else None

            # Try to load iteration-specific snapshot first, then asset-level file
            _active_iter = _ws.read_asset_history(
                context, asset_label).get("active_index", 0)
            _iter_json = _ws.load_asset_iteration_subjects_json(
                context, asset_label, _active_iter)
            _asset_json = _iter_json or _ws.load_asset_subjects_json(
                context, asset_label, path_components=_pc_arg)
            if _asset_json:
                _up._populate_refine_from_json(props, _asset_json)
                print(f"[Asset Mode] Subjects JSON loaded for '{asset_label}'")
            else:
                # Brand-new asset — clear subjects so the AI starts fresh
                props.refine_subjects.clear()
                print(f"[Asset Mode] No subjects JSON found — cleared for '{asset_label}'")
        except Exception as _sje:
            print(f"[Asset Mode] ⚠ Subjects JSON swap on enter skipped: {_sje}")

        # ── 12. Swap STYLEENGINE_Prompt ──────────────────────────────────────
        # Save the current scene prompt, then load the asset-specific prompt so
        # the text editor always shows the relevant history for the active mode.
        try:
            from . import workspace_setup as _ws
            _pt = bpy.data.texts.get("STYLEENGINE_Prompt")
            props.asset_prev_prompt = _pt.as_string() if _pt else ""

            # Look for the most recent .txt sidecar in the asset's Images/ dir
            _img_dir = _ws.get_asset_directory(context, asset_label) / "Images"
            _txts    = sorted(_img_dir.glob("*.txt")) if _img_dir.exists() else []
            if _txts:
                with open(_txts[-1], 'r', encoding='utf-8') as _f:
                    _asset_prompt = _f.read()
            else:
                _asset_prompt = (f"Extract {asset_label} from this scene as an "
                                 f"isolated asset in a neutral studio background.")
            if not _pt:
                _pt = bpy.data.texts.new("STYLEENGINE_Prompt")
            _pt.clear()
            _pt.write(_asset_prompt)
            print(f"[Asset Mode] Prompt swapped in for '{asset_label}'")
        except Exception as _pe:
            print(f"[Asset Mode] Prompt swap on enter skipped: {_pe}")

        # ── 12. Increment nesting depth ──────────────────────────────────
        props.asset_mode_depth += 1

        # ── 13. Queue the isolation render (uses asset_label via _ws) ────
        self._queue_isolation_render(context, obj, asset_label)

        _chain = [e["asset_name"]
                  for e in json.loads(props.asset_mode_stack or "[]")] + [asset_label]
        print(f"[Asset Mode] EnterAssetMode complete — depth={props.asset_mode_depth} "
              f"chain={' / '.join(_chain)} camera='"
              f"{scene.camera.name if scene.camera else 'None'}'")
        self.report({'INFO'}, f"Asset Mode: {' / '.join(_chain)}")
        return {'FINISHED'}

    def _queue_isolation_render(self, context, obj, asset_label=None):
        """Trigger the isolation render — only on first entry for this asset.

        All directory/camera lookups use asset_label (the concept base name) so
        iterations windmill, windmill.001, windmill.002 all share one directory.

        On subsequent entries the most recently saved image is restored
        to the asset temp folder so the asset camera shows the correct
        background without kicking off a new generation.
        """
        from . import workspace_setup as _ws
        import shutil as _shutil

        # Use asset_label (concept name) for directory lookups; fall back to obj.name.
        label = asset_label or obj.name

        # ── Skip if the asset already has saved images ────────────────────
        asset_dir   = _ws.ensure_asset_directory(context, label)
        images_dir  = asset_dir / "Images"
        existing    = sorted(images_dir.glob("*.png")) if images_dir.exists() else []
        if existing:
            latest     = existing[-1]
            asset_temp = _ws.get_asset_temp_directory(context, label)
            try:
                _shutil.copy2(latest, asset_temp / "current_ai.png")
                _ws.refresh_asset_camera_image(label)
                print(f"[Asset Mode] 📷 Restored existing asset image: {latest.name}")
            except Exception as e:
                print(f"[Asset Mode] ⚠ Could not restore existing image: {e}")
            return  # don't trigger a new generation

        # ── First entry — extract asset from scene via AssetNanoAlignmentRB ──
        _ws.queue_asset_isolation_workflow(context, label)


class STYLEENGINE_OT_ExitAssetMode(bpy.types.Operator):
    """Exit Asset Mode and return to Scene Mode"""
    bl_idname  = "style_engine.exit_asset_mode"
    bl_label   = "Exit Asset Mode"
    bl_description = "Exit Asset Mode, restore scene visibility and camera"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.style_engine_props.asset_mode

    def execute(self, context):
        scene = context.scene
        props = scene.style_engine_props

        # ── 1. Restore object visibility ─────────────────────────────────
        vis_json = props.asset_stored_visibility
        if vis_json:
            try:
                vis_dict = json.loads(vis_json)
                for obj_name, (hv, hr) in vis_dict.items():
                    o = bpy.data.objects.get(obj_name)
                    if o:
                        o.hide_viewport = hv
                        o.hide_render   = hr
            except Exception as e:
                print(f"[Asset Mode] ⚠ Could not restore visibility: {e}")

        # ── 2. Restore scene camera ───────────────────────────────────────
        prev_cam_name = props.asset_prev_camera
        if prev_cam_name and prev_cam_name in bpy.data.objects:
            scene.camera = bpy.data.objects[prev_cam_name]
        elif prev_cam_name == "":
            scene.camera = None

        # Re-hide the asset camera now that it's no longer the active camera.
        # Covers cameras created before hide_viewport was set in _get_or_create.
        _asset_cam_name = _get_asset_camera_name(props.current_asset_name)
        _asset_cam = bpy.data.objects.get(_asset_cam_name)
        if _asset_cam:
            _asset_cam.hide_viewport = True

        # ── 2b. Restore render resolution ────────────────────────────────
        scene.render.resolution_x = props.asset_prev_resolution_x
        scene.render.resolution_y = props.asset_prev_resolution_y

        # ── 3a. Persist active_index to asset_history.json before clearing ──
        asset_label = props.current_asset_name
        if asset_label:
            try:
                from . import workspace_setup as _ws
                history    = _ws.read_asset_history(context, asset_label)
                # active_index is already set correctly via switch_asset_iteration;
                # just make sure the file is up to date.
                _ws.write_asset_history(context, asset_label, history)
                print(f"[Asset Mode] 💾 Persisted history for '{asset_label}'")
            except Exception as _he:
                print(f"[Asset Mode] ⚠ Could not persist history: {_he}")

        # ── 3b. Sync scene objects → JSON subjects on exit ────────────────
        try:
            from . import ui_panel as _up
            _up.sync_scene_objects_to_json(props, context)
        except Exception as _se:
            print(f"[Asset Mode] ⚠ Post-exit sync skipped: {_se}")

        # ── 3b2. Save current asset subjects then restore scene subjects ──────
        try:
            from . import workspace_setup as _ws
            from . import ui_panel as _up
            # Persist the asset's current subjects to disk before clearing
            if asset_label:
                _current_json = _up._build_refine_json(props)
                _ws.save_asset_subjects_json(context, asset_label, _current_json)
                print(f"[Asset Mode] Saved asset subjects for '{asset_label}'")
            # Restore the scene subjects from the snapshot
            if props.asset_prev_subjects:
                _up._populate_refine_from_json(props, props.asset_prev_subjects)
                print("[Asset Mode] Scene subjects restored")
            else:
                props.refine_subjects.clear()
        except Exception as _sje:
            print(f"[Asset Mode] ⚠ Subjects restore on exit skipped: {_sje}")

        # ── 3c. Restore STYLEENGINE_Prompt to the scene snapshot ─────────────
        try:
            _pt = bpy.data.texts.get("STYLEENGINE_Prompt")
            if not _pt:
                _pt = bpy.data.texts.new("STYLEENGINE_Prompt")
            _pt.clear()
            _pt.write(props.asset_prev_prompt)
            print("[Asset Mode] Prompt restored to scene snapshot")
        except Exception as _pe:
            print(f"[Asset Mode] Prompt restore on exit skipped: {_pe}")

        # ── 4. Clear state — or pop the stack if nested ──────────────────
        _exit_stack = json.loads(props.asset_mode_stack or "[]")
        if _exit_stack:
            # ── Nested exit: restore the parent Asset Mode level ─────────
            _snapshot = _exit_stack.pop()
            props.asset_mode_stack          = json.dumps(_exit_stack)
            props.current_asset_name        = _snapshot["asset_name"]
            props.asset_prev_camera         = _snapshot["prev_camera"]
            props.asset_prev_prompt         = _snapshot["prev_prompt"]
            props.asset_prev_subjects       = _snapshot["prev_subjects"]
            props.asset_prev_resolution_x   = _snapshot["prev_resolution_x"]
            props.asset_prev_resolution_y   = _snapshot["prev_resolution_y"]
            props.asset_stored_visibility   = _snapshot["stored_visibility"]
            props.asset_subject_index       = _snapshot["asset_subject_index"]
            props.asset_object_links        = _snapshot["asset_object_links"]
            props.asset_current_3d_index    = _snapshot["asset_current_3d_index"]
            props.asset_mode_depth         -= 1
            # asset_mode stays True — we are still in an asset mode level
            # N-panel stays registered
            _parent = props.current_asset_name
            print(f"[Asset Mode] Popped stack — back to '{_parent}' "
                  f"(depth={props.asset_mode_depth})")
            self.report({'INFO'}, f"Back to Asset Mode: {_parent}")
        else:
            # ── Top-level exit: return to Scene Mode ─────────────────────
            props.asset_mode               = False
            props.current_asset_name       = ""
            props.asset_stored_visibility  = ""
            props.asset_prev_camera        = ""
            props.asset_current_3d_index   = 0
            props.asset_prev_resolution_x  = 1024
            props.asset_prev_resolution_y  = 1024
            props.asset_prev_prompt        = ""
            props.asset_prev_subjects      = ""
            props.asset_mode_stack         = "[]"
            props.asset_mode_depth         = 0

            # ── 5. Swap N-panels back ─────────────────────────────────────
            _unregister_asset_panel()
            self.report({'INFO'}, "Returned to Scene Mode")

        return {'FINISHED'}


class STYLEENGINE_OT_EditAsset(bpy.types.Operator):
    """Enter Asset Mode for the subject's associated mesh object"""
    bl_idname  = "style_engine.edit_asset"
    bl_label   = "Edit Asset"
    bl_description = (
        "Enter Asset Mode for the mesh object matching this subject label. "
        "If no matching object exists, a placeholder mesh is created."
    )
    bl_options = {'REGISTER', 'UNDO'}

    subject_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        props = context.scene.style_engine_props
        try:
            subj = props.refine_subjects[self.subject_index]
        except IndexError:
            self.report({'ERROR'}, "Subject index out of range")
            return {'CANCELLED'}

        target_name = subj.label.strip()
        if not target_name:
            self.report({'ERROR'}, "Subject has no label")
            return {'CANCELLED'}

        # Look for an existing object (MESH or EMPTY) with this name
        target_obj = bpy.data.objects.get(target_name)
        if target_obj is None or target_obj.type not in {'MESH', 'EMPTY'}:
            # Create an EMPTY (ARROWS) as the placeholder — no geometry means it can
            # never interfere with Trellis or render passes, and the arrows icon gives
            # a clear visual anchor in the viewport.
            target_obj = bpy.data.objects.new(target_name, None)  # None data = Empty
            target_obj.empty_display_type = 'ARROWS'
            target_obj.empty_display_size = 0.2
            context.scene.collection.objects.link(target_obj)
            print(f"[Asset Mode] 📦 Created EMPTY placeholder: {target_name}")

        # Make it the active object
        context.view_layer.objects.active = target_obj
        target_obj.select_set(True)

        # Pre-seed the link so EnterAssetMode fires Tier 1 immediately:
        # stamp linked_object_name on this subject and record the index.
        # EnterAssetMode will reinforce the same stamp — idempotent.
        subj.linked_object_name = target_name
        props.asset_subject_index = self.subject_index

        # Also keep the persistent label→object map up to date.
        try:
            _link_map = json.loads(props.asset_object_links or "{}")
        except Exception:
            _link_map = {}
        _link_map[subj.label] = target_name
        props.asset_object_links = json.dumps(_link_map)

        print(f"[Asset Mode] 🔗 EditAsset: pre-seeded link subject[{self.subject_index}]"
              f" '{subj.label}' → '{target_name}'")

        # Pass the active object explicitly so EnterAssetMode.poll() sees it
        # even when called from the N-panel (where context may lag behind the
        # view_layer assignment we just made above).
        with context.temp_override(active_object=target_obj):
            return bpy.ops.style_engine.enter_asset_mode('INVOKE_DEFAULT')


class STYLEENGINE_OT_AssetHistoryPrev(bpy.types.Operator):
    """Navigate to the previous iteration in asset history"""
    bl_idname  = "style_engine.asset_history_prev"
    bl_label   = "Previous Asset Iteration"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.scene.style_engine_props.asset_mode

    def execute(self, context):
        from . import workspace_setup as ws
        props      = context.scene.style_engine_props
        asset_name = props.current_asset_name
        if not asset_name:
            return {'CANCELLED'}

        history = ws.read_asset_history(context, asset_name)
        active  = history.get("active_index", 0)
        if active <= 0:
            self.report({'INFO'}, "Already at first iteration")
            return {'CANCELLED'}

        ws.switch_asset_iteration(context, asset_name, active - 1)
        return {'FINISHED'}


class STYLEENGINE_OT_AssetHistoryNext(bpy.types.Operator):
    """Navigate to the next iteration in asset history"""
    bl_idname  = "style_engine.asset_history_next"
    bl_label   = "Next Asset Iteration"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.scene.style_engine_props.asset_mode

    def execute(self, context):
        from . import workspace_setup as ws
        props      = context.scene.style_engine_props
        asset_name = props.current_asset_name
        if not asset_name:
            return {'CANCELLED'}

        history = ws.read_asset_history(context, asset_name)
        active  = history.get("active_index", 0)
        total   = len(history.get("iterations", []))
        if active >= total - 1:
            self.report({'INFO'}, "Already at latest iteration")
            return {'CANCELLED'}

        ws.switch_asset_iteration(context, asset_name, active + 1)
        return {'FINISHED'}


# ================================================================
#    Breadcrumb navigation operators
# ================================================================

class STYLEENGINE_OT_ExitAssetModeAll(bpy.types.Operator):
    """Exit all nested Asset Mode levels and return directly to Scene Mode"""
    bl_idname  = "style_engine.exit_asset_mode_all"
    bl_label   = "Exit to Scene Mode"
    bl_description = "Pop all Asset Mode levels and return to Scene Mode"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.style_engine_props.asset_mode

    def execute(self, context):
        props = context.scene.style_engine_props
        max_pops = props.asset_mode_depth + 1   # depth + 1 safety
        for _ in range(max_pops):
            if not props.asset_mode:
                break
            bpy.ops.style_engine.exit_asset_mode('INVOKE_DEFAULT')
        return {'FINISHED'}


class STYLEENGINE_OT_ExitAssetModeToName(bpy.types.Operator):
    """Navigate the breadcrumb back to a specific ancestor Asset Mode level"""
    bl_idname  = "style_engine.exit_asset_mode_to_name"
    bl_label   = "Back to Asset"
    bl_description = "Return to the specified ancestor Asset Mode level"
    bl_options = {'REGISTER', 'UNDO'}

    target_name: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return context.scene.style_engine_props.asset_mode

    def execute(self, context):
        props = context.scene.style_engine_props
        max_pops = props.asset_mode_depth + 1
        for _ in range(max_pops):
            if props.current_asset_name == self.target_name:
                break
            if not props.asset_mode:
                break
            bpy.ops.style_engine.exit_asset_mode('INVOKE_DEFAULT')
        return {'FINISHED'}


# ================================================================
#    Asset Mode N-Panel  (registered only while in Asset Mode)
# ================================================================

class VIEW3D_PT_AssetMode(bpy.types.Panel):
    """Asset Mode N-panel — replaces the scene panel while in Asset Mode."""
    bl_label      = "Style Engine  [ASSET MODE]"
    bl_idname     = "VIEW3D_PT_AssetMode"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category   = 'Style Engine'

    @classmethod
    def poll(cls, context):
        try:
            return context.scene.style_engine_props.asset_mode
        except Exception:
            return False

    def draw(self, context):
        layout = self.layout
        props  = context.scene.style_engine_props

        # ── Breadcrumb navigation ─────────────────────────────────────────
        # Shows: [Scene] › [facade] › [window ●]
        # Each ancestor is a clickable button that pops back to that level.
        _bc_stack = json.loads(props.asset_mode_stack or "[]")

        crumb_row = layout.row(align=True)
        crumb_row.scale_y = 0.85
        crumb_row.operator("style_engine.exit_asset_mode_all",
                           text="Scene", icon='SCENE_DATA')
        for _entry in _bc_stack:
            crumb_row.label(text="›")
            _bc_op = crumb_row.operator("style_engine.exit_asset_mode_to_name",
                                        text=_entry["asset_name"])
            _bc_op.target_name = _entry["asset_name"]
        crumb_row.label(text="›")
        crumb_row.label(text=f"{props.current_asset_name}  ●")

        # One-level back button — label adapts to parent name
        back_row = layout.row()
        back_row.scale_y = 1.2
        _parent_label = _bc_stack[-1]["asset_name"] if _bc_stack else "Scene"
        back_row.operator("style_engine.exit_asset_mode",
                          text=f"← {_parent_label}",
                          icon='BACK')

        # Apply to Parent — only shown when there is a parent level
        if props.asset_mode_depth > 0:
            apply_row = layout.row()
            apply_row.scale_y = 1.1
            apply_row.operator("style_engine.apply_to_parent",
                               text="↑ Apply to Parent",
                               icon='TRIA_UP')

        layout.separator()

        # ── Asset info ────────────────────────────────────────────────────
        info_box = layout.box()
        info_box.label(text=f"Asset:  {props.current_asset_name}", icon='OBJECT_DATA')
        obj = bpy.data.objects.get(props.current_asset_name)
        if obj and obj.material_slots and obj.material_slots[0].material:
            info_box.label(text=f"Material:  {obj.material_slots[0].material.name}",
                           icon='MATERIAL')
        cam_name = _get_asset_camera_name(props.current_asset_name)
        info_box.label(text=f"Camera:  {cam_name}", icon='CAMERA_DATA')

        # ── Iteration History Browser (manifest-driven) ───────────────────
        from . import workspace_setup as _ws
        history    = _ws.read_asset_history(context, props.current_asset_name)
        iters      = history.get("iterations", [])
        active_idx = history.get("active_index", 0)
        total      = len(iters)

        hist_box = layout.box()
        hist_hdr = hist_box.row()
        hist_hdr.label(text="Iterations", icon='TIME')

        if total:
            hist_hdr.label(text=f"{active_idx + 1} / {total}")
            nav_row   = hist_box.row(align=True)
            nav_row.scale_y = 1.3
            prev_part = nav_row.row(align=True)
            prev_part.enabled = (active_idx > 0)
            prev_part.operator("style_engine.asset_history_prev", text="", icon='TRIA_LEFT')
            entry     = iters[active_idx]
            obj_label = entry.get("object_name", "?")[:22]
            nav_row.label(text=obj_label)
            next_part = nav_row.row(align=True)
            next_part.enabled = (active_idx < total - 1)
            next_part.operator("style_engine.asset_history_next", text="", icon='TRIA_RIGHT')
        else:
            hist_box.label(text="No iterations yet — generate a 3D mesh", icon='INFO')

        layout.separator()

        # ── Progress bar (mirrors scene panel) ────────────────────────────
        from . import progress_bar as _pb
        status_box = layout.box()
        row = status_box.row(align=True)
        connection     = _pb.get_connection_status()
        _progress      = _pb.get_display_progress()
        display_status = _pb.get_display_status()
        progress_pct   = int(_progress * 100)
        if connection != "connected":
            row.label(text="", icon='KEYTYPE_EXTREME_VEC')
            row.label(text="Server: Offline")
        elif display_status == "ready" and (_progress == 0 or _progress >= 1.0):
            row.label(text="", icon='KEYTYPE_JITTER_VEC')
            row.label(text="Server: Ready")
        elif display_status in ("processing", "finishing") or (0 < _progress < 1.0):
            row.label(text="", icon='KEYTYPE_KEYFRAME_VEC')
            row.label(text="Server: Working...")
        else:
            row.label(text="", icon='KEYTYPE_JITTER_VEC')
            row.label(text="Server: Ready")
        row = status_box.row(align=True)
        bar_length = 15
        filled     = int(bar_length * _progress)
        bar_text   = "▓" * filled + "░" * (bar_length - filled)
        row.label(text=f"{bar_text} {progress_pct}%")
        node_name = _pb.get_display_node()
        if node_name and node_name != "Idle" and _progress > 0:
            row = status_box.row(align=True)
            row.scale_y = 0.8
            row.label(text=f"  {node_name}", icon='NODE')
        last_status = _pb.get_last_status()
        queue = last_status.get('queue_remaining', 0) if last_status else 0
        if queue > 0:
            row = status_box.row(align=True)
            row.scale_y = 0.8
            row.label(text=f"Queue: {queue}", icon='LINENUMBERS_ON')

        layout.separator()

        # ── 1:1 replica of all scene panel categories ─────────────────────
        # Delegates to VIEW3D_PT_StyleEngine.draw_body() so View → Texture
        # categories stay automatically in sync with the scene panel.
        from . import ui_panel
        ui_panel.VIEW3D_PT_StyleEngine.draw_body(self, context)


# ================================================================
#    Registration
# ================================================================

_operators = (
    STYLEENGINE_OT_EnterAssetMode,
    STYLEENGINE_OT_ExitAssetMode,
    STYLEENGINE_OT_ExitAssetModeAll,
    STYLEENGINE_OT_ExitAssetModeToName,
    STYLEENGINE_OT_EditAsset,
    STYLEENGINE_OT_AssetHistoryPrev,
    STYLEENGINE_OT_AssetHistoryNext,
)


def register():
    global _overlay_handle

    for cls in _operators:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[Asset Mode] ⚠ Could not register {cls.__name__}: {e}")

    # Register the viewport overlay draw handler
    _overlay_handle = bpy.types.SpaceView3D.draw_handler_add(
        _draw_asset_mode_overlay, (), 'WINDOW', 'POST_PIXEL'
    )
    print("[Style Engine] ✅ Asset Mode — operators + overlay registered")


def unregister():
    global _overlay_handle

    _unregister_asset_panel()

    if _overlay_handle is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_overlay_handle, 'WINDOW')
        except Exception:
            pass
        _overlay_handle = None

    for cls in reversed(_operators):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
