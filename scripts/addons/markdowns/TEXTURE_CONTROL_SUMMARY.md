# Texture Control - Quick Summary
**Feature:** img2img workflow with texture influence control  
**Status:** ✅ Ready to use

---

## 🎯 What Changed

Style Engine now uses **StyleEngineTexture.json** which transforms the workflow from **txt2img** to **img2img**:

### Before:
- Started from empty latent (pure AI)
- Render only used for ControlNet
- Fixed denoise (0.95)

### After:
- Starts from encoded render (img2img)
- Render provides base colors + ControlNet
- **Dynamic denoise** controlled by Texture slider

---

## 🎨 How to Use

**Location:** Pie Menu (Alt+W) → Bottom → Influences → **Texture slider**

```
Texture: 0.0 ──────────────────────→ 1.0
         ↑                           ↑
    Keep render                  Full AI
```

| Value | Effect |
|-------|--------|
| **0.0** | Keep 100% of render (minimal AI) |
| **0.3** | 70% render + 30% AI (subtle enhancement) |
| **0.5** | 50/50 blend (balanced) |
| **0.7** | 30% render + 70% AI (stylized) |
| **1.0** | 0% render + 100% AI (full generation) |

---

## 🔧 Technical Changes

1. ✅ **Workflow:** StyleEnginePreview.json → StyleEngineTexture.json
2. ✅ **Node 132:** NEW - VAEEncode (encodes render to latent)
3. ✅ **Node 135:** NEW - TextureStrength (controls denoise)
4. ✅ **Node 133:** Canny preview (was 134)
5. ✅ **Node 134:** Depth preview (was 135)
6. ✅ **Property:** texture_influence now active (was placeholder)
7. ✅ **Default:** Changed from 0.1 to 0.0 (preserve render)

---

## 📊 Use Cases

### Preserve Render (0.0 - 0.2)
- Final render polishing
- Client work
- Subtle adjustments

### Balanced Blend (0.3 - 0.7)
- Concept art
- Style exploration
- Creative variations

### Full AI (0.8 - 1.0)
- Dramatic changes
- Style transfer
- Maximum creativity

---

## ✅ What Works

- [x] Texture slider in pie menu
- [x] Maps to Node 135 (denoise control)
- [x] img2img workflow active
- [x] Preview images still download correctly
- [x] All existing features still work
- [x] No breaking changes

---

## 🚀 Quick Start

1. Press `Alt+W` (pie menu)
2. Look at **Bottom** → Influences section
3. Adjust **Texture** slider:
   - Left (0.0) = Keep your render
   - Middle (0.5) = Blend
   - Right (1.0) = Full AI
4. Generate and see the difference! 🎨

---

**Tip:** Start with 0.0-0.3 for subtle enhancements, or go 0.5+ for creative exploration!

