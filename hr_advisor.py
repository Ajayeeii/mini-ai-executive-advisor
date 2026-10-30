
from database import DATABASE_PATH
from knowledge_assistant import search_documents
from gemini_assistant import generate_answer


# --------------------------------------------------
# HR CONFIGURATION
# --------------------------------------------------

HR_KEYWORDS = {
    "employee",
    "employees",
    "leave",
    "annual leave",
    "sick leave",
    "attendance",
    "absence",
    "working hours",
    "overtime",
    "recruitment",
    "salary",
    "payroll",
    "resignation",
    "termination",
    "disciplinary",
    "performance",
    "workplace",
    "holiday",
    "maternity",
    "paternity",
    "benefits",
    "human resources",
    "hr policy",
}


# --------------------------------------------------
# HR RELEVANCE FILTER
# --------------------------------------------------

def is_hr_related(text):
    """
    Checks whether text contains HR-related keywords.

    This is a relevance filter, not a security control.
    """

    if not isinstance(text, str) or not text.strip():
        return False

    normalized_text = text.lower()

    return any(
        keyword in normalized_text
        for keyword in HR_KEYWORDS
    )


def filter_hr_passages(passages):
    """
    Keeps passages containing HR-related information.

    Document permissions must already have been
    checked by the existing retrieval engine.
    """

    return [
        passage
        for passage in passages
        if is_hr_related(passage.get("text", ""))
    ]


# --------------------------------------------------
# HR ADVISOR
# --------------------------------------------------

def ask_hr_advisor(
    user_id,
    role,
    question,
    db_path=DATABASE_PATH,
    client=None
):
    """
    Retrieves accessible HR evidence and generates
    an evidence-based HR response using Gemini.
    """

    # STEP 1: Validate the question.

    if not isinstance(question, str) or not question.strip():

        return {
            "status": "invalid_question",
            "answer": "Please enter a valid HR question.",
            "sources": [],
            "mode": "none"
        }

    # STEP 2: Retrieve documents using existing
    # server-side document permission checks.

    passages = search_documents(
        user_id=user_id,
        role=role,
        question=question,
        db_path=db_path
    )

    # STEP 3: Keep HR-related evidence.

    hr_passages = filter_hr_passages(passages)

    # STEP 4: Generate an answer using existing Gemini logic.

    if not hr_passages:

        return {
            "status": "insufficient_evidence",
            "answer": (
                "I could not find sufficient HR evidence "
                "in the accessible uploaded documents "
                "to answer this question."
            ),
            "sources": [],
            "mode": "none"
        }

    return generate_answer(
        question=question,
        passages=hr_passages,
        client=client
    )
