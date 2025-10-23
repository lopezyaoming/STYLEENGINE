"""
RunComfy Cloud API Test Module
Isolated testing for cloud-based workflow execution
"""

import httpx
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

# RunComfy API Configuration
RUNCOMFY_API_BASE = "https://api.runcomfy.net"
WORKFLOW_ID = "f0c32b81-8ea3-40bf-887f-d41c9a4d5ef5"

class RunComfyTester:
    def __init__(self, api_token: str, user_id: str):
        self.api_token = api_token
        self.user_id = user_id
        self.deployment_id: Optional[str] = None
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    async def create_deployment(self, name: str = "StyleEngine_Test") -> Dict[str, Any]:
        """Create a new deployment on RunComfy"""
        url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments"
        
        payload = {
            "name": name,
            "workflow_id": WORKFLOW_ID,
            "workflow_version": "v1",
            "hardware": ["AMPERE_48"],  # 48GB A6000
            "min_instances": 0,
            "max_instances": 1,
            "queue_size": 1,
            "keep_warm_duration_in_seconds": 300  # 5 minutes warm
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.deployment_id = data.get("id")
                return {
                    "success": True,
                    "deployment_id": self.deployment_id,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def list_deployments(self) -> Dict[str, Any]:
        """List all deployments"""
        url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "deployments": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def delete_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Delete a deployment"""
        url = f"{RUNCOMFY_API_BASE}/prod/v2/deployments/{deployment_id}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Deployment deleted successfully"
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def send_workflow(
        self, 
        deployment_id: str,
        prompt: str = "A beautiful landscape",
        width: int = 1024,
        height: int = 1024,
        depth_strength: float = 1.0,
        canny_strength: float = 1.0,
        steps: int = 15
    ) -> Dict[str, Any]:
        """Send a workflow inference request"""
        url = f"{RUNCOMFY_API_BASE}/prod/v1/deployments/{deployment_id}/inference"
        
        # Build overrides matching SDXLRCworkflow.json structure
        overrides = {
            "39": {  # Prompt node
                "inputs": {
                    "value": prompt
                }
            },
            "5": {  # Empty Latent Image
                "inputs": {
                    "width": width,
                    "height": height
                }
            },
            "40": {  # Steps
                "inputs": {
                    "value": steps
                }
            },
            "41": {  # Depth Strength
                "inputs": {
                    "value": depth_strength
                }
            },
            "42": {  # Canny Strength
                "inputs": {
                    "value": canny_strength
                }
            }
        }
        
        payload = {"overrides": overrides}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "request_id": data.get("request_id"),
                    "status_url": data.get("status_url"),
                    "result_url": data.get("result_url"),
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def check_status(self, deployment_id: str, request_id: str) -> Dict[str, Any]:
        """Check the status of a workflow request"""
        url = f"{RUNCOMFY_API_BASE}/prod/v1/deployments/{deployment_id}/requests/{request_id}/status"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def get_result(self, deployment_id: str, request_id: str) -> Dict[str, Any]:
        """Get the result of a completed workflow request"""
        url = f"{RUNCOMFY_API_BASE}/prod/v1/deployments/{deployment_id}/requests/{request_id}/result"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {response.text}"
                }
    
    async def wait_for_completion(
        self, 
        deployment_id: str, 
        request_id: str, 
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Wait for a workflow to complete and return the result"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status_result = await self.check_status(deployment_id, request_id)
            
            if not status_result["success"]:
                return status_result
            
            status_data = status_result["data"]
            status = status_data.get("status")
            
            if status == "completed":
                # Get the final result
                return await self.get_result(deployment_id, request_id)
            elif status in ["failed", "canceled"]:
                return {
                    "success": False,
                    "error": f"Request {status}",
                    "data": status_data
                }
            
            # Still in progress, wait before polling again
            await asyncio.sleep(poll_interval)
        
        return {
            "success": False,
            "error": f"Timeout after {timeout} seconds"
        }


# Singleton instance
_tester: Optional[RunComfyTester] = None

def get_tester(api_token: str, user_id: str) -> RunComfyTester:
    """Get or create the RunComfy tester instance"""
    global _tester
    if _tester is None or _tester.api_token != api_token:
        _tester = RunComfyTester(api_token, user_id)
    return _tester

