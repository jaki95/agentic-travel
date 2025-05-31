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


def display_price_metrics(results: pd.DataFrame) -> None:
    """Display price statistics if price data is available."""
    if "price" not in results.columns or not results["price"].notna().any():
        return

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
                "📊 Average Price", f"£{sum(numeric_prices) / len(numeric_prices):.0f}"
            )
        with col3:
            st.metric("📈 Highest Price", f"£{max(numeric_prices):.0f}")
    except Exception:
        # Silently fail if price parsing doesn't work
        pass


def display_flight_results(results: pd.DataFrame, summary: str = None) -> None:
    """Display flight results."""
    try:
        # Display summary if available
        if summary:
            st.info(f"📊 {summary}")

        results_display = results

        # Display flight results in a nice table
        st.subheader("✈️ Flight Options")
        st.dataframe(results_display, use_container_width=True, hide_index=True)

        # Display price metrics
        display_price_metrics(results_display)

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")


def render_suggestion_buttons() -> None:
    """Render suggestion buttons for common queries."""
    st.markdown("##### 💡 Try these examples:")
    suggestions = [
        "Flights from LCY to LIN 10/08/2025",
        "Round trip from SFO to LAX for 3 days in June 2025",
        "Find flights from CDG to NRT on 2025-07-10",
        "Multi-city: NYC to Paris Dec 15, Paris to Rome Dec 20, Rome to NYC Dec 25 2025",
    ]

    cols = st.columns(len(suggestions))
    for i, suggestion_text in enumerate(suggestions):
        if cols[i].button(suggestion_text, key=f"suggestion_{i}"):
            st.session_state.query_text = suggestion_text


def handle_search_results(result: dict) -> None:
    """Handle and display search results."""
    if result.get("success"):
        st.success("✅ Flight search completed!")
        st.header("📋 Search Results")

        results_obj = result.get("results")

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

    # Footer
    st.markdown("---")
    st.markdown("""
    **About:** This application uses advanced AI agents to understand and process complex travel queries. 
    The system can handle single flights, round trips, and complex multi-city itineraries.
    """)


if __name__ == "__main__":
    main()
