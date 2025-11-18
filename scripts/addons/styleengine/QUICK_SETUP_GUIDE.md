# 🚀 Quick Setup Guide - Credentials Import

## The Fastest Way to Set Up Style Engine!

Instead of manually copying and pasting your API credentials, you can now import them all at once from a file.

---

## ⚡ Quick Start (60 seconds)

### Step 1: Create credentials.txt

In your addon directory (`scripts/addons/styleengine/`), create a file called `credentials.txt`:

```
RUNCOMFY_API_TOKEN: 78356331-a9ec-49c2-a412-59140b32b9b3
RUNCOMFY_USER_ID: 0cb54d51-f01e-48e1-ae7b-28d1c21bc947
Workflow ID: f7ade856-0739-4fc8-8fa3-3b3857e2ebcb
Deployment ID: 1c6fa9a6-f60a-4e89-863d-40b03ad2564e
```

### Step 2: Import in Blender

1. Open Blender
2. Go to: **Edit → Preferences → Add-ons → Style Engine**
3. Look at the top of the preferences panel
4. You'll see a **"Quick Setup"** box
5. Click the big **"Import from credentials.txt"** button

### Step 3: Test Connection

Click **"Test Connection"** below to verify everything works!

Done! ✅

---

## 📸 What It Looks Like

When you open Style Engine preferences, you'll see this at the very top:

```
┌─────────────────────────────────────────────────────┐
│ 📦 API Configuration                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 📥 Quick Setup                              │   │
│  ├─────────────────────────────────────────────┤   │
│  │                                             │   │
│  │  ┌──────────────────────────────────────┐  │   │
│  │  │  Import from credentials.txt         │  │   │ ← CLICK THIS!
│  │  └──────────────────────────────────────┘  │   │
│  │                                             │   │
│  │  💡 Place credentials.txt in addon          │   │
│  │     directory to auto-fill below            │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [ ] Prefer Environment Variables                  │
│                                                     │
│  ... (rest of settings) ...                        │
└─────────────────────────────────────────────────────┘
```

---

## ✅ What Gets Imported

The import button will automatically fill in:

- ✅ **API Token** - Your RunComfy API authentication token
- ✅ **User ID** - Your RunComfy user identifier  
- ✅ **Workflow ID** - The workflow configuration ID
- ✅ **Deployment ID** - Your deployment instance ID (optional)

All fields are validated before import.

---

## 💡 Pro Tips

1. **Use the template**
   - Copy `credentials.txt.template` → `credentials.txt`
   - Fill in your actual values
   - This prevents formatting errors

2. **Keep it secure**
   - Add `credentials.txt` to your `.gitignore`
   - Never commit actual credentials to version control
   - File permissions: `chmod 600 credentials.txt` (Linux/macOS)

3. **Multiple machines**
   - Keep `credentials.txt` in a secure location
   - Copy it to each machine where you install Style Engine
   - One-click setup everywhere!

4. **Team workflow**
   - Commit `credentials.txt.template` to git
   - Team members create their own `credentials.txt`
   - Share actual credentials securely (encrypted chat, password manager, etc.)

---

## 🔍 What Happens When You Click Import

1. **Searches for file** - Looks in addon directory for `credentials.txt`
2. **Parses content** - Reads key-value pairs from the file
3. **Validates format** - Ensures required fields are present
4. **Imports values** - Fills in all preference fields
5. **Shows confirmation** - Success message appears
6. **Ready to use** - You can now test connection or start generating!

---

## 🛠️ Troubleshooting

### "credentials.txt not found"
→ Make sure the file is in: `scripts/addons/styleengine/credentials.txt`

### "Missing required credentials"
→ Check that `RUNCOMFY_API_TOKEN` and `RUNCOMFY_USER_ID` are in the file

### "Connection test failed"
→ Verify your credentials are correct (check with RunComfy dashboard)

### Import works but fields still empty
→ Click "Show API Keys" toggle to reveal the fields

---

## 🎯 Why This Feature Exists

**Before:** Manual copy-paste for each credential (tedious, error-prone)

**After:** One file, one click, done! ✨

This is especially helpful for:
- 🚀 New users getting started
- 👥 Teams onboarding multiple people
- 💻 Developers testing on multiple machines
- 🔄 Anyone reinstalling/updating the addon

---

## 📚 Further Reading

For complete documentation, see:
- `CREDENTIALS_IMPORT.md` - Full feature documentation
- `README.md` - Main addon documentation
- `credentials.txt.template` - Template file to copy

---

**Happy generating!** 🎨✨


