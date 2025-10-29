# Style Engine Cloud - RunComfy Version Development Plan

**Version:** 1.0  
**Date:** October 29, 2025  
**Target:** Lightweight, cloud-only Blender addon using RunComfy API

---

## 🎯 Project Goals

### Primary Objectives
1. Create a **zero-dependency** Blender addon that works exclusively via RunComfy API
2. Enable **cross-platform distribution** (Windows, Mac, Linux) without OS-specific setup
3. Provide **identical UX** to local version but with cloud backend
4. Eliminate need for local ComfyUI installation and FastAPI server
5. Make installation as simple as: Download → Install → Add API Keys → Generate

### Success Criteria
- ✅ Single `.zip` file distribution
- ✅ No `requirements.txt` or external Python packages
- ✅ Works on fresh Blender install (4.0+)
- ✅ API key setup takes < 2 minutes
- ✅ First generation works within 5 minutes of install

---

## 🏗️ Architecture Comparison

### Current "Pro" Version
```
Blender Addon
    ↓
FastAPI Local Server (localhost:8000)
    ↓
Local ComfyUI Instance (localhost:8188)
    ↓
Local GPU Processing
    ↓
File System (current_ai.png)
    ↓
Blender Camera Background
```

**Dependencies:**
- Python packages (fastapi, uvicorn, websockets, httpx, watchdog)
- Local ComfyUI installation
- GPU with sufficient VRAM
- Complex setup scripts

### New "Cloud" Version
```
Blender Addon (Pure Python)
    ↓
HTTPS POST (urllib.request)
    ↓
RunComfy API (https://api.runcomfy.net)
    ↓
Cloud GPU Processing
    ↓
Image URL → Download → current_ai.png
    ↓
Blender Camera Background
```

