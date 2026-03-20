import os
import requests
from google.cloud import storage


MIRO_TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_D0HicgBlQB_aMnGqWX9mqLYNpIg"
BUCKET_NAME = "style_engine_data"
# Using the first ID from your dataset
TEST_ID = "3458764664112081624"
TEST_URL = f"https://api.miro.com/v2/boards/uXjVGwURc0U%3D/resources/images/3458764517227179880?format=preview&redirect=false"


def test_sync():
    print(f"--- CANARY TEST: MIRO -> GCS ---")
    headers = {"Authorization": f"Bearer {MIRO_TOKEN}"}

    # 1. Test Miro Download
    print(f"Testing Miro Download for ID: {TEST_ID}...")
    response = requests.get(TEST_URL, headers=headers)

    if response.status_code == 200:
        print("Success: Image data retrieved from Miro.")

        # 2. Test GCS Upload
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(f"images/test_{TEST_ID}.png")
            blob.upload_from_string(response.content, content_type="image/png")
            print(f"Success: Image uploaded to gs://{BUCKET_NAME}/images/test_{TEST_ID}.png")
        except Exception as e:
            print(f"GCS Upload Failed: {e}")
    else:
        print(f"Miro Download Failed: {response.status_code}")
        print(f"Response: {response.text}")


if __name__ == "__main__":
    test_sync()