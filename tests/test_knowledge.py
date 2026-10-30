
import pytest

from pathlib import Path

import knowledge_assistant

from knowledge_assistant import (
    chunk_document,
    retrieve_relevant_passages,
    search_documents
)

from database import (
    initialize_database,
    create_user,
    add_document
)


# --------------------------------------------------
# TEST DATABASE FIXTURE
# --------------------------------------------------

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


# --------------------------------------------------
# HELPER: CREATE TEST DOCUMENT
# --------------------------------------------------

def create_test_document(
    test_database,
    file_name,
    content,
    access_level
):

    file_path = (
        test_database["directory"] / file_name
    )

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
# TEST 1: DOCUMENT CHUNKING
# --------------------------------------------------

def test_document_chunking_preserves_references():

    segments = [
        {
            "page_number": 8,
            "section": None,
            "text": "one two three four five six seven"
        }
    ]

    chunks = chunk_document(
        segments=segments,
        document_id=10,
        file_name="Employee_Handbook.pdf",
        chunk_size=4,
        overlap=1
    )

    assert len(chunks) == 2

    assert chunks[0]["document_id"] == 10

    assert chunks[0]["file_name"] == (
        "Employee_Handbook.pdf"
    )

    assert chunks[0]["page_number"] == 8

    assert chunks[0]["text"] == (
        "one two three four"
    )

    assert chunks[1]["text"] == (
        "four five six seven"
    )


# --------------------------------------------------
# TEST 2: DOCX SECTION PRESERVATION
# --------------------------------------------------

def test_document_chunking_preserves_section():

    segments = [
        {
            "page_number": None,
            "section": "Annual Leave Policy",
            "text": "Employees receive annual leave."
        }
    ]

    chunks = chunk_document(
        segments=segments,
        document_id=20,
        file_name="HR_Policy.docx"
    )

    assert chunks[0]["section"] == (
        "Annual Leave Policy"
    )

    assert chunks[0]["page_number"] is None


# --------------------------------------------------
# TEST 3: RETRIEVAL ACCURACY
# --------------------------------------------------

def test_retrieval_finds_relevant_passage():

    chunks = [
        {
            "document_id": 1,
            "file_name": "HR_Policy.txt",
            "text": (
                "Employees receive annual leave "
                "entitlement of 24 working days."
            )
        },
        {
            "document_id": 2,
            "file_name": "Finance_Report.txt",
            "text": (
                "Quarterly revenue and operating "
                "profit increased."
            )
        }
    ]

    results = retrieve_relevant_passages(
        question="What is the annual leave entitlement?",
        chunks=chunks,
        min_score=0.05
    )

    assert len(results) >= 1

    assert results[0]["file_name"] == (
        "HR_Policy.txt"
    )

    assert results[0]["similarity_score"] > 0


# --------------------------------------------------
# TEST 4: INSUFFICIENT EVIDENCE
# --------------------------------------------------

def test_retrieval_returns_empty_for_unrelated_question():

    chunks = [
        {
            "document_id": 1,
            "file_name": "HR_Policy.txt",
            "text": (
                "Employees receive annual leave."
            )
        }
    ]

    results = retrieve_relevant_passages(
        question="What is the company's spacecraft policy?",
        chunks=chunks,
        min_score=0.05
    )

    assert results == []


# --------------------------------------------------
# TEST 5: UNAUTHORIZED DOCUMENT IS NOT LOADED
# --------------------------------------------------

def test_standard_user_cannot_retrieve_admin_document(
    test_database,
    monkeypatch
):

    # Create a public document.
    public_id, public_path = create_test_document(
        test_database,
        "Employee_Handbook.txt",
        "Employees receive 24 working days of annual leave.",
        "public"
    )

    # Create an administrator-only document.
    secret_id, secret_path = create_test_document(
        test_database,
        "Confidential_Financial_Report.txt",
        "Dragonfruit confidential forecast revenue is 900000.",
        "admin_only"
    )

    # Track which files the retrieval engine opens.
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

    # Search as a standard user.
    results = search_documents(
        user_id=test_database["standard_id"],
        role="standard",
        question="What is the dragonfruit confidential forecast?",
        db_path=test_database["db_path"]
    )

    # No confidential results should be returned.
    assert results == []

    # Public document may be loaded.
    assert public_path.resolve() in accessed_files

    # Confidential document must never be opened.
    assert secret_path.resolve() not in accessed_files


# --------------------------------------------------
# TEST 6: ADMIN CAN ACCESS CONFIDENTIAL DOCUMENT
# --------------------------------------------------

def test_admin_can_retrieve_admin_document(test_database):

    secret_id, secret_path = create_test_document(
        test_database,
        "Confidential_Financial_Report.txt",
        "Dragonfruit confidential forecast revenue is 900000.",
        "admin_only"
    )

    results = search_documents(
        user_id=test_database["admin_id"],
        role="admin",
        question="What is the dragonfruit confidential forecast?",
        db_path=test_database["db_path"]
    )

    assert len(results) >= 1

    assert results[0]["document_id"] == secret_id

    assert results[0]["file_name"] == (
        "Confidential_Financial_Report.txt"
    )


# --------------------------------------------------
# TEST 7: EMPTY QUESTION
# --------------------------------------------------

def test_empty_question_returns_no_results():

    results = retrieve_relevant_passages(
        question="",
        chunks=[]
    )

    assert results == []
