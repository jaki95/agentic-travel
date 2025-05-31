import streamlit as st

from api import check_api_health, search_flights
from utils import handle_search_results, render_suggestion_buttons

# Page configuration
st.set_page_config(
    page_title="Agentic Travel",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    """Main application function."""
    # Header
    st.title("✈️ Agentic Travel")
    st.markdown(
        "Find flights using natural language queries with AI-powered multi-agent orchestration"
    )

    # Initialize session state
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
                "🤖 AI agents are searching for flights..."
            ):
                result = search_flights(st.session_state.query_text.strip())
                handle_search_results(result)
        else:
            st.warning("⚠️ Please enter a search query.")


if __name__ == "__main__":
    main()
