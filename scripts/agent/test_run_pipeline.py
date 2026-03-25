import json
import urllib.request
import urllib.error

BASE = "http://styleengine2:7860"

# Upload a tiny placeholder
boundary = "----Test123"
upload_body = (
    "--" + boundary + "\r\n"
    'Content-Disposition: form-data; name="files"; filename="test.glb"\r\n'
    "Content-Type: application/octet-stream\r\n\r\n"
).encode() + b"placeholder" + ("\r\n--" + boundary + "--\r\n").encode()

req = urllib.request.Request(
    BASE + "/gradio_api/upload",
    data=upload_body,
    headers={
        "Content-Type": "multipart/form-data; boundary=" + boundary,
        "User-Agent": "test",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=10) as resp:
    uploaded = json.loads(resp.read().decode())
remote_path = uploaded[0] if isinstance(uploaded[0], str) else uploaded[0]["path"]
print("Uploaded:", remote_path)

file_input = {
    "path": remote_path,
    "orig_name": "test.glb",
    "meta": {"_type": "gradio.FileData"},
}

payload = json.dumps({"data": [
    file_input, "Full Pipeline", 50000, 128, 16, 0.95, False,
    50, "512", -1.0, 10.5, 0.0, -0.001953125, 400000, 42,
]}).encode()

call_url = BASE + "/gradio_api/call/run_pipeline"
req2 = urllib.request.Request(
    call_url, data=payload,
    headers={"Content-Type": "application/json", "User-Agent": "test"},
    method="POST",
)
try:
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        result = resp2.read().decode()
        print("POST -> %d: %s" % (resp2.getcode(), result[:300]))
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:500]
    print("POST -> HTTP %d: %s" % (e.code, body))
