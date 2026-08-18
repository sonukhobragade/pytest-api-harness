"""
pytest API harness - Database Utilities
Multi-database connection manager for microservices architecture

Supports:
- Any number of named databases, configured through the environment
- Remote and local connections
- Query execution with automatic logging
- Data validation helpers
- Test data management

Usage:
    from api_core.utils.db_utils import db_utils

    # Query a named database
    user = db_utils.postgres.get_one("users", {"id": "1"})
    orders = db_utils.postgres.get_many("orders", {"user_id": "1"})

    # Validate API response against DB
    db_utils.validate_response_with_db(api_response, "orders", {"user_id": "1"})
"""

import logging
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

import allure
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Configure logging
logger = logging.getLogger(__name__)

# Import query registry (lazy import to avoid circular dependencies)
_query_registry = None

def _get_query_registry():
    """Lazy load query registry"""
    global _query_registry
    if _query_registry is None:
        from api_core.utils.query_registry import query_registry
        _query_registry = query_registry
    return _query_registry


# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

class DatabaseConfig:
    """Configuration for service databases"""

    # Remote database configuration. No defaults on purpose: a wrong default
    # silently points a test suite at somebody else's database.
    QA_HOST = os.getenv("DB_HOST", "")
    QA_PORT = os.getenv("DB_PORT", "5432")
    QA_USER = os.getenv("DB_USER", "")
    QA_PASSWORD = os.getenv("DB_PASSWORD", "")

    # Logical name -> actual database name. Set DATABASES in the environment
    # as a comma-separated list of alias=dbname pairs to match your own
    # topology, e.g. DATABASES="orders=orders-db,billing=billing".
    DATABASES = {
        "postgres": "postgres",
        **{
            pair.split("=", 1)[0].strip(): pair.split("=", 1)[1].strip()
            for pair in os.getenv("DATABASES", "").split(",")
            if "=" in pair
        },
    }

    # Local database configuration (fallback)
    LOCAL_HOST = os.getenv("POSTGRES_HOST", "localhost")
    LOCAL_PORT = os.getenv("POSTGRES_PORT", "5432")
    LOCAL_USER = os.getenv("POSTGRES_USER", "postgres")
    LOCAL_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

    @classmethod
    def get_connection_url(cls, database_name: str, use_qa: bool = True) -> str:
        """
        Build PostgreSQL connection URL for specific database

        Args:
            database_name: Logical database name from DatabaseConfig.DATABASES
            use_qa: If True, connect to QA AWS RDS. If False, use local.

        Returns:
            PostgreSQL connection URL
        """
        if use_qa:
            host = cls.QA_HOST
            port = cls.QA_PORT
            user = cls.QA_USER
            password = cls.QA_PASSWORD
        else:
            host = cls.LOCAL_HOST
            port = cls.LOCAL_PORT
            user = cls.LOCAL_USER
            password = cls.LOCAL_PASSWORD

        db_name = cls.DATABASES.get(database_name, database_name)
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


# =============================================================================
# DATABASE CLIENT
# =============================================================================

