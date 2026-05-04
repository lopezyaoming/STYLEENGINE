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


def _get_asset_camera_name(name_or_components):
    """Return the camera object name for an asset.

    Accepts either a plain string (leaf name) or a list of path components
    (full ancestry chain).  Using the full chain prevents naming collisions
    when two assets at different nesting depths share the same leaf label
    (e.g. a top-level 'trinkets' vs 'gollum/trinkets').
    """
    if isinstance(name_or_components, list):
        raw = "_".join(name_or_components)
    else:
        raw = name_or_components
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw)
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


def _get_or_create_asset_camera(path_components):
    """
    Return the asset camera for the given path, creating it if necessary.

    Accepts a list of path components (full ancestry chain, e.g. ["gollum",
    "trinkets"]) or a plain string for backward compatibility.  The camera
    name encodes the full path so there are no collisions between assets at
    different nesting depths that share a leaf label.
    """
    cam_name  = _get_asset_camera_name(path_components)
    leaf_name = path_components[-1] if isinstance(path_components, list) else path_components
    cam_obj   = bpy.data.objects.get(cam_name)
    if cam_obj is None:
        cam_data      = bpy.data.cameras.new(cam_name)
        cam_data.lens = 50.0
        cam_obj       = bpy.data.objects.new(cam_name, cam_data)

        # Link to scene root so it exists in the scene
        bpy.context.scene.collection.objects.link(cam_obj)

        # Hide from viewport by default — still works as active render/scene camera
        cam_obj.hide_viewport = True

        # Parent to the asset Empty anchor (leaf name) so the hierarchy is clean
        anchor = bpy.data.objects.get(leaf_name)
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
        # Use props.asset_mode (not asset_mode_depth) as the guard — depth can
        # survive a file-load reset and cause spurious stack pushes with an empty
        # current_asset_name, which corrupts the camera/directory path components.
        if props.asset_mode:
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
                    "prev_visual_style": {
                        "art_style":          props.refine_style_art_style,
                        "medium":             props.refine_style_medium,
                        "lighting_condition": props.refine_style_lighting,
                    },
                    # Identity of the asset being paused — restored on nested exit
                    "asset_subject_style":    props.asset_subject_style,
                    "asset_subject_scale":    props.asset_subject_scale,
                    "asset_subject_color":    props.asset_subject_color,
                    "asset_subject_material": props.asset_subject_material,
                    "asset_subject_features": [f.value for f in props.asset_subject_features
                                               if f.value.strip()],
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

        # ── 2b. Compute the full ancestry path for this entry ────────────────
        # The stack was already updated above (if nested), so reading it here
        # gives the correct parent chain.  A single-level entry still produces
        # a one-element list, which generates the same camera/dir name as before.
        _pending_stack_   = json.loads(props.asset_mode_stack or "[]")
        _pending_parents_ = [e["asset_name"] for e in _pending_stack_]
        _path_comps       = _pending_parents_ + [asset_label]

        # ── 3. Hide everything except the active object ────────────────────
        # Also keep the asset camera (full-path key) visible.
        _this_cam_name = _get_asset_camera_name(_path_comps)
        for o in scene.objects:
            if o == obj:
                continue
            if o.type == 'CAMERA' and o.name == _this_cam_name:
                continue
            o.hide_viewport = True
            o.hide_render   = True

        # ── 4. Create / retrieve the dedicated asset camera (full path key) ──
        cam_obj = _get_or_create_asset_camera(_path_comps)
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
        # Pass path_components so nested assets use their own subdirectory.
        try:
            from . import workspace_setup as _ws
            _ws.ensure_asset_directory(context, asset_label,
                                       path_components=_path_comps
                                       if len(_path_comps) > 1 else None)
            _ws.create_asset_placeholder_image(context, asset_label,
                                               path_components=_path_comps)
            _ws.setup_asset_camera_background(context, asset_label, cam_obj,
                                              path_components=_path_comps)
        except Exception as _e:
            print(f"[Asset Mode] ⚠ Could not set up camera background: {_e}")

        # ── 7. Update state props — current_asset_name is the LABEL, not obj.name ──
        props.asset_mode         = True
        props.current_asset_name = asset_label   # key fix: concept, not mesh iteration
        props.asset_current_3d_index = 0
        # Pre-populate the SAM3 subject string with the human-readable asset name
        # (underscores replaced with spaces).  The user can edit it before running
        # "Isolate Asset" if the name is too specific (e.g. "brick_facade_left" → "brick wall").
        props.sam3_isolate_subject = asset_label.replace("_", " ")

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

        # ── 11. Swap subjects JSON ───────────────────────────────────────────
        # Serialize the current scene subjects, then load the asset-specific
        # subjects from disk (or start fresh for a brand-new asset).
        try:
            from . import workspace_setup as _ws
            from . import ui_panel as _up

            # Capture the parent's visual_style BEFORE any overwrites so we can
            # inherit it into the asset if the asset has no override of its own.
            _parent_vs = {
                "art_style":          props.refine_style_art_style,
                "medium":             props.refine_style_medium,
                "lighting_condition": props.refine_style_lighting,
            }

            # Save scene subjects to the snapshot property AND to disk.
            # The disk copy survives a file saved in asset mode and acts as a
            # third-tier recovery path on the next file load.
            _scene_subj_json = _up._build_refine_json(props)
            props.asset_prev_subjects = _scene_subj_json
            try:
                _ws.save_scene_subjects_json(context, _scene_subj_json)
            except Exception as _ssje:
                print(f"[Asset Mode] ⚠ Could not save scene_subjects.json: {_ssje}")

            # Populate asset identity from the matching parent subject entry.
            # This gives the Asset Mode identity box its initial values.
            props.asset_subject_style    = ""
            props.asset_subject_scale    = ""
            props.asset_subject_color    = ""
            props.asset_subject_material = ""
            props.asset_subject_features.clear()
            try:
                _id_snap = json.loads(props.asset_prev_subjects)
                for _id_s in _id_snap.get("subject_matter", []):
                    if _id_s.get("label") == asset_label:
                        props.asset_subject_style    = _id_s.get("style",    "")
                        props.asset_subject_scale    = _id_s.get("scale",    "")
                        props.asset_subject_color    = _id_s.get("color",    "")
                        props.asset_subject_material = _id_s.get("material", "")
                        for _feat_str in _id_s.get("features", []):
                            if isinstance(_feat_str, str) and _feat_str.strip():
                                _fi = props.asset_subject_features.add()
                                _fi.value = _feat_str
                        print(f"[Asset Mode] Identity loaded for '{asset_label}': "
                              f"style={props.asset_subject_style!r} "
                              f"features={[f.value for f in props.asset_subject_features]!r}")
                        break
            except Exception as _ide:
                print(f"[Asset Mode] ⚠ Identity load skipped: {_ide}")

            # Determine nested path for loading this asset's subjects
            _pending_stack_11   = json.loads(props.asset_mode_stack or "[]")
            _pending_parents_11 = [e["asset_name"] for e in _pending_stack_11]
            _nested_comps_11    = _pending_parents_11 + [asset_label]
            _pc_arg             = _nested_comps_11 if len(_nested_comps_11) > 1 else None

            # Try to load iteration-specific snapshot first, then asset-level file.
            # If neither exists, fall back to the components embedded in the parent
            # subject entry (populated by ExitAssetMode auto-sync or Apply to Parent).
            _active_iter = _ws.read_asset_history(
                context, asset_label).get("active_index", 0)
            _iter_json = _ws.load_asset_iteration_subjects_json(
                context, asset_label, _active_iter)
            _asset_json = _iter_json or _ws.load_asset_subjects_json(
                context, asset_label, path_components=_pc_arg)

            # Fallback: extract components from the parent snapshot's matching subject.
            if not _asset_json and props.asset_prev_subjects:
                try:
                    _parent_snap = json.loads(props.asset_prev_subjects)
                    for _ps in _parent_snap.get("subject_matter", []):
                        if _ps.get("label") == asset_label:
                            _comps = (_ps.get("components")
                                      or _ps.get("nested_subjects"))
                            if _comps:
                                _seeded = {
                                    "mode": "asset",
                                    "metadata": _parent_snap.get("metadata", {}),
                                    "visual_style": _parent_snap.get("visual_style", {}),
                                    "composition": {
                                        "camera_angle": "",
                                        "framing": "",
                                    },
                                    "subject_matter": _comps,
                                    "thematic_tags": [],
                                }
                                _asset_json = json.dumps(_seeded, indent=2)
                                print(f"[Asset Mode] Seeded subjects from parent "
                                      f"components for '{asset_label}'")
                            break
                except Exception as _cse:
                    print(f"[Asset Mode] ⚠ Parent components fallback failed: {_cse}")

            if _asset_json:
                _up._populate_refine_from_json(props, _asset_json)
                # Inherit parent visual_style when the asset has no override yet
                if not any([props.refine_style_art_style,
                            props.refine_style_medium,
                            props.refine_style_lighting]):
                    props.refine_style_art_style = _parent_vs["art_style"]
                    props.refine_style_medium    = _parent_vs["medium"]
                    props.refine_style_lighting  = _parent_vs["lighting_condition"]
                    print(f"[Asset Mode] Visual style inherited from parent for '{asset_label}'")
                # Auto-expand all component rows so fields are immediately visible
                for _subj in props.refine_subjects:
                    _subj.show_expanded = True
                print(f"[Asset Mode] Subjects JSON loaded for '{asset_label}'")
            else:
                # Brand-new asset — clear subjects and inherit visual_style from parent
                props.refine_subjects.clear()
                props.refine_style_art_style = _parent_vs["art_style"]
                props.refine_style_medium    = _parent_vs["medium"]
                props.refine_style_lighting  = _parent_vs["lighting_condition"]
                print(f"[Asset Mode] No subjects JSON found — cleared for '{asset_label}', "
                      f"visual style inherited from parent")
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

        # Resolve the full ancestry chain (stack + current) so directory and
        # camera lookups are unique even when two assets share a leaf name.
        _nprops     = context.scene.style_engine_props
        path_comps  = _ws.get_asset_path_components(_nprops)
        # Fallback: if props not yet updated, build it manually.
        if not path_comps:
            path_comps = [label]

        # ── Skip if the asset already has saved images ────────────────────
        asset_dir   = _ws.ensure_asset_directory(context, label,
                                                 path_components=path_comps
                                                 if len(path_comps) > 1 else None)
        images_dir  = asset_dir / "Images"
        existing    = sorted(images_dir.glob("*.png")) if images_dir.exists() else []
        if existing:
            latest     = existing[-1]
            if len(path_comps) > 1:
                asset_temp = _ws.get_nested_asset_directory(context, path_comps) / "temp"
                asset_temp.mkdir(parents=True, exist_ok=True)
            else:
                asset_temp = _ws.get_asset_temp_directory(context, label)
            try:
                _shutil.copy2(latest, asset_temp / "current_ai.png")
                _ws.refresh_asset_camera_image(label, path_components=path_comps)
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
        # Use the full ancestry chain so nested cameras are found by their
        # path-qualified name (e.g. asset_camera_gollum_trinkets).
        try:
            from . import workspace_setup as _ws
            _exit_comps = _ws.get_asset_path_components(props)
        except Exception:
            _exit_comps = []
        _asset_cam_name = _get_asset_camera_name(
            _exit_comps if _exit_comps else props.current_asset_name
        )
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

            # Auto-sync: inject current asset subjects as 'components' on the
            # matching parent subject entry so the fractal JSON stays in sync.
            if asset_label and props.asset_prev_subjects:
                try:
                    _parent_snap = json.loads(props.asset_prev_subjects)
                    def _subject_to_dict(_s):
                        _e = {
                            "label":    _s.label,
                            "style":    _s.style,
                            "scale":    _s.scale,
                            "color":    _s.color,
                            "material": _s.material,
                        }
                        _feats = [f.value for f in _s.features if f.value.strip()]
                        if _feats:
                            _e["features"] = _feats
                        if _s.components_json:
                            try:
                                _e["components"] = json.loads(_s.components_json)
                            except Exception:
                                pass
                        return _e

                    _child_subjects = [_subject_to_dict(_s) for _s in props.refine_subjects]
                    for _pe in _parent_snap.get("subject_matter", []):
                        if _pe.get("label") == asset_label:
                            _pe["components"] = _child_subjects
                            # Write back any identity edits made in the identity box
                            if props.asset_subject_style:
                                _pe["style"]    = props.asset_subject_style
                            if props.asset_subject_scale:
                                _pe["scale"]    = props.asset_subject_scale
                            if props.asset_subject_color:
                                _pe["color"]    = props.asset_subject_color
                            if props.asset_subject_material:
                                _pe["material"] = props.asset_subject_material
                            # Write back asset-level features
                            _exit_feats = [f.value for f in props.asset_subject_features
                                           if f.value.strip()]
                            if _exit_feats:
                                _pe["features"] = _exit_feats
                            elif "features" in _pe and not _exit_feats:
                                # User cleared all features — reflect that in parent
                                _pe.pop("features", None)
                            break
                    props.asset_prev_subjects = json.dumps(_parent_snap, indent=2)
                    print(f"[Asset Mode] Auto-synced components → parent for '{asset_label}'")
                except Exception as _ase:
                    print(f"[Asset Mode] ⚠ Auto-sync to parent failed: {_ase}")

            # Restore the scene subjects from the (now updated) snapshot
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
            _vs = _snapshot.get("prev_visual_style", {})
            props.refine_style_art_style    = _vs.get("art_style", "")
            props.refine_style_medium       = _vs.get("medium", "")
            props.refine_style_lighting     = _vs.get("lighting_condition", "")
            # Restore the paused level's identity
            props.asset_subject_style    = _snapshot.get("asset_subject_style",    "")
            props.asset_subject_scale    = _snapshot.get("asset_subject_scale",    "")
            props.asset_subject_color    = _snapshot.get("asset_subject_color",    "")
            props.asset_subject_material = _snapshot.get("asset_subject_material", "")
            props.asset_subject_features.clear()
            for _feat_str in _snapshot.get("asset_subject_features", []):
                if isinstance(_feat_str, str) and _feat_str.strip():
                    _fi = props.asset_subject_features.add()
                    _fi.value = _feat_str
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
            props.asset_prev_resolution_x  = 0   # 0 = sentinel: nothing to restore on next load
            props.asset_prev_resolution_y  = 0
            props.asset_prev_prompt        = ""
            props.asset_prev_subjects      = ""
            props.asset_mode_stack         = "[]"
            props.asset_mode_depth         = 0
            # Clear identity fields — back in scene mode they are irrelevant
            props.asset_subject_style    = ""
            props.asset_subject_scale    = ""
            props.asset_subject_color    = ""
            props.asset_subject_material = ""
            props.asset_subject_features.clear()

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

        # ── Resolve the real Blender object name ──────────────────────────────
        # The label is always the base name (e.g. "cake") but the actual Blender
        # object may be a versioned MESH like "cake.001".  We collect ALL candidates
        # (exact name, versioned variants, link-map entry) and always prefer a MESH
        # over an EMPTY placeholder — this handles stale link maps and leftover
        # placeholder empties from previous sessions.

        try:
            _link_map = json.loads(props.asset_object_links or "{}")
        except Exception:
            _link_map = {}

        resolved_name = _link_map.get(target_name, target_name)

        # Gather every candidate: the link-map resolved name, the bare label, and
        # any versioned variant (label.001, label.002, …).
        _candidates = []
        for _o in bpy.data.objects:
            if _o.type not in {'MESH', 'EMPTY'}:
                continue
            if _o.name in (resolved_name, target_name):
                _candidates.append(_o)
            elif (_o.name.startswith(target_name + ".")
                    and _o.name[len(target_name) + 1:].isdigit()):
                _candidates.append(_o)

        # Always prefer a MESH over an EMPTY (EMPTY is just a placeholder).
        # Among MESHes prefer the link-map resolved name, then the highest version.
        _meshes  = [o for o in _candidates if o.type == 'MESH']
        _empties = [o for o in _candidates if o.type == 'EMPTY']

        if _meshes:
            # Prefer the exact name from the link map; otherwise take the first mesh
            target_obj = (bpy.data.objects.get(resolved_name)
                          if bpy.data.objects.get(resolved_name) in _meshes
                          else _meshes[0])
            if target_obj not in _meshes:
                target_obj = _meshes[0]
            print(f"[Asset Mode] 🔍 Resolved '{target_name}' → MESH '{target_obj.name}'")
        elif _empties:
            target_obj = _empties[0]
            print(f"[Asset Mode] 🔍 Resolved '{target_name}' → EMPTY '{target_obj.name}'")
        else:
            # Nothing exists — create an EMPTY placeholder
            target_obj = bpy.data.objects.new(target_name, None)  # None data = Empty
            target_obj.empty_display_type = 'ARROWS'
            target_obj.empty_display_size = 0.2
            context.scene.collection.objects.link(target_obj)
            print(f"[Asset Mode] 📦 Created EMPTY placeholder: {target_name}")

        # Make it the active object
        context.view_layer.objects.active = target_obj
        target_obj.select_set(True)

        # Pre-seed the link so EnterAssetMode fires Tier 1 immediately.
        # Always store the REAL object name (e.g. "transistor.001"), never the bare label,
        # so the isolation loop in EnterAssetMode correctly spares this object.
        subj.linked_object_name = target_obj.name
        props.asset_subject_index = self.subject_index

        # Write the correct real→name mapping back (never overwrite with bare label).
        _link_map[subj.label] = target_obj.name
        props.asset_object_links = json.dumps(_link_map)

        print(f"[Asset Mode] 🔗 EditAsset: pre-seeded link subject[{self.subject_index}]"
              f" '{subj.label}' → '{target_obj.name}'")

        # Pass the active object explicitly so EnterAssetMode.poll() sees it
        # even when called from the N-panel (where context may lag behind the
        # view_layer assignment we just made above).
        with context.temp_override(active_object=target_obj):
            return bpy.ops.style_engine.enter_asset_mode('INVOKE_DEFAULT')


