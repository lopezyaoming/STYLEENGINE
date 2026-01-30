# ================================================================
#    RunComfy Server API Client
#    Direct communication with ComfyUI Backend API
# ================================================================

import urllib.request
import urllib.error
import json
import base64
import uuid
import time
from pathlib import Path


# ================================================================
# EXCEPTIONS
# ================================================================

class ServerAPIError(Exception):
    """Base exception for Server API errors"""
    pass


class ServerConnectionError(ServerAPIError):
    """Failed to connect to server"""
    pass


class ServerExecutionError(ServerAPIError):
    """Workflow execution failed on server"""
    pass


# ================================================================
# SERVER API CLIENT
# ================================================================

class ComfyUIServerClient:
    """
    Direct client for ComfyUI Backend API.
    
    Communicates with a running ComfyUI server instance (e.g., on RunComfy)
    using the standard ComfyUI Backend API endpoints:
    - POST /prompt - Queue workflow execution
    - GET /history/{prompt_id} - Check execution status and get results
    - POST /upload/image - Upload images to server
    - GET /view - Download output images
    """
    
    def __init__(self, server_url, timeout=30):
        """
        Initialize ComfyUI Server client.
        
        Args:
            server_url: Base URL of ComfyUI backend (e.g., https://xxx-comfyui.runcomfy.com)
            timeout: Request timeout in seconds (default: 30)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
    
    def _request(self, method, endpoint, data=None, timeout=None, headers=None):
        """
        Make HTTP request to ComfyUI backend.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/prompt')
            data: Request body (dict will be JSON encoded, or bytes for raw data)
            timeout: Override default timeout
            headers: Additional headers dict
        
        Returns:
            dict or bytes: Parsed JSON response or raw bytes
        
        Raises:
            ServerConnectionError: Connection failed
            ServerAPIError: Server returned error
        """
        url = f"{self.server_url}{endpoint}"
        
        # Setup headers
        request_headers = {
            'User-Agent': 'StyleEngine-Blender/1.0'
        }
        if headers:
            request_headers.update(headers)
        
        # Prepare request body
        request_data = None
        if data:
            if isinstance(data, bytes):
                request_data = data
            else:
                request_data = json.dumps(data).encode('utf-8')
                if 'Content-Type' not in request_headers:
                    request_headers['Content-Type'] = 'application/json'
        
        try:
            req = urllib.request.Request(
                url,
                data=request_data,
                headers=request_headers,
                method=method
            )
            
            request_timeout = timeout if timeout is not None else self.timeout
            
            with urllib.request.urlopen(req, timeout=request_timeout) as response:
                response_data = response.read()
                
                # Try to parse as JSON
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    return json.loads(response_data.decode('utf-8'))
                else:
                    return response_data
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get('error', error_body)
            except json.JSONDecodeError:
                error_msg = error_body
            
            raise ServerAPIError(f"HTTP {e.code}: {error_msg}")
                    
        except urllib.error.URLError as e:
            raise ServerConnectionError(f"Connection failed: {e.reason}")
        
        except Exception as e:
            raise ServerAPIError(f"Unexpected error: {str(e)}")
    
    # ================================================================
    # WORKFLOW EXECUTION
    # ================================================================
    
    def queue_prompt(self, workflow_json):
        """
        Queue workflow for execution on ComfyUI backend.
        
        Args:
            workflow_json: Complete workflow JSON (workflow_api.json format)
        
        Returns:
            dict: Response with prompt_id
                {
                    "prompt_id": "uuid-string",
                    "number": 123,
                    "node_errors": {}
                }
        
        Raises:
            ServerAPIError: If queueing fails
        """
        # Note: We intentionally omit client_id so ComfyUI broadcasts
        # progress/executing messages to ALL connected WebSocket clients.
        # This allows our progress bridge to receive real-time updates.
        
        payload = {
            "prompt": workflow_json
        }
        
        response = self._request('POST', '/prompt', data=payload)
        
        # Check for node errors
        if response.get('node_errors'):
            errors = response['node_errors']
            error_details = []
            for node_id, error_info in errors.items():
                error_details.append(f"Node {node_id}: {error_info}")
            raise ServerExecutionError(f"Workflow validation failed: {'; '.join(error_details)}")
        
        return response
    
    def get_history(self, prompt_id):
        """
        Get execution history/results for a prompt.
        
        Args:
            prompt_id: Prompt ID from queue_prompt
        
        Returns:
            dict: History data for the prompt
                {
                    "prompt_id": {
                        "prompt": [...],
                        "outputs": {
                            "node_id": {
                                "images": [
                                    {
                                        "filename": "ComfyUI_00001_.png",
                                        "subfolder": "",
                                        "type": "output"
                                    }
                                ]
                            }
                        },
                        "status": {
                            "status_str": "success",
                            "completed": true,
                            "messages": [...]
                        }
                    }
                }
        """
        return self._request('GET', f'/history/{prompt_id}')
    
    def get_queue(self):
        """
        Get current queue status.
        
        Returns:
            dict: Queue information
                {
                    "queue_running": [...],
                    "queue_pending": [...]
                }
        """
        return self._request('GET', '/queue')
    
    # ================================================================
    # IMAGE HANDLING
    # ================================================================
    
    def upload_image(self, image_path, subfolder="", overwrite=False):
        """
        Upload image to ComfyUI server.
        
        Args:
            image_path: Path to image file
            subfolder: Optional subfolder in input directory
            overwrite: Whether to overwrite existing file
        
        Returns:
            dict: Upload response with filename
                {
                    "name": "uploaded_filename.png",
                    "subfolder": "",
                    "type": "input"
                }
        """
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Get filename
        filename = Path(image_path).name
        
        # Create multipart form data
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        
        body = []
        
        # Add image file
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"'.encode())
        body.append(f'Content-Type: image/png'.encode())
        body.append(b'')
        body.append(image_data)
        
        # Add subfolder if specified
        if subfolder:
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="subfolder"')
            body.append(b'')
            body.append(subfolder.encode())
        
        # Add overwrite flag
        body.append(f'--{boundary}'.encode())
        body.append(b'Content-Disposition: form-data; name="overwrite"')
        body.append(b'')
        body.append(str(overwrite).lower().encode())
        
        body.append(f'--{boundary}--'.encode())
        body.append(b'')
        
        request_body = b'\r\n'.join(body)
        
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
        
        return self._request('POST', '/upload/image', data=request_body, headers=headers)
    
    def upload_mesh(self, mesh_path, subfolder="", overwrite=False):
        """
        Upload 3D mesh file to ComfyUI server.
        
        Args:
            mesh_path: Path to mesh file (.glb, .obj, etc.)
            subfolder: Optional subfolder in input directory
            overwrite: Whether to overwrite existing file
        
        Returns:
            dict: Upload response with filename
                {
                    "name": "uploaded_filename.glb",
                    "subfolder": "",
                    "type": "input"
                }
        """
        # Read mesh file
        with open(mesh_path, 'rb') as f:
            mesh_data = f.read()
        
        # Get filename
        filename = Path(mesh_path).name
        
        # Determine content type based on extension
        ext = Path(mesh_path).suffix.lower()
        content_types = {
            '.glb': 'model/gltf-binary',
            '.gltf': 'model/gltf+json',
            '.obj': 'text/plain',
            '.fbx': 'application/octet-stream',
            '.stl': 'application/octet-stream',
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        # Create multipart form data
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        
        body = []
        
        # Add mesh file
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="image"; filename="{filename}"'.encode())
        body.append(f'Content-Type: {content_type}'.encode())
        body.append(b'')
        body.append(mesh_data)
        
        # Add subfolder if specified
        if subfolder:
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="subfolder"')
            body.append(b'')
            body.append(subfolder.encode())
        
        # Add overwrite flag
        body.append(f'--{boundary}'.encode())
        body.append(b'Content-Disposition: form-data; name="overwrite"')
        body.append(b'')
        body.append(str(overwrite).lower().encode())
        
        body.append(f'--{boundary}--'.encode())
        body.append(b'')
        
        request_body = b'\r\n'.join(body)
        
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
        
        print(f"[Server API] Uploading mesh: {filename} ({len(mesh_data)/1024:.1f} KB)")
        return self._request('POST', '/upload/image', data=request_body, headers=headers)
    
    def download_image(self, filename, save_path, subfolder="", image_type="output"):
        """
        Download image from ComfyUI server.
        
        Args:
            filename: Image filename on server
            save_path: Local path to save image
            subfolder: Optional subfolder path
            image_type: Type of image ("output", "input", "temp")
        
        Returns:
            bool: True if successful
        """
        try:
            # Build URL with query parameters
            params = {
                'filename': filename,
                'type': image_type
            }
            if subfolder:
                params['subfolder'] = subfolder
            
            query_string = '&'.join(f'{k}={v}' for k, v in params.items())
            endpoint = f'/view?{query_string}'
            
            # Download image
            image_data = self._request('GET', endpoint)
            
            # Ensure parent directory exists
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            with open(save_path, 'wb') as f:
                f.write(image_data)
            
            return True
        except Exception as e:
            print(f"[Server API] Download failed: {e}")
            return False
    
    def download_mesh(self, filename, save_path, subfolder="", file_type="output"):
        """
        Download 3D mesh file from ComfyUI server.
        
        Args:
            filename: Mesh filename on server (e.g., "Hy21_Mesh_00001_.glb")
            save_path: Local path to save mesh
            subfolder: Optional subfolder path
            file_type: Type of file ("output", "input", "temp")
        
        Returns:
            bool: True if successful
        """
        try:
            # Build URL with query parameters
            params = {
                'filename': filename,
                'type': file_type
            }
            if subfolder:
                params['subfolder'] = subfolder
            
            query_string = '&'.join(f'{k}={v}' for k, v in params.items())
            endpoint = f'/view?{query_string}'
            
            # Download mesh file
            mesh_data = self._request('GET', endpoint)
            
            # Ensure parent directory exists
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(save_path, 'wb') as f:
                f.write(mesh_data)
            
            print(f"[Server API] Downloaded mesh: {filename} ({len(mesh_data)/1024:.1f} KB)")
            return True
        except Exception as e:
            print(f"[Server API] Mesh download failed: {e}")
            return False
    
    # ================================================================
    # STATUS CHECKING
    # ================================================================
    
    def wait_for_completion(self, prompt_id, poll_interval=2, max_wait=600):
        """
        Poll server until workflow execution completes.
        
        Args:
            prompt_id: Prompt ID to monitor
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait
        
        Returns:
            dict: Final history data
        
        Raises:
            ServerExecutionError: If execution fails or times out
        """
        start_time = time.time()
        
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise ServerExecutionError(f"Execution timeout after {max_wait}s")
            
            # Get history
            history = self.get_history(prompt_id)
            
            if prompt_id in history:
                prompt_data = history[prompt_id]
                status = prompt_data.get('status', {})
                
                # Check if completed
                if status.get('completed', False):
                    status_str = status.get('status_str', 'unknown')
                    
                    if status_str == 'success':
                        return prompt_data
                    else:
                        # Execution failed
                        messages = status.get('messages', [])
                        error_msg = f"Execution failed: {status_str}"
                        if messages:
                            error_msg += f" - {messages}"
                        raise ServerExecutionError(error_msg)
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def check_connection(self):
        """
        Test connection to ComfyUI server with detailed diagnostics.
        
        Returns:
            tuple: (success: bool, status: dict)
                success: True if server is reachable and responding
                status: Dict with connection details:
                    {
                        'reachable': bool,
                        'queue_accessible': bool,
                        'server_url': str,
                        'error': str or None,
                        'queue_info': dict or None
                    }
        """
        status = {
            'reachable': False,
            'queue_accessible': False,
            'server_url': self.server_url,
            'error': None,
            'queue_info': None
        }
        
        print(f"[Server API] 🔍 Checking connection to: {self.server_url}")
        
        try:
            # Try to get queue status (lightweight endpoint)
            print(f"[Server API]   → Attempting to reach /queue endpoint...")
            queue_info = self.get_queue()
            
            status['reachable'] = True
            status['queue_accessible'] = True
            status['queue_info'] = queue_info
            
            # Extract queue statistics
            queue_running = queue_info.get('queue_running', [])
            queue_pending = queue_info.get('queue_pending', [])
            
            print(f"[Server API]   ✓ Server is reachable and responding")
            print(f"[Server API]   ✓ Queue endpoint accessible")
            print(f"[Server API]   → Queue status: {len(queue_running)} running, {len(queue_pending)} pending")
            
            return True, status
            
        except ServerConnectionError as e:
            status['error'] = f"Connection failed: {e}"
            print(f"[Server API]   ✗ Connection failed: {e}")
            print(f"[Server API]   → Server may be down or URL is incorrect")
            return False, status
            
        except ServerAPIError as e:
            status['reachable'] = True  # Server responded but with error
            status['error'] = f"Server error: {e}"
            print(f"[Server API]   ⚠ Server is reachable but returned error: {e}")
            return False, status
            
        except Exception as e:
            status['error'] = f"Unexpected error: {e}"
            print(f"[Server API]   ✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False, status
    
    def check_server_health(self):
        """
        Perform comprehensive server health check.
        
        Returns:
            dict: Health status with detailed information
                {
                    'healthy': bool,
                    'connection': dict,  # From check_connection()
                    'object_info_accessible': bool,
                    'details': str
                }
        """
        print(f"[Server API] 🏥 Performing server health check...")
        
        health = {
            'healthy': False,
            'connection': None,
            'object_info_accessible': False,
            'details': ''
        }
        
        # Step 1: Check basic connection
        connected, conn_status = self.check_connection()
        health['connection'] = conn_status
        
        if not connected:
            health['details'] = "Server is not reachable or not responding"
            print(f"[Server API] ❌ Server health check FAILED: {health['details']}")
            return health
        
        # Step 2: Check if object_info endpoint is accessible (indicates ComfyUI is fully loaded)
        try:
            print(f"[Server API]   → Checking /object_info endpoint (ComfyUI initialization)...")
            object_info = self._request('GET', '/object_info')
            
            if object_info and isinstance(object_info, dict):
                node_count = len(object_info)
                health['object_info_accessible'] = True
                health['details'] = f"Server is healthy. ComfyUI loaded with {node_count} nodes available."
                print(f"[Server API]   ✓ Object info accessible ({node_count} nodes)")
                health['healthy'] = True
            else:
                health['details'] = "Server responded but object_info format is invalid"
                print(f"[Server API]   ⚠ Object info returned invalid format")
                
        except Exception as e:
            health['details'] = f"Server is reachable but ComfyUI may not be fully initialized: {e}"
            print(f"[Server API]   ⚠ Object info check failed: {e}")
            # Still consider it partially healthy if connection works
            health['healthy'] = conn_status['reachable']
        
        if health['healthy']:
            print(f"[Server API] ✅ Server health check PASSED: {health['details']}")
        else:
            print(f"[Server API] ⚠ Server health check WARNING: {health['details']}")
        
        return health


# ================================================================
# HELPER FUNCTIONS
# ================================================================

def apply_overrides_to_workflow(workflow_json, overrides):
    """
    Apply overrides to workflow JSON (modifies in place).
    
    Args:
        workflow_json: Base workflow dict
        overrides: Overrides dict in format {node_id: {"inputs": {key: value}}}
    
    Returns:
        dict: Modified workflow
    """
    for node_id, node_overrides in overrides.items():
        if node_id in workflow_json:
            if 'inputs' in node_overrides:
                # Update node inputs
                workflow_json[node_id]['inputs'].update(node_overrides['inputs'])
    
    return workflow_json


def extract_output_images(prompt_data):
    """
    Extract output image information from prompt execution data.
    
    Args:
        prompt_data: Prompt data from get_history
    
    Returns:
        list: List of image dicts with 'filename', 'subfolder', 'type'
    """
    images = []
    outputs = prompt_data.get('outputs', {})
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output:
            for img in node_output['images']:
                images.append({
                    'filename': img['filename'],
                    'subfolder': img.get('subfolder', ''),
                    'type': img.get('type', 'output')
                })
    
    return images

