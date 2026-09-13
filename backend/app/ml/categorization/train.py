"""Offline categorization training + evaluation CLI.

Usage (from backend/ with venv active):

    python -m app.ml.categorization.train
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.ml.categorization.data import (
    EXCLUDED_CATEGORIES,
    TRUSTED_SOURCES,
    has_sufficient_data,
    load_real_examples,
    load_synthetic_examples,
    summarize_examples,
)
from app.ml.categorization.evaluate import (
    evaluate_pipeline_on_split,
    evaluate_rules,
    make_grouped_split,
    make_random_split,
    top_confusions,
)
from app.ml.categorization.features import build_logreg_pipeline
from app.services.transaction_normalize import CANONICAL_CATEGORIES

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_VERSION = "categorization-tfidf-logreg-v1"


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _print_summary(name: str, summary: dict[str, Any]) -> None:
    print(f"\n[{name}] total={summary['total']}  unique_merchants={summary['unique_merchants']}")
    print(f"[{name}] classes={summary['classes']}")
    print(f"[{name}] by_category={summary['by_category']}")
    print(f"[{name}] merchants_per_category={summary['merchants_per_category']}")


def _print_metrics(title: str, metrics: dict[str, Any]) -> None:
    print(f"\n--- {title} ---")
    for key in (
        "accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "weighted_f1",
        "n",
        "n_train",
        "n_test",
        "class_weight",
        "split",
        "group_leakage",
        "merchant_overlap",
    ):
        if key in metrics:
            print(f"  {key}: {metrics[key]}")
    if "per_class" in metrics:
        print("  per_class:")
        for label, vals in metrics["per_class"].items():
            print(
                f"    {label}: P={vals['precision']:.3f} R={vals['recall']:.3f} "
                f"F1={vals['f1']:.3f} support={vals['support']}"
            )
    if "confidence_bands" in metrics:
        print("  confidence_bands:")
        for band, vals in metrics["confidence_bands"].items():
            print(f"    {band}: {vals}")
    confusions = top_confusions(metrics)
    if confusions:
        print("  top_confusions:")
        for item in confusions:
            print(
                f"    true={item['true']} predicted={item['predicted']} count={item['count']}"
            )


def _run_model_suite(examples, *, dataset_name: str) -> dict[str, Any]:
    results: dict[str, Any] = {"dataset": dataset_name}

    rule_metrics = evaluate_rules(examples)
    _print_metrics(f"{dataset_name} / rule baseline (full set)", rule_metrics)
    results["rule_baseline"] = rule_metrics

    random_split = make_random_split(examples)
    grouped_split = make_grouped_split(examples)
    print(
        f"\n[{dataset_name}] random split merchants overlap: "
        f"{sorted(random_split.merchants_train & random_split.merchants_test)[:5]} "
        f"(count={len(random_split.merchants_train & random_split.merchants_test)})"
    )
    print(
        f"[{dataset_name}] grouped split merchants overlap: "
        f"{sorted(grouped_split.merchants_train & grouped_split.merchants_test)} "
        f"(must be empty)"
    )

    weight_results: dict[str, Any] = {}
    for class_weight in (None, "balanced"):
        label = "none" if class_weight is None else class_weight
        weight_results[label] = {}
        for split in (random_split, grouped_split):
            pipeline = build_logreg_pipeline(class_weight=class_weight)
            metrics = evaluate_pipeline_on_split(
                pipeline,
                split,
                class_weight=class_weight,
            )
            _print_metrics(
                f"{dataset_name} / TF-IDF+LogReg / class_weight={label} / {split.name}",
                metrics,
            )
            weight_results[label][split.name] = metrics

    results["logreg"] = weight_results

    # Prefer balanced + full-data fit for the saved synthetic artifact:
    # macro metrics matter more than majority-class accuracy for categorization.
    from app.ml.categorization.features import examples_to_labels, examples_to_texts

    final_pipeline = build_logreg_pipeline(class_weight="balanced")
    final_pipeline.fit(examples_to_texts(examples), examples_to_labels(examples))
    results["artifact_pipeline"] = final_pipeline
    results["artifact_class_weight"] = "balanced"
    return results


def _save_artifact(
    *,
    pipeline,
    dataset_name: str,
    summary: dict[str, Any],
    evaluation: dict[str, Any],
    class_weight: str,
) -> Path:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_path = ARTIFACTS_DIR / f"{MODEL_VERSION}-{dataset_name}-{stamp}.joblib"
    meta_path = ARTIFACTS_DIR / f"{MODEL_VERSION}-{dataset_name}-{stamp}.meta.json"

    joblib.dump(pipeline, model_path)

    # Drop non-serializable pipeline from nested evaluation before writing JSON.
    serializable_eval = {
        "rule_baseline": evaluation.get("rule_baseline"),
        "logreg": evaluation.get("logreg"),
        "artifact_class_weight": class_weight,
    }
    metadata = {
        "model_version": MODEL_VERSION,
        "trained_at_utc": stamp,
        "dataset": dataset_name,
        "taxonomy": sorted(CANONICAL_CATEGORIES),
        "trusted_sources": sorted(TRUSTED_SOURCES),
        "excluded_categories": sorted(EXCLUDED_CATEGORIES),
        "features": {
            "fields": ["merchant", "description"],
            "vectorizer": "TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)",
            "classifier": "LogisticRegression",
            "class_weight": class_weight,
        },
        "data_summary": summary,
        "evaluation": serializable_eval,
        "artifact_path": str(model_path.name),
        "note": (
            "Offline experiment only. Not wired into the live API. "
            "Do not overwrite transaction.category with these predictions."
        ),
    }
    meta_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved model artifact: {model_path}")
    print(f"Saved metadata:       {meta_path}")
    return model_path


def main() -> None:
    _print_header("FinSight offline categorization experiment")
    print("Trusted label sources:", sorted(TRUSTED_SOURCES))
    print("Excluded categories:", sorted(EXCLUDED_CATEGORIES))
    print(
        "Note: `other` is excluded because it is a heterogeneous catch-all "
        "from unsupported labels, not a coherent class."
    )

    # --- Real DB labels ---
    _print_header("REAL database labels")
    real_examples = load_real_examples()
    real_summary = summarize_examples(real_examples)
    _print_summary("real", real_summary)

    if not has_sufficient_data(real_summary):
        print(
            "\nCONCLUSION (real data): NOT ENOUGH DATA for meaningful ML evaluation.\n"
            f"Need >=30 usable rows, >=3 classes, >=2 merchants/class.\n"
            f"Have total={real_summary['total']}, classes={len(real_summary['classes'])}, "
            f"merchants_per_category={real_summary['merchants_per_category']}.\n"
            "Skipping real-data model training to avoid fabricating strong results.\n"
            "Will run the full experiment on a SEPARATE synthetic fixture instead."
        )
        if real_examples:
            # Still show rule baseline on whatever trusted rows exist (honest, tiny).
            _print_metrics(
                "real / rule baseline (tiny set — illustrative only)",
                evaluate_rules(real_examples),
            )
    else:
        real_results = _run_model_suite(real_examples, dataset_name="real")
        _save_artifact(
            pipeline=real_results["artifact_pipeline"],
            dataset_name="real",
            summary=real_summary,
            evaluation=real_results,
            class_weight=real_results["artifact_class_weight"],
        )

    # --- Synthetic fixture (clearly separated) ---
    _print_header("SYNTHETIC fixture (development only — not mixed with real eval)")
    synthetic_examples = load_synthetic_examples()
    synthetic_summary = summarize_examples(synthetic_examples)
    _print_summary("synthetic", synthetic_summary)

    if not has_sufficient_data(synthetic_summary):
        raise SystemExit("Synthetic fixture is unexpectedly too small.")

    synthetic_results = _run_model_suite(synthetic_examples, dataset_name="synthetic")
    _save_artifact(
        pipeline=synthetic_results["artifact_pipeline"],
        dataset_name="synthetic",
        summary=synthetic_summary,
        evaluation=synthetic_results,
        class_weight=synthetic_results["artifact_class_weight"],
    )

    _print_header("Done")
    print(
        "Next ML step (later): collect more user/csv labels, then re-run on real data.\n"
        "Do NOT integrate predictions into the API until real-data grouped-split "
        "metrics are trustworthy."
    )


if __name__ == "__main__":
    main()
