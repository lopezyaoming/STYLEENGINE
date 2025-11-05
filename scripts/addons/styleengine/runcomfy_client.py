# ================================================================
#    RunComfy API Client
#    Pure Python HTTP client for RunComfy cloud API
# ================================================================

import urllib.request
import urllib.error
import json
import base64
import time
from pathlib import Path


# ----------------------------------------------------------------
# EXCEPTIONS
# ----------------------------------------------------------------

class RunComfyError(Exception):
    """Base exception for RunComfy API errors"""
    pass


class RunComfyAuthError(RunComfyError):
    """401 - Authentication failed"""
    pass


class RunComfyDeploymentError(RunComfyError):
    """404/403 - Deployment not found or disabled"""
    pass


class RunComfyValidationError(RunComfyError):
    """422 - Invalid request data"""
    pass


class RunComfyTimeoutError(RunComfyError):
    """Request timeout"""
    pass


class RunComfyExecutionError(RunComfyError):
    """10011 - Workflow execution failed"""
    pass


# ----------------------------------------------------------------
# HTTP CLIENT
# ----------------------------------------------------------------

class RunComfyClient:
    """Pure Python HTTP client for RunComfy API"""
    
    API_BASE = "https://api.runcomfy.net"
    
    def __init__(self, api_token, user_id, timeout=30):
        """
        Initialize RunComfy client.
        
        Args:
            api_token: RunComfy API token
            user_id: RunComfy user ID
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_token = api_token
        self.user_id = user_id
        self.timeout = timeout
    
    def _request(self, method, endpoint, data=None, timeout=None, retry=True):
        """
        Make HTTP request with error handling and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/prod/v2/deployments')
            data: Request body (dict, will be JSON encoded)
            timeout: Override default timeout
            retry: Enable retry logic (default: True)
        
        Returns:
            dict: Parsed JSON response
        
        Raises:
            RunComfyAuthError: Authentication failed
            RunComfyDeploymentError: Deployment issue
            RunComfyValidationError: Invalid request data
            RunComfyTimeoutError: Request timeout
            RunComfyError: Other API errors
        """
        url = f"{self.API_BASE}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'StyleEngine-Blender/1.0'
        }
        
        # Prepare request body
        request_data = None
        if data:
            request_data = json.dumps(data).encode('utf-8')
        
        # Retry logic with exponential backoff
        max_retries = 3 if retry else 1
        backoff = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=request_data,
                    headers=headers,
                    method=method
                )
                
                request_timeout = timeout if timeout is not None else self.timeout
                
                with urllib.request.urlopen(req, timeout=request_timeout) as response:
                    response_data = response.read().decode('utf-8')
                    return json.loads(response_data) if response_data else {}
                    
            except urllib.error.HTTPError as e:
                # Parse error response
                error_body = e.read().decode('utf-8')
                try:
                    error_json = json.loads(error_body)
                    error_msg = error_json.get('message', error_body)
                    error_code = error_json.get('code')
                except json.JSONDecodeError:
                    error_msg = error_body
                    error_code = None
                
                # Map HTTP status to exception
                if e.code == 401:
                    raise RunComfyAuthError(f"Authentication failed: {error_msg}")
                elif e.code == 403:
                    raise RunComfyDeploymentError(f"Access denied: {error_msg}")
                elif e.code == 404:
                    raise RunComfyDeploymentError(f"Not found: {error_msg}")
                elif e.code == 422:
                    raise RunComfyValidationError(f"Validation error: {error_msg}")
                elif e.code == 10011 or error_code == 10011:
                    raise RunComfyExecutionError(f"Execution failed: {error_msg}")
                else:
                    # Retry on 5xx errors
                    if e.code >= 500 and attempt < max_retries - 1:
                        print(f"[RunComfy] Server error {e.code}, retrying in {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2
                        continue
                    raise RunComfyError(f"HTTP {e.code}: {error_msg}")
                    
            except urllib.error.URLError as e:
                # Network error - retry
                if attempt < max_retries - 1:
                    print(f"[RunComfy] Network error, retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RunComfyTimeoutError(f"Network error: {e.reason}")
            
            except Exception as e:
                # Unexpected error
                if attempt < max_retries - 1:
                    print(f"[RunComfy] Unexpected error, retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RunComfyError(f"Unexpected error: {str(e)}")
        
        # Should not reach here
        raise RunComfyError("Max retries exceeded")
    
    # ----------------------------------------------------------------
    # DEPLOYMENT MANAGEMENT
    # ----------------------------------------------------------------
    
    def list_deployments(self):
        """
        List all deployments for the user.
        
        Returns:
            list: List of deployment dicts
        """
        return self._request('GET', '/prod/v2/deployments')
    
    def get_deployment(self, deployment_id):
        """
        Get deployment details.
        
        Args:
            deployment_id: Deployment ID
        
        Returns:
            dict: Deployment details
        """
        return self._request('GET', f'/prod/v2/deployments/{deployment_id}')
    
    def create_deployment(self, workflow_id, name, hardware, config=None):
        """
        Create a new deployment.
        
        Args:
            workflow_id: RunComfy workflow ID
            name: Deployment name
            hardware: Hardware tier (e.g., 'AMPERE_48')
            config: Optional deployment configuration dict
        
        Returns:
            dict: Created deployment details
        """
        payload = {
            'workflow_id': workflow_id,
            'name': name,
            'hardware': hardware
        }
        
        if config:
            payload.update(config)
        
        return self._request('POST', '/prod/v2/deployments', data=payload)
    
    def update_deployment(self, deployment_id, updates):
        """
        Update deployment configuration.
        
        Args:
            deployment_id: Deployment ID
            updates: Dict of fields to update
        
        Returns:
            dict: Updated deployment details
        """
        return self._request('PATCH', f'/prod/v2/deployments/{deployment_id}', data=updates)
    
    def delete_deployment(self, deployment_id):
        """
        Delete a deployment.
        
        Args:
            deployment_id: Deployment ID
        
        Returns:
            dict: Deletion confirmation
        """
        return self._request('DELETE', f'/prod/v2/deployments/{deployment_id}')
    
    # ----------------------------------------------------------------
    # INFERENCE
    # ----------------------------------------------------------------
    
    def submit_inference(self, deployment_id, overrides):
        """
        Submit inference request to deployment.
        
        Args:
            deployment_id: Deployment ID
            overrides: Dict of node overrides for workflow
        
        Returns:
            dict: Response with request_id, status_url, result_url, cancel_url
        """
        payload = {'overrides': overrides}
        return self._request('POST', f'/prod/v1/deployments/{deployment_id}/inference', 
                           data=payload, timeout=60)  # Longer timeout for submission
    
    def check_status(self, deployment_id, request_id):
        """
        Check inference request status.
        
        Args:
            deployment_id: Deployment ID
            request_id: Request ID from submit_inference
        
        Returns:
            dict: Status data with 'status' field (in_queue|in_progress|completed|failed)
        """
        return self._request('GET', 
                           f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/status')
    
    def get_result(self, deployment_id, request_id):
        """
        Get inference result.
        
        Args:
            deployment_id: Deployment ID
            request_id: Request ID
        
        Returns:
            dict: Result with 'status', 'outputs', 'created_at', 'finished_at'
        """
        return self._request('GET', 
                           f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/result')
    
    def cancel_request(self, deployment_id, request_id):
        """
        Cancel inference request.
        
        Args:
            deployment_id: Deployment ID
            request_id: Request ID
        
        Returns:
            dict: Cancellation confirmation
        """
        return self._request('POST', 
                           f'/prod/v1/deployments/{deployment_id}/requests/{request_id}/cancel')


# ----------------------------------------------------------------
# IMAGE HELPERS
# ----------------------------------------------------------------

def encode_image_to_base64(image_path):
    """
    Encode image to base64 data URI.
    
    Args:
        image_path: Path to image file (PNG or JPEG)
    
    Returns:
        str: Base64 data URI (data:image/png;base64,... or data:image/jpeg;base64,...)
    
    Raises:
        RunComfyError: If encoding fails
    """
    try:
        # Detect image type from extension
        image_path_str = str(image_path).lower()
        if image_path_str.endswith('.jpg') or image_path_str.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif image_path_str.endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = 'image/png'  # Default to PNG
        
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime_type};base64,{img_data}"
    except Exception as e:
        raise RunComfyError(f"Failed to encode image: {e}")


def download_image_from_url(url, save_path, api_token=None):
    """
    Download image from URL.
    
    RunComfy output URLs don't require authentication headers.
    The URLs are either:
    1. Pre-signed URLs from external storage (S3, etc.)
    2. Public /outputs/ endpoints
    
    Args:
        url: Image URL
        save_path: Path to save image
        api_token: Optional API token (not used - kept for compatibility)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create request with minimal headers
        # Note: Do NOT add Authorization header - causes 403 on storage backends
        headers = {
            'User-Agent': 'StyleEngine-Blender/1.0'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        # Download with proper request object
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(save_path, 'wb') as f:
                f.write(response.read())
        
        return True
    except Exception as e:
        print(f"[RunComfy] Download failed: {e}")
        return False


def download_image_with_fallback(result, deployment_id, request_id, save_path, api_token, api_base="https://api.runcomfy.net"):
    """
    Download image from RunComfy result with automatic fallback to instance proxy.
    
    This function handles the case where deployments don't generate pre-signed URLs
    and falls back to using the instance proxy endpoint.
    
    Args:
        result: Result dict from get_result()
        deployment_id: Deployment ID
        request_id: Request ID
        save_path: Path to save image
        api_token: API token for authentication
        api_base: API base URL
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Extract URL and metadata
    url, needs_fallback, instance_id, filename, subfolder = extract_image_url_from_result(
        result, deployment_id, request_id, api_base
    )
    
    if not url:
        print("[RunComfy] No image URL found in result")
        return False
    
    # Try direct download first
    if download_image_from_url(url, save_path, api_token):
        return True
    
    # If direct download failed and we have instance_id, try instance proxy
    if needs_fallback and instance_id and filename:
        print("[RunComfy] Direct download failed, trying instance proxy...")
        
        try:
            # Build instance proxy URL for ComfyUI's /view endpoint
            proxy_url = f"{api_base}/prod/v2/deployments/{deployment_id}/instances/{instance_id}/proxy/view"
            proxy_url += f"?filename={filename}&type=output"
            if subfolder:
                proxy_url += f"&subfolder={subfolder}"
            
            # Ensure parent directory exists
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Try downloading through proxy with Bearer auth
            headers = {
                'Authorization': f'Bearer {api_token}',
                'User-Agent': 'StyleEngine-Blender/1.0'
            }
            
            req = urllib.request.Request(proxy_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(save_path, 'wb') as f:
                    f.write(response.read())
            
            print("[RunComfy] Downloaded via instance proxy")
            return True
        except Exception as e:
            print(f"[RunComfy] Instance proxy download also failed: {e}")
            return False
    
    return False


def construct_output_url(api_base, deployment_id, request_id, filename, subfolder=''):
    """
    Construct download URL for RunComfy output file.
    
    Args:
        api_base: API base URL
        deployment_id: Deployment ID
        request_id: Request ID
        filename: Output filename
        subfolder: Optional subfolder path
    
    Returns:
        str: Full download URL
    """
    if subfolder:
        filename_path = f"{subfolder}/{filename}"
    else:
        filename_path = filename
    
    return f"{api_base}/prod/v1/deployments/{deployment_id}/requests/{request_id}/outputs/{filename_path}"


def extract_image_url_from_result(result, deployment_id, request_id, api_base):
    """
    Extract image URL from RunComfy result, handling different response formats.
    
    Args:
        result: Result dict from get_result()
        deployment_id: Deployment ID
        request_id: Request ID
        api_base: API base URL
    
    Returns:
        tuple: (url, use_instance_proxy, instance_id, filename, subfolder)
               use_instance_proxy is True if URL is not pre-signed and instance proxy should be tried
    """
    outputs = result.get('outputs', {})
    instance_id = result.get('instance_id')
    
    for node_id, node_output in outputs.items():
        if 'images' in node_output and node_output['images']:
            first_image = node_output['images'][0]
            
            # Case 1: Direct URL string (pre-signed)
            if isinstance(first_image, str):
                return (first_image, False, None, None, None)
            
            # Case 2: Dict with 'url' key (pre-signed URL - PREFERRED)
            elif isinstance(first_image, dict) and 'url' in first_image:
                return (first_image['url'], False, None, None, None)
            
            # Case 3: Dict with filename but no URL
            # This means we need to either construct /outputs/ URL or use instance proxy
            elif isinstance(first_image, dict) and 'filename' in first_image:
                filename = first_image['filename']
                subfolder = first_image.get('subfolder', '')
                
                # Try /outputs/ URL first
                url = construct_output_url(api_base, deployment_id, request_id, filename, subfolder)
                
                # But flag that instance proxy might be needed as fallback
                return (url, True, instance_id, filename, subfolder)
    
    return (None, False, None, None, None)


def get_image_size_kb(image_path):
    """
    Get image file size in KB.
    
    Args:
        image_path: Path to image file
    
    Returns:
        float: Size in KB
    """
    try:
        size_bytes = Path(image_path).stat().st_size
        return size_bytes / 1024
    except Exception:
        return 0

