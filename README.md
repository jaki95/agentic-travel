# ✈️ Agentic Travel

A flight search application powered by AI that allows you to find flights using natural language queries.

## 🚀 Quick Start

### Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd agentic-travel
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Clone and setup the MCP server** (required for flight search)
   ```bash
   # Clone the Google Flights MCP Server to the parent directory
   cd ..
   git clone <google-flights-mcp-server-url> Google-Flights-MCP-Server
   cd agentic-travel
   
   # Setup MCP server dependencies (this will be done automatically when starting the backend)
   uv run setup-mcp
   ```

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

## 🏗️ Architecture

The application consists of several components:

- **Backend** (`backend/`): FastAPI-based REST API that handles flight search logic using CrewAI multi-agent orchestration
- **Frontend** (`frontend/`): Streamlit web application providing a user-friendly interface
- **Data** (`data/`): Contains airport codes database for validation and lookup
- **Scripts** (`scripts.py`): Utility scripts for running backend, frontend, and setting up MCP server

## 🔧 Development

### MCP Server Setup

The application uses a Google Flights MCP (Model Context Protocol) Server for flight data. The setup is automated, but you can manually set it up:

```bash
# The MCP server should be cloned to: ../Google-Flights-MCP-Server/
# Dependencies are automatically installed when you run the backend

# Manual setup (if needed):
uv run setup-mcp
```


```

## 📝 API Usage

The backend API provides the following endpoints:

### Health Check

```bash
curl "http://localhost:8000/health"
```

### Search Flights

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "Find flights from LHR to CDG on 2025-03-15"}'
```

### Example Queries

The AI agent can handle various natural language queries:

- "Find one way flight from STN to SAW on 11 September 2025"
- "Round trip from London to Paris next week"
- "Multi-city: NYC to Paris Dec 15, Paris to Rome Dec 20, Rome to NYC Dec 25"
- "Cheapest flights from NYC to LAX in December"
