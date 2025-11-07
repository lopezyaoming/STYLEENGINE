# ================================================================
#    RunComfy Server Manager
#    Handles launching and managing ComfyUI server instances
# ================================================================

import urllib.request
import urllib.error
import json
import time


# ================================================================
# EXCEPTIONS
# ================================================================

class ServerManagerError(Exception):
    """Base exception for server manager errors"""
    pass


class ServerLaunchError(ServerManagerError):
    """Failed to launch server"""
    pass


class ServerNotReadyError(ServerManagerError):
    """Server not ready after waiting"""
    pass


# ================================================================
# SERVER MANAGER
# ================================================================

class RunComfyServerManager:
    """
    Manages RunComfy server instances lifecycle.
    
    Handles:
    - Launching new server instances
    - Checking server status
    - Waiting for server readiness
    - Stopping servers (if supported)
    """
    
    # Try both API bases - machines might use the same base as serverless
    API_BASE_MACHINES = "https://api.runcomfy.net"
    API_BASE_SERVERLESS = "https://api.runcomfy.com"  # What serverless uses
    
    def __init__(self, api_token, user_id, timeout=30):
        """
        Initialize server manager.
        
        Args:
            api_token: RunComfy API token
            user_id: RunComfy user ID
            timeout: Request timeout in seconds
        """
        self.api_token = api_token
        self.user_id = user_id
        self.timeout = timeout
    
    def _request(self, method, endpoint, data=None, timeout=None):
        """
        Make HTTP request to RunComfy API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body (dict, will be JSON encoded)
            timeout: Override default timeout
        
        Returns:
            dict: Parsed JSON response
        """
        # Debug: Check if we have valid credentials
        if not self.api_token or len(self.api_token) < 10:
            raise ServerManagerError(f"Invalid API token (length: {len(self.api_token) if self.api_token else 0})")
        
        print(f"[Server Manager] Debug: Using API token (first 10 chars): {self.api_token[:10]}...")
        print(f"[Server Manager] Debug: User ID: {self.user_id}")
        
        # Try both API bases and multiple auth formats
        api_bases = [
            ("api.runcomfy.net", self.API_BASE_MACHINES),
            ("api.runcomfy.com", self.API_BASE_SERVERLESS),
        ]
        
        auth_formats = [
            ('Bearer Token', {'Authorization': f'Bearer {self.api_token}'}, None, False),
            ('Plain Token', {'Authorization': self.api_token}, None, False),
            ('Token= Format', {'Authorization': f'token={self.api_token}'}, None, False),
            ('X-API-Key', {'X-API-Key': self.api_token}, None, False),
            ('Query Param ONLY', {}, f'?api_key={self.api_token}', True),  # No auth header!
        ]
        
        last_error = None
        
        for base_name, api_base in api_bases:
            print(f"[Server Manager] Trying API base: {base_name}")
            
            for auth_name, auth_headers, query_params, skip_auth_header in auth_formats:
                try:
                    # Build URL with query parameters if needed
                    url = f"{api_base}{endpoint}"
                    if query_params:
                        url += query_params
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'StyleEngine-Blender/1.0'
                    }
                    
                    # Only add auth headers if not skipping them
                    if not skip_auth_header:
                        headers.update(auth_headers)
                    
                    request_data = None
                    if data:
                        request_data = json.dumps(data).encode('utf-8')
                    
                    req = urllib.request.Request(
                        url,
                        data=request_data,
                        headers=headers,
                        method=method
                    )
                    
                    request_timeout = timeout if timeout is not None else self.timeout
                    
                    with urllib.request.urlopen(req, timeout=request_timeout) as response:
                        response_data = response.read().decode('utf-8')
                        # If successful, log which auth worked for debugging
                        if method == 'POST' and 'machines' in endpoint:
                            print(f"[Server Manager] ✓ Auth successful with: {auth_name}")
                        return json.loads(response_data) if response_data else {}
                        
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode('utf-8')
                    try:
                        error_json = json.loads(error_body)
                        error_msg = error_json.get('message', error_body)
                    except json.JSONDecodeError:
                        error_msg = error_body
                    
                    last_error = ServerManagerError(f"HTTP {e.code}: {error_msg}")
                    
                    # If 403, try next auth format
                    if e.code == 403:
                        print(f"[Server Manager] Auth format '{auth_name}' failed, trying next...")
                        continue
                    else:
                        # Other errors, don't retry
                        raise last_error
                            
                except urllib.error.URLError as e:
                    last_error = ServerManagerError(f"Network error: {e.reason}")
                    raise last_error
                
                except Exception as e:
                    last_error = ServerManagerError(f"Unexpected error: {str(e)}")
                    raise last_error
        
        # All auth formats failed
        if last_error:
            raise last_error
        raise ServerManagerError("All authorization formats failed")
    
    def create_server(self, workflow_id=None, hardware_tier='AMPERE_48', name="StyleEngine Server"):
        """
        Launch a new ComfyUI server instance.
        
        Args:
            workflow_id: Optional workflow ID to load (uses default if not provided)
            hardware_tier: Hardware tier (e.g., 'AMPERE_48')
            name: Server instance name
        
        Returns:
            dict: Server information
                {
                    'server_id': str,
                    'server_url': str,
                    'status': str,
                    'created_at': str
                }
        
        Raises:
            ServerLaunchError: If launch fails
        """
        print(f"[Server Manager] =========================================")
        print(f"[Server Manager] LAUNCHING NEW COMFYUI SERVER INSTANCE")
        print(f"[Server Manager] =========================================")
        print(f"[Server Manager] Configuration:")
        print(f"[Server Manager]   Name: {name}")
        print(f"[Server Manager]   Hardware: {hardware_tier}")
        if workflow_id:
            print(f"[Server Manager]   Workflow: {workflow_id[:8]}...")
        print(f"[Server Manager]   User ID: {self.user_id}")
        print(f"[Server Manager]")
        
        # Correct endpoint with user_id in path (per RunComfy API docs)
        endpoint = f'/prod/api/users/{self.user_id}/machines'
        
        # Map hardware_tier to server_type expected by API
        # According to docs: medium, large, extra-large, 2x-large, 2xl-turbo
        hardware_map = {
            'AMPERE_48': 'large',
            'AMPERE_80': 'extra-large',
            'ADA_24': '2x-large',
            'H100': '2xl-turbo',
            'default': 'large'
        }
        server_type = hardware_map.get(hardware_tier, hardware_map['default'])
        
        payload = {
            'name': name,
            'server_type': server_type,  # API expects 'server_type' not 'hardware'
            'estimated_duration': 3600,  # 1 hour default (in seconds)
        }
        
        if workflow_id:
            payload['version_id'] = workflow_id  # API expects 'version_id' not 'workflow_id'
        
        try:
            print(f"[Server Manager] Calling: POST {endpoint}")
            print(f"[Server Manager] Server type: {server_type}")
            response = self._request('POST', endpoint, data=payload, timeout=60)
            
            # Extract server info from response
            server_id = response.get('server_id') or response.get('id')
            
            if not server_id:
                print(f"[Server Manager] Response missing server_id: {response}")
                raise ServerLaunchError(f"Server creation response missing server_id: {response}")
            
            # Construct server URL (will be updated when status is Ready)
            server_url = f"https://{server_id}-comfyui.runcomfy.com"
            
            server_info = {
                'server_id': server_id,
                'server_url': server_url,
                'status': response.get('status', 'starting'),
                'created_at': response.get('created_at', ''),
                'raw_response': response
            }
            
            print(f"[Server Manager]")
            print(f"[Server Manager] ✅ SERVER LAUNCH SUCCESSFUL")
            print(f"[Server Manager] Server ID: {server_id}")
            print(f"[Server Manager] Server URL: {server_url}")
            print(f"[Server Manager] Status: {server_info['status']}")
            print(f"[Server Manager] =========================================")
            
            return server_info
            
        except ServerManagerError as e:
            print(f"[Server Manager]")
            print(f"[Server Manager] ❌ SERVER LAUNCH FAILED")
            print(f"[Server Manager] Error: {e}")
            print(f"[Server Manager] =========================================")
            raise ServerLaunchError(f"Failed to launch server: {e}")
    
    def get_server_status(self, server_id):
        """
        Get status of a server instance.
        
        Args:
            server_id: Server ID
        
        Returns:
            dict: Server status information
                {
                    'status': str,  # 'starting', 'Ready', 'stopped', etc.
                    'ready': bool,
                    'url': str
                }
        """
        endpoint = f'/prod/api/users/{self.user_id}/machines/{server_id}'
        
        try:
            response = self._request('GET', endpoint)
            
            status_str = response.get('status', 'unknown')
            # Status is 'Ready' (capital R) when machine is fully operational per docs
            ready = status_str == 'Ready'
            
            # Get main_service_url from response when ready
            server_url = response.get('main_service_url')
            if not server_url:
                server_url = f"https://{server_id}-comfyui.runcomfy.com"
            
            return {
                'status': status_str,
                'ready': ready,
                'url': server_url,
                'raw_response': response
            }
            
        except ServerManagerError:
            # If API fails, try direct connection to server
            print(f"[Server Manager] API status check failed, trying direct connection...")
            server_url = f"https://{server_id}-comfyui.runcomfy.com"
            
            try:
                from . import runcomfy_server_client
                client = runcomfy_server_client.ComfyUIServerClient(server_url, timeout=10)
                connected, _ = client.check_connection()
                
                return {
                    'status': 'running' if connected else 'unknown',
                    'ready': connected,
                    'url': server_url
                }
            except Exception:
                return {
                    'status': 'unknown',
                    'ready': False,
                    'url': server_url
                }
    
    def wait_for_server_ready(self, server_id, timeout=300, poll_interval=10):
        """
        Wait for server to be ready.
        
        Args:
            server_id: Server ID
            timeout: Maximum seconds to wait
            poll_interval: Seconds between checks
        
        Returns:
            dict: Server info when ready
        
        Raises:
            ServerNotReadyError: If server not ready within timeout
        """
        print(f"[Server Manager] =========================================")
        print(f"[Server Manager] WAITING FOR SERVER TO BE READY")
        print(f"[Server Manager] Server ID: {server_id}")
        print(f"[Server Manager] Timeout: {timeout}s, Poll interval: {poll_interval}s")
        print(f"[Server Manager] =========================================")
        
        start_time = time.time()
        attempts = 0
        
        while True:
            attempts += 1
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                print(f"[Server Manager]")
                print(f"[Server Manager] ❌ TIMEOUT WAITING FOR SERVER")
                print(f"[Server Manager] Server did not become ready after {timeout}s")
                print(f"[Server Manager] =========================================")
                raise ServerNotReadyError(
                    f"Server {server_id[:8]}... not ready after {timeout}s"
                )
            
            print(f"[Server Manager] Attempt {attempts}: Checking server status...")
            
            try:
                status = self.get_server_status(server_id)
                
                print(f"[Server Manager]   Status: {status['status']}")
                print(f"[Server Manager]   Ready: {status['ready']}")
                
                if status['ready']:
                    print(f"[Server Manager]")
                    print(f"[Server Manager] ✅ SERVER IS READY")
                    print(f"[Server Manager] Server URL: {status['url']}")
                    print(f"[Server Manager] Total wait time: {elapsed:.1f}s")
                    print(f"[Server Manager] =========================================")
                    
                    return {
                        'server_id': server_id,
                        'server_url': status['url'],
                        'status': status['status'],
                        'wait_time': elapsed
                    }
                
                print(f"[Server Manager]   Server not ready yet, waiting {poll_interval}s...")
                time.sleep(poll_interval)
                
            except Exception as e:
                print(f"[Server Manager]   Error checking status: {e}")
                print(f"[Server Manager]   Will retry...")
                time.sleep(poll_interval)
    
    def stop_server(self, server_id):
        """
        Stop/delete a server instance.
        
        Args:
            server_id: Server ID
        
        Returns:
            bool: True if successful
        """
        print(f"[Server Manager] Stopping server {server_id[:8]}...")
        
        endpoint = f'/prod/api/users/{self.user_id}/machines/{server_id}'
        
        try:
            self._request('DELETE', endpoint)
            print(f"[Server Manager] ✓ Server stopped")
            return True
        except ServerManagerError as e:
            print(f"[Server Manager] ⚠ Could not stop server via API: {e}")
            return False
