# Per-Project Library - Quick Guide
**Date:** November 21, 2025

---

## 🎯 What Changed?

**Before:** Images saved to temp directory, easy to lose work  
**After:** Every generation automatically saved to project library

---

## 📁 Where Are My Images?

### If .blend is Saved:
```
YourProject.blend
YourProject_styleengine/        ← Look here!
└── generations/
    ├── 20251121_143022_001_gcs.png
    ├── 20251121_143145_002_runcomfy.png
    └── ...
```

### If .blend is NOT Saved:
```
C:\Users\You\AppData\Local\Temp\blender_styleengine\
└── sessions\
    └── 20251121_143022_abc123\  ← Session ID
        └── generations\
            └── ...
```

**💡 Tip:** Save your .blend file to get a permanent project library!

---

## 🔄 What Happens When I Save?

### Scenario: Unsaved → Saved

1. **Before saving:** Images go to temp (session folder)
2. **You save .blend:** 🚚 **Automatic migration!**
3. **After saving:** All images copied to project library
4. **Future generations:** Go directly to project library

**Result:** You never lose work! ✅

---

## 📝 Filename Format

```
20251121_143022_001_gcs.png
│        │       │   └─ Backend (gcs/runcomfy/local)
│        │       └───── Milliseconds (for uniqueness)
│        └───────────── Time (HHMMSS)
└────────────────────── Date (YYYYMMDD)
```

**Benefits:**
- ✅ Chronological sorting
- ✅ Unique names (no overwrites)
- ✅ Know which backend generated each image

---

## 🎨 Workflow Examples

### Example 1: Quick Sketch (Unsaved)
```
1. Open Blender (don't save)
2. Generate 5 images
3. Close Blender
→ Images in temp (kept for 7 days)
```

### Example 2: Real Project (Saved)
```
1. Open/Create MyProject.blend
2. Save it
3. Generate images
→ Images in MyProject_styleengine/generations/
→ Portable with .blend file!
```

### Example 3: Save Mid-Session
```
1. Open Blender (unsaved)
2. Generate 3 images (temp)
3. Save as MyProject.blend
→ 🚚 Auto-migration! All 3 images copied
4. Generate more images
→ All images now in MyProject_styleengine/
```

---

## ⚠️ Important Notes

### ✅ DO:
- Save your .blend file to get permanent library
- Keep `YourProject_styleengine` folder with your .blend
- Move both together if relocating project

### ❌ DON'T:
- Delete `_styleengine` folders (you'll lose generations!)
- Rename .blend without renaming `_styleengine` folder
- Worry about temp files (auto-cleaned after 7 days)

---

## 🔍 Finding Your Images

### Method 1: File Explorer
```
1. Navigate to your .blend file location
2. Look for YourProject_styleengine folder
3. Open generations/ subfolder
```

### Method 2: Blender Console
```
Look for console output:
[Style Engine] 💾 Saved generation: 20251121_143022_001_gcs.png
[Style Engine] 📁 Project library: C:\Projects\MyProject_styleengine
```

---

## 🚀 Coming Soon

**Phase 2: Generation Browser**
- Visual browser in UI panel
- Thumbnail previews
- Navigate prev/next
- Load to camera or project
- See generation history

**Phase 3: Advanced Features**
- Search by date/settings
- Export selections
- Delete unwanted
- Auto-cleanup old generations

---

## 💡 Pro Tips

1. **Save Early:** Save your .blend file early to get project library immediately

2. **Portable Projects:** Keep `_styleengine` folder with .blend for complete portability

3. **Backup:** The `_styleengine` folder IS your image backup - include in backups!

4. **Multiple Projects:** Each .blend gets its own `_styleengine` folder - no conflicts!

5. **Recovery:** If you forgot to save, check temp sessions folder within 7 days

---

## ❓ FAQ

**Q: What if I delete the `_styleengine` folder?**  
A: You'll lose all generations for that project. It will be recreated empty on next generation.

**Q: Can I rename my .blend file?**  
A: Yes, but manually rename the `_styleengine` folder to match: `NewName_styleengine`

**Q: What happens to temp sessions?**  
A: System auto-cleans after 7 days. Save your .blend to migrate before then!

**Q: Does this work with "Save As"?**  
A: Yes! "Save As" keeps your current library, doesn't migrate again.

**Q: Can I have multiple unsaved projects?**  
A: Yes! Each gets a unique session ID, no conflicts.

---

**That's it!** The system works automatically. Just save your .blend file and generate images. Everything else is handled for you! 🎨✨

