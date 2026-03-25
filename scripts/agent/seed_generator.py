import os
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

load_dotenv(override=True)

# --- VERIFIED 2026 CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
MODEL_ID = "gemini-2.5-flash"

vertexai.init(project=PROJECT_ID, location=LOCATION)


def run_seed_generation():
    print("--- [HUMAN SIMULATOR] GENERATING 1,000 NEUTRAL SEEDS ---")

    # 1. LOAD THE BAKED SUBJECT LIST
    if not os.path.exists("base_list.json"):
        print("CRITICAL: base_list.json not found.")
        return

    with open("base_list.json", "r", encoding="utf-8") as f:
        base_subjects = json.load(f)

    model = GenerativeModel(MODEL_ID)
    final_seeds = []
    total_target = 1000

    # 2. THE GENERATION CYCLE
    for i in range(total_target):
        # Cycle through the base_list.json to ensure all subjects are covered
        item = base_subjects[i % len(base_subjects)]

        # Scale density from 0.0 (first item) to 1.0 (last item)
        density = round(i / (total_target - 1), 3)

        print(f"[{i + 1}/{total_target}] Simulating User Input: {item['subject']} (Density: {density})")

        # The prompt is strictly neutral. It does NOT use the Art Bible/DNA.
        simulator_prompt = f"""
        ACT AS: A person typing a prompt into an image generator.
        SUBJECT: {item['subject']}
        CATEGORY: {item['category']}
        DENSITY: {density} (0.0 = minimal keyword, 1.0 = extremely verbose and detailed).

        STRICT RULES:
        1. NATURAL LANGUAGE: Describe the subject as a regular human would.
        2. DENSITY SCALING:
           - If DENSITY is near 0.0: Output only the subject name or a 2-word hint.
           - If DENSITY is near 1.0: Provide a rich, multi-sentence description of the object/scene, including scale, lighting, and composition.
        3. NO META-COMMENTARY: Output only the expanded text string.
        """

        try:
            # We use a lower temperature to keep the "Human" descriptions grounded and predictable
            response = model.generate_content(
                simulator_prompt,
                generation_config=GenerationConfig(temperature=0.4)
            )

            clean_text = response.text.strip()

            final_seeds.append({
                "id": i + 1,
                "category": item["category"],
                "subject": item["subject"],
                "density": density,
                "input_text": clean_text
            })

            # Heartbeat check for every 10 samples to prevent file loss
            if (i + 1) % 10 == 0:
                with open("seeds.json", "w", encoding="utf-8") as f:
                    json.dump(final_seeds, f, indent=2)

        except Exception as e:
            print(f"Error at index {i}: {e}")
            time.sleep(2)  # Backoff for API limits

    # 3. FINAL SAVE
    with open("seeds.json", "w", encoding="utf-8") as f:
        json.dump(final_seeds, f, indent=2)

    print("\nSUCCESS: 1,000 neutral seeds saved to seeds.json.")


if __name__ == "__main__":
    run_seed_generation()