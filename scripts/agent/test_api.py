import os
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

load_dotenv(override=True)

# CONFIG FOR MARCH 2026
PROJECT_ID = "ambient-sphere-469215-u9"
# 'global' often bypasses regional 404s for new models
LOCATION = "global"

# The 2026 Hierarchy:
# 1. gemini-2.5-flash (Stable Workhorse)
# 2. gemini-3.1-pro-preview (New Reasoning Flagship)
# 3. gemini-3-flash-preview (Fast Reasoning)
MODEL_ID = "gemini-2.5-flash"


def test_connection():
    print(f"--- [2026] TESTING STABLE CONNECTION: {MODEL_ID} ---")
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel(MODEL_ID)

        # Test with a high-density request to ensure the pipe is clear
        response = model.generate_content("Ping. Are you ready for Style Engine synthesis?")
        print(f"STATUS: SUCCESS")
        print(f"RESPONSE: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"CONNECTION FAILED: {e}")
        return False


if __name__ == "__main__":
    test_connection()