# Template Loading Bug Fix

**Date:** 2025-11-13  
**Status:** ✅ FIXED

---

## Issue

Templates were not being discovered when Prompt Builder was enabled:
```
[Style Engine] No templates found in templates folder
```

Despite templates existing in `scripts/addons/styleengine/templates/`:
- STYLEENGINE_Cinematic_Scene.txt
- STYLEENGINE_Fantasy_Dragon.txt
- STYLEENGINE_Portrait_Photo.txt
- STYLEENGINE_Product_Shot.txt
- STYLEENGINE_SciFi_Robot.txt

---

## Root Cause

**Bug in `list_templates()` glob pattern:**

### Before (Broken):
```python
for ext in ['*.txt', '*.md']:
    for template_file in templates_dir.glob(f"STYLEENGINE_{ext[1:]}"):
        templates.append(template_file.name)
```

**Problem:** 
- When `ext = '*.txt'`, then `ext[1:]` = `'.txt'`
- Creates pattern: `f"STYLEENGINE_{'.txt'}"` → `"STYLEENGINE_.txt"`
- This pattern **doesn't match** files like `STYLEENGINE_Cinematic_Scene.txt`

---

## Fix

### After (Fixed):
```python
for ext in ['.txt', '.md']:
    pattern = f"STYLEENGINE_*{ext}"
    for template_file in templates_dir.glob(pattern):
        templates.append(template_file.name)
```

**Changes:**
1. ✅ Changed list to `['.txt', '.md']` (without asterisk)
2. ✅ Explicit pattern: `f"STYLEENGINE_*{ext}"`
3. ✅ Results in correct patterns:
   - `STYLEENGINE_*.txt` ✓ Matches all .txt templates
   - `STYLEENGINE_*.md` ✓ Matches all .md templates

---

## Additional Improvements

### Added Debug Logging:
```python
# Debug: Show what was found
if templates:
    print(f"[Style Engine] Found {len(templates)} template(s) in {templates_dir}")
else:
    print(f"[Style Engine] No templates found in {templates_dir}")
    print(f"[Style Engine] Templates folder exists: {templates_dir.exists()}")
    if templates_dir.exists():
        all_files = list(templates_dir.glob("*"))
        print(f"[Style Engine] Files in folder: {[f.name for f in all_files]}")
```

**Benefits:**
- Shows how many templates were found
- If none found, shows folder path and existence
- Lists all files in folder for debugging

---

## Expected Behavior Now

When user enables Prompt Builder:

```
[Style Engine] Found 5 template(s) in C:\...\styleengine\templates
[Style Engine] Prompt Builder enabled: Loaded 5 template(s)
[Style Engine] Created text block: STYLEENGINE_Cinematic_Scene
[Style Engine] Created text block: STYLEENGINE_Fantasy_Dragon
[Style Engine] Created text block: STYLEENGINE_Portrait_Photo
[Style Engine] Created text block: STYLEENGINE_Product_Shot
[Style Engine] Created text block: STYLEENGINE_SciFi_Robot
```

---

## Testing

### Verify Fix:
1. Restart Blender or reload addon
2. Enable "Prompt Builder" checkbox
3. Check console for: `"Found 5 template(s)"`
4. Check text editor for 5 STYLEENGINE_* text blocks

### If Still Failing:
- Check console for debug output
- Verify templates folder exists
- Verify files are named correctly (STYLEENGINE_*.txt)
- Check file permissions

---

## Files Modified

**`utils.py` (lines 618-644):**
- Fixed `list_templates()` glob pattern
- Added debug logging

---

## Status

✅ **FIXED AND READY FOR TESTING**

The templates will now load correctly when Prompt Builder is enabled!

---

*Fix applied: 2025-11-13*

