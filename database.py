
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = BASE_DIR / "data" / "advisor.db"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

@contextmanager
def get_connection(db_path=DATABASE_PATH):
    """
    Opens a database connection.

    Commits changes when successful.
    Rolls back changes if an error occurs.
    Always closes the connection.
    """

    db_path = Path(db_path)

    # Create the database directory if necessary.
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)

    # Return database rows as dictionary-like objects.
    connection.row_factory = sqlite3.Row

    # Enable foreign key validation.
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database(db_path=DATABASE_PATH):
    """
    Creates all database tables if they do not exist.
    Safe to run multiple times.
    """

    with get_connection(db_path) as connection:

        connection.executescript("""

            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                role TEXT NOT NULL
                    CHECK(role IN ('admin', 'standard')),

                created_at TEXT NOT NULL

            );


            CREATE TABLE IF NOT EXISTS documents (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                file_name TEXT NOT NULL,

                file_type TEXT NOT NULL,

                storage_path TEXT NOT NULL,

                uploaded_by INTEGER NOT NULL,

                access_level TEXT NOT NULL
                    CHECK(access_level IN (
                        'public',
                        'restricted',
                        'admin_only'
                    )),

                created_at TEXT NOT NULL,

                FOREIGN KEY(uploaded_by)
                    REFERENCES users(id)

            );


            CREATE TABLE IF NOT EXISTS document_permissions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                document_id INTEGER NOT NULL,

                user_id INTEGER NOT NULL,

                permission TEXT NOT NULL DEFAULT 'read'
                    CHECK(permission IN ('read')),

                granted_at TEXT NOT NULL,

                UNIQUE(document_id, user_id),

                FOREIGN KEY(document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE,

                FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            );


            CREATE TABLE IF NOT EXISTS automation_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                automation_type TEXT NOT NULL,

                status TEXT NOT NULL
                    CHECK(status IN (
                        'pending',
                        'completed',
                        'failed'
                    )),

                summary TEXT,

                user_id INTEGER,

                created_at TEXT NOT NULL,

                FOREIGN KEY(user_id)
                    REFERENCES users(id)
                    ON DELETE SET NULL

            );


            CREATE INDEX IF NOT EXISTS idx_documents_uploader
            ON documents(uploaded_by);


            CREATE INDEX IF NOT EXISTS idx_permissions_user
            ON document_permissions(user_id);


            CREATE INDEX IF NOT EXISTS idx_automation_created
            ON automation_history(created_at);

        """)


# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------

def current_timestamp():
    """Returns the current UTC timestamp."""

    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    )


# --------------------------------------------------
# USER DATABASE FUNCTIONS
# --------------------------------------------------

def create_user(username, password_hash, role, db_path=DATABASE_PATH):
    """
    Creates a user account.

    Passwords must already be securely hashed
    before being passed to this function.
    """

    if role not in ("admin", "standard"):
        raise ValueError("Invalid user role.")

    with get_connection(db_path) as connection:

        cursor = connection.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                role,
                current_timestamp()
            )
        )

        return cursor.lastrowid


def get_user_by_username(username, db_path=DATABASE_PATH):
    """Finds a user by username."""

    with get_connection(db_path) as connection:

        result = connection.execute(
            """
            SELECT id, username, password_hash, role, created_at
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        return dict(result) if result else None


# --------------------------------------------------
# DOCUMENT DATABASE FUNCTIONS
# --------------------------------------------------

def add_document(
    file_name,
    file_type,
    storage_path,
    uploaded_by,
    access_level="public",
    db_path=DATABASE_PATH
):
    """Stores document metadata."""

    if access_level not in (
        "public",
        "restricted",
        "admin_only"
    ):
        raise ValueError("Invalid document access level.")

    with get_connection(db_path) as connection:

        cursor = connection.execute(
            """
            INSERT INTO documents (
                file_name,
                file_type,
                storage_path,
                uploaded_by,
                access_level,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_name,
                file_type,
                storage_path,
                uploaded_by,
                access_level,
                current_timestamp()
            )
        )

        return cursor.lastrowid


def grant_document_permission(
    document_id,
    user_id,
    db_path=DATABASE_PATH
):
    """Grants a standard user read access to a document."""

    with get_connection(db_path) as connection:

        connection.execute(
            """
            INSERT INTO document_permissions (
                document_id,
                user_id,
                permission,
                granted_at
            )
            VALUES (?, ?, 'read', ?)

            ON CONFLICT(document_id, user_id)
            DO UPDATE SET
                permission = 'read',
                granted_at = excluded.granted_at
            """,
            (
                document_id,
                user_id,
                current_timestamp()
            )
        )


def get_accessible_documents(
    user_id,
    role,
    db_path=DATABASE_PATH
):
    """
    Retrieves only documents the user is permitted to access.

    Administrators can access all documents.

    Standard users can access:
    - Public documents.
    - Restricted documents explicitly assigned to them.

    Administrator-only documents remain inaccessible
    to standard users.
    """

    with get_connection(db_path) as connection:

        if role == "admin":

            results = connection.execute(
                """
                SELECT *
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()

        elif role == "standard":

            results = connection.execute(
                """
                SELECT d.*
                FROM documents d

                WHERE d.access_level = 'public'

                OR (
                    d.access_level = 'restricted'

                    AND EXISTS (
                        SELECT 1
                        FROM document_permissions p

                        WHERE p.document_id = d.id
                        AND p.user_id = ?
                        AND p.permission = 'read'
                    )
                )

                ORDER BY d.created_at DESC
                """,
                (user_id,)
            ).fetchall()

        else:
            raise ValueError("Invalid user role.")

        return [dict(row) for row in results]


# --------------------------------------------------
# AUTOMATION HISTORY FUNCTIONS
# --------------------------------------------------

def record_automation(
    automation_type,
    status,
    summary=None,
    user_id=None,
    db_path=DATABASE_PATH
):
    """
    Records an automation execution.

    Returns the database record ID after commit.
    """

    if status not in ("pending", "completed", "failed"):
        raise ValueError("Invalid automation status.")

    with get_connection(db_path) as connection:

        cursor = connection.execute(
            """
            INSERT INTO automation_history (
                automation_type,
                status,
                summary,
                user_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                automation_type,
                status,
                summary,
                user_id,
                current_timestamp()
            )
        )

        return cursor.lastrowid


def get_automation_history(db_path=DATABASE_PATH):
    """Returns automation records, newest first."""

    with get_connection(db_path) as connection:

        results = connection.execute(
            """
            SELECT *
            FROM automation_history
            ORDER BY created_at DESC
            """
        ).fetchall()

        return [dict(row) for row in results]


# --------------------------------------------------
# INITIALIZATION WHEN RUN DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":

    initialize_database()

    print("Database initialized successfully!")

    print(f"Database location: {DATABASE_PATH}")
