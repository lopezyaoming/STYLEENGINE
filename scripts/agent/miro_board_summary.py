import requests
import json
import time

MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
BOARD_ID = "uXjVGwURc0U="
BASE_URL = f"https://api.miro.com/v2/boards/{BOARD_ID}"

headers = {"Authorization": f"Bearer {MIRO_TOKEN}"}

def get_items(limit=100):
    """Get items from board"""
    url = f"{BASE_URL}/items"
    params = {"limit": limit}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def get_comments(item_id):
    """Get comments for an item"""
    url = f"{BASE_URL}/items/{item_id}/comments"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", [])
    except:
        pass
    return []

print("Fetching board data...")
data = get_items(limit=50)

if data:
    items = data.get("data", [])
    total = data.get("total", 0)
    
    print(f"Retrieved {len(items)} items out of {total} total")
    
    # Organize data
    frames = {}
    texts = []
    images = []
    
    for item in items:
        item_type = item.get("type")
        item_id = item.get("id")
        
        if item_type == "frame":
            frames[item_id] = {
                "frame": item,
                "items": [],
                "comments": get_comments(item_id)
            }
        elif item_type == "text":
            text_data = item.get("data", {})
            content = text_data.get("content", "")
            texts.append({
                "id": item_id,
                "content": content,
                "style": item.get("style", {}),
                "parent": item.get("parent", {}).get("id") if "parent" in item else None,
                "comments": get_comments(item_id)
            })
        elif item_type == "image":
            images.append({
                "id": item_id,
                "url": item.get("data", {}).get("imageUrl", ""),
                "parent": item.get("parent", {}).get("id") if "parent" in item else None,
                "comments": get_comments(item_id)
            })
    
    # Organize items into frames
    for item in items:
        if "parent" in item:
            parent_id = item["parent"]["id"]
            if parent_id in frames:
                frames[parent_id]["items"].append(item)
    
    result = {
        "total_items": total,
        "frames": frames,
        "texts": texts,
        "images": images[:50]  # Limit images
    }
    
    with open("miro_board_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Saved analysis to miro_board_analysis.json")
    print(f"Frames: {len(frames)}")
    print(f"Text items: {len(texts)}")
    print(f"Image items: {len(images)}")
else:
    print("Failed to fetch board data")
