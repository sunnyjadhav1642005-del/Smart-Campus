
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database import get_connection


# Similarity threshold: 45%
SIMILARITY_THRESHOLD = 0.45


def normalize_text(text):
    """Convert text into a consistent format."""
    if not text:
        return ""

    return " ".join(str(text).lower().strip().split())


def find_duplicate(title, description, location):
    """
    Find the most similar existing complaint.

    Returns a dictionary if a possible duplicate is found.
    Otherwise, returns None.
    """

    new_text = normalize_text(f"{title} {description}")
    new_location = normalize_text(location)

    if not new_text:
        return None

    connection = get_connection()

    try:
        complaints = connection.execute("""
            SELECT id, title, description, location, status
            FROM complaints
            WHERE status != 'Resolved'
            ORDER BY id DESC
        """).fetchall()
    finally:
        connection.close()

    if not complaints:
        return None

    # Compare the new complaint with existing complaints.
    existing_texts = [
        normalize_text(
            f"{complaint['title']} {complaint['description']}"
        )
        for complaint in complaints
    ]

    all_texts = existing_texts + [new_text]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        strip_accents="unicode"
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(all_texts)
    except ValueError:
        # For example, when every text is empty.
        return None

    new_vector = tfidf_matrix[-1]
    existing_vectors = tfidf_matrix[:-1]

    similarity_scores = cosine_similarity(
        new_vector,
        existing_vectors
    )[0]

    best_match = None
    best_score = 0.0

    for index, score in enumerate(similarity_scores):
        complaint = complaints[index]
        old_location = normalize_text(complaint["location"])

        # Require the same location to reduce unrelated matches.
        if new_location != old_location:
            continue

        if score > best_score:
            best_score = float(score)
            best_match = complaint

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        return {
            "id": best_match["id"],
            "title": best_match["title"],
            "location": best_match["location"],
            "status": best_match["status"],
            "similarity": round(best_score * 100, 2)
        }

    return None
