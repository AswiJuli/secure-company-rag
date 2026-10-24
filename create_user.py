import csv
import sqlite3
from getpass import getpass
from pathlib import Path

from auth import hash_password
from database import create_user, initialize_database


HR_DATA_PATH = Path("data/hr/hr_data.csv")

DEPARTMENT_ACCESS_MAP = {
    "finance": "finance",
    "marketing": "marketing",
    "hr": "hr",
    "technology": "engineering"
}


def find_employee(employee_id):
    with HR_DATA_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        for employee in reader:
            if employee["employee_id"].lower() == employee_id.lower():
                return employee

    return None


initialize_database()

print("Create employee chatbot account")

employee_id = input("Employee ID: ").strip().upper()

employee = find_employee(employee_id)

if employee is None:
    print("Employee ID was not found in the HR records.")

else:
    department = employee["department"].strip()

    access_role = DEPARTMENT_ACCESS_MAP.get(
        department.lower(),
        "employee"
    )

    print("Employee:", employee["full_name"])
    print("Department:", department)
    print("Assigned chatbot role:", access_role)

    password = getpass("Create password: ")
    confirm_password = getpass("Confirm password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")

    elif password != confirm_password:
        print("Passwords do not match.")

    else:
        try:
            create_user(
                username=employee_id,
                password_hash=hash_password(password),
                role=access_role
            )

            print(
                f"Account created for {employee_id} "
                f"with access role '{access_role}'."
            )

        except sqlite3.IntegrityError:
            print("An account already exists for this employee.")