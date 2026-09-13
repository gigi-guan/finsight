"""Focused tests for offline categorization data/split/rules/pipeline."""

from __future__ import annotations

import pytest
from sklearn.pipeline import Pipeline

from app.ml.categorization.data import (
    LabeledExample,
    filter_labeled_rows,
    is_trusted_label,
    merchant_group_key,
)
from app.ml.categorization.evaluate import assert_no_group_leakage, make_grouped_split
from app.ml.categorization.features import build_logreg_pipeline, build_text_feature
from app.ml.categorization.rules import predict_category


def test_is_trusted_label_filters_sources_and_categories() -> None:
    assert is_trusted_label("user", "groceries") is True
    assert is_trusted_label("csv", "dining") is True
    assert is_trusted_label("model", "groceries") is False
    assert is_trusted_label("rules", "groceries") is False
    assert is_trusted_label("unknown", "groceries") is False
    assert is_trusted_label("user", "uncategorized") is False
    assert is_trusted_label("csv", "other") is False


def test_filter_labeled_rows_excludes_untrusted() -> None:
    rows = [
        {
            "merchant": "Whole Foods",
            "description": "food",
            "category": "groceries",
            "category_source": "user",
        },
        {
            "merchant": "X",
            "description": "y",
            "category": "groceries",
            "category_source": "model",
        },
        {
            "merchant": "Y",
            "description": "z",
            "category": "uncategorized",
            "category_source": "user",
        },
        {
            "merchant": "Z",
            "description": "q",
            "category": "other",
            "category_source": "csv",
        },
    ]
    examples = filter_labeled_rows(rows, origin="real")
    assert len(examples) == 1
    assert examples[0].merchant == "Whole Foods"
    assert examples[0].merchant_group == merchant_group_key("Whole Foods")


def test_merchant_group_normalization() -> None:
    assert merchant_group_key("  Whole   Foods ") == merchant_group_key("whole foods")
    assert build_text_feature("Uber", "Airport ride").startswith("uber")


def test_rule_baseline_is_deterministic() -> None:
    a = predict_category("Whole Foods Market", "Weekly groceries")
    b = predict_category("Whole Foods Market", "Weekly groceries")
    assert a == b
    assert a.category == "groceries"
    assert predict_category("Uber Trip", "Ride downtown").category == "transportation"
    assert predict_category("Spotify", "Music premium plan").category == "subscriptions"
    assert predict_category("Unknown Merchant XYZ", "misc").category == "uncategorized"


def test_grouped_split_has_no_merchant_leakage() -> None:
    examples = [
        LabeledExample("Whole Foods", "a", "groceries", "user", merchant_group_key("Whole Foods"), "synthetic"),
        LabeledExample("Safeway", "b", "groceries", "csv", merchant_group_key("Safeway"), "synthetic"),
        LabeledExample("Uber", "c", "transportation", "user", merchant_group_key("Uber"), "synthetic"),
        LabeledExample("Lyft", "d", "transportation", "csv", merchant_group_key("Lyft"), "synthetic"),
        LabeledExample("Netflix", "e", "subscriptions", "user", merchant_group_key("Netflix"), "synthetic"),
        LabeledExample("Spotify", "f", "subscriptions", "csv", merchant_group_key("Spotify"), "synthetic"),
        LabeledExample("Target", "g", "shopping", "user", merchant_group_key("Target"), "synthetic"),
        LabeledExample("Walmart", "h", "shopping", "csv", merchant_group_key("Walmart"), "synthetic"),
    ]
    split = make_grouped_split(examples)
    assert_no_group_leakage(split.groups_train, split.groups_test)
    assert split.merchants_train.isdisjoint(split.merchants_test)


def test_assert_no_group_leakage_raises() -> None:
    with pytest.raises(AssertionError, match="leakage"):
        assert_no_group_leakage(["uber", "lyft"], ["uber", "shell"])


def test_pipeline_fits_and_predicts_tiny_fixture() -> None:
    texts = [
        "whole foods weekly groceries",
        "safeway produce and milk",
        "uber ride to airport",
        "lyft shared ride downtown",
        "netflix streaming subscription",
        "spotify music premium plan",
    ]
    labels = [
        "groceries",
        "groceries",
        "transportation",
        "transportation",
        "subscriptions",
        "subscriptions",
    ]
    pipeline = build_logreg_pipeline(class_weight="balanced")
    assert isinstance(pipeline, Pipeline)
    pipeline.fit(texts, labels)
    pred = pipeline.predict(["trader joe organic food haul"])
    assert pred[0] in {"groceries", "transportation", "subscriptions"}
    proba = pipeline.predict_proba(["trader joe organic food haul"])
    assert proba.shape[1] == 3
    assert abs(float(proba.sum(axis=1)[0]) - 1.0) < 1e-6
