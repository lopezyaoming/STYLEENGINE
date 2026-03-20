# 🛡️ Safety Measures - IMPORTANT!

## ⚠️ Critical Safety Information

### DO NOT Move `styleengine/` Into `packaging/`!

The addon source directory should **ALWAYS** be at:
```
✅ CORRECT: scripts/addons/styleengine/
❌ WRONG:   scripts/addons/packaging/styleengine/
```

---

## 🚨 Why This Matters

If `styleengine/` is accidentally moved into the `packaging/` directory:
1. The packaging script won't find the correct source files
2. Old/incorrect scripts might delete the wrong directory during cleanup
3. You could lose your work

---

## 🛡️ Safety Features Implemented

### 1. **Path Validation**
The modern packaging script (`package_addon_modern.py`) includes a critical safety check:
- Verifies source directory is NOT inside packaging/
- Refuses to run if the structure is wrong
- Provides clear error messages

### 2. **Git Ignore**
`.gitignore` in this directory prevents:
- Accidentally committing `styleengine/` in the wrong location
- Tracking temporary ZIP files
- Log file clutter

### 3. **Dangerous Scripts Removed**
All OLD scripts have been deleted because they had incorrect path configurations:
- ❌ `OLD_package_addon.bat`
- ❌ `OLD_package_addon.py`
- ❌ `OLD_package_addon.ps1`
- ❌ `OLD_package_addon_fixed.ps1`
- ❌ `OLD_package_addon_posix.ps1`
- ❌ `OLD_package_addon_advanced.bat`

These scripts looked for `packaging/styleengine/` instead of `scripts/addons/styleengine/`.

---

## ✅ Safe Scripts (Use Only These!)

| Script | Purpose | Safety Level |
|--------|---------|--------------|
| `package_addon_modern.py` | Main packaging script | ✅ **SAFE** - Has path validation |
| `package_addon_EASY.bat` | Windows wrapper | ✅ **SAFE** - Just calls Python script |

---

## 🔧 If `styleengine/` Gets Deleted

**Immediate recovery:**
```bash
# Restore from Git immediately
git restore scripts/addons/styleengine/

# Verify it's back
ls scripts/addons/styleengine/art_director.py
```

**Investigation:**
```bash
# Check git status to see what happened
git status

# Check if you accidentally moved files
git diff

# Look for uncommitted changes
git log --oneline -5
```

---

## 📋 Pre-Flight Checklist

**Before running packaging:**
- [ ] `styleengine/` is at `scripts/addons/styleengine/`
- [ ] You're in the `packaging/` directory
- [ ] Blender is closed (to avoid file locks)
- [ ] You're using `package_addon_modern.py` or `package_addon_EASY.bat`

---

## 🐛 Debugging Tips

### "Source directory not found"
**Cause:** You're in the wrong directory or `styleengine/` was moved.

**Fix:**
```bash
# Check current location
pwd

# Should be: .../scripts/addons/packaging

# Check if styleengine exists
ls ../styleengine/art_director.py

# If missing, restore from git
git restore ../styleengine/
```

### "Safety check failed"
**Cause:** `styleengine/` is inside `packaging/` (wrong location).

**Fix:**
```bash
# Move it back to correct location
mv styleengine ../

# Or restore from git
git restore ../styleengine/
rm -rf styleengine/  # Remove the wrong copy
```

### "Permission denied" on ZIP
**Cause:** ZIP file is locked (Blender has addon loaded).

**Fix:**
1. Close Blender
2. Delete `styleengine.zip` manually
3. Run packaging script again

---

## 🎯 Best Practices

1. **Always run from packaging/ directory**
   ```bash
   cd scripts/addons/packaging
   python package_addon_modern.py
   ```

2. **Never manually move styleengine/**
   - It should stay at `scripts/addons/styleengine/`
   - Git will track it there

3. **Close Blender before packaging**
   - Prevents file locks
   - Ensures clean package

4. **Check git status if anything looks wrong**
   ```bash
   git status
   git diff
   ```

5. **Commit often**
   - Small, frequent commits make recovery easier
   - Tag stable versions

---

## 📞 Emergency Contact

If `styleengine/` keeps getting deleted:
1. Stop all operations immediately
2. Run `git status` and save the output
3. Check what scripts you ran before it happened
4. Restore from git: `git restore scripts/addons/styleengine/`
5. Review this safety document

---

## 🔍 Monitoring

**Signs something is wrong:**
- Packaging script can't find source files
- Git shows `styleengine/` as deleted
- Blender can't load the addon
- Multiple "directory not found" errors

**If you see these signs:**
1. **STOP** - Don't run any more scripts
2. **CHECK** - `git status`
3. **RESTORE** - `git restore scripts/addons/styleengine/`
4. **INVESTIGATE** - What caused it?

---

## ✨ Version History

- **2025-11-09**: Safety measures implemented
  - Added path validation to packaging script
  - Created `.gitignore` to prevent wrong location
  - Deleted dangerous OLD scripts
  - Created this safety documentation

---

**Remember:** The packaging script is a tool to help you. The safety checks are there to protect your work. If they trigger, something is genuinely wrong—investigate before proceeding!

🛡️ **Stay Safe!** 🛡️

