from typing import Optional

from pydantic import BaseModel, Field


class Flight(BaseModel):
    """Flat model for displaying individual flight options in the frontend."""

    origin: str = Field("", description="Origin airport and city")
    destination: str = Field("", description="Destination airport and city")
    departure_date: str = Field("", description="Departure date as string")
    departure_time: str = Field("", description="Departure time")
    arrival_time: str = Field("", description="Arrival time")
    duration: str = Field("", description="Total flight duration")
    price: str = Field("", description="Flight price")
    currency: str = Field("", description="Currency code")
    airline: str = Field("", description="Main airline")
    route: str = Field("", description="Route (e.g., 'LCY -> LIN')")
    stops: int = Field(0, description="Number of stops")
    direction: Optional[str] = Field(
        None,
        description="Flight direction for round trips: 'outbound', 'return', or None for one-way",
    )
    passengers: Optional[int] = Field(None, description="Number of passengers")


class FlightSearchResults(BaseModel):
    """Wrapper model for a list of flight display records."""

    flights: list[Flight] = Field(description="List of flight options")
    google_flights_url: Optional[str] = Field(
        None, description="Google Flights URL for this search"
    )
