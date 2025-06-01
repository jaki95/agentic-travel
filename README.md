# ✈️ Agentic Travel

A flight search application powered by AI that allows you to find flights using natural language queries.

## Quick Start

### Running the Application

1. **Start the backend API**
   ```bash
   uv run backend
   ```
   The API will be available at http://localhost:8000

2. **Start the frontend** (in a new terminal)
   ```bash
   uv run frontend
   ```
   The web app will be available at http://localhost:8501

## Architecture

The application consists of several components:

- **Backend** (`backend/`): FastAPI-based REST API that handles flight search logic using CrewAI multi-agent orchestration
- **Frontend** (`frontend/`): Streamlit web application providing a user-friendly interface
- **Data** (`data/`): Contains airport codes database for validation and lookup
- **Scripts** (`scripts.py`): Utility scripts for running backend, frontend, and setting up MCP server
  