import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


def run_instructional_synthesis():
    print("--- INITIALIZING INSTRUCTIONAL AGENT: AESTHETIC EXPANSION ---")

    if not os.path.exists("descriptive.md"):
        print("Error: descriptive.md not found.")
        return

    with open("descriptive.md", "r") as f:
        dna_archive = f.read()

    # THE EXPANDED SYSTEM PROMPT
    # Forces the agent to use direct references and broader aesthetic adjacencies.
    instructional_prompt = f"""
    You are the Lead Art Director. Your job is to translate 'descriptive.md' into a 
    broad, non-deterministic 'instructional.md' for the Synthetic Factory.

    ### 1. THE REFERENCE ANCHORS:
    - Periodically invoke the 'Foundational Spirits' to break the AI's robotic tone. 
    - Use: "In the spirit of Ariel Costa's flat-planar collage..." or "With the chunky, nostalgic weight of a 1980s vinyl toy..."
    - Reference: Studio Ghibli (for lighting/mood), John Howe (for gritty silhouette), and DIY Claymation (for texture).

    ### 2. AESTHETIC ADJACENCIES (The Material Cloud):
    - Don't just say 'plastic'. Broaden the surface vocabulary: 
      * Vinyl, PVC, Ceramic, High-Gloss Enamel, Gummy Resin, Polished Acrylic, Thick Latex.
    - Don't just say 'round'. Broaden the geometry: 
      * Bulbous, inflated, squashed, bean-like, heavy-bottomed, pill-shaped.

    ### 3. THE "COLLISION" RULE:
    - Every prompt must collide two 'Opposing Values' to find the studio's "Aggressive but Funny" sweet spot.
    - Example: A "cute, blobby character" in a "harsh, industrial noir refinery."

    ### 4. MULTIMODAL DATASET STRUCTURE:
    - INPUT: Image + Hint.
    - THOUGHT: 1-2 sentences explaining the 'Aesthetic Collision' and the 'Reference Anchor' used.
    - OUTPUT: A punchy, 3-sentence Master Prompt that feels like a human Art Director's note.

    ### POSITIVE DISPLACEMENT:
    - Describe the presence of 'automated desolation' instead of 'no people'.
    - Describe 'soft, plump junctions' instead of 'no sharp edges'.

    INPUT DNA ARCHIVE:
    {dna_archive}

    ### OUTPUT SECTIONS:
    1. THE MATERIAL & FORM CLOUD (Varied synonyms and adjacencies).
    2. THE REFERENCE LIBRARY (How and when to name-drop Ariel Costa, Howe, Ghibli, etc.).
    3. THE COLLISION PROTOCOL (Rules for mixing 'Cute' and 'Gritty').
    4. 3 DIVERSE SAMPLES (Varying in tone from 'Hyper-Clean Toy' to 'Industrial Noir').
    """

    try:
        print("Step 1: Compiling 'instructional.md' with Aesthetic Expansion...")

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=[instructional_prompt],
            config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="HIGH"))
        )

        with open("instructional.md", "w") as f:
            f.write(response.text)

        print("\nSUCCESS: 'instructional.md' is ready.")
        print("The Generative Agent now has a broader, reference-rich vocabulary.")

    except Exception as e:
        print(f"Instructional Synthesis Error: {e}")


if __name__ == "__main__":
    run_instructional_synthesis()