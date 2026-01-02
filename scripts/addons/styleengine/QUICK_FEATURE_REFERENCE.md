# Quick Feature Reference - Style Engine v0.3.3

**Last Updated**: December 29, 2025

---

## 🎨 LoRa Model Selection

### Location
Pie Menu (`Shift+E`) → Generate Image → LoRa section

### Quick Steps
1. Enable "Use LoRa"
2. Select model from dropdown (auto-fetched from server)
3. Adjust strength (0.0 to 1.0)
4. Generate!

### Code Location
- Properties: `ui_panel.py` lines 822-864
- UI: `pie_menu.py` lines 348-387
- Workflow: `workspace_setup.py` lines 2262-2282

### Console Check
```
[Style Engine] ✓ Found 10 LoRa models on server
[GCS] 🎨 LoRa enabled: xl_more_art-full_v1.safetensors
```

---

## 🎯 UV Texture Generation

### Location
Pie Menu (`Shift+E`) → Object → UV Texture

### Quick Steps
1. Generate an AI image (creates current_ai.png)
2. Select a mesh object
3. Click "UV Texture"
4. Wait 1-2 minutes
5. Textured mesh appears!

### Code Location
- Upload/Download: `runcomfy_server_client.py` lines 286-396
- Operator: `pie_menu.py` lines 27-197
- Workflow: `workflows/objectUVTexture.json`

### Console Check
```
[UV Texture] STARTING UV TEXTURE GENERATION
[UV Texture] ✓ Uploaded as: Cube_1735516800.glb
[UV Texture] ✓ Generation complete!
[UV Texture] ✓ Imported: Cube_Textured
```

---

## 📋 Quick Troubleshooting

### LoRa Issues
| Problem | Solution |
|---------|----------|
| Only shows "None" + one LoRa | Check GCS mode, test server connection |
| Can't see new LoRas | Click refresh button (🔄) |
| LoRa not applied | Check "Use LoRa" is enabled |

### UV Texture Issues
| Problem | Solution |
|---------|----------|
| "Requires GCS mode" | Switch backend to GCS in preferences |
| "current_ai.png not found" | Generate an image first |
| "No object selected" | Select a mesh object |
| Timeout | Check server, simplify mesh |

---

## 🔗 Full Documentation

- **LoRa**: `docs/LORA_FEATURE_IMPLEMENTATION.md`
- **UV Texture**: `docs/UV_TEXTURE_FEATURE.md`
- **Implementation**: `docs/IMPLEMENTATION_SUMMARY_2025-12-29.md`
- **Changelog**: `docs/CHANGELOG.md`

---

## 🎯 Node Quick Reference

### StyleEngineTexture.json (Main Workflow)
```
Node 34  → LoraLoader (lora_name, strength_model)
Node 25  → Prompt
Node 15  → Input image (combined pass)
Node 40  → Canny strength
Node 41  → Depth strength
Node 135 → Texture influence
Node 53  → Final output
```

### objectUVTexture.json (UV Texture Workflow)
```
Node 55  → TrimeshLoad (load mesh)
Node 14  → Image input (current_ai.png)
Node 32  → Output filename
Node 20  → MultiViews Generator (6 angles)
Node 49  → InPaint (seam filling)
Node 44  → Export result
```

---

## ⚡ Quick Commands

### Refresh LoRa List
```python
bpy.ops.style_engine.refresh_lora_list()
```

### Check LoRa Cache
```python
from styleengine import ui_panel
print(ui_panel._lora_cache)
```

### Manual UV Texture
```python
# Select object first
bpy.ops.style_engine.uv_texture()
```

---

**Version**: 0.3.3  
**Status**: All features operational  
**Ready**: For production use

