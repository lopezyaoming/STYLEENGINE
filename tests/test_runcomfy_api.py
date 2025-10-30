#!/usr/bin/env python3
"""
Standalone test script for RunComfy API validation.
Tests all API endpoints before integration into Blender addon.

Usage:
    # Interactive mode (will prompt for workflow choice):
    python tests/test_runcomfy_api.py
    
    # Or set workflow via environment variable:
    WORKFLOW_MODE=sdxl python tests/test_runcomfy_api.py
    WORKFLOW_MODE=ipadapter python tests/test_runcomfy_api.py
    
    # Test with batch mode (checks if models stay warm):
    RUNCOMFY_BATCH_TEST=1 python tests/test_runcomfy_api.py

Requirements:
    - Set RUNCOMFY_API_TOKEN environment variable
    - Set RUNCOMFY_USER_ID environment variable
    - Have a test image at tests/test_image.png (optional)
    - For IPAdapter mode: Have tests/IPtest.jpeg (reference image)

Environment Variables:
    RUNCOMFY_API_TOKEN  - Your RunComfy API token (required)
    RUNCOMFY_USER_ID    - Your RunComfy user ID (required)
    WORKFLOW_MODE       - 'sdxl' or 'ipadapter' (optional, will prompt if not set)
    RUNCOMFY_BATCH_TEST - '1' to enable batch testing (tests model warmth)
    RUNCOMFY_AUTO_TEST  - '1' to skip confirmation prompts
"""

import urllib.request
import urllib.error
import json
import base64
import time
import os
import sys
from pathlib import Path

# Configuration
API_BASE = "https://api.runcomfy.net"
TEST_PROMPT = "a beautiful sunset over mountains, photorealistic, 8k"
TEST_IMAGE_PATH = Path(__file__).parent / "test_image.png"
TEST_IPADAPTER_REFERENCE = Path(__file__).parent / "IPtest.jpeg"  # Reference image for IPAdapter mode

# Deployment ID (from RunComfy)
TEST_DEPLOYMENT_ID = "1c6fa9a6-f60a-4e89-863d-40b03ad2564e"  # NEW: Style Engine with easy imageSave

# Workflow selection (can be set via environment variable or interactive prompt)
# Options: 'sdxl' (default) or 'ipadapter'
WORKFLOW_MODE = None  # Will be set interactively or via env var

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def log_success(msg):
    print(f"{GREEN}[OK] {msg}{RESET}")


def log_error(msg):
    print(f"{RED}[FAIL] {msg}{RESET}")


def log_info(msg):
    print(f"{BLUE}[INFO] {msg}{RESET}")


def log_warning(msg):
    print(f"{YELLOW}[WARN] {msg}{RESET}")


