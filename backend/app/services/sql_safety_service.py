import re


ALLOWED_STATEMENT = "SELECT"

BLOCKED_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
}


class SQLSafetyError(ValueError):
    """Raised when submitted SQL is not safe for read-only analysis."""


def normalize_sql(query: str) -> str:
    return query.strip()


def remove_sql_comments(query: str) -> str:
    query = re.sub(r"/\*.*?\*/", " ", query, flags=re.DOTALL)
    query = re.sub(r"--[^\r\n]*", " ", query)
    return query


def validate_read_only_sql(query: str) -> str:
    if not query or not query.strip():
        raise SQLSafetyError("SQL query cannot be empty.")

    normalized_query = normalize_sql(query)
    query_without_comments = remove_sql_comments(normalized_query).strip()

    if not query_without_comments:
        raise SQLSafetyError("SQL query cannot contain only comments.")

    # Reject multiple SQL statements.
    statements = [
        statement.strip()
        for statement in query_without_comments.split(";")
        if statement.strip()
    ]

    if len(statements) != 1:
        raise SQLSafetyError(
            "Multiple SQL statements are not allowed."
        )

    statement = statements[0]

    # The first SQL keyword must be SELECT.
    first_keyword = re.match(
        r"^\s*([A-Za-z]+)",
        statement,
    )

    if first_keyword is None:
        raise SQLSafetyError("Unable to determine SQL statement type.")

    statement_type = first_keyword.group(1).upper()

    if statement_type != ALLOWED_STATEMENT:
        raise SQLSafetyError(
            "Only read-only SELECT queries are allowed."
        )

    # Check for blocked SQL keywords.
    keywords = re.findall(
        r"\b[A-Za-z]+\b",
        statement.upper(),
    )

    for keyword in keywords:
        if keyword in BLOCKED_KEYWORDS:
            raise SQLSafetyError(
                f"SQL keyword '{keyword}' is not allowed."
            )

    return statement