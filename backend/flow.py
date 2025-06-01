import asyncio
import logging
import os
from typing import Optional

from crewai import LLM, Crew
from crewai.flow.flow import Flow, listen, start
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters
from pydantic import BaseModel

from backend.agents import (
    create_analysis_task,
    create_query_analyzer_agent,
    create_search_task,
    create_structured_flight_agent,
)
from backend.mcp.flight_server import MCP_SERVER_PATH
from backend.models.flights import FlightSearchResults
from backend.models.search import QueryBreakdown

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FlightSearchState(BaseModel):
    message: str = ""
    query_breakdown: Optional[QueryBreakdown] = None
    search_results: Optional[list[FlightSearchResults]] = None


class FlightSearchFlow(Flow[FlightSearchState]):
    def __init__(self, query: str):
        super().__init__()
        self.query = query
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm = LLM(
            model="gpt-4.1-mini",
            api_key=api_key,
            temperature=0.1,
            verbose=True,
        )

    def _create_mcp_server_params(self):
        """Create fresh MCP server parameters."""
        return StdioServerParameters(
            command="uv",
            args=["run", MCP_SERVER_PATH.as_posix()],
            env={"UV_PYTHON": "3.12", **os.environ},
        )

    @start()
    def break_down_query(self):
        query_analyzer = create_query_analyzer_agent(self.llm)
        analysis_task = create_analysis_task(self.query, query_analyzer)
        crew = Crew(agents=[query_analyzer], tasks=[analysis_task], verbose=True)
        result = crew.kickoff()
        print(result.tasks_output[0].pydantic)
        self.state.query_breakdown = result.tasks_output[0].pydantic

    @listen(break_down_query)
    async def search_flights(self):
        server_params = self._create_mcp_server_params()

        with MCPServerAdapter(server_params) as tools:
            for tool in tools:
                tool.result_as_answer = True

            # Use the tools for flight search
            agent = create_structured_flight_agent(self.llm, tools)
            tasks = [
                create_search_task(agent, search_query)
                for search_query in self.state.query_breakdown.searches
            ]
            crews = {
                search_query.id: Crew(agents=[agent], tasks=[task], verbose=True)
                for search_query, task in zip(
                    self.state.query_breakdown.searches, tasks
                )
            }

            result_promises = {
                search_query.id: crews[search_query.id].kickoff_async(
                    inputs={"query": search_query.model_dump()}
                )
                for search_query in self.state.query_breakdown.searches
            }
            results = await asyncio.gather(*result_promises.values())

            for i, result in enumerate(results, 1):
                logger.info(f"Search {i}/{len(results)} completed")

            # Extract FlightSearchResults objects from crew task outputs
            flight_search_results: list[FlightSearchResults] = []
            for result in results:
                if result.tasks_output and len(result.tasks_output) > 0:
                    task_output = result.tasks_output[0]
                    flight_search_results.append(task_output.pydantic)
                else:
                    logger.warning("No task outputs found in crew result")

            self.state.search_results = flight_search_results


if __name__ == "__main__":
    flow = FlightSearchFlow("flight from london to paris on 1st of june 2025")
    flow.kickoff()
