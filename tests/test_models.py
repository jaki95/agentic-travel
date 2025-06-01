import uuid

import pytest
from pydantic import ValidationError

from backend.models.api import FlightSearchRequest, FlightSearchResponse
from backend.models.flights import Flight, FlightSearchResults
from backend.models.search import QueryBreakdown, SearchQuery


class TestFlight:
    """Test suite for Flight model."""

    def test_flight_creation(self):
        """Test creating a valid Flight."""
        record = Flight(
            origin="New York (JFK)",
            destination="London (LHR)",
            departure_date="2025-06-01",
            price="$450",
            currency="USD",
            airline="British Airways",
        )
        assert record.origin == "New York (JFK)"
        assert record.destination == "London (LHR)"
        assert record.price == "$450"

    def test_flight_optional_fields(self):
        """Test that all fields are optional."""
        # Should work with minimal data
        record = Flight()
        assert record.origin == ""
        assert record.destination == ""
        assert record.price == ""

    def test_flight_all_fields(self):
        """Test creating a record with all fields populated."""
        record = Flight(
            origin="New York (JFK)",
            destination="London (LHR)",
            departure_date="2025-06-01",
            passengers=2,
            price="$450",
            currency="USD",
            airline="British Airways",
            route="JFK → LHR",
            stops=0,
            departure_time="10:30",
            arrival_time="22:15",
            duration="7h 45m",
            direction="outbound",
        )
        assert record.passengers == 2
        assert record.stops == 0
        assert record.direction == "outbound"

    def test_flight_serialization(self):
        """Test that the record can be serialized to dict/JSON."""
        record = Flight(origin="NYC", destination="LAX", price="$300")
        data = record.model_dump()
        assert isinstance(data, dict)
        assert data["origin"] == "NYC"
        assert data["destination"] == "LAX"
        assert data["price"] == "$300"


class TestFlightSearchResults:
    """Test suite for FlightSearchResults model."""

    def test_flight_search_results_creation(self):
        """Test creating FlightSearchResults with flight list."""
        flight1 = Flight(origin="NYC", destination="LAX")
        flight2 = Flight(origin="LAX", destination="NYC")

        results = FlightSearchResults(flights=[flight1, flight2])
        assert len(results.flights) == 2
        assert results.flights[0].origin == "NYC"
        assert results.flights[1].origin == "LAX"

    def test_flight_search_results_empty(self):
        """Test creating empty FlightSearchResults."""
        results = FlightSearchResults(flights=[])
        assert len(results.flights) == 0

    def test_flight_search_results_default(self):
        """Test default FlightSearchResults creation."""
        # flights field is required, so pass empty list
        results = FlightSearchResults(flights=[])
        assert results.flights == []


class TestSearchQuery:
    """Test suite for SearchQuery model."""

    def test_search_query_creation(self):
        """Test creating a valid SearchQuery."""
        query = SearchQuery(
            origin="JFK", destination="LHR", departure_date="2025-06-01"
        )
        assert query.origin == "JFK"
        assert query.destination == "LHR"
        assert query.departure_date == "2025-06-01"
        assert query.passengers == 1  # default value
        assert query.search_type == "one_way"  # default value

    def test_search_query_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            SearchQuery()  # Missing required fields

        with pytest.raises(ValidationError):
            SearchQuery(origin="JFK")  # Missing destination and departure_date

    def test_search_query_round_trip(self):
        """Test creating a round trip SearchQuery."""
        query = SearchQuery(
            origin="JFK",
            destination="LHR",
            departure_date="2025-06-01",
            return_date="2025-06-15",
            passengers=2,
            search_type="round_trip",
        )
        assert query.return_date == "2025-06-15"
        assert query.passengers == 2
        assert query.search_type == "round_trip"

    def test_search_query_id_generation(self):
        """Test that ID is automatically generated."""
        query1 = SearchQuery(
            origin="JFK", destination="LHR", departure_date="2025-06-01"
        )
        query2 = SearchQuery(
            origin="LAX", destination="NYC", departure_date="2025-07-01"
        )

        assert query1.id != query2.id
        assert isinstance(query1.id, str)
        # Validate it's a UUID
        uuid.UUID(query1.id)

    def test_search_query_custom_id(self):
        """Test setting a custom ID."""
        custom_id = "custom-search-id"
        query = SearchQuery(
            id=custom_id, origin="JFK", destination="LHR", departure_date="2025-06-01"
        )
        assert query.id == custom_id


