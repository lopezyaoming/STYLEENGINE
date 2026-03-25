import os
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv

load_dotenv(override=True)

# --- PRODUCTION CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
LOCATION = "global"
MODEL_ID = "gemini-2.5-flash"
MAX_WORKERS = 5  # Number of parallel requests. Adjust based on your Quota.

OUTPUT_FILE = "style_train_managed.jsonl"
SEEDS_FILE = "seeds.json"
DNA_FILE = "descriptive.md"
MANUAL_FILE = "instructions_FACTORY.md"

vertexai.init(project=PROJECT_ID, location=LOCATION)


def load_context():
    with open(DNA_FILE, "r", encoding="utf-8") as f:
        dna = f.read()
    with open(MANUAL_FILE, "r", encoding="utf-8") as f:
        manual = f.read()
    return f"FACTORY MANUAL:\n{manual}\n\nPROJECT DNA:\n{dna}"


def strip_thoughts(text):
    parts = text.split("\n\n")
    if len(parts) > 1:
        return parts[-1].strip()
    clean = re.sub(r'(?s)THOUGHT:.*?\n\n', '', text).strip()
    return clean


def process_seed(seed, context_data, model):
    """Function for a single worker to process one seed."""
    prompt = f"""
    Using the FACTORY MANUAL and PROJECT DNA, process the following USER SEED.
    USER SEED: {seed['input_text']}
    DENSITY: {seed['density']}

    TASK: Generate aesthetically aligned response. Include THOUGHT block for reasoning, 
    followed by a double-newline and then the FINAL prompt string.
    """
    try:
        response = model.generate_content(
            [context_data, prompt],
            generation_config=GenerationConfig(temperature=0.7)
        )
        clean_output = strip_thoughts(response.text)

        return {
            "contents": [
                {"role": "user", "parts": [{"text": seed["input_text"]}]},
                {"role": "model", "parts": [{"text": clean_output}]}
            ]
        }
    except Exception as e:
        return {"error": str(e), "seed_id": seed.get('id')}


def run_factory_parallel():
    context_data = load_context()
    with open(SEEDS_FILE, "r", encoding="utf-8") as f:
        seeds = json.load(f)

    # Check progress to skip existing
    processed_count = 0
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            processed_count = sum(1 for _ in f)

    seeds_to_process = seeds[processed_count:]
    model = GenerativeModel(MODEL_ID)

    print(f"--- [PARALLEL FACTORY] STARTING {len(seeds_to_process)} SAMPLES ---")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        futures = {executor.submit(process_seed, s, context_data, model): s for s in seeds_to_process}

        for future in as_completed(futures):
            result = future.result()
            if "error" in result:
                print(f"X Error on seed: {result['error']}")
            else:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")
                print("█", end="", flush=True)

    print(f"\n--- [COMPLETE] Dataset saved to {OUTPUT_FILE} ---")


if __name__ == "__main__":
    run_factory_parallel()