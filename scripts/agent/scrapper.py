import requests
import math
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()
ACCESS_TOKEN = os.getenv("MIRO_ACCESS_TOKEN")

# 1. PASTE YOUR TOKEN DIRECTLY HERE (from Miro Dev Panel -> 'Install app and get OAuth token')
ACCESS_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_ZtgnCXmDaYIBprmeIn4qcGabkhs"

# 2. DOUBLE CHECK YOUR BOARD ID
# If your URL is miro.com/app/board/uXjVGwURc0U=/, the ID is uXjVGwURc0U=
BOARD_ID = "uXjVGwURc0U="


HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', str(raw_html)).strip()

def get_all_items():
    # Now it will find HEADERS defined above
    url = f"https://api.miro.com/v2/boards/{BOARD_ID}/items?limit=50"
    all_items = []
    while url:
        response = requests.get(url, headers=HEADERS)
        res = response.json()
        all_items.extend(res.get('data', []))
        url = res.get('links', {}).get('next')
    return all_items


def main():
    items = get_all_items()
    print(f"Total items fetched from Miro: {len(items)}")

    # Let's see the types of the first 10 items to be sure
    sample_types = [i['type'] for i in items[:10]]
    print(f"Sample types found: {sample_types}")

    # Broaden the search
    images = [i for i in items if i['type'] in ['image', 'document', 'embed']]
    texts = [i for i in items if i['type'] in ['text', 'sticky_note', 'shape']]

    print(f"Visuals found: {len(images)} | Text found: {len(texts)}")

    golden_pairs = []

    for img in images:
        # Check if position exists. Miro v2 sometimes uses 'position', sometimes 'geometry'
        pos = img.get('position') or img.get('geometry')
        if not pos or 'x' not in pos:
            print(f"Skipping image {img['id']} - no position data found.")
            continue

        img_x, img_y = pos['x'], pos['y']

        if not texts:
            print("No text items found on the whole board to pair with!")
            break

        # Find the closest text
        try:
            best_text = min(texts, key=lambda t: math.sqrt(
                (t.get('position', {}).get('x', 0) - img_x) ** 2 +
                (t.get('position', {}).get('y', 0) - img_y) ** 2
            ))

            prompt_content = best_text['data'].get('content', '') or best_text['data'].get('data', '')

            golden_pairs.append({
                "image_url": img['data'].get('imageUrl', 'no-url'),
                "original_note": clean_html(prompt_content),
                "miro_id": img['id']
            })
        except Exception as e:
            print(f"Error pairing image {img['id']}: {e}")

    with open("studio_style_dataset.jsonl", "w") as f:
        for entry in golden_pairs:
            f.write(json.dumps(entry) + "\n")

    print(f"Done! Created {len(golden_pairs)} pairs.")


if __name__ == "__main__":
    main()