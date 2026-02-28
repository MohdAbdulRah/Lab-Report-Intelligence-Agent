"""
store_report.py — Store extracted report text in the vector database.
"""

import uuid
from datetime import datetime
from vector_db.chroma_setup import _get_db, encode_text
import json


def store_report(user_id, report_text, report_name):
    """
    Store a medical report in the vector database.

    Args:
        user_id: The logged-in user's ID (int or str)
        report_text: Full extracted text from the PDF
        report_name: Original filename of the uploaded PDF

    Returns:
        report_id: The unique ID assigned to this report
    """
    conn = _get_db()

    report_id = f"report_{user_id}_{uuid.uuid4().hex[:12]}"
    upload_date = datetime.now().strftime("%Y-%m-%d")

    # Generate embedding
    embedding = encode_text(report_text)

    conn.execute(
        "INSERT INTO medical_reports (id, user_id, report_name, upload_date, document, embedding) VALUES (?, ?, ?, ?, ?, ?)",
        (report_id, str(user_id), report_name, upload_date, report_text, json.dumps(embedding))
    )
    conn.commit()
    conn.close()

    return report_id
