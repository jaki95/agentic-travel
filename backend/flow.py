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
from backend.models.search import QueryBreakdown
from backend.models.flights import FlightDisplayRecord


class FlightSearchState(BaseModel):
    message: str = ""
    query_breakdown: Optional[QueryBreakdown] = None
    search_results: Optional[list[FlightDisplayRecord]] = None


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
            args=["run", "../Google-Flights-MCP-Server/server.py"],
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
    def search_flights(self):
        server_params = self._create_mcp_server_params()

        with MCPServerAdapter(server_params) as tools:
            # Use the tools for flight search
            agent = create_structured_flight_agent(self.llm, tools)
            task = create_search_task(agent)
            crew = Crew(agents=[agent], tasks=[task], verbose=True)

            # Convert SearchQuery objects to dictionaries for kickoff_for_each
            search_inputs = [
                {"query": search.model_dump()}
                for search in self.state.query_breakdown.searches
            ]
            crew_outputs = crew.kickoff_for_each(inputs=search_inputs)

            # Extract FlightSearchResults from CrewOutput objects
            flight_results = []
            for crew_output in crew_outputs:
                if hasattr(crew_output, "tasks_output") and crew_output.tasks_output:
                    # Get the pydantic result from the first (and only) task
                    pydantic_result = crew_output.tasks_output[0].pydantic
                    if pydantic_result:
                        flight_results.append(pydantic_result)

            self.state.search_results = flight_results


if __name__ == "__main__":
    flow = FlightSearchFlow("flight from london to paris on 1st of june 2025")
    flow.kickoff()
