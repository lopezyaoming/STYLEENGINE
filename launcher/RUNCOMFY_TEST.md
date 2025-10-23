# RunComfy Cloud Test - Style Engine

This isolated test module allows you to deploy and test Style Engine workflows on RunComfy's cloud infrastructure.

## Overview

The RunComfy test system provides:
- **Cloud Deployments**: Create serverless ComfyUI instances in the cloud
- **Workflow Testing**: Send workflows with the same data structure as local generation
- **Independent Testing**: Isolated from local ComfyUI, perfect for testing cloud integration

## Setup

### 1. Environment Variables

Set your RunComfy API credentials as environment variables:

```bash
# Windows (PowerShell)
$env:RUNCOMFY_API_TOKEN="your_api_token_here"
$env:RUNCOMFY_USER_ID="your_user_id_here"

# Windows (CMD)
set RUNCOMFY_API_TOKEN=your_api_token_here
set RUNCOMFY_USER_ID=your_user_id_here

# Linux/Mac
export RUNCOMFY_API_TOKEN="your_api_token_here"
export RUNCOMFY_USER_ID="your_user_id_here"
```

**Note**: These credentials are already configured in Blender addon preferences, but the server needs them as environment variables for security.

### 2. Start the Server

```bash
cd launcher
python main.py
```

The server will start on `http://localhost:8000`

### 3. Access the RunComfy Test UI

Open your browser and navigate to:
```
http://localhost:8000/runcomfy
```

## Using the Test Interface

### Step 1: Create a Deployment

1. Click **"Create New Deployment"**
2. This will:
   - Create a new RunComfy deployment with your workflow
   - Use AMPERE_48 (48GB A6000) hardware
   - Set autoscaling from 0 to 1 instance
   - Send a warm-up request to pre-load models
3. Save the `deployment_id` that appears

### Step 2: Send a Test Workflow

1. **Select or Enter Deployment ID**: Either:
   - Click "Use This" on a deployment from the list, or
   - Manually enter the deployment ID
2. **Enter Prompt** (optional):
   - Leave empty to use data from `session.json` (Blender settings)
   - Or type a custom prompt
3. Click **"Send Workflow"**

### Step 3: Monitor Progress

The interface will automatically:
- Poll the status every 5 seconds
- Display the current status (in_queue → in_progress → completed)
- Show the final result with download links

**Note**: The first run (cold start) can take 3-5 minutes as it loads models.

## Workflow Configuration

The test uses `SDXLRCworkflow.json` (RunComfy version) which includes:

- **Node 39**: Prompt (from `global_prompt` in session.json)
- **Node 5**: Resolution (width/height from session.json)
- **Node 40**: Steps (from session.json)
- **Node 41**: Depth Strength (from `depth_influence`)
- **Node 42**: Canny Strength (from `silhouette_influence`)

All parameters are dynamically injected from your Blender session data.

## API Endpoints

The test system exposes these endpoints:

- `POST /runcomfy/create_deployment` - Create a new cloud deployment
- `GET /runcomfy/deployments` - List all deployments
- `DELETE /runcomfy/deployment/{id}` - Delete a deployment
- `POST /runcomfy/send_workflow` - Send a workflow for generation
- `GET /runcomfy/status/{deployment_id}/{request_id}` - Check request status
- `GET /runcomfy/result/{deployment_id}/{request_id}` - Get completed results

## Managing Deployments

### List Deployments

Click **"Refresh Deployments"** to see all your active deployments with:
- Name
- Deployment ID
- Hardware configuration
- Instance scaling settings
- Creation date

### Delete Deployments

Click the red **"Delete"** button on any deployment to remove it and stop billing.

**Warning**: Deleting a deployment is permanent and cannot be undone.

## Cost Considerations

- **Hobby Plan**: $2.50/hour for AMPERE_48 (A6000 48GB)
- **Pro Plan**: $1.99/hour for AMPERE_48 (20% discount)
- **Scaling**: Set to 0-1 instances (scale to zero when idle)
- **Keep-warm**: 5 minutes (300 seconds) after last job

You are only billed for active compute time (cold start + execution + keep-warm).

## Troubleshooting

### "Credentials not found"
- Make sure environment variables are set **before** starting the server
- Restart the server after setting environment variables

### "Deployment creation failed"
- Check your RunComfy account balance
- Verify your API credentials are correct
- Check the server console for detailed error messages

### "Request timeout"
- First-time cold starts can take 3-5 minutes
- Check the status URL directly for detailed progress
- Verify the deployment is enabled

### "Generation failed"
- Check the result data for specific error messages
- Verify the workflow has all required models
- Ensure input data matches the workflow structure

## Architecture

```
Blender Addon (session.json)
    ↓
FastAPI Server (launcher/server.py)
    ↓
RunComfy API (https://api.runcomfy.net)
    ↓
Cloud ComfyUI Instance (SDXLRCworkflow.json)
    ↓
Generated Images (returned via URLs)
```

## Next Steps

After successful testing:
1. Integrate cloud generation into the main workflow
2. Add automatic fallback (cloud when local is unavailable)
3. Implement result caching and local storage
4. Add cloud/local toggle in Blender UI

## References

- **RunComfy Docs**: See `context/RUNCOMFY API DOCS.txt`
- **Workflow ID**: `f0c32b81-8ea3-40bf-887f-d41c9a4d5ef5`
- **RunComfy Dashboard**: https://www.runcomfy.com/
- **Pricing**: https://www.runcomfy.com/pricing

