import streamlit as st
import requests
import time

# Configure the page
st.set_page_config(
    page_title="Agentic Travel",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# API configuration
API_BASE_URL = "http://localhost:8000"


def check_api_health():
    """Check if the backend API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def search_flights(query: str):
    """Send flight search request to the backend API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"query": query},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out. Please try again.",
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def main():
    # Header
    st.title("✈️ Agentic Travel")
    st.markdown("Find flights using natural language queries")

    # Check API status
    api_status = check_api_health()

    if not api_status:
        st.error("Backend API is not running.")
        st.stop()

    # Main search interface
    st.header("🔍 Search Flights")

    # Search input
    query = st.text_area(
        "Enter your flight search query:",
        placeholder="e.g., Find flights from LHR to CDG on 2025-03-15",
        height=100,
        help="Use airport codes and specific dates for best results. Searches may take 15-30 seconds.",
    )

    # Search button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button(
            "🔍 Search Flights", type="primary", use_container_width=True
        )

    # Handle search
    if search_button and query.strip():
        with st.spinner("Searching for flights... This may take up to 30 seconds."):
            # Perform search
            result = search_flights(query.strip())
            if result.get("success"):
                st.success("✅ Flight search completed!")

                # Display results
                st.header("📋 Search Results")

                # Format and display the results
                results_text = result.get("results", "")
                if results_text:
                    # Try to format as markdown if it contains markdown
                    if (
                        "**" in results_text
                        or "*" in results_text
                        or "#" in results_text
                    ):
                        st.markdown(results_text)
                    else:
                        st.text(results_text)
                else:
                    st.warning("No results found for your query.")

            else:
                error_message = result.get("error", "Unknown error")
                st.error(f"❌ Search failed: {error_message}")

    elif search_button and not query.strip():
        st.warning("⚠️ Please enter a search query.")


if __name__ == "__main__":
    main()
