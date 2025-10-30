# RunComfy Cloud - Testing Guide

**Deployment ID:** `408d6662-46ff-49bb-a480-cb6d7df7c4cd`  
**API Endpoint:** `https://api.runcomfy.net`

---

## ✅ Setup Complete

The following has been configured:

1. **✓ Deployment ID set** in `scripts/addons/styleengine/prefs.py`
   - Both SDXL and IPAdapter use the same deployment
   
2. **✓ API endpoint corrected** to `https://api.runcomfy.net`
   - Updated in `runcomfy_client.py`
   - Updated in `test_runcomfy_api.py`
   
3. **✓ Node mapping confirmed**:
   - SDXL: Nodes 25, 15, 40, 41, 42, 9 ✓
   - IPAdapter: All SDXL + nodes 43, 49, 52 ✓
   
4. **✓ Test script prepared** with deployment ID

---

## 🧪 Step 1: Test API Client (Isolated)

### Prerequisites

Set your RunComfy credentials as environment variables:

**Windows (PowerShell):**
```powershell
$env:RUNCOMFY_API_TOKEN="your_api_token_here"
$env:RUNCOMFY_USER_ID="your_user_id_here"
```

**Windows (CMD):**
```cmd
set RUNCOMFY_API_TOKEN=your_api_token_here
set RUNCOMFY_USER_ID=your_user_id_here
```

**Linux/Mac:**
```bash
export RUNCOMFY_API_TOKEN="your_api_token_here"
export RUNCOMFY_USER_ID="your_user_id_here"
```

### Run the Test

```bash
cd tests
python test_runcomfy_api.py
```

### Expected Output

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
  - Deployment Name (ID: 408d6662...)

ℹ Using deployment: 408d6662... for remaining tests

ℹ Test 3: Getting deployment details for 408d6662...
✓ Retrieved deployment: Your Deployment Name
  Status: Enabled
  Workflow ID: xxxxxxxx...

⚠ Test 4-6 will submit actual inference (may incur costs)
Continue? (y/N):
```

**If you choose to continue:**
```
ℹ Test 4: Submitting inference to 408d6662...
✓ Inference submitted! Request ID: abc12345...

ℹ Test 5: Polling status for request abc12345...
  Status: in_queue (elapsed: 5s)
  Status: in_progress (elapsed: 15s)
  Status: in_progress (elapsed: 25s)
✓ Request completed in 30s!

ℹ Test 6: Getting result for request abc12345...
✓ Found image URL: https://...
✓ Downloaded to: tests/test_download.png
  File size: 2.35 MB

ℹ Test 7: Testing image encoding...
⚠ Test image not found at tests/test_image.png, skipping encoding test

ℹ Test 8: Testing error handling...
✓ Correctly handled invalid deployment: HTTP 404: ...

==============================================================
  Test Summary
==============================================================
✓ auth: PASS
✓ list_deployments: PASS
✓ get_deployment: PASS
✓ submit_inference: PASS
✓ poll_status: PASS
✓ get_result: PASS
⚠ image_encoding: SKIPPED
✓ error_handling: PASS

✓ All tests passed! (7/8)
```

### Troubleshooting

**"Missing credentials"**
- Make sure environment variables are set
- Verify they're set in the current terminal session

**"Authentication failed"**
- Check API token is correct
- Check User ID is correct
- Verify credentials haven't expired

**"Deployment not found"**
- Verify deployment ID is correct: `408d6662-46ff-49bb-a480-cb6d7df7c4cd`
- Check deployment is enabled in RunComfy dashboard

**"Connection timeout"**
- Check internet connection
- Verify firewall isn't blocking HTTPS
- Try increasing timeout in client

---

## 🧪 Step 2: Test in Blender (Full Integration)

Once Step 1 passes, test in Blender:

### 2.1: Load Addon

1. Open Blender
2. Edit → Preferences → Add-ons
3. Install/Enable "Style Engine"
4. Check console for errors

**Expected console:**
```
[Style Engine] Addon loaded successfully
```

### 2.2: Configure Preferences

1. Edit → Preferences → Add-ons → Style Engine
2. **API Configuration:**
   - Set API Token (or use environment variable)
   - Set User ID (or use environment variable)
   - Click "Test Connection"

**Expected:**
```
✓ RUNCOMFY_API_TOKEN found in environment
✓ RUNCOMFY_USER_ID found in environment
Connection test successful!
```

3. **Workflow Configuration:** (expand section)
   - Verify "SDXL Deployment ID" = `408d6662-46ff-49bb-a480-cb6d7df7c4cd`
   - Verify "IPAdapter Deployment ID" = `408d6662-46ff-49bb-a480-cb6d7df7c4cd`

### 2.3: Test Workspace Setup

1. Switch to "Style Engine" tab in 3D viewport (N key)
2. Expand "Workspace Setup"
3. Click "Setup Workspace"

**Expected console:**
```
[Style Engine] Creating AI camera...
[Style Engine] Setting up compositor...
[Style Engine] Workspace setup complete!
```

**Expected result:**
- ai_camera created in scene
- Compositor enabled with Mist pass

### 2.4: Test Cloud Generation (Simple)

**⚠️ Warning:** This will incur costs on RunComfy

1. Set "Global Prompt": `"a beautiful sunset, photorealistic"`
2. Set Depth Influence: `0.5`
3. Set Silhouette Influence: `0.75`
4. Set Steps: `15`
5. Click "Generate (Cloud)"

**Expected console:**
```
[Style Engine] Using workflow: sdxl
[Style Engine] Using existing deployment: 408d6662...
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
- Server Status: "Connecting" → "Running Workflow" → "Disconnected"
- Elapsed time updates every 5 seconds
- AI image appears in camera background after completion

