import os
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "us-west1"
MEGA_FILE = "mega_summaries.json"
OUTPUT_FILE = "descriptive.md"
TIMEOUT = 600  # 10 minutes is plenty for Flash

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_sectional_synthesis():
    print("--- [FINAL PIVOT] COMMENCING STREAMING SECTIONAL SYNTHESIS ---")

    if not os.path.exists(MEGA_FILE):
        print(f"Error: {MEGA_FILE} not found. Ensure Stage 2 (Mega-Summaries) complete.")
        return

    with open(MEGA_FILE, "r", encoding="utf-8") as f:
        mega_summaries = json.load(f)

    final_input = "\n\n=== DNA CHAPTERS ===\n".join(mega_summaries)

    # We break the 1,500-word target into 5 distinct "Handshakes"
    sections = [
        ("CHAIN OF THOUGHT", "Autopsy the team's internal priorities and creative vision."),
        ("AESTHETIC PHILOSOPHY",
         "Define the 'Aggressive but Funny' collision and reference anchors (Costa, Howe, Ghibli)."),
        ("SHAPE LANGUAGE", "Technical mapping of silhouettes, macro-bevels, and massing rules."),
        ("MOOD, TONE AND INTENT", "Document lighting physics, volumetric fog, and cinematic setups."),
        ("VISUAL TAXONOMY", "Perform pattern-matching across all items. Document recurring materials and subjects.")
    ]

    # Initialize the file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# DESCRIPTIVE BIBLE: THE STYLE ENGINE DNA\n\n")

    for title, instruction in sections:
        print(f"Generating Section: {title}...")

        section_prompt = f"""
        You are the Lead Aesthetic Analyst. Using the DNA CHAPTERS as your dataset, 
        write the '{title}' section of the art bible.

        DNA CHAPTERS:
        {final_input}

        TASK: {instruction}

        RULES:
        1. Write exactly 400 words for this section to ensure high density.
        2. Describe what 'is'. No 'should' or 'must'.
        3. Use technical terms: Gummy Resin, Macro-Bevels, John Howe silhouettes, etc.
        """

        try:
            # We use generate_content_stream to keep the gateway from timing out
            response_stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=[section_prompt],
                config=types.GenerateContentConfig(http_options={'timeout': TIMEOUT})
            )

            with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                f.write(f"## {title}\n\n")
                for chunk in response_stream:
                    if chunk.text:
                        f.write(chunk.text)
                f.write("\n\n")

            print(f"   > Success: {title} appended.")
            time.sleep(2)  # Brief cooldown for rate limits

        except Exception as e:
            print(f"   > Error generating {title}: {e}")
            continue

    print(f"\nSUCCESS: {OUTPUT_FILE} is finalized and ready.")


if __name__ == "__main__":
    run_sectional_synthesis()