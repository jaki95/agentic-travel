import asyncio
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from agno.team import Team
from dotenv import load_dotenv
import logging
from pathlib import Path
from datetime import datetime
from backend.observability import setup_tracing, get_tracer
from backend.models import FlightSearchResults

load_dotenv()

logger = logging.getLogger(__name__)
setup_tracing()
tracer = get_tracer(__name__)


class FlightService:
    """Service for flight search operations using MCP agents."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.mcp_server_path = self._get_mcp_server_path()
        self.mcp_commands = [
            f"fastmcp run {self.mcp_server_path}",
            f"uv run python {self.mcp_server_path}",
        ]

    def _get_mcp_server_path(self) -> Path:
        """Get the path to the MCP server."""
        project_root = Path(__file__).parent.parent
        return project_root.parent / "Google-Flights-MCP-Server" / "server.py"

    def _validate_mcp_server(self) -> str | None:
        """Validate MCP server exists. Returns error message if invalid."""
        if not self.mcp_server_path.exists():
            return (
                "❌ **MCP Server Not Found**\n\n"
                f"The Google Flights MCP Server was not found at: `{self.mcp_server_path}`\n\n"
                "**Setup Instructions:**\n"
                "1. Clone the Google Flights MCP Server repository\n"
                "2. Ensure it's located at `../Google-Flights-MCP-Server/`\n"
                "3. Install its dependencies\n"
                "4. Restart the backend server"
            )
        return None

    async def _create_mcp_tools(self, command: str) -> MCPTools:
        """Create MCP tools with the given command."""
        # Use timeout_seconds parameter for longer flight searches
        return MCPTools(command, timeout_seconds=60.0)

    async def _test_mcp_server_connectivity(self, command: str) -> bool:
        """Test if the MCP server can be connected to and responds."""
        try:
            logger.info(f"Testing MCP server connectivity: {command}")
            
            # Create MCP tools synchronously (constructor is not async)
            mcp_tools = MCPTools(command, timeout_seconds=10.0)
            
            # Test the async connection with timeout
            async def test_connection():
                async with mcp_tools:
                    # Just test the connection without doing any operations
                    await asyncio.sleep(0.1)
            
            await asyncio.wait_for(test_connection(), timeout=5.0)
                
            logger.info(f"MCP server connectivity test passed: {command}")
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"MCP server connectivity test timed out: {command}")
            return False
        except Exception as e:
            logger.warning(f"MCP server connectivity test failed: {command} - {e}")
            return False

    def _create_flight_agent(self, mcp_tools: MCPTools) -> Agent:
        """Create a flight search agent with the given MCP tools."""
        return Agent(
            model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
            tools=[mcp_tools],
            show_tool_calls=False,
            markdown=True,
            name="flight_search_agent",
            instructions=[
                "Search for flights and provide detailed information including:",
                "- Airline names and flight numbers",
                "- Exact departure and arrival times",
                "- Prices in clear currency format",
                "- Airport codes and names",
                "- Flight duration and number of stops",
                "- Booking class information",
                "Present results in a structured, easy-to-parse format"
            ]
        )

    def _create_structured_flight_agent(self, mcp_tools: MCPTools) -> Agent:
        """Create a flight search agent that returns structured data."""
        return Agent(
            model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
            tools=[mcp_tools],
            show_tool_calls=False,
            markdown=False,
            name="structured_flight_search_agent",
            response_model=FlightSearchResults,  # This makes the agent return structured data!
            instructions=[
                "Search for flights and return structured data.",
                "Extract all relevant flight information and populate the response model fields.",
                "For each flight option found, include:",
                "- Exact airline name and flight number",
                "- Departure and arrival times",
                "- Prices with currency",
                "- Airport information",
                "- Duration and stops",
                "Parse the query to extract origin, destination, dates, and passengers.",
                "If multiple flight options are available, include them all in the flight_options list."
            ]
        )

    async def _execute_agent_with_retry(self, agent: Agent, query: str, max_retries: int = 2) -> str:
        """Execute agent with retry logic for common errors."""
        for attempt in range(max_retries + 1):
            try:
                # Reduced timeout to fail faster and avoid TaskGroup issues
                response = await asyncio.wait_for(agent.arun(query), timeout=20.0)
                return response.content if hasattr(response, "content") else str(response)
            
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"Agent timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(1)
                else:
                    logger.error("Agent execution timed out after all retries")
                    raise
            
            except Exception as e:
                error_str = str(e)
                # Handle various MCP-related errors
                if any(keyword in error_str for keyword in ["TaskGroup", "CancelledError", "WouldBlock"]):
                    if attempt < max_retries:
                        logger.warning(f"MCP connection error on attempt {attempt + 1}, retrying: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"MCP connection failed after all retries: {e}")
                        raise
                else:
                    # For other errors, don't retry
                    logger.error(f"Agent execution failed: {e}")
                    raise

    async def _execute_structured_agent_with_retry(self, agent: Agent, query: str, max_retries: int = 2) -> FlightSearchResults:
        """Execute structured agent with retry logic."""
        for attempt in range(max_retries + 1):
            try:
                # Reduced timeout to fail faster and avoid TaskGroup issues
                response = await asyncio.wait_for(agent.arun(query), timeout=20.0)
                # The agent should return a FlightSearchResults object directly
                if isinstance(response, FlightSearchResults):
                    response.search_timestamp = datetime.now().isoformat()
                    return response
                else:
                    # Fallback if response isn't structured
                    return FlightSearchResults(
                        query=query,
                        search_timestamp=datetime.now().isoformat(),
                        error_message="Agent did not return structured data"
                    )
            
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"Structured agent timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(1)
                else:
                    logger.error("Structured agent execution timed out after all retries")
                    raise
            
            except Exception as e:
                error_str = str(e)
                # Handle various MCP-related errors
                if any(keyword in error_str for keyword in ["TaskGroup", "CancelledError", "WouldBlock"]):
                    if attempt < max_retries:
                        logger.warning(f"MCP connection error on attempt {attempt + 1}, retrying: {e}")
                        await asyncio.sleep(2)
                    else:
                        logger.error(f"MCP connection failed after all retries: {e}")
                        raise
                else:
                    # For other errors, don't retry
                    logger.error(f"Structured agent execution failed: {e}")
                    raise

    def _format_error(self, error: Exception) -> str:
        """Format error messages for user display."""
        error_str = str(error)
        
        if isinstance(error, asyncio.TimeoutError):
            return "The flight search request timed out after 30 seconds."
        
        if "Timed out while waiting for response" in error_str:
            return "The MCP server timed out while fetching flight data."
        
        if "Connection" in error_str or "connection" in error_str:
            return "Failed to connect to the MCP server. Please ensure it's properly configured."
        
        if "fastmcp" in error_str and "not found" in error_str.lower():
            return (
                "The 'fastmcp' command was not found. Please install dev dependencies:\n"
                "• Run: `uv sync --dev`\n"
                "• Or install fastmcp: `uv add --dev fastmcp`"
            )
        
        # Handle Playwright/Google Flights specific errors
        if "Locator.wait_for: Timeout" in error_str and ".eQ35Ce" in error_str:
            return (
                "The Google Flights MCP server encountered a web scraping issue. "
                "This often happens when Google changes their page structure or implements anti-bot measures. "
                "Please try again in a few minutes, or the MCP server may need updating."
            )
        
        if "Target page, context or browser has been closed" in error_str:
            return (
                "The Google Flights browser session was interrupted. "
                "This can happen due to anti-bot detection or page loading issues. "
                "Please try again with a different query or wait a few minutes."
            )
        
        if "Playwright" in error_str or "playwright" in error_str:
            return (
                "The Google Flights MCP server encountered a browser automation issue. "
                "This may be due to Google's anti-bot measures or page structure changes. "
                "Try again later or consider using alternative flight search methods."
            )
        
        return f"An unexpected error occurred during flight search: {error_str}"

    async def _try_mcp_command(self, command: str, query: str, span) -> str | None:
        """Try executing a flight search with a specific MCP command."""
        mcp_tools = None
        try:
            span.set_attribute("mcp.command", command)
            logger.info(f"Attempting MCP server with: {command}")

            # Create MCP tools with shorter timeout
            mcp_tools = await asyncio.wait_for(
                self._create_mcp_tools(command), 
                timeout=10.0
            )
            
            async with mcp_tools:
                with tracer.start_as_current_span("mcp_agent_execution") as agent_span:
                    agent_span.set_attribute("agent.model", "gpt-4o-mini")
                    agent_span.set_attribute("agent.tools", "mcp_tools")

                    agent = self._create_flight_agent(mcp_tools)

                    result = await self._execute_agent_with_retry(agent, query)
                    
                    agent_span.set_attribute("response.length", len(result))
                    span.set_attribute("response.length", len(result))
                    
                    logger.info("Flight search completed successfully")
                    return result

        except asyncio.TimeoutError:
            logger.error(f"MCP command '{command}' timed out during setup or execution")
            return None
        except Exception as e:
            error_str = str(e)
            if any(keyword in error_str for keyword in ["TaskGroup", "CancelledError", "WouldBlock"]):
                logger.error(f"TaskGroup/MCP error with '{command}': {e}")
            else:
                logger.warning(f"Failed MCP command '{command}': {e}")
            return None
        finally:
            # Ensure cleanup even if errors occur
            if mcp_tools is not None:
                try:
                    # Give the context manager a chance to clean up properly
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    logger.warning(f"Error during MCP cleanup: {cleanup_error}")

    async def _try_structured_mcp_command(self, command: str, query: str, span) -> FlightSearchResults | None:
        """Try executing a structured flight search with a specific MCP command."""
        mcp_tools = None
        try:
            span.set_attribute("mcp.command", command)
            logger.info(f"Attempting structured MCP server with: {command}")

            # Create MCP tools with shorter timeout
            mcp_tools = await asyncio.wait_for(
                self._create_mcp_tools(command), 
                timeout=10.0
            )
            
            async with mcp_tools:
                with tracer.start_as_current_span("structured_mcp_agent_execution") as agent_span:
                    agent_span.set_attribute("agent.model", "gpt-4o-mini")
                    agent_span.set_attribute("agent.tools", "mcp_tools")

                    agent = self._create_structured_flight_agent(mcp_tools)

                    result = await self._execute_structured_agent_with_retry(agent, query)
                    
                    agent_span.set_attribute("response.flight_options", len(result.flight_options))
                    span.set_attribute("response.flight_options", len(result.flight_options))
                    
                    logger.info("Structured flight search completed successfully")
                    return result

        except asyncio.TimeoutError:
            logger.error(f"Structured MCP command '{command}' timed out during setup or execution")
            return None
        except Exception as e:
            error_str = str(e)
            if any(keyword in error_str for keyword in ["TaskGroup", "CancelledError", "WouldBlock"]):
                logger.error(f"TaskGroup/MCP error with '{command}': {e}")
            else:
                logger.warning(f"Failed structured MCP command '{command}': {e}")
            return None
        finally:
            # Ensure cleanup even if errors occur
            if mcp_tools is not None:
                try:
                    # Give the context manager a chance to clean up properly
                    await asyncio.sleep(0.1)
                except Exception as cleanup_error:
                    logger.warning(f"Error during MCP cleanup: {cleanup_error}")

    async def search_flights(self, query: str) -> str:
        """
        Search for flights using MCP agent (returns raw string).

        Args:
            query: Natural language flight search query

        Returns:
            Flight search results as a string
        """
        with tracer.start_as_current_span("flight_search") as span:
            span.set_attribute("flight.query", query)
            span.set_attribute("service.name", "flight_service")
            
            logger.info(f"Starting flight search: {query}")

            # Validate MCP server setup
            if error := self._validate_mcp_server():
                span.set_attribute("error.type", "mcp_server_not_found")
                return error

            # Test connectivity to each MCP command first
            working_commands = []
            for command in self.mcp_commands:
                if await self._test_mcp_server_connectivity(command):
                    working_commands.append(command)
                else:
                    logger.warning(f"MCP server connectivity test failed for: {command}")

            if not working_commands:
                error_msg = "No MCP servers are responding. Please check your MCP server setup."
                span.set_attribute("error.type", "no_working_mcp_servers")
                logger.error(error_msg)
                return error_msg

            # Try each working MCP command until one succeeds
            last_error = None
            for command in working_commands:
                try:
                    if result := await self._try_mcp_command(command, query, span):
                        return result
                except Exception as e:
                    last_error = e

            # All commands failed
            if last_error:
                error_msg = self._format_error(last_error)
                span.set_attribute("error.type", "mcp_agent_error")
                span.set_attribute("error.message", str(last_error))
                logger.error(f"All working MCP commands failed: {last_error}", exc_info=True)
                return error_msg

            return "All flight search attempts failed. Please try again."

    async def search_flights_structured(self, query: str) -> FlightSearchResults:
        """
        Search for flights and return structured data using response_model.

        Args:
            query: Natural language flight search query

        Returns:
            FlightSearchResults with structured flight data
        """
        with tracer.start_as_current_span("structured_flight_search") as span:
            span.set_attribute("flight.query", query)
            span.set_attribute("service.name", "flight_service")
            
            logger.info(f"Starting structured flight search: {query}")

            # Validate MCP server setup
            if error := self._validate_mcp_server():
                span.set_attribute("error.type", "mcp_server_not_found")
                return FlightSearchResults(
                    query=query,
                    error_message=error,
                    search_timestamp=datetime.now().isoformat()
                )

            # Test connectivity to each MCP command first
            working_commands = []
            for command in self.mcp_commands:
                if await self._test_mcp_server_connectivity(command):
                    working_commands.append(command)
                else:
                    logger.warning(f"MCP server connectivity test failed for: {command}")

            if not working_commands:
                error_msg = "No MCP servers are responding. Please check your MCP server setup."
                span.set_attribute("error.type", "no_working_mcp_servers")
                logger.error(error_msg)
                return FlightSearchResults(
                    query=query,
                    error_message=error_msg,
                    search_timestamp=datetime.now().isoformat()
                )

            # Try each working MCP command until one succeeds
            last_error = None
            for command in working_commands:
                try:
                    if result := await self._try_structured_mcp_command(command, query, span):
                        return result
                except Exception as e:
                    last_error = e

            # All commands failed
            if last_error:
                error_msg = self._format_error(last_error)
                span.set_attribute("error.type", "mcp_agent_error")
                span.set_attribute("error.message", str(last_error))
                logger.error(f"All working structured MCP commands failed: {last_error}", exc_info=True)
                return FlightSearchResults(
                    query=query,
                    error_message=error_msg,
                    search_timestamp=datetime.now().isoformat()
                )

            return FlightSearchResults(
                query=query,
                error_message="All flight search attempts failed. Please try again.",
                search_timestamp=datetime.now().isoformat()
            )
