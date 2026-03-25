import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
MEGA_FILE = "mega_summaries.json"
OUTPUT_FILE = "descriptive.md"
TIMEOUT = 600

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_sectional_synthesis():
    print("--- [FINAL ATTEMPT] STARTING SECTIONAL BIBLE SYNTHESIS ---")

    if not os.path.exists(MEGA_FILE):
        print(f"CRITICAL: {MEGA_FILE} not found. Run Tiered Synthesis Stage 2 first.")
        return

    with open(MEGA_FILE, "r", encoding="utf-8") as f:
        mega_summaries = json.load(f)

    final_input = "\n\n=== DNA CHAPTERS ===\n".join(mega_summaries)

    sections = [
        ("CHAIN OF THOUGHT", "Analyze the team's internal priorities, cognitive friction, and creative vision."),
        ("AESTHETIC PHILOSOPHY",
         "Define core intent, cultural references (Costa, Howe, Ghibli), and 'Aggressive but Funny' logic."),
        ("SHAPE LANGUAGE", "Technical autopsy of silhouettes, macro-bevels, non-Euclidean geometry, and massing."),
        ("MOOD, TONE AND INTENT", "Document lighting physics, volumetric fog logic, and cinematic setups."),
        ("VISUAL TAXONOMY", "Perform pattern-matching across all 327 items. Document recurring materials and subjects.")
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# DESCRIPTIVE BIBLE: THE STYLE ENGINE DNA\n\n")

    for title, instruction in sections:
        print(f"Generating Section: {title}...")

        section_prompt = f"""
        You are the Lead Aesthetic Analyst. Using the DNA CHAPTERS below, 
        write the '{title}' section of the 'descriptive.md' art bible.

        DNA CHAPTERS:
        {final_input}

        SECTION TASK: {instruction}

        RULES:
        1. OBJECTIVE: Describe what 'is'. No 'shoulds' or 'musts'.
        2. DENSITY: Write exactly 400 words for this section. Be extremely technical.
        3. TERMINOLOGY: Use terms like Gummy Resin, Macro-Bevels, and John Howe silhouettes.
        """

        try:
            # SWITCH TO 2.0 FLASH + STREAMING TO PREVENT 499s
            response_stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=[section_prompt],
                config=types.GenerateContentConfig(
                    http_options={'timeout': TIMEOUT}
                )
            )

            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"## {title}\n\n")
                for chunk in response_stream:
                    f.write(chunk.text)
                f.write("\n\n")

            print(f"   > SUCCESS: {title} appended.")
            time.sleep(2)  # Minimal cooldown for Flash

        except Exception as e:
            print(f"   > FAILED {title}: {e}")
            continue

    print(f"\nCOMPLETED: {OUTPUT_FILE} is ready for the instructional agent.")


if __name__ == "__main__":
    run_sectional_synthesis()