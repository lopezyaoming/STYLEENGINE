# AI Vision MVP - Testing Checklist

## Quick Test Guide

Use this checklist to verify the MVP setup is working correctly.

## ✅ Pre-Test Setup

- [ ] Blender 4.5 is running
- [ ] Style Engine addon is enabled (Edit → Preferences → Add-ons)
- [ ] You can see the Style Engine panel (Press `N` in 3D Viewport)
- [ ] You have a basic scene (even just the default cube is fine)

## ✅ Test 1: Basic Workspace Setup

1. **Position your 3D view** where you want the camera
   - Navigate around your scene
   - Find a good angle

2. **Open Style Engine panel**
   - Press `N` in 3D Viewport
   - Click "Style Engine" tab

3. **Click "Setup Workspace" button**
   - Look for it under "AI Vision Setup" section

4. **Expected Results:**
   - [ ] Console message: "AI Vision workspace created successfully!"
   - [ ] Workspace automatically switches to "AI"
   - [ ] Two viewports appear (left and right)
   - [ ] Right viewport shows camera view
   - [ ] No error messages in console

## ✅ Test 2: Verify Camera Creation

1. **Open Outliner** (Scene Collection panel)

2. **Look for `ai_camera`**
   - [ ] Camera object exists
   - [ ] Camera icon is highlighted (active camera)
   - [ ] Camera is positioned in your scene

3. **Check camera properties**
   - Select `ai_camera` object
   - Go to Camera Properties (camera icon in properties panel)
   - [ ] "Background Images" is enabled
   - [ ] One background image is listed
   - [ ] Image points to "current_ai.png"

## ✅ Test 3: Verify Directory Structure

1. **Locate your project folder**
   - If saved: Same directory as your .blend file
   - If not saved: Check Blender temp directory

2. **Check for temp directory**
   - [ ] `temp/` folder exists
   - [ ] `temp/ai_vision/` folder exists  
   - [ ] `temp/ai_vision/current_ai.png` exists

3. **View the placeholder image**
   - Open `current_ai.png` in an image viewer
   - [ ] Image is dark blue color
   - [ ] Resolution is 1920x1080

## ✅ Test 4: Workspace Layout

1. **Verify workspace tabs**
   - Look at top of Blender window
   - [ ] "AI" workspace tab exists
   - [ ] You're currently on "AI" workspace

2. **Check left viewport**
   - [ ] Normal 3D view
   - [ ] Can orbit/pan/zoom freely
   - [ ] Standard shading modes available

3. **Check right viewport**
   - [ ] Shows camera view
   - [ ] Camera view is locked (can't orbit)
   - [ ] Background image visible (dark blue placeholder)

## ✅ Test 5: Camera Alignment

1. **Check camera position**
   - Select `ai_camera` in outliner
   - [ ] Camera is where you were looking when you clicked setup
   - [ ] Camera rotation matches your view angle

2. **Test from different positions**
   - Switch back to "Layout" workspace
   - Navigate to a different view
   - Click "Setup Workspace" again
   - [ ] Camera repositions to new view
   - [ ] No duplicate cameras created

## ✅ Test 6: Background Image Display

1. **In the right viewport (camera view)**
   - [ ] Placeholder image is visible
   - [ ] Image fills the viewport
   - [ ] Image is in front of scene geometry
   - [ ] Opacity appears to be 100%

2. **Try replacing the image**
   - Save any image as `temp/ai_vision/current_ai.png`
   - In Blender: Go to UV Editor or Image Editor
   - Find "current_ai.png" image
   - Click reload button (circular arrow icon)
   - [ ] Image updates in camera viewport

## ✅ Test 7: Multiple Runs

1. **Run setup multiple times**
   - Click "Setup Workspace" button again
   - [ ] No error messages
   - [ ] Workspace reused (not duplicated)
   - [ ] Camera reused (not duplicated)
   - [ ] System remains stable

2. **Check scene outliner**
   - [ ] Only ONE `ai_camera` exists
   - [ ] No duplicate objects

## ✅ Test 8: Console Output

1. **Open System Console** (Windows → Toggle System Console)

2. **Look for these messages:**
   ```
   [Style Engine] Temp directory: [path]
   [Style Engine] Created placeholder image: [path]
   [Style Engine] Created new ai_camera (or Using existing ai_camera)
   [Style Engine] Camera aligned to view at [location]
   [Style Engine] Background image set: [path]
   [Style Engine] Created new AI workspace (or AI workspace already exists)
   [Style Engine] Configuring workspace layout...
   [Style Engine] Right viewport configured as locked camera view
   ```

3. **Verify no Python errors**
   - [ ] No red error text in console
   - [ ] No traceback messages

## ✅ Test 9: Navigation Test

1. **In left viewport**
   - [ ] Middle mouse to orbit works
   - [ ] Shift+middle mouse to pan works
   - [ ] Scroll to zoom works
   - [ ] All standard navigation works

2. **In right viewport**
   - [ ] Camera view stays locked
   - [ ] Can't orbit (view is locked)
   - [ ] Background image stays visible
   - [ ] Can still zoom (but view stays camera-locked)

## ✅ Test 10: Integration with Existing Features

1. **Test existing operators**
   - Click "Visualize (30s)" button
   - [ ] No errors
   - [ ] Camera and credentials work together

2. **Check preferences**
   - Edit → Preferences → Add-ons → Style Engine
   - [ ] Preferences panel still works
   - [ ] No conflicts with new features

## 🐛 Troubleshooting

### If tests fail:

**No "AI" workspace created:**
- Check console for errors
- Verify addon is fully enabled
- Try reloading Blender

**Camera not visible:**
- Check outliner for `ai_camera`
- Select camera and press `Numpad 0` to switch to camera view
- Verify camera is in scene, not deleted

**Viewport doesn't split:**
- Manually split: Drag from viewport corner
- Set right view to camera: View → Cameras → Active Camera
- Try running setup again

**Background image not showing:**
- Camera Properties → Background Images → Check "Enabled"
- Verify image file exists in temp/ai_vision/
- Try reloading image

**"Setup Workspace" button doesn't respond:**
- Check for Python errors in console
- Restart Blender
- Reinstall addon

## 📊 Expected Performance

- Setup time: < 1 second
- No lag or freezing
- Smooth viewport navigation in both views
- No memory leaks on repeated runs

## ✅ Success Criteria

All of the following should be true:

- [ ] "AI" workspace exists and is functional
- [ ] Two viewports: modeling (left) and camera (right)
- [ ] `ai_camera` object exists and is active
- [ ] Background image system works
- [ ] temp/ai_vision/ directory structure created
- [ ] No errors in console
- [ ] Can run setup multiple times safely
- [ ] System ready for AI generation pipeline integration

## Next Steps After Testing

Once all tests pass, you're ready for:
1. Implement auto-refresh timer
2. Add viewport rendering functionality  
3. Integrate RunComfy API calls
4. Add AI generation pipeline
5. Configure update intervals

---

**Note**: This is the MVP skeleton. The actual AI generation is not yet implemented - this tests the infrastructure only.

