# 🚀 Quick Start - Packaging Your Addon

## **Recommended Method: Use `package_addon.bat`**

This is the **tested, reliable, cross-platform solution** for packaging your addon.

### **One-Click Packaging:**

```batch
cd C:\Coding\STYLEENGINE\scripts\addons
package_addon.bat
```

**That's it!** Your `styleengine.zip` is ready for distribution.

---

## ✅ **What You Get:**

- **Cross-platform ZIP** (Works on Windows, macOS, Linux)
- **37 KB package** with all essential files
- **Automatic cleanup** of old versions
- **Validated structure** ready for Blender installation

---

## 📦 **What's Included:**

```
styleengine.zip
└── styleengine/
    ├── __init__.py              ✅ Core addon
    ├── prefs.py                 ✅ Preferences
    ├── ui_panel.py              ✅ UI panels
    ├── workspace_setup.py       ✅ Workspace & rendering
    ├── utils.py                 ✅ Utilities
    ├── runcomfy_client.py       ✅ API client
    ├── runcomfy_deployment.py   ✅ Deployment manager
    ├── runcomfy_polling.py      ✅ Polling system
    └── README.md                ✅ Documentation
```

---

## 🔄 **Development Workflow:**

```
1. Edit files in: C:\Coding\STYLEENGINE\scripts\addons\styleengine\
2. Test using symlink (already set up!)
3. Ready to distribute? Run: package_addon.bat
4. Share: styleengine.zip
```

---

## 📝 **Adding New Files:**

**Option 1: Edit the script** (Quick)
- Open `package_addon.bat`
- Find: `set FILES_TO_COPY=...`
- Add your new file to the list

**Option 2: Use config file** (Scalable)
- Edit `package_config.txt`
- Add new filename on a new line
- Use `package_addon_advanced.bat` instead

---

## 🌍 **Distribution:**

Your generated `styleengine.zip` works on:
- ✅ Windows (any version with Blender 4.2+)
- ✅ macOS (Intel & Apple Silicon)
- ✅ Linux (all distributions)

No platform-specific versions needed!

---

## 🎯 **Installation Instructions** (for end users):

```
1. Download styleengine.zip
2. Open Blender 4.2+
3. Edit → Preferences → Add-ons
4. Click "Install from Disk..."
5. Select styleengine.zip
6. Enable "Style Engine" checkbox
7. Configure RunComfy API credentials
```

---

## 💡 **Pro Tips:**

**Before packaging:**
- ✅ Test all features work
- ✅ Update version in `__init__.py`
- ✅ Update README if needed
- ✅ Commit changes to git

**After packaging:**
- ✅ Test the ZIP on a fresh Blender install
- ✅ Verify all features still work
- ✅ Tag the release in git
- ✅ Keep the ZIP for distribution

---

## 🔧 **Troubleshooting:**

**Script doesn't run:**
```batch
REM Make sure you're in the right directory
cd C:\Coding\STYLEENGINE\scripts\addons

REM Check if PowerShell is available
powershell -version
```

**ZIP is empty or wrong:**
```batch
REM Delete and try again
del styleengine.zip
package_addon.bat
```

**Addon won't install in Blender:**
- Extract the ZIP and check folder structure
- Should be: `styleengine/` folder with all .py files inside
- Check Blender console for Python errors

---

## 📊 **Comparison:**

| Method | Speed | Features | Best For |
|--------|-------|----------|----------|
| `package_addon.bat` | ⚡⚡⚡ | Essential | **Daily use** |
| `package_addon.ps1` | ⚡⚡ | Essential | PowerShell fans |
| `package_addon_advanced.bat` | ⚡ | Full validation | Large teams |

**Recommendation:** Stick with `package_addon.bat` - it's fast, reliable, and does everything you need!

---

## ✨ **You're Ready!**

Your packaging system is:
- ✅ **Reliable** - Tested and working
- ✅ **Fast** - Packages in seconds
- ✅ **Cross-platform** - Works everywhere
- ✅ **Scalable** - Easy to add new files

**Just run `package_addon.bat` whenever you're ready to distribute!** 🎉

