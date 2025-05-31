import asyncio
import logging
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
    Search for flights using the CrewAI orchestrator.
    """
    try:
        logger.info(f"Orchestrating flight search with query: {request.query}")

        def run_flow():
            flow = FlightSearchFlow(request.query)
            flow.kickoff()
            return flow.state.search_results

        with ThreadPoolExecutor() as executor:
            results = await asyncio.get_event_loop().run_in_executor(executor, run_flow)

        # Flatten FlightSearchResults objects to FlightDisplayRecord objects
        flight_records = []
        if results:
            for flight_search_result in results:
                if hasattr(flight_search_result, "flights"):
                    flight_records.extend(flight_search_result.flights)

        # Create summary
        total_flight_options = len([r for r in flight_records])
        total_searches = len(results) if results else 0

        summary = f"Found {total_flight_options} flight options from {total_searches} searches"

        # Add route information if available
        unique_routes = set(r.route for r in flight_records if r.route)
        if unique_routes:
            summary += f" for routes: {', '.join(sorted(unique_routes))}"

        return FlightSearchResponse(
            results=flight_records, success=True, summary=summary
        )

    except Exception as e:
        logger.error(f"Error in flight search: {str(e)}")
        return FlightSearchResponse(results=[], success=False, error=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "agentic-travel-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
