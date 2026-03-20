import os
import json
import requests
import io
from PIL import Image
from google.cloud import storage

# --- CONFIG ---
MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
BUCKET_NAME = "style_engine_data"
MAPPING_FILE = "studio_style_dataset.jsonl"
TARGET_SIZE = (896, 896)  # Gemma 3's native resolution

storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)


def sync_and_resize():
    print(f"--- STARTING OPTIMIZED SYNC (MAX {TARGET_SIZE[0]}px) ---")
    headers = {"Authorization": f"Bearer {MIRO_TOKEN}"}
    count = 0

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                miro_id, raw_url = item.get('miro_id'), item.get('image_url')
                if not miro_id or not raw_url or raw_url == "no-url": continue

                blob = bucket.blob(f"images/{miro_id}.png")

                # 1. Get the High-Res URL from Miro
                res = requests.get(raw_url.replace("format=preview", "format=original"), headers=headers)
                real_url = res.json().get('url')
                if not real_url: continue

                # 2. Download into Memory
                img_data = requests.get(real_url).content
                img = Image.open(io.BytesIO(img_data))

                # 3. Resize with High-Quality Lanczos Filtering
                # This maintains aspect ratio but caps the longest side at 896px
                img.thumbnail(TARGET_SIZE, Image.Resampling.LANCZOS)

                # 4. Save to a Buffer and Upload
                byte_arr = io.BytesIO()
                img.save(byte_arr, format='PNG', optimize=True)
                blob.upload_from_string(byte_arr.getvalue(), content_type="image/png")

                print(f"Optimized Sync: {miro_id}.png ({len(byte_arr.getvalue()) // 1024} KB)")
                count += 1

            except Exception as e:
                print(f"Error on {miro_id}: {e}")
                continue

    print(f"--- DONE: {count} IMAGES OPTIMIZED FOR GEMMA 3 ---")


if __name__ == "__main__":
    sync_and_resize()