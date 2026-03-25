"""
Diagnostic script for Hunyuan3D-Part Gradio API.
Run from any Python with requests: python test_part_api.py
"""
import json
import urllib.request
import urllib.error
import sys

BASE = "http://styleengine2:7860"

def fetch(url, data=None, method="GET"):
    headers = {"User-Agent": "test", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode(), resp.getcode()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return body, e.code

print("=" * 60)
print("1. Checking /info endpoint (API schema)")
print("=" * 60)
for path in ["/info", "/gradio_api/info", "/api/info"]:
    body, code = fetch(f"{BASE}{path}")
    print(f"  {path} -> {code}")
    if code == 200:
        try:
            info = json.loads(body)
            print(json.dumps(info, indent=2)[:3000])
        except Exception:
            print(body[:1000])
        break
    else:
        print(f"  {body[:200]}")

print()
print("=" * 60)
print("2. Checking /config endpoint")
print("=" * 60)
for path in ["/config", "/gradio_api/config"]:
    body, code = fetch(f"{BASE}{path}")
    print(f"  {path} -> {code}")
    if code == 200:
        try:
            cfg = json.loads(body)
            # Print just the dependencies/endpoints part
            deps = cfg.get("dependencies", [])
            for i, dep in enumerate(deps):
                api_name = dep.get("api_name", "unnamed")
                inputs = dep.get("inputs", [])
                outputs = dep.get("outputs", [])
                print(f"\n  Endpoint {i}: api_name={api_name}")
                print(f"    inputs:  {json.dumps(inputs)[:300]}")
                print(f"    outputs: {json.dumps(outputs)[:300]}")
        except Exception:
            print(body[:2000])
        break

print()
print("=" * 60)
print("3. Testing upload")
print("=" * 60)
# Create a tiny test GLB (just enough to test the upload path)
test_data = b"glTF-test-placeholder"
boundary = "----TestBoundary123"
upload_body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="files"; filename="test.glb"\r\n'
    f"Content-Type: application/octet-stream\r\n\r\n"
).encode() + test_data + f"\r\n--{boundary}--\r\n".encode()

for path in ["/gradio_api/upload", "/upload"]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(
        url, data=upload_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": "test"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = resp.read().decode()
            print(f"  {path} -> {resp.getcode()}: {result[:300]}")
            # Try calling segment with this uploaded file
            uploaded = json.loads(result)
            first = uploaded[0]
            remote_path = first.get("path", first) if isinstance(first, dict) else first

            print()
            print("=" * 60)
            print("4. Testing /call/segment with uploaded file")
            print("=" * 60)

            # Try different file_input formats
            formats = {
                "with meta": {
                    "path": remote_path,
                    "orig_name": "test.glb",
                    "meta": {"_type": "gradio.FileData"},
                },
                "path only": remote_path,
                "url style": {
                    "url": f"{BASE}/gradio_api/file={remote_path}",
                    "path": remote_path,
                    "orig_name": "test.glb",
                    "meta": {"_type": "gradio.FileData"},
                },
                "minimal dict": {"path": remote_path},
            }

            for label, file_input in formats.items():
                payload = json.dumps({
                    "data": [file_input, True, 0.95, 42]
                }).encode()
                for prefix in ["/gradio_api"]:
                    call_url = f"{BASE}{prefix}/call/segment"
                    body, code = fetch(call_url, data=payload, method="POST")
                    status_str = "OK" if code == 200 else f"HTTP {code}"
                    print(f"  [{label}] {call_url} -> {status_str}")
                    print(f"    Response: {body[:400]}")
                    if code == 200:
                        print(f"    SUCCESS with format: {label}")
                break
    except urllib.error.HTTPError as e:
        print(f"  {path} -> {e.code}")
    except Exception as e:
        print(f"  {path} -> Error: {e}")

print()
print("Done.")
