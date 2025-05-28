import asyncio
import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv
import logging
from pathlib import Path

load_dotenv()

logger = logging.getLogger(__name__)


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
        try:
            logger.info(f"Starting flight search for query: {query}")

            project_root = Path(__file__).parent.parent
            mcp_server_path = (
                project_root.parent / "Google-Flights-MCP-Server" / "server.py"
            )

            if not mcp_server_path.exists():
                return (
                    "❌ **MCP Server Not Found**\n\n"
                    f"The Google Flights MCP Server was not found at: `{mcp_server_path}`\n\n"
                    "**Setup Instructions:**\n"
                    "1. Clone the Google Flights MCP Server repository\n"
                    "2. Ensure it's located at `../Google-Flights-MCP-Server/`\n"
                    "3. Install its dependencies\n"
                    "4. Restart the backend server"
                )

            async with MCPTools(
                f"fastmcp run {mcp_server_path}", timeout_seconds=30.0
            ) as mcp_tools:
                agent = Agent(
                    model=OpenAIChat(id="gpt-4o-mini", api_key=self.api_key),
                    tools=[mcp_tools],
                    show_tool_calls=False,
                    markdown=True,
                )

                logger.info("MCP tools initialized, running agent...")

                response = await agent.arun(query)
                result = (
                    response.content if hasattr(response, "content") else str(response)
                )

                logger.info("Flight search completed successfully")
                return result

        except asyncio.TimeoutError:
            error_msg = "The flight search request timed out after 30 seconds."
            logger.error(f"Timeout error during flight search: {query}")
            return error_msg

        except Exception as e:
            if "Timed out while waiting for response" in str(e):
                error_msg = "The MCP server timed out while fetching flight data."
            else:
                error_msg = f"An unexpected error occurred: {str(e)}"
            logger.error(f"Error during flight search: {e}")
            return error_msg

    def search_flights_sync(self, query: str) -> str:
        """
        Synchronous wrapper for flight search.

        Args:
            query: Natural language flight search query

        Returns:
            Flight search results as a string
        """
        return asyncio.run(self.search_flights(query))
