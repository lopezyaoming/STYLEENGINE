import requests
import json
from collections import defaultdict

MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
BOARD_ID = "uXjVGwURc0U="
BASE_URL = f"https://api.miro.com/v2/boards/{BOARD_ID}"

headers = {"Authorization": f"Bearer {MIRO_TOKEN}"}

def fetch_items_page(limit=100, cursor=None):
    """Fetch a page of items"""
    url = f"{BASE_URL}/items"
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def fetch_item_comments(item_id):
    """Fetch comments for an item"""
    try:
        url = f"{BASE_URL}/items/{item_id}/comments"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("data", [])
    except:
        pass
    return []

def analyze_board_structure():
    """Analyze board structure focusing on frames and their organization"""
    print("Fetching initial items...")
    data = fetch_items_page(limit=200)
    if not data:
        return None
    
    all_items = data.get("data", [])
    total = data.get("total", 0)
    print(f"Total items on board: {total}")
    print(f"Fetched {len(all_items)} items in first batch")
    
    # Organize by frames
    frames = {}
    root_items = []
    items_by_type = defaultdict(list)
    
    for item in all_items:
        item_type = item.get("type", "unknown")
        items_by_type[item_type].append(item)
        
        if item_type == "frame":
            frame_id = item["id"]
            frames[frame_id] = {
                "frame": item,
                "items": [],
                "comments": []
            }
        elif "parent" in item:
            parent_id = item["parent"]["id"]
            if parent_id in frames:
                frames[parent_id]["items"].append(item)
            else:
                root_items.append(item)
        else:
            root_items.append(item)
    
    # Fetch comments for frames (sample first 20 frames)
    print("Fetching comments for frames...")
    frame_ids = list(frames.keys())[:20]
    for frame_id in frame_ids:
        frames[frame_id]["comments"] = fetch_item_comments(frame_id)
    
    # Get text content from items in frames
    print("Extracting text content...")
    for frame_id, frame_data in list(frames.items())[:20]:
        text_items = [item for item in frame_data["items"] if item.get("type") == "text"]
        for text_item in text_items[:10]:  # Sample first 10 text items per frame
            text_item["comments"] = fetch_item_comments(text_item["id"])
    
    return {
        "frames": {k: v for k, v in list(frames.items())[:20]},  # First 20 frames
        "root_items": root_items[:50],  # First 50 root items
        "items_by_type": {k: len(v) for k, v in items_by_type.items()},
        "total_items": total,
        "sampled_frames": len(frame_ids),
        "total_frames": len(frames)
    }

if __name__ == "__main__":
    result = analyze_board_structure()
    
    if result:
        # Save to JSON
        with open("../miro_board_analysis.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nAnalysis complete!")
        print(f"Total items: {result['total_items']}")
        print(f"Total frames found: {result['total_frames']}")
        print(f"Sampled frames: {result['sampled_frames']}")
        print(f"Item types: {result['items_by_type']}")
        print(f"Data saved to miro_board_analysis.json")
