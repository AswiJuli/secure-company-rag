import pytest

from rag import ROLE_ACCESS, retrieve_documents


def get_sources(results):
    return {
        metadata["source"]
        for metadata in results["metadatas"][0]
    }


def get_departments(results):
    return {
        metadata["department"]
        for metadata in results["metadatas"][0]
    }


@pytest.mark.parametrize(
    "question, role, expected_source",
    [
        (
            "What are the different types of leave?",
            "employee",
            "general/employee_handbook.md"
        ),
        (
            "What was the Q4 net income?",
            "finance",
            "finance/quarterly_financial_report.md"
        ),
        (
            "What was the Q3 customer acquisition target?",
            "marketing",
            "marketing/marketing_report_q3_2024.md"
        ),
        (
            "What is the disaster recovery RTO?",
            "engineering",
            "engineering/engineering_master_doc.md"
        ),
        (
            "Tell me about Prisha Mehta.",
            "hr",
            "hr/hr_data.csv"
        )
    ]
)
def test_correct_source_is_retrieved(
    question,
    role,
    expected_source
):
    results = retrieve_documents(question, role)

    sources = get_sources(results)

    assert expected_source in sources


@pytest.mark.parametrize(
    "question, role",
    [
        (
            "What was the Q4 net income?",
            "employee"
        ),
        (
            "Show me employee salary records.",
            "marketing"
        ),
        (
            "Explain the engineering architecture.",
            "finance"
        ),
        (
            "What was the marketing ROI?",
            "hr"
        )
    ]
)
def test_retrieval_never_returns_unauthorized_departments(
    question,
    role
):
    results = retrieve_documents(question, role)

    retrieved_departments = get_departments(results)
    permitted_departments = set(ROLE_ACCESS[role])

    assert retrieved_departments.issubset(
        permitted_departments
    )


def test_employee_cannot_retrieve_prisha_hr_record():
    results = retrieve_documents(
        question="Tell me about Prisha Mehta.",
        role="employee"
    )

    retrieved_departments = get_departments(results)

    assert "hr" not in retrieved_departments


def test_executive_can_retrieve_finance_information():
    results = retrieve_documents(
        question="What was the Q4 net income?",
        role="executive"
    )

    sources = get_sources(results)

    assert "finance/quarterly_financial_report.md" in sources