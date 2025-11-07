# Filepath Lock Fix - Save Mid-Session Bug

**Date:** 2025-11-05  
**Type:** Critical Bug Fix  
**Status:** ✅ FIXED

---

## 🐛 The Bug (Reported by Boss/Ian)

**Symptom:** Files break when user starts generation with unsaved .blend, then saves during session.

**User Story:**
1. Opens Blender (unsaved .blend file)
2. Sets up AI workspace → Files go to: `C:\Users\Juan\AppData\Local\Temp\blender_styleengine\`
3. Starts generation → `session.json`, `current_ai.png` written to temp
4. **Saves .blend to disk** → Path changes to: `C:\Projects\MyFile\temp\ai_vision\`
5. Generation continues looking for files → **Can't find them!** They're in the OLD location!

---

## 💥 Root Cause

**File:** `workspace_setup.py`  
**Function:** `get_temp_directory()`

```python
# OLD CODE (BROKEN)
def get_temp_directory(context=None):
    if bpy.data.is_saved:
        blend_dir = Path(bpy.path.abspath("//"))
        temp_dir = blend_dir / "temp" / "ai_vision"
        return temp_dir  # ❌ Path changes when .blend is saved!
    
    # Fall back to system temp
    temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "ai_vision"
    return temp_dir
```

**Problem:** Every call to `get_temp_directory()` re-evaluates `bpy.data.is_saved`, causing the path to change mid-session!

---

## ✅ The Fix: Session Lock

**Strategy:** Lock the temp directory path once determined, prevent changes during session.

### Changes Made:

#### 1. Added Global Variable (Line 55)

```python
# Global variable to lock temp directory for session consistency
_session_temp_dir = None
```

#### 2. Rewrote `get_temp_directory()` (Lines 17-62)

```python
def get_temp_directory(context=None):
    """
    Get the temp directory for storing AI vision data.
    Once determined, the path is locked for the entire session to prevent
    filepath issues when .blend file is saved mid-session.
    """
    global _session_temp_dir
    
    # If already determined, reuse it (prevents save-time path changes)
    if _session_temp_dir is not None:
        return _session_temp_dir  # ✅ Locked path!
    
    # Determine temp directory (priority order)
    temp_dir = None
    
    # 1. Try .blend file directory if saved
    if bpy.data.is_saved:
        blend_dir = Path(bpy.path.abspath("//"))
        temp_dir = blend_dir / "temp" / "ai_vision"
    
    # 2. Try user's output_path setting
    elif context:
        try:
            props = context.scene.style_engine_props
            if hasattr(props, 'output_path') and props.output_path:
                output_path = Path(props.output_path)
                if output_path.exists():
                    temp_dir = output_path / "temp" / "ai_vision"
        except:
            pass
    
    # 3. Fall back to system temp
    if temp_dir is None:
        import tempfile
        temp_dir = Path(tempfile.gettempdir()) / "blender_styleengine" / "ai_vision"
    
    # Lock it for this session
    _session_temp_dir = temp_dir
    print(f"[Style Engine] 🔒 Temp directory locked: {temp_dir}")
    
    return temp_dir
```

#### 3. Added Reset Function (Lines 65-74)

```python
def reset_temp_directory():
    """
    Reset temp directory lock (called when setting up new workspace).
    Allows the path to be re-determined based on current .blend save state.
    """
    global _session_temp_dir
    old_path = _session_temp_dir
    _session_temp_dir = None
    if old_path:
        print(f"[Style Engine] 🔓 Temp directory unlocked (was: {old_path})")
```

#### 4. Call Reset in Workspace Setup (Line 666)

```python
def execute(self, context):
    # Reset temp directory lock (allows re-determination if .blend was saved)
    reset_temp_directory()
    
    # Create temp directory for AI images
    self.ensure_temp_directory(context)
```

---

## 🎯 How It Works Now

### Scenario 1: Unsaved → Saved Mid-Session

```
1. Open Blender (unsaved)
   └─ get_temp_directory() → System temp: C:\...\AppData\Local\Temp\blender_styleengine\
   └─ 🔒 Path locked!

2. Start generation
   └─ Files written to: C:\...\AppData\Local\Temp\blender_styleengine\
   └─ session.json, current_ai.png, combined.jpg

3. User saves .blend to C:\Projects\MyFile.blend
   └─ get_temp_directory() → Still returns: C:\...\AppData\Local\Temp\blender_styleengine\
   └─ 🔒 Path LOCKED (unchanged!)

4. Generation continues
   └─ Files read from: C:\...\AppData\Local\Temp\blender_styleengine\
   └─ ✅ Everything works!

5. User runs "Setup Workspace" again
   └─ reset_temp_directory() → 🔓 Unlocked!
   └─ get_temp_directory() → NOW uses .blend path: C:\Projects\temp\ai_vision\
   └─ 🔒 New path locked!
```

### Scenario 2: Saved → Generation

```
1. Open saved .blend (C:\Projects\MyFile.blend)
   └─ get_temp_directory() → C:\Projects\temp\ai_vision\
   └─ 🔒 Path locked!

2. Start generation
   └─ Files written to: C:\Projects\temp\ai_vision\
   └─ ✅ Stays consistent throughout session
```

---

## 📊 Console Output

### First Lock (Workspace Setup)
```
[Style Engine] 🔓 Temp directory unlocked (was: C:\...\Temp\blender_styleengine\ai_vision)
[Style Engine] 🔒 Temp directory locked: C:\Projects\MyFile\temp\ai_vision
[Style Engine] Temp directory: C:\Projects\MyFile\temp\ai_vision
```

### During Session (All Calls Return Locked Path)
```
# No output - just returns cached path
# No re-evaluation of bpy.data.is_saved!
```

---

## ✅ Benefits

1. **Consistent Paths** - Same temp directory throughout session
2. **No Mid-Session Breaks** - Saving .blend doesn't cause file lookups to fail
3. **Smart Reset** - Fresh workspace setup re-evaluates based on current state
4. **Clear Logging** - 🔒/🔓 emojis show when lock changes
5. **Backwards Compatible** - Works with existing code, no API changes

---

## 🧪 Testing Scenarios

### Test 1: Unsaved → Save → Generate
- [ ] Start with unsaved .blend
- [ ] Setup workspace (locks to system temp)
- [ ] Start generation
- [ ] Save .blend to disk
- [ ] Verify generation continues without errors
- [ ] Check console shows locked path

### Test 2: Saved → Generate
- [ ] Open saved .blend
- [ ] Setup workspace (locks to .blend directory)
- [ ] Start generation
- [ ] Verify files in `{blend_dir}/temp/ai_vision/`

### Test 3: Reset Between Sessions
- [ ] Setup workspace (path locked)
- [ ] Save .blend to new location
- [ ] Setup workspace again (should unlock and relock to new path)
- [ ] Verify new path is used

---

## 🎉 Boss Approval

> "dude holy shit it worked so well. just came out with meeting with boss and it worked well"

**Status:** Production ready! 🚀

---

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `workspace_setup.py` | 55 | Added `_session_temp_dir` global |
| `workspace_setup.py` | 17-62 | Rewrote `get_temp_directory()` with lock |
| `workspace_setup.py` | 65-74 | Added `reset_temp_directory()` |
| `workspace_setup.py` | 666 | Call reset in workspace setup |

**Total:** ~60 lines changed/added

---

**TLDR:** Temp directory path is now locked for the entire session, preventing filepath breaks when .blend is saved mid-generation. Reset on workspace setup to adapt to new save state. Boss approved! ✅ 🎉

