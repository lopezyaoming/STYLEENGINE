# Preferences UI Cleanup

## Changes Made

### 1. Default Backend Changed
- **Before**: RunComfy Cloud (developer-focused)
- **After**: Self-Hosted ComfyUI (user-focused)

### 2. Structure Simplified
- **Before**: 400+ lines, multiple nested boxes, verbose
- **After**: ~110 lines, Basic/Advanced split

### 3. Basic Settings (Always Visible)
**Self-Hosted ComfyUI mode:**
- Server URL field
- Test Connection button

**RunComfy Cloud mode:**
- Credentials file browser
- Import Credentials button
- Show Credentials toggle
- Manual API Token/User ID fields (if toggled)
- Test Connection button

### 4. Advanced Settings (Collapsed by Default)
**GCS mode:**
- Preview images option (Canny & Depth download)

**RunComfy mode:**
- Workflow Configuration (IDs)
- Hardware Settings (GPU tier, scaling)

**Both modes:**
- Timeout Configuration
- ComfyUI Installation path
- Conflict Resolution (debug, naming overrides)
- Feature Toggles (HEAVYPOLY, camera, workspace, etc.)

### 5. Removed Verbosity
- ❌ No more example URLs
- ❌ No more "How to use" instructions
- ❌ No more validation status messages (✓/⚠)
- ❌ No more help text and hints
- ✅ Crystal clear, minimal UI

## Result
90% of users see only:
- Backend selector
- Server URL field
- Test Connection button

Developers see full control in Advanced Settings.

