from typing import Optional

from pydantic import BaseModel

from backend.models.flights import Flight


class FlightSearchRequest(BaseModel):
    query: str


class FlightSearchResponse(BaseModel):
    results: list[Flight]
    success: bool
    error: Optional[str] = None
    summary: Optional[str] = None
    duration_seconds: Optional[float] = None