class DatabaseClient:
    """
    Enhanced database client for the services under test

    Handles connections to multiple databases with automatic logging
    """

    def __init__(self, database_name: str, use_qa: bool = True):
        """
        Initialize database client

        Args:
            database_name: Logical database name from DatabaseConfig.DATABASES
            use_qa: Connect to QA AWS RDS (True) or local (False)
        """
        self.database_name = database_name
        self.use_qa = use_qa
        self.connection_url = DatabaseConfig.get_connection_url(database_name, use_qa)

        # Create engine with connection pooling
        self.engine = create_engine(
            self.connection_url,
            poolclass=NullPool,  # No connection pooling for test environment
            echo=False,  # Set to True for SQL debugging
            future=True
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info(f"DatabaseClient initialized: {database_name} ({'QA' if use_qa else 'Local'})")

    @contextmanager
    def session(self) -> Session:
        """
        Context manager for database session

        Usage:
            with db.session() as session:
                result = session.execute(text("SELECT * FROM users"))
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def execute(self, query: str, params: dict | None = None) -> list[dict]:
        """
        Execute raw SQL query

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of results as dictionaries
        """
        with self.session() as session:
            result = session.execute(text(query), params or {})

            # Convert to list of dicts
            rows = []
            if result.returns_rows:
                columns = result.keys()
                rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

            # Log to Allure
            self._log_query(query, params, rows)

            return rows

    def execute_named(self, name: str, params: dict | None = None) -> list[dict]:
        """
        Execute named query from query registry

        Args:
            name: Query name (from SQL files)
            params: Query parameters

        Returns:
            List of results as dictionaries

        Example:
            # Execute: SELECT * FROM orders WHERE user_id = :user_id
            results = db_utils.postgres.execute_named(
                "orders_by_user",
                {"user_id": "1"}
            )

        Raises:
            KeyError: If query name not found
            RuntimeError: If attempting write query in production
        """
        registry = _get_query_registry()
        query = registry.get(self.database_name, name)

        # Security: Block write operations in production
        self._validate_query_safety(query)

        # Execute with safe parameter logging
        return self.execute(query, params)

    def _validate_query_safety(self, query: str):
        """
        Validate query is safe to execute

        Args:
            query: SQL query string

        Raises:
            RuntimeError: If write query attempted in production environment
        """
        # Check if this is a write query (INSERT, UPDATE, DELETE)
        query_upper = query.strip().upper()
        write_operations = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER']

        is_write_query = any(query_upper.startswith(op) for op in write_operations)

        if is_write_query:
            # Check environment
            env = os.getenv("ENV", "qa").lower()
            if env == "prod" or env == "production":
                raise RuntimeError(
                    f"❌ BLOCKED: Write queries are not allowed in production environment. "
                    f"Query starts with: {query[:50]}..."
                )

            logger.warning(f"⚠️  Executing write query in {env} environment")

    def get_one(self, table: str, conditions: dict[str, Any]) -> dict | None:
        """
        Get single record from table

        Args:
            table: Table name
            conditions: WHERE conditions as dict

        Returns:
            Single record as dict or None
        """
        where_clause = " AND ".join([f"{k} = :{k}" for k in conditions.keys()])
        query = f"SELECT * FROM {table} WHERE {where_clause} LIMIT 1"

        results = self.execute(query, conditions)
        return results[0] if results else None

    def get_many(
        self,
        table: str,
        conditions: dict[str, Any] | None = None,
        limit: int | None = None,
        order_by: str | None = None
    ) -> list[dict]:
        """
        Get multiple records from table

        Args:
            table: Table name
            conditions: WHERE conditions as dict (optional)
            limit: Maximum number of records
            order_by: ORDER BY clause (e.g., "created_at DESC")

        Returns:
            List of records as dicts
        """
        query = f"SELECT * FROM {table}"
        params = {}

        if conditions:
            where_clause = " AND ".join([f"{k} = :{k}" for k in conditions.keys()])
            query += f" WHERE {where_clause}"
            params = conditions

        if order_by:
            query += f" ORDER BY {order_by}"

        if limit:
            query += f" LIMIT {limit}"

        return self.execute(query, params)

    def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """
        Count records in table

        Args:
            table: Table name
            conditions: WHERE conditions as dict (optional)

        Returns:
            Number of matching records
        """
        query = f"SELECT COUNT(*) as count FROM {table}"
        params = {}

        if conditions:
            where_clause = " AND ".join([f"{k} = :{k}" for k in conditions.keys()])
            query += f" WHERE {where_clause}"
            params = conditions

        result = self.execute(query, params)
        return result[0]["count"] if result else 0

    def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """
        Check if record exists

        Args:
            table: Table name
            conditions: WHERE conditions as dict

        Returns:
            True if record exists
        """
        return self.count(table, conditions) > 0

    def insert(self, table: str, data: dict[str, Any]) -> dict | None:
        """
        Insert record into table

        Args:
            table: Table name
            data: Data to insert as dict

        Returns:
            Inserted record (if RETURNING *)
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{k}" for k in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *"

        results = self.execute(query, data)
        return results[0] if results else None

    def update(
        self,
        table: str,
        conditions: dict[str, Any],
        data: dict[str, Any]
    ) -> list[dict]:
        """
        Update records in table

        Args:
            table: Table name
            conditions: WHERE conditions as dict
            data: Data to update as dict

        Returns:
            Updated records
        """
        set_clause = ", ".join([f"{k} = :new_{k}" for k in data.keys()])
        where_clause = " AND ".join([f"{k} = :where_{k}" for k in conditions.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause} RETURNING *"

        # Prefix params to avoid conflicts
        params = {f"new_{k}": v for k, v in data.items()}
        params.update({f"where_{k}": v for k, v in conditions.items()})

        return self.execute(query, params)

    def delete(self, table: str, conditions: dict[str, Any]) -> int:
        """
        Delete records from table

        Args:
            table: Table name
            conditions: WHERE conditions as dict

        Returns:
            Number of deleted records
        """
        where_clause = " AND ".join([f"{k} = :{k}" for k in conditions.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"

        self.execute(query, conditions)
        # Return count (SQLAlchemy doesn't return count for DELETE)
        return 1  # Assume success if no exception

    def _log_query(self, query: str, params: dict | None, results: list[dict]) -> None:
        """
        Log query to Allure report (with safe parameter logging)

        Only logs parameter keys, not values, for security
        """
        # Safe parameter logging (keys only, no sensitive values)
        param_keys = list(params.keys()) if params else []

        log_data = {
            "database": self.database_name,
            "environment": "QA" if self.use_qa else "Local",
            "query": query,
            "parameter_keys": param_keys,  # Log keys only, not values
            "result_count": len(results)
        }

        allure.attach(
            str(log_data),
            name=f"DB Query: {self.database_name}",
            attachment_type=allure.attachment_type.TEXT
        )


# =============================================================================
# MULTI-DATABASE MANAGER
# =============================================================================

class MultiDatabaseManager:
    """
    Manager for multiple database connections

    Usage:
        db_utils = MultiDatabaseManager(use_qa=True)

        # Access specific database
        user = db_utils.postgres.get_one("users", {"id": "1"})
        order = db_utils.db("orders").get_one("orders", {"id": "1"})

        # Validate response
        db_utils.validate_response_with_db(
            api_response=response.json(),
            table="orders",
            conditions={"user_id": "1"},
            database="postgres"
        )
    """

    def __init__(self, use_qa: bool = True):
        """
        Initialize multi-database manager

        Args:
            use_qa: Connect to QA AWS RDS (True) or local (False)
        """
        self.use_qa = use_qa
        self._clients: dict[str, DatabaseClient] = {}

        logger.info(f"MultiDatabaseManager initialized ({'QA' if use_qa else 'Local'})")

    def _get_client(self, database_name: str) -> DatabaseClient:
        """Get or create database client"""
        if database_name not in self._clients:
            self._clients[database_name] = DatabaseClient(database_name, self.use_qa)
        return self._clients[database_name]

    @property
    def postgres(self) -> DatabaseClient:
        """Access postgres database (main DB)"""
        return self._get_client("postgres")

    def db(self, name: str) -> DatabaseClient:
        """Access any database declared in DatabaseConfig.DATABASES.

        Replaces the per-service properties this module used to hard-code:
        which databases exist is a property of your deployment, not of the
        harness.
        """
        if name not in DatabaseConfig.DATABASES:
            raise KeyError(
                f"Unknown database {name!r}. Declare it in the DATABASES "
                f"environment variable. Known: {sorted(DatabaseConfig.DATABASES)}"
            )
        return self._get_client(name)

    def run(self, db: str, query: str, params: dict | None = None) -> list[dict]:
        """
        Execute named query on any database (convenience method)

        Args:
            db: Logical database name from DatabaseConfig.DATABASES
            query: Query name from registry
            params: Query parameters

        Returns:
            List of results as dictionaries

        Example:
            # Execute named query on a named database
            rows = db_utils.run("orders", "order_by_id", {"id": "1"})

            # Execute on postgres
            user = db_utils.run("postgres", "user_by_id", {"user_id": "1"})

        Raises:
            KeyError: If database or query name not found
            RuntimeError: If attempting write query in production
        """
        client = self._get_client(db)
        return client.execute_named(query, params)

    def validate_response_with_db(
        self,
        api_response: list[dict] | dict,
        table: str,
        conditions: dict[str, Any],
        database: str = "postgres",
        fields_to_compare: list[str] | None = None,
        ignore_fields: list[str] | None = None
    ) -> bool:
        """
        Validate API response against database records

        Args:
            api_response: API response data (list or dict)
            table: Database table name
            conditions: Query conditions to fetch DB records
            database: Database name (default: postgres)
            fields_to_compare: Specific fields to compare (optional)
            ignore_fields: Fields to ignore in comparison (optional)

        Returns:
            True if response matches database

        Raises:
            AssertionError if mismatch found
        """
        client = self._get_client(database)

        # Fetch records from database
        db_records = client.get_many(table, conditions)

        # Normalize API response to list
        if isinstance(api_response, dict):
            # Handle wrapped responses like {"data": [...]} or {"items": [...]}
            api_data = (api_response.get("data") or api_response.get("items")
                        or [api_response])
        else:
            api_data = api_response

        # Compare counts
        assert len(api_data) == len(db_records), \
            f"Count mismatch: API returned {len(api_data)} records, DB has {len(db_records)}"

        # Default fields to ignore
        default_ignore = ignore_fields or ["created_at", "updated_at", "timestamp"]

        # Compare each record
        for api_record, db_record in zip(api_data, db_records, strict=False):
            if fields_to_compare:
                # Compare only specific fields
                for field in fields_to_compare:
                    assert api_record.get(field) == db_record.get(field), \
                        f"Field mismatch: {field} - API: {api_record.get(field)}, DB: {db_record.get(field)}"
            else:
                # Compare all fields except ignored
                for key, value in db_record.items():
                    if key not in default_ignore:
                        assert api_record.get(key) == value, \
                            f"Field mismatch: {key} - API: {api_record.get(key)}, DB: {value}"

        # Log success to Allure
        allure.attach(
            f"✓ Validated {len(api_data)} records against {database}.{table}",
            name="DB Validation Success",
            attachment_type=allure.attachment_type.TEXT
        )

        return True

    def close_all(self):
        """Close all database connections"""
        for client in self._clients.values():
            client.engine.dispose()
        self._clients.clear()
        logger.info("All database connections closed")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

@lru_cache
def get_db_utils(use_qa: bool = True) -> MultiDatabaseManager:
    """
    Get singleton instance of MultiDatabaseManager

    Args:
        use_qa: Connect to QA AWS RDS (True) or local (False)

    Returns:
        MultiDatabaseManager instance
    """
    return MultiDatabaseManager(use_qa=use_qa)


# Global instance - import this in tests
db_utils = get_db_utils(use_qa=True)  # Default to QA database


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compare_api_response_with_db(
    api_response: list | dict,
    db_records: list[dict],
    field_mapping: dict[str, str] | None = None,
    ignore_fields: list[str] | None = None
) -> dict[str, Any]:
    """
    Compare API response with database records

    Args:
        api_response: Response from API
        db_records: Records from database
        field_mapping: Map API field names to DB column names (e.g., {"id": "order_id"})
        ignore_fields: Fields to skip in comparison

    Returns:
        Comparison result with mismatches
    """
    # Normalize to lists
    if isinstance(api_response, dict):
        api_data = api_response.get("data") or api_response.get("items") or [api_response]
    else:
        api_data = api_response

    ignore = ignore_fields or ["created_at", "updated_at", "timestamp"]
    mapping = field_mapping or {}

    result = {
        "match": True,
        "api_count": len(api_data),
        "db_count": len(db_records),
        "mismatches": []
    }

    # Count check
    if len(api_data) != len(db_records):
        result["match"] = False
        result["mismatches"].append({
            "type": "count_mismatch",
            "api_count": len(api_data),
            "db_count": len(db_records)
        })

    # Field comparison
    for idx, (api_rec, db_rec) in enumerate(zip(api_data, db_records, strict=False)):
        for api_field, api_value in api_rec.items():
            if api_field in ignore:
                continue

            # Get corresponding DB field name
            db_field = mapping.get(api_field, api_field)
            db_value = db_rec.get(db_field)

            if api_value != db_value:
                result["match"] = False
                result["mismatches"].append({
                    "index": idx,
                    "field": api_field,
                    "api_value": api_value,
                    "db_value": db_value
                })

    return result
