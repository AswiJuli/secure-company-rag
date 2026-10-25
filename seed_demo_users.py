import os
import sqlite3

from auth import hash_password
from database import (
    create_user,
    get_user,
    initialize_database
)

from dotenv import load_dotenv


load_dotenv()

DEMO_USERS = [
    ("FINEMP1002", "employee"),
    ("FINEMP1013", "engineering"),
    ("FINEMP1001", "finance"),
    ("FINEMP1007", "marketing"),
    ("FINEMP1010", "hr"),
    ("EXECDEMO", "executive")
]


def main():
    demo_password = os.getenv("DEMO_PASSWORD")

    if not demo_password:
        raise RuntimeError(
            "DEMO_PASSWORD environment variable is missing."
        )

    initialize_database()

    for username, role in DEMO_USERS:

        if get_user(username) is not None:
            print(f"User already exists: {username}")
            continue

        try:
            create_user(
                username=username,
                password_hash=hash_password(
                    demo_password
                ),
                role=role
            )

            print(
                f"Created {username} "
                f"with role {role}."
            )

        except sqlite3.IntegrityError:
            print(f"User already exists: {username}")


if __name__ == "__main__":
    main()