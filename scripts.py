#!/usr/bin/env python3
"""
Scripts for running backend and frontend.
"""

import subprocess
import sys
import uvicorn
from pathlib import Path


def setup_mcp_server():
    """Setup and check MCP server dependencies."""

    def check_mcp_server():
        """Check if the MCP server exists and is properly configured."""
        # Get the MCP server path relative to project root
        project_root = Path(__file__).parent
        mcp_path = project_root.parent / "Google-Flights-MCP-Server"
        server_file = mcp_path / "server.py"

        print("🔍 Checking MCP Server setup...")

        if not mcp_path.exists():
            print("❌ Google Flights MCP Server directory not found")
            print(f"   Expected location: {mcp_path.absolute()}")
            print("\n📥 Please clone the repository:")
            print("   git clone <repository-url> ../Google-Flights-MCP-Server")
            return False

        if not server_file.exists():
            print("❌ server.py not found in MCP Server directory")
            print(f"   Expected file: {server_file.absolute()}")
            return False

        print("✅ MCP Server directory found")
        return True

    def install_mcp_dependencies():
        """Install dependencies for the MCP server."""
        # Get the MCP server path relative to project root
        project_root = Path(__file__).parent
        mcp_path = project_root.parent / "Google-Flights-MCP-Server"

        print("📦 Installing MCP Server dependencies...")

        # Check for requirements.txt or pyproject.toml in MCP server
        requirements_file = mcp_path / "requirements.txt"
        pyproject_file = mcp_path / "pyproject.toml"

        try:
            if pyproject_file.exists():
                print("   Found pyproject.toml, installing with uv...")
                subprocess.run(
                    ["uv", "pip", "install", "-e", str(mcp_path)],
                    check=True,
                    cwd=mcp_path,
                )
            elif requirements_file.exists():
                print("   Found requirements.txt, installing...")
                subprocess.run(
                    ["uv", "pip", "install", "-r", str(requirements_file)], check=True
                )
            else:
                print(
                    "   No requirements file found, installing common dependencies..."
                )
                # Install common dependencies that are usually needed
                subprocess.run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "selectolax",
                        "requests",
                        "beautifulsoup4",
                        "lxml",
                    ],
                    check=True,
                )

            print("✅ MCP Server dependencies installed")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install MCP dependencies: {e}")
            return False

    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ uv package manager not found")
        print(
            "   Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )
        return False

    # Check MCP server and install dependencies if needed
    if not check_mcp_server():
        return False

    return install_mcp_dependencies()


def run_backend():
    """Run the Flight Finder backend API server."""
    print("🚀 Starting Flight Finder Backend API...")
    print("📍 API will be available at: http://localhost:8000")
    print("📖 API documentation at: http://localhost:8000/docs")
    print("🔄 Auto-reload enabled for development")
    print("-" * 50)

    # Automatically setup MCP server before starting
    print("🔧 Setting up MCP Server dependencies...")
    if not setup_mcp_server():
        print("❌ MCP Server setup failed. Backend may not work properly.")
        print("   Please fix the MCP server setup and try again.")
        sys.exit(1)

    print("✅ MCP Server setup complete!")
    print("-" * 50)

    uvicorn.run(
        "backend.api:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )


def run_frontend():
    """Run the Flight Finder Streamlit frontend."""
    print("🚀 Starting Flight Finder Frontend...")
    print("📍 Frontend will be available at: http://localhost:8501")
    print("🔄 Auto-reload enabled for development")
    print("-" * 50)

    # Run streamlit
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
        print("\n👋 Frontend stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running frontend: {e}")
        sys.exit(1)
