"""
Style Engine Launcher
Main entry point for the FastAPI server that bridges Blender and ComfyUI.
"""

import uvicorn
import sys
from pathlib import Path

# Add the launcher directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Start the FastAPI server."""
    print("=" * 60)
    print("Style Engine - AI Generation Bridge Server")
    print("=" * 60)
    print("\n[INFO] Starting server on http://localhost:8000")
    print("[INFO] API documentation available at http://localhost:8000/docs")
    print("[INFO] Press CTRL+C to stop the server\n")
    
    # Run the FastAPI server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes during development
        log_level="info"
    )


if __name__ == "__main__":
    main()

