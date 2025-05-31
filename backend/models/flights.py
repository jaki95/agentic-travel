import datetime
import time
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


# Flight data models for structured returns
class FlightSegment(BaseModel):
    """Represents a single flight segment."""

    airline: Optional[str] = Field(
        None, description="Airline name (e.g., 'British Airways')"
    )
    # flight_number: Optional[str] = Field(
    #     None, description="Flight number (e.g., 'BA123')"
    # )
    departure_airport: str = Field(None, description="Departure airport code and name")
    arrival_airport: str = Field(None, description="Arrival airport code and name")
    departure_time: Optional[datetime.time] = Field(
        None, description="Departure time (e.g., 14:30)"
    )
    arrival_time: Optional[datetime.time] = Field(
        None, description="Arrival time (e.g., 18:45)"
    )
    duration: Optional[str] = Field(
        None, description="Flight duration (e.g., '4h 15m')"
    )

    @field_serializer("departure_time")
    def serialize_departure_time(self, value: Optional[datetime.time]) -> Optional[str]:
        """Serialize departure_time to string for JSON compatibility."""
        return value.strftime("%H:%M") if value else None

    @field_serializer("arrival_time")
    def serialize_arrival_time(self, value: Optional[datetime.time]) -> Optional[str]:
        """Serialize arrival_time to string for JSON compatibility."""
        return value.strftime("%H:%M") if value else None


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
    # booking_class: Optional[str] = Field(
    #     None, description="Booking class (Economy, Business, etc.)"
    # )
    # availability: Optional[str] = Field(None, description="Availability information")
    # booking_url: Optional[str] = Field(None, description="URL for booking")


class FlightSearchResults(BaseModel):
    """Structured flight search results."""

    query: str = Field(description="Original search query")
    origin: Optional[str] = Field(None, description="Origin airport and city")
    destination: Optional[str] = Field(None, description="Destination airport and city")
    departure_date: Optional[datetime.date] = Field(None, description="Departure date")
    return_date: Optional[datetime.date] = Field(
        None, description="Return date (if round trip)"
    )
    passengers: Optional[int] = Field(None, description="Number of passengers")
    flight_options: list[FlightOption] = Field(
        default_factory=list, description="Available flight options"
    )
    search_timestamp: Optional[datetime.datetime] = Field(
        None, description="When the search was performed"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if search failed"
    )
