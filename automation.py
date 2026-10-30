import logging

from database import (
    DATABASE_PATH,
    get_accessible_documents,
    record_automation
)

from knowledge_assistant import build_document_chunks
from gemini_assistant import generate_answer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

AUTOMATION_TYPE = "financial_report_summary"

SUMMARY_QUESTION = (
    "Prepare a concise executive summary of this financial report. "
    "Highlight the main financial results, important business "
    "developments, and any risks explicitly mentioned. "
    "Use only the supplied document evidence. "
    "Do not invent figures or calculate missing values."
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# AUTOMATION HISTORY
# --------------------------------------------------

def _save_automation_history(
    status,
    summary,
    user_id,
    db_path
):
    """
    Saves the final automation result in SQLite.
    Returns the database record ID.
    """

    return record_automation(
        automation_type=AUTOMATION_TYPE,
        status=status,
        summary=summary,
        user_id=user_id,
        db_path=db_path
    )


# --------------------------------------------------
# FINANCIAL REPORT AUTOMATION
# --------------------------------------------------

def run_financial_report_automation(
    user_id,
    role,
    document_id,
    db_path=DATABASE_PATH,
    client=None
):
    """
    Generates and stores an executive summary
    of an uploaded financial report.

    Workflow:
        1. Check administrator access.
        2. Find the selected accessible document.
        3. Extract document text into chunks.
        4. Generate an evidence-based Gemini summary.
        5. Record the final result in SQLite.

    An injected client supports mock testing.
    """

    # STEP 1: Only administrators can run this automation.

    if role != "admin":

        message = (
            "Access denied. Only administrators can "
            "run financial report automation."
        )

        automation_id = _save_automation_history(
            status="failed",
            summary=message,
            user_id=user_id,
            db_path=db_path
        )

        return {
            "status": "access_denied",
            "summary": message,
            "automation_id": automation_id,
            "sources": [],
            "mode": "none"
        }

    # STEP 2: Validate document ID.

    if (
        isinstance(document_id, bool)
        or not isinstance(document_id, int)
        or document_id <= 0
    ):

        message = "A valid document ID is required."

        automation_id = _save_automation_history(
            status="failed",
            summary=message,
            user_id=user_id,
            db_path=db_path
        )

        return {
            "status": "invalid_document",
            "summary": message,
            "automation_id": automation_id,
            "sources": [],
            "mode": "none"
        }

    try:

        # STEP 3: Retrieve documents the administrator
        # is permitted to access.

        documents = get_accessible_documents(
            user_id=user_id,
            role=role,
            db_path=db_path
        )

        selected_document = next(
            (
                document
                for document in documents
                if document["id"] == document_id
            ),
            None
        )

        if selected_document is None:

            message = (
                "The selected document was not found "
                "or is not accessible."
            )

            automation_id = _save_automation_history(
                status="failed",
                summary=message,
                user_id=user_id,
                db_path=db_path
            )

            return {
                "status": "document_not_found",
                "summary": message,
                "automation_id": automation_id,
                "sources": [],
                "mode": "none"
            }

        # STEP 4: Extract document text using the
        # existing document retrieval functionality.

        passages = build_document_chunks(
            documents=[selected_document]
        )

        if not passages:

            message = (
                "The selected document contains no "
                "usable text for summarization."
            )

            automation_id = _save_automation_history(
                status="failed",
                summary=message,
                user_id=user_id,
                db_path=db_path
            )

            return {
                "status": "insufficient_evidence",
                "summary": message,
                "automation_id": automation_id,
                "sources": [],
                "mode": "none"
            }

        # STEP 5: Generate the executive summary.

        ai_result = generate_answer(
            question=SUMMARY_QUESTION,
            passages=passages,
            client=client
        )

        # STEP 6: Record the final result in SQLite.

        successful = ai_result.get("status") == "success"

        automation_status = (
            "completed" if successful else "failed"
        )

        summary = ai_result.get(
            "answer",
            "No summary was generated."
        )

        automation_id = _save_automation_history(
            status=automation_status,
            summary=summary,
            user_id=user_id,
            db_path=db_path
        )

        return {
            "status": ai_result["status"],
            "summary": summary,
            "automation_id": automation_id,
            "automation_status": automation_status,
            "sources": ai_result.get("sources", []),
            "mode": ai_result.get("mode", "none")
        }

    except Exception:

        logger.exception(
            "Financial report automation failed."
        )

        message = (
            "Financial report automation failed. "
            "Please check the document and try again."
        )

        try:

            automation_id = _save_automation_history(
                status="failed",
                summary=message,
                user_id=user_id,
                db_path=db_path
            )

        except Exception:

            logger.exception(
                "Could not record automation failure."
            )

            automation_id = None

        return {
            "status": "error",
            "summary": message,
            "automation_id": automation_id,
            "sources": [],
            "mode": "none"
        }