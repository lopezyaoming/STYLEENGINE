import requests
import json
from collections import defaultdict

MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
BOARD_ID = "uXjVGwURc0U="
BASE_URL = f"https://api.miro.com/v2/boards/{BOARD_ID}"

headers = {"Authorization": f"Bearer {MIRO_TOKEN}"}

def fetch_all_items():
    """Fetch all items from the board with pagination"""
    all_items = []
    url = f"{BASE_URL}/items"
    cursor = None
    
    while True:
        params = {"limit": 50}
        if cursor:
            params["cursor"] = cursor
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error fetching items: {response.status_code}")
            break
        
        data = response.json()
        all_items.extend(data.get("data", []))
        
        cursor = data.get("cursor")
        if not cursor or len(data.get("data", [])) == 0:
            break
    
    return all_items

def fetch_item_details(item_id, item_type):
    """Fetch detailed information for a specific item"""
    try:
        if item_type == "text":
            url = f"{BASE_URL}/texts/{item_id}"
        elif item_type == "image":
            url = f"{BASE_URL}/images/{item_id}"
        elif item_type == "shape":
            url = f"{BASE_URL}/shapes/{item_id}"
        elif item_type == "frame":
            url = f"{BASE_URL}/frames/{item_id}"
        else:
            url = f"{BASE_URL}/items/{item_id}"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching {item_type} {item_id}: {e}")
    return None

def fetch_comments(item_id):
    """Fetch comments for an item"""
    try:
        url = f"{BASE_URL}/items/{item_id}/comments"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("data", [])
    except Exception as e:
        print(f"Error fetching comments for {item_id}: {e}")
    return []

def organize_by_frames(items):
    """Organize items by their parent frames"""
    frames = {}
    root_items = []
    
    for item in items:
        if item.get("type") == "frame":
            frames[item["id"]] = {
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
    
    return frames, root_items

def analyze_board():
    print("Fetching all board items...")
    all_items = fetch_all_items()
    print(f"Found {len(all_items)} items")
    
    print("Organizing by frames...")
    frames, root_items = organize_by_frames(all_items)
    print(f"Found {len(frames)} frames and {len(root_items)} root items")
    
    print("Fetching comments and details...")
    for frame_id, frame_data in frames.items():
        # Fetch comments for frame
        frame_data["comments"] = fetch_comments(frame_id)
        
        # Fetch details for items in frame
        for item in frame_data["items"]:
            item["details"] = fetch_item_details(item["id"], item.get("type", "item"))
            item["comments"] = fetch_comments(item["id"])
    
    # Fetch details for root items
    for item in root_items:
        item["details"] = fetch_item_details(item["id"], item.get("type", "item"))
        item["comments"] = fetch_comments(item["id"])
    
    return {
        "frames": frames,
        "root_items": root_items,
        "total_items": len(all_items)
    }

if __name__ == "__main__":
    result = analyze_board()
    
    # Save to JSON for analysis
    with open("../miro_board_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nAnalysis complete. Data saved to miro_board_analysis.json")
    print(f"Total frames: {len(result['frames'])}")
    print(f"Total root items: {len(result['root_items'])}")
