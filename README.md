# Mini AI Executive Advisory System

An AI-powered business advisory application designed to help small and medium-sized businesses manage company information, access business documents, and obtain financial and HR-related insights through an integrated AI assistant.

**Project Status: Partially Completed — Under Development**

## 1. Project Overview

The Mini AI Executive Advisory System is a Python-based application developed to explore how Artificial Intelligence can support business management and executive decision-making.

The system combines document processing, information retrieval, financial analysis, HR advisory capabilities, and Google's Gemini AI integration within a Streamlit web application.

The main objective is to create a centralised platform where administrators and authorised users can access company information and obtain AI-assisted business insights.

## 2. Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.15.2 | Main programming language |
| Streamlit 1.66.1 | Web application interface |
| Google Gemini API | AI-powered responses |
| google-genai 2.34.0 | Gemini API integration |
| SQLite | Database management |
| TF-IDF | Document information retrieval |
| Pytest 9.2.0 | Automated testing |
| PyMuPDF | PDF document processing |

## 3. Implemented Features

The following backend and application components have been developed:

### Authentication and Security
- User authentication.
- Password hashing.
- Administrator and standard-user roles.
- Role-based application navigation.
- Document access permissions.

### Database Management
- SQLite database integration.
- User management.
- Document records.
- Document permission management.
- Automation history records.

### Document Management
- Document uploading and processing.
- PDF and text document processing.
- Text extraction.
- Document chunking.
- TF-IDF-based document retrieval.
- Permission-aware document access.

### AI Knowledge Assistant
- Integration with Google Gemini.
- Retrieval of relevant information from company documents.
- AI-assisted answers to business questions.
- Integration between document retrieval and Gemini.

### Finance Advisor
- Financial information analysis.
- Financial report interpretation.
- AI-assisted financial insights.

### HR Advisor
- HR policy information retrieval.
- Employee-related information assistance.
- AI-assisted HR responses.

### Financial Automation
- Financial report automation functionality.
- Automation history storage and retrieval.

### Streamlit Application
The frontend has been developed using Streamlit and includes:

- Login page.
- Executive Overview.
- Document Management.
- Knowledge Assistant.
- Finance Advisor.
- HR Advisor.
- Financial Automation.
- Automation History.
- Role-based navigation.

## 4. Project Structure

```text
mini-ai-executive-advisor/
│
├── app.py
├── auth.py
├── automation.py
├── database.py
├── document_processor.py
├── finance_advisor.py
├── gemini_assistant.py
├── gemini_live_check.py
├── hr_advisor.py
├── knowledge_assistant.py
│
├── data/
│   └── sample_documents/
│       └── Annual_Financial_Report.txt
│
├── tests/
│   ├── test_automation.py
│   ├── test_database.py
│   ├── test_document_processor.py
│   ├── test_finance.py
│   ├── test_gemini_assistant.py
│   ├── test_knowledge.py
│   └── test_security.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 5. Google Gemini API Integration

Google Gemini API is used as the AI engine for generating responses based on retrieved business information.

For this project, I used the Google Gemini API free tier rather than a paid API subscription.

The free-tier integration was useful for developing and testing the AI functionality while keeping development costs low.

However, the free tier has usage limitations, including applicable request quotas and rate limits. Response latency and API availability can also affect the application experience.

## 6. Testing and Verification

Automated testing has been performed using Pytest.

**Latest verified test result:**

- Total tests: 54
- Passed: 54
- Failed: 0
- Execution time: 8.56 seconds

The tests cover:

- Database functionality.
- Document processing.
- Financial analysis.
- Gemini integration.
- Knowledge retrieval.
- Authentication and security.
- Financial automation.

One third-party PyMuPDF deprecation warning was observed during testing. It did not cause any test failures.

## 7. Current Limitations and Project Status

**This project is partially completed and is not yet a fully production-ready enterprise application.**

Although several backend components and the Streamlit interface have been implemented, some areas still require further development, troubleshooting and validation.

The main limitations include:

1. Knowledge Assistant response delays still require investigation and optimisation.
2. Document retrieval performance needs further improvement.
3. Gemini API free-tier usage limitations may affect response speed and availability.
4. End-to-end testing of all advisory modules and document permission scenarios is still required.
5. Additional frontend improvements and usability testing are needed.
6. Further validation of financial automation and reporting workflows is required.

Due to my current technical knowledge and development limitations, I have not been able to complete every planned functionality or fully resolve all outstanding issues.

I consider this an ongoing development project and an opportunity to improve my Python programming, software architecture, database management and AI integration skills.

## 8. Running the Application

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

Navigate to the project directory:

```bash
cd mini-ai-executive-advisor
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure the environment variables using `.env.example` as a reference. Add your own Gemini API credentials locally. Never upload your `.env` file to GitHub.

Run the application:

```powershell
python -m streamlit run app.py
```

Open the local application:

```text
http://localhost:8501
```

## 9. Future Improvements

Planned areas for further development include:

- Improving document retrieval speed.
- Optimising Gemini API response times.
- Improving AI response accuracy and source references.
- Completing end-to-end Finance and HR Advisor testing.
- Improving financial report automation.
- Enhancing the user interface.
- Expanding security and permission testing.
- Improving application reliability and error handling.
- Preparing the application for deployment.

## 10. Project Disclaimer

This project was developed for educational purposes and practical exploration of AI-assisted business advisory applications.

It should not currently be considered a fully tested production system or relied upon for actual financial, legal or HR decisions.

All AI-generated outputs should be independently verified.

---

**Developer:** Independent Python Development Project

**Project:** Mini AI Executive Advisory System

**Status:** Partially Completed — Under Development

**AI Platform:** Google Gemini API (Free Tier)