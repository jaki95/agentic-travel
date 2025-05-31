import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.flow import FlightSearchFlow
from backend.models.api import FlightSearchRequest, FlightSearchResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Travel API",
    description="API for searching flights using natural language queries with multi-agent orchestration",
    version="1.0.0",
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Agentic Travel API is running"}


@app.post("/search", response_model=FlightSearchResponse)
async def search_flights(request: FlightSearchRequest):
    """
    Search for flights using the new CrewAI orchestrator (returns DataFrame as CSV).

    This is now the main endpoint that uses the orchestrator pattern:
    question -> multiple queries if needed -> MCP execution -> combine -> return DataFrame

    Example queries:
    - "Find one way flight from STN to SAW on 11 September 2025"
    - "Round trip from London to Paris next week"
    - "Multi-city: NYC to Paris Dec 15, Paris to Rome Dec 20, Rome to NYC Dec 25"
    - "Cheapest flights from NYC to LAX in December"
    """
    try:
        logger.info(f"Orchestrating flight search with query: {request.query}")

        def run_flow():
            flow = FlightSearchFlow(request.query)
            flow.kickoff()
            return flow.state.search_results

        with ThreadPoolExecutor() as executor:
            results = await asyncio.get_event_loop().run_in_executor(executor, run_flow)

        # Create a summary
        total_searches = len(results)
        total_flight_options = sum(len(result.flight_options) for result in results)
        successful_searches = len([r for r in results if not r.error_message])

        summary = f"Executed {total_searches} flight searches ({successful_searches} successful), found {total_flight_options} total flight options"

        # Add route information if available
        unique_routes = set()
        for result in results:
            if result.origin and result.destination:
                unique_routes.add(f"{result.origin} → {result.destination}")

        if unique_routes:
            summary += f" for routes: {', '.join(sorted(unique_routes))}"

        return FlightSearchResponse(results=results, success=True, summary=summary)

    except Exception as e:
        logger.error(f"Error in orchestrated flight search: {str(e)}")
        return FlightSearchResponse(results=[], success=False, error=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "agentic-travel-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
