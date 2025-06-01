import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.api import app


@pytest.fixture
def test_client():
    """FastAPI test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_llm():
    """Mock LLM fixture for testing."""
    mock = MagicMock()
    mock.model = "gpt-4-mini"
    mock.api_key = "test-key"
    mock.temperature = 0.1
    # Don't add verbose attribute since real LLM doesn't have it
    return mock


@pytest.fixture
def mock_agent():
    """Mock CrewAI Agent fixture."""
    mock = MagicMock()
    mock.role = "Test Agent"
    mock.goal = "Test goal"
    mock.backstory = "Test backstory"
    mock.verbose = True
    mock.allow_delegation = False
    mock.max_iter = 2
    return mock


@pytest.fixture
def mock_tools():
    """Mock tools that behave like CrewAI tools."""
    tool1 = MagicMock()
    tool1.__name__ = "mock_tool_1"
    tool2 = MagicMock()
    tool2.__name__ = "mock_tool_2"
    return [tool1, tool2]


@pytest.fixture
def sample_airport_data():
    """Sample airport data for testing."""
    return pd.DataFrame(
        [
            {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
            {"name": "London Heathrow Airport", "iata_code": "LHR"},
            {"name": "Charles de Gaulle Airport", "iata_code": "CDG"},
            {"name": "Los Angeles International Airport", "iata_code": "LAX"},
            {"name": "Paris Orly Airport", "iata_code": "ORY"},
        ]
    )


@pytest.fixture
def temp_airport_csv(sample_airport_data):
    """Temporary CSV file with airport data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_airport_data.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def mock_openai_env():
    """Mock OpenAI API key environment variable."""
    original_key = os.environ.get("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "test-api-key"
    yield
    if original_key:
        os.environ["OPENAI_API_KEY"] = original_key
    else:
        os.environ.pop("OPENAI_API_KEY", None)


@pytest.fixture
def sample_flight_record():
    """Sample flight display record for testing."""
    from backend.models.flights import Flight

    return Flight(
        origin="New York (JFK)",
        destination="London (LHR)",
        departure_date="2025-06-01",
        passengers=1,
        price="$450",
        currency="USD",
        airline="British Airways",
        route="JFK → LHR",
        stops=0,
        departure_time="10:30",
        arrival_time="22:15",
        duration="7h 45m",
        direction=None,
    )


@pytest.fixture
def sample_query_breakdown():
    """Sample query breakdown for testing."""
    from backend.models.search import QueryBreakdown, SearchQuery

    return QueryBreakdown(
        searches=[
            SearchQuery(
                origin="JFK",
                destination="LHR",
                departure_date="2025-06-01",
                passengers=1,
                search_type="one_way",
            )
        ]
    )


@pytest.fixture
def mock_context_manager():
    """Mock context manager for MCP adapter and similar."""
    mock_cm = MagicMock()
    mock_instance = MagicMock()
    mock_cm.return_value = mock_instance
    mock_instance.__enter__ = MagicMock(return_value=[MagicMock(), MagicMock()])
    mock_instance.__exit__ = MagicMock(return_value=None)
    return mock_cm
