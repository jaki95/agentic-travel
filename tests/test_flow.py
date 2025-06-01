import os
from unittest.mock import Mock, patch

import pytest

from backend.flow import FlightSearchFlow, FlightSearchState
from backend.models.flights import FlightSearchResults


class TestFlightSearchState:
    """Test suite for FlightSearchState model."""

    def test_flight_search_state_creation(self):
        """Test creating a FlightSearchState."""
        state = FlightSearchState()
        assert state.message == ""
        assert state.query_breakdown is None
        assert state.search_results is None

    def test_flight_search_state_with_data(
        self, sample_query_breakdown, sample_flight_record
    ):
        """Test creating FlightSearchState with data."""
        flight_search_results = FlightSearchResults(flights=[sample_flight_record])

        state = FlightSearchState(
            message="Processing query",
            query_breakdown=sample_query_breakdown,
            search_results=[flight_search_results],
        )
        assert state.message == "Processing query"
        assert state.query_breakdown == sample_query_breakdown
        assert len(state.search_results) == 1


class TestFlightSearchFlow:
    """Test suite for FlightSearchFlow class."""

    def test_flow_initialization(self):
        """Test FlightSearchFlow initialization."""
        query = "flight from NYC to London"
        flow = FlightSearchFlow(query)

        assert flow.query == query
        assert flow.llm.model == "gpt-4.1-mini"
        assert flow.llm.temperature == 0.1

    def test_flow_initialization_without_api_key(self):
        """Test that flow raises error without OpenAI API key."""
        # Remove the API key
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        with pytest.raises(
            ValueError, match="OPENAI_API_KEY environment variable is required"
        ):
            FlightSearchFlow("test query")

    def test_create_mcp_server_params(self):
        """Test MCP server parameters creation."""
        flow = FlightSearchFlow("test query")
        params = flow._create_mcp_server_params()

        assert params.command == "uv"
        assert "run" in params.args
        assert "UV_PYTHON" in params.env
        assert params.env["UV_PYTHON"] == "3.12"

    @patch("backend.flow.Crew")
    @patch("backend.flow.create_query_analyzer_agent")
    @patch("backend.flow.create_analysis_task")
    def test_break_down_query(
        self,
        mock_create_task,
        mock_create_agent,
        mock_crew_class,
        sample_query_breakdown,
    ):
        """Test the break_down_query method."""
        # Setup mocks
        mock_agent = Mock()
        mock_task = Mock()
        mock_crew = Mock()
        mock_result = Mock()
        mock_task_output = Mock()
        mock_task_output.pydantic = sample_query_breakdown
        mock_result.tasks_output = [mock_task_output]

        mock_create_agent.return_value = mock_agent
        mock_create_task.return_value = mock_task
        mock_crew_class.return_value = mock_crew
        mock_crew.kickoff.return_value = mock_result

        # Test the method
        flow = FlightSearchFlow("test query")
        flow.break_down_query()

        # Verify calls
        mock_create_agent.assert_called_once_with(flow.llm)
        mock_create_task.assert_called_once_with("test query", mock_agent)
        mock_crew_class.assert_called_once_with(
            agents=[mock_agent], tasks=[mock_task], verbose=True
        )
        mock_crew.kickoff.assert_called_once()

        # Verify state is updated
        assert flow.state.query_breakdown == sample_query_breakdown

    @patch("backend.flow.MCPServerAdapter")
    @patch("backend.flow.Crew")
    @patch("backend.flow.create_structured_flight_agent")
    @patch("backend.flow.create_search_task")
    @pytest.mark.asyncio
    async def test_search_flights(
        self,
        mock_create_task,
        mock_create_agent,
        mock_crew_class,
        mock_mcp_adapter,
        mock_openai_env,
        sample_query_breakdown,
        sample_flight_record,
    ):
        """Test the search_flights async method."""
        # Setup mocks
        mock_agent = Mock()
        mock_task = Mock()
        mock_crew = Mock()
        mock_result = Mock()
        mock_task_output = Mock()
        mock_task_output.pydantic = Mock(flights=[sample_flight_record])
        mock_result.tasks_output = [mock_task_output]

        mock_create_agent.return_value = mock_agent
        mock_create_task.return_value = mock_task
        mock_crew_class.return_value = mock_crew

        # Create proper async coroutine for kickoff_async
        async def async_kickoff(**kwargs):
            return mock_result

        mock_crew.kickoff_async = Mock(side_effect=async_kickoff)

        # Setup adapter - fix context manager mocking
        mock_tools = [Mock()]
        mock_adapter_instance = Mock()
        mock_adapter_instance.__enter__ = Mock(return_value=mock_tools)
        mock_adapter_instance.__exit__ = Mock(return_value=None)
        mock_mcp_adapter.return_value = mock_adapter_instance

        # Test the method
        flow = FlightSearchFlow("test query")
        flow.state.query_breakdown = sample_query_breakdown

        await flow.search_flights()

        # Verify MCP adapter was used
        mock_mcp_adapter.assert_called_once()
        mock_create_agent.assert_called_once_with(flow.llm, mock_tools)

        # Verify tasks were created for each search
        assert mock_create_task.call_count == len(sample_query_breakdown.searches)

        # Verify crews were created and executed
        assert mock_crew_class.call_count == len(sample_query_breakdown.searches)

        # Verify state is updated
        assert flow.state.search_results is not None
        assert len(flow.state.search_results) == 1

    @patch("backend.flow.MCPServerAdapter")
    @patch("backend.flow.Crew")
    @patch("backend.flow.create_structured_flight_agent")
    @patch("backend.flow.create_search_task")
    @pytest.mark.asyncio
    async def test_search_flights_no_results(
        self,
        mock_create_task,
        mock_create_agent,
        mock_crew_class,
        mock_mcp_adapter,
        mock_openai_env,
        sample_query_breakdown,
    ):
        """Test search_flights with no results."""
        # Setup mocks for empty results
        mock_agent = Mock()
        mock_task = Mock()
        mock_crew = Mock()
        mock_result = Mock()
        mock_result.tasks_output = []  # No task outputs

        mock_create_agent.return_value = mock_agent
        mock_create_task.return_value = mock_task
        mock_crew_class.return_value = mock_crew

        # Create proper async coroutine
        async def async_kickoff(**kwargs):
            return mock_result

        mock_crew.kickoff_async = Mock(side_effect=async_kickoff)

        # Setup adapter
        mock_tools = [Mock()]
        mock_adapter_instance = Mock()
        mock_adapter_instance.__enter__ = Mock(return_value=mock_tools)
        mock_adapter_instance.__exit__ = Mock(return_value=None)
        mock_mcp_adapter.return_value = mock_adapter_instance

        # Test the method
        flow = FlightSearchFlow("test query")
        flow.state.query_breakdown = sample_query_breakdown

        await flow.search_flights()

        # Verify empty results are handled
        assert flow.state.search_results == []

    @patch("backend.flow.MCPServerAdapter")
    @patch("backend.flow.Crew")
    @patch("backend.flow.create_structured_flight_agent")
    @patch("backend.flow.create_search_task")
    @pytest.mark.asyncio
    async def test_search_flights_missing_pydantic(
        self,
        mock_create_task,
        mock_create_agent,
        mock_crew_class,
        mock_mcp_adapter,
        mock_openai_env,
        sample_query_breakdown,
    ):
        """Test search_flights when task output is missing pydantic result."""
        # Setup mocks with missing pydantic
        mock_agent = Mock()
        mock_task = Mock()
        mock_crew = Mock()
        mock_result = Mock()
        mock_task_output = Mock()
        mock_task_output.pydantic = None  # Missing pydantic result
        mock_result.tasks_output = [mock_task_output]

        mock_create_agent.return_value = mock_agent
        mock_create_task.return_value = mock_task
        mock_crew_class.return_value = mock_crew

        # Create proper async coroutine
        async def async_kickoff(**kwargs):
            return mock_result

        mock_crew.kickoff_async = Mock(side_effect=async_kickoff)

        # Setup adapter
        mock_tools = [Mock()]
        mock_adapter_instance = Mock()
        mock_adapter_instance.__enter__ = Mock(return_value=mock_tools)
        mock_adapter_instance.__exit__ = Mock(return_value=None)
        mock_mcp_adapter.return_value = mock_adapter_instance

        # Test the method
        flow = FlightSearchFlow("test query")
        flow.state.query_breakdown = sample_query_breakdown

        await flow.search_flights()

        # Based on the actual flow logic, if pydantic is None, it should still be appended
        # The flow currently appends task_output.pydantic regardless of whether it's None
        assert flow.state.search_results == [None]

    def test_flow_state_initialization(self, mock_openai_env):
        """Test that flow initializes with proper state."""
        flow = FlightSearchFlow("test query")

        # State should be initialized
        assert hasattr(flow, "state")
        assert isinstance(flow.state, FlightSearchState)
        assert flow.state.message == ""
        assert flow.state.query_breakdown is None
        assert flow.state.search_results is None

    @patch("backend.flow.MCP_SERVER_PATH")
    def test_mcp_server_path_usage(self, mock_server_path, mock_openai_env):
        """Test that MCP server path is used correctly."""
        # Fix the mock to return a proper path string
        mock_path = Mock()
        mock_path.as_posix.return_value = "/path/to/server"
        mock_server_path.as_posix.return_value = "/path/to/server"

        flow = FlightSearchFlow("test query")
        params = flow._create_mcp_server_params()

        # Should use the server path
        assert "/path/to/server" in params.args

    def test_flow_query_storage(self, mock_openai_env):
        """Test that the original query is stored correctly."""
        query = "flight from NYC to London on June 15th"
        flow = FlightSearchFlow(query)

        assert flow.query == query

    @patch("backend.flow.LLM")
    def test_llm_configuration(self, mock_llm_class, mock_openai_env):
        """Test that LLM is configured correctly."""
        mock_llm_instance = Mock()
        mock_llm_class.return_value = mock_llm_instance

        flow = FlightSearchFlow("test query")

        mock_llm_class.assert_called_once_with(
            model="gpt-4.1-mini",
            api_key="test-api-key",
            temperature=0.1,
            verbose=True,
        )
        assert flow.llm == mock_llm_instance

    def test_flow_inheritance(self, mock_openai_env):
        """Test that FlightSearchFlow properly inherits from Flow."""
        from crewai.flow.flow import Flow

        flow = FlightSearchFlow("test query")
        assert isinstance(flow, Flow)

    @patch("backend.flow.os.environ")
    def test_environment_variable_usage(self, mock_environ, mock_openai_env):
        """Test that environment variables are properly used."""
        mock_environ.get.return_value = "test-api-key"
        mock_environ.__contains__ = lambda x, key: key == "OPENAI_API_KEY"
        mock_environ.__getitem__ = (
            lambda x, key: "test-api-key" if key == "OPENAI_API_KEY" else ""
        )

        # Test accessing the environment in _create_mcp_server_params
        flow = FlightSearchFlow("test query")
        params = flow._create_mcp_server_params()

        # Should include environment variables
        assert isinstance(params.env, dict)
        assert "UV_PYTHON" in params.env
