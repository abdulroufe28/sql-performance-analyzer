import pytest

from backend.app.services.sql_safety_service import (
    SQLSafetyError,
    validate_read_only_sql,
)


def test_select_query_is_allowed():
    query = "SELECT * FROM users"

    result = validate_read_only_sql(query)

    assert result == query


def test_delete_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "DELETE FROM users"
        )


def test_drop_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "DROP TABLE users"
        )


def test_multiple_statements_are_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "SELECT * FROM users; DROP TABLE users"
        )


def test_empty_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql("")


def test_comment_only_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "-- SELECT * FROM users"
        )

def test_update_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "UPDATE users SET full_name = 'Admin'"
        )


def test_insert_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "INSERT INTO users (email) VALUES ('test@example.com')"
        )


def test_alter_query_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "ALTER TABLE users ADD COLUMN test VARCHAR(50)"
        )


def test_trailing_semicolon_is_allowed():
    result = validate_read_only_sql(
        "SELECT * FROM users;"
    )

    assert result == "SELECT * FROM users"


def test_sql_comments_are_ignored():
    result = validate_read_only_sql(
        "-- get all users\nSELECT * FROM users"
    )

    assert result == "SELECT * FROM users"


def test_non_select_query_with_leading_whitespace_is_blocked():
    with pytest.raises(SQLSafetyError):
        validate_read_only_sql(
            "   DELETE FROM users"
        )