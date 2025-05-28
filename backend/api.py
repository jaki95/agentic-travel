from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging

from .flight_service import FlightService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Travel API",
    description="API for searching flights using natural language queries",
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

# Initialize flight service
flight_service = FlightService()


class FlightSearchRequest(BaseModel):
    query: str


class FlightSearchResponse(BaseModel):
    results: str
    success: bool
    error: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Agentic Travel API is running"}


@app.post("/search", response_model=FlightSearchResponse)
async def search_flights(request: FlightSearchRequest):
    """
    Search for flights using natural language query.

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


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "flight-finder-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
