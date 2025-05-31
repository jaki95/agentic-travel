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


class AgenticFlightData(FlightData):
    direction: Optional[Literal["outbound", "return"]] = None
    route_segment: Optional[str] = None


async def _get_flight_result(flight_data_list, passengers, fare_type, loop):
    """Helper to get flight results and handle errors"""
    result = await loop.run_in_executor(
        None,
        lambda: get_flights(
            flight_data=flight_data_list,
            passengers=Passengers(adults=passengers),
            trip="one-way",
            seat=fare_type,
            fetch_mode="local",
        ),
    )
    if not result or not result.flights:
        return None
    return result


def _add_flight_metadata(flights, direction, route_segment):
    """Helper to add metadata to flights"""
    for flight in flights:
        setattr(flight, "direction", direction)
        setattr(flight, "route_segment", route_segment)


@mcp.tool()
async def find_flights_on_date(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: Optional[int] = 1,
    max_stops: Optional[int] = 0,
    round_trip: Optional[bool] = False,
    fare_type: Optional[
        Literal["economy", "premium-economy", "business", "first"]
    ] = "economy",
) -> AgenticFlightData:
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
        AgenticFlightData: The result of the flight search.
    """
    if round_trip:
        log = f"Getting flights {origin} <-> {destination} on {departure_date} and {return_date} for {passengers} passengers"
    else:
        log = f"Getting flights {origin} -> {destination} on {departure_date} for {passengers} passengers"

    logger.info(log)

    # Validate dates
    datetime.strptime(departure_date, "%Y-%m-%d")
    if round_trip:
        datetime.strptime(return_date, "%Y-%m-%d")

    loop = asyncio.get_running_loop()

    if round_trip and return_date:
        logger.info("Making separate one-way requests for round-trip")

        # Create flight data for both directions
        outbound_data = [
            FlightData(
                date=departure_date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            )
        ]
        return_data = [
            FlightData(
                date=return_date,
                from_airport=destination,
                to_airport=origin,
                max_stops=max_stops,
            )
        ]

        # Get both results concurrently
        outbound_result, return_result = await asyncio.gather(
            _get_flight_result(outbound_data, passengers, fare_type, loop),
            _get_flight_result(return_data, passengers, fare_type, loop),
        )

        if not outbound_result or not return_result:
            raise Exception("No outbound or return flights found")

        # Add metadata and combine
        _add_flight_metadata(
            outbound_result.flights, "outbound", f"{origin}→{destination}"
        )
        _add_flight_metadata(return_result.flights, "return", f"{destination}→{origin}")

        outbound_result.flights.extend(return_result.flights)
        logger.info(f"Combined {len(outbound_result.flights)} flights")
        return outbound_result

    else:
        # One-way flight
        flight_data = [
            FlightData(
                date=departure_date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            )
        ]
        result = await _get_flight_result(flight_data, passengers, fare_type, loop)

        if not result:
            raise Exception("No flights found")

        _add_flight_metadata(result.flights, None, f"{origin}→{destination}")
        return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
