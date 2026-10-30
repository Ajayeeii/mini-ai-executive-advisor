
from gemini_assistant import generate_answer


sample_passages = [
    {
        "document_id": 1,
        "file_name": "Employee_Handbook.pdf",
        "page_number": 8,
        "section": "Annual Leave",
        "text": (
            "Employees receive 24 working days "
            "of annual leave per year."
        )
    }
]


result = generate_answer(
    question="How many annual leave days do employees receive?",
    passages=sample_passages
)


print("\n--- LIVE GEMINI TEST ---")

print("Status:", result["status"])
print("Mode:", result["mode"])

print("\nAnswer:")
print(result["answer"])

print("\nSources:")
for source in result["sources"]:
    print(source)

print("\n------------------------")
