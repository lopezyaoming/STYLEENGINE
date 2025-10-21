# Testing the Auto-Refresh Feature

## Quick Test Guide

### Step 1: Setup Workspace ✨

1. Open Blender
2. Press `N` in 3D Viewport
3. Click "Style Engine" tab
4. Click **"Setup Workspace"** button

**Expected**:
- Two viewports appear (left and right)
- Console shows: `[Style Engine] Auto-refresh timer started`
- Blue placeholder visible in right viewport

---

### Step 2: Verify Directory Structure 📁

Navigate to your project folder and verify:

```
YourProject/
├── YourBlendFile.blend
└── data/                    ← Should exist now
    └── temp/
        └── ai_vision/
            └── current_ai.png    ← Blue placeholder image
```

---

### Step 3: Test Auto-Refresh 🔄

#### Option A: Use Any Image

1. Find any image file (PNG, JPG, etc.)
2. **Resize it to 1920x1080** (or any size)
3. **Save as**: `data/temp/ai_vision/current_ai.png` (overwrite existing)
4. **Watch Blender**: Within ~1 second, the image should update!
5. **Check console**: Should show `[Style Engine] Image reloaded: current_ai.png`

#### Option B: Paint/Edit the Image

1. Open `data/temp/ai_vision/current_ai.png` in any image editor (Photoshop, GIMP, Paint, etc.)
2. Draw something on it
3. **Save** the file (overwrite)
4. **Watch Blender**: Image updates automatically!

#### Option C: Create Test Images

Create multiple test images and swap them:

```batch
# Windows Command Prompt
cd data\temp\ai_vision
copy test_image_1.png current_ai.png
# Wait, see it update in Blender
copy test_image_2.png current_ai.png
# Watch it update again!
```

---

### Step 4: Test Manual Controls ⏯️

#### Stop Auto-Refresh

1. In Style Engine panel, click **"Stop Refresh"**
2. Update the `current_ai.png` file
3. ✅ Verify: Image does NOT update in Blender
4. Console shows: `[Style Engine] Auto-refresh timer stopped`

#### Start Auto-Refresh

1. Click **"Start Refresh"**
2. Update the `current_ai.png` file again
3. ✅ Verify: Image DOES update now
4. Console shows: `[Style Engine] Auto-refresh timer started`

---

## Visual Test Results

### Before Refresh
```
Right Viewport:
┌─────────────────┐
│                 │
│  Blue           │
│  Placeholder    │
│                 │
└─────────────────┘
```

### After You Replace Image
```
Right Viewport:
┌─────────────────┐
│                 │
│  Your Image     │
│  Appears Here!  │
│                 │
└─────────────────┘
```

---

## Common Test Scenarios

### Scenario 1: Simulating AI Generation

```python
# Simulate what AI pipeline will do:
1. Your AI generates an image
2. AI saves it to: data/temp/ai_vision/current_ai.png
3. Blender detects the change automatically
4. Image refreshes in right viewport
5. You see the result in real-time!
```

### Scenario 2: Rapid Updates

Test how it handles quick changes:

1. Prepare 5 different images
2. Rapidly copy them to `current_ai.png` (one after another)
3. Watch Blender update for each change
4. All updates should appear smoothly

### Scenario 3: Large Images

Test with different resolutions:

1. Try a 4K image (3840x2160)
2. Try a small image (512x512)
3. Try a portrait image (1080x1920)
4. All should display correctly (stretched to fit)

---

## Console Messages to Look For

### Success Messages ✅

```
[Style Engine] Auto-refresh timer started
[Style Engine] Image reloaded: current_ai.png
```

### Error Messages (if something goes wrong)

```
[Style Engine] Error in refresh timer: [error details]
```

---

## Troubleshooting

### Issue: Image doesn't update

**Check**:
1. Is timer running? Click "Start Refresh"
2. Is file path correct? Must be `data/temp/ai_vision/current_ai.png`
3. Did you save the file? Make sure you saved changes
4. File permissions? Can Blender read the file?

**Solution**:
```python
# Check in Blender Python Console:
import bpy
print("current_ai.png" in bpy.data.images)  # Should be True
img = bpy.data.images["current_ai.png"]
print(img.filepath)  # Check the path
img.reload()  # Manual reload
```

### Issue: Updates are slow

**Explanation**: Timer checks every 1 second. This is intentional to avoid performance issues.

**To change interval** (in `workspace_setup.py`):
```python
# Change from:
return 1.0  # 1 second

# To:
return 0.5  # 0.5 seconds (faster, but more CPU)
```

### Issue: Wrong viewport updates

**Check**: Make sure you're looking at the **right viewport** (the camera-locked one).

**Solution**: 
- Right viewport should show camera icon in top-left
- Should show "Camera View" in the header

---

## Performance Testing

### Test 1: CPU Usage
1. Open Task Manager (Windows) or Activity Monitor (Mac)
2. Watch Blender's CPU usage
3. With auto-refresh running, it should be minimal (<1% extra)

### Test 2: Many Updates
1. Update image 20 times in a row
2. Blender should handle all updates smoothly
3. No lag or freezing

### Test 3: Large Files
1. Use a 10MB+ PNG image
2. Auto-refresh should still work
3. May take slightly longer to load

---

## Integration Test (For Future AI Pipeline)

Simulate the full workflow:

```python
# In Blender Python Console:
import bpy
import os
from pathlib import Path

# 1. Get the image path
base = os.path.dirname(bpy.data.filepath)
img_path = os.path.join(base, "data", "temp", "ai_vision", "current_ai.png")

# 2. Simulate AI generation (just copy a test image)
import shutil
shutil.copy("C:/path/to/test_image.png", img_path)

# 3. Watch it auto-refresh in ~1 second! ✨
```

---

## Success Criteria

✅ All tests pass when:

1. **Setup**: Workspace creates successfully
2. **Path**: File is in `data/temp/ai_vision/current_ai.png`
3. **Auto-Refresh**: Image updates within 1-2 seconds of file change
4. **Manual Control**: Start/Stop buttons work
5. **Performance**: No lag or performance issues
6. **Multiple Updates**: Handles rapid file changes
7. **Console**: Shows clear status messages

---

## Real-World Usage

Once you integrate AI generation:

```
You model in left viewport
         ↓
Every X seconds:
  1. AI captures your view
  2. AI processes with RunComfy
  3. AI saves to current_ai.png
  4. Auto-refresh detects change
  5. Right viewport updates
         ↓
You see AI visualization in real-time! 🎨
```

---

**Status**: Auto-refresh system fully functional  
**Refresh Rate**: 1 second  
**Path**: `data/temp/ai_vision/current_ai.png`  
**Controls**: Start/Stop buttons in UI  

🎉 **Ready for AI pipeline integration!**

