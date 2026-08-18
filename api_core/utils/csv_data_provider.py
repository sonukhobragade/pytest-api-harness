"""
CSV Data Provider - Data-Driven Testing Utility

Provides CSV loading, validation, and parametrization for pytest tests.
Supports dynamic CSV reload for CI/CD environments.
"""

import csv
import re
from functools import wraps
from pathlib import Path
from typing import Any

import allure
import pytest

# =============================================================================
# CSV LOADER WITH VALIDATION
# =============================================================================

class CSVDataLoader:
    """
    CSV Data Loader with schema validation and dynamic reload support.

    Features:
    - Schema validation (required columns)
    - Dynamic CSV reload (for CI/CD)
    - Enabled/disabled test filtering
    - Type conversion (bool, int)
    """

    # Cache for loaded CSV data
    _cache: dict[str, list[dict[str, Any]]] = {}

    @classmethod
    def load_csv(
        cls,
        csv_file_path: str,
        required_columns: list[str] | None = None,
        reload: bool = False
    ) -> list[dict[str, Any]]:
        """
        Load CSV file with validation and caching.

        Args:
            csv_file_path: Path to CSV file relative to resources/test_data/
                          Example: "jwt_auth/jwt_tests.csv"
            required_columns: List of required column names for validation
            reload: Force reload from disk (useful for CI/CD dynamic data)

        Returns:
            List of dictionaries, each representing a CSV row

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If required columns are missing

        Example:
            >>> data = CSVDataLoader.load_csv("jwt_auth/jwt_tests.csv")
            >>> print(data[0])
            {'case_id': 'TC001', 'description': 'Valid user', ...}
        """
        # Build full path
        base_path = Path(__file__).parent.parent.parent / "resources" / "test_data"
        full_path = base_path / csv_file_path

        # Check cache (unless reload requested)
        cache_key = str(full_path)
        if not reload and cache_key in cls._cache:
            return cls._cache[cache_key]

        # Validate file exists
        if not full_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {full_path}\n"
                f"Expected path: resources/test_data/{csv_file_path}"
            )

        # Load CSV
        with open(full_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Validate schema (required columns)
            if required_columns:
                missing_columns = set(required_columns) - set(reader.fieldnames)
                if missing_columns:
                    raise ValueError(
                        f"Missing required columns in {csv_file_path}: {missing_columns}\n"
                        f"Available columns: {reader.fieldnames}"
                    )

            # Load all rows
            data = []
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Type conversions
                processed_row = cls._process_row(row, row_num, csv_file_path)
                data.append(processed_row)

        # Cache the data
        cls._cache[cache_key] = data

        return data

    @staticmethod
    def _process_row(row: dict[str, str], row_num: int, csv_file: str) -> dict[str, Any]:
        """
        Process CSV row: type conversions, validations.

        Args:
            row: Raw CSV row as string dict
            row_num: Row number for error reporting
            csv_file: CSV file name for error reporting

        Returns:
            Processed row with proper types
        """
        processed = {}

        for key, value in row.items():
            # Handle empty strings
            if value == "":
                processed[key] = None
            # Convert enabled column to boolean
            elif key == "enabled":
                processed[key] = value.lower() in ("true", "1", "yes")
            # Convert expected_status to int
            elif key == "expected_status":
                try:
                    processed[key] = int(value) if value else None
                except ValueError as err:
                    raise ValueError(
                        f"Invalid expected_status in {csv_file} row {row_num}: '{value}' (must be integer)"
                    ) from err
            # Keep as string
            else:
                processed[key] = value if value else None

        return processed

    @classmethod
    def clear_cache(cls):
        """Clear CSV cache - useful for testing or dynamic reload."""
        cls._cache.clear()

    @classmethod
    def reload_csv(cls, csv_file_path: str, required_columns: list[str] | None = None):
        """
        Reload CSV from disk (bypass cache).

        Useful for CI/CD environments where CSV data is updated dynamically.

        Args:
            csv_file_path: Path to CSV file
            required_columns: Required columns for validation

        Returns:
            Reloaded CSV data
        """
        return cls.load_csv(csv_file_path, required_columns, reload=True)


# =============================================================================
# DATA PROVIDER DECORATOR
# =============================================================================

def data_provider(
    csv_file_path: str,
    required_columns: list[str] | None = None,
    filter_enabled: bool = True,
    reload: bool = False
):
    """
    Decorator to parametrize tests from CSV data.

    Automatically:
    - Loads CSV data
    - Validates schema
    - Filters enabled/disabled tests
    - Adds pytest markers from 'tags' column
    - Adds case_id to Allure test title

    Args:
        csv_file_path: Path to CSV file relative to resources/test_data/
        required_columns: List of required columns (validates schema)
        filter_enabled: Only run tests where enabled=true (default: True)
        reload: Force reload from disk (for CI/CD)

    Example:
        @data_provider("jwt_auth/jwt_tests.csv", required_columns=["case_id", "user_id"])
        async def test_jwt_auth(self, test_data):
            user_id = test_data["user_id"]
            ...

    Test name will be: [TC001] Valid user credentials
    """
    def decorator(test_func):
        # Load CSV data
        csv_data = CSVDataLoader.load_csv(csv_file_path, required_columns, reload)

        # Filter enabled tests
        if filter_enabled:
            csv_data = [row for row in csv_data if row.get("enabled", True)]

        # Create test IDs for pytest (use case_id + description)
        test_ids = [
            f"[{row.get('case_id', 'N/A')}] {row.get('description', 'No description')}"
            for row in csv_data
        ]

        # Create parametrized wrapper
        @pytest.mark.parametrize("test_data", csv_data, ids=test_ids)
        @wraps(test_func)
        async def wrapper(self, test_data):
            # Apply pytest markers from 'tags' column
            tags = test_data.get("tags", "")
            if tags:
                for tag in re.split(r"[,|]", tags):
                    tag = tag.strip()
                    if tag:
                        pytest.mark.__getattr__(tag)(test_func)

            # Add case_id to Allure title
            case_id = test_data.get("case_id", "N/A")
            description = test_data.get("description", "No description")

            with allure.step(f"Executing test case: [{case_id}] {description}"):
                allure.dynamic.title(f"[{case_id}] {description}")
                allure.dynamic.description(
                    f"**Test Type:** {test_data.get('type', 'N/A')}\n"
                    f"**Case ID:** {case_id}"
                )

                # Execute the actual test
                return await test_func(self, test_data)

        return wrapper

    return decorator


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_test_data_by_case_id(csv_file_path: str, case_id: str) -> dict[str, Any] | None:
    """
    Get single test data row by case_id.

    Useful for debugging or running specific test cases.

    Args:
        csv_file_path: Path to CSV file
        case_id: Test case ID to find

    Returns:
        Test data dictionary or None if not found

    Example:
        >>> data = get_test_data_by_case_id("jwt_auth/jwt_tests.csv", "TC001")
        >>> print(data["description"])
        'Valid user credentials'
    """
    csv_data = CSVDataLoader.load_csv(csv_file_path)
    for row in csv_data:
        if row.get("case_id") == case_id:
            return row
    return None


def get_valid_users() -> list[dict[str, Any]]:
    """
    Get all valid users from shared/valid_users.csv.

    Returns:
        List of valid user dictionaries

    Example:
        >>> users = get_valid_users()
        >>> primary_user = users[0]
        >>> print(primary_user["user_id"])
        '1001'
    """
    return CSVDataLoader.load_csv("shared/valid_users.csv")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "CSVDataLoader",
    "data_provider",
    "get_test_data_by_case_id",
    "get_valid_users",
]