### 2.5: Test IPAdapter Workflow

1. Expand "Image Reference" section
2. Check "Use image reference"
3. Browse to a reference image
4. Select Mode: "Style Transfer"
5. Set Strength: `0.75`
6. Click "Generate (Cloud)"

**Expected console:**
```
[Style Engine] Using workflow: ipadapter
[Style Engine] Using existing deployment: 408d6662...
[Style Engine] ☁️ Cloud generation started (request_id: xyz67890...)
...
```

### 2.6: Test Project Texture & Iterations

1. After successful generation
2. Click "Project Texture"

**Expected console:**
```
[Style Engine] 🎨 Projected texture onto 4 objects
[Style Engine] 📦 Duplicated 4 objects
[Style Engine] 💾 Created Iteration_000 in Iterations collection
[Style Engine]    └─ Hidden from viewport (eye icon) and disabled in renders
[Style Engine] 📸 Saved image: Iteration_000.png
[Style Engine] 🎨 Material 'Iteration_000_Material' assigned with texture
```

**Expected result:**
- Texture projected onto all meshes
- Iteration_000 created (hidden, in Iterations collection)
- Image saved to `output_path/generated/Iteration_000.png`

---

## 🐛 Common Issues

### "Workflow ID not configured"
- Not applicable - deployment handles both workflows
- Deployment ID should be set: `408d6662-46ff-49bb-a480-cb6d7df7c4cd`

### "Generation timeout"
- Increase timeout in Advanced Settings (try 1200s)
- Cold start takes 2-5 minutes first time
- Check RunComfy dashboard for deployment status

### "No image found in result"
- Verify workflow completed successfully
- Check RunComfy dashboard for execution logs
- Review node mapping in NODE_MAPPING.md

### "Failed to encode image"
- Verify render passes exist (combined0001.png, depth0001.png)
- Check workspace was set up properly
- Try re-running "Setup Workspace"

---

## 📊 Expected Performance

### First Generation (Cold Start)
- **Time:** 2-5 minutes (SDXL), 3-6 minutes (IPAdapter)
- **Cost:** $0.05-$0.25 (depending on hardware)
- **Status progression:** in_queue (2-4 min) → in_progress (30-60s) → completed

### Subsequent Generations (Warm)
- **Time:** 15-30 seconds (SDXL), 20-40 seconds (IPAdapter)
- **Cost:** $0.008-$0.021 per generation
- **Status progression:** in_queue (0-5s) → in_progress (15-30s) → completed

---

## ✅ Success Criteria

API tests pass when:
- [ ] Authentication succeeds
- [ ] Deployment found and enabled
- [ ] Inference submitted successfully
- [ ] Status polling completes
- [ ] Result downloaded

Blender tests pass when:
- [ ] Addon loads without errors
- [ ] Test Connection validates credentials
- [ ] Workspace Setup creates camera
- [ ] Cloud generation completes
- [ ] AI image appears in background
- [ ] IPAdapter workflow works
- [ ] Project Texture works
- [ ] Iterations save correctly

---

## 📝 Next Steps After Testing

Once all tests pass:

1. **Update Documentation:**
   - Add any workflow-specific notes
   - Document any deviations
   - Update cost estimates based on actual usage

2. **User Testing:**
   - Test on different OS (Windows/Mac/Linux)
   - Test with different scenes
   - Test error scenarios

3. **Optimization:**
   - Adjust keep-warm duration based on usage patterns
   - Fine-tune timeout settings
   - Optimize polling interval

4. **Distribution:**
   - Package addon for distribution
   - Create user guide
   - Add troubleshooting documentation

---

**Ready to test?** Start with Step 1: `python tests/test_runcomfy_api.py`

