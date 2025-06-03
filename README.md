# sqlite-reader-mcp

MCP server for reading SQLite databases.

## Overview

`sqlite-reader-mcp` is a Python-based server that provides read-only access to SQLite databases using the FastMCP framework. It allows users to execute SELECT queries, list tables, and describe table schemas in a secure manner.

## Features

-   **Read-Only Access**: Ensures data integrity by only allowing read operations (SELECT queries).
-   **Secure Path Handling**: Restricts database access to pre-approved absolute file paths and directories.
-   **SQL Validation**: Parses and validates SQL queries, permitting only `SELECT` and `WITH` statements to prevent unintended operations.
-   **Asynchronous Operations**: Utilizes `aiosqlite` for non-blocking database interactions.
-   **Row Limiting**: Automatically limits the number of rows returned by queries to prevent excessive data retrieval.
-   **MCP Tools**:
    -   `read_query`: Execute a SELECT SQL query on a specified SQLite database.
    -   `list_tables`: List all tables within a given SQLite database.
    -   `describe_table`: Get schema information (column names, types, etc.) for a specific table.

## Requirements

-   Python 3.13+
-   `aiosqlite >= 0.21.0`
-   `fastmcp >= 2.6.1`
-   `sqlparse >= 0.5.3`

## Installation

The recommended installation method is with `uv`:
```bash
uv tool install --from git:https://github.com/abhinavnatarajan/sqlite-reader-mcp
```

## Usage

To start the server, run the main script from your terminal. You must provide the allowed paths for database access:

Using `python -m`:
```bash
python -m sqlite_reader_mcp.__main__ --paths /path/to/your/database.db /path/to/another/allowed_dir
```

If the package is installed and the script `sqlite-reader-mcp` is in your PATH:
```bash
sqlite-reader-mcp --paths /path/to/your/database.db /path/to/another/allowed_dir
```

**Arguments:**

-   `--paths` (or `-p`): A list of absolute paths to SQLite database files or directories containing them that the server is allowed to access.

Once the server is running, you can interact with it using a FastMCP client, utilizing the following tools:

### `read_query`

Executes a SELECT query on a specified SQLite database file.

-   **Args**:
    -   `file_path` (str): Absolute path to the SQLite database file.
    -   `query` (str): The SELECT SQL query to execute.
    -   `params` (Optional[List[Any]]): Optional list of parameters for the query.
    -   `fetch_all` (bool): If `True` (default), fetches all results. If `False`, fetches one row.
    -   `row_limit` (int): Maximum number of rows to return (default 1000).
-   **Returns**: A list of dictionaries, where each dictionary represents a row from the query result.

### `list_tables`

Lists all tables in the specified SQLite database file.

-   **Args**:
    -   `file_path` (str): Absolute path to the SQLite database file.
-   **Returns**: A list of table names (strings).

### `describe_table`

Provides detailed schema information for a specific table in a SQLite database.

-   **Args**:
    -   `file_path` (str): Absolute path to the SQLite database file.
    -   `table_name` (str): The name of the table to describe.
-   **Returns**: A list of dictionaries, each describing a column (e.g., name, type, notnull, default value, primary key status).

## Security

-   **Read-Only**: The server is strictly read-only. No `INSERT`, `UPDATE`, `DELETE`, or other data modification SQL commands are permitted.
-   **Path Whitelisting**: Access is restricted to SQLite files located in paths explicitly provided via the `--paths` command-line argument. Paths must be absolute and existent.
-   **Query Validation**: All SQL queries are parsed. Only `SELECT` statements (including those with Common Table Expressions using `WITH`) are allowed. Multiple statements in a single query string are rejected. Trailing semicolons are automatically removed.

## Development

This project is built using `setuptools`. Configuration is in `pyproject.toml`.
