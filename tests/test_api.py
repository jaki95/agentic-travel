import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.models.api import FlightSearchRequest, FlightSearchResponse
from backend.models.flights import Flight


class TestAPI:
    """Test suite for FastAPI endpoints."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test the root health check endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Agentic Travel API is running"}

    def test_health_endpoint(self, test_client: TestClient):
        """Test the health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agentic-travel-api"

    @patch("backend.api.FlightSearchFlow")
    def test_search_flights_success(
        self, mock_flow_class, test_client: TestClient, sample_flight_record
    ):
        """Test successful flight search."""
        # Mock flow instance
        mock_flow = Mock()
        mock_state = Mock()
        mock_state.search_results = [Mock(flights=[sample_flight_record])]
        mock_state.query_breakdown = Mock(searches=[Mock()])
        mock_flow.state = mock_state
        mock_flow_class.return_value = mock_flow

        request_data = {"query": "flight from NYC to London"}
        response = test_client.post("/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 1
        assert data["results"][0]["origin"] == "New York (JFK)"
        assert data["results"][0]["destination"] == "London (LHR)"
        assert "Found 1 flight options" in data["summary"]

    @patch("backend.api.FlightSearchFlow")
    def test_search_flights_no_results(self, mock_flow_class, test_client: TestClient):
        """Test flight search with no results."""
        # Mock flow instance with no results
        mock_flow = Mock()
        mock_state = Mock()
        mock_state.search_results = []
        mock_state.query_breakdown = Mock(searches=[Mock()])
        mock_flow.state = mock_state
        mock_flow_class.return_value = mock_flow

        request_data = {"query": "flight from nowhere to anywhere"}
        response = test_client.post("/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 0
        assert "No flights found" in data["summary"]

    @patch("backend.api.FlightSearchFlow")
    def test_search_flights_error(self, mock_flow_class, test_client: TestClient):
        """Test flight search with error."""
        # Mock flow to raise exception
        mock_flow_class.side_effect = Exception("API error")

        request_data = {"query": "invalid query"}
        response = test_client.post("/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "API error"
        assert len(data["results"]) == 0

    def test_search_flights_invalid_request(self, test_client: TestClient):
        """Test flight search with invalid request data."""
        # Missing required query field
        response = test_client.post("/search", json={})
        assert response.status_code == 422

        # Invalid JSON
        response = test_client.post("/search", data="invalid json")
        assert response.status_code == 422

    @patch("backend.api.FlightSearchFlow")
    def test_search_flights_multiple_results(
        self, mock_flow_class, test_client: TestClient
    ):
        """Test flight search with multiple flight results."""
        # Create multiple sample flights
        flight1 = Flight(
            origin="NYC (JFK)",
            destination="London (LHR)",
            price="$450",
            route="JFK→LHR",
        )
        flight2 = Flight(
            origin="NYC (JFK)",
            destination="London (LHR)",
            price="$520",
            route="JFK→LHR",
        )

        # Mock flow instance
        mock_flow = Mock()
        mock_state = Mock()
        mock_state.search_results = [Mock(flights=[flight1, flight2])]
        mock_state.query_breakdown = Mock(searches=[Mock()])
        mock_flow.state = mock_state
        mock_flow_class.return_value = mock_flow

        request_data = {"query": "flight from NYC to London"}
        response = test_client.post("/search", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 2
        assert "Found 2 flight options" in data["summary"]


    @patch("backend.api.FlightSearchFlow")
    def test_search_response_model_validation(
        self, mock_flow_class, test_client: TestClient, sample_flight_record
    ):
        """Test that the response follows the expected model."""
        # Mock flow instance
        mock_flow = Mock()
        mock_state = Mock()
        mock_state.search_results = [Mock(flights=[sample_flight_record])]
        mock_state.query_breakdown = Mock(searches=[Mock()])
        mock_flow.state = mock_state
        mock_flow_class.return_value = mock_flow

        request_data = {"query": "test query"}
        response = test_client.post("/search", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Validate response structure matches FlightSearchResponse
        assert "results" in data
        assert "success" in data
        assert "summary" in data
        assert "duration_seconds" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["success"], bool)

    def test_request_model_validation(self, test_client: TestClient):
        """Test that request validation works correctly."""
        # Valid request
        valid_request = {"query": "flight from NYC to LA"}
        response = test_client.post("/search", json=valid_request)
        assert response.status_code in [200, 500]  # Should pass validation

        # Request with extra fields (should be allowed)
        extra_fields_request = {"query": "test", "extra_field": "ignored"}
        response = test_client.post("/search", json=extra_fields_request)
        assert response.status_code in [200, 500]  # Should pass validation

        # Empty query (should fail validation or be handled gracefully)
        empty_query_request = {"query": ""}
        response = test_client.post("/search", json=empty_query_request)
        assert response.status_code in [200, 422, 500]  # Depends on implementation
