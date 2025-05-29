from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging

from .flight_service import FlightService

from .orchestrator import TravelOrchestrator
from .models import TravelItinerary, FlightSearchResults

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

# Initialize services
flight_service = FlightService()
travel_orchestrator = TravelOrchestrator()


class FlightSearchRequest(BaseModel):
    query: str


class TravelPlanRequest(BaseModel):
    query: str


class FlightSearchResponse(BaseModel):
    results: str
    success: bool
    error: Optional[str] = None


class StructuredFlightSearchResponse(BaseModel):
    results: FlightSearchResults
    success: bool
    error: Optional[str] = None


class TravelPlanResponse(BaseModel):
    results: TravelItinerary
    success: bool
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Agentic Travel API is running"}


@app.post("/search", response_model=FlightSearchResponse)
async def search_flights(request: FlightSearchRequest):
    """
    Search for flights using natural language query (single flight search, returns text).

    Example queries:
    - "Find one way flight from STN to SAW on 11 September 2025"
    - "Round trip from London to Paris next week"
    - "Cheapest flights from NYC to LAX in December"
    """
    try:
        logger.info(f"Searching flights with query: {request.query}")
        results = await flight_service.search_flights(request.query)

        return FlightSearchResponse(results=results, success=True)

    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}")
        return FlightSearchResponse(results="", success=False, error=str(e))


@app.post("/search/structured", response_model=StructuredFlightSearchResponse)
async def search_flights_structured(request: FlightSearchRequest):
    """
    Search for flights and return structured data with parsed flight information.

    This endpoint returns JSON with structured flight data including:
    - Parsed origins and destinations
    - Flight options with airlines, times, prices
    - Structured segments and routing information
    - Metadata like search timestamp

    Example queries:
    - "Find one way flight from STN to SAW on 11 September 2025"
    - "Round trip from London to Paris next week"
    - "Cheapest flights from NYC to LAX in December"
    """
    try:
        logger.info(f"Searching structured flights with query: {request.query}")
        results = await flight_service.search_flights_structured(request.query)

        return StructuredFlightSearchResponse(results=results, success=True)

    except Exception as e:
        logger.error(f"Error searching structured flights: {str(e)}")
        return StructuredFlightSearchResponse(
            results=FlightSearchResults(query=request.query, error_message=str(e)),
            success=False,
            error=str(e),
        )


@app.post("/plan", response_model=TravelPlanResponse)
async def plan_travel(request: TravelPlanRequest):
    """
    Plan complex travel itineraries using multi-agent orchestration.

    This endpoint can handle complex travel requests that may require:
    - Multiple flight searches
    - Multi-city trips
    - Complex itineraries
    - Travel planning with multiple requirements

    Returns structured itinerary data with recommendations.

    Example queries:
    - "I need to fly from NYC to London on March 15, then London to Paris on March 20, and back to NYC on March 25"
    - "Plan a business trip for 3 people from San Francisco to Tokyo and Seoul, departing next month"
    - "Find flights for a family vacation: 2 adults and 2 children from LAX to multiple European cities"
    - "I need to visit Boston, Chicago, and Miami for work meetings next week"
    """
    try:
        logger.info(f"Planning travel with orchestrator: {request.query}")
        results = await travel_orchestrator.orchestrate_travel_search(request.query)

        return TravelPlanResponse(results=results, success=True)

    except Exception as e:
        logger.error(f"Error planning travel: {str(e)}")
        return TravelPlanResponse(
            results=TravelItinerary(
                original_query=request.query,
                recommendations=f"Error occurred: {str(e)}",
            ),
            success=False,
            error=str(e),
        )


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "agentic-travel-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
