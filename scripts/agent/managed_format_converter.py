import json
import random

# --- CONFIG ---
INPUT_FILE = "vertex_multimodal_ready.jsonl"
TRAIN_FILE = "style_train_managed.jsonl"
VAL_FILE = "style_val_managed.jsonl"
SPLIT_RATIO = 0.9


def convert_to_managed():
    print(f"--- CONVERTING TO MANAGED TUNING SCHEMA ---")

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Error: vertex_multimodal_ready.jsonl not found.")
        return

    # Shuffle for a clean validation split
    random.shuffle(lines)
    split_idx = int(len(lines) * SPLIT_RATIO)

    train_lines = lines[:split_idx]
    val_lines = lines[split_idx:]

    def process(subset, out_path):
        with open(out_path, 'w', encoding='utf-8') as f_out:
            for line in subset:
                old = json.loads(line)

                # Extract original data
                image_uri = old['contents'][0]['parts'][0]['fileData']['fileUri']
                user_text = old['contents'][0]['parts'][1]['text']
                assistant_text = old['contents'][1]['parts'][0]['text']

                # Build the structure required by the "Open Models" docs
                managed_entry = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_text},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_uri, "detail": "low"}
                                }
                            ]
                        },
                        {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": assistant_text}
                            ]
                        }
                    ]
                }
                f_out.write(json.dumps(managed_entry) + '\n')

    process(train_lines, TRAIN_FILE)
    process(val_lines, VAL_FILE)
    print(f"Done! Created {TRAIN_FILE} and {VAL_FILE}.")


if __name__ == "__main__":
    convert_to_managed()