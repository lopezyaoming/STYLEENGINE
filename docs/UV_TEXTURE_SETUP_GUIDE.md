# UV Texture Setup Guide

**Quick Setup for UV Texture Feature**

---

## ⚙️ Required: Set ComfyUI Path

The UV Texture feature needs to know where ComfyUI is installed on your server to construct proper file paths.

### How to Set

1. **Open Blender Preferences**:
   - Edit → Preferences → Add-ons
   - Find "Style Engine"
   - Expand addon details

2. **Expand Advanced Settings**:
   - Click "Advanced Settings" to expand

3. **Set ComfyUI Path**:
   - Find "ComfyUI Installation" section
   - Path field: Enter your server's ComfyUI path
   - **Example**: `/home/Juan/ComfyUI`

4. **Save Preferences**

---

## 🖥️ Common Paths

### Linux/GCS Server
```
/home/Juan/ComfyUI
/home/ubuntu/ComfyUI
/opt/ComfyUI
```

### Windows
```
C:/ComfyUI
D:/AI/ComfyUI
```

### macOS
```
/Users/username/ComfyUI
~/ComfyUI
```

---

## 🔍 How to Find Your Path

### Method 1: SSH into Server
```bash
ssh user@your-server
cd ComfyUI
pwd
# Output: /home/Juan/ComfyUI  ← Use this!
```

### Method 2: Check ComfyUI Startup
When ComfyUI starts, it prints:
```
Starting server
Working directory: /home/Juan/ComfyUI  ← Use this!
```

### Method 3: Check Workflow JSON
Look at your existing workflow:
```json
"55": {
  "inputs": {
    "load_path": "/home/Juan/ComfyUI/output/Hy21_Mesh_00006_.glb"
                  ^^^^^^^^^^^^^^^^^^^^^ This is the base path!
  }
}
```

---

## ✅ Verify Setup

After setting the path:

1. **Check console** when running UV Texture:
   ```
   [UV Texture] ✓ Node 55 (mesh): /home/Juan/ComfyUI/input/Mr.Cube_XXX.glb
   ```

2. **Should see full path** starting with your ComfyUI installation

3. **No errors** about "string is not a file"

---

## 🐛 Troubleshooting

### Error: "string is not a file: `filename.glb`"

**Cause**: ComfyUI path not set or incorrect

**Solution**:
1. Set ComfyUI path in preferences
2. Verify path matches your server
3. Reload scripts (F3 → "Reload Scripts")
4. Try UV Texture again

### Error: "File not found"

**Cause**: Path is set but incorrect

**Solution**:
1. SSH into server and verify path with `pwd`
2. Update path in preferences
3. Make sure to use forward slashes (`/`) even on Windows

---

## 💡 Why This Is Needed

**TrimeshLoad node** (Node 55) requires an **absolute file path** on the server:
- ✅ Correct: `/home/Juan/ComfyUI/input/mesh.glb`
- ❌ Wrong: `mesh.glb`

**LoadImage node** (Node 14) works with just the filename:
- ✅ Correct: `current_ai.png` (ComfyUI finds it automatically)

Different nodes, different requirements!

---

## 🎯 Quick Fix

If you don't want to set it in preferences, you can hardcode it temporarily in the code:

**File**: `pie_menu.py` (around line 135)

```python
# Quick hardcode (temporary)
comfy_base_path = "/home/Juan/ComfyUI"  # Your server path
```

But **setting in preferences is better** for long-term use!

---

**After setting the path, reload scripts and try UV Texture again!** 🚀

