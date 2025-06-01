import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fast_flights import FlightData, Passengers, Result, create_filter, get_flights
from mcp.server.fastmcp import FastMCP

from backend.models.flights import Flight, FlightSearchResults

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MCP_SERVER_PATH = Path(__file__).resolve()

mcp = FastMCP("google-flights-mcp")


class AgenticFlightData(FlightData):
    direction: Optional[Literal["outbound", "return"]] = None
    route_segment: Optional[str] = None


async def _get_flight_result(flight_data_list, passengers, fare_type, loop) -> Result:
    """Helper to get flight results and handle errors with multiple fallback modes"""

    # Try different fetch modes in order of preference
    fetch_modes = ["local", "fallback", "server"]

    for fetch_mode in fetch_modes:
        try:
            logger.info(f"Attempting flight search with fetch_mode: {fetch_mode}")

            try:
                result: Result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: get_flights(
                            flight_data=flight_data_list,
                            passengers=Passengers(adults=passengers),
                            trip="one-way",
                            seat=fare_type,
                            fetch_mode=fetch_mode,
                        ),
                    ),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout after 10 seconds with {fetch_mode} mode")
                continue

            if result and result.flights:
                logger.info(
                    f"Successfully retrieved {len(result.flights)} flights with {fetch_mode} mode"
                )
                return result
            else:
                logger.warning(
                    f"No flights found with {fetch_mode} mode, trying next option"
                )
        except Exception as e:
            logger.warning(f"Error with {fetch_mode} mode: {str(e)}")
            if fetch_mode == fetch_modes[-1]:  # Last mode, re-raise the error
                raise e
            continue

    # If all modes fail, return empty result
    logger.error("All fetch modes failed, returning empty result")
    return Result(flights=[])


def _generate_google_flights_url(
    origin,
    destination,
    departure_date,
    return_date,
    passengers,
    fare_type,
    round_trip,
    max_stops,
    currency="USD",
):
    """Helper to generate Google Flights URL"""
    if round_trip and return_date:
        # Create flight data for round-trip
        flight_data = [
            FlightData(
                date=departure_date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            ),
            FlightData(
                date=return_date,
                from_airport=destination,
                to_airport=origin,
                max_stops=max_stops,
            ),
        ]
        trip_type = "round-trip"
    else:
        # Create flight data for one-way
        flight_data = [
            FlightData(
                date=departure_date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            )
        ]
        trip_type = "one-way"

    # Create filter
    filter_obj = create_filter(
        flight_data=flight_data,
        trip=trip_type,
        seat=fare_type,
        passengers=Passengers(
            adults=passengers,
            children=0,
            infants_in_seat=0,
            infants_on_lap=0,
        ),
        max_stops=max_stops,
    )

    # Encode the filter to base64
    b64 = filter_obj.as_b64().decode("utf-8")

    # Construct the Google Flights URL
    url = f"https://www.google.com/travel/flights?tfs={b64}&curr={currency}"
    return url


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
) -> FlightSearchResults:
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
        FlightSearchResults: The result of the flight search with Google Flights URL.
    """
    try:
        if round_trip:
            log = f"Getting flights {origin} <-> {destination} on {departure_date} and {return_date} for {passengers} passengers"
        else:
            log = f"Getting flights {origin} -> {destination} on {departure_date} for {passengers} passengers"

        logger.info(log)

        # Validate dates
        datetime.strptime(departure_date, "%Y-%m-%d")
        if round_trip:
            datetime.strptime(return_date, "%Y-%m-%d")

        # Generate Google Flights URL
        google_flights_url = _generate_google_flights_url(
            origin,
            destination,
            departure_date,
            return_date,
            passengers,
            fare_type,
            round_trip,
            max_stops,
        )
        logger.info(f"Generated Google Flights URL: {google_flights_url}")

        loop = asyncio.get_running_loop()

        outbound_data = [
            FlightData(
                date=departure_date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            )
        ]

        return_data = []
        if round_trip and return_date:
            # Due to current limitations of fast_flights, we need to make separate one-way requests for round-trip
            logger.info("Making separate one-way requests for round-trip")
            return_data = [
                FlightData(
                    date=return_date,
                    from_airport=destination,
                    to_airport=origin,
                    max_stops=max_stops,
                )
            ]

        if return_data:
            # For round trips, get both results concurrently
            outbound_result, return_result = await asyncio.gather(
                _get_flight_result(outbound_data, passengers, fare_type, loop),
                _get_flight_result(return_data, passengers, fare_type, loop),
                return_exceptions=True,  # Don't fail the whole operation if one fails
            )
        else:
            # For one-way trips, just get outbound result
            outbound_result = await _get_flight_result(
                outbound_data, passengers, fare_type, loop
            )
            return_result = None

        search_results: list[FlightSearchResults] = []

        # Handle outbound result
        if isinstance(outbound_result, Exception):
            logger.error(f"Outbound search failed: {outbound_result}")
        elif outbound_result and outbound_result.flights:
            search_results.append(
                _result_to_flight_search_results(
                    outbound_result,
                    origin,
                    destination,
                    departure_date,
                    "outbound",
                    passengers,
                )
            )
        else:
            logger.warning("No outbound flights found")

        # Handle return result
        if return_result:
            if isinstance(return_result, Exception):
                logger.error(f"Return search failed: {return_result}")
            elif return_result.flights:
                search_results.append(
                    _result_to_flight_search_results(
                        return_result,
                        destination,
                        origin,
                        return_date,
                        "return",
                        passengers,
                    )
                )
            else:
                logger.warning("No return flights found")

        # Combine all flights into a single FlightSearchResults object
        all_flights = []
        for result in search_results:
            all_flights.extend(result.flights)

        if not all_flights:
            logger.warning(
                f"No flights found for {origin} -> {destination} on {departure_date}"
            )

        return FlightSearchResults(
            flights=all_flights, google_flights_url=google_flights_url
        )

    except Exception as e:
        logger.error(f"Error in find_flights_on_date: {str(e)}")
        # Return empty result with just the Google Flights URL for manual fallback
        google_flights_url = _generate_google_flights_url(
            origin,
            destination,
            departure_date,
            return_date,
            passengers,
            fare_type,
            round_trip,
            max_stops,
        )
        return FlightSearchResults(flights=[], google_flights_url=google_flights_url)


def _result_to_flight_search_results(
    result: Result,
    origin: str,
    destination: str,
    departure_date: str,
    direction: Literal["outbound", "return"],
    passengers: int,
) -> FlightSearchResults:
    return FlightSearchResults(
        flights=[
            Flight(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                departure_time=flight.departure,
                arrival_time=flight.arrival,
                duration=flight.duration,
                price=flight.price,
                currency="GBP",
                airline=flight.name,
                route=f"{origin}→{destination}",
                stops=flight.stops,
                direction=direction,
                passengers=passengers,
            )
            for flight in result.flights
        ],
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
