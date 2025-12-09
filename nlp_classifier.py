"""NLP-based category classification using TF-IDF and Naive Bayes."""

import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from db import get_connection

# Training keywords for each category
CATEGORY_KEYWORDS = {
    1: ["food", "restaurant", "lunch", "dinner", "breakfast", "coffee", "meal", "eat", "cafe", "pizza", "burger"],
    2: ["transport", "taxi", "uber", "bus", "train", "metro", "subway", "gas", "fuel", "parking", "ticket"],
    3: ["entertainment", "movie", "cinema", "game", "concert", "show", "theater", "music", "netflix", "spotify"],
    4: ["other", "misc", "shopping", "store", "market", "pharmacy", "medicine", "utility", "bill"],
}


def _preprocess_text(text: str) -> str:
    """Normalize text for classification."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _build_training_data() -> tuple[list[str], list[int]]:
    """Build training dataset from keyword mappings."""
    texts = []
    labels = []
    for category_id, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            texts.append(keyword)
            labels.append(category_id)
    return texts, labels


def _train_classifier() -> Pipeline:
    """Train TF-IDF + Naive Bayes classifier."""
    texts, labels = _build_training_data()
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=100, ngram_range=(1, 2))),
            ("nb", MultinomialNB(alpha=0.1)),
        ]
    )
    pipeline.fit(texts, labels)
    return pipeline


# Global classifier instance (lazy-loaded)
_classifier: Optional[Pipeline] = None


def get_classifier() -> Pipeline:
    """Get or create the classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = _train_classifier()
    return _classifier


def predict_category(note: str, amount: Optional[float] = None) -> Optional[int]:
    """
    Predict category ID from transaction note using NLP.

    Args:
        note: Transaction note/description
        amount: Optional amount (not used currently, but can be extended)

    Returns:
        Predicted category_id or None if prediction fails
    """
    if not note or not note.strip():
        return None

    try:
        processed = _preprocess_text(note)
        if not processed:
            return None

        clf = get_classifier()
        predicted = clf.predict([processed])[0]
        return int(predicted)
    except Exception:
        return None


def train_from_user_data(user_id: int) -> bool:
    """
    Retrain classifier using user's historical transaction data.

    Args:
        user_id: User ID to fetch transactions from

    Returns:
        True if retraining succeeded, False otherwise
    """
    global _classifier

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.note, t.category_id
                FROM transactions t
                WHERE t.user_id = %s AND t.note IS NOT NULL AND t.note != ''
                ORDER BY t.tx_date DESC
                LIMIT 1000;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

        if len(rows) < 10:
            return False

        texts = [_preprocess_text(row[0]) for row in rows]
        labels = [row[1] for row in rows]

        pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(max_features=100, ngram_range=(1, 2))),
                ("nb", MultinomialNB(alpha=0.1)),
            ]
        )
        pipeline.fit(texts, labels)
        _classifier = pipeline
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()

