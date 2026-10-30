
import pytest

import automation

from database import (
    initialize_database,
    create_user,
    add_document,
    get_automation_history
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
    access_level="admin_only"
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

    return document_id


# --------------------------------------------------
# MOCK GEMINI CLIENT
# --------------------------------------------------

class MockResponse:

    def __init__(self, output_text):
        self.output_text = output_text


class MockInteractions:

    def __init__(self, output_text="Executive summary generated."):

        self.output_text = output_text
        self.call_count = 0

    def create(self, **kwargs):

        self.call_count += 1

        return MockResponse(self.output_text)


class MockGeminiClient:

    def __init__(self, output_text="Executive summary generated."):

        self.interactions = MockInteractions(output_text)


# --------------------------------------------------
# TEST 1: SUCCESSFUL AUTOMATION
# --------------------------------------------------

def test_financial_report_automation_success(test_database):

    document_id = create_test_document(
        test_database,
        "Financial_Report.txt",
        """
        Total Revenue: 100000
        Total Cost of Goods Sold: 40000
        Total Operating Expenses: 25000
        Net Profit: 35000
        """
    )

    mock_client = MockGeminiClient(
        "Revenue was 100000 and net profit was 35000."
    )

    result = automation.run_financial_report_automation(
        user_id=test_database["admin_id"],
        role="admin",
        document_id=document_id,
        db_path=test_database["db_path"],
        client=mock_client
    )

    assert result["status"] == "success"

    assert result["automation_status"] == "completed"

    assert result["summary"] == (
        "Revenue was 100000 and net profit was 35000."
    )

    assert result["automation_id"] is not None

    assert mock_client.interactions.call_count == 1

    history = get_automation_history(
        test_database["db_path"]
    )

    assert len(history) == 1

    assert history[0]["status"] == "completed"

    assert history[0]["user_id"] == test_database["admin_id"]


# --------------------------------------------------
# TEST 2: STANDARD USER ACCESS DENIED
# --------------------------------------------------

def test_standard_user_cannot_run_automation(test_database):

    result = automation.run_financial_report_automation(
        user_id=test_database["standard_id"],
        role="standard",
        document_id=1,
        db_path=test_database["db_path"]
    )

    assert result["status"] == "access_denied"

    assert result["automation_id"] is not None

    history = get_automation_history(
        test_database["db_path"]
    )

    assert len(history) == 1

    assert history[0]["status"] == "failed"


# --------------------------------------------------
# TEST 3: DOCUMENT NOT FOUND
# --------------------------------------------------

def test_automation_handles_missing_document(test_database):

    result = automation.run_financial_report_automation(
        user_id=test_database["admin_id"],
        role="admin",
        document_id=999,
        db_path=test_database["db_path"]
    )

    assert result["status"] == "document_not_found"

    assert result["automation_id"] is not None

    history = get_automation_history(
        test_database["db_path"]
    )

    assert len(history) == 1

    assert history[0]["status"] == "failed"


# --------------------------------------------------
# TEST 4: GEMINI FAILURE
# --------------------------------------------------

def test_automation_handles_gemini_failure(test_database):

    document_id = create_test_document(
        test_database,
        "Financial_Report.txt",
        """
        Total Revenue: 100000
        Total Cost of Goods Sold: 40000
        Total Operating Expenses: 25000
        """
    )

    class FailingInteractions:

        def create(self, **kwargs):
            raise RuntimeError("Simulated Gemini failure.")

    class FailingGeminiClient:

        def __init__(self):
            self.interactions = FailingInteractions()

    result = automation.run_financial_report_automation(
        user_id=test_database["admin_id"],
        role="admin",
        document_id=document_id,
        db_path=test_database["db_path"],
        client=FailingGeminiClient()
    )

    assert result["status"] == "error"

    assert result["automation_status"] == "failed"

    assert result["automation_id"] is not None

    history = get_automation_history(
        test_database["db_path"]
    )

    assert len(history) == 1

    assert history[0]["status"] == "failed"


# --------------------------------------------------
# TEST 5: INVALID DOCUMENT ID
# --------------------------------------------------

@pytest.mark.parametrize(
    "invalid_id",
    [0, -1, "invalid", True, None]
)
def test_automation_rejects_invalid_document_id(
    test_database,
    invalid_id
):

    result = automation.run_financial_report_automation(
        user_id=test_database["admin_id"],
        role="admin",
        document_id=invalid_id,
        db_path=test_database["db_path"]
    )

    assert result["status"] == "invalid_document"

    assert result["automation_id"] is not None


# --------------------------------------------------
# TEST 6: DOCUMENT WITHOUT USABLE TEXT
# --------------------------------------------------

def test_automation_handles_empty_document(test_database):

    document_id = create_test_document(
        test_database,
        "Empty_Report.txt",
        "   \n   \n   "
    )

    mock_client = MockGeminiClient()

    result = automation.run_financial_report_automation(
        user_id=test_database["admin_id"],
        role="admin",
        document_id=document_id,
        db_path=test_database["db_path"],
        client=mock_client
    )

    assert result["status"] == "error"

    assert result["automation_id"] is not None

    assert mock_client.interactions.call_count == 0

    history = get_automation_history(
        test_database["db_path"]
    )

    assert len(history) == 1

    assert history[0]["status"] == "failed"
