from pydantic import BaseModel, Field
from typing import Optional


# Flight data models for structured returns
class FlightSegment(BaseModel):
    """Represents a single flight segment."""

    airline: Optional[str] = Field(
        None, description="Airline name (e.g., 'British Airways')"
    )
    flight_number: Optional[str] = Field(
        None, description="Flight number (e.g., 'BA123')"
    )
    departure_airport: Optional[str] = Field(
        None, description="Departure airport code or name"
    )
    arrival_airport: Optional[str] = Field(
        None, description="Arrival airport code or name"
    )
    departure_time: Optional[str] = Field(
        None, description="Departure time (e.g., '14:30')"
    )
    arrival_time: Optional[str] = Field(
        None, description="Arrival time (e.g., '18:45')"
    )
    duration: Optional[str] = Field(
        None, description="Flight duration (e.g., '4h 15m')"
    )
    aircraft: Optional[str] = Field(None, description="Aircraft type")


class FlightOption(BaseModel):
    """Represents a complete flight option (may include multiple segments)."""

    price: Optional[str] = Field(None, description="Flight price (e.g., '299')")
    currency: Optional[str] = Field(
        None, description="Currency code (e.g., 'USD', 'EUR')"
    )
    total_duration: Optional[str] = Field(
        None, description="Total travel time including layovers"
    )
    stops: Optional[int] = Field(None, description="Number of stops (0 for direct)")
    segments: list[FlightSegment] = Field(
        default_factory=list, description="List of flight segments"
    )
    booking_class: Optional[str] = Field(
        None, description="Booking class (Economy, Business, etc.)"
    )
    availability: Optional[str] = Field(None, description="Availability information")
    booking_url: Optional[str] = Field(None, description="URL for booking")


class FlightSearchResults(BaseModel):
    """Structured flight search results."""

    query: str = Field(description="Original search query")
    origin: Optional[str] = Field(None, description="Origin airport or city")
    destination: Optional[str] = Field(None, description="Destination airport or city")
    departure_date: Optional[str] = Field(None, description="Departure date")
    return_date: Optional[str] = Field(None, description="Return date (if round trip)")
    passengers: Optional[int] = Field(None, description="Number of passengers")
    flight_options: list[FlightOption] = Field(
        default_factory=list, description="Available flight options"
    )
    search_timestamp: Optional[str] = Field(
        None, description="When the search was performed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if search failed"
    )


class TravelItinerary(BaseModel):
    """Complete travel itinerary with multiple flight searches."""

    original_query: str = Field(description="Original travel request")
    flight_searches: list[FlightSearchResults] = Field(
        default_factory=list, description="Flight search results"
    )
    recommendations: Optional[str] = Field(
        None, description="Travel recommendations and summary"
    )
    total_estimated_cost: Optional[str] = Field(
        None, description="Total estimated cost"
    )
    itinerary_summary: Optional[str] = Field(
        None, description="Brief itinerary summary"
    )
