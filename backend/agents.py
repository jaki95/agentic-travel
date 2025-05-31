from crewai import LLM, Agent, Task

from backend.models.flights import FlightSearchResults
from backend.models.search import QueryBreakdown
from backend.tools import iata_code_to_name, name_to_iata_code


def create_query_analyzer_agent(llm: LLM) -> Agent:
    """Create agent to analyze and break down travel queries."""
    return Agent(
        role="Travel Query Analyzer",
        goal="Break down complex travel requests into specific flight search queries",
        backstory=(
            "You are an expert travel planner who specializes in understanding complex travel requirements. "
            "You excel at analyzing travel queries and identifying all distinct flight searches needed. "
            "You extract origin, destination, dates, passenger count, and determine if multiple searches are required."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_analysis_task(query: str, agent: Agent) -> Task:
    return Task(
        description=f"""
                    Analyze this travel request and break it down into individual flight searches:
                    "{query}"
                    
                    Determine:
                    1. How many separate flight searches are needed
                    2. Origin and destination for each search
                    3. The IATA code for the origin and destination (if the query contains a name, 
                    lookup the code using the tools, if it contains a code use the tools to lookup the name)
                    4. Departure dates (and return dates if round trip)
                    5. Number of passengers
                    6. Whether each search is one-way or round-trip
                    7. Whether the search is for direct flights only
                    
                    IMPORTANT: For international flights, prefer the main international hub over the secondary airport(s).
                    
                    For example:
                    - "Flight from NYC to Paris on Dec 15" → 1 search
                    - "Round trip NYC to Paris Dec 15-22" → 1 round-trip search  
                    - "Multi-city: NYC to Paris Dec 15, Paris to Rome Dec 20, Rome to NYC Dec 25" → 3 searches
                    """,
        expected_output="Structured breakdown of flight searches needed with origins, destinations, dates, and reasoning",
        agent=agent,
        output_pydantic=QueryBreakdown,
        tools=[name_to_iata_code, iata_code_to_name],
    )


def create_structured_flight_agent(llm: LLM, tools: list) -> Agent:
    """Create a flight search agent that returns top 10 sorted structured flight results."""
    return Agent(
        role="Structured Flight Data Analyst",
        goal=(
            "Search for flights and return ONLY valid JSON matching the schema. "
            "Return the TOP 10 flights sorted by (price + duration)."
        ),
        backstory=(
            "You are a specialized flight data analyst. You are given raw flight options "
            "and must return a structured JSON object that matches the given schema exactly. "
            "You must first sort the flight options by the sum of price and duration (ascending). "
            "Return ONLY the top 10 results. Do not include any explanation or text - just the JSON."
        ),
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
