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
def name_to_iata_code(airport_names: list[str]) -> list[Airport]:
    """Lookup the airport iata codes for a list of airport or city names."""

    all_codes = load_airport_codes()
    result = []
    
    for airport_name in airport_names:
        matching_rows = all_codes[
            all_codes["name"].str.contains(airport_name, case=False, na=False)
        ]
        matching_rows = matching_rows.dropna(subset=["iata_code"])
        for _, row in matching_rows.iterrows():
            result.append(Airport(name=row["name"], code=row["iata_code"]))

    return result


@tool
def iata_code_to_name(airport_codes: list[str]) -> list[Airport]:
    """Lookup the airport names for a list of airport iata codes"""
    all_codes = load_airport_codes()
    result = []
    for airport_code in airport_codes:
        matching_rows = all_codes[all_codes["iata_code"] == airport_code]
        for _, row in matching_rows.iterrows():
            result.append(Airport(name=row["name"], code=row["iata_code"]))
    return result


if __name__ == "__main__":
    print(name_to_iata_code("Heathrow"))
