import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
INPUT_FILE = "audit_results_partial.json" # Change to audit_results.json if final
OUTPUT_FILE = "descriptive.md"
# Increase timeout for high-thinking/large-context synthesis
TIMEOUT = 900 # 15 minutes

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def run_descriptive_synthesis():
    print("--- INITIALIZING SYNTHESIS AGENT: AESTHETIC AUTOPSY ---")

    # 1. Load the Forensic Audits
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found. Run audit_agent.py first.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    print(f"Aggregating {len(audit_data)} forensic observations...")

    # 2. Format observations for the prompt
    # We pair the artist's original intent with the machine's objective vision
    formatted_observations = []
    for miro_id, content in audit_data.items():
        entry = (
            f"--- ITEM {miro_id} ---\n"
            f"ARTIST INTENT NOTE: {content['note']}\n"
            f"FORENSIC AUDIT: {content['audit']}\n"
        )
        formatted_observations.append(entry)

    all_observations_text = "\n".join(formatted_observations)

    # 3. The Forensic Synthesis Prompt
    synthesis_prompt = f"""
    You are the Lead Aesthetic Analyst and Cognitive Mapper. 
    Review the following dataset containing 300+ raw visual audit observations, artist comments, and structural notes from a Miro board.

    NEW AUDIT OBSERVATIONS:
    {all_observations_text}

    TASK:
    Generate 'descriptive.md'. It's a CoT (Chain-of-thought) documentation on a whole creative team's creative process. This is an exhaustive, objective autopsy of the project's aesthetic DNA. 

    RULES:
    1. NOT INSTRUCTIONAL: Do not use 'should' or 'must'. Describe what 'is' (e.g., 'The system utilizes macro-beveled edges' instead of 'The user should use bevels').
    2. COGNITIVE TOPOLOGY: Map the mental structure of the artists. Identify 'Anchor Assets' (recurring pillars), 'Friction Points' (where style breaks), and 'Logical Clusters' (groups of related items).
    3. HYPER-DETAILED: Describe the physics of light (specular response, subsurface scattering), shapes (weight, mass), and material collisions (silicone vs. resin).
    4. NO CRITICAL TONE: Be a neutral observer documenting a factual visual system.
    5. PLAIN LANGUAGE: Keep the language as straight-forward and technical as possible. Make an effort that the language is actionable, clear, and highly descriptive.
    6. WORD LIMIT: Your report must be at least 1,500 words long to capture the depth of 300+ assets.

    OUTPUT SECTIONS:
    - CHAIN OF THOUGHT: Your observations on how the team thinks, what are their priorities, and what is their overall vision based on the audit.
    - AESTHETIC PHILOSOPHY: How is the team building an aesthetic philosophy with clear intent, references and influences?
    - SHAPE LANGUAGE: How is silhouette, form, proportion, and shape being expressed? What are the rules and boundaries of the geometry? 
    - MOOD, TONE AND INTENT: What is the mood of the scene? What does the lighting, weather, and camerawork say about the state of the story? 
    - VISUAL TAXONOMY (Pattern Matching): Name the elements present across the images. Find patterns in materials, characters, and settings. Document what is being repeated.
    """

    print("Sending to Gemini 3.1 Pro (Thinking: HIGH)... This will take a few minutes.")

    try:
        final_response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[synthesis_prompt],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                http_options={'timeout': TIMEOUT}
            )
        )

        # 4. Save the Final Bible
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(final_response.text)

        print(f"SUCCESS: {OUTPUT_FILE} has been generated.")

    except Exception as e:
        print(f"Synthesis failed: {e}")

if __name__ == "__main__":
    run_descriptive_synthesis()