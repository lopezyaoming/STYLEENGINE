import threading
import json
import websocket
import uvicorn
import requests
from fastapi import FastAPI

# --- CONFIG ---
COMFY_ADDR = "127.0.0.1:8188"
FIXED_CLIENT_ID = "transposer_bridge_v1"
COMFY_WS_URL = f"ws://{COMFY_ADDR}/ws?clientId={FIXED_CLIENT_ID}"
BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 8189

app = FastAPI()

class BridgeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.data = {
            "status": "ready",
            "progress": 0.0,
            "node_name": "Idle",
            "queue_remaining": 0,
            "total_nodes": 0,
            "current_node_idx": 0
        }

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                self.data[key] = value

    def get_snapshot(self):
        with self.lock:
            return self.data.copy()

state = BridgeState()

def get_total_nodes(prompt_id):
    """Queries ComfyUI to see how many nodes are in this specific job"""
    try:
        response = requests.get(f"http://{COMFY_ADDR}/history/{prompt_id}")
        history = response.json()
        prompt = history.get(prompt_id, {}).get("prompt", [None, {}])[2] 
        # Note: Depending on Comfy version, the prompt is stored differently. 
        # If the above fails, we'll default to a reasonable number or wait for 'executing'.
        return len(prompt) if prompt else 0
    except:
        return 0

def on_message(ws, message):
    if isinstance(message, bytes): return

    try:
        msg = json.loads(message)
        m_type = msg.get("type")
        data = msg.get("data", {})

        if m_type == "status":
            q = data.get("status", {}).get("exec_info", {}).get("queue_remaining", 0)
            state.update(queue_remaining=q)
            if q == 0 and state.get_snapshot()["status"] != "processing":
                # Reset to idle state when queue is empty and not processing
                state.update(status="ready", node_name="Idle", progress=0.0, current_node_idx=0)

        elif m_type == "execution_start":
            # Reset counters for the new job
            state.update(status="processing", progress=0.0, current_node_idx=0, node_name="Starting...")
            # Optional: Dynamic node counting. For now, we increment as we go.

        elif m_type == "executing":
            node_id = data.get("node")
            if node_id is None: # Finished
                state.update(status="ready", progress=1.0, node_name="Finished", current_node_idx=0)
            else:
                # Increment the checklist
                snapshot = state.get_snapshot()
                new_idx = snapshot["current_node_idx"] + 1
                
                # We don't know the TOTAL nodes until the end, so we 'approximate' 
                # progress based on typical workflow sizes (usually 10-20 nodes)
                # OR we just let the progress climb.
                state.update(
                    status="processing", 
                    node_name=f"Node {node_id}", 
                    current_node_idx=new_idx,
                    # Placeholder progress based on a typical 12-node workflow 
                    # until we find a better way to get the total count.
                    progress = round(min(new_idx / 12.0, 0.95), 2) 
                )

        elif m_type == "progress":
            # Micro-progress: Moves the bar slightly between node increments
            val = data.get("value", 0)
            m_val = data.get("max", 1)
            snapshot = state.get_snapshot()
            
            # This keeps the bar moving within the current 'chunk'
            base_p = snapshot["progress"]
            micro_p = (val / m_val) * 0.05 
            state.update(progress=round(base_p + micro_p, 2))

    except Exception as e:
        print(f"Bridge Logic Error: {e}")

def run_ws():
    while True:
        ws = websocket.WebSocketApp(COMFY_WS_URL, 
                                    on_open=lambda w: state.update(status="ready"),
                                    on_message=on_message,
                                    on_close=lambda w, s, m: state.update(status="disconnected"))
        ws.run_forever()

@app.get("/status")
async def get_status():
    return state.get_snapshot()

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=run_ws, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)