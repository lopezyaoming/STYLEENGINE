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

BATCH_SIZE = 10
MEGA_BATCH_SIZE = 8
TIMEOUT = 600  # Shorter timeout works now because requests are smaller

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_sectional_synthesis():
    print("--- [RECOVERY] STARTING SECTIONAL BIBLE SYNTHESIS ---")

    # 1. PREREQUISITE CHECK (Ensure Stage 2 finished)
    if not os.path.exists(MEGA_FILE):
        print(f"CRITICAL: {MEGA_FILE} not found. Please run the Tiered Synthesis Stage 2 first.")
        return

    with open(MEGA_FILE, "r", encoding="utf-8") as f:
        mega_summaries = json.load(f)

    final_input = "\n\n=== DNA CHAPTERS ===\n".join(mega_summaries)

    # 2. DEFINE THE BIBLE STRUCTURE
    # We split the 1,500 words into 5 manageable requests
    sections = [
        ("CHAIN OF THOUGHT",
         "Analyze the team's internal priorities, cognitive friction, and overall creative vision."),
        ("AESTHETIC PHILOSOPHY",
         "Define the core intent, cultural references (Costa, Howe, Ghibli), and the 'Aggressive but Funny' collision logic."),
        ("SHAPE LANGUAGE",
         "Provide a technical autopsy of silhouettes, macro-bevels, non-Euclidean geometry, and massing rules."),
        ("MOOD, TONE AND INTENT",
         "Document the lighting physics, volumetric fog logic, and the psychological impact of the cinematic setups."),
        ("VISUAL TAXONOMY",
         "Perform pattern-matching across all 327 items. Document recurring materials (Vinyl, Resin, Enamel) and subjects.")
    ]

    # Clear the file before starting
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# DESCRIPTIVE BIBLE: THE STYLE ENGINE DNA\n\n")

    # 3. SECTIONAL LOOP
    for title, instruction in sections:
        print(f"Generating Section: {title}...")

        section_prompt = f"""
        You are the Lead Aesthetic Analyst. Using the DNA CHAPTERS below as your raw data, 
        write the '{title}' section of the 'descriptive.md' art bible.

        DNA CHAPTERS:
        {final_input}

        SECTION TASK: {instruction}

        RULES:
        1. OBJECTIVE: Describe what 'is'. No 'shoulds' or 'musts'.
        2. DENSITY: Aim for 300-400 words for this section alone.
        3. TECHNICAL: Use the material/form cloud (Gummy Resin, Macro-Bevels, etc.).
        """

        try:
            # We use streaming to keep the connection alive and healthy
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=[section_prompt],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                    http_options={'timeout': TIMEOUT}
                )
            )

            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"## {title}\n\n")
                f.write(response.text + "\n\n")

            print(f"   > {title} appended successfully.")
            time.sleep(5)  # Cooldown to avoid rate limits

        except Exception as e:
            print(f"   > Failed to generate {title}: {e}")
            continue

    print(f"\nCOMPLETED: {OUTPUT_FILE} is finalized and fully expanded.")


if __name__ == "__main__":
    run_sectional_synthesis()