import json
import re


def convert_to_multimodal(input_file, output_file, bucket_name):
    print(f"--- CONVERTING {input_file} TO VERTEX MULTIMODAL FORMAT ---")

    all_items = []

    with open(input_file, 'r') as f:
        content = f.read()

        # Use regex to find every [...] block in the file to handle the "Extra Data"
        # This fixes the issue where multiple JSON lists were appended together
        blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)

        for block in blocks:
            try:
                items = json.loads(block)
                all_items.extend(items)
            except json.JSONDecodeError as e:
                print(f"Skipping a malformed block: {e}")

    print(f"Found {len(all_items)} training pairs. Formatting...")

    with open(output_file, 'w') as f_out:
        for item in all_items:
            # Handle mixed-case keys (some of your items use 'INPUT', some 'input')
            input_hint = item.get('input_hint', item.get('INPUT', item.get('input', '')))
            thought = item.get('thought', item.get('THOUGHT', ''))
            master_prompt = item.get('master_prompt', item.get('OUTPUT', item.get('output', '')))
            miro_id = item.get('miro_id', 'unknown')

            image_uri = f"gs://{bucket_name}/images/{miro_id}.png"

            # Official Vertex AI Multimodal JSONL format
            entry = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"fileData": {"mimeType": "image/png", "fileUri": image_uri}},
                            {"text": input_hint}
                        ]
                    },
                    {
                        "role": "model",
                        "parts": [
                            {"text": f"THOUGHT: {thought} OUTPUT: {master_prompt}"}
                        ]
                    }
                ]
            }
            f_out.write(json.dumps(entry) + '\n')

    print(f"SUCCESS: Created {output_file}")


if __name__ == "__main__":
    convert_to_multimodal('gemma_distillation_v2_creative.jsonl', 'vertex_multimodal_ready.jsonl', 'style_engine_data')