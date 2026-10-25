import os

import pytest

from rag import answer_question


# These tests run only when RUN_LIVE_EVALS=1.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_EVALS") != "1",
    reason="Live Groq evaluations are disabled."
)


@pytest.mark.parametrize(
    "question, role, expected_words, expected_source",
    [
        (
            "How many days of sick leave are provided?",
            "employee",
            ["sick", "12"],
            "general/employee_handbook.md"
        ),
        (
            "What is the disaster recovery RTO?",
            "engineering",
            ["4", "hour"],
            "engineering/engineering_master_doc.md"
        ),
        (
            "What was the Q4 2024 net income?",
            "finance",
            ["325", "million"],
            "finance/quarterly_financial_report.md"
        ),
        (
            "What was the Q3 customer acquisition target?",
            "marketing",
            ["180", "000"],
            "marketing/marketing_report_q3_2024.md"
        ),
        (
            "Tell me about Prisha Mehta.",
            "hr",
            ["prisha mehta", "marketing manager"],
            "hr/hr_data.csv"
        )
    ]
)
def test_answer_contains_expected_facts(
    question,
    role,
    expected_words,
    expected_source
):
    answer, sources = answer_question(
        question=question,
        role=role
    )

    normalized_answer = (
        answer.lower()
        .replace(",", "")
        .replace("-", " ")
    )

    for expected_word in expected_words:
        normalized_word = (
            expected_word.lower()
            .replace(",", "")
            .replace("-", " ")
        )

        assert normalized_word in normalized_answer

    assert expected_source in sources