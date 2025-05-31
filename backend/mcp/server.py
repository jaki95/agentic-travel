import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fast_flights import FlightData, Passengers, Result, get_flights
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MCP_SERVER_PATH = Path(__file__).resolve()

mcp = FastMCP("google-flights-mcp")


@mcp.tool()
async def find_flights_on_date(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: Optional[int] = 1,
    max_stops: Optional[int] = 0,
    round_trip: Optional[bool] = False,
    fare_type: Optional[Literal["economy", "premium-economy", "business", "first"]] = "economy",
) -> Result:
    """
    Get flights on a given date from a given origin to a given destination.

    Args:
        origin (str): The origin airport code.
        destination (str): The destination airport code.
        date (str): The date of the flight in YYYY-MM-DD format.
        passengers (int): The number of passengers.
        max_stops (int): The maximum number of stops.
        fare_type (Literal["economy", "premium-economy", "business", "first"]): The type of fare.

    Returns:
        Result: The result of the flight search.
    """
    if round_trip:
        log = f"Getting flights {origin} <-> {destination} on {departure_date} and {return_date} for {passengers} passengers"
    else:
        log = f"Getting flights {origin} -> {destination} on {departure_date} for {passengers} passengers"
   
    logger.info(log)

    datetime.strptime(departure_date, "%Y-%m-%d")
    if round_trip:
        datetime.strptime(return_date, "%Y-%m-%d")

    flight_data = [
        FlightData(
            date=departure_date,
            from_airport=origin,
            to_airport=destination,
            max_stops=max_stops,
        )
    ]
    
    # Only add return flight if it's a round trip
    if round_trip and return_date:
        flight_data.append(
            FlightData(
                date=return_date,
                from_airport=destination,
                to_airport=origin,
                max_stops=max_stops,
            )
        )

    # Run the blocking get_flights function in a thread pool executor
    # to avoid the "asyncio.run() cannot be called from a running event loop" error
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,  # Use default thread pool executor
        lambda: get_flights(
            flight_data=flight_data,
            passengers=Passengers(adults=passengers),
            trip="round-trip" if round_trip else "one-way",
            seat=fare_type,
            fetch_mode="local",
        ),
    )

    if result and result.flights:
        return result
    else:
        raise Exception("No flights found")
    

if __name__ == "__main__":
    mcp.run(transport="stdio")
