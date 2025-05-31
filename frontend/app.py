import re
from datetime import date, datetime, time

import pandas as pd
import requests
import streamlit as st

from backend.models.api import FlightSearchResponse

# Configure the page
st.set_page_config(
    page_title="Agentic Travel",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API configuration
API_BASE_URL = "http://localhost:8000"


def check_api_health() -> bool:
    """Check if the backend API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def search_flights(query: str) -> dict:
    """Send flight search request to the backend API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"query": query},
            timeout=90,
        )
        response.raise_for_status()
        
        return {
            "success": True,
            "results": FlightSearchResponse.model_validate(response.json()),
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out. Please try again.",
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def extract_numeric_prices(prices: pd.Series) -> list[float]:
    """Extract numeric values from price strings."""
    numeric_prices = []
    for price in prices:
        numbers = re.findall(r"\d+\.?\d*", str(price))
        if numbers:
            numeric_prices.append(float(numbers[0]))
    return numeric_prices


def display_price_metrics(
    results: pd.DataFrame,
    is_round_trip: bool = False,
    outbound_flights: pd.DataFrame = None,
    return_flights: pd.DataFrame = None,
) -> None:
    """Display price statistics if price data is available."""
    if "price" not in results.columns or not results["price"].notna().any():
        return

    if (
        is_round_trip
        and outbound_flights is not None
        and return_flights is not None
        and not outbound_flights.empty
        and not return_flights.empty
    ):
        # For round trips, calculate combined prices (outbound + return)
        print("🔄 Calculating round-trip combined prices...")

        # Extract numeric prices from both outbound and return flights
        outbound_prices = extract_numeric_prices(outbound_flights["price"])
        return_prices = extract_numeric_prices(return_flights["price"])

        if not outbound_prices or not return_prices:
            return

        # Create all possible combinations of outbound + return prices
        combined_prices = []
        for out_price in outbound_prices:
            for ret_price in return_prices:
                combined_prices.append(out_price + ret_price)

        if combined_prices:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Lowest Round-Trip", f"£{min(combined_prices):.0f}")
            with col2:
                st.metric(
                    "📊 Average Round-Trip",
                    f"£{sum(combined_prices) / len(combined_prices):.0f}",
                )
            with col3:
                st.metric("📈 Highest Round-Trip", f"£{max(combined_prices):.0f}")
    else:
        # For one-way flights, use individual flight prices
        price_df = results[results["price"].notna() & (results["price"] != "-")]
        if price_df.empty:
            return

        try:
            numeric_prices = extract_numeric_prices(price_df["price"])
            if not numeric_prices:
                return

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Lowest Price", f"£{min(numeric_prices):.0f}")
            with col2:
                st.metric(
                    "📊 Average Price",
                    f"£{sum(numeric_prices) / len(numeric_prices):.0f}",
                )
            with col3:
                st.metric("📈 Highest Price", f"£{max(numeric_prices):.0f}")
        except Exception:
            # Silently fail if price parsing doesn't work
            pass


def display_flight_results(results: pd.DataFrame, summary: str = None) -> None:
    """Display search results in a clean table format."""
    if results.empty:
        st.warning("No flights found.")
        return

    try:
        # Display summary if provided
        if summary:
            st.write(summary)

        # Check for round trip flights using the direction field
        has_outbound = (
            "direction" in results.columns
            and (results["direction"] == "outbound").any()
        )
        has_return = (
            "direction" in results.columns and (results["direction"] == "return").any()
        )
        is_round_trip = has_outbound and has_return

        # Check for multi-city flights using route_segment field
        unique_segments = (
            results["route_segment"].nunique()
            if "route_segment" in results.columns
            else 1
        )
        is_multi_city = unique_segments > 2 or (
            unique_segments == 2 and not is_round_trip
        )

        if is_round_trip:
            st.subheader("🔄 Round Trip Flights")

            # Split into outbound and return flights
            outbound_flights = results[results["direction"] == "outbound"].copy()
            return_flights = results[results["direction"] == "return"].copy()

            # Clean up airline names by removing direction markers for display
            # (Note: direction markers should no longer exist, but keeping this as safety)
            for df in [outbound_flights, return_flights]:
                if "airline" in df.columns:
                    df["airline"] = df["airline"].str.replace(
                        r"^\[OUTBOUND\]\s*", "", regex=True
                    )
                    df["airline"] = df["airline"].str.replace(
                        r"^\[RETURN\]\s*", "", regex=True
                    )

            # Display price metrics for round trip combinations
            display_price_metrics(results, True, outbound_flights, return_flights)

            # Display outbound flights
            st.markdown("#### ✈️ Outbound Flights")
            display_flight_table(outbound_flights)

            # Display return flights
            st.markdown("#### 🔙 Return Flights")
            display_flight_table(return_flights)

        elif is_multi_city:
            st.subheader("🗺️ Multi-City Trip")

            # Group flights by route segment
            if "route_segment" in results.columns:
                unique_segments = results["route_segment"].unique()

                # Display individual flight prices for multi-city
                display_price_metrics(results, False)

                # Simple check for incomplete multi-city trips
                expected_legs = 3  # For typical multi-city trips
                actual_legs = len(unique_segments)

                if actual_legs < expected_legs:
                    st.info(
                        f"ℹ️ Showing {actual_legs} available leg(s) of your multi-city trip."
                    )

                for i, segment in enumerate(unique_segments, 1):
                    segment_flights = results[
                        results["route_segment"] == segment
                    ].copy()

                    # Clean up airline names (safety measure)
                    if "airline" in segment_flights.columns:
                        segment_flights["airline"] = segment_flights[
                            "airline"
                        ].str.replace(r"^\[(OUTBOUND|RETURN)\]\s*", "", regex=True)

                    st.markdown(f"#### Leg {i}: {segment}")
                    display_flight_table(segment_flights)
            else:
                # Fallback if route_segment not available
                display_flight_table(results)
                display_price_metrics(results, False)
        else:
            # One-way flights
            st.subheader("✈️ Flight Options")
            display_flight_table(results)
            display_price_metrics(results, False)

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")


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
    available_columns = [
        col for col in preferred_columns if col in results_display.columns
    ]

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
            columns={
                k: v for k, v in column_renames.items() if k in results_to_show.columns
            }
        )
    else:
        results_to_show = results_display
    st.dataframe(results_to_show, use_container_width=True, hide_index=True)


