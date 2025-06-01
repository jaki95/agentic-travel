from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from backend.tools import (
    Airport,
    iata_code_to_name,
    load_airport_codes,
    name_to_iata_code,
)


class TestAirportTools:
    """Test suite for airport code lookup tools."""

    def test_airport_model(self):
        """Test the Airport model creation."""
        airport = Airport(name="John F Kennedy International Airport", code="JFK")
        assert airport.name == "John F Kennedy International Airport"
        assert airport.code == "JFK"

    @patch("backend.tools.load_airport_codes")
    def test_name_to_iata_code_single_match(self, mock_load):
        """Test looking up IATA code for a single airport name."""
        # Mock the CSV data
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
                {"name": "London Heathrow Airport", "iata_code": "LHR"},
                {"name": "Charles de Gaulle Airport", "iata_code": "CDG"},
            ]
        )
        mock_load.return_value = mock_df

        # Call the tool's func attribute since it's decorated
        result = name_to_iata_code.func(["Kennedy"])
        assert len(result) == 1
        assert result[0].name == "John F Kennedy International Airport"
        assert result[0].code == "JFK"

    @patch("backend.tools.load_airport_codes")
    def test_name_to_iata_code_multiple_matches(self, mock_load):
        """Test looking up IATA codes for multiple airport names."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
                {"name": "London Heathrow Airport", "iata_code": "LHR"},
                {"name": "London City Airport", "iata_code": "LCY"},
                {"name": "Charles de Gaulle Airport", "iata_code": "CDG"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func(["London"])
        assert len(result) == 2
        codes = [airport.code for airport in result]
        assert "LHR" in codes
        assert "LCY" in codes

    @patch("backend.tools.load_airport_codes")
    def test_name_to_iata_code_no_match(self, mock_load):
        """Test looking up IATA code for non-existent airport."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
                {"name": "London Heathrow Airport", "iata_code": "LHR"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func(["NonExistentAirport"])
        assert len(result) == 0

    @patch("backend.tools.load_airport_codes")
    def test_name_to_iata_code_case_insensitive(self, mock_load):
        """Test that name lookup is case insensitive."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func(["kennedy"])
        assert len(result) == 1
        assert result[0].code == "JFK"

        result = name_to_iata_code.func(["KENNEDY"])
        assert len(result) == 1
        assert result[0].code == "JFK"

    @patch("backend.tools.load_airport_codes")
    def test_name_to_iata_code_with_null_iata(self, mock_load):
        """Test that airports with null IATA codes are filtered out."""
        mock_df = pd.DataFrame(
            [
                {"name": "Airport with Code", "iata_code": "ABC"},
                {"name": "Airport without Code", "iata_code": None},
                {"name": "Another Airport", "iata_code": "XYZ"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func(["Airport"])
        assert len(result) == 2
        codes = [airport.code for airport in result]
        assert "ABC" in codes
        assert "XYZ" in codes
        assert None not in codes

    @patch("backend.tools.load_airport_codes")
    def test_iata_code_to_name_single_match(self, mock_load):
        """Test looking up airport name for a single IATA code."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
                {"name": "London Heathrow Airport", "iata_code": "LHR"},
            ]
        )
        mock_load.return_value = mock_df

        result = iata_code_to_name.func(["JFK"])
        assert len(result) == 1
        assert result[0].name == "John F Kennedy International Airport"
        assert result[0].code == "JFK"

    @patch("backend.tools.load_airport_codes")
    def test_iata_code_to_name_multiple_codes(self, mock_load):
        """Test looking up airport names for multiple IATA codes."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
                {"name": "London Heathrow Airport", "iata_code": "LHR"},
                {"name": "Charles de Gaulle Airport", "iata_code": "CDG"},
            ]
        )
        mock_load.return_value = mock_df

        result = iata_code_to_name.func(["JFK", "LHR"])
        assert len(result) == 2
        names = [airport.name for airport in result]
        assert "John F Kennedy International Airport" in names
        assert "London Heathrow Airport" in names

    @patch("backend.tools.load_airport_codes")
    def test_iata_code_to_name_no_match(self, mock_load):
        """Test looking up airport name for non-existent IATA code."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
            ]
        )
        mock_load.return_value = mock_df

        result = iata_code_to_name.func(["XYZ"])
        assert len(result) == 0

    @patch("backend.tools.load_airport_codes")
    def test_empty_input_lists(self, mock_load):
        """Test that empty input lists return empty results."""
        mock_df = pd.DataFrame(
            [
                {"name": "John F Kennedy International Airport", "iata_code": "JFK"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func([])
        assert len(result) == 0

        result = iata_code_to_name.func([])
        assert len(result) == 0

    @patch("pandas.read_csv")
    def test_load_airport_codes(self, mock_read_csv):
        """Test the load_airport_codes function."""
        mock_df = pd.DataFrame(
            [
                {"name": "Test Airport", "iata_code": "TST"},
            ]
        )
        mock_read_csv.return_value = mock_df

        result = load_airport_codes()

        # Verify pandas.read_csv was called
        mock_read_csv.assert_called_once()

        # Check that we got the expected dataframe
        assert result.equals(mock_df)

    @patch("backend.tools.load_airport_codes")
    def test_partial_name_matches(self, mock_load):
        """Test that partial name matches work correctly."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "New York John F Kennedy International Airport",
                    "iata_code": "JFK",
                },
                {"name": "New York LaGuardia Airport", "iata_code": "LGA"},
                {"name": "Newark Liberty International Airport", "iata_code": "EWR"},
            ]
        )
        mock_load.return_value = mock_df

        # Test partial match for "New York"
        result = name_to_iata_code.func(["New York"])
        assert len(result) == 2
        codes = [airport.code for airport in result]
        assert "JFK" in codes
        assert "LGA" in codes
        assert "EWR" not in codes

    @patch("backend.tools.load_airport_codes")
    def test_name_with_special_characters(self, mock_load):
        """Test name lookup with special characters."""
        mock_df = pd.DataFrame(
            [
                {"name": "Charles de Gaulle Airport", "iata_code": "CDG"},
                {"name": "Zürich Airport", "iata_code": "ZUR"},
            ]
        )
        mock_load.return_value = mock_df

        result = name_to_iata_code.func(["Gaulle"])
        assert len(result) == 1
        assert result[0].code == "CDG"

    @patch("backend.tools.load_airport_codes")
    def test_dataframe_with_missing_columns(self, mock_load):
        """Test behavior when CSV has missing expected columns."""
        # DataFrame missing 'iata_code' column
        mock_df = pd.DataFrame(
            [
                {"name": "Test Airport", "code": "TST"},
            ]
        )
        mock_load.return_value = mock_df

        # Should handle gracefully when iata_code column is missing
        with pytest.raises(KeyError):
            name_to_iata_code.func(["Test"])

    @patch("backend.tools.load_airport_codes")
    def test_duplicate_airport_codes(self, mock_load):
        """Test handling of duplicate airport codes in the data."""
        mock_df = pd.DataFrame(
            [
                {"name": "Airport One", "iata_code": "ABC"},
                {"name": "Airport Two", "iata_code": "ABC"},  # Duplicate code
            ]
        )
        mock_load.return_value = mock_df

        result = iata_code_to_name.func(["ABC"])
        assert len(result) == 2  # Should return both airports with same code
