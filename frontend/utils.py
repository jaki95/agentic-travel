import re
from typing import Optional

import pandas as pd
import streamlit as st

from config import EXPECTED_MULTI_CITY_LEGS, PRICE_DECIMAL_PLACES, SUGGESTION_QUERIES


def extract_numeric_prices(prices: pd.Series) -> list[float]:
    """Extract numeric values from price strings."""
    numeric_prices = []
    for price in prices:
        numbers = re.findall(r"\d+\.?\d*", str(price))
        if numbers:
            numeric_prices.append(float(numbers[0]))
    return numeric_prices


def clean_airline_names(df: pd.DataFrame) -> pd.DataFrame:
    """Remove direction markers from airline names for display."""
    if "airline" in df.columns:
        df = df.copy()
        df["airline"] = df["airline"].str.replace(
            r"^\[(OUTBOUND|RETURN)\]\s*", "", regex=True
        )
    return df


def get_flight_type_info(results: pd.DataFrame) -> tuple[bool, bool, int]:
    """Determine flight type characteristics from the results DataFrame."""
    has_outbound = (
        "direction" in results.columns
        and (results["direction"] == "outbound").any()
    )
    has_return = (
        "direction" in results.columns 
        and (results["direction"] == "return").any()
    )
    is_round_trip = has_outbound and has_return
    
    unique_segments = (
        results["route_segment"].nunique()
        if "route_segment" in results.columns
        else 1
    )
    is_multi_city = unique_segments > 2 or (unique_segments == 2 and not is_round_trip)
    
    return is_round_trip, is_multi_city, unique_segments


def get_route_segments(results: pd.DataFrame) -> list[str]:
    """Get all route segments from the results DataFrame."""
    if "route_segment" in results.columns:
        return sorted(results["route_segment"].unique())
    elif "direction" in results.columns:
        # For round-trip flights, use direction as segments
        directions = []
        if (results["direction"] == "outbound").any():
            directions.append("outbound")
        if (results["direction"] == "return").any():
            directions.append("return")
        return directions
    else:
        # Single route
        return ["single"]


def calculate_combined_route_prices(results: pd.DataFrame) -> Optional[dict]:
    """
    Calculate combined prices for multi-segment routes.
    Returns min, max, and avg combined prices, or None if not applicable.
    """
    if "price" not in results.columns or not results["price"].notna().any():
        return None
    
    segments = get_route_segments(results)
    
    # For single segment routes, return individual flight prices
    if len(segments) == 1:
        return _calculate_single_segment_prices(results)
    
    # For multi-segment routes, calculate combinations
    return _calculate_multi_segment_prices(results, segments)


def _calculate_single_segment_prices(results: pd.DataFrame) -> Optional[dict]:
    """Calculate prices for single segment routes."""
    price_df = results[results["price"].notna() & (results["price"] != "-")]
    if price_df.empty:
        return None
    
    try:
        numeric_prices = extract_numeric_prices(price_df["price"])
        if not numeric_prices:
            return None
            
        return {
            "min_price": min(numeric_prices),
            "max_price": max(numeric_prices),
            "avg_price": sum(numeric_prices) / len(numeric_prices),
            "price_type": "Price"
        }
    except Exception:
        return None


def _calculate_multi_segment_prices(results: pd.DataFrame, segments: list[str]) -> Optional[dict]:
    """Calculate combined prices for multi-segment routes."""
    segment_prices = {}
    
    for segment in segments:
        if segment in ["outbound", "return"]:
            # Handle round-trip using direction field
            segment_data = results[results["direction"] == segment]
        else:
            # Handle multi-city using route_segment field
            segment_data = results[results["route_segment"] == segment]
        
        if segment_data.empty:
            continue
            
        segment_price_df = segment_data[
            segment_data["price"].notna() & (segment_data["price"] != "-")
        ]
        
        if segment_price_df.empty:
            continue
            
        try:
            numeric_prices = extract_numeric_prices(segment_price_df["price"])
            if numeric_prices:
                segment_prices[segment] = {
                    "min": min(numeric_prices),
                    "max": max(numeric_prices),
                    "prices": numeric_prices
                }
        except Exception:
            continue
    
    if not segment_prices or len(segment_prices) != len(segments):
        return None
    
    # Calculate combined prices
    min_combined = sum(segment_prices[seg]["min"] for seg in segments)
    max_combined = sum(segment_prices[seg]["max"] for seg in segments)
    
    # Calculate average of all possible combinations
    all_combinations = _generate_price_combinations(segment_prices, segments)
    avg_combined = sum(all_combinations) / len(all_combinations) if all_combinations else min_combined
    
    # Determine price type label
    if len(segments) == 2 and "outbound" in segments and "return" in segments:
        price_type = "Round-Trip"
    else:
        price_type = f"{len(segments)}-Segment Trip"
    
    return {
        "min_price": min_combined,
        "max_price": max_combined,
        "avg_price": avg_combined,
        "price_type": price_type
    }


def _generate_price_combinations(segment_prices: dict, segments: list[str]) -> list[float]:
    """Generate all possible price combinations for segments."""
    if not segments:
        return []
    
    if len(segments) == 1:
        return segment_prices[segments[0]]["prices"]
    
    # Recursively generate combinations
    first_segment = segments[0]
    remaining_segments = segments[1:]
    
    remaining_combinations = _generate_price_combinations(segment_prices, remaining_segments)
    
    combinations = []
    for price in segment_prices[first_segment]["prices"]:
        if remaining_combinations:
            for remaining_price in remaining_combinations:
                combinations.append(price + remaining_price)
        else:
            combinations.append(price)
    
    return combinations


