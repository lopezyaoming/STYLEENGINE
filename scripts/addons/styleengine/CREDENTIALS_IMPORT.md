# Credentials Import Feature

## Overview

The **credentials.txt import feature** allows you to quickly set up Style Engine by loading API credentials from a text file instead of manually entering them.

This is especially useful for:
- ✅ **Quick Installation** - Import all credentials with one click
- ✅ **Team Sharing** - Share credentials securely with team members
- ✅ **Multiple Installations** - Easily configure Style Engine on multiple machines
- ✅ **Development Workflow** - Keep credentials in a file for easy updates

---

## How to Use

### 1. Create credentials.txt

Copy the `credentials.txt.template` file and rename it to `credentials.txt`:

```bash
# In the styleengine addon directory:
cp credentials.txt.template credentials.txt
```

### 2. Fill in Your Credentials

Edit `credentials.txt` with your actual values:

```
RUNCOMFY_API_TOKEN: 78356331-a9ec-49c2-a412-59140b32b9b3
RUNCOMFY_USER_ID: 0cb54d51-f01e-48e1-ae7b-28d1c21bc947
Workflow ID: f7ade856-0739-4fc8-8fa3-3b3857e2ebcb
Deployment ID: 1c6fa9a6-f60a-4e89-863d-40b03ad2564e
```

### 3. Import in Blender

1. Open Blender
2. Go to: **Edit → Preferences → Add-ons → Style Engine**
3. Look for the **"Quick Setup"** section at the top
4. Click **"Import from credentials.txt"**
5. Check the console/info area for success message

### 4. Verify Connection

After import, click **"Test Connection"** to verify your credentials work.

---

## File Format

The parser looks for this **exact format**:

```
RUNCOMFY_API_TOKEN: <value>
RUNCOMFY_USER_ID: <value>
Workflow ID: <value>
Deployment ID: <value>
```

### Format Rules:
- ✅ Use `KEY: value` format (colon + space)
- ✅ No quotes around values
- ✅ Lines starting with `#` are comments (ignored)
- ✅ Empty lines are ignored
- ✅ Key names must match exactly (case-sensitive)

---

## File Location

The importer looks for `credentials.txt` in these locations (in order):

1. `scripts/addons/styleengine/credentials.txt` (recommended)
2. `scripts/addons/credentials.txt` (alternative)

Choose whichever location is most convenient for your workflow.

---

## Security Notes

### ⚠️ Important Security Considerations:

1. **Never commit credentials.txt to version control**
   ```bash
   # Add to .gitignore:
   credentials.txt
   ```

2. **Use credentials.txt.template for sharing**
   - Commit the template file (with placeholder values)
   - Team members copy it and fill in their own credentials

3. **File permissions**
   - On Linux/macOS, consider: `chmod 600 credentials.txt`
   - This makes the file readable only by you

4. **For production/team use:**
   - Consider using **environment variables** instead
   - Or use a secrets management system
   - The credentials.txt method is best for development/personal use

---

## Troubleshooting

### "credentials.txt not found"
- Check the file is in the correct location
- Make sure it's named exactly `credentials.txt` (not `credentials.txt.txt`)
- Verify the addon is installed in the expected directory

### "Missing required credentials"
- Ensure `RUNCOMFY_API_TOKEN` and `RUNCOMFY_USER_ID` are present
- Check for typos in the key names (case-sensitive)
- Verify the format: `KEY: value` (with colon and space)

### "Error reading credentials.txt"
- Check file encoding is UTF-8
- Ensure no special characters in the file
- Try viewing the file in a plain text editor

### Credentials imported but connection fails
- Click "Test Connection" to verify credentials
- Check API token is valid and not expired
- Verify User ID matches your RunComfy account
- Check internet connection

---

## Example Workflow

### Personal Development:
```bash
# Create credentials file
cd scripts/addons/styleengine/
cp credentials.txt.template credentials.txt
nano credentials.txt  # Fill in your values

# In Blender:
# Edit > Preferences > Add-ons > Style Engine
# Click "Import from credentials.txt"
# Click "Test Connection"
```

### Team Sharing:
```bash
# Developer:
1. Keep credentials.txt in .gitignore
2. Commit credentials.txt.template with instructions

# Team member:
1. Clone repo
2. Copy credentials.txt.template to credentials.txt
3. Get credentials from team lead
4. Fill in credentials.txt
5. Import in Blender
```

---

## Alternative: Environment Variables

If you prefer, you can also use **environment variables** instead:

```bash
# On Linux/macOS:
export RUNCOMFY_API_TOKEN="your-token-here"
export RUNCOMFY_USER_ID="your-user-id-here"

# On Windows PowerShell:
$env:RUNCOMFY_API_TOKEN="your-token-here"
$env:RUNCOMFY_USER_ID="your-user-id-here"
```

Enable "Prefer Environment Variables" in preferences, and Style Engine will use these values.

---

## FAQ

**Q: Do I need to import every time I open Blender?**  
A: No, credentials are saved to Blender preferences and persist between sessions.

**Q: Can I update credentials later?**  
A: Yes, edit `credentials.txt` and click "Import from credentials.txt" again.

**Q: What if I want to use different credentials temporarily?**  
A: Either:
- Import a different credentials.txt
- Manually edit in preferences
- Use environment variables

**Q: Does this work on all platforms?**  
A: Yes! Works on Windows, macOS, and Linux.

**Q: Can I use this for multiple RunComfy accounts?**  
A: You can switch between accounts by importing different credentials.txt files or by manually editing in preferences.

---

## Technical Details

### Parser Implementation:
- **Location:** `utils.py::parse_credentials_file()`
- **Operator:** `prefs.py::WM_OT_ImportCredentials`
- **UI:** Preferences panel, "Quick Setup" section

### What Gets Imported:
- `RUNCOMFY_API_TOKEN` → `runcomfy_api_token`
- `RUNCOMFY_USER_ID` → `runcomfy_user_id`
- `Workflow ID` → `runcomfy_workflow_id`
- `Deployment ID` → `runcomfy_deployment_id`

### Import Process:
1. Parse credentials.txt for key-value pairs
2. Validate required fields exist
3. Apply values to addon preferences
4. Show success/error message
5. Suggest testing connection

---

## Support

If you encounter issues with credential import:
1. Check the Blender console for detailed error messages
2. Verify file format matches the template exactly
3. Test with a fresh copy of credentials.txt.template
4. Check file permissions and encoding

For additional help, refer to the main README.md or contact support.


