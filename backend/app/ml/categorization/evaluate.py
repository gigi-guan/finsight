"""Evaluation helpers for offline categorization experiments."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline

from app.ml.categorization.data import LabeledExample
from app.ml.categorization.features import (
    examples_to_groups,
    examples_to_labels,
    examples_to_texts,
)
from app.ml.categorization.rules import predict_many

RANDOM_STATE = 42
TEST_SIZE = 0.25


@dataclass
class SplitResult:
    name: str
    X_train: list[str]
    X_test: list[str]
    y_train: list[str]
    y_test: list[str]
    groups_train: list[str]
    groups_test: list[str]
    merchants_train: set[str]
    merchants_test: set[str]


def assert_no_group_leakage(groups_train: Sequence[str], groups_test: Sequence[str]) -> None:
    overlap = set(groups_train) & set(groups_test)
    if overlap:
        raise AssertionError(f"Merchant group leakage detected: {sorted(overlap)[:10]}")


def make_random_split(examples: Sequence[LabeledExample]) -> SplitResult:
    texts = examples_to_texts(examples)
    labels = examples_to_labels(examples)
    groups = examples_to_groups(examples)
    indices = np.arange(len(examples))

    # Stratify when every class has ≥2 samples; otherwise fall back.
    label_counts: dict[str, int] = defaultdict(int)
    for label in labels:
        label_counts[label] += 1
    can_stratify = all(count >= 2 for count in label_counts.values()) and len(label_counts) > 1

    train_idx, test_idx = train_test_split(
        indices,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels if can_stratify else None,
    )
    return _split_from_indices("random_stratified", examples, texts, labels, groups, train_idx, test_idx)


def make_grouped_split(examples: Sequence[LabeledExample]) -> SplitResult:
    texts = examples_to_texts(examples)
    labels = examples_to_labels(examples)
    groups = examples_to_groups(examples)
    indices = np.arange(len(examples))

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )
    train_idx, test_idx = next(splitter.split(indices, labels, groups=groups))
    split = _split_from_indices(
        "merchant_grouped",
        examples,
        texts,
        labels,
        groups,
        train_idx,
        test_idx,
    )
    assert_no_group_leakage(split.groups_train, split.groups_test)
    return split


def _split_from_indices(
    name: str,
    examples: Sequence[LabeledExample],
    texts: list[str],
    labels: list[str],
    groups: list[str],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
) -> SplitResult:
    train_idx_list = [int(i) for i in train_idx]
    test_idx_list = [int(i) for i in test_idx]
    return SplitResult(
        name=name,
        X_train=[texts[i] for i in train_idx_list],
        X_test=[texts[i] for i in test_idx_list],
        y_train=[labels[i] for i in train_idx_list],
        y_test=[labels[i] for i in test_idx_list],
        groups_train=[groups[i] for i in train_idx_list],
        groups_test=[groups[i] for i in test_idx_list],
        merchants_train={groups[i] for i in train_idx_list},
        merchants_test={groups[i] for i in test_idx_list},
    )


def compute_classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    *,
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    label_list = list(labels) if labels is not None else sorted(set(y_true) | set(y_pred))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=label_list,
        average=None,
        zero_division=0,
    )
    per_class = {
        label: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i, label in enumerate(label_list)
    }
    matrix = confusion_matrix(y_true, y_pred, labels=label_list).tolist()
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_precision": float(
            precision_recall_fscore_support(
                y_true, y_pred, average="macro", zero_division=0
            )[0]
        ),
        "macro_recall": float(
            precision_recall_fscore_support(
                y_true, y_pred, average="macro", zero_division=0
            )[1]
        ),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(
            f1_score(y_true, y_pred, average="weighted", zero_division=0)
        ),
        "per_class": per_class,
        "labels": label_list,
        "confusion_matrix": matrix,
        "classification_report": classification_report(
            y_true, y_pred, labels=label_list, zero_division=0
        ),
    }


def evaluate_rules(examples: Sequence[LabeledExample]) -> dict[str, Any]:
    merchants = [ex.merchant for ex in examples]
    descriptions = [ex.description for ex in examples]
    y_true = examples_to_labels(examples)
    y_pred = predict_many(merchants, descriptions)
    labels = sorted(set(y_true) | set(y_pred))
    metrics = compute_classification_metrics(y_true, y_pred, labels=labels)
    metrics["model"] = "rule_baseline"
    metrics["n"] = len(examples)
    return metrics


def evaluate_pipeline_on_split(
    pipeline: Pipeline,
    split: SplitResult,
    *,
    class_weight: str | None,
) -> dict[str, Any]:
    pipeline.fit(split.X_train, split.y_train)
    y_pred = pipeline.predict(split.X_test)
    labels = sorted(set(split.y_train) | set(split.y_test) | set(y_pred))
    metrics = compute_classification_metrics(split.y_test, y_pred, labels=labels)
    metrics["model"] = "tfidf_logreg"
    metrics["split"] = split.name
    metrics["class_weight"] = class_weight
    metrics["n_train"] = len(split.y_train)
    metrics["n_test"] = len(split.y_test)
    metrics["merchant_overlap"] = sorted(split.merchants_train & split.merchants_test)
    metrics["group_leakage"] = bool(metrics["merchant_overlap"])

    # Confidence bands from predict_proba
    if hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba(split.X_test)
        confidences = proba.max(axis=1)
        metrics["confidence_bands"] = _confidence_band_metrics(
            list(split.y_test), list(y_pred), confidences
        )
    return metrics


def _confidence_band_metrics(
    y_true: list[str],
    y_pred: list[str],
    confidences: np.ndarray,
) -> dict[str, Any]:
    bands = {
        "ge_0.90": confidences >= 0.90,
        "0.70_to_0.90": (confidences >= 0.70) & (confidences < 0.90),
        "lt_0.70": confidences < 0.70,
    }
    out: dict[str, Any] = {}
    for name, mask in bands.items():
        idx = np.where(mask)[0]
        if len(idx) == 0:
            out[name] = {"n": 0, "accuracy": None, "macro_f1": None}
            continue
        yt = [y_true[i] for i in idx]
        yp = [y_pred[i] for i in idx]
        out[name] = {
            "n": int(len(idx)),
            "accuracy": float(accuracy_score(yt, yp)),
            "macro_f1": float(f1_score(yt, yp, average="macro", zero_division=0)),
            "mean_confidence": float(confidences[idx].mean()),
        }
    return out


def top_confusions(metrics: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    labels = metrics["labels"]
    matrix = metrics["confusion_matrix"]
    pairs: list[dict[str, Any]] = []
    for i, true_label in enumerate(labels):
        for j, pred_label in enumerate(labels):
            if i == j:
                continue
            count = matrix[i][j]
            if count:
                pairs.append(
                    {
                        "true": true_label,
                        "predicted": pred_label,
                        "count": count,
                    }
                )
    pairs.sort(key=lambda item: item["count"], reverse=True)
    return pairs[:limit]
