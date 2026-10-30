
from types import SimpleNamespace
from unittest.mock import Mock

import gemini_assistant


# --------------------------------------------------
# TEST DATA
# --------------------------------------------------

SAMPLE_PASSAGES = [
    {
        "document_id": 1,
        "file_name": "Employee_Handbook.pdf",
        "page_number": 8,
        "section": "Annual Leave",
        "text": "Employees receive 24 working days of annual leave."
    }
]


# --------------------------------------------------
# TEST 1: SUCCESSFUL MOCK RESPONSE
# --------------------------------------------------

def test_generate_answer_success():

    client = Mock()

    client.interactions.create.return_value = SimpleNamespace(
        output_text="Employees receive 24 working days of annual leave."
    )

    result = gemini_assistant.generate_answer(
        question="How many annual leave days are provided?",
        passages=SAMPLE_PASSAGES,
        client=client
    )

    assert result["status"] == "success"

    assert result["mode"] == "mock"

    assert "24 working days" in result["answer"]

    assert result["sources"][0]["file_name"] == (
        "Employee_Handbook.pdf"
    )

    assert result["sources"][0]["page_number"] == 8

    client.interactions.create.assert_called_once()

    call_arguments = client.interactions.create.call_args.kwargs

    assert call_arguments["store"] is False

    assert call_arguments["model"] == (
        gemini_assistant.DEFAULT_MODEL
    )


# --------------------------------------------------
# TEST 2: INSUFFICIENT EVIDENCE
# --------------------------------------------------

def test_generate_answer_without_evidence():

    client = Mock()

    result = gemini_assistant.generate_answer(
        question="What is the company revenue?",
        passages=[],
        client=client
    )

    assert result["status"] == "insufficient_evidence"

    assert result["sources"] == []

    assert "sufficient evidence" in result["answer"]

    client.interactions.create.assert_not_called()


# --------------------------------------------------
# TEST 3: GEMINI API FAILURE
# --------------------------------------------------

def test_generate_answer_api_failure():

    client = Mock()

    client.interactions.create.side_effect = Exception(
        "Simulated Gemini API failure"
    )

    result = gemini_assistant.generate_answer(
        question="What is the annual leave policy?",
        passages=SAMPLE_PASSAGES,
        client=client
    )

    assert result["status"] == "error"

    assert result["mode"] == "mock"

    assert "temporarily unavailable" in result["answer"]

    assert len(result["sources"]) == 1


# --------------------------------------------------
# TEST 4: MISSING API KEY
# --------------------------------------------------

def test_generate_answer_missing_api_key(monkeypatch):

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = gemini_assistant.generate_answer(
        question="What is the annual leave policy?",
        passages=SAMPLE_PASSAGES
    )

    assert result["status"] == "configuration_error"

    assert "API key is not configured" in result["answer"]


# --------------------------------------------------
# TEST 5: INVALID QUESTION
# --------------------------------------------------

def test_generate_answer_empty_question():

    client = Mock()

    result = gemini_assistant.generate_answer(
        question="   ",
        passages=SAMPLE_PASSAGES,
        client=client
    )

    assert result["status"] == "invalid_question"

    client.interactions.create.assert_not_called()


# --------------------------------------------------
# TEST 6: RETRIEVAL INTEGRATION
# --------------------------------------------------

def test_ask_knowledge_assistant_uses_existing_retrieval(
    monkeypatch
):

    client = Mock()

    client.interactions.create.return_value = SimpleNamespace(
        output_text="Employees receive 24 working days."
    )

    retrieval_mock = Mock(return_value=SAMPLE_PASSAGES)

    monkeypatch.setattr(
        gemini_assistant,
        "search_documents",
        retrieval_mock
    )

    result = gemini_assistant.ask_knowledge_assistant(
        user_id=1,
        role="standard",
        question="What is the annual leave entitlement?",
        client=client
    )

    retrieval_mock.assert_called_once()

    assert result["status"] == "success"

    assert result["mode"] == "mock"
