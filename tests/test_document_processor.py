
import io
import tempfile
import unittest

from pathlib import Path

import pymupdf

from docx import Document

from database import (
    initialize_database,
    create_user,
    get_accessible_documents
)

from document_processor import (
    DocumentProcessingError,
    validate_uploaded_file,
    extract_document_text,
    process_and_store_document
)


class TestDocumentProcessor(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.base_path = Path(self.temp_dir.name)

        self.db_path = self.base_path / "test.db"

        self.upload_dir = self.base_path / "uploads"

        initialize_database(self.db_path)

        self.admin_id = create_user(
            "admin",
            "test_hash",
            "admin",
            self.db_path
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    # ---------------------------------------------
    # HELPER: CREATE A TEST PDF
    # ---------------------------------------------

    def create_test_pdf(self):

        pdf = pymupdf.open()

        page = pdf.new_page()

        page.insert_text(
            (72, 72),
            "Annual Revenue: 100000"
        )

        pdf_bytes = pdf.tobytes()

        pdf.close()

        return pdf_bytes

    # ---------------------------------------------
    # HELPER: CREATE A TEST DOCX
    # ---------------------------------------------

    def create_test_docx(self):

        document = Document()

        document.add_heading(
            "Employee Handbook",
            level=1
        )

        document.add_paragraph(
            "Employees receive 24 working days of annual leave."
        )

        document.add_heading(
            "Attendance Policy",
            level=2
        )

        document.add_paragraph(
            "Employees must report their attendance."
        )

        output = io.BytesIO()

        document.save(output)

        return output.getvalue()

    # ---------------------------------------------
    # TEST 1: FILE VALIDATION
    # ---------------------------------------------

    def test_valid_txt_file(self):

        result = validate_uploaded_file(
            "report.txt",
            b"Annual revenue is 100000."
        )

        self.assertEqual(result, "report.txt")

    # ---------------------------------------------
    # TEST 2: UNSUPPORTED FILE
    # ---------------------------------------------

    def test_reject_unsupported_file(self):

        with self.assertRaises(DocumentProcessingError):

            validate_uploaded_file(
                "report.exe",
                b"some content"
            )

    # ---------------------------------------------
    # TEST 3: INVALID PDF
    # ---------------------------------------------

    def test_reject_invalid_pdf(self):

        with self.assertRaises(DocumentProcessingError):

            extract_document_text(
                "report.pdf",
                b"this is not a real PDF"
            )

    # ---------------------------------------------
    # TEST 4: EMPTY FILE
    # ---------------------------------------------

    def test_reject_empty_file(self):

        with self.assertRaises(DocumentProcessingError):

            extract_document_text(
                "report.txt",
                b""
            )

    # ---------------------------------------------
    # TEST 5: PDF EXTRACTION
    # ---------------------------------------------

    def test_extract_pdf(self):

        result = extract_document_text(
            "financial_report.pdf",
            self.create_test_pdf()
        )

        self.assertIn(
            "Annual Revenue",
            result["text"]
        )

        self.assertEqual(
            result["segments"][0]["page_number"],
            1
        )

    # ---------------------------------------------
    # TEST 6: DOCX EXTRACTION
    # ---------------------------------------------

    def test_extract_docx(self):

        result = extract_document_text(
            "employee_handbook.docx",
            self.create_test_docx()
        )

        self.assertIn(
            "24 working days",
            result["text"]
        )

        self.assertIn(
            "Attendance Policy",
            result["text"]
        )

    # ---------------------------------------------
    # TEST 7: TXT EXTRACTION
    # ---------------------------------------------

    def test_extract_txt(self):

        result = extract_document_text(
            "report.txt",
            b"Annual expenses are 65000."
        )

        self.assertIn(
            "65000",
            result["text"]
        )

    # ---------------------------------------------
    # TEST 8: FILE SIZE VALIDATION
    # ---------------------------------------------

    def test_reject_oversized_file(self):

        oversized_content = b"A" * (10 * 1024 * 1024 + 1)

        with self.assertRaises(DocumentProcessingError):

            validate_uploaded_file(
                "large_report.txt",
                oversized_content
            )

    # ---------------------------------------------
    # TEST 9: SAVE DOCUMENT TO SQLITE
    # ---------------------------------------------

    def test_store_document(self):

        result = process_and_store_document(
            file_name="financial_report.txt",
            file_bytes=b"Revenue: 100000",
            uploaded_by=self.admin_id,
            access_level="public",
            db_path=self.db_path,
            upload_dir=self.upload_dir
        )

        self.assertIsInstance(
            result["document_id"],
            int
        )

        self.assertTrue(
            Path(result["storage_path"]).exists()
        )

        self.assertEqual(
            result["file_name"],
            "financial_report.txt"
        )

    # ---------------------------------------------
    # TEST 10: STORED DOCUMENT ACCESS
    # ---------------------------------------------

    def test_stored_document_access(self):

        process_and_store_document(
            file_name="financial_report.txt",
            file_bytes=b"Revenue: 100000",
            uploaded_by=self.admin_id,
            access_level="admin_only",
            db_path=self.db_path,
            upload_dir=self.upload_dir
        )

        documents = get_accessible_documents(
            self.admin_id,
            "admin",
            self.db_path
        )

        self.assertEqual(len(documents), 1)

        self.assertEqual(
            documents[0]["access_level"],
            "admin_only"
        )


if __name__ == "__main__":

    unittest.main()
