import re
from typing import Optional
import datetime

import pandas as pd
import streamlit as st
from config import EXPECTED_MULTI_CITY_LEGS, PRICE_DECIMAL_PLACES, SUGGESTION_QUERIES

# Import airport lookup functions
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Import the underlying function directly
def get_airport_name_from_code(airport_code: str) -> str:
    """Get airport name from IATA code using the airport database."""
    try:
        # Load airport codes
        airport_codes_path = Path(__file__).parent.parent / "data" / "airport-codes.csv"
        all_codes = pd.read_csv(airport_codes_path)
        
        matching_rows = all_codes[all_codes["iata_code"] == airport_code]
        if not matching_rows.empty:
            return matching_rows.iloc[0]["name"]
    except Exception:
        pass
    return None


def extract_numeric_prices(prices: pd.Series) -> list[float]:
    """Extract numeric values from price strings."""
    numeric_prices = []
    for price in prices:
        numbers = re.findall(r"\d+\.?\d*", str(price))
        if numbers:
            numeric_prices.append(float(numbers[0]))
    return numeric_prices



def get_flight_type_info(results: pd.DataFrame) -> tuple[bool, bool, int]:
    """Determine flight type characteristics from the results DataFrame."""
    has_outbound = (
        "direction" in results.columns and (results["direction"] == "outbound").any()
    )
    has_return = (
        "direction" in results.columns and (results["direction"] == "return").any()
    )
    is_round_trip = has_outbound and has_return

    unique_segments = (
        results["route"].nunique() if "route" in results.columns else 1
    )
    is_multi_city = unique_segments > 2 or (unique_segments == 2 and not is_round_trip)

    return is_round_trip, is_multi_city, unique_segments


def get_route_segments(results: pd.DataFrame) -> list[str]:
    """Get all route segments from the results DataFrame."""
    if "route" in results.columns:
        return sorted(results["route"].unique())
    elif "direction" in results.columns:
        # For round-trip flights, use direction as segments
        directions = []
        if (results["direction"] == "outbound").any():
            directions.append("outbound")
        if (results["direction"] == "return").any():
            directions.append("return")
        return directions
    else:
        # Single route
        return ["single"]


def calculate_combined_route_prices(results: pd.DataFrame) -> Optional[dict]:
    """
    Calculate combined prices for multi-segment routes.
    Returns min, max, and avg combined prices, or None if not applicable.
    """
    if "price" not in results.columns or not results["price"].notna().any():
        return None

    segments = get_route_segments(results)

    # For single segment routes, return individual flight prices
    if len(segments) == 1:
        return _calculate_single_segment_prices(results)

    # For multi-segment routes, calculate combinations
    return _calculate_multi_segment_prices(results, segments)


def _calculate_single_segment_prices(results: pd.DataFrame) -> Optional[dict]:
    """Calculate prices for single segment routes."""
    price_df = results[results["price"].notna() & (results["price"] != "-")]
    if price_df.empty:
        return None

    try:
        numeric_prices = extract_numeric_prices(price_df["price"])
        if not numeric_prices:
            return None

        return {
            "min_price": min(numeric_prices),
            "max_price": max(numeric_prices),
            "avg_price": sum(numeric_prices) / len(numeric_prices),
            "price_type": "Price",
        }
    except Exception:
        return None


def _calculate_multi_segment_prices(
    results: pd.DataFrame, segments: list[str]
) -> Optional[dict]:
    """Calculate combined prices for multi-segment routes."""
    segment_prices = {}

    for segment in segments:
        if segment in ["outbound", "return"]:
            segment_data = results[results["direction"] == segment]
        else:
            segment_data = results[results["route"] == segment]

        if segment_data.empty:
            continue

        segment_price_df = segment_data[
            segment_data["price"].notna() & (segment_data["price"] != "-")
        ]

        if segment_price_df.empty:
            continue

        try:
            numeric_prices = extract_numeric_prices(segment_price_df["price"])
            if numeric_prices:
                segment_prices[segment] = {
                    "min": min(numeric_prices),
                    "max": max(numeric_prices),
                    "prices": numeric_prices,
                }
        except Exception:
            continue

    if not segment_prices or len(segment_prices) != len(segments):
        return None

    # Calculate combined prices
    min_combined = sum(segment_prices[seg]["min"] for seg in segments)
    max_combined = sum(segment_prices[seg]["max"] for seg in segments)

    # Calculate average of all possible combinations
    all_combinations = _generate_price_combinations(segment_prices, segments)
    avg_combined = (
        sum(all_combinations) / len(all_combinations)
        if all_combinations
        else min_combined
    )

    # Determine price type label
    if len(segments) == 2 and "outbound" in segments and "return" in segments:
        price_type = "Round-Trip"
    else:
        price_type = f"{len(segments)}-Segment Trip"

    return {
        "min_price": min_combined,
        "max_price": max_combined,
        "avg_price": avg_combined,
        "price_type": price_type,
    }


