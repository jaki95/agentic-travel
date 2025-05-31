#!/usr/bin/env python3
"""
Scripts for running backend and frontend.
"""

import subprocess
import sys

import uvicorn


def run_backend():
    """Run the Agentic Travel backend API server."""
    print("🚀 Starting Agentic Travel Backend API...")
    print("📍 API: http://localhost:8000")
    print("-" * 40)

    uvicorn.run(
        "backend.api:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )


def run_frontend():
    """Run the Agentic Travel Streamlit frontend."""
    print("🚀 Starting Agentic Travel Frontend...")
    print("📍 Frontend: http://localhost:8501")
    print("-" * 40)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "frontend/app.py",
                "--server.port=8501",
                "--server.address=0.0.0.0",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped")
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend error: {e}")
        sys.exit(1)
