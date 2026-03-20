import os
import json
import requests
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
CHECKPOINT_FILE = "audit_results_partial.json"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def get_image_bytes(image_url):
    """Resilient binary download for Miro v2."""
    try:
        # Miro images often need a redirect to get the actual binary
        fallback_url = image_url.replace("redirect=false", "redirect=true")
        res = requests.get(fallback_url, headers={"Authorization": f"Bearer {MIRO_TOKEN}"}, timeout=20)
        return res.content if res.status_code == 200 else None
    except Exception as e:
        print(f"      ! Download Error: {e}")
        return None


def run_forensic_audit():
    print("--- INITIALIZING AUDIT AGENT: LIVE-SAVE MODE ---")

    # 1. Load existing progress if available
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            try:
                audit_results = json.load(f)
                print(f"--- RESUMING: {len(audit_results)} items already in checkpoint ---")
            except:
                audit_results = {}
    else:
        audit_results = {}

    with open("studio_style_dataset.jsonl", "r") as f:
        lines = f.readlines()

    # Stage 1: Multimodal Forensic Audit
    for i, line in enumerate(lines):
        data = json.loads(line)
        miro_id = data['miro_id']

        # SKIP if already audited
        if miro_id in audit_results:
            continue

        print(f"[{i + 1}/{len(lines)}] Auditing Item: {miro_id}...")

        image_bytes = get_image_bytes(data['image_url'])
        if not image_bytes:
            print(f"   > Skip: Could not fetch image.")
            continue

        # [Audit Prompt remains exactly as you specified]
        audit_prompt = """ [Your 10-point Forensic Prompt here] """

        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image_part, audit_prompt]
            )

            # 2. Update memory
            audit_results[miro_id] = {
                "note": data['original_note'],
                "audit": response.text
            }

            # 3. LIVE-SAVE: Write to disk immediately
            with open(CHECKPOINT_FILE, "w", encoding="utf-8") as tmp_f:
                json.dump(audit_results, tmp_f, indent=2)

            print(f"   > SUCCESS: {miro_id} saved to {CHECKPOINT_FILE}.")

        except Exception as e:
            print(f"   > Audit error on {miro_id}: {e}")
            time.sleep(1)  # Small cool-down

    print(f"\nCOMPLETED: All {len(audit_results)} items audited.")


if __name__ == "__main__":
    run_forensic_audit()