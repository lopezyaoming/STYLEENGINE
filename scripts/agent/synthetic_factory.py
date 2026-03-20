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


def run_synthetic_factory():
    print("--- STARTING HIGH-CREATIVITY GENERATIVE AGENT ---")

    with open("descriptive.md", "r") as f:
        dna_archive = f.read()
    with open("instructional.md", "r") as f:
        instructions = f.read()

    with open("studio_style_dataset.jsonl", "r") as f:
        items = [json.loads(line) for line in f.readlines()]

    for i, item in enumerate(items):
        print(f"[{i + 1}/{len(items)}] Distilling with HIGH TEMP: {item['miro_id']}...")

        # Binary download logic remains standard
        # ... (get_image_bytes function omitted for brevity)

        factory_prompt = f"""
        DNA ARCHIVE: {dna_archive}
        INSTRUCTIONAL PROTOCOL: {instructions}

        HINT: {item['original_note']}

        TASK: 
        Generate a synthetic training pair. 
        Don't be robotic. Use the 'Aesthetic Collision' protocol to mix cute and gritty.
        Reference our 'Aesthetic Anchors' (Ariel Costa, Howe, Ghibli) where appropriate.
        """

        try:
            # We set temperature to 0.9 for maximum creative 'vibe' while keeping the JSON structure
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=[factory_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.9,
                    thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                    response_mime_type="application/json"
                )
            )

            with open("tests/gemma_distillation_v2_creative.jsonl", "a") as f:
                f.write(response.text.strip() + "\n")

        except Exception as e:
            print(f"Error on {item['miro_id']}: {e}")


if __name__ == "__main__":
    run_synthetic_factory()