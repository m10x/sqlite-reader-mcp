import argparse
from pathlib import Path
from typing import Any, Optional

import aiosqlite
import sqlparse
from fastmcp import FastMCP

allowed_dirs = []
allowed_files = []

mcp = FastMCP(
    name="SQLite MCP Server",
    instruction="This server allows read-only access to SQLite databases.",
    log_level="CRITICAL",
)


class SQLiteConnection:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    async def __aenter__(self):
        self.conn = await aiosqlite.connect(
            "file:" + str(self.db_path) + "?mode=ro", uri=True
        )
        self.conn.row_factory = aiosqlite.Row
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            await self.conn.close()

# TODO: persistent connections to avoid reopening databases
# connections: dict[str, SQLiteConnection] = {}


def file_allowed(path: Path) -> bool:
    """Validate if the given path is allowed."""
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return any(path == f for f in allowed_files) or any(
        path.is_relative_to(d) for d in allowed_dirs
    )

@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "openWorldHint": True,
    }
)
async def read_query(
    file_path: str,
    query: str,
    params: Optional[list[Any]] = None,
    fetch_all: bool = True,
    row_limit: int = 1000,
) -> list[dict[str, Any]]:
    """
    Execute a query on an SQLite database.

    Args:
        file_path: Absolute path to the SQLite database file.
        query: 'SELECT' or 'WITH' SQL query to execute.
        params: Optional list of parameters for the query
        fetch_all: If True, fetches all results. If False, fetches one row.
        row_limit: Maximum number of rows to return (default 1000).

    Returns:
        List of dictionaries containing the query results.
    """

    path = Path(file_path).resolve()
    if not file_allowed(path):
        raise FileNotFoundError(f"Path not allowed: {path}")

    # Clean and validate the query
    query = query.strip()

    # Remove trailing semicolon if present
    if query.endswith(";"):
        query = query[:-1].strip()

    sql = sqlparse.parse(query)
    if len(sql) != 1:
        raise ValueError("Multiple SQL statements are not allowed")
    sql = sql[0]

    # Validate query type (allowing common CTEs)
    if sql.get_type().lower() not in ("select", "with"):
        raise ValueError(
            "Only SELECT queries (including WITH clauses) are allowed for safety"
        )

    params = params or []

    async with SQLiteConnection(path) as conn:
        cursor = await conn.cursor()

        try:
            # Only add LIMIT if query doesn't already have one
            if "limit" not in query.lower():
                query = f"{query} LIMIT {row_limit}"

            await cursor.execute(query, params)

            if fetch_all:
                results = await cursor.fetchall()
            else:
                results = [await cursor.fetchone()]

            return [dict(row) for row in results if row is not None]

        except aiosqlite.Error as e:
            raise ValueError(f"SQLite error: {str(e)}")


@mcp.tool()
async def list_tables(
    file_path: str,
) -> list[str]:
    """
    List all tables in the database.

    Args:
        file_path: Absolute path to the SQLite database file.

    Returns:
        List of all tables in the database.
    """
    path = Path(file_path).resolve()
    if not file_allowed(path):
        raise FileNotFoundError(f"Path not allowed: {path}")

    async with SQLiteConnection(path) as conn:
        cursor = await conn.cursor()

        try:
            await cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)

            return [row["name"] for row in await cursor.fetchall()]

        except aiosqlite.Error as e:
            raise ValueError(f"SQLite error: {str(e)}")


@mcp.tool()
async def describe_table(
    file_path: str,
    table_name: str,
) -> list[dict[str, str]]:
    """Get detailed information about a table's schema.

    Args:
        file_path: Absolute path to the SQLite database file.
        table_name: Name of the table to describe

    Returns:
        List of dictionaries containing column information:
        - name: Column name
        - type: Column data type
        - notnull: Whether the column can contain NULL values
        - dflt_value: Default value for the column
        - pk: Whether the column is part of the primary key
    """
    path = Path(file_path).resolve()
    if not file_allowed(path):
        raise FileNotFoundError(f"Path not allowed: {path}")

    async with SQLiteConnection(path) as conn:
        cursor = await conn.cursor()

        try:
            # Verify table exists
            await cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """,
                [table_name],
            )

            if not cursor.fetchone():
                raise ValueError(f"Table '{table_name}' does not exist")

            # Get table schema
            await cursor.execute(f"PRAGMA table_info({table_name})")
            columns = await cursor.fetchall()

            return [dict(row) for row in columns]

        except aiosqlite.Error as e:
            raise ValueError(f"SQLite error: {str(e)}")


# Initialize FastMCP server
def main():
    parser = argparse.ArgumentParser(description="SQLite MCP Server")
    parser.add_argument(
        "-p",
        "--paths",
        help="Absolute paths of directories and files allowed for access",
        type=str,
        nargs="*",
        default=[],
    )
    args = parser.parse_args()
    for path in args.paths:
        p = Path(path).resolve()
        if not p.is_absolute():
            raise ValueError(f"Path must be absolute: {path}")
        if not p.exists():
            raise ValueError(f"Path does not exist: {path}")
        if p.is_dir():
            allowed_dirs.append(p.as_uri())
        elif p.is_file():
            allowed_files.append(p.as_uri())
    mcp.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting SQLite MCP Server")