**Dependencies:**
- None! (All built into Blender's Python)

---

## 📦 File Structure

```
scripts/addons/styleengine/
├── __init__.py                    # Addon registration (MODIFIED)
├── blender_manifest.toml          # Addon metadata (MODIFIED)
├── prefs.py                       # Preferences UI (MODIFIED)
├── runcomfy_client.py             # NEW: Pure Python API client
├── runcomfy_deployment.py         # NEW: Deployment management
├── runcomfy_polling.py            # NEW: Status polling system
├── workspace_setup_cloud.py       # NEW: Cloud-specific setup
└── UI/
    └── ui_panel_cloud.py          # NEW: Cloud UI panel

# Keep existing for reference:
├── workspace_setup.py             # Original (local version)
└── UI/
    └── ui_panel.py                # Original (local version)
```

---

## 🔧 Technical Implementation Plan

### Phase 1: Core API Client (Week 1)

#### 1.1: `runcomfy_client.py` - HTTP Client Module
**Purpose:** Pure Python HTTP client for RunComfy API

**Key Functions:**
```python
class RunComfyClient:
    def __init__(self, api_token: str, user_id: str):
        """Initialize with credentials from addon prefs"""
        
    def create_deployment(self, workflow_id: str, name: str, hardware: str) -> dict:
        """POST /prod/v2/deployments"""
        
    def get_deployment(self, deployment_id: str) -> dict:
        """GET /prod/v2/deployments/{deployment_id}"""
        
    def list_deployments(self) -> list:
        """GET /prod/v2/deployments"""
        
    def submit_inference(self, deployment_id: str, overrides: dict) -> dict:
        """POST /prod/v1/deployments/{deployment_id}/inference
        Returns: {request_id, status_url, result_url, cancel_url}"""
        
    def check_status(self, deployment_id: str, request_id: str) -> dict:
        """GET /prod/v1/deployments/{deployment_id}/requests/{request_id}/status
        Returns: {status: in_queue|in_progress|completed|failed}"""
        
    def get_result(self, deployment_id: str, request_id: str) -> dict:
        """GET /prod/v1/deployments/{deployment_id}/requests/{request_id}/result
        Returns: {status, outputs, created_at, finished_at}"""
        
    def cancel_request(self, deployment_id: str, request_id: str) -> dict:
        """POST /prod/v1/deployments/{deployment_id}/requests/{request_id}/cancel"""
```

**Implementation Details:**
- Use `urllib.request` for HTTP (built-in)
- Use `json` for serialization (built-in)
- Proper error handling with custom exceptions
- Add timeout (30s for API calls)
- Add retry logic (3 attempts with exponential backoff)

**Error Handling:**
```python
class RunComfyError(Exception):
    pass

class RunComfyAuthError(RunComfyError):
    """401 - Invalid API key"""
    
class RunComfyDeploymentError(RunComfyError):
    """404/403 - Deployment not found or disabled"""
    
class RunComfyValidationError(RunComfyError):
    """422 - Invalid request data"""
    
class RunComfyExecutionError(RunComfyError):
    """10011 - Workflow execution failed"""
```

---

#### 1.2: Image Encoding/Decoding
**Purpose:** Convert render passes to Base64 for upload

**Key Functions:**
```python
def encode_image_to_base64(image_path: str) -> str:
    """Read PNG file and convert to base64 data URI"""
    with open(image_path, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode('utf-8')
    return f"data:image/png;base64,{img_data}"

def download_image_from_url(url: str, save_path: str) -> bool:
    """Download image from RunComfy result URL"""
    try:
        urllib.request.urlretrieve(url, save_path)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False
```

**Optimization:**
- Compress PNGs before encoding (PIL if available, else raw)
- Target <1MB for fast upload
- Validate file size before encoding

---

#### 1.3: Testing Strategy
**Test Cases:**
- ✅ Valid API token → successful auth
- ✅ Invalid API token → proper error
- ✅ Create deployment → returns deployment_id
- ✅ Submit inference → returns request_id
- ✅ Check status → returns status progression
- ✅ Get result → downloads image successfully
- ✅ Network timeout → retry logic works
- ✅ Malformed response → graceful error

**Test Script:** Create `tests/test_runcomfy_client.py`

---

### Phase 2: Deployment Management (Week 1-2)

#### 2.1: `runcomfy_deployment.py` - Deployment Lifecycle
**Purpose:** Manage deployment creation, selection, and validation

**Key Features:**
```python
class DeploymentManager:
    def ensure_deployment(self, context) -> str:
        """Check if deployment exists, create if needed
        Returns: deployment_id"""
        
    def validate_deployment(self, deployment_id: str) -> bool:
        """Check if deployment is enabled and ready"""
        
    def get_or_create_default_deployment(self) -> str:
        """Get existing deployment or create with default settings:
        - Name: "Style Engine Cloud"
        - Workflow: SDXL workflow (predefined workflow_id)
        - Hardware: AMPERE_48 (48GB A6000)
        - Min instances: 0 (scale to zero)
        - Max instances: 1 (single user)
        - Queue size: 1
        - Keep warm: 60 seconds
        """
        
    def estimate_cost(self, hardware: str, duration_seconds: int) -> float:
        """Calculate estimated cost for generation"""
```

**Deployment Strategy:**
Two options for user choice:

**Option A: User-Managed** (Recommended for v1)
- User creates deployment via RunComfy dashboard
- User copies deployment_id into addon preferences
- Addon validates deployment before use
- Pro: User has full control, transparent costs
- Con: One extra setup step

**Option B: Auto-Created** (Future enhancement)
- Addon creates deployment on first use
- Stored in addon preferences
- Addon manages lifecycle (disable when not in use)
- Pro: Zero setup for user
- Con: More complex, need cleanup logic

**Implementation for v1:** Option A with guided instructions

---

#### 2.2: Preferences Integration
**Modify `prefs.py`:**

```python
class StyleEnginePreferences(bpy.types.AddonPreferences):
    # Existing fields
    runcomfy_api_token: StringProperty(...)
    runcomfy_user_id: StringProperty(...)
    
    # NEW: Cloud version fields
    runcomfy_deployment_id: StringProperty(
        name="Deployment ID",
        description="RunComfy deployment ID for cloud generation",
        default=""
    )
    
    use_cloud_mode: BoolProperty(
        name="Use Cloud Mode",
        description="Use RunComfy cloud instead of local ComfyUI",
        default=False
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Mode selector
        box = layout.box()
        box.label(text="Generation Mode:", icon='WORLD')
        box.prop(self, "use_cloud_mode")
        
        if self.use_cloud_mode:
            # Cloud settings
            box.prop(self, "runcomfy_api_token")
            box.prop(self, "runcomfy_user_id")
            box.prop(self, "runcomfy_deployment_id")
            
            # Test connection button
            row = box.row()
            row.operator("styleengine.test_runcomfy_connection", 
                        text="Test Connection", icon='CHECKBOX_HLT')
            
            # Quick setup guide
            box.label(text="Setup Guide:", icon='INFO')
            box.label(text="1. Get API keys from runcomfy.com/profile")
            box.label(text="2. Create deployment at runcomfy.com/comfyui-api/deployments")
            box.label(text="3. Copy deployment ID here")
            
        else:
            # Local settings (existing)
            box.prop(self, "comfyui_path")
            # ...
```

**New Operators:**
```python
class STYLEENGINE_OT_TestRunComfyConnection(bpy.types.Operator):
    bl_idname = "styleengine.test_runcomfy_connection"
    bl_label = "Test RunComfy Connection"
    
    def execute(self, context):
        prefs = get_addon_prefs()
        client = RunComfyClient(prefs.runcomfy_api_token, prefs.runcomfy_user_id)
        
        try:
            # Test API connection
            deployments = client.list_deployments()
            self.report({'INFO'}, f"✅ Connected! Found {len(deployments)} deployments")
            
            # Validate deployment if set
            if prefs.runcomfy_deployment_id:
                deployment = client.get_deployment(prefs.runcomfy_deployment_id)
                if deployment['is_enabled']:
                    self.report({'INFO'}, f"✅ Deployment '{deployment['name']}' is ready")
                else:
                    self.report({'WARNING'}, "⚠️ Deployment is disabled")
                    
        except RunComfyAuthError:
            self.report({'ERROR'}, "❌ Invalid API credentials")
        except Exception as e:
            self.report({'ERROR'}, f"❌ Connection failed: {str(e)}")
            
        return {'FINISHED'}
```

---

### Phase 3: Async Polling System (Week 2)

#### 3.1: `runcomfy_polling.py` - Non-Blocking Status Checks
**Purpose:** Poll RunComfy API without freezing Blender UI

**Architecture:**
```python
class RunComfyPoller:
    """Manages background polling of RunComfy requests"""
    
    active_requests: Dict[str, RequestState] = {}
    
    @classmethod
    def start_polling(cls, deployment_id: str, request_id: str, callback: callable):
        """Register a request for polling"""
        cls.active_requests[request_id] = RequestState(
            deployment_id=deployment_id,
            request_id=request_id,
            status="in_queue",
            callback=callback,
            start_time=time.time()
        )
        
        # Register timer if not already running
        if not bpy.app.timers.is_registered(cls._poll_tick):
            bpy.app.timers.register(cls._poll_tick, first_interval=5.0)
    
    @classmethod
    def _poll_tick(cls) -> float:
        """Called by Blender timer every 5 seconds"""
        client = get_runcomfy_client()
        
        completed = []
        for request_id, state in cls.active_requests.items():
            try:
                status_data = client.check_status(
                    state.deployment_id, 
                    request_id
                )
                
                state.status = status_data['status']
                
                if state.status == 'completed':
                    # Fetch result
                    result = client.get_result(state.deployment_id, request_id)
                    state.callback(success=True, result=result)
                    completed.append(request_id)
                    
                elif state.status == 'failed':
                    result = client.get_result(state.deployment_id, request_id)
                    error = result.get('error', 'Unknown error')
                    state.callback(success=False, error=error)
                    completed.append(request_id)
                    
                elif time.time() - state.start_time > 600:  # 10 min timeout
                    state.callback(success=False, error="Timeout")
                    completed.append(request_id)
                    
            except Exception as e:
                state.callback(success=False, error=str(e))
                completed.append(request_id)
        
        # Clean up completed requests
        for request_id in completed:
            del cls.active_requests[request_id]
        
        # Continue polling if requests remain, else stop timer
        return 5.0 if cls.active_requests else None
```

**UI Status Indicator:**
```python
def draw_polling_status(layout, context):
    """Show active generation status in UI"""
    active = RunComfyPoller.active_requests
    
    if active:
        box = layout.box()
        box.label(text=f"⏳ Generating... ({len(active)} active)", icon='TIME')
        
        for req_id, state in active.items():
            row = box.row()
            row.label(text=f"Status: {state.status}")
            
            elapsed = int(time.time() - state.start_time)
            row.label(text=f"Time: {elapsed}s")
            
            # Cancel button
            op = row.operator("styleengine.cancel_runcomfy_request", 
                             text="", icon='X')
            op.request_id = req_id
```

---

### Phase 4: Cloud-Specific Workflow Setup (Week 2-3)

#### 4.1: `workspace_setup_cloud.py` - Modified Setup
**Purpose:** Same workspace setup but with cloud generation

**Key Differences from Local Version:**
```python
class CloudWorkspaceSetup:
    """Cloud-specific workspace and generation logic"""
    
    def setup_workspace(self, context):
        """Same as local version:
        - Create AI camera
        - Setup compositor with Mist pass
        - Configure render settings
        - Create background image
        """
        # Reuse existing logic from workspace_setup.py
        
    def generate_ai_image(self, context):
        """NEW: Cloud generation workflow"""
        
        # 1. Render passes (same as local)
        self.render_passes(context)
        
        # 2. Encode images to Base64
        combined_b64 = encode_image_to_base64("combined0001.png")
        depth_b64 = encode_image_to_base64("depth0001.png")
        
        # 3. Read session data (same as local)
        session_data = self.read_session_json()
        
        # 4. Build RunComfy overrides
        overrides = self.build_overrides(
            prompt=session_data['global_prompt'],
            combined_image=combined_b64,
            depth_image=depth_b64,
            depth_influence=session_data['depth_influence'],
            silhouette_influence=session_data['silhouette_influence'],
            steps=session_data['steps'],
            resolution=session_data['resolution']
        )
        
        # 5. Submit to RunComfy
        prefs = get_addon_prefs()
        client = RunComfyClient(prefs.runcomfy_api_token, prefs.runcomfy_user_id)
        
        try:
            response = client.submit_inference(
                deployment_id=prefs.runcomfy_deployment_id,
                overrides=overrides
            )
            
            # 6. Start polling for result
            RunComfyPoller.start_polling(
                deployment_id=prefs.runcomfy_deployment_id,
                request_id=response['request_id'],
                callback=self.on_generation_complete
            )
            
            self.report({'INFO'}, "☁️ Cloud generation started!")
            
        except RunComfyError as e:
            self.report({'ERROR'}, f"Cloud generation failed: {str(e)}")
    
    def build_overrides(self, prompt, combined_image, depth_image, 
                       depth_influence, silhouette_influence, steps, resolution):
        """Build RunComfy API overrides JSON
        
        Maps to SDXLworkflow.json nodes:
        - Node 25: Prompt text
        - Node 15: Combined pass image (Base64)
        - Node 40: Silhouette strength (canny)
        - Node 41: Depth strength
        - Node 42: Steps
        """
        return {
            "25": {  # PrimitiveString - Prompt
                "inputs": {
                    "value": prompt
                }
            },
            "15": {  # LoadImage - Combined Pass
                "inputs": {
                    "image": combined_image  # Base64 data URI
                }
            },
            "40": {  # cannyStrength
                "inputs": {
                    "value": silhouette_influence
                }
            },
            "41": {  # depthStrength
                "inputs": {
                    "value": depth_influence
                }
            },
            "42": {  # Steps
                "inputs": {
                    "value": steps
                }
            }
        }
    
    def on_generation_complete(self, success: bool, result=None, error=None):
        """Callback when RunComfy generation finishes"""
        
        if success and result:
            # Extract image URL from result
            outputs = result.get('outputs', {})
            
            # Find SaveImage node output (Node 9 in SDXLworkflow.json)
            for node_id, node_output in outputs.items():
                if 'images' in node_output and node_output['images']:
                    image_url = node_output['images'][0]['url']
                    
                    # Download image
                    ai_path = self.get_ai_image_path()
                    if download_image_from_url(image_url, ai_path):
                        # Refresh camera background
                        self.update_camera_background()
                        print("[Style Engine] ✅ Cloud generation complete!")
                    else:
                        print("[Style Engine] ❌ Failed to download result")
                    break
        else:
            print(f"[Style Engine] ❌ Generation failed: {error}")
```

#### 4.2: Auto-Generation with Cloud
**Challenge:** Cloud has longer latency (15-30s vs 5s local)

**Solution:** Adjust auto-generation logic
```python
def should_trigger_auto_generation(self, context):
    """Only trigger if no active cloud requests"""
    
    # Don't trigger if already generating
    if RunComfyPoller.active_requests:
        return False
    
    # Check if render passes changed (same as local)
    if self.render_passes_changed():
        return True
    
    return False
```

**User Control:**
```python
# In UI panel
row.prop(props, "auto_generate_cloud", text="Auto-Generate (Cloud)")
row.label(text="⚠️ Uses cloud credits", icon='INFO')
```

---

### Phase 5: UI Integration (Week 3)

#### 5.1: `ui_panel_cloud.py` - Cloud UI Panel
**Purpose:** Modified UI panel for cloud mode

**Key Changes:**
```python
class STYLEENGINE_PT_CloudPanel(bpy.types.Panel):
    bl_label = "Style Engine Cloud"
    bl_idname = "STYLEENGINE_PT_cloud_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Style Engine'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.styleengine_props
        prefs = get_addon_prefs()
        
        # Status indicator
        self.draw_status(layout, prefs)
        
        # Workspace setup (same as local)
        box = layout.box()
        box.label(text="Workspace", icon='SCENE_DATA')
        box.operator("styleengine.setup_workspace_cloud")
        
        # Generation settings (same as local)
        box = layout.box()
        box.label(text="Generation", icon='IMAGE_DATA')
        box.prop(props, "global_prompt")
        box.prop(props, "depth_influence")
        box.prop(props, "silhouette_influence")
        box.prop(props, "steps")
        
        # Generate button with status
        row = box.row(align=True)
        row.scale_y = 1.5
        
        if RunComfyPoller.active_requests:
            row.enabled = False
            row.operator("styleengine.generate_cloud", 
                        text="⏳ Generating...", icon='TIME')
        else:
            row.operator("styleengine.generate_cloud", 
                        text="☁️ Generate Cloud", icon='WORLD')
        
        # Cost estimate
        self.draw_cost_estimate(box, props)
        
        # Active requests status
        if RunComfyPoller.active_requests:
            draw_polling_status(layout, context)
        
        # Project texture (same as local)
        box = layout.box()
        box.label(text="Apply Result", icon='TEXTURE')
        box.operator("styleengine.project_texture")
        box.prop(props, "background_opacity")
    
    def draw_status(self, layout, prefs):
        """Show connection status"""
        box = layout.box()
        
        if not prefs.runcomfy_api_token or not prefs.runcomfy_user_id:
            box.label(text="⚠️ API keys not configured", icon='ERROR')
            box.operator("preferences.addon_show", 
                        text="Open Preferences").module = "styleengine"
            return
        
        if not prefs.runcomfy_deployment_id:
            box.label(text="⚠️ No deployment configured", icon='ERROR')
            box.operator("preferences.addon_show", 
                        text="Configure Deployment").module = "styleengine"
            return
        
        # All good
        box.label(text="☁️ Cloud Ready", icon='CHECKBOX_HLT')
    
    def draw_cost_estimate(self, layout, props):
        """Show estimated cost for generation"""
        box = layout.box()
        box.label(text="💰 Cost Estimate:", icon='INFO')
        
        # Estimate based on typical generation time
        # AMPERE_48 = $2.50/hour
        # Typical generation: 20 seconds
        cost_per_second = 2.50 / 3600
        estimated_seconds = 20  # Cold start + generation
        estimated_cost = cost_per_second * estimated_seconds
        
        box.label(text=f"~${estimated_cost:.3f} per generation")
        box.label(text="(First generation may take longer)")
```

---

### Phase 6: Workflow Configuration (Week 3)

#### 6.1: Predefined Workflow Setup
**Challenge:** User needs a workflow deployed on RunComfy

**Solutions:**

**Option 1: User Deploys via RunComfy Dashboard** (Recommended for v1)
```markdown
# User Instructions:
1. Go to runcomfy.com
2. Navigate to ComfyUI Workflows
3. Find "SDXL Image Generation with ControlNet"
4. Click "Deploy as API"
5. Configure:
   - Hardware: AMPERE_48 (48GB)
   - Min instances: 0
   - Max instances: 1
   - Queue size: 1
   - Keep warm: 60s
6. Copy Deployment ID
7. Paste into Blender > Preferences > Style Engine
```

**Option 2: Shared Public Workflow** (Future)
- Create a public RunComfy workflow template
- User clicks "Clone & Deploy" link
- Automated setup

**Option 3: Addon-Managed Deployment** (Future)
- Addon creates deployment via API
- Requires workflow_id from RunComfy
- More complex, need cleanup logic

**Implementation for v1:** Option 1 with clear documentation

#### 6.2: Workflow JSON Validation
**Ensure local workflow matches cloud workflow:**

```python
def validate_workflow_compatibility(workflow_json: dict) -> bool:
    """Check if workflow has expected nodes"""
    
    required_nodes = {
        "25": "PrimitiveString",  # Prompt
        "15": "LoadImage",         # Combined pass
        "40": "PrimitiveFloat",    # Canny strength
        "41": "PrimitiveFloat",    # Depth strength
        "42": "PrimitiveInt",      # Steps
        "9": "SaveImage"           # Output
    }
    
    for node_id, expected_type in required_nodes.items():
        if node_id not in workflow_json:
            print(f"Missing node {node_id} ({expected_type})")
            return False
    
    return True
```

---

### Phase 7: Error Handling & User Feedback (Week 4)

#### 7.1: Comprehensive Error Messages
**Map RunComfy error codes to user-friendly messages:**

```python
ERROR_MESSAGES = {
    # Auth errors
    401001: {
        'title': "Invalid API Key",
        'message': "Your RunComfy API key is invalid or expired. Please check your credentials in addon preferences.",
        'action': "Open Preferences"
    },
    
    # Deployment errors
    10002: {
        'title': "Deployment Disabled",
        'message': "Your deployment is currently disabled. Please enable it on the RunComfy dashboard.",
        'action': "Open RunComfy Dashboard"
    },
    
    10001: {
        'title': "Insufficient Funds",
        'message': "Your RunComfy account has insufficient credits. Please add funds to continue.",
        'action': "Add Credits"
    },
    
    # Execution errors
    10011: {
        'title': "Generation Failed",
        'message': "The AI generation failed. This could be due to invalid settings or workflow issues.",
        'action': "Check Settings"
    },
    
    # Network errors
    'timeout': {
        'title': "Connection Timeout",
        'message': "Could not connect to RunComfy API. Please check your internet connection.",
        'action': "Retry"
    }
}

def show_error_popup(error_code, details=""):
    """Show modal error dialog"""
    def draw(self, context):
        error_info = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES['timeout'])
        
        layout = self.layout
        layout.label(text=error_info['title'], icon='ERROR')
        
        box = layout.box()
        for line in error_info['message'].split('\n'):
            box.label(text=line)
        
        if details:
            box.label(text=f"Details: {details}")
        
        layout.operator("styleengine.error_action", 
                       text=error_info['action'])
    
    bpy.context.window_manager.popup_menu(draw, 
                                          title="Style Engine Error", 
                                          icon='ERROR')
```

#### 7.2: Progress Indicators
**Show detailed progress during generation:**

```python
class GenerationProgress:
    """Track and display generation progress"""
    
    stages = {
        'in_queue': {
            'icon': 'SORTTIME',
            'message': 'Waiting in queue...',
            'progress': 0.1
        },
        'cold_start': {
            'icon': 'TIME',
            'message': 'Starting instance (2-5 min)...',
            'progress': 0.3
        },
        'in_progress': {
            'icon': 'MOD_BUILD',
            'message': 'Generating image...',
            'progress': 0.6
        },
        'downloading': {
            'icon': 'IMPORT',
            'message': 'Downloading result...',
            'progress': 0.9
        },
        'completed': {
            'icon': 'CHECKMARK',
            'message': 'Complete!',
            'progress': 1.0
        }
    }
    
    @classmethod
    def draw(cls, layout, current_stage, elapsed_time):
        """Draw progress bar and status"""
        
        stage_info = cls.stages.get(current_stage, cls.stages['in_queue'])
        
        row = layout.row()
        row.label(text=stage_info['message'], icon=stage_info['icon'])
        
        # Progress bar
        layout.progress(
            factor=stage_info['progress'],
            type='BAR',
            text=f"{int(stage_info['progress'] * 100)}%"
        )
        
        # Time elapsed
        minutes, seconds = divmod(int(elapsed_time), 60)
        layout.label(text=f"Time: {minutes}m {seconds}s")
```

---

### Phase 8: Testing & Validation (Week 4)

#### 8.1: Unit Tests
```python
# tests/test_runcomfy_client.py
def test_api_connection():
    """Test basic API connectivity"""
    
def test_deployment_creation():
    """Test creating a deployment"""
    
def test_inference_submission():
    """Test submitting an inference request"""
    
def test_status_polling():
    """Test polling request status"""
    
def test_result_retrieval():
    """Test downloading result"""
    
def test_error_handling():
    """Test proper error handling"""

# tests/test_image_encoding.py
def test_base64_encoding():
    """Test image to base64 conversion"""
    
def test_image_size_limits():
    """Test handling of large images"""
    
def test_image_download():
    """Test downloading from URL"""
```

#### 8.2: Integration Tests
```python
# tests/test_full_workflow.py
def test_end_to_end_generation():
    """Test complete generation workflow:
    1. Setup workspace
    2. Render passes
    3. Encode images
    4. Submit to RunComfy
    5. Poll status
    6. Download result
    7. Update camera
    """
    
def test_auto_generation():
    """Test auto-generation triggers properly"""
    
def test_texture_projection():
    """Test projecting result onto objects"""
```

#### 8.3: Manual Testing Checklist
- [ ] Fresh Blender install on Windows
- [ ] Fresh Blender install on Mac
- [ ] Fresh Blender install on Linux
- [ ] First-time setup experience
- [ ] API key validation
- [ ] Deployment selection
- [ ] Single generation
- [ ] Auto-generation toggle
- [ ] Multiple sequential generations
- [ ] Texture projection
- [ ] Error scenarios (invalid key, no deployment, network error)
- [ ] Cost estimation accuracy

---

### Phase 9: Documentation (Week 4-5)

#### 9.1: User Documentation

**Create: `docs/CLOUD_SETUP_GUIDE.md`**
```markdown
# Style Engine Cloud - Setup Guide

## Prerequisites
- Blender 4.0 or later
- RunComfy account (runcomfy.com)
- Active payment method on RunComfy

## Step 1: Install Addon
1. Download `styleengine_cloud.zip`
2. Open Blender
3. Edit → Preferences → Add-ons
4. Click "Install" and select the zip file
5. Enable "Style Engine Cloud"

## Step 2: Get RunComfy API Keys
1. Go to runcomfy.com/profile
2. Copy your "API Token"
3. Copy your "User ID"

## Step 3: Create Deployment
[Detailed steps with screenshots]

## Step 4: Configure Addon
[Screenshots and instructions]

## First Generation
[Step-by-step walkthrough]
```

**Create: `docs/COST_GUIDE.md`**
```markdown
# Understanding Costs

## Pricing
- AMPERE_48 (recommended): $2.50/hour
- Average generation: 20 seconds = $0.014
- First generation (cold start): 3-5 minutes = $0.10-$0.21

## Cost Optimization Tips
1. Keep deployment warm during active sessions
2. Disable auto-generation when experimenting
3. Use lower step counts for testing
4. Scale down resolution for previews

## Monthly Estimates
- Casual use (10 generations/day): ~$4/month
- Regular use (50 generations/day): ~$21/month
- Heavy use (200 generations/day): ~$84/month
```

**Create: `docs/TROUBLESHOOTING.md`**
```markdown
# Troubleshooting Guide

## Common Issues

### "Invalid API Key" Error
[Solutions]

### "Deployment Not Found" Error
[Solutions]

### "Generation Timeout" Error
[Solutions]

### Slow Generation Times
[Solutions]

### Image Quality Issues
[Solutions]
```

#### 9.2: Developer Documentation

**Create: `docs/API_REFERENCE.md`**
- Complete API documentation
- Code examples
- Extension guidelines

**Create: `docs/ARCHITECTURE.md`**
- System architecture diagram
- Data flow explanation
- Module interactions

---

### Phase 10: Distribution & Deployment (Week 5)

#### 10.1: Packaging
**Create distribution package:**

```bash
# Build script: scripts/build_cloud_addon.py
python build_cloud_addon.py
# Output: dist/styleengine_cloud_v1.0.0.zip
```

**Package contents:**
```
styleengine_cloud_v1.0.0.zip
├── __init__.py
├── blender_manifest.toml
├── prefs.py
├── runcomfy_client.py
├── runcomfy_deployment.py
├── runcomfy_polling.py
├── workspace_setup_cloud.py
├── UI/
│   └── ui_panel_cloud.py
├── README.md
├── LICENSE
└── docs/
    ├── SETUP_GUIDE.md
    ├── COST_GUIDE.md
    └── TROUBLESHOOTING.md
```

#### 10.2: Version Management
**Semantic versioning:**
- v1.0.0: Initial cloud release
- v1.1.0: Minor features
- v1.0.1: Bug fixes

**Update `blender_manifest.toml`:**
```toml
id = "styleengine_cloud"
version = "1.0.0"
name = "Style Engine Cloud"
tagline = "AI-powered real-time visualization with RunComfy"
maintainer = "Your Name <email>"
type = "add-on"
tags = ["Render", "Import-Export", "Material"]
blender_version_min = "4.0.0"
website = "https://github.com/yourusername/styleengine"
```

#### 10.3: Distribution Channels
1. **GitHub Releases**
   - Create release with changelog
   - Attach `.zip` file
   - Tag version

2. **Blender Market** (Optional)
   - Submit for review
   - Set pricing (free or paid)

3. **Direct Website** (Optional)
   - Host download page
   - Include documentation
   - Add video tutorials

---

## 📊 Project Timeline

### Week 1: Core Infrastructure
- [ ] Day 1-2: `runcomfy_client.py` - HTTP client
- [ ] Day 3-4: Image encoding/decoding
- [ ] Day 5: Unit tests for API client
- [ ] Day 6-7: `runcomfy_deployment.py` - Deployment management

### Week 2: Integration
- [ ] Day 8-9: `runcomfy_polling.py` - Async polling
- [ ] Day 10-11: `workspace_setup_cloud.py` - Cloud workflow
- [ ] Day 12-13: Preferences integration
- [ ] Day 14: Integration tests

### Week 3: UI & UX
- [ ] Day 15-16: `ui_panel_cloud.py` - Cloud UI
- [ ] Day 17-18: Status indicators and progress bars
- [ ] Day 19-20: Error handling and user feedback
- [ ] Day 21: Cost estimation display

### Week 4: Polish & Testing
- [ ] Day 22-23: Manual testing (Windows, Mac, Linux)
- [ ] Day 24-25: Bug fixes and refinements
- [ ] Day 26-27: Documentation writing
- [ ] Day 28: Final testing

### Week 5: Distribution
- [ ] Day 29-30: Package creation and testing
- [ ] Day 31: GitHub release
- [ ] Day 32: Video tutorial recording
- [ ] Day 33-35: Community feedback and hotfixes

**Total:** ~5 weeks for v1.0.0 release

---

## 🎯 Success Metrics

### Technical Metrics
- [ ] Zero external dependencies (uses only Blender built-ins)
- [ ] <2 minute setup time for new users
- [ ] <5 second API response time (submit inference)
- [ ] 95%+ successful generation rate
- [ ] Supports Windows, Mac, Linux without modification

### User Experience Metrics
- [ ] One-click installation
- [ ] Clear error messages for all failure modes
- [ ] Real-time progress feedback
- [ ] Accurate cost estimates
- [ ] Intuitive UI matching local version

### Distribution Metrics
- [ ] <10MB package size
- [ ] Clear documentation covering all features
- [ ] <5 support tickets per 100 users (quality goal)
- [ ] 90%+ user satisfaction rating

---

## 🚧 Known Limitations & Future Enhancements

### v1.0.0 Limitations
1. **Latency:** Cloud generation slower than local (15-30s vs 5s)
2. **Cost:** Pay-per-use model vs free local generation
3. **Internet Required:** No offline mode
4. **Single Deployment:** User manages one deployment at a time
5. **Fixed Workflow:** Uses predefined SDXL workflow only

### Future Enhancements (v1.1.0+)

#### v1.1.0 - Advanced Features
- [ ] Multiple deployment profiles
- [ ] Custom workflow upload
- [ ] Hardware tier selector in UI
- [ ] Batch generation queue
- [ ] Generation history viewer

#### v1.2.0 - Optimization
- [ ] Image compression for faster uploads
- [ ] Result caching to reduce redundant generations
- [ ] Parallel polling for multiple requests
- [ ] Smart keep-warm management

#### v1.3.0 - Collaboration
- [ ] Share generations with team
- [ ] Cloud project storage
- [ ] Version control for prompts
- [ ] Collaborative prompt library

#### v2.0.0 - Hybrid Mode
- [ ] Automatic fallback: cloud → local → cloud
- [ ] Smart routing based on load/cost
- [ ] Unified UI for both modes
- [ ] Seamless mode switching

---

## 🔐 Security Considerations

### API Key Management
- [ ] Store API keys securely in Blender preferences
- [ ] Never log API keys to console
- [ ] Validate key format before use
- [ ] Clear instructions for key rotation

### Data Privacy
- [ ] Render passes uploaded to RunComfy are temporary
- [ ] Results deleted after download (optional setting)
- [ ] No user data stored on our servers
- [ ] Comply with RunComfy's data retention policy

### Error Reporting
- [ ] Sanitize error logs (remove sensitive data)
- [ ] Optional telemetry (opt-in only)
- [ ] Clear privacy policy in documentation

---

## 📚 Required Documentation

### User-Facing
1. ✅ **SETUP_GUIDE.md** - Step-by-step installation
2. ✅ **COST_GUIDE.md** - Pricing and optimization
3. ✅ **TROUBLESHOOTING.md** - Common issues and solutions
4. ✅ **FAQ.md** - Frequently asked questions
5. ⚠️ **VIDEO_TUTORIAL.md** - Link to video walkthrough

### Developer-Facing
1. ✅ **API_REFERENCE.md** - Complete API documentation
2. ✅ **ARCHITECTURE.md** - System design overview
3. ✅ **CONTRIBUTING.md** - Guidelines for contributors
4. ✅ **CHANGELOG.md** - Version history

---

## 🧪 Quality Assurance Checklist

### Pre-Release Checklist
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual testing on Windows 10/11
- [ ] Manual testing on macOS (Intel & Apple Silicon)
- [ ] Manual testing on Linux (Ubuntu 22.04+)
- [ ] Documentation reviewed and proofread
- [ ] Code reviewed by peer
- [ ] Performance benchmarked
- [ ] Error handling tested for all API endpoints
- [ ] User flow tested end-to-end

### Release Checklist
- [ ] Version number updated in all files
- [ ] CHANGELOG.md updated
- [ ] Git tag created
- [ ] GitHub release published
- [ ] Download link tested
- [ ] Installation tested from release package
- [ ] Announcement posted (optional)

---

## 💡 Design Decisions & Rationale

### Why Pure Python?
**Decision:** Use only Blender's built-in Python modules  
**Rationale:**
- Zero installation friction
- Cross-platform compatibility guaranteed
- No dependency version conflicts
- Easier distribution and support

### Why User-Managed Deployments (v1)?
**Decision:** User creates deployment via RunComfy dashboard  
**Rationale:**
- User has full cost control
- Transparent pricing
- Simpler addon logic
- Easier to troubleshoot
- Users learn RunComfy platform

### Why Polling vs WebSockets?
**Decision:** Use HTTP polling every 5 seconds  
**Rationale:**
- Simpler implementation
- No persistent connection management
- Works with Blender's timer system
- Sufficient for 15-30s generation times
- More reliable across networks/proxies

### Why Base64 Image Upload?
**Decision:** Encode images as Base64 data URIs  
**Rationale:**
- No need for separate file hosting
- Self-contained API requests
- RunComfy API supports it natively
- Simpler than presigned URLs
- Acceptable for <1MB images

---

## 🎓 Learning Resources

### For Users
- [RunComfy Documentation](https://docs.runcomfy.com/)
- [Blender Python API](https://docs.blender.org/api/current/)
- [ComfyUI Workflows Guide](https://comfyui-guides.runcomfy.com/)

### For Developers
- [Blender Addon Development](https://docs.blender.org/manual/en/latest/advanced/scripting/addon_tutorial.html)
- [Python urllib Tutorial](https://docs.python.org/3/howto/urllib2.html)
- [REST API Best Practices](https://restfulapi.net/)

---

## 📞 Support Plan

### User Support Channels
1. **GitHub Issues** - Bug reports and feature requests
2. **GitHub Discussions** - General questions and community help
3. **Email** - Direct support for critical issues
4. **Discord** (Optional) - Community chat and quick help

### Support Response Targets
- **Critical bugs:** <24 hours
- **Feature requests:** Review within 1 week
- **Questions:** <48 hours
- **Documentation updates:** <72 hours

---

## ✅ Launch Criteria

### Must Have (Blocking)
- [x] Core API client functional
- [x] Deployment management working
- [x] Polling system stable
- [x] UI complete and intuitive
- [x] Error handling comprehensive
- [x] Tested on all platforms
- [x] Documentation complete

### Should Have (Important)
- [ ] Cost estimation accurate
- [ ] Progress indicators polished
- [ ] Video tutorial available
- [ ] FAQ comprehensive
- [ ] GitHub repo public

### Nice to Have (Optional)
- [ ] Blender Market listing
- [ ] Project website
- [ ] Social media presence
- [ ] Community Discord

---

## 🎉 Post-Launch Plan

### Week 1
- Monitor GitHub issues
- Respond to user feedback
- Fix critical bugs immediately
- Publish FAQ based on questions

### Month 1
- Collect usage analytics (if opt-in telemetry)
- Plan v1.1.0 features based on feedback
- Write technical blog post
- Create additional tutorials

### Month 3
- Release v1.1.0 with community-requested features
- Evaluate hybrid mode (local + cloud) feasibility
- Explore partnerships with RunComfy
- Consider premium features

---

## 📋 Appendix: Code Samples

### Sample: Minimal Working Generation
```python
# Minimal example of cloud generation
import bpy
from styleengine.runcomfy_client import RunComfyClient

# Initialize client
client = RunComfyClient(
    api_token="your_token_here",
    user_id="your_user_id_here"
)

# Submit inference
response = client.submit_inference(
    deployment_id="your_deployment_id",
    overrides={
        "25": {"inputs": {"value": "a beautiful sunset"}}
    }
)

# Poll status
import time
while True:
    status = client.check_status(
        deployment_id="your_deployment_id",
        request_id=response['request_id']
    )
    
    if status['status'] == 'completed':
        result = client.get_result(
            deployment_id="your_deployment_id",
            request_id=response['request_id']
        )
        print("Generation complete!", result)
        break
    
    time.sleep(5)
```

---

**End of Development Plan**

This plan provides a complete roadmap for building the RunComfy cloud version of Style Engine. Follow the phases sequentially, and adjust timelines based on your development velocity and available resources.

For questions or clarifications, refer to the detailed phase descriptions above.

