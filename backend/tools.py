from pathlib import Path

import pandas as pd
from crewai.tools import tool
from pydantic import BaseModel


class Airport(BaseModel):
    name: str
    code: str


AIRPORT_CODES_PATH = Path(__file__).parent.parent / "data" / "airport-codes.csv"


def load_airport_codes() -> pd.DataFrame:
    return pd.read_csv(AIRPORT_CODES_PATH)


@tool
def airport_codes_lookup(airport_name: str) -> list[Airport]:
    """Lookup the airport code for a given airport or city name."""

    all_codes = load_airport_codes()
    # Use case-insensitive partial matching to find airports containing the input text
    matching_rows = all_codes[
        all_codes["name"].str.contains(airport_name, case=False, na=False)
    ]

    # Filter out rows with missing IATA codes (NaN values)
    matching_rows = matching_rows.dropna(subset=["iata_code"])

    # Convert matching rows to AirportCode objects
    result = []
    for _, row in matching_rows.iterrows():
        result.append(Airport(name=row["name"], code=row["iata_code"]))

    return result


@tool
def check_code_validity(airport_code: str) -> Airport:
    """Check if the given airport code is valid and return the corresponding airport name"""
    all_codes = load_airport_codes()
    matching_rows = all_codes[all_codes["iata_code"] == airport_code]
    if len(matching_rows) == 0:
        raise ValueError(f"Invalid airport code: {airport_code}")
    return Airport(
        name=matching_rows["name"].iloc[0],
        code=airport_code,
    )


if __name__ == "__main__":
    print(airport_codes_lookup("London"))