def render_suggestion_buttons() -> None:
    """Render suggestion buttons for common queries."""
    st.markdown("##### 💡 Try these examples:")
    suggestions = [
        "Flights from LCY to LIN 10/08/2025",
        "Round trip from SFO to LAX leaving on June 25 2025 and returning 5 days later",
        "Find flights from Charles de Gaulle to Miami on 2025-07-10",
        "Multi-city: New York JFK to Paris Dec 15, Paris to Rome Dec 20, Rome to New York JFK Dec 25 2025",
    ]

    cols = st.columns(len(suggestions))
    for i, suggestion_text in enumerate(suggestions):
        if cols[i].button(suggestion_text, key=f"suggestion_{i}"):
            st.session_state.query_text = suggestion_text


def handle_search_results(result: dict) -> None:
    """Handle and display search results."""
    if result.get("success"):
        results_obj = result.get("results")
        st.header("📋 Search Results")

        if results_obj and results_obj.results:
            list_of_flat_records = [
                record.model_dump() for record in results_obj.results
            ]
            df = pd.DataFrame(list_of_flat_records)

        else:
            df = pd.DataFrame()

        display_flight_results(
            df, results_obj.summary if results_obj else "No summary available."
        )
    else:
        error_message = result.get("error", "Unknown error")
        st.error(f"❌ Search failed: {error_message}")


def main():
    """Main application function."""
    # Header
    st.title("✈️ Agentic Travel")
    st.markdown(
        "Find flights using natural language queries with AI-powered multi-agent orchestration"
    )

    # Initialise session state
    if "query_text" not in st.session_state:
        st.session_state.query_text = ""

    # Check API health
    if not check_api_health():
        st.error("🔴 Backend API is not running. Please start the backend server.")
        st.stop()

    st.header("🔍 Search Flights")

    # Render suggestion buttons
    render_suggestion_buttons()

    # Search input
    query = st.text_area(
        "Enter your flight search query:",
        value=st.session_state.query_text,
        placeholder="e.g., Find flights from LHR to MXP on 2025-01-15, or plan a multi-city trip",
        height=100,
        help="Use airport codes and specific dates for best results. The AI can handle complex queries including multi-city trips. Searches may take 30-60 seconds.",
        key="query_input",
    )

    # Update session state when text area changes
    if query != st.session_state.query_text:
        st.session_state.query_text = query

    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button(
            "🔍 Search Flights", type="primary", use_container_width=True
        )

    # Handle search
    if search_button:
        if st.session_state.query_text.strip():
            with st.spinner(
                "🤖 AI agents are searching for flights... This may take up to 60 seconds."
            ):
                result = search_flights(st.session_state.query_text.strip())
                handle_search_results(result)
        else:
            st.warning("⚠️ Please enter a search query.")


if __name__ == "__main__":
    main()
