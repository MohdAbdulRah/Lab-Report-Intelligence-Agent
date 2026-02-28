"""
search_reports.py — Retrieve past reports for a user using cosine similarity search.
"""

import json
from vector_db.chroma_setup import _get_db, encode_text, cosine_similarity


def get_user_reports(user_id, new_report_text, n_results=5):
    """
    Query the vector database for the most similar past reports
    belonging to this user.

    Args:
        user_id: The logged-in user's ID
        new_report_text: Text of the newly uploaded report
        n_results: Number of past reports to retrieve (default 5)

    Returns:
        List of dicts with keys: document, report_name, upload_date
        Returns empty list if no past reports found.
    """
    conn = _get_db()

    # Get all reports for this user
    cursor = conn.execute(
        "SELECT document, report_name, upload_date, embedding FROM medical_reports WHERE user_id = ?",
        (str(user_id),)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    # Compute similarity to the new report
    query_embedding = encode_text(new_report_text)

    scored = []
    for doc, name, date, emb_json in rows:
        emb = json.loads(emb_json)
        sim = cosine_similarity(query_embedding, emb)
        scored.append({
            "document": doc,
            "report_name": name,
            "upload_date": date,
            "similarity": sim
        })

    # Sort by similarity (highest first) and return top N
    scored.sort(key=lambda x: x["similarity"], reverse=True)

    return [
        {"document": s["document"], "report_name": s["report_name"], "upload_date": s["upload_date"]}
        for s in scored[:n_results]
    ]
