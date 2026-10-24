import sqlite3
from pathlib import Path


DATABASE_PATH = Path("users.db")

ALLOWED_ROLES = {
    "employee",
    "engineering",
    "finance",
    "marketing",
    "hr",
    "executive"
}

#Connect to SQLLite
#row_factory lets Python access database columns by name
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """
    Creates the users table if it does not already exist.
    """
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def create_user(username, password_hash, role):
    """
    Adds a user with an assigned role.
    """
    normalized_username = username.lower().strip()
    normalized_role = role.lower().strip()

    if normalized_role not in ALLOWED_ROLES:
        raise ValueError(
            f"Invalid role. Choose from: "
            f"{', '.join(sorted(ALLOWED_ROLES))}"
        )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role
            )
            VALUES (?, ?, ?)
            """,
            (
                normalized_username,
                password_hash,
                normalized_role
            )
        )


def get_user(username):
    """
    Retrieves one user by username.
    """
    with get_connection() as connection:
        user = connection.execute(
            """
            SELECT id, username, password_hash, role, is_active
            FROM users
            WHERE username = ?
            """,
            (username.lower().strip(),)
        ).fetchone()

    if user is None:
        return None

    return dict(user)


def list_users():
    """
    Returns usernames and roles without password hashes.
    """
    with get_connection() as connection:
        users = connection.execute(
            """
            SELECT username, role, is_active
            FROM users
            ORDER BY username
            """
        ).fetchall()

    return [dict(user) for user in users]