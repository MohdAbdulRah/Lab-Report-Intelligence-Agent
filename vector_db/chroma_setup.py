"""
chroma_setup.py — Lightweight vector store using SQLite + sentence-transformers.
Replaces ChromaDB (incompatible with Python 3.14).
Stores embeddings as JSON arrays in SQLite with cosine similarity search.
"""

import sqlite3
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

STORAGE_DIR = Path(__file__).parent.parent / "chroma_storage"
DB_PATH = STORAGE_DIR / "vector_store.db"

# Load embedding model (cached after first load)
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_db():
    """Get database connection, creating tables if needed."""
    STORAGE_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medical_reports (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            report_name TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            document TEXT NOT NULL,
            embedding TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_id ON medical_reports(user_id)
    """)
    conn.commit()
    return conn


def encode_text(text):
    """Generate embedding for text using sentence-transformers."""
    model = _get_model()
    embedding = model.encode([text])[0]
    return embedding.tolist()


def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
