import streamlit as st

# API configuration
API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 90
HEALTH_CHECK_TIMEOUT = 5

# Display constants
EXPECTED_MULTI_CITY_LEGS = 3
PRICE_DECIMAL_PLACES = 0

# Suggestion queries
SUGGESTION_QUERIES = [
    "Flights from LCY to LIN 10/08/2025",
    "Round trip from SFO to LAX leaving on June 25 2025 and returning 5 days later",
    "Find flights from Charles de Gaulle to Miami on 2025-07-10",
    "Multi-city: New York JFK to Paris Dec 15, Paris to Rome Dec 20, Rome to New York JFK Dec 25 2025",
]
