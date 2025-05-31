import requests
from config import API_BASE_URL, API_TIMEOUT, HEALTH_CHECK_TIMEOUT

from backend.models.api import FlightSearchResponse


def check_api_health() -> bool:
    """Check if the backend API is running."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=HEALTH_CHECK_TIMEOUT)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def search_flights(query: str) -> dict:
    """Send flight search request to the backend API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={"query": query},
            timeout=API_TIMEOUT,
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
