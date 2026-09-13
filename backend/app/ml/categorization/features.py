"""Feature construction for transaction categorization (does not mutate DB text)."""

from __future__ import annotations

from typing import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.ml.categorization.data import LabeledExample
from app.services.transaction_normalize import normalize_merchant


def build_text_feature(merchant: str, description: str) -> str:
    """Combine merchant + description into one text document for TF-IDF.

    Uses normalize_merchant for stable token form; description is lightly cleaned
    for features only — persisted DB strings are never overwritten.
    """
    merchant_part = normalize_merchant(merchant)
    description_part = " ".join(description.strip().split()).casefold()
    return f"{merchant_part} {description_part}".strip()


def examples_to_texts(examples: Sequence[LabeledExample]) -> list[str]:
    return [build_text_feature(ex.merchant, ex.description) for ex in examples]


def examples_to_labels(examples: Sequence[LabeledExample]) -> list[str]:
    return [ex.category for ex in examples]


def examples_to_groups(examples: Sequence[LabeledExample]) -> list[str]:
    return [ex.merchant_group for ex in examples]


def build_logreg_pipeline(*, class_weight: str | None) -> Pipeline:
    """TF-IDF + multinomial Logistic Regression as a single coupled Pipeline."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    sublinear_tf=True,
                ),
            ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight=class_weight,
                        random_state=42,
                        solver="lbfgs",
                    ),
                ),
        ]
    )
