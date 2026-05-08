# Blender Addon — Branching Context Push

**Document type:** Agent-to-Agent (A2A) specification  
**Audience:** The Blender addon coding agent  
**Hub counterpart changes:** None required — the hub already stores and indexes
any extra fields placed inside the `config` dict that `push_config` sends.  
**No new dependencies:** All changes use only `bpy`, `json`, and the standard
library already in use.

---

## Background

The hub now supports a lineage/branching graph view of all generations within a
session.  Every generation record already carries a `sources` array (written by
the addon today) that records which frame/canny/depth images it was derived from.

To make the graph aware of **where in Blender's scene hierarchy** each image was
produced (top-level scene vs. a named asset inside that scene vs. a nested
asset-within-asset), the hub needs three additional fields inside the `config`
dict that is sent in Step 2 of every push.

These fields map directly to three `StyleEngineProperties` that already exist on
`bpy.context.scene.style_engine_props` — no new properties, no new dependencies.

---

## The Change — one location, three lines

### File

`scripts/addons/styleengine/workspace_setup.py`

### Exact location

Find the `_hub_config` dict that is built immediately after snapshotting
`_props = _ctx.scene.style_engine_props`.  It currently reads:

```python
_hub_config = {
    "prompt":         _prompt,
    "temperature":    getattr(_props, "gemini_temperature", 1.0),
    "imageSize":      getattr(_props, "gemini_image_size", "1K"),
    "aspectRatio":    getattr(_props, "refine_meta_aspect", ""),
    "alignmentMode":  getattr(_props, "gemini_alignment", False),
    "model":          "gemini" if getattr(_props, "ai_model", "SDXL") == "GEMINI" else "sdxl",
}
```

### Replace with

```python
# ── context: where in the scene hierarchy this generation was produced ──
_is_asset    = getattr(_props, "asset_mode", False)
_asset_label = getattr(_props, "current_asset_name", "")
_asset_stack = []
try:
    import json as _json
    _asset_stack = [
        e.get("asset_name", "")
        for e in _json.loads(getattr(_props, "asset_mode_stack", "[]") or "[]")
    ]
except Exception:
    pass
_context_path = _asset_stack + ([_asset_label] if _is_asset and _asset_label else [])

_hub_config = {
    "prompt":         _prompt,
    "temperature":    getattr(_props, "gemini_temperature", 1.0),
    "imageSize":      getattr(_props, "gemini_image_size", "1K"),
    "aspectRatio":    getattr(_props, "refine_meta_aspect", ""),
    "alignmentMode":  getattr(_props, "gemini_alignment", False),
    "model":          "gemini" if getattr(_props, "ai_model", "SDXL") == "GEMINI" else "sdxl",
    # ── branching context (new) ────────────────────────────────────────
    "context": {
        "type":  "asset" if _is_asset else "scene",
        "label": _asset_label if _is_asset else "",
        "path":  _context_path,
    },
}
```

### What each field means

| Field | Type | Example values |
|---|---|---|
| `context.type` | `"scene"` \| `"asset"` | `"scene"` when in normal mode, `"asset"` when in Asset Mode |
| `context.label` | string | `""` in scene mode, `"helmet"` in asset mode |
| `context.path` | list of strings | `[]` in scene mode, `["knight"]` one level deep, `["knight", "helmet"]` nested |

`context.path` is the full ancestry chain from root to the current asset,
matching exactly what the viewport overlay watermark already renders
(`ASSET MODE — knight / helmet`).

---

## Why `SKIP_SAVE` is not a problem

All three source properties (`asset_mode`, `current_asset_name`,
`asset_mode_stack`) are declared with `options={'SKIP_SAVE'}`.  This means they
are runtime-only and reflect the **current live state of Blender at the moment
the push fires**.  That is exactly what we want — the context captured in the
push record should describe where the generation happened, not a stale saved
value.  No serialisation changes needed.

---

## Robustness requirements

- Wrap the entire context-building block in a `try/except Exception: pass` so
  that any unexpected property access failure never interrupts the push.  The
  block shown above already does this for the JSON parse; extend the outer guard
  to cover the whole section if preferred.
- If `asset_mode` is `False`, always emit `"type": "scene"`, `"label": ""`,
  `"path": []` — never `None`.
- If `asset_mode` is `True` but `current_asset_name` is somehow empty (e.g.
  the operator was interrupted), emit `"type": "asset"`, `"label": ""`,
  `"path": _asset_stack` — still valid, still useful.

---

## Verification

After the change, generate an image while in **Scene Mode**.  Open the hub's
Library, click the generation card, and inspect the raw config JSON (via the
lightbox panel or the API directly at
`GET /api/sessions/{session_id}/history/{gen_id}/config`).  You should see:

```json
"context": { "type": "scene", "label": "", "path": [] }
```

Then enter **Asset Mode** on any object and generate again.  The config should
read:

```json
"context": { "type": "asset", "label": "MyObject", "path": ["MyObject"] }
```

For a nested asset (`knight → helmet`):

```json
"context": { "type": "asset", "label": "helmet", "path": ["knight", "helmet"] }
```

No hub restart is needed.  The hub transparently stores whatever is inside
`config` and the new `context` sub-key will appear in the index on the next
`push_config` call.
