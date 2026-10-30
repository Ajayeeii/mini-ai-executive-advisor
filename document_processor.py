
import io
import uuid
import zipfile

from pathlib import Path

import pymupdf
from docx import Document

from database import DATABASE_PATH, add_document


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "data" / "uploads"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}


# --------------------------------------------------
# CUSTOM ERROR
# --------------------------------------------------

class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed safely."""
    pass


# --------------------------------------------------
# FILE VALIDATION
# --------------------------------------------------

def validate_uploaded_file(file_name, file_bytes):
    """
    Validates filename, extension, size and basic file format.

    Returns the safe original filename.
    """

    if not isinstance(file_name, str) or not file_name.strip():
        raise DocumentProcessingError("Invalid filename.")

    if not isinstance(file_bytes, bytes):
        raise DocumentProcessingError("File content must be bytes.")

    # Remove any directory components from the filename.
    safe_name = file_name.replace("\\", "/").rsplit("/", 1)[-1]

    if safe_name in ("", ".", ".."):
        raise DocumentProcessingError("Invalid filename.")

    extension = Path(safe_name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentProcessingError(
            "Unsupported file type. Upload PDF, DOCX or TXT."
        )

    if not file_bytes:
        raise DocumentProcessingError("The uploaded file is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise DocumentProcessingError(
            "File exceeds the maximum size of 10 MB."
        )

    # Check the actual PDF signature.
    if extension == ".pdf":

        if not file_bytes.startswith(b"%PDF-"):
            raise DocumentProcessingError(
                "Invalid PDF file. File signature not recognised."
            )

    # Check the DOCX ZIP package structure.
    elif extension == ".docx":

        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:

                required_files = archive.namelist()

                if (
                    "[Content_Types].xml" not in required_files
                    or "word/document.xml" not in required_files
                ):
                    raise DocumentProcessingError(
                        "Invalid DOCX document structure."
                    )

        except (zipfile.BadZipFile, OSError):
            raise DocumentProcessingError(
                "The uploaded DOCX file is corrupted."
            )

    # Reject obvious binary content in TXT files.
    elif extension == ".txt":

        if b"\x00" in file_bytes:
            raise DocumentProcessingError(
                "TXT file contains invalid binary content."
            )

    return safe_name


# --------------------------------------------------
# PDF EXTRACTION
# --------------------------------------------------

def extract_pdf_text(file_bytes):
    """
    Extracts text from each PDF page.

    Preserves actual PDF page numbers.
    """

    extracted_segments = []

    try:

        with pymupdf.open(
            stream=file_bytes,
            filetype="pdf"
        ) as pdf_document:

            if pdf_document.is_encrypted:
                raise DocumentProcessingError(
                    "Password-protected PDFs are not supported."
                )

            for page_number, page in enumerate(
                pdf_document,
                start=1
            ):

                page_text = page.get_text("text").strip()

                if page_text:

                    extracted_segments.append({
                        "page_number": page_number,
                        "section": None,
                        "text": page_text
                    })

    except DocumentProcessingError:
        raise

    except Exception as error:

        raise DocumentProcessingError(
            f"Could not read PDF document: {error}"
        ) from error

    if not extracted_segments:
        raise DocumentProcessingError(
            "No extractable text found in PDF. "
            "The document may be scanned or empty. "
            "OCR is not implemented in this prototype."
        )

    return extracted_segments


# --------------------------------------------------
# WORD DOCUMENT EXTRACTION
# --------------------------------------------------

def extract_docx_text(file_bytes):
    """
    Extracts paragraphs and tables from a Word document.

    Preserves heading names as section references.
    DOCX page numbers are not reliably available.
    """

    extracted_segments = []

    current_heading = "Document body"

    try:

        word_document = Document(
            io.BytesIO(file_bytes)
        )

        # Extract paragraphs.
        for paragraph in word_document.paragraphs:

            paragraph_text = paragraph.text.strip()

            if not paragraph_text:
                continue

            style_name = paragraph.style.name

            if style_name.startswith("Heading"):

                current_heading = paragraph_text

            extracted_segments.append({
                "page_number": None,
                "section": current_heading,
                "text": paragraph_text
            })

        # Extract tables.
        for table_number, table in enumerate(
            word_document.tables,
            start=1
        ):

            table_rows = []

            for row in table.rows:

                cells = [
                    cell.text.strip()
                    for cell in row.cells
                ]

                table_rows.append(" | ".join(cells))

            table_text = "\n".join(table_rows).strip()

            if table_text:

                extracted_segments.append({
                    "page_number": None,
                    "section": f"Table {table_number}",
                    "text": table_text
                })

    except Exception as error:

        raise DocumentProcessingError(
            f"Could not read Word document: {error}"
        ) from error

    if not extracted_segments:
        raise DocumentProcessingError(
            "No extractable text found in Word document."
        )

    return extracted_segments


# --------------------------------------------------
# TEXT FILE EXTRACTION
# --------------------------------------------------

def extract_txt_text(file_bytes):
    """
    Extracts text from a TXT file.

    Supports UTF-8 and Windows-1252 encoding.
    """

    try:

        try:
            extracted_text = file_bytes.decode("utf-8-sig")

        except UnicodeDecodeError:
            extracted_text = file_bytes.decode("cp1252")

    except UnicodeDecodeError as error:

        raise DocumentProcessingError(
            "Could not decode the TXT file."
        ) from error

    if not extracted_text.strip():
        raise DocumentProcessingError(
            "TXT file contains no readable text."
        )

    # Reject excessive non-printable control characters.
    invalid_characters = sum(
        1 for character in extracted_text
        if ord(character) < 32
        and character not in "\n\r\t\f"
    )

    if invalid_characters / max(len(extracted_text), 1) > 0.05:
        raise DocumentProcessingError(
            "TXT file contains invalid binary content."
        )

    return [{
        "page_number": None,
        "section": None,
        "text": extracted_text.strip()
    }]


# --------------------------------------------------
# GENERAL DOCUMENT EXTRACTION
# --------------------------------------------------

def extract_document_text(file_name, file_bytes):
    """
    Validates and extracts an uploaded document.

    Returns filename, file type, full text and segments.
    """

    safe_name = validate_uploaded_file(
        file_name,
        file_bytes
    )

    extension = Path(safe_name).suffix.lower()

    if extension == ".pdf":

        segments = extract_pdf_text(file_bytes)

    elif extension == ".docx":

        segments = extract_docx_text(file_bytes)

    elif extension == ".txt":

        segments = extract_txt_text(file_bytes)

    else:
        raise DocumentProcessingError(
            "Unsupported document format."
        )

    full_text = "\n\n".join(
        segment["text"]
        for segment in segments
    )

    return {
        "file_name": safe_name,
        "file_type": extension.lstrip("."),
        "text": full_text,
        "segments": segments
    }


# --------------------------------------------------
# SAVE DOCUMENT AND STORE METADATA
# --------------------------------------------------

def process_and_store_document(
    file_name,
    file_bytes,
    uploaded_by,
    access_level="public",
    db_path=DATABASE_PATH,
    upload_dir=UPLOAD_DIR
):
    """
    Validates and extracts a document.

    Saves the original file to disk and records
    its metadata in SQLite.

    If database insertion fails, removes the
    newly saved file.
    """

    # Extract before saving anything permanently.
    extracted_document = extract_document_text(
        file_name,
        file_bytes
    )

    safe_name = extracted_document["file_name"]

    extension = Path(safe_name).suffix.lower()

    # Generate a unique stored filename.
    unique_name = f"{uuid.uuid4().hex}{extension}"

    destination_dir = Path(upload_dir)

    destination_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    destination_path = destination_dir / unique_name

    # Save the original document.
    destination_path.write_bytes(file_bytes)

    try:

        # Store metadata in SQLite.
        document_id = add_document(
            file_name=safe_name,
            file_type=extracted_document["file_type"],
            storage_path=str(destination_path.resolve()),
            uploaded_by=uploaded_by,
            access_level=access_level,
            db_path=db_path
        )

    except Exception:

        # Prevent orphan files if database insertion fails.
        destination_path.unlink(missing_ok=True)

        raise

    return {
        "document_id": document_id,
        "file_name": safe_name,
        "file_type": extracted_document["file_type"],
        "storage_path": str(destination_path.resolve()),
        "text": extracted_document["text"],
        "segments": extracted_document["segments"]
    }


# --------------------------------------------------
# RUN MODULE DIRECTLY
# --------------------------------------------------

if __name__ == "__main__":

    print("Document Processor is ready.")

    print("Supported formats: PDF, DOCX, TXT")

    print(f"Maximum file size: {MAX_FILE_SIZE // (1024 * 1024)} MB")
