import asyncio
import os
import sys
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv
import logging
from pathlib import Path
from backend.observability import setup_tracing, get_tracer

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
        return MCPTools(command, timeout_seconds=30.0)

    def _create_flight_agent(self, mcp_tools: MCPTools) -> Agent:
        """Create a flight search agent with the given MCP tools."""
        return Agent(
            model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
            tools=[mcp_tools],
            show_tool_calls=False,
            markdown=True,
            name="flight_search_agent",
        )

    async def _execute_agent_with_retry(self, agent: Agent, query: str, max_retries: int = 2) -> str:
        """Execute agent with retry logic for common errors."""
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(agent.arun(query), timeout=25.0)
                return response.content if hasattr(response, "content") else str(response)
            
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    logger.warning(f"Agent timeout on attempt {attempt + 1}, retrying...")
                    await asyncio.sleep(1)
                else:
                    raise
            
            except Exception as e:
                if "TaskGroup" in str(e) and attempt < max_retries:
                    logger.warning(f"TaskGroup error on attempt {attempt + 1}, retrying: {e}")
                    await asyncio.sleep(2)
                else:
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
        
        return f"An unexpected error occurred during flight search: {error_str}"

    async def _try_mcp_command(self, command: str, query: str, span) -> str | None:
        """Try executing a flight search with a specific MCP command."""
        try:
            span.set_attribute("mcp.command", command)
            logger.info(f"Attempting MCP server with: {command}")

            async with await self._create_mcp_tools(command) as mcp_tools:
                with tracer.start_as_current_span("mcp_agent_execution") as agent_span:
                    agent_span.set_attribute("agent.model", "gpt-4o-mini")
                    agent_span.set_attribute("agent.tools", "mcp_tools")

                    agent = self._create_flight_agent(mcp_tools)
                    logger.info("MCP tools initialized, running agent...")

                    result = await self._execute_agent_with_retry(agent, query)
                    
                    agent_span.set_attribute("response.length", len(result))
                    span.set_attribute("response.length", len(result))
                    
                    logger.info("Flight search completed successfully")
                    return result

        except Exception as e:
            if "TaskGroup" in str(e):
                logger.error(f"TaskGroup error with '{command}':", exc_info=True)
            else:
                logger.warning(f"Failed MCP command '{command}': {e}")
            return None

    async def search_flights(self, query: str) -> str:
        """
        Search for flights using MCP agent.

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

            # Try each MCP command until one succeeds
            last_error = None
            for command in self.mcp_commands:
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
                logger.error(f"All MCP commands failed: {last_error}", exc_info=True)
                return error_msg

            return "All flight search attempts failed. Please try again."
