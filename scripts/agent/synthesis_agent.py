import os
import json
import math
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
INPUT_FILE = "audit_results_partial.json"
BATCH_SIZE = 10  # Number of audits to synthesize at once
TIMEOUT = 600

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_recursive_synthesis():
    print("--- INITIALIZING RECURSIVE SYNTHESIS AGENT ---")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    items = list(audit_data.items())
    num_batches = math.ceil(len(items) / BATCH_SIZE)
    cluster_summaries = []

    # STAGE 1: CLUSTER SUMMARIZATION
    for i in range(num_batches):
        batch = items[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]
        print(f"Processing Cluster {i + 1}/{num_batches} ({len(batch)} items)...")

        batch_text = "\n".join([f"ID: {k} | NOTE: {v['note']} | AUDIT: {v['audit']}" for k, v in batch])

        cluster_prompt = f"""
        Analyze this cluster of 3D asset audits and artist notes. 
        Extract the recurring 'Aesthetic Facts' and 'Production Logic'.
        Focus on: Subject, Mood, Medium, and Elements.

        DATASET:
        {batch_text}
        """

        try:
            # We use Flash for the clusters—it's fast and handles large context well
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[cluster_prompt]
            )
            cluster_summaries.append(response.text)
        except Exception as e:
            print(f"   > Cluster {i + 1} failed: {e}")

    # STAGE 2: FINAL DNA AUTOPSY
    print("\n--- ALL CLUSTERS SUMMARIZED. COMMENCING FINAL BIBLE SYNTHESIS ---")

    final_input = "\n\n=== CLUSTER SUMMARY ===\n".join(cluster_summaries)

    synthesis_prompt = f"""
    You are the Lead Aesthetic Analyst. Review these Cluster Summaries from a Miro board audit.

    CLUSTER DATA:
    {final_input}

    TASK:
    Generate 'descriptive.md'. This is an exhaustive, 1,500-word objective autopsy of the project's DNA.

    RULES:
    1. NOT INSTRUCTIONAL: Describe what 'is'.
    2. COGNITIVE TOPOLOGY: Map 'Anchor Assets', 'Friction Points', and 'Logical Clusters'.
    3. HYPER-DETAILED: Describe the physics of light, shapes, and material collisions.
    4. WORD LIMIT: Minimum 1,500 words.

    SECTIONS:
    - CHAIN OF THOUGHT
    - AESTHETIC PHILOSOPHY
    - SHAPE LANGUAGE
    - MOOD, TONE AND INTENT
    - VISUAL TAXONOMY
    """

    try:
        final_response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[synthesis_prompt],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                http_options={'timeout': TIMEOUT}
            )
        )

        with open("descriptive.md", "w", encoding="utf-8") as f:
            f.write(final_response.text)
        print("SUCCESS: descriptive.md is ready.")

    except Exception as e:
        print(f"Final Synthesis failed: {e}")


if __name__ == "__main__":
    run_recursive_synthesis()