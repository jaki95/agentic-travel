from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Individual flight search query."""

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
