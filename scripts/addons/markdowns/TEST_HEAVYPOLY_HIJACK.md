# Testing HeavyPoly Hijacking Feature

**Quick test guide to verify the workspace hijacking works correctly**

---

## 🎯 Prerequisites

1. ✅ Blender 4.4 running
2. ✅ Style Engine addon enabled
3. ✅ HeavyPoly addon installed (with "Modelling" workspace)

---

## 🧪 Test 1: Standard Mode (Control Test)

**Purpose:** Verify normal behavior is unchanged

### Steps:
1. Open Blender
2. Go to **Edit → Preferences → Add-ons → Style Engine**
3. Make sure **"Enable HEAVYPOLY Compatibility"** is **OFF** (unchecked)
4. In 3D View, open **N-panel** → **Style Engine** tab
5. Click **"Setup Workspace"**

### Expected Result:
```
✅ Creates "AI" workspace from "Layout"
✅ Split view with camera on right
✅ Text editor at bottom-right
✅ Console shows standard creation messages
✅ No mention of HeavyPoly in console
```

---

## 🧪 Test 2: HeavyPoly Mode (Hijacking Test)

**Purpose:** Verify HeavyPoly workspace hijacking works

### Steps:
1. **Enable HeavyPoly Mode:**
   - Edit → Preferences → Add-ons → Style Engine
   - Expand **Advanced Settings**
   - ✅ Check **"Enable HEAVYPOLY Compatibility"**
   - You should see a checkmark icon appear

2. **Switch to a fresh scene:**
   - File → New → General
   - (This ensures clean test)

3. **Make sure HeavyPoly's workspace exists:**
   - Look at workspace tabs at top
   - Should see: "Layout", "Modelling", "Sculpting", etc.
   - The "Modelling" workspace must exist

4. **Run Setup:**
   - Open N-panel → Style Engine tab
   - Click **"Setup Workspace"**

5. **Watch the console** (Window → Toggle System Console)

### Expected Console Output:
```
[Style Engine] HeavyPoly compatibility enabled - attempting hijack...
[Style Engine] 🎯 HEAVYPOLY MODE: Found 'Modelling' workspace
[Style Engine] ✅ Duplicated Modelling → AI workspace
[Style Engine] 🔧 Hijacking HeavyPoly window areas...
[Style Engine]   📷 Found Image Editor at (x, y)
[Style Engine]   ✅ Converted to camera-locked 3D View
[Style Engine]   📝 Found Text Editor at (x, y)
[Style Engine]   ✅ Loaded Style Engine prompt
[Style Engine] 🎉 HeavyPoly workspace successfully hijacked!
```

### Expected Blender Result:
1. ✅ New workspace tab called **"AI"** appears
2. ✅ Workspace layout matches HeavyPoly's "Modelling"
3. ✅ **Where Image Editor was** → Now camera-locked 3D View
4. ✅ **Where Text Editor was** → Shows "STYLEENGINE_Prompt" file
5. ✅ All other windows unchanged (Properties, Outliner, etc.)
6. ✅ Original "Modelling" workspace still exists and is unchanged

---

## 🧪 Test 3: Fallback Behavior

**Purpose:** Verify graceful fallback if HeavyPoly not found

### Steps:
1. **Temporarily rename "Modelling" workspace:**
   - Right-click "Modelling" workspace tab
   - Rename to "Modelling_backup"

2. **Enable HeavyPoly Mode** (in preferences)

3. **Run Setup Workspace**

### Expected Result:
```
[Style Engine] HeavyPoly compatibility enabled - attempting hijack...
[Style Engine] WARNING: HeavyPoly 'Modelling' workspace not found
[Style Engine] Falling back to standard workspace creation
[Style Engine] HeavyPoly hijack failed, using standard workspace creation
[Style Engine] Using clean 'Layout' workspace as base
[Style Engine] Created fresh AI workspace from clean Layout layout
```

✅ **Should create standard workspace** (not crash)

4. **Restore the name:**
   - Rename "Modelling_backup" back to "Modelling"

---

## 🧪 Test 4: Toggle On/Off

**Purpose:** Verify switching between modes works

### Steps:
1. **With HeavyPoly mode ON:**
   - Setup workspace → Should hijack

2. **Delete AI workspace:**
   - Right-click "AI" workspace tab → Delete

3. **Disable HeavyPoly mode:**
   - Preferences → Uncheck "Enable HEAVYPOLY Compatibility"

4. **Setup workspace again:**
   - Should create standard workspace

5. **Enable HeavyPoly mode again:**
   - Check the toggle

6. **Setup workspace one more time:**
   - Should hijack HeavyPoly's layout

### Expected Result:
✅ Seamlessly switches between modes  
✅ No errors or crashes  
✅ Console shows correct mode messages  

---

## 🧪 Test 5: Verify Window Transformations

**Purpose:** Confirm the hijacked windows work correctly

### After successful hijack:

1. **Check AI Output Window (former Image Editor):**
   - Should show 3D view
   - Should be locked to camera perspective
   - Camera should show background image setup
   - ✅ Can't orbit view (locked)
   - ✅ Shows "ai_camera" name

2. **Check Prompt Window (Text Editor):**
   - Should show "STYLEENGINE_Prompt" at top
   - Should have syntax highlighting
   - Should have line numbers
   - Should be editable
   - ✅ Can type prompt here

3. **Check Other Windows:**
   - Properties panel → unchanged
   - Outliner → unchanged
   - Any other HeavyPoly windows → unchanged

---

## ✅ Success Criteria

All tests should pass with these results:

| Test | Expected | Status |
|------|----------|--------|
| Standard mode works | ✅ Creates split layout | ⬜ |
| HeavyPoly mode hijacks | ✅ Duplicates Modelling | ⬜ |
| Image Editor converted | ✅ Camera-locked 3D View | ⬜ |
| Text Editor loaded | ✅ Shows prompt file | ⬜ |
| Fallback works | ✅ No crash if missing | ⬜ |
| Toggle switches modes | ✅ Seamless transition | ⬜ |
| Other windows preserved | ✅ Unchanged layout | ⬜ |
| Console logging clear | ✅ Shows what happened | ⬜ |

---

## 🐛 Common Issues & Solutions

### Issue: "No HeavyPoly workspace found"
**Solution:** Make sure HeavyPoly addon is installed and has created its workspaces

### Issue: "Image Editor not found"
**Solution:** HeavyPoly's layout might be different. Check what windows exist in "Modelling" workspace

### Issue: Text Editor shows wrong file
**Solution:** Manually select "STYLEENGINE_Prompt" from Text Editor menu

### Issue: Camera view not locked
**Solution:** In camera view, press Numpad 0 or View → Cameras → Active Camera

### Issue: Original code still running
**Solution:** Press F3 → "Reload Scripts" to reload the addon

---

## 📊 Test Report Template

```
Date: ___________
Blender Version: 4.4
Style Engine Version: 0.1.0
HeavyPoly Version: _______

Test Results:
[ ] Test 1: Standard Mode - PASS/FAIL
[ ] Test 2: HeavyPoly Mode - PASS/FAIL  
[ ] Test 3: Fallback - PASS/FAIL
[ ] Test 4: Toggle - PASS/FAIL
[ ] Test 5: Windows - PASS/FAIL

Notes:
_________________________________
_________________________________
_________________________________

Tested by: _____________
```

---

**Happy Testing! 🚀**

