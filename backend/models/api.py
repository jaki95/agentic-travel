from typing import Optional

from pydantic import BaseModel

from backend.models.flights import FlightDisplayRecord


class FlightSearchRequest(BaseModel):
    query: str


class FlightSearchResponse(BaseModel):
    results: list[FlightDisplayRecord]
    success: bool
    error: Optional[str] = None
    summary: Optional[str] = None
