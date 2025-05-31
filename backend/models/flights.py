from typing import Optional

from pydantic import BaseModel, Field


class FlightDisplayRecord(BaseModel):
    """Flat model for displaying individual flight options in the frontend."""

    # Search context
    origin: Optional[str] = Field(None, description="Origin airport and city")
    destination: Optional[str] = Field(None, description="Destination airport and city")
    departure_date: Optional[str] = Field(None, description="Departure date as string")
    return_date: Optional[str] = Field(None, description="Return date as string")
    passengers: Optional[int] = Field(None, description="Number of passengers")

    # Flight option details
    price: Optional[str] = Field(None, description="Flight price")
    currency: Optional[str] = Field(None, description="Currency code")
    airline: Optional[str] = Field(None, description="Main airline")
    route: Optional[str] = Field(None, description="Route (e.g., 'LCY -> LIN')")
    stops: Optional[int] = Field(None, description="Number of stops")
    departure_time: Optional[str] = Field(None, description="Departure time")
    arrival_time: Optional[str] = Field(None, description="Arrival time")
    duration: Optional[str] = Field(None, description="Total flight duration")


class FlightSearchResults(BaseModel):
    """Wrapper model for a list of flight display records."""

    flights: list[FlightDisplayRecord] = Field(description="List of flight options")
