from agno.models.openai import OpenAIChat
from agno.team import Team
from agno.agent import Agent
from backend.flight_service import FlightService
from backend.models import FlightSearchResults, TravelItinerary
from backend.observability import get_tracer
import logging
import os
from opentelemetry import trace as trace_api
import asyncio

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class TravelOrchestrator:
    """Orchestrates multiple agents for complex travel planning using agno.team."""

    def __init__(self):
        with tracer.start_as_current_span("orchestrator_init") as span:
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                span.set_attribute("error", "Missing OPENAI_API_KEY")
                span.set_status(trace_api.StatusCode.ERROR, "Missing API key")
                raise ValueError("OPENAI_API_KEY environment variable is required")

            self.flight_service = FlightService()
            self.model = OpenAIChat(id="gpt-4o-mini", api_key=self.api_key)
            
            span.set_attribute("model_id", "gpt-4o-mini")
            span.set_attribute("initialization_complete", True)

    def _create_travel_team(self) -> Team:
        """Create a team of agents for travel planning."""
        with tracer.start_as_current_span("create_travel_team") as span:
            span.set_attribute("team_type", "travel_planning")
            
            # Task breakdown agent
            with tracer.start_as_current_span("create_task_analyzer_agent"):
                task_analyzer = Agent(
                    model=self.model,
                    name="task_analyzer",
                    role="Travel Query Analyzer",
                    goal="Break down complex travel requests into specific, actionable flight search tasks",
                    backstory="You are an expert travel planner who specializes in understanding complex travel requirements.",
                    instructions=[
                        "Analyze travel queries and identify all distinct flight searches needed",
                        "Extract origin, destination, dates, passenger count, and preferences for each flight",
                        "Handle multi-city trips, round trips, and complex itineraries",
                        "Return structured information in a clear format",
                        "Consider different travel scenarios and requirements",
                    ],
                    show_tool_calls=True,
                    markdown=False,
                    debug_mode=True,
                )

            # Flight search coordinator
            with tracer.start_as_current_span("create_flight_coordinator_agent"):
                flight_coordinator = Agent(
                    model=self.model,
                    name="flight_coordinator",
                    role="Flight Search Coordinator",
                    goal="Coordinate multiple flight searches and gather results",
                    backstory="You are a flight search specialist who coordinates multiple searches efficiently.",
                    instructions=[
                        "Execute flight searches based on the breakdown from the task analyzer",
                        "Coordinate multiple concurrent flight searches",
                        "Gather and organize all flight search results",
                        "Present flight information in a consistent format with:",
                        "- Airlines and flight numbers",
                        "- Departure and arrival times",
                        "- Prices and booking classes",
                        "- Duration and stops information",
                        "- Clear routing details",
                        "Handle any errors or issues during searches",
                    ],
                    show_tool_calls=True,
                    markdown=True,
                    debug_mode=True,
                )

            # Results synthesizer
            with tracer.start_as_current_span("create_results_synthesizer_agent"):
                results_synthesizer = Agent(
                    model=self.model,
                    name="results_synthesizer",
                    role="Travel Results Synthesizer",
                    goal="Combine flight search results into comprehensive travel recommendations",
                    backstory="You are a travel coordinator who creates clear, actionable travel plans from multiple search results.",
                    instructions=[
                        "Analyze all flight search results and organize them logically",
                        "Present information in a standardized format:",
                        "## Flight Options",
                        "### Route: [Origin] → [Destination]",
                        "**Option 1:** [Airline] [Flight#] - $[Price]",
                        "- Departure: [Time] from [Airport]",
                        "- Arrival: [Time] at [Airport]",
                        "- Duration: [Time] ([Stops] stops)",
                        "- Class: [Class]",
                        "",
                        # "Group related flights (outbound/return, multi-city connections)",
                        # "Highlight best options based on price, timing, and convenience",
                        # "Provide clear next steps for booking",
                        # "Include total estimated costs where possible",
                    ],
                    show_tool_calls=True,
                    markdown=True,
                    debug_mode=True,
                )

            # Create and return the team
            with tracer.start_as_current_span("instantiate_team") as team_span:
                team = Team(
                    agents=[task_analyzer, flight_coordinator, results_synthesizer],
                    name="travel_planning_team",
                    description="Team of agents that work together to plan complex travel itineraries",
                    planning_agent=task_analyzer,  # The task analyzer leads the planning
                    show_tool_calls=True,
                )
                
                team_span.set_attribute("agent_count", len(team.agents))
                team_span.set_attribute("team_name", "travel_planning_team")
                team_span.set_attribute("planning_agent", "task_analyzer")
                team_span.set_attribute("debug_mode_enabled", True)
                
            span.set_attribute("team_creation_complete", True)
            return team

    async def _trace_agent_execution(self, agent, task: str, span_name: str = None):
        """Execute an agent with detailed tracing."""
        agent_name = getattr(agent, 'name', 'unknown_agent')
        span_name = span_name or f"{agent_name}_execution"
        
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("agent.name", agent_name)
            span.set_attribute("agent.role", getattr(agent, 'role', 'unknown_role'))
            span.set_attribute("agent.model", getattr(agent.model, 'id', 'unknown_model'))
            span.set_attribute("task.length", len(task))
            span.set_attribute("task.preview", task[:200] + "..." if len(task) > 200 else task)
            
            try:
                logger.info(f"Executing agent: {agent_name}")
                
                # Add timeout to prevent hanging
                response = await asyncio.wait_for(agent.arun(task), timeout=60.0)
                
                # Extract response content
                response_content = (
                    response.content if hasattr(response, 'content') 
                    else str(response)
                )
                
                span.set_attribute("response.length", len(response_content))
                span.set_attribute("response.preview", response_content[:200] + "..." if len(response_content) > 200 else response_content)
                span.set_attribute("execution.success", True)
                
                logger.info(f"Agent {agent_name} completed successfully")
                return response_content
                
            except asyncio.TimeoutError:
                error_msg = f"Agent {agent_name} timed out after 60 seconds"
                span.set_attribute("execution.timeout", True)
                span.set_attribute("error.message", error_msg)
                span.set_status(trace_api.StatusCode.ERROR, error_msg)
                logger.error(error_msg)
                raise
                
            except Exception as e:
                error_msg = f"Agent {agent_name} execution failed: {str(e)}"
                span.set_attribute("execution.failed", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(trace_api.StatusCode.ERROR, str(e))
                logger.error(error_msg, exc_info=True)
                raise

    async def _trace_team_execution(self, team, task: str):
        """Execute a team with detailed tracing."""
        with tracer.start_as_current_span("team_execution") as span:
            span.set_attribute("team.name", getattr(team, 'name', 'unknown_team'))
            span.set_attribute("team.agents_count", len(team.agents))
            span.set_attribute("team.planning_agent", getattr(team.planning_agent, 'name', 'unknown_planning_agent'))
            span.set_attribute("task.length", len(task))
            span.set_attribute("task.preview", task[:200] + "..." if len(task) > 200 else task)
            
            try:
                logger.info(f"Executing team: {team.name}")
                
                # Add timeout to prevent hanging
                response = await asyncio.wait_for(team.arun(task), timeout=120.0)
                
                # Extract response content
                response_content = (
                    response.content if hasattr(response, 'content') 
                    else str(response)
                )
                
                span.set_attribute("response.length", len(response_content))
                span.set_attribute("response.preview", response_content[:200] + "..." if len(response_content) > 200 else response_content)
                span.set_attribute("execution.success", True)
                
                logger.info(f"Team {team.name} completed successfully")
                return response_content
                
            except asyncio.TimeoutError:
                error_msg = f"Team {team.name} timed out after 120 seconds"
                span.set_attribute("execution.timeout", True)
                span.set_attribute("error.message", error_msg)
                span.set_status(trace_api.StatusCode.ERROR, error_msg)
                logger.error(error_msg)
                raise
                
            except Exception as e:
                error_msg = f"Team {team.name} execution failed: {str(e)}"
                span.set_attribute("execution.failed", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(trace_api.StatusCode.ERROR, str(e))
                logger.error(error_msg, exc_info=True)
                raise

    async def orchestrate_travel_search(self, query: str) -> TravelItinerary:
        """
        Orchestrate a complex travel search using agno.team.

        Args:
            query: Complex travel query that may require multiple flight searches

        Returns:
            TravelItinerary with structured flight data
        """
        with tracer.start_as_current_span("travel_orchestration") as span:
            span.set_attribute("original_query", query)
            span.set_attribute("query_length", len(query))

            logger.info(f"Starting team-based travel orchestration for: {query}")

            try:
                # Create the travel planning team
                with tracer.start_as_current_span("team_creation"):
                    travel_team = self._create_travel_team()

                # Execute a flight search with structured parsing
                with tracer.start_as_current_span("flight_search_execution") as search_span:
                    search_span.set_attribute("search_type", "structured")
                    flight_results = await self.flight_service.search_flights_structured(
                        query
                    )
                    
                    search_span.set_attribute("origin", flight_results.origin)
                    search_span.set_attribute("destination", flight_results.destination)
                    search_span.set_attribute("departure_date", str(flight_results.departure_date))
                    search_span.set_attribute("flight_options_count", len(flight_results.flight_options))

                # Use the team to analyze and plan the travel
                with tracer.start_as_current_span("team_planning_execution") as team_span:
                    team_span.set_attribute("team_name", "travel_planning_team")
                    team_span.set_attribute("agents_count", len(travel_team.agents))
                    
                    # Create a comprehensive task for the team
                    team_task = f"""
                    Analyze this travel request and create a comprehensive travel plan:
                    
                    Original request: "{query}"
                    
                    Available flight data:
                    - Origin: {flight_results.origin}
                    - Destination: {flight_results.destination}
                    - Date: {flight_results.departure_date}
                    - Found {len(flight_results.flight_options)} flight options
                    - Flight details: {flight_results}
                    
                    Please work together as a team to:
                    1. Analyze the travel requirements
                    2. Review the available flight options
                    3. Provide comprehensive recommendations with clear formatting
                    """
                    
                    team_span.set_attribute("team_task_length", len(team_task))
                    logger.info(f"Executing team planning for travel request")
                    
                    # Execute the team workflow
                    with tracer.start_as_current_span("team_run_execution") as run_span:
                        run_span.set_attribute("execution_type", "team_arun")
                        
                        try:
                            team_response = await self._trace_team_execution(travel_team, team_task)
                            
                            # Extract the content from team response
                            team_recommendations = team_response
                            
                            run_span.set_attribute("team_response_length", len(team_recommendations))
                            run_span.set_attribute("team_execution_success", True)
                            
                        except Exception as team_error:
                            logger.warning(f"Team execution failed, falling back to individual agent: {team_error}")
                            run_span.set_attribute("team_execution_failed", True)
                            run_span.set_attribute("team_error", str(team_error))
                            
                            # Fallback to individual agent execution
                            with tracer.start_as_current_span("fallback_agent_execution") as fallback_span:
                                synthesizer = travel_team.agents[2]  # results_synthesizer
                                fallback_span.set_attribute("agent_name", "results_synthesizer") 
                                fallback_span.set_attribute("agent_role", synthesizer.role)
                                
                                fallback_prompt = f"""
                                Original travel request: "{query}"
                                
                                Flight search results:
                                - Origin: {flight_results.origin}
                                - Destination: {flight_results.destination}
                                - Date: {flight_results.departure_date}
                                - Found {len(flight_results.flight_options)} flight options
                                
                                Raw flight data: {flight_results}
                                
                                Please provide a comprehensive travel recommendation using the standardized format specified in your instructions.
                                Focus on presenting the flight options clearly with all key details.
                                """
                                
                                fallback_span.set_attribute("prompt_length", len(fallback_prompt))
                                
                                try:
                                    agent_response = await self._trace_agent_execution(synthesizer, fallback_prompt)
                                    team_recommendations = agent_response
                                    fallback_span.set_attribute("agent_response_length", len(team_recommendations))
                                    fallback_span.set_attribute("agent_execution_success", True)
                                    
                                except Exception as agent_error:
                                    fallback_span.set_attribute("agent_execution_failed", True)
                                    fallback_span.set_attribute("agent_error", str(agent_error))
                                    team_recommendations = f"Agent execution failed: {agent_error}"

                # Create travel itinerary
                with tracer.start_as_current_span("itinerary_creation") as itinerary_span:
                    itinerary = TravelItinerary(
                        original_query=query,
                        flight_searches=[flight_results],
                        recommendations=team_recommendations,
                    )
                    
                    itinerary_span.set_attribute("recommendations_length", len(team_recommendations))
                    itinerary_span.set_attribute("flight_searches_count", len(itinerary.flight_searches))

                span.set_attribute("team_workflow_completed", True)
                span.set_attribute("success", True)
                logger.info("Team-based travel orchestration completed successfully")

                return itinerary

            except Exception as e:
                logger.error(
                    f"Error in team-based travel orchestration: {e}", exc_info=True
                )
                span.set_attribute("error", str(e))
                span.set_attribute("error_type", type(e).__name__)
                span.set_status(trace_api.StatusCode.ERROR, str(e))

                # Fallback to simple flight search
                with tracer.start_as_current_span("fallback_search") as fallback_span:
                    logger.info("Falling back to simple flight search...")
                    fallback_span.set_attribute("fallback_reason", "team_orchestration_failed")
                    
                    try:
                        fallback_result = await self.flight_service.search_flights(query)
                        fallback_span.set_attribute("fallback_success", True)
                        
                        # If the fallback also indicates MCP server issues, provide helpful guidance
                        if any(keyword in fallback_result.lower() for keyword in ["playwright", "scraping", "browser", "anti-bot"]):
                            fallback_result += (
                                "\n\n**Alternative Options:**\n"
                                "• Try searching for flights on major routes (LHR-JFK, LAX-LGW)\n"
                                "• Use different date formats (YYYY-MM-DD)\n"
                                "• Search for one route at a time\n"
                                "• Check flights manually on Google Flights, Skyscanner, or airline websites\n"
                                "• The MCP server may need updates due to Google Flights changes"
                            )
                            
                    except Exception as fallback_error:
                        fallback_span.set_attribute("fallback_error", str(fallback_error))
                        fallback_span.set_status(trace_api.StatusCode.ERROR, str(fallback_error))
                        fallback_result = (
                            "Both team orchestration and fallback search failed. "
                            "This may be due to Google Flights anti-bot measures or server issues. "
                            "Please try again later or search manually on flight booking websites."
                        )

                    return TravelItinerary(
                        original_query=query,
                        flight_searches=[
                            FlightSearchResults(
                                query=query,
                                error_message="Team orchestration failed, using fallback search",
                            )
                        ],
                        recommendations=f"Team orchestration encountered an issue, but here are the flight results:\n\n{fallback_result}",
                    )
