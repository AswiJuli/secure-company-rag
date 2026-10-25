import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


HR_CSV_PATH = Path("data") / "hr" / "hr_data.csv"

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# Fields that the query planner is allowed to use.
ALLOWED_FIELDS = [
    "employee_id",
    "full_name",
    "role",
    "department",
    "location",
    "date_of_joining",
    "manager_id",
    "salary",
    "leave_balance",
    "leaves_taken",
    "attendance_pct",
    "performance_rating",
    "last_review_date"
]


# Fields that must be converted to numbers before
# comparisons or calculations are performed.
NUMERIC_FIELDS = {
    "salary",
    "leave_balance",
    "leaves_taken",
    "attendance_pct",
    "performance_rating"
}


ALLOWED_OPERATIONS = {
    "list",
    "count",
    "count_and_list",
    "sum",
    "average",
    "minimum",
    "maximum"
}


ALLOWED_FILTER_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "greater_than",
    "less_than",
    "greater_than_or_equal",
    "less_than_or_equal"
}


QUERY_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {
            "type": "string",
            "enum": ["structured", "rag"]
        },
        "operation": {
            "type": "string",
            "enum": [
                "list",
                "count",
                "count_and_list",
                "sum",
                "average",
                "minimum",
                "maximum"
            ]
        },
        "filters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "enum": ALLOWED_FIELDS
                    },
                    "operator": {
                        "type": "string",
                        "enum": [
                            "equals",
                            "not_equals",
                            "contains",
                            "greater_than",
                            "less_than",
                            "greater_than_or_equal",
                            "less_than_or_equal"
                        ]
                    },
                    "value": {
                        "type": "string"
                    }
                },
                "required": [
                    "field",
                    "operator",
                    "value"
                ],
                "additionalProperties": False
            }
        },
        "return_fields": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ALLOWED_FIELDS
            }
        },
        "aggregate_field": {
            "type": "string",
            "enum": [
                "",
                "salary",
                "leave_balance",
                "leaves_taken",
                "attendance_pct",
                "performance_rating"
            ]
        },
        "sort_by": {
            "type": "string",
            "enum": [
                "",
                *ALLOWED_FIELDS
            ]
        },
        "sort_order": {
            "type": "string",
            "enum": ["ascending", "descending"]
        },
        "limit": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100
        }
    },
    "required": [
        "route",
        "operation",
        "filters",
        "return_fields",
        "aggregate_field",
        "sort_by",
        "sort_order",
        "limit"
    ],
    "additionalProperties": False
}


def create_query_plan(question):
    """
    Uses the LLM to decide whether a question needs
    structured employee-data processing.

    It returns a restricted JSON query plan.
    """

    response = groq_client.chat.completions.create(
        model=os.getenv(
            "GROQ_MODEL",
            "openai/gpt-oss-20b"
        ),
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """
You route questions for an internal company assistant.

Use route "structured" when answering requires filtering,
listing, counting, sorting or calculating across employee rows.

Examples of structured questions:
- How many Marketing Managers are there?
- List all employees in Hyderabad.
- Who has attendance below 85 percent?
- What is the average salary in Finance?
- Show the five employees with the highest leave balance.

Use route "rag" for:
- company policies
- financial reports
- marketing reports
- engineering documents
- company FAQs
- questions about one specifically named employee or employee ID

All filters are combined using AND.

For percentage values, use the number without the percent sign.
For example, 85 percent becomes "85".

Use an empty string when aggregate_field or sort_by is unnecessary.
Use zero for limit when no limit was requested.

Return only the fields explicitly requested by the user.

Always include full_name when employees must be identified.

Examples:
- "What are their names?" -> return_fields: ["full_name"]
- "List employees in Hyderabad" -> return_fields: ["full_name"]
- "List their names and roles" ->
  return_fields: ["full_name", "role"]
- "Who has attendance below 85 percent?" ->
  return_fields: ["full_name", "attendance_pct"]
- "Show the five employees with the highest leave balance" ->
  return_fields: ["full_name", "leave_balance"]

Do not include role, department, location or other fields unless
the user asks for them or the field is necessary to answer the question.
Do not generate SQL.
"""
            },
            {
                "role": "user",
                "content": question
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "employee_query_plan",
                "strict": True,
                "schema": QUERY_PLAN_SCHEMA
            }
        }
    )

    return json.loads(
        response.choices[0].message.content
    )


def validate_query_plan(plan):
    """
    Performs our own validation even though the LLM uses
    a JSON schema.
    """

    if plan["route"] not in {"structured", "rag"}:
        raise ValueError("Invalid query route.")

    if plan["operation"] not in ALLOWED_OPERATIONS:
        raise ValueError("Invalid operation.")

    for query_filter in plan["filters"]:
        field = query_filter["field"]
        operator = query_filter["operator"]

        if field not in ALLOWED_FIELDS:
            raise ValueError(
                f"Filtering by {field} is not allowed."
            )

        if operator not in ALLOWED_FILTER_OPERATORS:
            raise ValueError(
                f"Operator {operator} is not allowed."
            )

        if (
            operator in {
                "greater_than",
                "less_than",
                "greater_than_or_equal",
                "less_than_or_equal"
            }
            and field not in NUMERIC_FIELDS
        ):
            raise ValueError(
                f"Numeric comparison cannot be used on {field}."
            )

    aggregate_field = plan["aggregate_field"]

    if (
        plan["operation"] in {
            "sum",
            "average",
            "minimum",
            "maximum"
        }
        and aggregate_field not in NUMERIC_FIELDS
    ):
        raise ValueError(
            "This calculation needs a numeric field."
        )


