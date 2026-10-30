
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import DATABASE_PATH, get_accessible_documents
from document_processor import extract_document_text


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

DEFAULT_CHUNK_SIZE = 150
DEFAULT_OVERLAP = 30

DEFAULT_TOP_K = 5
DEFAULT_MIN_SCORE = 0.05


# --------------------------------------------------
# CUSTOM ERROR
# --------------------------------------------------

class DocumentRetrievalError(Exception):
    """Raised when document retrieval cannot be completed."""
    pass


# --------------------------------------------------
# DOCUMENT CHUNKING
# --------------------------------------------------

def chunk_document(
    segments,
    document_id,
    file_name,
    chunk_size=DEFAULT_CHUNK_SIZE,
    overlap=DEFAULT_OVERLAP
):
    """
    Splits extracted document segments into smaller chunks.

    Preserves document IDs, filenames, page numbers
    and section headings.
    """

    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Overlap must be non-negative and smaller than chunk size."
        )

    chunks = []
    chunk_index = 0

    for segment_index, segment in enumerate(segments):

        text = segment.get("text", "").strip()

        if not text:
            continue

        words = text.split()

        start = 0

        while start < len(words):

            end = min(start + chunk_size, len(words))

            chunk_text = " ".join(words[start:end])

            chunks.append({
                "document_id": document_id,
                "file_name": file_name,
                "chunk_index": chunk_index,
                "segment_index": segment_index,
                "page_number": segment.get("page_number"),
                "section": segment.get("section"),
                "text": chunk_text
            })

            chunk_index += 1

            if end == len(words):
                break

            start = end - overlap

    return chunks


# --------------------------------------------------
# BUILD CHUNKS FROM PERMITTED DOCUMENTS
# --------------------------------------------------

def build_document_chunks(
    documents,
    chunk_size=DEFAULT_CHUNK_SIZE,
    overlap=DEFAULT_OVERLAP
):
    """
    Reads and extracts only the documents supplied
    by the permission-filtered database query.
    """

    all_chunks = []

    for document in documents:

        storage_path = Path(document["storage_path"])

        if not storage_path.is_file():
            raise DocumentRetrievalError(
                f"Stored document is missing: {document['file_name']}"
            )

        try:
            file_bytes = storage_path.read_bytes()

            extracted_document = extract_document_text(
                document["file_name"],
                file_bytes
            )

        except Exception as error:

            raise DocumentRetrievalError(
                f"Could not process {document['file_name']}: {error}"
            ) from error

        document_chunks = chunk_document(
            segments=extracted_document["segments"],
            document_id=document["id"],
            file_name=document["file_name"],
            chunk_size=chunk_size,
            overlap=overlap
        )

        all_chunks.extend(document_chunks)

    return all_chunks


# --------------------------------------------------
# TF-IDF RETRIEVAL
# --------------------------------------------------

def retrieve_relevant_passages(
    question,
    chunks,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE
):
    """
    Searches document chunks using TF-IDF and
    cosine similarity.

    Returns the highest-scoring relevant passages.
    """

    if not isinstance(question, str) or not question.strip():
        return []

    if not chunks:
        return []

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    if min_score < 0 or min_score > 1:
        raise ValueError("min_score must be between 0 and 1.")

    document_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    try:

        vectorizer = TfidfVectorizer()

        document_vectors = vectorizer.fit_transform(
            document_texts
        )

        question_vector = vectorizer.transform([
            question
        ])

        similarity_scores = cosine_similarity(
            question_vector,
            document_vectors
        ).flatten()

    except ValueError:
        # Handles empty documents or text with no usable vocabulary.
        return []

    ranked_results = []

    for index, score in enumerate(similarity_scores):

        if score >= min_score:

            result = chunks[index].copy()

            result["similarity_score"] = float(score)

            ranked_results.append(result)

    ranked_results.sort(
        key=lambda item: item["similarity_score"],
        reverse=True
    )

    return ranked_results[:top_k]


# --------------------------------------------------
# MAIN DOCUMENT SEARCH FUNCTION
# --------------------------------------------------

def search_documents(
    user_id,
    role,
    question,
    db_path=DATABASE_PATH,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE
):
    """
    Searches only documents the authenticated user
    is authorised to access.

    IMPORTANT:
    Permissions are checked BEFORE document files
    are opened, extracted, chunked or searched.
    """

    if not isinstance(question, str) or not question.strip():
        return []

    # STEP 1: Retrieve permitted document metadata.
    accessible_documents = get_accessible_documents(
        user_id=user_id,
        role=role,
        db_path=db_path
    )

    # STEP 2: Load and chunk only permitted documents.
    document_chunks = build_document_chunks(
        accessible_documents
    )

    # STEP 3: Retrieve relevant passages.
    results = retrieve_relevant_passages(
        question=question,
        chunks=document_chunks,
        top_k=top_k,
        min_score=min_score
    )

    return results
