
import logging
import streamlit as st

from auth import verify_password
from database import (
    DATABASE_PATH,
    initialize_database,
    get_user_by_username,
    get_accessible_documents,
    get_automation_history,
)
from document_processor import process_and_store_document
from gemini_assistant import ask_knowledge_assistant
from finance_advisor import analyze_financial_document
from hr_advisor import ask_hr_advisor
from automation import run_financial_report_automation


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Executive Advisory System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize the existing SQLite database.
initialize_database()


# --------------------------------------------------
# PROFESSIONAL DASHBOARD STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .main-header {
        font-size: 30px;
        font-weight: 700;
        color: #193653;
        margin-bottom: 4px;
    }

    .sub-header {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 25px;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    [data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.07);
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def display_header(title, subtitle):
    st.markdown(
        f'<div class="main-header">{title}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="sub-header">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def display_sources(sources):
    if not sources:
        st.info("No supporting document references available.")
        return

    st.markdown("**Supporting document references**")

    for source in sources:
        file_name = source.get("file_name", "Unknown document")
        page = source.get("page_number")
        section = source.get("section")

        details = [file_name]

        if page is not None:
            details.append(f"Page {page}")

        if section:
            details.append(f"Section: {section}")

        st.markdown("- " + " | ".join(details))


def get_documents():
    user = st.session_state.user

    return get_accessible_documents(
        user_id=user["id"],
        role=user["role"],
        db_path=DATABASE_PATH,
    )


def show_error(message):
    st.error(message)


def format_amount(value):
    if value is None:
        return "Not available"

    return f"{value:,.2f}"


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

def login_screen():

    st.markdown("")
    st.markdown("")

    left, center, right = st.columns([1, 1.4, 1])

    with center:

        st.markdown(
            "<h1 style='text-align:center;color:#193653;'>"
            "AI Executive Advisory System"
            "</h1>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<p style='text-align:center;color:gray;'>"
            "Secure Business Intelligence & Advisory Platform"
            "</p>",
            unsafe_allow_html=True,
        )

        st.markdown("---")

        with st.form("login_form"):

            username = st.text_input(
                "Username",
                placeholder="Enter your username",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            submitted = st.form_submit_button(
                "Sign in",
                use_container_width=True,
                type="primary",
            )

        if submitted:

            if not username.strip() or not password:
                st.warning("Please enter your username and password.")

            else:
                try:
                    user = get_user_by_username(
                        username.strip(),
                        db_path=DATABASE_PATH,
                    )

                    if user and verify_password(
                        password,
                        user["password_hash"],
                    ):

                        # Only trusted database identity is stored.
                        st.session_state.user = {
                            "id": user["id"],
                            "username": user["username"],
                            "role": user["role"],
                        }

                        st.rerun()

                    else:
                        st.error("Invalid username or password.")

                except Exception:
                    logger.exception("Login operation failed.")
                    st.error("Unable to complete login. Please try again.")


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

def sidebar_navigation():

    user = st.session_state.user

    with st.sidebar:

        st.markdown("## 📊 Executive Advisor")
        st.caption("Business Intelligence Platform")

        st.divider()

        st.markdown(f"**User:** {user['username']}")

        role_label = (
            "Administrator"
            if user["role"] == "admin"
            else "Standard User"
        )

        st.caption(f"Role: {role_label}")

        st.divider()

        pages = [
            "Executive Overview",
            "Document Management",
            "Knowledge Assistant",
            "Finance Advisor",
            "HR Advisor",
        ]

        if user["role"] == "admin":
            pages.extend([
                "Financial Automation",
                "Automation History",
            ])

        selected_page = st.radio(
            "Navigation",
            pages,
        )

        st.divider()

        if st.button("Log out", use_container_width=True):

            st.session_state.user = None
            st.rerun()

    return selected_page


# --------------------------------------------------
# EXECUTIVE OVERVIEW
# --------------------------------------------------

def overview_page():

    display_header(
        "Executive Overview",
        "Your business intelligence workspace.",
    )

    try:
        documents = get_documents()

        document_count = len(documents)

        admin = st.session_state.user["role"] == "admin"

        col1, col2, col3 = st.columns(3)

        col1.metric("Accessible Documents", document_count)

        col2.metric(
            "Account Type",
            "Administrator" if admin else "Standard User",
        )

        col3.metric(
            "AI Platform",
            "Gemini",
        )

        st.markdown("---")

        st.subheader("Welcome to your advisory workspace")

        st.markdown(
            """
            Use the navigation panel to access:

            - **Document Management:** Upload and review business documents.
            - **Knowledge Assistant:** Ask questions about uploaded documents.
            - **Finance Advisor:** Review financial figures and profitability.
            - **HR Advisor:** Retrieve employee policies and HR information.
            """
        )

        if admin:
            st.info(
                "Administrator privileges include financial report "
                "automation and automation history."
            )

        st.subheader("Recently accessible documents")

        if documents:
            st.dataframe(
                [
                    {
                        "Document": doc["file_name"],
                        "Type": doc["file_type"],
                        "Access": doc["access_level"],
                        "Uploaded": doc["created_at"],
                    }
                    for doc in documents[:5]
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("No accessible documents have been uploaded yet.")

    except Exception:
        logger.exception("Overview loading failed.")
        show_error("Unable to load the dashboard overview.")


# --------------------------------------------------
# DOCUMENT MANAGEMENT
# --------------------------------------------------

def document_management_page():

    display_header(
        "Document Management",
        "Upload and manage business knowledge documents.",
    )

    user = st.session_state.user
    is_admin = user["role"] == "admin"

    st.subheader("Upload a document")

    with st.form("document_upload_form"):

        uploaded_file = st.file_uploader(
            "Select a document",
            type=["pdf", "docx", "txt"],
            help="Maximum file size: 10 MB.",
        )

        if is_admin:

            access_level = st.selectbox(
                "Document access level",
                ["public", "restricted", "admin_only"],
            )

        else:

            access_level = "public"

            st.info(
                "Standard-user uploads are restricted to public documents."
            )

        upload_submitted = st.form_submit_button(
            "Upload document",
            type="primary",
        )

    if upload_submitted:

        if uploaded_file is None:
            st.warning("Please select a document.")

        else:
            try:
                # Server-side role and access-level validation.
                if (
                    user["role"] == "standard"
                    and access_level != "public"
                ):
                    st.error("You are not permitted to assign this access level.")

                elif (
                    user["role"] not in ("admin", "standard")
                ):
                    st.error("Invalid account permissions.")

                else:
                    result = process_and_store_document(
                        file_name=uploaded_file.name,
                        file_bytes=uploaded_file.getvalue(),
                        uploaded_by=user["id"],
                        access_level=access_level,
                        db_path=DATABASE_PATH,
                    )

                    st.success(
                        f"Successfully uploaded: {result['file_name']}"
                    )

                    st.caption(
                        f"Document ID: {result['document_id']}"
                    )

                    st.rerun()

            except Exception:
                logger.exception("Document upload failed.")
                st.error(
                    "The document could not be uploaded. "
                    "Check its format and try again."
                )

    st.divider()

    st.subheader("Accessible documents")

    try:
        documents = get_documents()

        if documents:

            st.dataframe(
                [
                    {
                        "ID": doc["id"],
                        "Document": doc["file_name"],
                        "Type": doc["file_type"],
                        "Access": doc["access_level"],
                        "Uploaded": doc["created_at"],
                    }
                    for doc in documents
                ],
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("No accessible documents found.")

    except Exception:
        logger.exception("Document listing failed.")
        st.error("Unable to retrieve documents.")


# --------------------------------------------------
# KNOWLEDGE ASSISTANT
# --------------------------------------------------

def knowledge_page():

    display_header(
        "Knowledge Assistant",
        "Ask questions using evidence from your accessible documents.",
    )

    with st.form("knowledge_form"):

        question = st.text_area(
            "Your question",
            placeholder="Example: What is the company's annual leave entitlement?",
        )

        submitted = st.form_submit_button(
            "Ask Knowledge Assistant",
            type="primary",
        )

    if submitted:

        if not question.strip():
            st.warning("Please enter a question.")

        else:

            user = st.session_state.user

            with st.spinner("Searching documents and generating an answer..."):

                try:
                    result = ask_knowledge_assistant(
                        user_id=user["id"],
                        role=user["role"],
                        question=question,
                        db_path=DATABASE_PATH,
                    )

                    st.subheader("Answer")

                    if result["status"] == "success":
                        st.success(result["answer"])

                    elif result["status"] == "insufficient_evidence":
                        st.warning(result["answer"])

                    else:
                        st.error(result["answer"])

                    if result.get("mode") == "real_gemini":
                        st.caption("Response generated using Gemini.")

                    display_sources(result.get("sources", []))

                except Exception:
                    logger.exception("Knowledge Assistant failed.")
                    st.error(
                        "The Knowledge Assistant encountered an error. "
                        "Please try again."
                    )


# --------------------------------------------------
# FINANCE ADVISOR
# --------------------------------------------------

def finance_page():

    display_header(
        "Finance Advisor",
        "Financial analysis based on accessible business documents.",
    )

    st.info(
        "Financial metrics are calculated using Python Decimal, "
        "not generated by the language model."
    )

    if st.button("Run Financial Analysis", type="primary"):

        user = st.session_state.user

        with st.spinner("Analysing financial documents..."):

            try:
                result = analyze_financial_document(
                    user_id=user["id"],
                    role=user["role"],
                    db_path=DATABASE_PATH,
                )

                metrics = result["metrics"]

                st.subheader("Financial Performance")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Revenue",
                    format_amount(metrics["revenue"]),
                )

                col2.metric(
                    "Gross Profit",
                    format_amount(metrics["gross_profit"]),
                )

                col3.metric(
                    "Net Profit",
                    format_amount(metrics["net_profit"]),
                )

                st.divider()

                col1, col2 = st.columns(2)

                col1.metric(
                    "Total Expenses",
                    format_amount(metrics["total_expenses"]),
                )

                col2.metric(
                    "Cost of Goods Sold",
                    format_amount(metrics["cost_of_goods_sold"]),
                )

                col1, col2 = st.columns(2)

                gross_margin = metrics["gross_profit_margin"]
                net_margin = metrics["net_profit_margin"]

                col1.metric(
                    "Gross Profit Margin",
                    f"{gross_margin:.2f}%" if gross_margin is not None else "N/A",
                )

                col2.metric(
                    "Net Profit Margin",
                    f"{net_margin:.2f}%" if net_margin is not None else "N/A",
                )

                st.subheader("Financial Inputs")

                st.json(result["financial_inputs"])

                display_sources(result.get("sources", []))

            except ValueError as error:
                st.warning(str(error))

            except Exception:
                logger.exception("Finance Advisor failed.")
                st.error(
                    "Financial analysis could not be completed."
                )


# --------------------------------------------------
# HR ADVISOR
# --------------------------------------------------

def hr_page():

    display_header(
        "HR Advisor",
        "Find answers using accessible employee policies and HR documents.",
    )

    with st.form("hr_form"):

        question = st.text_area(
            "Your HR question",
            placeholder="Example: How many annual leave days are provided?",
        )

        submitted = st.form_submit_button(
            "Ask HR Advisor",
            type="primary",
        )

    if submitted:

        if not question.strip():
            st.warning("Please enter an HR question.")

        else:

            user = st.session_state.user

            with st.spinner("Searching HR documents..."):

                try:
                    result = ask_hr_advisor(
                        user_id=user["id"],
                        role=user["role"],
                        question=question,
                        db_path=DATABASE_PATH,
                    )

                    st.subheader("HR Advisory Response")

                    if result["status"] == "success":
                        st.success(result["answer"])

                    elif result["status"] == "insufficient_evidence":
                        st.warning(result["answer"])

                    else:
                        st.error(result["answer"])

                    display_sources(result.get("sources", []))

                except Exception:
                    logger.exception("HR Advisor failed.")
                    st.error(
                        "The HR Advisor encountered an error. "
                        "Please try again."
                    )


# --------------------------------------------------
# ADMINISTRATOR: FINANCIAL AUTOMATION
# --------------------------------------------------

def automation_page():

    user = st.session_state.user

    if user["role"] != "admin":
        st.error("Access denied.")
        return

    display_header(
        "Financial Report Automation",
        "Generate and store AI-powered financial report summaries.",
    )

    try:
        documents = get_documents()

        if not documents:
            st.warning("Upload a financial report before running automation.")
            return

        document_options = {
            f"{doc['file_name']} (ID: {doc['id']})": doc["id"]
            for doc in documents
        }

        with st.form("automation_form"):

            selected_document = st.selectbox(
                "Select financial report",
                list(document_options.keys()),
            )

            submitted = st.form_submit_button(
                "Generate Executive Summary",
                type="primary",
            )

        if submitted:

            document_id = document_options[selected_document]

            with st.spinner("Generating financial report summary..."):

                result = run_financial_report_automation(
                    user_id=user["id"],
                    role=user["role"],
                    document_id=document_id,
                    db_path=DATABASE_PATH,
                )

            if result["status"] == "success":
                st.success("Financial report automation completed.")

                st.subheader("Executive Summary")
                st.markdown(result["summary"])

                st.caption(
                    f"Automation record ID: {result['automation_id']}"
                )

                display_sources(result.get("sources", []))

            else:
                st.error(result["summary"])

                if result.get("automation_id"):
                    st.caption(
                        f"Execution record ID: {result['automation_id']}"
                    )

    except Exception:
        logger.exception("Financial automation page failed.")
        st.error("Unable to run financial report automation.")


# --------------------------------------------------
# ADMINISTRATOR: AUTOMATION HISTORY
# --------------------------------------------------

def automation_history_page():

    user = st.session_state.user

    if user["role"] != "admin":
        st.error("Access denied.")
        return

    display_header(
        "Automation History",
        "Review previously executed business automations.",
    )

    try:
        # History is retrieved only after the server-side role check.
        history = get_automation_history(
            db_path=DATABASE_PATH,
        )

        if not history:
            st.info("No automation records found.")
            return

        st.metric("Total Automation Executions", len(history))

        st.dataframe(
            [
                {
                    "ID": item["id"],
                    "Type": item["automation_type"],
                    "Status": item["status"],
                    "User ID": item["user_id"],
                    "Created": item["created_at"],
                    "Summary": item["summary"],
                }
                for item in history
            ],
            use_container_width=True,
            hide_index=True,
        )

    except Exception:
        logger.exception("Automation history retrieval failed.")
        st.error("Unable to retrieve automation history.")


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

def main():

    if st.session_state.user is None:
        login_screen()
        return

    selected_page = sidebar_navigation()

    if selected_page == "Executive Overview":
        overview_page()

    elif selected_page == "Document Management":
        document_management_page()

    elif selected_page == "Knowledge Assistant":
        knowledge_page()

    elif selected_page == "Finance Advisor":
        finance_page()

    elif selected_page == "HR Advisor":
        hr_page()

    elif selected_page == "Financial Automation":
        automation_page()

    elif selected_page == "Automation History":
        automation_history_page()


if __name__ == "__main__":
    main()
