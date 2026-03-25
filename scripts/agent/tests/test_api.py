import vertexai
from vertexai.generative_models import GenerativeModel

# Try the most stable 2026 model first
MODEL_ID = "gemini-3-flash-preview"

try:
    vertexai.init(project="ambient-sphere-469215-u9", location="us-central1")
    model = GenerativeModel(MODEL_ID)
    response = model.generate_content("API check. Respond with 'READY'.")
    print(f"STATUS: {response.text.strip()}")
except Exception as e:
    print(f"CONNECTION FAILED: {e}")