def display_price_metrics(results: pd.DataFrame) -> None:
    """Display unified price statistics for any route type."""
    price_data = calculate_combined_route_prices(results)
    
    if price_data:
        _display_price_columns(
            price_data["min_price"],
            price_data["max_price"], 
            price_data["avg_price"],
            price_data["price_type"]
        )


def _display_price_columns(min_price: float, max_price: float, avg_price: float, price_type: str) -> None:
    """Display price metrics in three columns."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(f"💰 Lowest {price_type}", f"£{min_price:.{PRICE_DECIMAL_PLACES}f}")
    with col2:
        st.metric(f"📊 Average {price_type}", f"£{avg_price:.{PRICE_DECIMAL_PLACES}f}")
    with col3:
        st.metric(f"📈 Highest {price_type}", f"£{max_price:.{PRICE_DECIMAL_PLACES}f}")


def display_flight_table(results_display: pd.DataFrame) -> None:
    """Display a flight table with consistent formatting."""
    if results_display.empty:
        st.warning("No flights to display.")
        return

    # Define the preferred column order and only show available columns
    preferred_columns = [
        "route",
        "departure_date", 
        "departure_time",
        "arrival_time",
        "duration",
        "price",
        "airline",
        "stops",
    ]
    
    available_columns = [col for col in preferred_columns if col in results_display.columns]
    
    if available_columns:
        results_to_show = results_display[available_columns]
        column_renames = {
            "route": "Route",
            "departure_date": "Date",
            "departure_time": "Departure", 
            "arrival_time": "Arrival",
            "duration": "Duration",
            "price": "Price",
            "airline": "Airline",
            "stops": "Stops",
        }
        results_to_show = results_to_show.rename(
            columns={k: v for k, v in column_renames.items() if k in results_to_show.columns}
        )
    else:
        results_to_show = results_display
        
    st.dataframe(results_to_show, use_container_width=True, hide_index=True)


def display_flight_results(results: pd.DataFrame, summary: Optional[str] = None) -> None:
    """Display search results in a clean table format."""
    if results.empty:
        st.warning("No flights found.")
        return

    try:
        # Display summary if provided
        if summary:
            st.write(summary)

        is_round_trip, is_multi_city, unique_segments = get_flight_type_info(results)

        # Display unified price metrics for all route types
        display_price_metrics(results)

        if is_round_trip:
            _display_round_trip_results(results)
        elif is_multi_city:
            _display_multi_city_results(results, unique_segments)
        else:
            _display_one_way_results(results)

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")


def _display_round_trip_results(results: pd.DataFrame) -> None:
    """Display round-trip flight results."""
    st.subheader("🔄 Round Trip Flights")

    # Split into outbound and return flights
    outbound_flights = clean_airline_names(results[results["direction"] == "outbound"])
    return_flights = clean_airline_names(results[results["direction"] == "return"])

    # Display flight sections
    st.markdown("#### ✈️ Outbound Flights")
    display_flight_table(outbound_flights)

    st.markdown("#### 🔙 Return Flights")
    display_flight_table(return_flights)


def _display_multi_city_results(results: pd.DataFrame, unique_segments: int) -> None:
    """Display multi-city flight results."""
    st.subheader("🗺️ Multi-City Trip")

    if "route_segment" in results.columns:
        _display_multi_city_segments(results, unique_segments)
    else:
        # Fallback if route_segment not available
        display_flight_table(results)


def _display_multi_city_segments(results: pd.DataFrame, unique_segments: int) -> None:
    """Display individual segments of a multi-city trip."""
    segments = results["route_segment"].unique()
    
    # Check for incomplete multi-city trips
    if unique_segments < EXPECTED_MULTI_CITY_LEGS:
        st.info(f"ℹ️ Showing {unique_segments} available leg(s) of your multi-city trip.")

    for i, segment in enumerate(segments, 1):
        segment_flights = results[results["route_segment"] == segment]
        segment_flights = clean_airline_names(segment_flights)
        
        st.markdown(f"#### Leg {i}: {segment}")
        display_flight_table(segment_flights)


def _display_one_way_results(results: pd.DataFrame) -> None:
    """Display one-way flight results."""
    st.subheader("✈️ Flight Options")
    display_flight_table(results)


def render_suggestion_buttons() -> None:
    """Render suggestion buttons for common queries."""
    st.markdown("##### 💡 Try these examples:")
    
    cols = st.columns(len(SUGGESTION_QUERIES))
    for i, suggestion_text in enumerate(SUGGESTION_QUERIES):
        if cols[i].button(suggestion_text, key=f"suggestion_{i}"):
            st.session_state.query_text = suggestion_text


def handle_search_results(result: dict) -> None:
    """Handle and display search results."""
    if result.get("success"):
        results_obj = result.get("results")
        st.header("📋 Search Results")

        if results_obj and results_obj.results:
            # Convert results to DataFrame
            list_of_flat_records = [record.model_dump() for record in results_obj.results]
            df = pd.DataFrame(list_of_flat_records)
        else:
            df = pd.DataFrame()

        summary = results_obj.summary if results_obj else "No summary available."
        display_flight_results(df, summary)
    else:
        error_message = result.get("error", "Unknown error")
        st.error(f"❌ Search failed: {error_message}")