class STYLEENGINE_OT_SAM3IsolateAsset(bpy.types.Operator):
    """Run SAM3 segmentation to isolate the active asset from the current image"""
    bl_idname  = "style_engine.sam3_isolate_asset"
    bl_label   = "Isolate Asset"
    bl_description = (
        "Use SAM3 segmentation to isolate the active asset by name from the "
        "current image. Result is saved as a history entry and becomes the "
        "new current_ai for this asset."
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.style_engine_props
        return getattr(props, 'asset_mode', False) and bool(getattr(props, 'current_asset_name', ''))

    def execute(self, context):
        from . import workspace_setup as _ws
        props  = context.scene.style_engine_props
        method = getattr(props, 'isolate_method', 'SAM3')

        if method == 'U2NET':
            print("[Isolate Asset] Using U2Net — no subject string needed")
            _ws.queue_u2net_isolate_workflow(context)
            self.report({'INFO'}, "U2Net isolation started")
        else:
            # SAM3: use the editable subject string
            subject = getattr(props, 'sam3_isolate_subject', '').strip()
            if not subject:
                subject = props.current_asset_name.replace("_", " ")
            if not subject:
                self.report({'ERROR'}, "No active asset name")
                return {'CANCELLED'}
            print(f"[Isolate Asset] SAM3 — subject: '{subject}'")
            _ws.queue_sam3_isolate_workflow(context, subject)
            self.report({'INFO'}, f"SAM3 isolation started: '{subject}'")
        return {'FINISHED'}


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

        # ── Asset header (name + camera — compact, non-editable) ─────────
        # The editable style/scale/color/material live inside the Refine
        # Image section so they sit in context with Components and Tags.
        id_box = layout.box()
        id_row = id_box.row(align=True)
        id_row.label(text=props.current_asset_name, icon='OBJECT_DATA')
        try:
            from . import workspace_setup as _ws
            _panel_comps = _ws.get_asset_path_components(props)
        except Exception:
            _panel_comps = []
        cam_name = _get_asset_camera_name(_panel_comps if _panel_comps else props.current_asset_name)
        id_row.label(text=cam_name, icon='CAMERA_DATA')

        # ── Active mesh display ───────────────────────────────────────────
        try:
            _subj_idx = props.asset_subject_index
            _linked   = (props.refine_subjects[_subj_idx].linked_object_name
                         if 0 <= _subj_idx < len(props.refine_subjects) else "")
        except Exception:
            _linked = ""
        mesh_box = layout.box()
        mesh_row = mesh_box.row()
        mesh_row.label(text="Active mesh:", icon='MESH_DATA')
        mesh_row.label(text=_linked if _linked else "(none)")

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
    STYLEENGINE_OT_SAM3IsolateAsset,
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
