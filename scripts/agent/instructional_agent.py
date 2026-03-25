import os
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

load_dotenv(override=True)

# --- VERIFIED 2026 CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"  # Verified location for model availability
MODEL_ID = "gemini-2.5-flash"

# Initialize the Vertex AI environment
vertexai.init(project=PROJECT_ID, location=LOCATION)


def run_instructional_foreman():
    print(f"--- [PRODUCTION] GENERATING FACTORY MANUAL: {MODEL_ID} ---")

    # 1. INPUT VALIDATION
    if not os.path.exists("descriptive.md") or not os.path.exists("agent_description.md"):
        print("CRITICAL: descriptive.md or agent_description.md not found.")
        return

    with open("descriptive.md", "r", encoding="utf-8") as f:
        dna = f.read()
    with open("agent_description.md", "r", encoding="utf-8") as f:
        spec = f.read()

    # 2. THE UNIVERSAL LOGIC PROMPT (Neutral & Structural)
    foreman_prompt = f"""
    TASK: Generate 'instructions_FACTORY.md' for a Synthetic Data Factory.

    GROUND TRUTH (DNA):
    {dna}

    TOOL SPECIFICATION:
    {spec}

    ### INSTRUCTIONS FOR THE FACTORY MANUAL:
    As the Lead Systems Architect, synthesize the inputs above into a technical 'Factory Manual'. 
    The Manual must provide the following sections for a synthetic data generation model:

    1. STRATEGIC MAPPING: 
       Define how the functional requirements of the Tool Specification must be executed 
       using the specific technical vocabulary and visual rules established in the DNA.

    2. REASONING PROTOCOL: 
       Define the mandatory 'THOUGHT' block logic. Every synthetic sample must justify 
       its output based on the DNA pillars (Subject, Mood, Medium, Elements).

    3. SEMANTIC DICTIONARY: 
       Map generic user concepts to the specific technical terminology found in the DNA.

    4. ELASTICITY RULES: 
       Provide logic for handling variable input densities (sparse vs. dense inputs) 
       as defined in the Tool Specification.

    5. QUALITY BENCHMARKS: 
       Provide 3 'Gold Standard' synthetic [INPUT -> THOUGHT -> OUTPUT] samples 
       that demonstrate the required technical precision.

    TONE: Clinical, technical, directive. No conversational filler or use-case examples.
    """

    model = GenerativeModel(MODEL_ID)

    try:
        print("Opening Stream...")
        # Streaming ensures the socket stays active during pre-fill
        responses = model.generate_content(
            foreman_prompt,
            stream=True,
            generation_config=GenerationConfig(
                temperature=0.1,
                max_output_tokens=8192
            )
        )

        output_filename = "instructions_FACTORY.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            for response in responses:
                if response.text:
                    print("█", end="", flush=True)
                    f.write(response.text)

        print(f"\n\nSUCCESS: {output_filename} is ready.")

    except Exception as e:
        print(f"\n\nSynthesis Error: {e}")


if __name__ == "__main__":
    run_instructional_foreman()