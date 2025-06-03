from pathlib import Path
from crewai import LLM, Agent, Task
from crewai.tools import BaseTool
import yaml

from backend.models.flights import FlightSearchResults
from backend.models.search import QueryBreakdown
from backend.tools import iata_code_to_name, name_to_iata_code


with open(Path(__file__).parent / "config" / "agents.yaml", "r") as f:
    agents_config = yaml.safe_load(f)

with open(Path(__file__).parent / "config" / "tasks.yaml", "r") as f:
    tasks_config = yaml.safe_load(f)

def create_query_analyzer_agent(llm: LLM) -> Agent:
    """Create agent to analyze and break down travel queries."""
    return Agent(
        config=agents_config["query_analyser"],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_analysis_task(agent: Agent) -> Task:
    return Task(
        config=tasks_config["analysis_task"],
        agent=agent,
        output_pydantic=QueryBreakdown,
        tools=[name_to_iata_code, iata_code_to_name],
    )


def create_structured_flight_agent(llm: LLM, tools: list[BaseTool]) -> Agent:
    """Create a flight search agent that returns top 10 sorted structured flight results."""
    return Agent(
        config=agents_config["flight_finder"],
        llm=llm,
        tools=tools,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_search_task(agent: Agent, query: str) -> Task:
    return Task(
        description=f"""
        Search for flights based on the input query: {query}.
        Use the tools provided to gather raw flight options.
        Then, sort the flights by (price + duration) in ascending order.
        Return ONLY the top 10 flights as a valid JSON object that matches the expected schema exactly.
            
        The route_segment will be in format like "JFK→CDG", "CDG→FCO", etc.
        
        Do not include any other output.
        """,
        expected_output="Valid JSON object containing up to 10 flights sorted by (price + duration).",
        agent=agent,
        output_pydantic=FlightSearchResults,
    )
