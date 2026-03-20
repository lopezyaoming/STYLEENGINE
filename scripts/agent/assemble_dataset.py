import json
import re
import html
from difflib import SequenceMatcher

# --- CONFIG ---
BUCKET_NAME = "style_engine_data"
INPUT_CREATIVE = "gemma_distillation_v2_creative.jsonl"
MAPPING_FILE = "studio_style_dataset.jsonl"
OUTPUT_FILE = "vertex_multimodal_ready.jsonl"


def fuzzy_ratio(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def assemble():
    print(f"--- ASSEMBLING DATASET (FUZZY + SEQUENTIAL FALLBACK) ---")

    # 1. Load Mapping Data
    mapping_items = []
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            note = html.unescape(item.get('original_note', '')).strip()
            mapping_items.append({"id": item.get('miro_id'), "note": note})

    # 2. Load Creative Content
    with open(INPUT_CREATIVE, 'r', encoding='latin-1') as f:
        content = f.read()
        blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
        creative_items = []
        for b in blocks:
            creative_items.extend(json.loads(b))

    print(f"Creative: {len(creative_items)} | Images: {len(mapping_items)}")

    # 3. Enhanced Join Logic
    valid_pairs = 0
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        for idx, c_item in enumerate(creative_items):
            input_text = c_item.get('input', c_item.get('INPUT', ''))
            hint_match = re.search(r'\[Hint:\s*(.*?)\]', input_text)
            hint = hint_match.group(1).strip() if hint_match else ""

            matched_id = None

            # Strategy A: Sequence Match (High Probability if files match board order)
            if idx < len(mapping_items):
                current_map = mapping_items[idx]
                # Verify if the notes are reasonably similar
                if not hint or not current_map["note"] or fuzzy_ratio(hint, current_map["note"]) > 0.6:
                    matched_id = current_map["id"]

            # Strategy B: Search Entire Mapping for Text Match (Fallback)
            if not matched_id:
                for map_item in mapping_items:
                    if map_item["note"] and (map_item["note"] in hint or fuzzy_ratio(hint, map_item["note"]) > 0.8):
                        matched_id = map_item["id"]
                        break

            if matched_id:
                entry = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"fileData": {"mimeType": "image/png",
                                              "fileUri": f"gs://{BUCKET_NAME}/images/{matched_id}.png"}},
                                {"text": input_text}
                            ]
                        },
                        {
                            "role": "model",
                            "parts": [
                                {
                                    "text": f"THOUGHT: {c_item.get('thought', c_item.get('THOUGHT'))} OUTPUT: {c_item.get('output', c_item.get('OUTPUT'))}"}
                            ]
                        }
                    ]
                }
                f_out.write(json.dumps(entry) + '\n')
                valid_pairs += 1

    print(f"--- SUCCESS: Created {OUTPUT_FILE} with {valid_pairs} pairs ---")


if __name__ == "__main__":
    assemble()