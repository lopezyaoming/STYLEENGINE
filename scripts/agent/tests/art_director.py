import os
import json
import requests
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
MIRO_TOKEN = str(os.getenv("MIRO_ACCESS_TOKEN")).strip().replace('"', '').replace("'", "")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def art_director_review(image_url, studio_note):
    if not image_url or image_url == "no-url":
        return None

    try:
        # STEP 1: Attempt to get metadata
        headers = {"Authorization": f"Bearer {MIRO_TOKEN}", "Accept": "application/json"}
        res = requests.get(image_url, headers=headers, timeout=10)

        if res.status_code == 401: return "TOKEN_EXPIRED"

        image_bytes = None

        if res.status_code == 200:
            data = res.json()
            # Try to find the nested download link Miro sometimes provides
            download_url = data.get("imageUrl") or data.get("image_url") or \
                           (data.get("data") and data.get("data").get("image_url"))

            if download_url:
                img_res = requests.get(download_url, timeout=15)
                if img_res.status_code == 200:
                    image_bytes = img_res.content

        # STEP 2: FALLBACK - If JSON had no link, request raw pixels from the original URL
        if not image_bytes:
            print(f"   > No link in JSON. Trying direct binary download...")
            fallback_res = requests.get(
                image_url.replace("redirect=false", "redirect=true"),  # Force Miro to redirect to the file
                headers={"Authorization": f"Bearer {MIRO_TOKEN}"},
                timeout=15
            )
            if fallback_res.status_code == 200:
                image_bytes = fallback_res.content

        if not image_bytes:
            print(f"   > Failed to acquire pixels for this item.")
            return None

    except Exception as e:
        print(f"   > Connection error: {e}")
        return None

    # --- GEMINI 3.1 PRO REASONING ---
    try:
        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        with open("ART_BIBLE.md", "r") as f:
            bible_text = f.read()

        user_query = f"STUDIO NOTE: {studio_note}\n\nReview this asset against our Art Bible. Is it on-brand? Then generate a master prompt."

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[image_part, user_query],
            config=types.GenerateContentConfig(
                system_instruction=f"You are the Art Director. Rules:\n{bible_text}",
                thinking_config=types.ThinkingConfig(thinking_level="HIGH")
            )
        )
        return response.text
    except Exception as e:
        print(f"   > Gemini Error: {e}")
        return None


def run_distillation():
    # Process the dataset
    with open("../studio_style_dataset.jsonl", "r") as f:
        lines = f.readlines()

    for line in lines:
        data = json.loads(line)
        # REMOVE THE [cite: 1] HERE:
        print(f"--- Reviewing Miro Item: {data['miro_id']} ---")

        review = art_director_review(data['image_url'], data['original_note'])

        if review == "TOKEN_EXPIRED":
            print("FATAL: Token expired. Refresh and restart.")
            break

        if review:
            with open("../training_ready_gemma.jsonl", "a") as out:
                out.write(json.dumps({"input": data['original_note'], "output": review}) + "\n")
            print("   > Success: Review saved.")


if __name__ == "__main__":
    run_distillation()