# Style Engine - API Setup Guide

## RunComfy API Configuration

Style Engine supports two methods for configuring your RunComfy API credentials:

### Method 1: Environment Variables (Recommended)

Setting environment variables keeps your API keys secure and separate from your code.

#### Windows Setup:

1. **Open Environment Variables:**
   - Press `Win + X` and select "System"
   - Click "Advanced system settings"
   - Click "Environment Variables"

2. **Add User Variables:**
   - Click "New" under "User variables"
   - Variable name: `RUNCOMFY_API_TOKEN`
   - Variable value: `your_actual_api_token_here`
   - Click OK
   
   - Click "New" again
   - Variable name: `RUNCOMFY_USER_ID`
   - Variable value: `your_user_id_here`
   - Click OK

3. **Restart Blender:**
   - Close Blender completely
   - Reopen Blender for changes to take effect

#### Quick PowerShell Setup:

You can also set environment variables temporarily for the current session:

```powershell
$env:RUNCOMFY_API_TOKEN = "your_actual_api_token_here"
$env:RUNCOMFY_USER_ID = "your_user_id_here"
# Then launch Blender from the same PowerShell window
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

#### Using a .env file (Developer Method):

Create a batch file to launch Blender with environment variables:

**`launch_blender_dev.bat`:**
```batch
@echo off
set RUNCOMFY_API_TOKEN=your_actual_api_token_here
set RUNCOMFY_USER_ID=your_user_id_here
start "" "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
```

### Method 2: Manual Entry in Blender

If you prefer not to use environment variables:

1. Open Blender
2. Go to **Edit → Preferences**
3. Select **Add-ons** tab
4. Find **Style Engine** in the list
5. Expand the addon preferences
6. **Uncheck** "Prefer Environment Variables"
7. Click "Show API Keys"
8. Enter your credentials manually:
   - **RunComfy API Token**
   - **RunComfy User ID**
9. Click "Test Connection" to verify

## Security Best Practices

### ✅ Do:
- Use environment variables for production
- Keep API tokens in `.env` files that are `.gitignore`d
- Use the "Show API Keys" toggle to hide sensitive data
- Test your connection after setup

### ❌ Don't:
- Commit API keys to version control
- Share screenshots with visible API keys
- Use the same API token across multiple machines without proper security

## Testing Your Setup

After configuration:

1. Open the Style Engine panel in Blender (press `N` in 3D Viewport)
2. Click any operation button (e.g., "Visualize")
3. Check the Blender console for output:
   - If configured correctly: You'll see masked API credentials
   - If not configured: You'll see an error message

Or use the preferences:

1. **Edit → Preferences → Add-ons → Style Engine**
2. Click **"Test Connection"**
3. Check for success/error messages

## Troubleshooting

### "API Token is not set" error

- **If using environment variables:**
  - Verify they're set: Open PowerShell and run `$env:RUNCOMFY_API_TOKEN`
  - Restart Blender after setting environment variables
  - Check "Prefer Environment Variables" is enabled in preferences

- **If using manual entry:**
  - Go to Edit → Preferences → Add-ons → Style Engine
  - Uncheck "Prefer Environment Variables"
  - Enter credentials manually

### Environment variables not detected

- Restart Blender completely
- Check that you set **User** or **System** variables, not just the current session
- Make sure there are no typos in variable names (they're case-sensitive)

## Getting Your RunComfy Credentials

1. Visit the RunComfy website
2. Log in to your account
3. Navigate to API settings or developer section
4. Generate or copy your API token
5. Note your User ID from your account settings

---

**Note:** Replace `your_actual_api_token_here` and `your_user_id_here` with your real credentials from RunComfy.


