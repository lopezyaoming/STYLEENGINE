import os
import google.auth
import google.auth.transport.requests
from google.cloud import aiplatform

# --- CONFIG ---
PROJECT_ID = "ambient-sphere-469215-u9"
REGION = "us-west1"
BUCKET_NAME = "gs://style_engine_data"
CREDENTIALS_PATH = r"C:\Users\Juan\AppData\Roaming\gcloud\application_default_credentials.json"

# --- AUTH INJECTION ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH

# Manually refresh the token to ensure it's active
credentials, project = google.auth.default()
auth_req = google.auth.transport.requests.Request()
credentials.refresh(auth_req)

print(f"Authenticated as: {credentials.service_account_email if hasattr(credentials, 'service_account_email') else 'User Account'}")
print(f"Token active: {credentials.valid}")

aiplatform.init(
    project=PROJECT_ID,
    location=REGION,
    staging_bucket=BUCKET_NAME,
    credentials=credentials
)

def run_gemma_fine_tuning():
    print("--- STARTING VERTEX AI FINE-TUNING: MANUAL TOKEN MODE ---")

    # Use the specific regional URL to minimize redirect friction
    REGIONAL_TEMPLATE = f"https://{REGION}-kfp.pkg.dev/ml-pipeline/google-cloud-pipeline-templates/tune-language-model/v1.0.0"

    job = aiplatform.PipelineJob(
        display_name="gemma-style-engine-distillation-v1",
        template_path=REGIONAL_TEMPLATE,
        # Passing credentials here forces the SDK to use the refreshed token for the URL fetch
        credentials=credentials,
        parameter_values={
            "project": PROJECT_ID,
            "location": REGION,
            "dataset_uri": f"{BUCKET_NAME}/gemma_distillation_v2_creative.jsonl",
            "model_display_name": "gemma-3-4b-style-engine",
            "training_steps": 300,
            "learning_rate": 2e-4,
            "lora_rank": 8,
        }
    )

    # Sync=True will keep the script running so you can see the logs in your terminal
    job.run(sync=True)

if __name__ == "__main__":
    run_gemma_fine_tuning()