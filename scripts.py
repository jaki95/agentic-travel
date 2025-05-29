#!/usr/bin/env python3
"""
Scripts for running backend and frontend.
"""

import subprocess
import sys
import uvicorn
from pathlib import Path


def run_command(cmd, timeout=30, silent=False):
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=True
        )
        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        if not silent:
            print(f"❌ Command failed: {' '.join(cmd)}")
        return False


def check_and_install_uv():
    """Ensure uv package manager is available."""
    if not run_command(["uv", "--version"], silent=True):
        print("❌ uv package manager not found")
        print(
            "   Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )
        return False
    return True


def setup_dev_dependencies():
    """Install development dependencies if needed."""
    print("🔍 Checking dev dependencies...")

    if run_command(["fastmcp", "--version"], silent=True):
        print("✅ Dev dependencies available")
        return True

    print("📦 Installing dev dependencies...")
    if run_command(["uv", "sync", "--dev"]):
        print("✅ Dev dependencies installed")
        return True
    return False


def check_mcp_server():
    """Verify MCP server directory and files exist."""
    project_root = Path(__file__).parent
    mcp_path = project_root.parent / "Google-Flights-MCP-Server"
    server_file = mcp_path / "server.py"

    print("🔍 Checking MCP Server...")

    if not mcp_path.exists():
        print("❌ Google Flights MCP Server directory not found")
        print(f"   Expected: {mcp_path.absolute()}")
        print(
            "   Please clone: git clone <repository-url> ../Google-Flights-MCP-Server"
        )
        return False

    if not server_file.exists():
        print(f"❌ server.py not found: {server_file.absolute()}")
        return False

    print("✅ MCP Server found")
    return True


def install_mcp_dependencies():
    """Install MCP server dependencies."""
    project_root = Path(__file__).parent
    mcp_path = project_root.parent / "Google-Flights-MCP-Server"

    print("📦 Installing MCP dependencies...")

    # Install from requirements.txt if it exists
    requirements_file = mcp_path / "requirements.txt"
    if requirements_file.exists():
        if not run_command(["uv", "pip", "install", "-r", str(requirements_file)]):
            return False

    # Install MCP server package if pyproject.toml exists
    pyproject_file = mcp_path / "pyproject.toml"
    if pyproject_file.exists():
        if not run_command(["uv", "pip", "install", "-e", str(mcp_path)]):
            return False

    # Install playwright browsers
    print("📦 Installing playwright browsers...")
    run_command(
        ["uv", "run", "playwright", "install", "chromium"], timeout=120, silent=True
    )

    print("✅ MCP dependencies installed")
    return True


def setup_mcp_server():
    """Setup and verify MCP server is ready."""
    if not check_and_install_uv():
        return False

    if not setup_dev_dependencies():
        return False

    if not check_mcp_server():
        return False

    return install_mcp_dependencies()


def run_backend():
    """Run the Agentic Travel backend API server."""
    print("🚀 Starting Agentic Travel Backend API...")
    print("📍 API: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs")
    print("-" * 40)

    print("🔧 Setting up MCP Server...")
    if not setup_mcp_server():
        print("❌ MCP Server setup failed")
        sys.exit(1)

    print("✅ Setup complete!")
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
