import pytest

import rag


EXPECTED_ROLE_ACCESS = {
    "employee": ["general"],
    "engineering": ["general", "engineering"],
    "finance": ["general", "finance"],
    "marketing": ["general", "marketing"],
    "hr": ["general", "hr"],
    "executive": [
        "general",
        "engineering",
        "finance",
        "marketing",
        "hr"
    ]
}


def test_role_access_mapping_is_correct():
    """
    Ensures that the permission configuration has not been
    accidentally changed.
    """

    assert rag.ROLE_ACCESS == EXPECTED_ROLE_ACCESS


@pytest.mark.parametrize(
    "role",
    [
        "employee",
        "engineering",
        "finance",
        "marketing",
        "hr",
        "executive"
    ]
)
def test_retrieval_uses_correct_department_filter(
    role,
    monkeypatch
):
    """
    Ensures retrieve_documents() sends the correct RBAC
    metadata filter to ChromaDB.
    """

    captured_query = {}

    class FakeCollection:

        def query(self, **kwargs):
            captured_query.update(kwargs)

            return {
                "ids": [["test-document"]],
                "documents": [["Test company information"]],
                "metadatas": [[{
                    "source": "test.md",
                    "department": rag.ROLE_ACCESS[role][0]
                }]],
                "distances": [[0.1]]
            }

    # Replace the real Chroma collection during this test.
    monkeypatch.setattr(
        rag,
        "collection",
        FakeCollection()
    )

    # Skip exact employee matching for this test.
    monkeypatch.setattr(
        rag,
        "retrieve_exact_employee",
        lambda question, allowed_departments: None
    )

    rag.retrieve_documents(
        question="Test company question",
        role=role
    )

    assert captured_query["where"] == {
        "department": {
            "$in": EXPECTED_ROLE_ACCESS[role]
        }
    }


@pytest.mark.parametrize(
    "role",
    [
        "employee",
        "engineering",
        "finance",
        "marketing"
    ]
)
def test_non_hr_roles_cannot_use_exact_employee_lookup(
    role,
    monkeypatch
):
    """
    Ensures roles without HR permission cannot retrieve
    exact employee records.
    """

    class FailIfDatabaseIsAccessed:

        def get(self, **kwargs):
            pytest.fail(
                "ChromaDB should not be accessed for an "
                "unauthorized exact employee lookup."
            )

    monkeypatch.setattr(
        rag,
        "collection",
        FailIfDatabaseIsAccessed()
    )

    result = rag.retrieve_exact_employee(
        question="Tell me about Prisha Mehta",
        allowed_departments=rag.ROLE_ACCESS[role]
    )

    assert result is None


@pytest.mark.parametrize(
    "role",
    [
        "hr",
        "executive"
    ]
)
def test_hr_and_executive_can_use_exact_employee_lookup(
    role,
    monkeypatch
):
    """
    Ensures HR and executives can retrieve an employee
    using an exact full-name match.
    """

    class FakeEmployeeCollection:

        def get(self, **kwargs):
            return {
                "ids": ["employee:FINEMP1007"],
                "documents": [
                    "Employee Id: FINEMP1007\n"
                    "Full Name: Prisha Mehta\n"
                    "Role: Marketing Manager"
                ],
                "metadatas": [{
                    "department": "hr",
                    "record_type": "employee",
                    "employee_id": "FINEMP1007",
                    "full_name": "Prisha Mehta",
                    "source": "hr/hr_data.csv"
                }]
            }

    monkeypatch.setattr(
        rag,
        "collection",
        FakeEmployeeCollection()
    )

    result = rag.retrieve_exact_employee(
        question="Tell me about Prisha Mehta",
        allowed_departments=rag.ROLE_ACCESS[role]
    )

    assert result is not None
    assert result["ids"][0] == ["employee:FINEMP1007"]
    assert result["metadatas"][0][0]["department"] == "hr"


def test_invalid_role_is_rejected():
    """
    Ensures an unknown role cannot perform retrieval.
    """

    with pytest.raises(
        ValueError,
        match="Invalid role"
    ):
        rag.retrieve_documents(
            question="Show me company information",
            role="admin"
        )