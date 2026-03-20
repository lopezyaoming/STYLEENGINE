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


def get_image_bytes(image_url):
    """Resilient binary download for Miro v2."""
    try:
        fallback_url = image_url.replace("redirect=false", "redirect=true")
        res = requests.get(fallback_url, headers={"Authorization": f"Bearer {MIRO_TOKEN}"}, timeout=15)
        return res.content if res.status_code == 200 else None
    except:
        return None


def run_descriptive_synthesis():
    print("--- INITIALIZING DESCRIPTIVE AGENT: DNA AUTOPSY ---")

    with open("studio_style_dataset.jsonl", "r") as f:
        lines = f.readlines()

    observation_buffer = []

    # Stage 1: Multimodal Forensic Audit
    for i, line in enumerate(lines):
        data = json.loads(line)
        print(f"[{i + 1}/{len(lines)}] Auditing Item: {data['miro_id']}...")

        image_bytes = get_image_bytes(data['image_url'])
        if not image_bytes: continue

        # REPLACEMENT 1: AGNOSTIC AUDIT PROMPT
        audit_prompt = f"""
        TASK: Perform a high-fidelity visual audit of this 3D layout/asset.
        HINT (FOR IDENTIFICATION ONLY): {data['original_note']}

        You are a machine vision analysis agent. Your task is to extract visual information from a single image with maximum precision, density, and descriptive richness. Do not be vague. Do not summarize too early. Look carefully and describe what is actually visible.
        
        Analyze the image systematically from overall composition down to small details.
        
        Your output must follow this order:
        
        1. OVERALL SCENE
        - State what the image shows in one precise sentence.
        - Identify the image type if possible: photograph, render, screenshot, scan, drawing, diagram, collage, painting, UI mockup, etc.
        - State the apparent setting or environment.
        
        2. PRIMARY SUBJECTS
        - List all major visible objects, people, structures, or entities.
        - For each one, describe:
          - what it is
          - where it is located in the frame
          - approximate size relative to the image
          - color
          - material
          - shape/form
          - pose/orientation
          - condition/state
          - relationship to nearby elements
        
        3. SPATIAL COMPOSITION
        - Describe the layout of the image.
        - Explain foreground, midground, background.
        - Mention alignment, symmetry, clustering, spacing, overlap, cropping, framing, and depth.
        - Note camera/viewpoint if inferable: eye-level, aerial, top-down, close-up, wide shot, tilted, perspective distortion, zoom level.
        
        4. VISUAL DETAILS
        - Extract fine-grained observable details:
          - textures
          - edges
          - reflections
          - shadows
          - patterns
          - seams
          - labels
          - interfaces
          - decorations
          - wear, damage, dirt, folds, wrinkles, grain, noise
        - Mention anything small but visually important.
        
        5. PEOPLE (if present)
        - Describe each visible person separately.
        - Include:
          - approximate age group
          - apparent gender presentation if visually evident
          - clothing
          - accessories
          - hairstyle
          - facial expression
          - body posture
          - gesture
          - gaze direction
          - interaction with objects or other people
        - Do not infer identity unless clearly indicated.
        
        6. TEXT IN IMAGE
        - Transcribe all visible text exactly as it appears.
        - Preserve line breaks when possible.
        - Distinguish between clearly readable text and uncertain text.
        - If text is partial or obscured, mark it as [unclear].
        
        7. COLOR AND LIGHT
        - Describe dominant colors and local color contrasts.
        - Explain lighting direction and quality: soft, harsh, diffuse, artificial, daylight, backlit, etc.
        - Mention exposure, highlights, shadows, glow, transparency, and atmosphere.
        
        8. STYLE AND IMAGE CHARACTER
        - Describe the visual style:
          - realistic, stylized, cinematic, flat, technical, editorial, commercial, documentary, game-like, architectural, product-shot, etc.
        - Mention mood conveyed by strictly visual means, not narrative speculation.
        
        9. ACTIONS AND INTERACTIONS
        - Describe what appears to be happening in the image.
        - Note interactions between subjects, objects, and environment.
        - Distinguish clearly between directly visible action and inferred action.
        
        10. AMBIGUITIES / UNCERTAINTIES
        - Explicitly state anything unclear, occluded, too small to verify, or uncertain.
        - Never invent hidden details.
        
        Rules:
        - Be descriptive, specific, and literal.
        - Prefer concrete nouns and adjectives over general wording.
        - Do not say “nice,” “interesting,” or “beautiful” unless that is part of a clearly observable style.
        - Do not speculate beyond the evidence.
        - If something is inferred, label it as “likely” or “possibly.”
        - If the image contains technical, architectural, product, interface, or material information, describe it with domain-specific precision.
        - Prioritize observable facts over interpretation.
        
        Formatting:
        - Use section headers exactly as listed above.
        - Write in dense, information-rich prose.
        - Do not skip small details.
        - Do not compress the answer into a short summary. 
        """

        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=[image_part, audit_prompt]
            )
            observation_buffer.append(f"OBSERVATION {data['miro_id']}: {response.text}")
        except Exception as e:
            print(f"   > Audit error: {e}")

    # Stage 2: Descriptive DNA Synthesis
    print("\n--- GENERATING descriptive.md ---")

    # REPLACEMENT 2: FORENSIC SYNTHESIS PROMPT
    synthesis_prompt = f"""
    You are the Lead Aesthetic Analyst and Cognitive Mapper. 
    Review the following Miro board with raw visual audit observations, artist comments, and structural notes.
    
    NEW AUDIT OBSERVATIONS:
    {chr(10).join(observation_buffer)}

    TASK:
    Generate 'descriptive.md'. It's a CoT (Chain-of-thought) documentation on a whole creative team's creative process. This is an exhaustive, objective autopsy of the project's aesthetic DNA. 

    RULES:
    1. NOT INSTRUCTIONAL: Do not use 'should' or 'must'. Describe what 'is'.
    2. COGNITIVE TOPOLOGY: Map the mental structure of the artists. Identify 'Anchor Assets', 'Friction Points', and 'Logical Clusters'.
    3. HYPER-DETAILED: Describe the physics of light, shapes, and line weights.
    4. NO CRITICAL TONE: Be a neutral observer documenting a visual system.
    5. PLAIN LANGUAGE: Keep the language as straight-forward as possible. Make an effort that the language is actionable, clear and highly descriptive.
    6. WORD LIMIT: keep it at the very least, 1500 words long.

    OUTPUT SECTIONS:
    - CHAIN OF THOUGHT: Your observations on how the team thinks, what are their priorities, and what is their overall vision.
    - AESTHETIC PHILOSOPHY: How is the team building an aesthetic philosophy with clear intent, references and influences, and where is the vision going.
    - SHAPE LANGUAGE: How is silhouette, form, proportion and shape being expressed? what is are the rules and boundries? 
    - MOOD, TONE AND INTENT: What is the mood of the scene, the tone and the atmosphere? What does the time of the day, weather and camerawork say about the state of the story, the psychological and tonal shifts of characters? 
    - THEMES, SUBJECTS AND SETTINGS: Name what are the elements present in the images. if there is reference to a particular character with distinguishable characteristics? Is a particular space, place (Interior or Exterior) being repeated? Are objects being constantly being referenced? The idea is to find patterns between images and document them.
    """

    final_response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=[synthesis_prompt],
        config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="HIGH"))
    )

    with open("descriptive.md", "w") as f:
        f.write(final_response.text)

    print("COMPLETED: descriptive.md is ready.")


if __name__ == "__main__":
    run_descriptive_synthesis()