class TestQueryBreakdown:
    """Test suite for QueryBreakdown model."""

    def test_query_breakdown_creation(self):
        """Test creating a QueryBreakdown with searches."""
        search1 = SearchQuery(
            origin="JFK", destination="LHR", departure_date="2025-06-01"
        )
        search2 = SearchQuery(
            origin="LHR", destination="CDG", departure_date="2025-06-05"
        )

        breakdown = QueryBreakdown(searches=[search1, search2])
        assert len(breakdown.searches) == 2
        assert breakdown.searches[0].origin == "JFK"
        assert breakdown.searches[1].origin == "LHR"

    def test_query_breakdown_empty(self):
        """Test creating empty QueryBreakdown."""
        breakdown = QueryBreakdown(searches=[])
        assert len(breakdown.searches) == 0

    def test_query_breakdown_single_search(self):
        """Test QueryBreakdown with single search."""
        search = SearchQuery(
            origin="JFK", destination="LHR", departure_date="2025-06-01"
        )
        breakdown = QueryBreakdown(searches=[search])
        assert len(breakdown.searches) == 1


class TestFlightSearchRequest:
    """Test suite for FlightSearchRequest model."""

    def test_flight_search_request_creation(self):
        """Test creating a valid FlightSearchRequest."""
        request = FlightSearchRequest(query="flight from NYC to London")
        assert request.query == "flight from NYC to London"

    def test_flight_search_request_required_field(self):
        """Test that query field is required."""
        with pytest.raises(ValidationError):
            FlightSearchRequest()

    def test_flight_search_request_empty_query(self):
        """Test FlightSearchRequest with empty query."""
        request = FlightSearchRequest(query="")
        assert request.query == ""


class TestFlightSearchResponse:
    """Test suite for FlightSearchResponse model."""

    def test_flight_search_response_success(self):
        """Test creating a successful FlightSearchResponse."""
        flight = Flight(origin="NYC", destination="LAX")
        response = FlightSearchResponse(
            results=[flight],
            success=True,
            summary="Found 1 flight",
            duration_seconds=1.5,
        )

        assert response.results == [flight]
        assert response.success is True
        assert response.summary == "Found 1 flight"
        assert response.duration_seconds == 1.5
        assert response.error is None

    def test_flight_search_response_error(self):
        """Test creating an error FlightSearchResponse."""
        response = FlightSearchResponse(
            results=[], success=False, error="Search failed", duration_seconds=0.5
        )

        assert response.results == []
        assert response.success is False
        assert response.error == "Search failed"
        assert response.duration_seconds == 0.5

    def test_flight_search_response_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            FlightSearchResponse()  # Missing required fields

    def test_flight_search_response_minimal(self):
        """Test creating minimal FlightSearchResponse."""
        response = FlightSearchResponse(
            results=[], success=True, duration_seconds=1.0
        )
        assert response.results == []
        assert response.success is True
        assert response.summary is None
        assert response.error is None

    def test_flight_search_response_serialization(self):
        """Test that the response can be serialized to dict/JSON."""
        flight = Flight(origin="NYC", destination="LAX")
        response = FlightSearchResponse(
            results=[flight], success=True, summary="Test", duration_seconds=1.0
        )
        data = response.model_dump()
        assert isinstance(data, dict)
        assert "results" in data
        assert "success" in data
        assert data["success"] is True