def _generate_price_combinations(
    segment_prices: dict, segments: list[str]
) -> list[float]:
    """Generate all possible price combinations for segments."""
    if not segments:
        return []

    if len(segments) == 1:
        return segment_prices[segments[0]]["prices"]

    # Recursively generate combinations
    first_segment = segments[0]
    remaining_segments = segments[1:]

    remaining_combinations = _generate_price_combinations(
        segment_prices, remaining_segments
    )

    combinations = []
    for price in segment_prices[first_segment]["prices"]:
        if remaining_combinations:
            for remaining_price in remaining_combinations:
                combinations.append(price + remaining_price)
        else:
            combinations.append(price)

    return combinations


def display_price_metrics(results: pd.DataFrame) -> None:
    """Display unified price statistics for any route type."""
    price_data = calculate_combined_route_prices(results)

    if price_data:
        _display_price_columns(
            price_data["min_price"],
            price_data["max_price"],
            price_data["avg_price"],
            price_data["price_type"],
        )


def _display_price_columns(
    min_price: float, max_price: float, avg_price: float, price_type: str
) -> None:
    """Display price metrics in three columns."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(f"💰 Lowest {price_type}", f"£{min_price:.{PRICE_DECIMAL_PLACES}f}")
    with col2:
        st.metric(f"📊 Average {price_type}", f"£{avg_price:.{PRICE_DECIMAL_PLACES}f}")
    with col3:
        st.metric(f"📈 Highest {price_type}", f"£{max_price:.{PRICE_DECIMAL_PLACES}f}")


def extract_airport_info(airport_code: str) -> str:
    """Extract airport name and code for display."""
    try:
        if not airport_code or airport_code.strip() == "":
            return airport_code
            
        # Handle cases where it might already be formatted like "City (CODE)" 
        if "(" in airport_code and ")" in airport_code:
            return airport_code  # Already formatted
            
        # Remove any extra text and get just the airport code
        code = airport_code.strip().upper()
        
        # Extract 3-letter IATA code if embedded in longer string
        iata_match = re.search(r'\b[A-Z]{3}\b', code)
        if iata_match:
            code = iata_match.group()
        
        if len(code) == 3 and code.isalpha():  # Valid IATA code
            airport_name = get_airport_name_from_code(code)
            if airport_name:
                return f"{airport_name} ({code})"
        
        # If lookup fails or invalid code, return original
        return airport_code
    except Exception as e:
        # Log error but don't break the display
        print(f"Error looking up airport {airport_code}: {e}")
        return airport_code


def extract_time_from_datetime(time_str: str) -> str:
    """Extract just the time portion from datetime string and convert to 24-hour format."""
    try:
        # Handle various time formats
        if not time_str or time_str == "-" or str(time_str).strip() == "":
            return time_str
        
        time_str = str(time_str).strip()
        
        # Handle format like "2:10 PM on Sun, Aug 10"
        if " on " in time_str.lower():
            time_part = time_str.split(" on ")[0].strip()
            time_str = time_part
        
        # Convert AM/PM format to 24-hour format for proper sorting
        if re.match(r'^\d{1,2}:\d{2}\s*(AM|PM)$', time_str, re.IGNORECASE):
            try:
                import datetime
                # Parse the AM/PM time and convert to 24-hour format
                time_obj = datetime.datetime.strptime(time_str, "%I:%M %p")
                return time_obj.strftime("%H:%M")
            except ValueError:
                # If parsing fails, return original
                return time_str
        
        # If it's already in 24-hour format (HH:MM), return as is
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
            return time_str[:5]  # Return HH:MM format
            
        # If it contains a space, likely datetime format like "2024-01-10 14:30:00"
        if " " in time_str:
            parts = time_str.split(" ")
            if len(parts) >= 2:
                time_part = parts[1]  # Take second part as time
                # Validate it looks like a time
                if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_part):
                    return time_part[:5]  # Return HH:MM format
        
        # If it looks like a date (YYYY-MM-DD), this might be a date column not time
        if re.match(r'^\d{4}-\d{2}-\d{2}$', time_str):
            return "-"  # Return dash for missing time
            
        # Try to parse as datetime and extract time
        import datetime
        try:
            # Try various datetime formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"]:
                try:
                    dt = datetime.datetime.strptime(time_str, fmt)
                    return dt.strftime("%H:%M")
                except ValueError:
                    continue
        except:
            pass
            
        # If all else fails, return original
        return time_str
        
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")
        return str(time_str)


def get_departure_date_for_display(results_display: pd.DataFrame) -> str:
    """Extract departure date for header display."""
    try:
        if "departure_date" in results_display.columns:
            dates = results_display["departure_date"].dropna().unique()
            if len(dates) > 0:
                date_str = str(dates[0])
                # Try to parse and format the date nicely
                try:
                    parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    return parsed_date.strftime("%B %d, %Y")
                except:
                    return date_str
    except Exception:
        pass
    return ""


def convert_price_for_sorting(price_str: str) -> float:
    """Convert price string to numeric value for proper sorting."""
    try:
        if not price_str or price_str == "-" or str(price_str).strip() == "":
            return 0.0
        
        price_str = str(price_str).strip()
        
        # Extract numeric values from price strings using the existing function
        numbers = re.findall(r"\d+\.?\d*", price_str)
        if numbers:
            return float(numbers[0])
        
        return 0.0
    except Exception:
        return 0.0


def get_currency_symbol(price_str: str) -> str:
    """Extract currency symbol from price string."""
    try:
        if not price_str or price_str == "-":
            return "£"  # Default to pounds
        
        price_str = str(price_str).strip()
        
        # Check for common currency symbols
        if "£" in price_str:
            return "£"
        elif "$" in price_str:
            return "$"
        elif "€" in price_str:
            return "€"
        else:
            return "£"  # Default to pounds
    except Exception:
        return "£"


def display_flight_table(results_display: pd.DataFrame, show_date_in_header: bool = True) -> str:
    """Display a flight table with consistent formatting."""
    if results_display.empty:
        st.warning("No flights to display.")
        return ""

    # Extract departure date for header
    departure_date = get_departure_date_for_display(results_display) if show_date_in_header else ""

    # Create a copy to avoid modifying original
    results_to_show = results_display.copy()
    
    # Transform origin and destination to show airport names
    if "origin" in results_to_show.columns:
        results_to_show["from_display"] = results_to_show["origin"].apply(extract_airport_info)
    
    if "destination" in results_to_show.columns:
        results_to_show["to_display"] = results_to_show["destination"].apply(extract_airport_info)
    
    # Clean up time fields
    if "departure_time" in results_to_show.columns:
        results_to_show["departure_time_clean"] = results_to_show["departure_time"].apply(extract_time_from_datetime)
    
    if "arrival_time" in results_to_show.columns:
        results_to_show["arrival_time_clean"] = results_to_show["arrival_time"].apply(extract_time_from_datetime)

    # Convert price to numeric for proper sorting while keeping display format
    if "price" in results_to_show.columns:
        # Create a numeric price column for sorting
        results_to_show["price_numeric"] = results_to_show["price"].apply(convert_price_for_sorting)

    # Define the new preferred column order
    preferred_columns = [
        "from_display",
        "departure_time_clean", 
        "to_display",
        "arrival_time_clean",
        "duration",
        "price_numeric",  # Use numeric price instead of original
        "airline",
        "stops",
    ]

    # Only show available columns
    available_columns = [
        col for col in preferred_columns if col in results_to_show.columns
    ]

    if available_columns:
        results_final = results_to_show[available_columns]
        
        # Define column renames
        column_renames = {
            "from_display": "From",
            "departure_time_clean": "Departure Time",
            "to_display": "To", 
            "arrival_time_clean": "Arrival Time",
            "duration": "Duration",
            "price_numeric": "Price (£)",  # Show it's numeric and indicate currency
            "airline": "Airline",
            "stops": "Stops",
        }
        
        results_final = results_final.rename(
            columns={
                k: v for k, v in column_renames.items() if k in results_final.columns
            }
        )
        
        # Format the numeric price column to show currency properly
        if "Price (£)" in results_final.columns:
            # Detect the actual currency from the original price data
            if "price" in results_to_show.columns and not results_to_show["price"].empty:
                sample_price = results_to_show["price"].iloc[0]
                currency_symbol = get_currency_symbol(sample_price)
                
                # Update column name to reflect actual currency
                if currency_symbol != "£":
                    results_final = results_final.rename(columns={"Price (£)": f"Price ({currency_symbol})"})
                    column_name = f"Price ({currency_symbol})"
                else:
                    column_name = "Price (£)"
                
                results_final[column_name] = results_final[column_name].apply(
                    lambda x: f"{currency_symbol}{x:.2f}" if x > 0 else "-"
                )
            else:
                results_final["Price (£)"] = results_final["Price (£)"].apply(
                    lambda x: f"£{x:.2f}" if x > 0 else "-"
                )
        
    else:
        results_final = results_to_show

    st.dataframe(results_final, use_container_width=True, hide_index=True)
    return departure_date


def display_flight_results(
    results: pd.DataFrame, summary: Optional[str] = None
) -> None:
    """Display search results in a clean table format."""
    if results.empty:
        st.warning("No flights found.")
        return

    try:
        # Display summary if provided
        if summary:
            st.write(summary)

        # Drop duplicates
        results = results.drop_duplicates()

        is_round_trip, is_multi_city, unique_segments = get_flight_type_info(results)

        # Display unified price metrics for all route types
        display_price_metrics(results)

        if is_round_trip:
            _display_round_trip_results(results)
        elif is_multi_city:
            _display_multi_city_results(results, unique_segments)
        else:
            _display_one_way_results(results)

    except Exception as e:
        st.error(f"Error displaying results: {str(e)}")


def _display_round_trip_results(results: pd.DataFrame) -> None:
    """Display round-trip flight results."""
    st.subheader("🔄 Round Trip Flights")

    # Split into outbound and return flights
    outbound_flights = results[results["direction"] == "outbound"]
    return_flights = results[results["direction"] == "return"]

    # Display flight sections with dates in headers
    outbound_date = ""
    return_date = ""
    
    if not outbound_flights.empty:
        outbound_date = get_departure_date_for_display(outbound_flights)
        header_text = "#### ✈️ Outbound Flights"
        if outbound_date:
            header_text += f" - {outbound_date}"
        st.markdown(header_text)
        display_flight_table(outbound_flights, show_date_in_header=False)

    if not return_flights.empty:
        return_date = get_departure_date_for_display(return_flights)
        header_text = "#### 🔙 Return Flights"
        if return_date:
            header_text += f" - {return_date}"
        st.markdown(header_text)
        display_flight_table(return_flights, show_date_in_header=False)


def _display_multi_city_results(results: pd.DataFrame, unique_segments: int) -> None:
    """Display multi-city flight results."""
    st.subheader("🗺️ Multi-City Trip")

    if "route" in results.columns:
        _display_multi_city_segments(results, unique_segments)
    else:
        departure_date = display_flight_table(results)
        # Update header to include date if available
        if departure_date:
            st.markdown(f"**Departure Date: {departure_date}**")


def _display_multi_city_segments(results: pd.DataFrame, unique_segments: int) -> None:
    """Display individual segments of a multi-city trip."""
    segments = results["route"].unique()

    # Check for incomplete multi-city trips
    if unique_segments < EXPECTED_MULTI_CITY_LEGS:
        st.info(
            f"ℹ️ Showing {unique_segments} available leg(s) of your multi-city trip."
        )

    for i, segment in enumerate(segments, 1):
        segment_flights = results[results["route"] == segment]
        
        departure_date = get_departure_date_for_display(segment_flights)
        header_text = f"#### Leg {i}: {segment}"
        if departure_date:
            header_text += f" - {departure_date}"
        st.markdown(header_text)
        display_flight_table(segment_flights, show_date_in_header=False)


def _display_one_way_results(results: pd.DataFrame) -> None:
    """Display one-way flight results."""
    departure_date = get_departure_date_for_display(results)
    header_text = "✈️ Flight Options"
    if departure_date:
        header_text += f" - {departure_date}"
    st.subheader(header_text)
    display_flight_table(results, show_date_in_header=False)


def render_suggestion_buttons() -> None:
    """Render suggestion buttons for common queries."""
    st.markdown("##### 💡 Try these examples:")

    cols = st.columns(len(SUGGESTION_QUERIES))
    for i, suggestion_text in enumerate(SUGGESTION_QUERIES):
        if cols[i].button(suggestion_text, key=f"suggestion_{i}"):
            st.session_state.query_text = suggestion_text


def handle_search_results(result: dict) -> None:
    """Handle and display search results."""
    if result.get("success"):
        results_obj = result.get("results")
        st.header("📋 Search Results")

        if results_obj and results_obj.results:
            # Convert results to DataFrame
            list_of_flat_records = [
                record.model_dump() for record in results_obj.results
            ]
            df = pd.DataFrame(list_of_flat_records)
        else:
            df = pd.DataFrame()

        summary = results_obj.summary if results_obj else "No summary available."
        display_flight_results(df, summary)
    else:
        error_message = result.get("error", "Unknown error")
        st.error(f"❌ Search failed: {error_message}")