class RunComfyTestClient:
    """Minimal HTTP client for testing RunComfy API"""
    
    def __init__(self, api_token, user_id):
        self.api_token = api_token
        self.user_id = user_id
        self.timeout = 30
    
    def _request(self, method, endpoint, data=None):
        """Make HTTP request with error handling"""
        url = f"{API_BASE}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'StyleEngine-Test/1.0'
        }
        
        # Prepare request
        if data:
            data = json.dumps(data).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data) if response_data else {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                raise Exception(f"HTTP {e.code}: {error_json}")
            except json.JSONDecodeError:
                raise Exception(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")
    
    def list_deployments(self):
        """GET /prod/v2/deployments"""
        return self._request('GET', '/prod/v2/deployments')
    
    def get_deployment(self, deployment_id, include_payload=False):
        """GET /prod/v2/deployments/{deployment_id}"""
        endpoint = f'/prod/v2/deployments/{deployment_id}'
        if include_payload:
            endpoint += '?includes=payload'
        return self._request('GET', endpoint)
    
    def submit_inference(self, deployment_id, overrides):
        """POST /prod/v1/deployments/{deployment_id}/inference"""
        return self._request('POST', f'/prod/v1/deployments/{deployment_id}/inference', 
                           data={'overrides': overrides})
    
    def check_status(self, deployment_id, request_id):
        """GET /prod/v1/deployments/{deployment_id}/requests/{request_id}/status"""
        return self._request('GET', f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/status')
    
    def get_result(self, deployment_id, request_id):
        """GET /prod/v1/deployments/{deployment_id}/requests/{request_id}/result"""
        return self._request('GET', f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/result')
    
    def cancel_request(self, deployment_id, request_id):
        """POST /prod/v1/deployments/{deployment_id}/requests/{request_id}/cancel"""
        return self._request('POST', f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/cancel')


def encode_image_to_base64(image_path):
    """Encode image to base64 data URI (supports PNG and JPEG)"""
    try:
        image_path = Path(image_path)
        
        # Determine MIME type from extension
        ext = image_path.suffix.lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        else:
            raise ValueError(f"Unsupported image format: {ext}")
        
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        return f"data:{mime_type};base64,{img_data}"
    except Exception as e:
        raise Exception(f"Failed to encode image: {e}")


def download_image_from_url(url, save_path, api_token=None):
    """Download image from URL (no auth needed for output URLs)"""
    try:
        # Create request with minimal headers
        # Note: Output URLs don't need/accept Authorization headers
        headers = {
            'User-Agent': 'StyleEngine-Test/1.0'
        }
        
        log_info(f"  Attempting download from: {url[:100]}...")
        log_info(f"  Note: No auth header (output URLs are publicly accessible)")
        
        req = urllib.request.Request(url, headers=headers)
        
        # Download
        with urllib.request.urlopen(req, timeout=30) as response:
            log_info(f"  Response status: {response.status}")
            with open(save_path, 'wb') as f:
                f.write(response.read())
        return True
    except urllib.error.HTTPError as e:
        log_error(f"Download failed: HTTP {e.code} - {e.reason}")
        log_error(f"  URL: {url}")
        try:
            error_body = e.read().decode('utf-8')
            log_error(f"  Response: {error_body[:200]}")
        except:
            pass
        return False
    except Exception as e:
        log_error(f"Download failed: {e}")
        return False


# TEST FUNCTIONS

def test_auth(client):
    """Test 1: Authentication"""
    log_info("Test 1: Testing authentication...")
    try:
        deployments = client.list_deployments()
        log_success(f"Authentication successful! Found {len(deployments)} deployments")
        return True
    except Exception as e:
        log_error(f"Authentication failed: {e}")
        return False


def test_list_deployments(client):
    """Test 2: List deployments"""
    log_info("Test 2: Listing deployments...")
    try:
        deployments = client.list_deployments()
        log_success(f"Retrieved {len(deployments)} deployments")
        
        for dep in deployments[:3]:  # Show first 3
            log_info(f"  - {dep.get('name', 'Unnamed')} (ID: {dep.get('id', 'N/A')[:8]}...)")
        
        return deployments
    except Exception as e:
        log_error(f"Failed to list deployments: {e}")
        return None


def test_get_deployment(client, deployment_id):
    """Test 3: Get deployment details"""
    log_info(f"Test 3: Getting deployment details for {deployment_id[:8]}...")
    try:
        deployment = client.get_deployment(deployment_id)
        log_success(f"Retrieved deployment: {deployment.get('name', 'Unnamed')}")
        log_info(f"  Status: {'Enabled' if deployment.get('is_enabled') else 'Disabled'}")
        log_info(f"  Workflow ID: {deployment.get('workflow_id', 'N/A')[:8]}...")
        log_info(f"  Hardware: {deployment.get('hardware', [])}")
        log_info(f"  Min/Max Instances: {deployment.get('min_instances', 0)}/{deployment.get('max_instances', 1)}")
        
        # Check if payload is included
        if 'payload' in deployment:
            payload = deployment['payload']
            log_info(f"  Payload keys: {list(payload.keys())}")
            if 'object_info_url' in payload:
                log_info(f"  Object Info URL: {payload['object_info_url'][:60] if payload['object_info_url'] else 'Not set'}...")
        else:
            log_warning("  Payload not included in response (use ?includes=payload)")
        
        return deployment
    except Exception as e:
        log_error(f"Failed to get deployment: {e}")
        return None


def test_submit_inference(client, deployment_id):
    """Test 4: Submit inference (supports SDXL and IPAdapter modes)"""
    log_info(f"Test 4: Submitting inference to {deployment_id[:8]}...")
    log_info(f"  Workflow Mode: {WORKFLOW_MODE.upper()}")
    
    try:
        # Generate random seed to avoid ComfyUI caching
        import random
        seed = random.randint(1, 2**32 - 1)
        
        log_info(f"  Using random seed: {seed} to avoid caching")
        
        # Base overrides (common to both workflows)
        overrides = {
            "25": {"inputs": {"value": TEST_PROMPT}},      # Prompt
            "40": {"inputs": {"value": 0.75}},             # Silhouette strength
            "41": {"inputs": {"value": 0.5}},              # Depth strength
            "42": {"inputs": {"value": 15}},               # Steps
            "3": {"inputs": {"seed": seed}}                # Random seed to force new generation
        }
        
        # Add IPAdapter-specific overrides
        if WORKFLOW_MODE == 'ipadapter':
            if not TEST_IPADAPTER_REFERENCE.exists():
                log_error(f"  IPAdapter reference image not found: {TEST_IPADAPTER_REFERENCE}")
                log_error(f"  Falling back to SDXL mode")
            else:
                log_info(f"  Encoding IPAdapter reference: {TEST_IPADAPTER_REFERENCE.name}")
                try:
                    ref_image_b64 = encode_image_to_base64(str(TEST_IPADAPTER_REFERENCE))
                    ref_size_kb = len(ref_image_b64) / 1024
                    log_info(f"  Reference image encoded: {ref_size_kb:.2f} KB")
                    
                    # Add IPAdapter-specific nodes
                    overrides.update({
                        "43": {"inputs": {"image": ref_image_b64}},           # IPAdapter reference image
                        "52": {"inputs": {"value": 0.8}}                      # IPAdapter strength
                    })
                    # Note: Node 49 (IPAdapterEmbeds) has upstream connections and should NOT be overridden
                    
                    log_success(f"  IPAdapter mode enabled with reference image")
                except Exception as e:
                    log_error(f"  Failed to encode reference image: {e}")
                    log_error(f"  Falling back to SDXL mode")
        
        # Note: Node 15 (combined image) is optional for testing without actual image
        
        response = client.submit_inference(deployment_id, overrides)
        request_id = response.get('request_id')
        
        log_success(f"Inference submitted! Request ID: {request_id[:8]}...")
        return request_id
    except Exception as e:
        log_error(f"Failed to submit inference: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_instance_history(deployment_id, instance_id, api_token, show_errors=True):
    """Get detailed execution history from ComfyUI instance"""
    try:
        proxy_url = f"{API_BASE}/prod/v2/deployments/{deployment_id}/instances/{instance_id}/proxy/history"
        
        headers = {
            'Authorization': f'Bearer {api_token}',
            'User-Agent': 'StyleEngine-Test/1.0'
        }
        
        req = urllib.request.Request(proxy_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read().decode('utf-8')
            
            # Check if response is empty
            if not raw_data or raw_data.strip() == '':
                if show_errors:
                    log_warning("  History endpoint returned empty response")
                return None
            
            # Try to parse JSON
            try:
                history = json.loads(raw_data)
                log_info(f"  ✓ Got history with {len(history)} items")
                return history
            except json.JSONDecodeError as je:
                if show_errors:
                    log_warning(f"  Invalid JSON from history endpoint (size: {len(raw_data)} bytes)")
                    log_warning(f"  First 100 chars: {raw_data[:100]}")
                return None
                
    except urllib.error.HTTPError as e:
        if show_errors:
            log_warning(f"  HTTP {e.code} when fetching history: {e.reason}")
        return None
    except Exception as e:
        if show_errors:
            log_warning(f"  Failed to fetch history: {type(e).__name__}: {e}")
        return None


def display_execution_breakdown(history):
    """Display detailed per-node execution timing"""
    if not history:
        log_warning("  No execution history available")
        return
    
    # DEBUG: Show raw history structure
    log_info("  Raw history keys: " + str(list(history.keys())[:3]))
    if history:
        first_key = list(history.keys())[0] if history else None
        if first_key:
            log_info(f"  Sample data structure: {str(history[first_key].keys())}")
    
    # Node type mapping for the SDXL workflow
    node_types = {
        '3': 'KSampler',
        '4': 'CheckpointLoader (SDXL)',
        '5': 'EmptyLatentImage',
        '6': 'CLIPTextEncode (Positive)',
        '7': 'CLIPTextEncode (Negative)',
        '8': 'VAEDecode',
        '13': 'ControlNetLoader (Depth)',
        '14': 'ControlNetApply (Silhouette)',
        '15': 'LoadImage (Combined)',
        '25': 'String (Prompt)',
        '34': 'LoraLoader',
        '35': 'Canny Edge Detection',
        '37': 'ControlNetApply (Depth)',
        '38': 'ControlNetLoader (Canny)',
        '39': 'DepthAnything Preprocessor',
        '40': 'Float (Silhouette Strength)',
        '41': 'Float (Depth Strength)',
        '42': 'Int (Steps)',
        '43': 'LoadImage (Depth)',
        '50': 'PreviewImage (Silhouette)',
        '51': 'PreviewImage (Depth)',
        '53': 'SaveImage (Output)'
    }
    
    log_info("=" * 60)
    log_info("  📊 EXECUTION BREAKDOWN")
    log_info("=" * 60)
    
    total_time = 0
    node_times = []
    
    # Parse all prompts in history
    for prompt_id, prompt_data in history.items():
        log_info(f"  Processing prompt: {prompt_id[:8]}...")
        
        if 'outputs' in prompt_data:
            outputs = prompt_data['outputs']
            log_info(f"    Found {len(outputs)} output nodes")
            
            # Collect timing for each node
            for node_id, node_output in outputs.items():
                # Try to get execution time (may not always be present)
                exec_time = node_output.get('execution_time', 0)
                
                # DEBUG: Show what's in node_output
                if len(node_times) < 3:  # Only for first few nodes
                    log_info(f"    Node {node_id} keys: {list(node_output.keys())}")
                
                if exec_time > 0:
                    node_name = node_types.get(node_id, 'Unknown Node')
                    node_times.append((node_id, node_name, exec_time))
                    total_time += exec_time
        else:
            log_warning(f"    No 'outputs' in prompt data. Keys: {list(prompt_data.keys())}")
    
    # Sort by time (longest first)
    node_times.sort(key=lambda x: x[2], reverse=True)
    
    if node_times:
        log_info("  Node Execution Times (slowest first):")
        log_info("")
        for node_id, node_name, exec_time in node_times:
            percentage = (exec_time / total_time * 100) if total_time > 0 else 0
            
            # Add emoji indicators for key operations
            emoji = ""
            if "Checkpoint" in node_name or "Lora" in node_name or "ControlNet" in node_name:
                emoji = "🔄"  # Model loading
            elif "KSampler" in node_name:
                emoji = "🎨"  # Generation
            elif "Preprocessor" in node_name or "Canny" in node_name or "Depth" in node_name:
                emoji = "⚙️"  # Preprocessing
            elif "Save" in node_name:
                emoji = "💾"  # Saving
            elif "VAE" in node_name:
                emoji = "🖼️"  # Decoding
            
            log_info(f"    {emoji} Node {node_id:>3} ({node_name:.<35}): {exec_time:>6.2f}s  ({percentage:>5.1f}%)")
        
        log_info("")
        log_info("-" * 60)
        log_success(f"  Total Execution Time: {total_time:.2f}s")
        log_info("")
        
        # Categorize timing
        model_loading_time = sum(t for _, name, t in node_times 
                                if any(x in name for x in ['Checkpoint', 'Lora', 'ControlNet']))
        preprocessing_time = sum(t for _, name, t in node_times 
                               if any(x in name for x in ['Preprocessor', 'Canny', 'Depth']))
        inference_time = sum(t for _, name, t in node_times 
                           if 'KSampler' in name or 'VAE' in name)
        
        if model_loading_time > 0:
            log_info(f"  🔄 Model Loading: {model_loading_time:.2f}s ({model_loading_time/total_time*100:.1f}%)")
        if preprocessing_time > 0:
            log_info(f"  ⚙️  Preprocessing: {preprocessing_time:.2f}s ({preprocessing_time/total_time*100:.1f}%)")
        if inference_time > 0:
            log_info(f"  🎨 Generation: {inference_time:.2f}s ({inference_time/total_time*100:.1f}%)")
    else:
        log_warning("  No per-node timing data available")
    
    log_info("=" * 60)


def test_poll_status(client, deployment_id, request_id):
    """Test 5: Poll status with precise timing breakdown"""
    log_info(f"Test 5: Polling status for request {request_id[:8]}...")
    
    # Timing checkpoints
    timings = {
        'submit_complete': time.time(),
        'queue_start': None,
        'in_progress_start': None,
        'completion': None
    }
    
    max_wait = 600  # 10 minutes
    start_time = time.time()
    poll_interval = 2  # Check every 2 seconds for precise timing
    instance_id = None
    last_status = None
    
    try:
        while time.time() - start_time < max_wait:
            status_data = client.check_status(deployment_id, request_id)
            status = status_data.get('status', 'unknown')
            elapsed = time.time() - start_time
            
            # Capture instance_id when available
            if not instance_id and 'instance_id' in status_data:
                instance_id = status_data['instance_id']
                log_success(f"  Instance ID: {instance_id[:16]}... (+{elapsed:.1f}s from submit)")
            
            # Record precise timing for each status transition
            if status != last_status:
                now = time.time()
                
                if status == 'in_queue' and timings['queue_start'] is None:
                    timings['queue_start'] = now
                    queue_pos = status_data.get('queue_position', 'unknown')
                    log_info(f"  [+{elapsed:>6.1f}s] 📋 QUEUE START (position: {queue_pos})")
                    
                elif status == 'in_progress' and timings['in_progress_start'] is None:
                    timings['in_progress_start'] = now
                    queue_time = now - timings['queue_start'] if timings['queue_start'] else 0
                    log_info(f"  [+{elapsed:>6.1f}s] 🔄 EXECUTION START (queued for {queue_time:.1f}s)")
                    
                elif status == 'completed':
                    timings['completion'] = now
                    
                last_status = status
            else:
                # Periodic updates every 15 seconds
                if int(elapsed) % 15 == 0 and int(elapsed) > 0:
                    log_info(f"  [+{elapsed:>6.1f}s] ⏳ Still {status}...")
            
            # Check for completion
            if status == 'completed':
                total = timings['completion'] - timings['submit_complete']
                queue_time = (timings['in_progress_start'] - timings['queue_start']) if (timings['queue_start'] and timings['in_progress_start']) else 0
                exec_time = (timings['completion'] - timings['in_progress_start']) if timings['in_progress_start'] else total
                overhead_time = total - queue_time - exec_time
                
                log_success(f"Request completed in {total:.2f}s!")
                
                # Display timing breakdown
                log_info("")
                log_info("=" * 60)
                log_info("  ⏱️  TIMING BREAKDOWN")
                log_info("=" * 60)
                
                if queue_time > 0:
                    log_info(f"  📋 Queue Time:       {queue_time:>7.2f}s  ({queue_time/total*100:>5.1f}%)")
                if exec_time > 0:
                    log_info(f"  🔄 Execution Time:   {exec_time:>7.2f}s  ({exec_time/total*100:>5.1f}%)")
                if overhead_time > 0:
                    log_info(f"  ⚙️  Overhead/Setup:   {overhead_time:>7.2f}s  ({overhead_time/total*100:>5.1f}%)")
                
                log_info("  " + "-" * 56)
                log_info(f"  ⏰ Total Time:       {total:>7.2f}s")
                log_info("=" * 60)
                
                # Diagnosis
                if queue_time > 10:
                    log_warning(f"  ⚠️  High queue time detected ({queue_time:.1f}s)")
                    log_info("  This may indicate:")
                    log_info("    - Instance warm-up despite min_instances=1")
                    log_info("    - Internal RunComfy queueing/rate limiting")
                    log_info("    - Model loading to instance")
                
                if exec_time > 30:
                    log_warning(f"  ⚠️  Long execution time ({exec_time:.1f}s)")
                    log_info("  This may indicate:")
                    log_info("    - Models being loaded during execution")
                    log_info("    - Heavy preprocessing (DepthAnything, ControlNet)")
                
                log_info("")
                
                # Try to get detailed execution breakdown
                if instance_id:
                    log_info("  Attempting to fetch ComfyUI execution details...")
                    
                    history = None
                    for attempt in range(3):
                        history = get_instance_history(deployment_id, instance_id, client.api_token, show_errors=(attempt == 2))
                        if history:
                            break
                        if attempt < 2:
                            time.sleep(2)
                    
                    if history:
                        display_execution_breakdown(history)
                    else:
                        log_warning("  ⚠️  Could not retrieve node-level timing")
                        log_info("  Note: ComfyUI history may not be available via instance proxy")
                
                return True
                
            elif status == 'failed':
                log_error("Request failed")
                if 'error' in status_data:
                    log_error(f"  Error details: {status_data['error']}")
                return False
            
            time.sleep(poll_interval)
        
        log_warning(f"Timeout after {max_wait}s")
        return False
        
    except Exception as e:
        log_error(f"Failed to poll status: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_result(client, deployment_id, request_id, api_token):
    """Test 6: Get result and download image (with detailed debugging)"""
    log_info(f"Test 6: Getting result for request {request_id[:8]}...")
    log_info(f"  Workflow Mode: {WORKFLOW_MODE.upper()}")
    
    try:
        result = client.get_result(deployment_id, request_id)
        
        # DEBUG: Print the entire result structure
        log_info("=" * 80)
        log_info("  🔍 FULL RESULT STRUCTURE")
        log_info("=" * 80)
        print(json.dumps(result, indent=2))
        log_info("=" * 80)
        
        # Check for instance_id
        instance_id = result.get('instance_id')
        if instance_id:
            log_info(f"✓ Found instance_id: {instance_id[:16]}...")
        else:
            log_warning("✗ No instance_id in result")
        
        # Extract image URL
        outputs = result.get('outputs', {})
        log_info(f"\n📊 Outputs Analysis:")
        log_info(f"  Total output nodes: {len(outputs)}")
        
        # Debug: Show all output node IDs and their structure
        for node_id, node_output in outputs.items():
            log_info(f"\n  Node {node_id}:")
            log_info(f"    Keys: {list(node_output.keys())}")
            if 'images' in node_output:
                images = node_output['images']
                log_info(f"    Has 'images': YES ({len(images)} image(s))")
                if images:
                    first_img = images[0]
                    if isinstance(first_img, dict):
                        log_info(f"    First image keys: {list(first_img.keys())}")
                        if 'url' in first_img:
                            log_success(f"    First image URL: {first_img['url'][:60]}...")
                        elif 'filename' in first_img:
                            log_warning(f"    First image filename: {first_img.get('filename')}")
                    else:
                        log_info(f"    First image type: {type(first_img)}")
            else:
                log_warning(f"    Has 'images': NO")
        
        log_info("")
        image_url = None
        node_output = None
        
        # Workflow-specific output node detection
        if WORKFLOW_MODE == 'ipadapter':
            # IPAdapter workflow outputs to Node 9 (SaveImage)
            if '9' in outputs and 'images' in outputs['9']:
                node_output = outputs['9']
                log_success("✓ Found output in Node 9 (IPAdapter SaveImage)")
            else:
                log_warning("✗ Node 9 not found in IPAdapter mode, checking all nodes...")
        else:
            # SDXL workflow outputs to Node 53 (easy imageSave)
            if '53' in outputs and 'images' in outputs['53']:
                node_output = outputs['53']
                log_success("✓ Found output in Node 53 (SDXL easy imageSave)")
            else:
                log_warning("✗ Node 53 not found in SDXL mode, checking all nodes...")
        
        # Fallback: check any node with images
        # Priority: 'output' type images > 'temp' type images (last one wins)
        if not node_output:
            log_info("Searching all nodes for images...")
            
            # First pass: Look for 'output' type images (final SaveImage nodes)
            for node_id, node_data in outputs.items():
                if 'images' in node_data and node_data['images']:
                    img_type = node_data['images'][0].get('type', '')
                    if img_type == 'output':
                        node_output = node_data
                        log_success(f"✓ Found 'output' type image in Node {node_id}")
                        break
            
            # Second pass: Accept any image if no 'output' found (last one wins)
            if not node_output:
                for node_id, node_data in outputs.items():
                    if 'images' in node_data and node_data['images']:
                        node_output = node_data
                        img_type = node_data['images'][0].get('type', 'unknown')
                        log_warning(f"Using '{img_type}' image from Node {node_id}")
                        # Don't break - keep iterating to get the LAST one
        
        if node_output and 'images' in node_output and node_output['images']:
            first_image = node_output['images'][0]
            log_info(f"  Image structure: {first_image}")
            
            # Case 1: Direct URL string
            if isinstance(first_image, str):
                image_url = first_image
                log_info("  -> Using direct string as URL")
            
            # Case 2: Dict with 'url' key (PREFERRED - pre-signed URL)
            elif isinstance(first_image, dict) and 'url' in first_image:
                image_url = first_image['url']
                log_success(f"  -> Found 'url' key in dict! URL: {image_url[:60]}...")
            
            # Case 3: Dict with filename - TRY to construct download URL
            elif isinstance(first_image, dict) and 'filename' in first_image:
                filename = first_image['filename']
                subfolder = first_image.get('subfolder', '')
                
                log_warning("  -> No 'url' field found, will try constructing URL from filename")
                log_warning("     This may fail if deployment doesn't generate pre-signed URLs")
                
                # Construct RunComfy download URL
                # Format: /prod/v1/deployments/{deployment_id}/requests/{request_id}/outputs/{filename}
                if subfolder:
                    filename_path = f"{subfolder}/{filename}"
                else:
                    filename_path = filename
                
                image_url = f"{API_BASE}/prod/v1/deployments/{deployment_id}/requests/{request_id}/outputs/{filename_path}"
                log_info(f"  -> Constructed URL: {image_url[:80]}...")
        
        if image_url:
            log_success(f"Found image URL: {image_url[:80]}...")
            
            # Download test
            test_download_path = Path(__file__).parent / "test_download.png"
            if download_image_from_url(image_url, str(test_download_path), api_token):
                log_success(f"Downloaded to: {test_download_path}")
                
                # Check file size
                size_mb = test_download_path.stat().st_size / (1024 * 1024)
                log_info(f"  File size: {size_mb:.2f} MB")
                return True
            else:
                # If direct download failed and we have instance_id, try instance proxy
                if instance_id and first_image and isinstance(first_image, dict) and 'filename' in first_image:
                    log_warning("Direct download failed, trying instance proxy endpoint...")
                    
                    filename = first_image['filename']
                    subfolder = first_image.get('subfolder', '')
                    
                    # Build instance proxy URL for ComfyUI's /view endpoint
                    # Format: /prod/v2/deployments/{deployment_id}/instances/{instance_id}/proxy/view?filename={filename}&type=output
                    proxy_url = f"{API_BASE}/prod/v2/deployments/{deployment_id}/instances/{instance_id}/proxy/view"
                    proxy_url += f"?filename={filename}&type=output"
                    if subfolder:
                        proxy_url += f"&subfolder={subfolder}"
                    
                    log_info(f"  Trying instance proxy: {proxy_url[:100]}...")
                    
                    # Try downloading through proxy (this needs Bearer auth)
                    try:
                        headers = {
                            'Authorization': f'Bearer {api_token}',
                            'User-Agent': 'StyleEngine-Test/1.0'
                        }
                        req = urllib.request.Request(proxy_url, headers=headers)
                        
                        with urllib.request.urlopen(req, timeout=30) as response:
                            with open(test_download_path, 'wb') as f:
                                f.write(response.read())
                        
                        log_success(f"Downloaded via instance proxy to: {test_download_path}")
                        size_mb = test_download_path.stat().st_size / (1024 * 1024)
                        log_info(f"  File size: {size_mb:.2f} MB")
                        return True
                    except Exception as e:
                        log_error(f"Instance proxy also failed: {e}")
                        return False
                else:
                    return False
        else:
            log_error("No image found in result")
            log_error(f"Available outputs: {list(outputs.keys())}")
            if outputs:
                log_error(f"Sample output structure: {list(outputs.values())[0]}")
            return False
            
    except Exception as e:
        log_error(f"Failed to get result: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_encoding():
    """Test 7: Image encoding"""
    log_info("Test 7: Testing image encoding...")
    
    if not TEST_IMAGE_PATH.exists():
        log_warning(f"Test image not found at {TEST_IMAGE_PATH}, skipping encoding test")
        return None
    
    try:
        encoded = encode_image_to_base64(str(TEST_IMAGE_PATH))
        
        # Validate format
        if not encoded.startswith('data:image/png;base64,'):
            log_error("Invalid base64 format")
            return False
        
        # Check size
        size_kb = len(encoded) / 1024
        log_success(f"Encoded successfully! Size: {size_kb:.2f} KB")
        
        if size_kb > 1024:
            log_warning(f"Encoded size is large ({size_kb:.2f} KB). Consider compression.")
        
        return True
        
    except Exception as e:
        log_error(f"Failed to encode image: {e}")
        return False


def test_error_handling(client):
    """Test 8: Error handling"""
    log_info("Test 8: Testing error handling...")
    
    # Test invalid deployment ID
    try:
        client.get_deployment("invalid-deployment-id")
        log_error("Should have raised error for invalid deployment")
        return False
    except Exception as e:
        log_success(f"Correctly handled invalid deployment: {str(e)[:50]}...")
        return True


def test_batch_inference(client, deployment_id, api_token, batch_size=2):
    """Test batch inference to check if models stay warm"""
    log_info(f"\n{'='*60}")
    log_info(f"  🚀 BATCH INFERENCE TEST ({batch_size} requests)")
    log_info(f"  Workflow Mode: {WORKFLOW_MODE.upper()}")
    log_info(f"{'='*60}\n")
    
    request_data = []
    
    # Submit all requests
    log_info(f"Submitting {batch_size} requests...")
    for i in range(batch_size):
        import random
        seed = random.randint(1, 2**32 - 1)
        
        log_info(f"\n[Request {i+1}/{batch_size}] Submitting with seed: {seed}")
        
        # Base overrides
        overrides = {
            "25": {"inputs": {"value": TEST_PROMPT}},
            "40": {"inputs": {"value": 0.75}},
            "41": {"inputs": {"value": 0.5}},
            "42": {"inputs": {"value": 15}},
            "3": {"inputs": {"seed": seed}}
        }
        
        # Add IPAdapter overrides if needed
        if WORKFLOW_MODE == 'ipadapter' and TEST_IPADAPTER_REFERENCE.exists():
            try:
                ref_image_b64 = encode_image_to_base64(str(TEST_IPADAPTER_REFERENCE))
                overrides.update({
                    "43": {"inputs": {"image": ref_image_b64}},
                    "52": {"inputs": {"value": 0.8}}
                })
            except Exception as e:
                log_error(f"  Failed to encode IPAdapter reference: {e}")
        
        # Submit directly with custom seed
        try:
            response = client.submit_inference(deployment_id, overrides)
            request_id = response.get('request_id')
            if request_id:
                log_success(f"  Request ID: {request_id[:8]}...")
        except Exception as e:
            log_error(f"  Failed: {e}")
            request_id = None
        if request_id:
            request_data.append({
                'request_id': request_id,
                'seed': seed,
                'submit_time': time.time(),
                'index': i + 1
            })
        else:
            log_error(f"Failed to submit request {i+1}")
            return False
        
        # Small delay between submissions
        if i < batch_size - 1:
            time.sleep(1)
    
    log_info(f"\n{'='*60}")
    log_info(f"All {batch_size} requests submitted! Now polling...")
    log_info(f"{'='*60}\n")
    
    # Poll all requests
    timings = []
    for req in request_data:
        log_info(f"\n[Request {req['index']}/{batch_size}] Polling {req['request_id'][:8]}...")
        log_info(f"  Seed: {req['seed']}")
        
        success = test_poll_status(client, deployment_id, req['request_id'])
        
        if success:
            # Get result to confirm unique output
            test_get_result(client, deployment_id, req['request_id'], api_token)
        
        timings.append({
            'index': req['index'],
            'success': success,
            'seed': req['seed']
        })
    
    # Summary
    log_info(f"\n{'='*60}")
    log_info(f"  📊 BATCH TEST SUMMARY")
    log_info(f"{'='*60}\n")
    
    success_count = sum(1 for t in timings if t['success'])
    log_info(f"Successful: {success_count}/{batch_size}")
    
    if success_count == batch_size:
        log_success("✅ All batch requests completed!")
        log_info("\nCompare the execution times above:")
        log_info("  - If Request 1 is ~52s and Request 2 is ~5s → Models staying warm! ✓")
        log_info("  - If both are ~52s → Models unloading between requests ✗")
        return True
    else:
        log_error(f"Some batch requests failed ({success_count}/{batch_size})")
        return False


def run_all_tests():
    """Run all tests"""
    global WORKFLOW_MODE
    
    print("\n" + "="*60)
    print("  RunComfy API Test Suite")
    print("="*60 + "\n")
    
    # Check for batch mode
    batch_mode = os.environ.get('RUNCOMFY_BATCH_TEST', '').lower() in ['1', 'true', 'yes']
    
    # Get credentials
    api_token = os.environ.get('RUNCOMFY_API_TOKEN')
    user_id = os.environ.get('RUNCOMFY_USER_ID')
    
    if not api_token or not user_id:
        log_error("Missing credentials!")
        log_info("Set RUNCOMFY_API_TOKEN and RUNCOMFY_USER_ID environment variables")
        return False
    
    log_success("Credentials found")
    log_info(f"User ID: {user_id}")
    log_info(f"API Token: {'*' * len(api_token)}")
    print()
    
    # Workflow selection (interactive or from env var)
    env_workflow = os.environ.get('WORKFLOW_MODE', '').lower()
    
    if env_workflow in ['sdxl', 'ipadapter']:
        WORKFLOW_MODE = env_workflow
        log_info(f"Using workflow from environment: {WORKFLOW_MODE.upper()}")
    else:
        # Interactive selection
        print("="*60)
        print("  🎨 Select Workflow Mode:")
        print("="*60)
        print(f"{BLUE}[1]{RESET} SDXL (Standard ControlNet workflow)")
        print(f"{BLUE}[2]{RESET} IPAdapter (Image-to-Image with reference)")
        print()
        
        try:
            choice = input(f"Enter your choice (1 or 2) [{BLUE}1{RESET}]: ").strip()
        except EOFError:
            choice = '1'
        
        if choice == '2':
            WORKFLOW_MODE = 'ipadapter'
        else:
            WORKFLOW_MODE = 'sdxl'
    
    # Display workflow mode
    print()
    log_success(f"Workflow Mode: {WORKFLOW_MODE.upper()}")
    
    if WORKFLOW_MODE == 'ipadapter':
        if TEST_IPADAPTER_REFERENCE.exists():
            log_success(f"  IPAdapter reference: {TEST_IPADAPTER_REFERENCE.name} ✓")
        else:
            log_error(f"  IPAdapter reference NOT FOUND: {TEST_IPADAPTER_REFERENCE}")
            log_error(f"  Please ensure IPtest.jpeg exists in tests/ folder")
            return False
    
    if batch_mode:
        log_info("🚀 BATCH MODE ENABLED")
    
    print()
    
    client = RunComfyTestClient(api_token, user_id)
    
    results = {}
    
    # Test 1: Auth
    results['auth'] = test_auth(client)
    if not results['auth']:
        log_error("Authentication failed, stopping tests")
        return False
    print()
    
    # Test 2: List deployments
    deployments = test_list_deployments(client)
    results['list_deployments'] = deployments is not None
    print()
    
    # Use predefined deployment ID for tests
    deployment_id = TEST_DEPLOYMENT_ID
    log_info(f"Using deployment: {deployment_id[:8]}... for remaining tests\n")
    
    # Test 3: Get deployment
    results['get_deployment'] = test_get_deployment(client, deployment_id) is not None
    print()
    
    # Test 3b: Get deployment with payload
    log_info(f"Test 3b: Getting deployment with payload...")
    try:
        deployment_full = client.get_deployment(deployment_id, include_payload=True)
        log_success("Retrieved deployment with payload")
        
        payload = deployment_full.get('payload', {})
        log_info(f"  Workflow API JSON nodes: {len(payload.get('workflow_api_json', {}).keys())} nodes")
        log_info(f"  Has object_info_url: {'Yes' if payload.get('object_info_url') else 'No'}")
    except Exception as e:
        log_warning(f"Could not get payload: {e}")
    print()
    
    # Test 4-6: Inference tests
    if batch_mode:
        # BATCH MODE: Submit multiple requests to test model warmth
        log_warning("Batch mode: Will submit 2 inference requests (may incur costs)")
        
        # Auto-continue if RUNCOMFY_AUTO_TEST is set
        auto_test = os.environ.get('RUNCOMFY_AUTO_TEST', '').lower() in ['1', 'true', 'yes']
        
        if not auto_test:
            try:
                response = input("Continue? (y/N): ")
            except EOFError:
                response = 'y'
        else:
            response = 'y'
            log_info("Auto-continuing (RUNCOMFY_AUTO_TEST is set)")
        
        if response.lower() != 'y':
            log_info("Skipping batch inference test")
            results['batch_inference'] = None
        else:
            results['batch_inference'] = test_batch_inference(client, deployment_id, api_token, batch_size=2)
            print()
    else:
        # NORMAL MODE: Single inference test
        log_warning("Test 4-6 will submit actual inference (may incur costs)")
        log_info("TIP: Set RUNCOMFY_BATCH_TEST=1 to test if models stay warm between requests")
        print()
        
        # Auto-continue if RUNCOMFY_AUTO_TEST is set (for CI/non-interactive)
        auto_test = os.environ.get('RUNCOMFY_AUTO_TEST', '').lower() in ['1', 'true', 'yes']
        
        if not auto_test:
            try:
                response = input("Continue? (y/N): ")
            except EOFError:
                response = 'y'  # Auto-continue if input not available
        else:
            response = 'y'
            log_info("Auto-continuing (RUNCOMFY_AUTO_TEST is set)")
        
        if response.lower() != 'y':
            log_info("Skipping inference tests")
            results['submit_inference'] = None
            results['poll_status'] = None
            results['get_result'] = None
        else:
            request_id = test_submit_inference(client, deployment_id)
            results['submit_inference'] = request_id is not None
            print()
            
            if request_id:
                # Test 5: Poll status
                results['poll_status'] = test_poll_status(client, deployment_id, request_id)
                print()
                
                # Test 6: Get result
                if results['poll_status']:
                    results['get_result'] = test_get_result(client, deployment_id, request_id, api_token)
                    print()
    
    # Test 7: Image encoding
    results['image_encoding'] = test_image_encoding()
    print()
    
    # Test 8: Error handling
    results['error_handling'] = test_error_handling(client)
    print()
    
    # Summary
    print("="*60)
    print("  Test Summary")
    print("="*60)
    
    for test_name, result in results.items():
        if result is True:
            log_success(f"{test_name}: PASS")
        elif result is False:
            log_error(f"{test_name}: FAIL")
        else:
            log_warning(f"{test_name}: SKIPPED")
    
    print()
    
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    
    if passed == total:
        log_success(f"All tests passed! ({passed}/{total})")
        return True
    else:
        log_warning(f"Some tests failed ({passed}/{total})")
        return False


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

