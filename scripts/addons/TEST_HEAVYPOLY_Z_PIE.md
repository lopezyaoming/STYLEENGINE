# Testing Guide: HeavyPoly Z Pie Menu Integration 🪂

**Feature:** Style Engine injection into HeavyPoly's Z key (View/Shading pie)  
**Type:** Paratrooper-style (self-contained, no HeavyPoly edits)  
**Date:** 2025-11-05

---

## Prerequisites

✅ **HeavyPoly addon installed** (get it from Ian Hubert's repo)  
✅ **Style Engine addon installed** (with HeavyPoly integration)  
✅ **Blender 4.2+**

---

## Test Scenario 1: Initial Setup

### Step 1: Fresh Install
1. Open Blender
2. Install HeavyPoly addon (if not already)
3. Install Style Engine addon from `styleengine.zip`
4. Enable both addons in Preferences

**Expected Result:**
- Both addons load without errors
- Console shows: `[Style Engine] All modules loaded successfully!`
- Console does NOT show HeavyPoly integration messages (compatibility mode is OFF by default)

---

### Step 2: Enable HeavyPoly Compatibility
1. Open Edit → Preferences → Add-ons
2. Find Style Engine addon
3. Expand addon preferences
4. **Enable:** "Enable HEAVYPOLY Compatibility" checkbox
5. Click "Save Preferences"
6. Press `F3` → type "Reload Scripts" → run it (or restart Blender)

**Expected Result:**
- Console shows:
  ```
  [Style Engine] 🪂 HeavyPoly integration mode activated
  [Style Engine] ✅ Infiltrated HeavyPoly's Z (Shading) pie
  [Style Engine] 🎯 HeavyPoly integration ready!
  ```

---

## Test Scenario 2: Z Pie Menu Injection

### Step 3: Open Z Pie Menu
1. Have a 3D viewport active
2. Press **Z** key

**Expected Result:**
- Pie menu appears with **8 directions filled:**
  - **WEST (LEFT):** Solid shading (HeavyPoly)
  - **NORTH (TOP):** Material Preview shading (HeavyPoly)
  - **EAST (RIGHT):** **Style Engine AI operators** ← NEW!
    - "🎨 Render AI" button
    - "🎨 Generate" button
    - "Setup AI" button
  - **SOUTH (BOTTOM):** Rendered shading (HeavyPoly)
  - Other directions filled with HeavyPoly's shading options

**Visual Check:**
- RIGHT side of pie should have Style Engine operators
- All other directions should be normal HeavyPoly options
- No layout breaks, no missing items

---

### Step 4: Test "🎨 Render AI" Button
1. Press **Z** → Click "🎨 Render AI"

**Expected Result:**
- Blender renders combined pass from current view (using ultra-fast Workbench engine)
- Render completes quickly (no ray-tracing, just viewport-style render)
- Info message: "AI pass rendered!"
- Pass saved to temp directory as `combined.jpg`

---

### Step 5: Test "🎨 Generate" Button
1. Ensure RunComfy API key is set in addon preferences
2. Press **Z** → Click "🎨 Generate"

**Expected Result:**
- Blender renders combined pass (Workbench)
- RunComfy deployment starts
- Info message: "AI generation started!"
- Polling begins for results
- Generated image appears in AI viewport (if workspace is set up)
- **Note:** This is the full workflow in one button!

---

### Step 6: Test "Setup AI" Button
1. Press **Z** → Click "Setup AI"

**Expected Result (with HeavyPoly compatibility ON):**
- HeavyPoly's "Modeling" workspace is duplicated
- New "AI" workspace created
- Workspace switches to "AI"
- Areas are hijacked:
  - IMAGE_EDITOR → 3D viewport (camera-locked)
  - TEXT_EDITOR → Loads STYLEENGINE_Prompt

**Expected Result (without HeavyPoly compatibility):**
- Standard Style Engine AI workspace created
- Single 3D viewport with camera-locked view

---

## Test Scenario 3: Disable HeavyPoly Compatibility

### Step 7: Disable Compatibility Mode
1. Open Edit → Preferences → Add-ons → Style Engine
2. **Disable:** "Enable HEAVYPOLY Compatibility" checkbox
3. Press `F3` → "Reload Scripts" (or restart Blender)

**Expected Result:**
- Console shows:
  ```
  [Style Engine] 🪂 Removing HeavyPoly integrations...
  [Style Engine] ✅ Removed from HP_MT_pie_shading
  [Style Engine] ✅ HeavyPoly integration removed
  ```

---

### Step 8: Verify Z Pie is Back to Normal
1. Press **Z** key

**Expected Result:**
- Pie menu shows **ONLY HeavyPoly's default options**
- NO Style Engine buttons
- RIGHT side of pie is back to normal HeavyPoly layout

---

## Test Scenario 4: HeavyPoly Not Installed

### Step 9: Test Without HeavyPoly
1. Disable HeavyPoly addon (or test on fresh Blender)
2. Enable Style Engine with "Enable HEAVYPOLY Compatibility" ON
3. Reload scripts

**Expected Result:**
- Console shows:
  ```
  [Style Engine] 🪂 HeavyPoly integration mode activated
  [Style Engine] ℹ️  HeavyPoly not detected, pie injection skipped
  [Style Engine] 🎯 HeavyPoly integration ready!
  ```
- No errors
- Style Engine functions normally (without HeavyPoly integration)

---

## Test Scenario 5: Workflow Integration

### Step 10: Full HeavyPoly + Style Engine Workflow
1. Enable both addons with compatibility ON
2. Model something in HeavyPoly's "Modeling" workspace
3. Press **Z** → "Setup AI" → Creates AI workspace
4. AI workspace opens (hijacked HeavyPoly layout)
5. Type prompt in text editor
6. Press **Z** → "🎨 Generate"
7. AI generates texture
8. Texture appears in camera-locked viewport
9. Switch back to "Modeling" workspace (Alt+←)
10. Continue modeling with HeavyPoly tools

**Expected Result:**
- Seamless switching between HeavyPoly modeling and Style Engine AI generation
- No hotkey conflicts
- Both addons work in harmony

---

## Common Issues & Fixes

### Issue: "Style Engine operators not appearing in Z pie"
**Fix:**
- Ensure "Enable HEAVYPOLY Compatibility" is ON
- Reload scripts (`F3` → "Reload Scripts")
- Check console for `✅ Infiltrated HeavyPoly's Z` message

### Issue: "Z pie layout is broken"
**Fix:**
- Disable compatibility mode
- Reload scripts
- Re-enable compatibility mode
- Reload scripts again

### Issue: "Render AI does nothing"
**Fix:**
- Ensure you have an active camera in the scene
- Check console for error messages
- Verify Blender's render settings are valid

### Issue: "Generate button fails"
**Fix:**
- Check RunComfy API key is set in addon preferences
- Ensure internet connection is active
- Check console for API errors

---

## Success Criteria

✅ Z pie menu shows Style Engine operators when compatibility is ON  
✅ Z pie menu is normal HeavyPoly when compatibility is OFF  
✅ "Render AI" button renders depth + AO passes  
✅ "Generate" button triggers full AI workflow  
✅ "Setup AI" button creates/hijacks workspace  
✅ No errors in console  
✅ No conflicts with HeavyPoly's normal operation  
✅ Clean unregister when compatibility is disabled  
✅ Graceful fallback when HeavyPoly is not installed  

---

## Advanced Testing

### Test A: Multiple 3D Viewports
1. Split viewport into 4 views
2. Press **Z** in each viewport
3. Verify pie menu works in all viewports

### Test B: Different Workspace Contexts
1. Try Z pie in "Modeling" workspace
2. Try Z pie in "Shading" workspace
3. Try Z pie in "UV Editing" workspace
4. Verify consistent behavior

### Test C: Rapid Toggle
1. Enable compatibility → Reload
2. Disable compatibility → Reload
3. Enable compatibility → Reload
4. Repeat 5 times
5. Verify no registration issues

### Test D: Performance
1. Open/close Z pie 20 times rapidly
2. Check for lag or slowdown
3. Verify no memory leaks

---

## Reporting Bugs

If you find issues, report with:
- Blender version
- HeavyPoly version
- Style Engine version
- Console output (from startup to error)
- Steps to reproduce

---

## Notes

- This integration uses Blender's **dynamic menu system** (`append()` method)
- Zero modifications to HeavyPoly's code files
- Integration is **self-contained** in `heavypoly_integration.py`
- Can be extended to other HeavyPoly pie menus in the future

---

**Happy testing! 🪂🎨**

