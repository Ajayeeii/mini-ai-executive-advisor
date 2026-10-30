
import unittest
import tempfile

from pathlib import Path

from database import (
    initialize_database,
    create_user,
    get_user_by_username,
    add_document,
    grant_document_permission,
    get_accessible_documents,
    record_automation,
    get_automation_history
)


class TestDatabase(unittest.TestCase):

    def setUp(self):
        """Create a temporary database for each test."""

        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name) / "test.db"
        )

        initialize_database(self.db_path)

        self.admin_id = create_user(
            "admin",
            "example_hash_admin",
            "admin",
            self.db_path
        )

        self.user_id = create_user(
            "standard",
            "example_hash_user",
            "standard",
            self.db_path
        )

    def tearDown(self):
        """Remove temporary test database."""

        self.temp_dir.cleanup()

    def test_database_initialization(self):

        self.assertTrue(self.db_path.exists())

    def test_create_and_find_user(self):

        user = get_user_by_username(
            "admin",
            self.db_path
        )

        self.assertIsNotNone(user)

        self.assertEqual(user["role"], "admin")

    def test_add_document(self):

        document_id = add_document(
            "Employee_Handbook.pdf",
            "pdf",
            "data/sample_documents/Employee_Handbook.pdf",
            self.admin_id,
            "public",
            self.db_path
        )

        self.assertIsInstance(document_id, int)

    def test_document_permissions(self):

        public_id = add_document(
            "Public_Policy.txt",
            "txt",
            "public.txt",
            self.admin_id,
            "public",
            self.db_path
        )

        restricted_id = add_document(
            "HR_Policy.txt",
            "txt",
            "hr.txt",
            self.admin_id,
            "restricted",
            self.db_path
        )

        confidential_id = add_document(
            "Financial_Report.txt",
            "txt",
            "financial.txt",
            self.admin_id,
            "admin_only",
            self.db_path
        )

        grant_document_permission(
            restricted_id,
            self.user_id,
            self.db_path
        )

        user_documents = get_accessible_documents(
            self.user_id,
            "standard",
            self.db_path
        )

        user_document_ids = [
            doc["id"] for doc in user_documents
        ]

        self.assertIn(public_id, user_document_ids)

        self.assertIn(restricted_id, user_document_ids)

        self.assertNotIn(
            confidential_id,
            user_document_ids
        )

    def test_admin_can_access_all_documents(self):

        add_document(
            "Financial_Report.txt",
            "txt",
            "financial.txt",
            self.admin_id,
            "admin_only",
            self.db_path
        )

        documents = get_accessible_documents(
            self.admin_id,
            "admin",
            self.db_path
        )

        self.assertEqual(len(documents), 1)

    def test_automation_history(self):

        automation_id = record_automation(
            "Financial Report Summary",
            "completed",
            "Synthetic report summary",
            self.admin_id,
            self.db_path
        )

        self.assertIsInstance(automation_id, int)

        history = get_automation_history(
            self.db_path
        )

        self.assertEqual(len(history), 1)

        self.assertEqual(
            history[0]["status"],
            "completed"
        )


if __name__ == "__main__":
    unittest.main()
