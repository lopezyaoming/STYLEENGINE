import json
import requests
import sys

# --- CONFIGURATION ---
VM_IP = "34.145.107.158"  # Replace with your VM's public IP
COMFY_URL = f"http://{VM_IP}:8188/prompt"
BRIDGE_CLIENT_ID = "transposer_bridge_v1" # MUST match the ID in bridge.py

def send_workflow(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_json = json.load(f)
            
        # We wrap the workflow in the required ComfyUI API format
        payload = {
            "prompt": workflow_json,
            "client_id": BRIDGE_CLIENT_ID
        }
        
        print(f"🚀 Sending '{file_path}' to {VM_IP}...")
        response = requests.post(COMFY_URL, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Job Queued! Prompt ID: {result.get('prompt_id')}")
            print(f"📊 Monitor progress at: http://{VM_IP}:8189/status")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except FileNotFoundError:
        print(f"Error: Could not find file {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python queue_job.py your_workflow.json")
    else:
        send_workflow(sys.argv[1])