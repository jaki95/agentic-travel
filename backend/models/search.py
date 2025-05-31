import uuid

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Individual flight search query."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the search query",
    )

    origin: str = Field(description="Origin airport/city")
    destination: str = Field(description="Destination airport/city")
    departure_date: str = Field(description="Departure date")
    return_date: str = Field(None, description="Return date if round trip")
    passengers: int = Field(default=1, description="Number of passengers")
    search_type: str = Field(default="one_way", description="one_way or round_trip")


class QueryBreakdown(BaseModel):
    """Breakdown of travel query into individual searches."""

    searches: list[SearchQuery] = Field(
        description="List of individual flight searches needed"
    )
