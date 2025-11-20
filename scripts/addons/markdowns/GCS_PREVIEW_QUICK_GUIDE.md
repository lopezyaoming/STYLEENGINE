# GCS Preview Images - Quick Guide
**Feature:** Download Canny & Depth preview images  
**Status:** ✅ Ready to use

---

## 🎯 What It Does

Downloads 3 images instead of 1:
- **current_ai.png** - Your final generated image (always)
- **canny.png** - Edge detection map (optional)
- **depth.png** - Depth map (optional)

---

## 🔧 How to Enable

1. Open Blender Preferences (`Edit → Preferences`)
2. Go to `Add-ons → Style Engine`
3. Set **Backend Mode** to `Self-Hosted ComfyUI`
4. Find **Preview Images** section
5. Check ☑ **Download Canny & Depth Maps**

---

## 📁 Where Are They Saved?

```
C:\Users\Juan\AppData\Local\Temp\blender_styleengine\ai_vision\
├── current_ai.png  ← Always downloaded
├── canny.png       ← If enabled
└── depth.png       ← If enabled
```

---

## ⚡ Performance

| Setting | Images | Bandwidth | Time |
|---------|--------|-----------|------|
| **Disabled** (default) | 1 | ~1 MB | ~500ms |
| **Enabled** | 3 | ~3 MB | ~1.5s |

---

## 💡 When to Use

### ✅ Enable When:
- Debugging ControlNet issues
- Learning how preprocessors work
- Quality control checks
- Documenting your process

### ❌ Keep Disabled When:
- Production workflow (default)
- Bandwidth is limited
- Speed is priority
- You only need final image

---

## 🎨 What You'll See

### Canny Preview
- White edges on black background
- Shows detected contours and silhouettes
- Helps understand edge influence

### Depth Preview
- Grayscale depth map
- Bright = near, dark = far
- Shows spatial understanding

---

## ⚙️ Requirements

- **Workflow:** Must use `StyleEnginePreview.json` (has SaveImage nodes)
- **Backend:** GCS mode only (not RunComfy)
- **Blender:** Any version with Style Engine addon

---

## 🐛 Troubleshooting

**Preview images not downloading?**
- Check that toggle is enabled in preferences
- Verify you're using `StyleEnginePreview.json` workflow
- Check console for error messages

**Images are black/empty?**
- ControlNet preprocessors may need different settings
- Check that input image has visible edges/depth

---

**Quick Tip:** Keep this disabled by default. Only enable when you need to debug or learn! 🚀

