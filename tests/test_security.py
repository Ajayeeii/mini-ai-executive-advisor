from pathlib import Path

import pytest

import hr_advisor
import knowledge_assistant

from database import (
    initialize_database,
    create_user,
    add_document
)


@pytest.fixture
def test_database(tmp_path):

    db_path = tmp_path / "test_advisor.db"

    initialize_database(db_path)

    admin_id = create_user(
        username="test_admin",
        password_hash="test_hash",
        role="admin",
        db_path=db_path
    )

    standard_id = create_user(
        username="test_user",
        password_hash="test_hash",
        role="standard",
        db_path=db_path
    )

    return {
        "db_path": db_path,
        "admin_id": admin_id,
        "standard_id": standard_id,
        "directory": tmp_path
    }


def create_document(
    test_database,
    file_name,
    content,
    access_level
):

    file_path = test_database["directory"] / file_name

    file_path.write_text(
        content,
        encoding="utf-8"
    )

    document_id = add_document(
        file_name=file_name,
        file_type="txt",
        storage_path=str(file_path),
        uploaded_by=test_database["admin_id"],
        access_level=access_level,
        db_path=test_database["db_path"]
    )

    return document_id, file_path


# --------------------------------------------------
# TEST 1: INVALID HR QUESTION
# --------------------------------------------------

def test_hr_advisor_rejects_empty_question(monkeypatch):

    def unexpected_search(**kwargs):
        raise AssertionError("Search should not run.")

    monkeypatch.setattr(
        hr_advisor,
        "search_documents",
        unexpected_search
    )

    result = hr_advisor.ask_hr_advisor(
        user_id=1,
        role="standard",
        question=""
    )

    assert result["status"] == "invalid_question"
    assert result["sources"] == []


# --------------------------------------------------
# TEST 2: HR RELEVANCE FILTER
# --------------------------------------------------

def test_hr_filter_keeps_hr_passages():

    passages = [
        {
            "text": "Employees receive annual leave."
        },
        {
            "text": "Quarterly revenue increased."
        }
    ]

    results = hr_advisor.filter_hr_passages(passages)

    assert len(results) == 1
    assert "annual leave" in results[0]["text"]


# --------------------------------------------------
# TEST 3: NO HR EVIDENCE
# --------------------------------------------------

def test_hr_advisor_returns_insufficient_evidence(
    monkeypatch
):

    monkeypatch.setattr(
        hr_advisor,
        "search_documents",
        lambda **kwargs: [
            {
                "text": "Quarterly revenue increased.",
                "file_name": "Finance_Report.txt"
            }
        ]
    )

    def unexpected_generation(**kwargs):
        raise AssertionError("Gemini should not be called.")

    monkeypatch.setattr(
        hr_advisor,
        "generate_answer",
        unexpected_generation
    )

    result = hr_advisor.ask_hr_advisor(
        user_id=2,
        role="standard",
        question="What is the annual leave policy?"
    )

    assert result["status"] == "insufficient_evidence"
    assert result["sources"] == []


# --------------------------------------------------
# TEST 4: ONLY HR PASSAGES REACH GEMINI
# --------------------------------------------------

def test_hr_advisor_sends_only_hr_passages_to_gemini(
    monkeypatch
):

    passages = [
        {
            "text": "Employees receive 24 days annual leave.",
            "file_name": "HR_Policy.txt"
        },
        {
            "text": "Quarterly revenue increased.",
            "file_name": "Finance_Report.txt"
        }
    ]

    monkeypatch.setattr(
        hr_advisor,
        "search_documents",
        lambda **kwargs: passages
    )

    captured = {}

    def fake_generate_answer(question, passages, client=None):

        captured["question"] = question
        captured["passages"] = passages

        return {
            "status": "success",
            "answer": "Employees receive 24 days annual leave.",
            "sources": [],
            "mode": "mock"
        }

    monkeypatch.setattr(
        hr_advisor,
        "generate_answer",
        fake_generate_answer
    )

    result = hr_advisor.ask_hr_advisor(
        user_id=2,
        role="standard",
        question="What is the annual leave policy?"
    )

    assert result["status"] == "success"

    assert len(captured["passages"]) == 1

    assert captured["passages"][0]["file_name"] == (
        "HR_Policy.txt"
    )


# --------------------------------------------------
# TEST 5: STANDARD USER CANNOT ACCESS ADMIN HR FILE
# --------------------------------------------------

def test_standard_user_cannot_access_admin_hr_document(
    test_database,
    monkeypatch
):

    public_id, public_path = create_document(
        test_database,
        "Public_Company_Info.txt",
        "The company provides general business services.",
        "public"
    )

    secret_id, secret_path = create_document(
        test_database,
        "Confidential_HR_Policy.txt",
        "Confidential employee termination policy.",
        "admin_only"
    )

    accessed_files = []

    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(path):

        accessed_files.append(path.resolve())

        return original_read_bytes(path)

    monkeypatch.setattr(
        knowledge_assistant.Path,
        "read_bytes",
        tracked_read_bytes
    )

    result = hr_advisor.ask_hr_advisor(
        user_id=test_database["standard_id"],
        role="standard",
        question="What is the confidential employee termination policy?",
        db_path=test_database["db_path"]
    )

    assert result["status"] == "insufficient_evidence"

    assert secret_path.resolve() not in accessed_files


# --------------------------------------------------
# TEST 6: ADMIN CAN ACCESS ADMIN HR DOCUMENT
# --------------------------------------------------

def test_admin_can_access_admin_hr_document(
    test_database,
    monkeypatch
):

    document_id, file_path = create_document(
        test_database,
        "Confidential_HR_Policy.txt",
        "Employees must follow the company disciplinary policy.",
        "admin_only"
    )

    captured = {}

    def fake_generate_answer(question, passages, client=None):

        captured["passages"] = passages

        return {
            "status": "success",
            "answer": "The document describes the disciplinary policy.",
            "sources": [],
            "mode": "mock"
        }

    monkeypatch.setattr(
        hr_advisor,
        "generate_answer",
        fake_generate_answer
    )

    result = hr_advisor.ask_hr_advisor(
        user_id=test_database["admin_id"],
        role="admin",
        question="What is the employee disciplinary policy?",
        db_path=test_database["db_path"]
    )

    assert result["status"] == "success"

    assert len(captured["passages"]) >= 1

    assert captured["passages"][0]["document_id"] == document_id