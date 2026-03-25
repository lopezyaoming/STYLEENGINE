import os
import json
import math
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
INPUT_FILE = "audit_results_partial.json"
CLUSTER_FILE = "cluster_summaries.json"
MEGA_FILE = "mega_summaries.json"
OUTPUT_FILE = "descriptive.md"

BATCH_SIZE = 10  # Individual audits per Cluster
MEGA_BATCH_SIZE = 8  # Clusters per Mega-Cluster
TIMEOUT = 1800  # 30-minute ceiling for final synthesis

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_tiered_synthesis():
    print("--- [STAGE 1] INITIALIZING CLUSTER SUMMARIZATION ---")

    if not os.path.exists(INPUT_FILE):
        print(f"CRITICAL: {INPUT_FILE} not found. Please verify the forensic audit path.")
        return

    # 1. LOAD AUDITS & GENERATE CLUSTERS
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    items = list(audit_data.items())
    num_batches = math.ceil(len(items) / BATCH_SIZE)

    # Resume clusters if file exists
    if os.path.exists(CLUSTER_FILE):
        with open(CLUSTER_FILE, "r", encoding="utf-8") as f:
            cluster_summaries = json.load(f)
        print(f"Resuming: {len(cluster_summaries)} existing cluster summaries found.")
    else:
        cluster_summaries = []

    for i in range(len(cluster_summaries), num_batches):
        batch = items[i * BATCH_SIZE: (i + 1) * BATCH_SIZE]
        print(f"Processing Cluster {i + 1}/{num_batches}...")

        batch_text = "\n".join([f"ID: {k} | NOTE: {v['note']} | AUDIT: {v['audit']}" for k, v in batch])
        cluster_prompt = f"Analyze this cluster of 3D asset audits. Extract Aesthetic Facts and Production Logic: \n{batch_text}"

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[cluster_prompt]
            )
            cluster_summaries.append(response.text)
            # Live-save cluster progress
            with open(CLUSTER_FILE, "w", encoding="utf-8") as f:
                json.dump(cluster_summaries, f, indent=2)
            time.sleep(2)
        except Exception as e:
            print(f"   > Cluster {i + 1} execution failed: {e}")
            return

    # 2. GENERATE MEGA-CLUSTERS (TIER 2)
    print("\n--- [STAGE 2] COMPRESSING TO MEGA-SUMMARIES ---")
    num_mega = math.ceil(len(cluster_summaries) / MEGA_BATCH_SIZE)

    if os.path.exists(MEGA_FILE):
        with open(MEGA_FILE, "r", encoding="utf-8") as f:
            mega_summaries = json.load(f)
        print(f"Resuming: {len(mega_summaries)} mega-summaries found.")
    else:
        mega_summaries = []

    for i in range(len(mega_summaries), num_mega):
        mega_batch = cluster_summaries[i * MEGA_BATCH_SIZE: (i + 1) * MEGA_BATCH_SIZE]
        print(f"Processing Mega-Cluster {i + 1}/{num_mega}...")

        mega_text = "\n\n".join(mega_batch)
        mega_prompt = f"Synthesize these cluster summaries into a high-level chapter of aesthetic DNA: \n{mega_text}"

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[mega_prompt]
            )
            mega_summaries.append(response.text)
            with open(MEGA_FILE, "w", encoding="utf-8") as f:
                json.dump(mega_summaries, f, indent=2)
        except Exception as e:
            print(f"   > Mega-Cluster {i + 1} execution failed: {e}")
            return

    # 3. FINAL SYNTHESIS (TIER 3)
    print("\n--- [STAGE 3] COMMENCING FINAL BIBLE SYNTHESIS ---")
    final_input = "\n\n=== DNA CHAPTERS ===\n".join(mega_summaries)

    synthesis_prompt = f"""
    You are the Lead Aesthetic Analyst. Synthesize the following DNA Chapters into 'descriptive.md'.
    This is an exhaustive, 1,500-word objective autopsy of the project's visual and conceptual DNA.

    DNA CHAPTERS:
    {final_input}

    RULES:
    1. NOT INSTRUCTIONAL: Describe what 'is'.
    2. COGNITIVE TOPOLOGY: Map 'Anchor Assets', 'Friction Points', and 'Logical Clusters'.
    3. HYPER-DETAILED: Describe Subject, Mood, Medium, and Elements. 

    OUTPUT SECTIONS:
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

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(final_response.text)
        print(f"SUCCESS: {OUTPUT_FILE} is finalized and ready for the instructional agent.")

    except Exception as e:
        print(f"Final Synthesis failed during high-reasoning pass: {e}")


if __name__ == "__main__":
    run_tiered_synthesis()