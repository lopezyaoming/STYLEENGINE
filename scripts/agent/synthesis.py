import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def generate_art_bible_v1():
    print("Step 1: Loading all 327 Miro reference notes...")

    if not os.path.exists("studio_style_dataset.jsonl"):
        print("Error: studio_style_dataset.jsonl not found.")
        return

    # Ingest the entire JSONL file as a single block of text
    with open("studio_style_dataset.jsonl", "r") as f:
        full_dataset_context = f.read()

    print("Step 2: Sending context to Gemini 3.1 Pro for Big Picture Synthesis...")

    # The Synthesis Prompt: Focuses on pattern recognition across the whole board
    synthesis_prompt = """
    You are the Lead Creative Technologist at Spiridellis Bros. Studios. 
    Attached is a raw dataset of 327 Miro board items, including image URLs and artist notes.

    TASK:
    1. Analyze the patterns in the notes. You will see recurring phrases like 'I love this one's plasticness' and technical rigging thoughts for characters like 'Black Hamster'.
    2. Synthesize these into a formal 'ART_BIBLE_v1.md'.
    3. Define exactly what 'Plasticness' means in Blender terms (Specular, Roughness, Subsurface Scattering).
    4. Define the 'Boiling Line' requirement (3px to 8px variance).
    5. Define the aesthetic for 'Underwear Frog' and 'Black Hamster' based on the collective notes.

    OUTPUT:
    Provide only the content for a high-quality Markdown file.
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[synthesis_prompt, full_dataset_context],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="HIGH")
            )
        )

        # Step 3: Save the Evolved Bible
        with open("tests/ART_BIBLE_v1.md", "w") as f:
            f.write(response.text)

        print("\nSUCCESS: ART_BIBLE_v1.md has been generated.")
        print("Review the file to see how the agent interpreted your studio DNA.")

    except Exception as e:
        print(f"Synthesis Error: {e}")


if __name__ == "__main__":
    generate_art_bible_v1()