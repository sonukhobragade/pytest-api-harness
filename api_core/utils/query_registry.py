"""
pytest API harness - Query Registry
Centralized repository for reusable SQL queries organized by database and domain.

Usage:
    from api_core.utils.query_registry import query_registry

    # Get query SQL
    sql = query_registry.get("postgres", "user_by_id")

    # Execute via db_utils
    result = db_utils.postgres.execute_named("user_by_id", {"user_id": "1"})
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class QueryRegistry:
    """
    Centralized registry for SQL queries organized by database and domain.

    Loads queries from: tests/utils/db_queries/{db_name}/{domain}.sql

    Query format in SQL files:
        -- name: query_name
        -- Optional description
        SELECT * FROM table WHERE id = :param;
    """

    def __init__(self, queries_dir: str = None):
        """
        Initialize query registry

        Args:
            queries_dir: Path to queries directory (default: tests/utils/db_queries)
        """
        if queries_dir is None:
            # Auto-detect queries directory
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            queries_dir = project_root / "tests" / "utils" / "db_queries"

        self.queries_dir = Path(queries_dir)
        self.queries: dict[str, dict[str, str]] = {}  # {db_name: {query_name: sql}}

        if self.queries_dir.exists():
            self._load_all_queries()
        else:
            logger.warning(f"Query directory not found: {self.queries_dir}")

    def _load_all_queries(self):
        """Load all queries from directory structure"""
        for db_dir in self.queries_dir.iterdir():
            if db_dir.is_dir():
                db_name = db_dir.name
                self.queries[db_name] = {}

                # Load all .sql files in this database directory
                for sql_file in db_dir.glob("*.sql"):
                    queries = self._parse_sql_file(sql_file)
                    self.queries[db_name].update(queries)

                logger.info(f"Loaded {len(self.queries[db_name])} queries for '{db_name}' database")

    def _parse_sql_file(self, file_path: Path) -> dict[str, str]:
        """
        Parse SQL file and extract named queries

        Format:
            -- name: query_name
            -- Optional description
            SELECT * FROM table WHERE id = :param;

        Args:
            file_path: Path to SQL file

        Returns:
            Dictionary of {query_name: sql_string}
        """
        queries = {}

        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # Split by query blocks (-- name: pattern)
        pattern = r'--\s*name:\s*(\w+)'
        matches = list(re.finditer(pattern, content))

        for i, match in enumerate(matches):
            query_name = match.group(1)
            start_pos = match.end()

            # Find end position (next query or end of file)
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)

            # Extract SQL (skip comment lines, trim whitespace)
            sql_block = content[start_pos:end_pos]
            sql_lines = []

            for line in sql_block.split('\n'):
                stripped = line.strip()
                # Skip empty lines and comment lines
                if stripped and not stripped.startswith('--'):
                    sql_lines.append(line.rstrip())

            if sql_lines:
                sql = '\n'.join(sql_lines)
                queries[query_name] = sql
                logger.debug(f"Loaded query: {query_name} from {file_path.name}")

        return queries

    def get(self, db: str, name: str) -> str:
        """
        Get SQL query by database and query name

        Args:
            db: Logical database name from DatabaseConfig.DATABASES
            name: Query name

        Returns:
            SQL query string

        Raises:
            KeyError: If database or query name not found
        """
        if db not in self.queries:
            available_dbs = list(self.queries.keys())
            raise KeyError(
                f"Database '{db}' not found in query registry. "
                f"Available databases: {available_dbs}"
            )

        if name not in self.queries[db]:
            available_queries = list(self.queries[db].keys())
            raise KeyError(
                f"Query '{name}' not found in '{db}' database. "
                f"Available queries: {available_queries}"
            )

        return self.queries[db][name]

    def list_databases(self) -> list[str]:
        """List all available databases"""
        return list(self.queries.keys())

    def list_queries(self, db: str) -> list[str]:
        """List all queries for a specific database"""
        if db not in self.queries:
            raise KeyError(f"Database '{db}' not found")
        return list(self.queries[db].keys())

    def query_exists(self, db: str, name: str) -> bool:
        """Check if query exists"""
        return db in self.queries and name in self.queries[db]

    def reload(self):
        """Reload all queries from disk"""
        self.queries.clear()
        self._load_all_queries()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global instance - import this in tests
query_registry = QueryRegistry()
