import json
import time
from vertexai.generative_models import GenerativeModel, Part
import vertexai

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
REGION = "us-central1"
INPUT_FILE = "style_train_managed.jsonl"
OUTPUT_FILE = "style_train_text_only.jsonl"

vertexai.init(project=PROJECT_ID, location=REGION)
# Flash is perfect for this: fast, cheap, and excellent at technical descriptions
vision_model = GenerativeModel("gemini-2.5-flash")


def transcribe_dataset():
    print(f"--- STARTING VISION-TO-TEXT TRANSCRIPTION ---")

    transcribed_count = 0
    with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
            open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:

        for line in f_in:
            data = json.loads(line)

            # Extract the GCS Image URI and the Original User Text
            user_content = data['messages'][0]['content']
            original_text = next(c['text'] for c in user_content if c['type'] == 'text')
            image_uri = next(c['image_url']['url'] for c in user_content if c['type'] == 'image_url')

            # 1. Ask Gemini to "See" the style details
            prompt = """
            Analyze this Blender storyboard frame. 
            Describe the visual style using these specific keywords if they apply: 
            macro-beveled edges, gummy resin, frosted silicone, John Howe silhouettes, 
            Ariel Costa 2.5D spatial logic, Studio Ghibli volumetric fog, 
            brutalist mass, and high-gloss enamel. 
            Focus on the material collisions and lighting.
            """

            image_part = Part.from_uri(image_uri, mime_type="image/png")

            try:
                # Generate the technical description
                response = vision_model.generate_content([prompt, image_part])
                visual_description = response.text.strip()

                # 2. Build the new TEXT-ONLY entry
                # We combine the vision description with the original user text
                combined_input = f"VISUAL CONTEXT: {visual_description}\n\nUSER REQUEST: {original_text}"

                text_only_entry = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": combined_input}]
                        },
                        {
                            "role": "assistant",
                            "content": data['messages'][1]['content']  # Keep your original THOUGHT/OUTPUT
                        }
                    ]
                }

                f_out.write(json.dumps(text_only_entry) + '\n')
                transcribed_count += 1
                print(f"Transcribed {transcribed_count}: {image_uri}")

                # Simple rate limiting for the API
                time.sleep(1)

            except Exception as e:
                print(f"Failed to transcribe {image_uri}: {e}")
                continue

    print(f"--- SUCCESS: {OUTPUT_FILE} created with {transcribed_count} entries ---")


if __name__ == "__main__":
    transcribe_dataset()