# Style Engine — Architecture Mappings Report

> Generated: 2026-05-04  
> Add-on version: 0.6.0 (`bl_info`)  
> Blender target: 4.2+

---

## Table of Contents

1. [Ports & Services](#1-ports--services)
2. [Connection Layer (Transport)](#2-connection-layer-transport)
3. [Connection Mode Selection](#3-connection-mode-selection)
4. [Workflow JSON → Operator Mapping](#4-workflow-json--operator-mapping)
   - [Image Generation (SDXL path)](#41-image-generation--sdxl-path)
   - [Image Generation (Gemini path)](#42-image-generation--gemini-path)
   - [SAM3 / Asset Isolation](#43-sam3--asset-isolation)
   - [3D Generation](#44-3d-generation)
   - [UV / Projection / Patch](#45-uv--projection--patch)
   - [PBR Workflows](#46-pbr-workflows)
   - [Text / Agent / Prompt](#47-text--agent--prompt)
   - [Asset Parent Update](#48-asset-parent-update)
5. [Workflow Files — Full Inventory](#5-workflow-files--full-inventory)
6. [Module Responsibilities](#6-module-responsibilities)
7. [Conceptual Space Map](#7-conceptual-space-map)
8. [Data Flow Summary](#8-data-flow-summary)

---

## 1. Ports & Services

| Port | Protocol | Service | Where defined | Who calls it from the add-on |
|------|----------|---------|--------------|------------------------------|
| **8188** | HTTP | Local ComfyUI backend (or RunComfy-proxied backend) | `runcomfy_deployment.py` default, `runcomfy_server_client.py` | `ComfyUIServerClient._request()` — all queue/upload/download calls |
| **8189** | HTTP | `scripts/bridge.py` — WebSocket relay from ComfyUI → HTTP status endpoint | `progress_bar.py` `BRIDGE_PORT = 8189` | `progress_bar.fetch_bridge_status()` polled every 2 s via `bpy.app.timers` |
| **8190** | HTTP | Hunyuan3D-Omni inference server (`context/omni_server.py`) | `ui_panel.py` `OMNI_PORT = 8190` | `WM_OT_OmniGenerate.execute()` — direct urllib POST |
| **8195** | HTTP | Trellis 3D generation service | `trellis_client.py` `TRELLIS_PORT = 8195` | `trellis_client.submit_generate()`, `submit_retexture()`, `poll_status()`, `download_glb()` |
| **7860** | HTTP | Hunyuan3D-Part — Gradio API | `ui_panel.py` `PART_PORT = 7860` | `WM_OT_SegmentMesh.execute()` — direct urllib call |
| **8000** | HTTP | `launcher/server.py` — dashboard / debug bridge | `launcher/main.py` | **Not called from the add-on itself.** External process for developer use only. |
| **`api.runcomfy.net`** | HTTPS | RunComfy Cloud REST API | `runcomfy_client.py` `API_BASE = "https://api.runcomfy.net"` | `RunComfyClient._request()` — cloud deployments, inference, status |

### Notes on the bridge (port 8189)

`scripts/bridge.py` is a small standalone FastAPI app run **outside Blender**. It:

- Opens a persistent WebSocket to ComfyUI at `ws://127.0.0.1:8188/ws?clientId=transposer_bridge_v1`
- Translates WS progress events (`execution_start`, `executing`, `progress`) into a simple JSON state object
- Exposes `GET /status` which the add-on's `progress_bar.py` polls

When queueing prompts to local ComfyUI, `runcomfy_server_client.py` sends `"client_id": "transposer_bridge_v1"` so ComfyUI routes progress events to the same WS channel the bridge is listening on.

---

## 2. Connection Layer (Transport)

All network calls from inside Blender use **Python stdlib only** (`urllib.request` / `urllib.error`). There is no `requests`, `httpx`, or `websockets` dependency in the add-on itself.

```
ComfyUIServerClient._request()         → urllib  → :8188
RunComfyClient._request()              → urllib  → api.runcomfy.net (HTTPS)
trellis_client.*()                     → urllib multipart  → :8195
WM_OT_OmniGenerate                     → urllib POST  → :8190
WM_OT_SegmentMesh                      → urllib  → :7860
progress_bar.fetch_bridge_status()     → urllib GET  → :8189/status
RunComfyServerManager._request()       → urllib  → api.runcomfy.net (server management)
```

`runcomfy_server_client.py` endpoints used:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/prompt` | Queue a workflow |
| GET | `/history/{prompt_id}` | Poll job result |
| GET | `/queue` | Check queue depth |
| POST | `/upload/image` | Upload image to ComfyUI input dir |
| POST | `/upload/model/3d` | Upload mesh/GLB |
| GET | `/view` | Download image or mesh |
| GET | `/object_info` | Health / node availability check |

---

## 3. Connection Mode Selection

`runcomfy_deployment.is_server_mode()` determines which backend is used at runtime:

```
gcs_server_url set in Preferences
        │
        ├─ YES → Server mode
        │         get_server_client()
        │         → ComfyUIServerClient(gcs_server_url : gcs_comfy_port)
        │           default port 8188, overridable via prefs
        │
        └─ NO  → Cloud mode
                  get_runcomfy_client()
                  → RunComfyClient(api_token, user_id)
                  → api.runcomfy.net HTTPS
                  → manage deployments via RunComfyServerManager
```

The `gcs_comfy_port` port priority:
1. `prefs.gcs_comfy_port` if explicitly changed from the default 8188
2. Port already embedded in `gcs_server_url` string
3. Fallback: **8188**

---

## 4. Workflow JSON → Operator Mapping

All workflow JSON files live under:
```
scripts/addons/styleengine/workflows/
    Image/
    Object/
    Text/
```

### 4.1 Image Generation — SDXL path

Triggered by the main **Generate** button when `ai_model != 'GEMINI'`.  
Logic in `workspace_setup.py` around line 5900.

| Condition | Workflow loaded |
|-----------|----------------|
| No ref images, no rembg | `Image/Image.json` |
| No ref images, rembg ON | `Image/ImageRB.json` |
| Ref images set, no rembg | `Image/ImageRef.json` |
| Ref images set, rembg ON | `Image/ImageRefRB.json` |
| Server API unified path (override) | `Image/SDXLREF.json` *(from `ComfyUI/runcomfyWorkflows/`)* |

IPAdapter reference slots (nodes 43, 44, 45, etc.) are only patched when `ImageRef.json` or `ImageRefRB.json` is loaded.

### 4.2 Image Generation — Gemini path

Triggered by the main **Generate** button when `props.ai_model == 'GEMINI'`.  
Logic in `workspace_setup.py` lines 5140–5280.

Decision matrix (three boolean flags evaluated in order):

| `has_gemini_refs` | `gemini_alignment` | `gemini_remove_bg` | Workflow loaded |
|:-----------------:|:------------------:|:------------------:|----------------|
| ✓ | — | ✗ | `Image/ImageNanoReference.json` |
| ✓ | — | ✓ | `Image/ImageNanoReferenceRB.json` |
| ✗ | ✓ | ✗ | `Image/ImageNanoAlignment.json` |
| ✗ | ✓ | ✓ | `Image/ImageNanoAlignmentRB.json` |
| ✗ | ✗ | ✗ | `Image/ImageNanoText.json` |
| ✗ | ✗ | ✓ | `Image/ImageNanoTextRB.json` |

Key Gemini-specific node patches:

| Node ID | Field patched | Source |
|---------|--------------|--------|
| `"63"` | `text` | `STYLEENGINE_Prompt` text block |
| `"65"` | `value` | `STYLEENGINE_Instructions` text block |
| `"56"` | `image` | Uploaded render (alignment / reference workflows only) |
| `"66"` | `value` | `templates/spatial_alignment.txt` content |
| `"50"` | `temperature`, `image_size`, `aspect_ratio` | Prefs + auto-detected render ratio |
| `"67"`–`"71"` | `image` | Gemini ref images 1–5 (Reference workflow only) |

### 4.3 SAM3 / Asset Isolation

All functions in `workspace_setup.py`.

| Function | Workflow JSON | Purpose |
|----------|-------------|---------|
| `queue_asset_isolation_workflow()` | `Image/AssetNanoAlignmentRB.json` | Extract single asset from scene image |
| `queue_sam3_rembg_workflow()` | `Image/SAM3Rembg.json` | Remove background via SAM3 |
| `queue_explode_workflow()` | `Image/ImageExplode.json` | Explode asset for inspection |
| `queue_u2net_workflow()` | `Image/u2netrembg.json` | Background removal via U2Net |
| `queue_apply_to_parent_workflow()` | `Image/ImageNanoAlignmentRef.json` or `Image/ImageNanoAlignmentRefRB.json` | Update parent `current_ai.png` after child asset edit |
| `STYLEENGINE_OT_SAM3IsolateAsset` (`asset_mode.py`) | Calls `queue_asset_isolation_workflow()` → `AssetNanoAlignmentRB.json` | Asset mode isolation button |
| `WM_OT_SegmentMesh` (`ui_panel.py`) | No local JSON — HTTP to **:7860** (Hunyuan3D-Part Gradio) | Mesh segmentation |

### 4.4 3D Generation

| Operator | Workflow / Backend | Notes |
|----------|-------------------|-------|
| `WM_OT_Nano3DGenerate` | `Object/objectCreateObject.json` → ComfyUI | Mesh from image via ComfyUI |
| `WM_OT_TrellisGenerate` | `trellis_client.submit_generate()` → **:8195** | No local JSON; pre-step uses `Image/UtilsImageRB.json` for rembg |
| `WM_OT_TrellisRetexture` | `trellis_client.submit_retexture()` → **:8195** | Same rembg pre-step |
| `WM_OT_OmniGenerate` | HTTP POST → **:8190** | Hunyuan3D-Omni; no local workflow JSON |

`WM_OT_TrellisGenerate` / `WM_OT_TrellisRetexture` pre-step:
1. Upload `current_ai.png` to ComfyUI
2. Queue `Image/UtilsImageRB.json` (InspyrenetRembg) on :8188
3. Download result
4. Submit cleaned image to Trellis :8195

### 4.5 UV / Projection / Patch

| Operator | Workflow JSON | Module |
|----------|-------------|--------|
| `WM_OT_UVTexture` (pie) | `Object/objectUVTexture.json` | `pie_menu.py` |
| `WM_OT_CreateObject` (pie) | `Object/objectCreateObject.json` | `pie_menu.py` |
| `WM_OT_CreateTexturedObject` (pie) | `Object/objectCreateTexturedObject.json` | `pie_menu.py` |
| `WM_OT_ApplyPatch` | `Object/objectPatch.json` | `ui_panel.py` |
| `WM_OT_MultiviewFromProjected` | `Image/ImageRef.json` (refs set) or `Image/Image.json` | `ui_panel.py` |
| `WM_OT_ProjectTextureScene` (pie) | Calls `WM_OT_ProjectTexture` → render + queue | `pie_menu.py` |

### 4.6 PBR Workflows

| Operator | Workflow JSON | Condition |
|----------|-------------|-----------|
| `WM_OT_PBRFromProjectedTexture` | `Object/objectPBRproject.json` | Always |
| `WM_OT_PBRFromText` | `Object/objectNanoPBRtext.json` | Gemini model path |
| `WM_OT_PBRFromText` | `Object/objectPBRtext.json` | Non-Gemini fallback |

### 4.7 Text / Agent / Prompt

Two profiles selectable in preferences (`workflow_profile` property):

| Operator | Profile | Workflow JSON | Key nodes |
|----------|---------|-------------|-----------|
| `WM_OT_RefinePrompt` | DEFAULT | `Text/TextRefine.json` | Text node `"7"` |
| `WM_OT_RefinePrompt` | BLACKHAMSTER | `Text/AgentTextRefine.json` | Griptape agent node `"9"` |
| `WM_OT_GenerateImageDescription` | DEFAULT | `Text/TextImage.json` | LoadImage `"23"` |
| `WM_OT_GenerateImageDescription` | BLACKHAMSTER | `Text/AgentImageRefine.json` | LoadImage `"11"` |
| `WM_OT_GenerateImageDescriptionFromFile` | DEFAULT | `Text/TextImage.json` | LoadImage `"23"` |
| `WM_OT_GenerateImageDescriptionFromViewport` | DEFAULT | `Text/TextViewport.json` | LoadImage `"23"` |
| `WM_OT_GenerateImageDescriptionFromViewport` | BLACKHAMSTER | `Text/AgentImageRefine.json` | LoadImage `"11"` |
| AgentJSON dissect (no subject) | — | `Text/AgentJSON.json` | — |
| AgentJSON dissect (subjects exist) | — | `Text/AgentJSONMerge.json` | — |

### 4.8 Asset Parent Update

| Function | Workflow JSON | Condition |
|----------|-------------|-----------|
| `queue_apply_to_parent_workflow()` | `Image/ImageNanoAlignmentRefRB.json` | Parent has component assets |
| `queue_apply_to_parent_workflow()` | `Image/ImageNanoAlignmentRef.json` | Parent has no component assets |

---

## 5. Workflow Files — Full Inventory

All 34 JSON files in `scripts/addons/styleengine/workflows/`:

### Image/

| File | Status | Called by |
|------|--------|-----------|
| `Image.json` | ✅ Active | SDXL generate — no refs, no rembg |
| `ImageRB.json` | ✅ Active | SDXL generate — no refs, rembg ON |
| `ImageRef.json` | ✅ Active | SDXL generate — refs set, no rembg; also `WM_OT_MultiviewFromProjected` |
| `ImageRefRB.json` | ✅ Active | SDXL generate — refs set, rembg ON |
| `ImageNanoAlignment.json` | ✅ Active | Gemini generate — alignment ON, no rembg |
| `ImageNanoAlignmentRB.json` | ✅ Active | Gemini generate — alignment ON, rembg ON |
| `ImageNanoAlignmentRef.json` | ✅ Active | `queue_apply_to_parent_workflow()` — no components |
| `ImageNanoAlignmentRefRB.json` | ✅ Active | `queue_apply_to_parent_workflow()` — has components |
| `ImageNanoReference.json` | ✅ Active | Gemini generate — refs set, no rembg |
| `ImageNanoReferenceRB.json` | ✅ Active | Gemini generate — refs set, rembg ON |
| `ImageNanoText.json` | ✅ Active | Gemini generate — text only, no rembg |
| `ImageNanoTextRB.json` | ✅ Active | Gemini generate — text only, rembg ON |
| `AssetNanoAlignmentRB.json` | ✅ Active | `queue_asset_isolation_workflow()`, `queue_apply_to_parent_workflow()` (dynamic) |
| `SAM3Rembg.json` | ✅ Active | `queue_sam3_rembg_workflow()` |
| `ImageExplode.json` | ✅ Active | `queue_explode_workflow()` |
| `u2netrembg.json` | ✅ Active | `queue_u2net_workflow()` |
| `UtilsImageRB.json` | ✅ Active | Trellis pre-step (rembg before Trellis submit) |
| `ImageSAM3.json` | ⚠️ Present | Not found referenced in current Python — reserved / future |
| `TestImageNano.json` | ✅ Active | `WM_OT_NanoGenerate` (non-Gemini nano path) |

### Object/

| File | Status | Called by |
|------|--------|-----------|
| `objectCreateObject.json` | ✅ Active | `WM_OT_Nano3DGenerate`, `WM_OT_CreateObject` (pie) |
| `objectCreateTexturedObject.json` | ✅ Active | `WM_OT_CreateTexturedObject` (pie) |
| `objectUVTexture.json` | ✅ Active | `WM_OT_UVTexture` (pie) |
| `objectPatch.json` | ✅ Active | `WM_OT_ApplyPatch` |
| `objectPBRproject.json` | ✅ Active | `WM_OT_PBRFromProjectedTexture` |
| `objectPBRtext.json` | ✅ Active | `WM_OT_PBRFromText` (non-Gemini fallback) |
| `objectNanoPBRtext.json` | ✅ Active | `WM_OT_PBRFromText` (Gemini path) |

### Text/

| File | Status | Called by |
|------|--------|-----------|
| `TextRefine.json` | ✅ Active | `WM_OT_RefinePrompt` (DEFAULT profile) |
| `TextImage.json` | ✅ Active | `WM_OT_GenerateImageDescription` / `FromFile` (DEFAULT) |
| `TextViewport.json` | ✅ Active | `WM_OT_GenerateImageDescriptionFromViewport` (DEFAULT) |
| `AgentTextRefine.json` | ✅ Active | `WM_OT_RefinePrompt` (BLACKHAMSTER profile) |
| `AgentImageRefine.json` | ✅ Active | `WM_OT_GenerateImageDescription` / `FromViewport` (BLACKHAMSTER) |
| `AgentJSON.json` | ✅ Active | AgentJSON dissect (no existing subjects) |
| `AgentJSONMerge.json` | ✅ Active | AgentJSON dissect (subjects already exist) |

---

## 6. Module Responsibilities

| Module | Core responsibility |
|--------|-------------------|
| `__init__.py` | Registration, macOS import fallback, Blender app handlers |
| `prefs.py` | `StyleEnginePreferences`: all credentials, server URLs, RunComfy settings, connection test operators |
| `workspace_setup.py` | AI workspace layout, session.json, all GCS/Gemini generate flows, SAM3/asset isolation queue functions, save/load handlers |
| `ui_panel.py` | Main N-panel, `StyleEngineProperties`, most generation operators (Nano, Nano3D, Omni, Trellis, Patch, Multiview, PBR, text/agent, group management) |
| `asset_mode.py` | Asset mode enter/exit, SAM3 isolate, asset history, dedicated asset panel |
| `pie_menu.py` | Pie menus (main, texture, 3D, refine, agent, view), UV texture, create object, create textured object operators |
| `runcomfy_client.py` | `RunComfyClient` — cloud REST: deployments, inference, status, result download |
| `runcomfy_server_client.py` | `ComfyUIServerClient` — local/proxied ComfyUI: queue, upload, download, health |
| `runcomfy_deployment.py` | Mode selection (`is_server_mode()`), `_build_server_url()`, factory functions `get_server_client()` / `get_runcomfy_client()` |
| `runcomfy_server_manager.py` | `RunComfyServerManager` — cloud server start/stop/wait via RunComfy API |
| `runcomfy_polling.py` | `RunComfyPoller` — async job polling with callbacks; `cleanup_poller()` on unregister |
| `progress_bar.py` | Bridge HTTP polling every 2 s, Blender UI progress display |
| `trellis_client.py` | Trellis HTTP: health, submit generate/retexture, poll, download GLB |
| `heavypoly_integration.py` | HeavyPoly UX hooks: quick render, quick generate, refine, explode |
| `utils.py` | Credentials parsing, prompt helpers, template system, `build_reference_workflow()` |

---

## 7. Conceptual Space Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLENDER N-PANEL / PIE MENUS                  │
│  ui_panel.py · pie_menu.py · asset_mode.py · heavypoly_*.py    │
└────────────────────────────┬────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────────┐
          │                  │                      │
   ┌──────▼──────┐   ┌──────▼──────┐      ┌────────▼──────────┐
   │  Image Gen  │   │   3D Gen    │      │  Text / Agent     │
   │  SDXL path  │   │  Trellis    │      │  Refine / Descr   │
   │  Gemini path│   │  Omni       │      │  AgentJSON        │
   │  SAM3/Asset │   │  Nano3D     │      │  Prompt templates │
   └──────┬──────┘   └──────┬──────┘      └────────┬──────────┘
          │                  │                      │
          └──────────────────┼──────────────────────┘
                             │
   ┌─────────────────────────▼───────────────────────────────────┐
   │               TRANSPORT (stdlib urllib only)                 │
   ├─────────────┬──────────────┬───────────┬────────┬───────────┤
   │  ComfyUI    │  RunComfy    │  Trellis  │  Omni  │  Part     │
   │  :8188      │  cloud HTTPS │  :8195    │  :8190 │  :7860    │
   └─────────────┴──────────────┴───────────┴────────┴───────────┘
                             │
   ┌─────────────────────────▼───────────────────────────────────┐
   │               PROGRESS FEEDBACK                              │
   │  bridge.py :8189  ← WebSocket ← ComfyUI :8188               │
   │  progress_bar.py polls :8189/status every 2 s               │
   └─────────────────────────────────────────────────────────────┘
```

---

## 8. Data Flow Summary

### Standard generation cycle (server mode, Gemini example)

```
1. User presses Generate in N-panel
        ↓
2. workspace_setup.py reads props.ai_model == 'GEMINI'
   Selects workflow JSON from 6-variant matrix
        ↓
3. Render current viewport → combined PNG saved to temp dir
        ↓
4. server_client.upload_image() → POST :8188/upload/image
        ↓
5. Patch workflow JSON nodes (prompt, alignment, refs, temperature…)
        ↓
6. server_client.queue_prompt(workflow_json) → POST :8188/prompt
   with client_id = "transposer_bridge_v1"
        ↓
7. runcomfy_polling.RunComfyPoller watches job via
   server_client.wait_for_completion() / get_history()
        ↓
8. (Parallel) progress_bar polls :8189/status every 2 s
   bridge.py translates WS events → UI progress bar
        ↓
9. On completion: server_client.download_image() → GET :8188/view
   Result saved as current_ai.png
        ↓
10. Blender image datablock refreshed → AI viewport updates
```

### Asset isolation cycle

```
1. User enters Asset Mode (asset_mode.py)
        ↓
2. queue_asset_isolation_workflow()
   Uploads scene image → POST :8188/upload/image
   Queues AssetNanoAlignmentRB.json → POST :8188/prompt
        ↓
3. On completion: downloads extracted asset PNG
        ↓
4. (Optional) queue_sam3_rembg_workflow() → SAM3Rembg.json
   Background removal for clean asset
        ↓
5. Asset saved to Models/<label>/  with asset_history.json sidecar
```

### Trellis cycle

```
1. WM_OT_TrellisGenerate
        ↓
2. (If remove_bg) Queue UtilsImageRB.json → :8188 → download clean PNG
        ↓
3. trellis_client.submit_generate() → POST :8195/generate
        ↓
4. trellis_client.poll_status() loop until done
        ↓
5. trellis_client.download_glb() → GET :8195/result/{job_id}
        ↓
6. GLB imported into Blender scene
```

---

*This document was generated from source analysis of the Style Engine v0.6.0 codebase.*