def load_employee_rows():
    """
    Loads every employee from the HR CSV.
    """

    if not HR_CSV_PATH.exists():
        raise FileNotFoundError(
            f"HR CSV not found: {HR_CSV_PATH}"
        )

    with HR_CSV_PATH.open(
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as csv_file:

        reader = csv.DictReader(csv_file)

        return [
            {
                key: (value or "").strip()
                for key, value in row.items()
            }
            for row in reader
        ]


def convert_numeric_value(value, field):
    """
    Converts numeric CSV values into floats.
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid numeric value for {field}: {value}"
        )


def row_matches_filter(row, query_filter):
    """
    Checks whether one employee row satisfies one filter.
    """

    field = query_filter["field"]
    operator = query_filter["operator"]
    expected_value = query_filter["value"]

    actual_value = row.get(field, "")

    if field in NUMERIC_FIELDS:
        actual_number = convert_numeric_value(
            actual_value,
            field
        )

        expected_number = convert_numeric_value(
            expected_value,
            field
        )

        if operator == "equals":
            return actual_number == expected_number

        if operator == "not_equals":
            return actual_number != expected_number

        if operator == "greater_than":
            return actual_number > expected_number

        if operator == "less_than":
            return actual_number < expected_number

        if operator == "greater_than_or_equal":
            return actual_number >= expected_number

        if operator == "less_than_or_equal":
            return actual_number <= expected_number

        return False

    actual_text = actual_value.casefold()
    expected_text = expected_value.casefold()

    if operator == "equals":
        return actual_text == expected_text

    if operator == "not_equals":
        return actual_text != expected_text

    if operator == "contains":
        return expected_text in actual_text

    return False


def filter_employee_rows(rows, filters):
    """
    Keeps rows that satisfy every requested filter.
    """

    filtered_rows = []

    for row in rows:

        matches_every_filter = all(
            row_matches_filter(row, query_filter)
            for query_filter in filters
        )

        if matches_every_filter:
            filtered_rows.append(row)

    return filtered_rows


def sort_employee_rows(rows, sort_by, sort_order):
    """
    Sorts matching rows when the question asks for sorting.
    """

    if not sort_by:
        return rows

    reverse = sort_order == "descending"

    if sort_by in NUMERIC_FIELDS:
        return sorted(
            rows,
            key=lambda row: convert_numeric_value(
                row.get(sort_by, ""),
                sort_by
            ),
            reverse=reverse
        )

    return sorted(
        rows,
        key=lambda row: row.get(
            sort_by,
            ""
        ).casefold(),
        reverse=reverse
    )


def format_employee_rows(rows, return_fields):
    """
    Converts matching rows into readable bullet points.
    """

    if not return_fields:
        return_fields = [
            "full_name",
            "role",
            "department",
            "location"
        ]

    formatted_rows = []

    for row in rows:
        field_parts = []

        for field in return_fields:
            field_name = field.replace(
                "_",
                " "
            ).title()

            field_parts.append(
                f"{field_name}: {row.get(field, '')}"
            )

        formatted_rows.append(
            "- " + " | ".join(field_parts)
        )

    return "\n".join(formatted_rows)


def execute_query_plan(plan):
    """
    Executes the validated query plan against the entire CSV.
    """

    rows = load_employee_rows()

    matching_rows = filter_employee_rows(
        rows,
        plan["filters"]
    )

    matching_rows = sort_employee_rows(
        matching_rows,
        plan["sort_by"],
        plan["sort_order"]
    )

    operation = plan["operation"]

    if operation == "count":
        return (
            f"There are {len(matching_rows)} "
            f"matching employees."
        )

    if operation in {"list", "count_and_list"}:
        if not matching_rows:
            return "No matching employees were found."

        displayed_rows = matching_rows

        if plan["limit"] > 0:
            displayed_rows = displayed_rows[
                :plan["limit"]
            ]

        formatted_rows = format_employee_rows(
            displayed_rows,
            plan["return_fields"]
        )

        if operation == "count_and_list":
            return (
                f"There are {len(matching_rows)} "
                f"matching employees:\n\n"
                f"{formatted_rows}"
            )

        return formatted_rows

    aggregate_field = plan["aggregate_field"]

    numeric_values = [
        convert_numeric_value(
            row[aggregate_field],
            aggregate_field
        )
        for row in matching_rows
        if row.get(aggregate_field, "") != ""
    ]

    if not numeric_values:
        return (
            "No matching numeric values were found "
            "for that calculation."
        )

    if operation == "sum":
        result = sum(numeric_values)

    elif operation == "average":
        result = sum(numeric_values) / len(
            numeric_values
        )

    elif operation == "minimum":
        result = min(numeric_values)

    elif operation == "maximum":
        result = max(numeric_values)

    else:
        raise ValueError("Unsupported operation.")

    readable_field = aggregate_field.replace(
        "_",
        " "
    ).title()

    return (
        f"{operation.title()} {readable_field}: "
        f"{result:,.2f}"
    )


def try_structured_employee_query(question, role):
    """
    Returns an answer-and-sources tuple for structured
    employee questions.

    Returns None when the normal RAG path should be used.
    """

    plan = create_query_plan(question)

    validate_query_plan(plan)

    if plan["route"] == "rag":
        return None

    if role not in {"hr", "executive"}:
        return (
            "You do not have permission to access "
            "structured employee information.",
            []
        )

    answer = execute_query_plan(plan)

    return answer, ["hr/hr_data.csv"]