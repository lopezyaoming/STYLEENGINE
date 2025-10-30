# RunComfy Cloud - Next Steps

**Status:** Implementation 85% Complete  
**Date:** October 29, 2025

---

## 🎉 What's Been Completed

### ✅ Phase 1-5: Core Infrastructure (Complete)

All essential code has been implemented:
- ✅ Pure Python HTTP client (runcomfy_client.py)
- ✅ Deployment management (runcomfy_deployment.py)
- ✅ Async polling system (runcomfy_polling.py)
- ✅ Cloud generation functions (workspace_setup.py)
- ✅ UI integration with server status (ui_panel.py)
- ✅ Comprehensive preferences (prefs.py)
- ✅ Standalone test script (tests/test_runcomfy_api.py)

---

## 🔧 What Needs To Be Done

### Step 1: Upload Workflows to RunComfy

**Action:** Deploy workflow JSONs to RunComfy platform

**Files to upload:**
1. `ComfyUI/workflows/SDXLworkflow.json`
2. `ComfyUI/workflows/IPAdapterworkflow.json`

**Process:**
1. Go to https://runcomfy.com
2. Sign in to your account
3. Navigate to "Workflows" section
4. Upload each workflow
5. **Note the Workflow IDs** (you'll need these)

**Expected result:**
- SDXL Workflow ID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- IPAdapter Workflow ID: `yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy`

---

### Step 2: Update Workflow IDs in Code

**Action:** Set workflow IDs in preferences

**File:** `scripts/addons/styleengine/prefs.py`  
**Lines:** 49-58

**Current code:**
```python
runcomfy_workflow_id_sdxl: StringProperty(
    name="SDXL Workflow ID",
    description="RunComfy workflow ID for SDXL generation (provided by developer)",
    default=""  # ← EMPTY
)

runcomfy_workflow_id_ipadapter: StringProperty(
    name="IPAdapter Workflow ID",
    description="RunComfy workflow ID for IPAdapter generation (provided by developer)",
    default=""  # ← EMPTY
)
```

**Updated code:**
```python
runcomfy_workflow_id_sdxl: StringProperty(
    name="SDXL Workflow ID",
    description="RunComfy workflow ID for SDXL generation (provided by developer)",
    default="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # ← PASTE YOUR ID HERE
)

runcomfy_workflow_id_ipadapter: StringProperty(
    name="IPAdapter Workflow ID",
    description="RunComfy workflow ID for IPAdapter generation (provided by developer)",
    default="yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"  # ← PASTE YOUR ID HERE
)
```

---

### Step 3: Test Standalone API Client

**Action:** Verify RunComfy API connectivity

**Prerequisites:**
```bash
# Set environment variables (or use addon preferences)
export RUNCOMFY_API_TOKEN="your_api_token"
export RUNCOMFY_USER_ID="your_user_id"
```

**Run tests:**
```bash
cd tests
python test_runcomfy_api.py
```

**Expected output:**
```
==============================================================
  RunComfy API Test Suite
==============================================================

✓ Credentials found
ℹ User ID: your_user_id
ℹ API Token: ********************

ℹ Test 1: Testing authentication...
✓ Authentication successful! Found X deployments

ℹ Test 2: Listing deployments...
✓ Retrieved X deployments
  - Deployment Name (ID: abc12345...)

...

==============================================================
  Test Summary
==============================================================
✓ auth: PASS
✓ list_deployments: PASS
...

✓ All tests passed! (X/X)
```

**If tests fail:**
- Verify API credentials
- Check internet connection
- Review error messages
- See troubleshooting section below

---

### Step 4: Load Addon in Blender

**Action:** Test addon loads without errors

**Process:**
1. Open Blender
2. Edit → Preferences → Add-ons
3. Install → Select zip or point to `scripts/addons/styleengine/`
4. Enable "Style Engine"
5. Check Blender console for errors

**Expected console output:**
```
[Style Engine] Addon loaded successfully
```

**If errors occur:**
- Check Python console for traceback
- Verify all files are present
- Ensure Blender version 4.2+

---

### Step 5: Configure Preferences

**Action:** Set up RunComfy credentials and settings

**Location:** Edit → Preferences → Add-ons → Style Engine

**Required settings:**
1. **API Configuration:**
   - Set "RunComfy API Token" (or use environment variable)
   - Set "RunComfy User ID" (or use environment variable)
   - Click "Test Connection" to verify

2. **Workflow Configuration:** (expand section)
   - Verify "SDXL Workflow ID" is set
   - Verify "IPAdapter Workflow ID" is set
   - Leave "Deployment IDs" empty (will auto-create)

3. **Hardware Settings:** (expand section)
   - Select hardware tier (default: AMPERE_48 recommended)
   - Set Min Instances to 0 (scale to zero)
   - Set Max Instances to 1
   - Set Queue Size to 1
   - Set Keep Warm to 60 seconds

4. **Advanced Settings:** (expand section)
   - Request Timeout: 600 seconds (default)
   - Poll Interval: 5 seconds (default)

**Click "Test Connection"** to verify setup.

---

### Step 6: Test Workspace Setup

**Action:** Verify workspace creation works

**Process:**
1. Open new Blender file
2. Switch to "Style Engine" tab in 3D viewport sidebar (N key)
3. Expand "Workspace Setup"
4. Click "Setup Workspace"

**Expected result:**
- ai_camera created
- Compositor configured with Mist pass and Color Ramp
- Render settings updated
- Background image added to camera
- Console confirms: `[Style Engine] Workspace setup complete!`

**If errors occur:**
- Check Blender console
- Verify scene has at least one object
- Try in fresh .blend file

---

### Step 7: Test Cloud Generation

**Action:** Trigger actual cloud generation

**⚠️ Warning:** This will incur costs on RunComfy. First generation (cold start) may take 2-5 minutes.

**Process:**
1. Ensure workspace is set up (Step 6)
2. Set "Global Prompt" (e.g., "a beautiful sunset over mountains, photorealistic")
3. Adjust Depth Influence and Silhouette Influence if desired
4. Click "Generate (Cloud)"

**Expected console output:**
```
[Style Engine] Using workflow: sdxl
[Style Engine] Started polling for request abc12345...
[Style Engine] Polling timer started (interval: 5s)
[Style Engine] ☁️ Cloud generation started (request_id: abc12345...)
[RunComfy] Request abc12345: in_queue → in_progress
[RunComfy] Request abc12345: in_progress → completed
[RunComfy] Request abc12345 completed!
[Style Engine] Downloading result from: https://...
[Style Engine] ✅ Downloaded to temp
[Style Engine] 💾 Saved to C:\path\to\output\generated\20251029_143052_runcomfy.png
```

**Expected UI:**
- Server Status shows: "Connecting" → "Running Workflow" → "Disconnected"
- Elapsed time updates every 5 seconds
- After completion, AI image appears in camera background

**If generation fails:**
- Check console for error messages
- Verify workflow IDs are correct
- Check RunComfy account has sufficient credits
- Try increasing timeout in Advanced Settings

---

### Step 8: Test IPAdapter Workflow

**Action:** Verify reference image workflow works

**Process:**
1. Expand "Image Reference" section
2. Check "Use image reference"
3. Browse to a reference image
4. Select Mode (e.g., "Style Transfer")
5. Set Strength (e.g., 0.75)
6. Click "Generate (Cloud)"

**Expected:**
- Workflow type: ipadapter (in console)
- Generation includes reference image influence
- Output matches reference style/composition

---

### Step 9: Test Project Texture & Iterations

**Action:** Verify texture projection and saving works

**Process:**
1. After successful generation
2. Click "Project Texture"

**Expected:**
- Texture projected onto all meshes from AI camera
- If "Save Iterations" enabled:
  - Iteration_000 created in "Iterations" collection
  - Hidden from viewport (eye icon closed)
  - Disabled in renders
  - Has material with AI texture
  - Image saved to `output_path/generated/Iteration_000.png`

---

### Step 10: Document Workflow IDs

**Action:** Update workflow documentation

**File:** `docs/RUNCOMFY_WORKFLOWS.md`

**Update these sections:**
- Replace "PASTE_SDXL_WORKFLOW_ID_HERE" with actual ID
- Replace "PASTE_IPADAPTER_WORKFLOW_ID_HERE" with actual ID
- Add any workflow-specific notes
- Document any deviations from expected node structure

---

## 🧪 Testing Checklist

### Minimal Testing (Quick Validation)
- [ ] Addon loads without errors
- [ ] Preferences display correctly
- [ ] Test Connection works
- [ ] Workspace Setup creates camera
- [ ] Single cloud generation completes
- [ ] Result appears in camera background

### Full Testing (Comprehensive)
- [ ] All minimal tests pass
- [ ] Output path saving works
- [ ] IPAdapter workflow works
- [ ] Project Texture works
- [ ] Save Iterations works
- [ ] Cancel generation works
- [ ] Multiple sequential generations
- [ ] Auto-generation respects polling state
- [ ] Error scenarios handled gracefully

---

## 🐛 Troubleshooting

### "Workflow ID not configured"

**Error:** `RunComfyError: SDXL workflow ID not configured`

**Solution:**
1. Open `scripts/addons/styleengine/prefs.py`
2. Update lines 49-58 with workflow IDs
3. Reload addon in Blender

---

### "Authentication failed"

**Error:** `RunComfyAuthError: Authentication failed: Invalid token`

**Solutions:**
1. Verify API token is correct
2. Check environment variables are set
3. Ensure "Prefer Environment Variables" is enabled if using env vars
4. Try pasting credentials directly in preferences

---

### "Deployment not found"

**Error:** `RunComfyDeploymentError: Not found`

**Solutions:**
1. Clear deployment IDs in preferences (let addon auto-create)
2. Verify workflow IDs are correct
3. Check RunComfy account has proper permissions

---

### "Generation timeout"

**Error:** `Timeout after 600s`

**Solutions:**
1. Increase timeout in Advanced Settings (try 1200s)
2. Cold start takes longer (2-5 minutes first time)
3. Check RunComfy status page for issues

---

### "No image found in result"

**Error:** `[Style Engine] No image found in result`

**Solutions:**
1. Verify workflow has SaveImage node (Node 9)
2. Check workflow executed successfully in RunComfy dashboard
3. Review workflow structure matches specifications

---

### "Failed to encode image"

**Error:** `RunComfyError: Failed to encode image`

**Solutions:**
1. Verify render passes exist (combined0001.png, depth0001.png)
2. Check file paths are correct
3. Ensure workspace was set up properly
4. Try re-running "Setup Workspace"

---

## 📊 Performance Expectations

### First Generation (Cold Start)
- **Time:** 2-5 minutes (SDXL), 3-6 minutes (IPAdapter)
- **Cost:** $0.05-$0.25 depending on hardware

### Subsequent Generations (Warm)
- **Time:** 15-30 seconds (SDXL), 20-40 seconds (IPAdapter)
- **Cost:** $0.008-$0.021 per generation

### Keep-Warm Strategy
- Set "Keep Warm" to 60+ seconds for active sessions
- Scale to zero (Min Instances = 0) when not in use
- Balance between cost and convenience

---

## 📁 Required Files Checklist

Ensure all files are present:

### Core Implementation
- [x] `scripts/addons/styleengine/runcomfy_client.py`
- [x] `scripts/addons/styleengine/runcomfy_deployment.py`
- [x] `scripts/addons/styleengine/runcomfy_polling.py`
- [x] `scripts/addons/styleengine/workspace_setup.py` (modified)
- [x] `scripts/addons/styleengine/ui_panel.py` (modified)
- [x] `scripts/addons/styleengine/prefs.py` (modified)
- [x] `scripts/addons/styleengine/__init__.py` (modified)

### Testing & Documentation
- [x] `tests/test_runcomfy_api.py`
- [x] `docs/RUNCOMFY_WORKFLOWS.md`
- [x] `context/RUNCOMFY_IMPLEMENTATION_STATUS.md`
- [x] `context/RUNCOMFY_NEXT_STEPS.md` (this file)

### Workflows (to deploy)
- [ ] `ComfyUI/workflows/SDXLworkflow.json` (needs deployment)
- [ ] `ComfyUI/workflows/IPAdapterworkflow.json` (needs deployment)

---

## 🎯 Success Criteria

The implementation is complete when:
1. ✅ All code files implemented
2. ⏳ Workflows deployed to RunComfy
3. ⏳ Workflow IDs set in prefs.py
4. ⏳ API tests pass
5. ⏳ Addon loads in Blender
6. ⏳ Test generation completes successfully
7. ⏳ IPAdapter workflow works
8. ⏳ All features (texture, iterations, cancel) work

**Current Status:** 1/8 complete (code done, awaiting deployment)

---

## 💬 Support Resources

### Documentation
- `context/RUNCOMFY_IMPLEMENTATION_STATUS.md` - Implementation details
- `docs/RUNCOMFY_WORKFLOWS.md` - Workflow specifications
- `context/RUNCOMFY_CLOUD_VERSION_PLAN.md` - Original plan

### Code References
- `tests/test_runcomfy_api.py` - API usage examples
- `scripts/addons/styleengine/runcomfy_client.py` - Client documentation
- Blender console - Real-time logging

### External
- RunComfy Dashboard: https://runcomfy.com
- RunComfy API Docs: (see RUNCOMFY API DOCS.txt)
- Blender API: https://docs.blender.org/api/

---

**Ready to proceed?** Start with Step 1: Upload workflows to RunComfy!

