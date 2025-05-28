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
    """Service class for handling flight search operations using the MCP agent."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

    async def search_flights(self, query: str) -> str:
        """
        Search for flights using the MCP agent.

        Args:
            query: Natural language flight search query

        Returns:
            Flight search results as a string
        """
        with tracer.start_as_current_span("flight_search") as span:
            try:
                span.set_attribute("flight.query", query)
                span.set_attribute("service.name", "flight_service")

                logger.info(f"Starting flight search for query: {query}")

                project_root = Path(__file__).parent.parent
                mcp_server_path = (
                    project_root.parent / "Google-Flights-MCP-Server" / "server.py"
                )

                if not mcp_server_path.exists():
                    error_msg = (
                        "❌ **MCP Server Not Found**\n\n"
                        f"The Google Flights MCP Server was not found at: `{mcp_server_path}`\n\n"
                        "**Setup Instructions:**\n"
                        "1. Clone the Google Flights MCP Server repository\n"
                        "2. Ensure it's located at `../Google-Flights-MCP-Server/`\n"
                        "3. Install its dependencies\n"
                        "4. Restart the backend server"
                    )
                    span.set_attribute("error.type", "mcp_server_not_found")
                    span.set_attribute("error.message", "MCP server not found")
                    return error_msg

                # Try fastmcp first (preferred), then fall back to uv run python
                commands_to_try = [
                    f"fastmcp run {mcp_server_path}",
                    f"uv run python {mcp_server_path}",
                ]

                last_error = None

                for python_cmd in commands_to_try:
                    try:
                        span.set_attribute("mcp.command", python_cmd)
                        logger.info(
                            f"Attempting to start MCP server with: {python_cmd}"
                        )

                        async with MCPTools(
                            python_cmd, timeout_seconds=30.0
                        ) as mcp_tools:
                            with tracer.start_as_current_span(
                                "mcp_agent_execution"
                            ) as agent_span:
                                agent_span.set_attribute("agent.model", "gpt-4o-mini")
                                agent_span.set_attribute("agent.tools", "mcp_tools")

                                agent = Agent(
                                    model=OpenAIChat(
                                        id="gpt-4o-mini", api_key=self.api_key
                                    ),
                                    tools=[mcp_tools],
                                    show_tool_calls=False,
                                    markdown=True,
                                    name="flight_search_agent",
                                )

                                logger.info("MCP tools initialized, running agent...")

                                # Try agent execution with retry mechanism for TaskGroup errors
                                max_retries = 2
                                for attempt in range(max_retries + 1):
                                    try:
                                        response = await asyncio.wait_for(
                                            agent.arun(query), timeout=25.0
                                        )
                                        result = (
                                            response.content
                                            if hasattr(response, "content")
                                            else str(response)
                                        )

                                        agent_span.set_attribute(
                                            "response.length", len(result)
                                        )
                                        span.set_attribute(
                                            "response.length", len(result)
                                        )

                                        logger.info(
                                            "Flight search completed successfully"
                                        )
                                        return result

                                    except asyncio.TimeoutError:
                                        if attempt < max_retries:
                                            logger.warning(
                                                f"Agent execution timeout on attempt {attempt + 1}, retrying..."
                                            )
                                            await asyncio.sleep(1)
                                            continue
                                        else:
                                            raise

                                    except Exception as agent_error:
                                        if (
                                            "TaskGroup" in str(agent_error)
                                            and attempt < max_retries
                                        ):
                                            logger.warning(
                                                f"TaskGroup error on attempt {attempt + 1}, retrying: {agent_error}"
                                            )
                                            await asyncio.sleep(2)
                                            continue
                                        else:
                                            raise

                    except asyncio.TimeoutError:
                        error_msg = (
                            "The flight search request timed out after 30 seconds."
                        )
                        logger.error(
                            f"Timeout error during flight search with '{python_cmd}': {query}"
                        )
                        span.set_attribute("error.type", "timeout")
                        span.set_attribute("error.message", error_msg)
                        return error_msg

                    except Exception as cmd_error:
                        last_error = cmd_error
                        error_str = str(cmd_error)

                        # Log the full exception details for TaskGroup errors
                        if "TaskGroup" in error_str:
                            logger.error(
                                f"TaskGroup error details for '{python_cmd}':",
                                exc_info=True,
                            )

                            # Try to extract more details from the exception
                            if hasattr(cmd_error, "__cause__") and cmd_error.__cause__:
                                logger.error(
                                    f"TaskGroup underlying cause: {cmd_error.__cause__}"
                                )
                            if (
                                hasattr(cmd_error, "__context__")
                                and cmd_error.__context__
                            ):
                                logger.error(
                                    f"TaskGroup context: {cmd_error.__context__}"
                                )
                            if hasattr(cmd_error, "exceptions"):
                                logger.error(
                                    f"TaskGroup exceptions: {cmd_error.exceptions}"
                                )
                        else:
                            logger.warning(
                                f"Failed to start MCP server with '{python_cmd}': {cmd_error}"
                            )
                        continue

                # If we get here, all commands failed
                if last_error:
                    error_str = str(last_error)
                    logger.error(
                        f"All MCP server commands failed. Last error: {last_error}",
                        exc_info=True,
                    )

                    span.set_attribute("error.type", "mcp_agent_error")
                    span.set_attribute("error.message", error_str)

                    if "Timed out while waiting for response" in error_str:
                        error_msg = (
                            "The MCP server timed out while fetching flight data."
                        )
                    elif "Connection" in error_str or "connection" in error_str:
                        error_msg = "Failed to connect to the MCP server. Please ensure it's properly configured."
                    elif "fastmcp" in error_str and "not found" in error_str.lower():
                        error_msg = (
                            "The 'fastmcp' command was not found. Please install dev dependencies:\n"
                            "• Run: `uv sync --dev`\n"
                            "• Or install fastmcp: `uv add --dev fastmcp`"
                        )
                    else:
                        error_msg = f"An unexpected error occurred during flight search: {error_str}"

                    return error_msg

            except Exception as e:
                # Catch any other unexpected errors
                error_str = str(e)
                logger.error(
                    f"Unexpected error during flight search: {e}", exc_info=True
                )

                span.set_attribute("error.type", "unexpected_error")
                span.set_attribute("error.message", error_str)

                return f"An unexpected error occurred: {error_str}"
