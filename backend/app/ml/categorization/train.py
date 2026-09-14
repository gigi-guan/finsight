"""Offline categorization training + evaluation CLI.

Usage (from backend/ with venv active and optional ML deps installed):

    pip install -e ".[ml,dev]"
    python -m app.ml.categorization.train

Offline experiment only — not wired into the live API.
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
    GROUPED_EVAL_SEEDS,
    RANDOM_STATE,
    evaluate_pipeline_grouped_multi_seed,
    evaluate_pipeline_on_split,
    evaluate_rules,
    make_grouped_split,
    make_random_split,
    top_confusions,
)
from app.ml.categorization.features import (
    build_logreg_pipeline,
    examples_to_labels,
    examples_to_texts,
)
from app.services.transaction_normalize import CANONICAL_CATEGORIES

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
RESULTS_MD = Path(__file__).resolve().parent / "RESULTS.md"
RESULTS_JSON = Path(__file__).resolve().parent / "results_metrics.json"
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
    print(
        "\nNOTE: Rule baseline is NOT an independent benchmark — keyword rules "
        "overlap synthetic fixture vocabulary (and would overlap many demo merchants)."
    )
    print(
        "NOTE: Synthetic description text carries much of the TF-IDF signal and "
        "may not resemble noisy real bank-feed descriptors."
    )
    results["rule_baseline"] = rule_metrics
    results["evaluation_caveats"] = {
        "rule_baseline_not_independent": True,
        "synthetic_descriptions_carry_signal": True,
        "not_integrated_into_api": True,
    }

    random_split = make_random_split(examples)
    grouped_example = make_grouped_split(examples, random_state=RANDOM_STATE)
    print(
        f"\n[{dataset_name}] random split merchants overlap: "
        f"{sorted(random_split.merchants_train & random_split.merchants_test)[:5]} "
        f"(count={len(random_split.merchants_train & random_split.merchants_test)})"
    )
    print(
        f"[{dataset_name}] example grouped split (seed={RANDOM_STATE}) merchants overlap: "
        f"{sorted(grouped_example.merchants_train & grouped_example.merchants_test)} "
        f"(must be empty)"
    )

    weight_results: dict[str, Any] = {}
    for class_weight in (None, "balanced"):
        label = "none" if class_weight is None else class_weight
        weight_results[label] = {}

        pipeline = build_logreg_pipeline(class_weight=class_weight)
        random_metrics = evaluate_pipeline_on_split(
            pipeline,
            random_split,
            class_weight=class_weight,
        )
        _print_metrics(
            f"{dataset_name} / TF-IDF+LogReg / class_weight={label} / {random_split.name}",
            random_metrics,
        )
        weight_results[label][random_split.name] = random_metrics

        grouped_multi = evaluate_pipeline_grouped_multi_seed(
            examples,
            class_weight=class_weight,
            seeds=GROUPED_EVAL_SEEDS,
            build_pipeline=build_logreg_pipeline,
        )
        agg = grouped_multi["aggregate"]
        print(
            f"\n--- {dataset_name} / TF-IDF+LogReg / class_weight={label} / "
            f"merchant_grouped_multi_seed (seeds={list(GROUPED_EVAL_SEEDS)}) ---"
        )
        for key in (
            "accuracy",
            "macro_precision",
            "macro_recall",
            "macro_f1",
            "weighted_f1",
        ):
            print(f"  {key}: {agg[key]['display']}")
        weight_results[label]["merchant_grouped_multi_seed"] = grouped_multi

    results["logreg"] = weight_results

    final_pipeline = build_logreg_pipeline(class_weight="balanced")
    final_pipeline.fit(examples_to_texts(examples), examples_to_labels(examples))
    results["artifact_pipeline"] = final_pipeline
    results["artifact_class_weight"] = "balanced"
    return results


def _serializable_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_baseline": evaluation.get("rule_baseline"),
        "logreg": evaluation.get("logreg"),
        "evaluation_caveats": evaluation.get("evaluation_caveats"),
        "artifact_class_weight": evaluation.get("artifact_class_weight"),
    }


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
        "evaluation": _serializable_evaluation(evaluation),
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


def _write_committed_results(
    *,
    real_summary: dict[str, Any],
    synthetic_summary: dict[str, Any],
    synthetic_evaluation: dict[str, Any],
) -> None:
    """Write reproducible RESULTS.md + JSON (committed; .joblib stays gitignored)."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    balanced = (
        synthetic_evaluation.get("logreg", {})
        .get("balanced", {})
        .get("merchant_grouped_multi_seed", {})
    )
    random_bal = (
        synthetic_evaluation.get("logreg", {})
        .get("balanced", {})
        .get("random_stratified", {})
    )
    rule = synthetic_evaluation.get("rule_baseline", {})

    payload = {
        "generated_at_utc": stamp,
        "model_version": MODEL_VERSION,
        "not_integrated_into_api": True,
        "real_data_summary": real_summary,
        "synthetic_data_summary": synthetic_summary,
        "caveats": synthetic_evaluation.get("evaluation_caveats"),
        "synthetic_rule_baseline": {
            "accuracy": rule.get("accuracy"),
            "macro_f1": rule.get("macro_f1"),
            "note": (
                "Not an independent benchmark — rules overlap fixture vocabulary."
            ),
        },
        "synthetic_logreg_balanced": {
            "random_stratified": {
                "accuracy": random_bal.get("accuracy"),
                "macro_f1": random_bal.get("macro_f1"),
            },
            "merchant_grouped_multi_seed": balanced,
        },
        "grouped_seeds": list(GROUPED_EVAL_SEEDS),
    }
    RESULTS_JSON.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    grouped_agg = balanced.get("aggregate", {})
    lines = [
        "# Offline categorization RESULTS",
        "",
        f"Generated: `{stamp}` (UTC)",
        "",
        "**Status: offline experiment only — not integrated into the FinSight API.**",
        "",
        "## Caveats",
        "",
        "- Real trusted labels are currently insufficient for training/integration.",
        "- Synthetic fixture results are for pipeline demonstration only.",
        "- Synthetic **description** text carries much of the TF-IDF signal and may",
        "  not resemble noisy real bank-feed descriptors.",
        "- The **rule baseline is not an independent benchmark**: keyword rules",
        "  overlap the synthetic fixture vocabulary.",
        "- Prefer **merchant-grouped** metrics over random splits; random splits can",
        "  look optimistic when the same merchant appears in train and test.",
        "- Grouped metrics below are **mean ± sample std** over seeds",
        f"  `{list(GROUPED_EVAL_SEEDS)}`.",
        "",
        "## Real data",
        "",
        f"- Usable labeled rows: **{real_summary.get('total', 0)}**",
        f"- Classes: `{real_summary.get('classes', [])}`",
        "- Conclusion: **not enough data** for meaningful real-data ML evaluation.",
        "",
        "## Synthetic fixture (LogReg class_weight=balanced)",
        "",
        f"- Rows: **{synthetic_summary.get('total', 0)}**, "
        f"merchants: **{synthetic_summary.get('unique_merchants', 0)}**",
        f"- Rule baseline (full set): accuracy="
        f"{rule.get('accuracy')}, macro_f1={rule.get('macro_f1')} "
        "(not independent)",
        f"- Random stratified: accuracy={random_bal.get('accuracy')}, "
        f"macro_f1={random_bal.get('macro_f1')}",
        "- Merchant-grouped multi-seed:",
    ]
    for key in (
        "accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "weighted_f1",
    ):
        display = grouped_agg.get(key, {}).get("display", "n/a")
        lines.append(f"  - {key}: **{display}**")
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "cd backend",
            'pip install -e ".[ml,dev]"',
            "python -m app.ml.categorization.train",
            "```",
            "",
            "Heavy `.joblib` artifacts remain gitignored; this file and "
            "`results_metrics.json` are the committed evidence.",
            "",
        ]
    )
    RESULTS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote committed results: {RESULTS_MD}")
    print(f"Wrote committed metrics:  {RESULTS_JSON}")


def main() -> None:
    _print_header("FinSight offline categorization experiment")
    print("Trusted label sources:", sorted(TRUSTED_SOURCES))
    print("Excluded categories:", sorted(EXCLUDED_CATEGORIES))
    print(
        "Note: `other` is excluded because it is a heterogeneous catch-all "
        "from unsupported labels, not a coherent class."
    )
    print("Decision: do NOT integrate predictions into the production API.")

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
    _write_committed_results(
        real_summary=real_summary,
        synthetic_summary=synthetic_summary,
        synthetic_evaluation=synthetic_results,
    )

    _print_header("Done")
    print(
        "Next ML step (later): collect more user/csv labels, then re-run on real data.\n"
        "Do NOT integrate predictions into the API until real-data grouped-split "
        "metrics are trustworthy."
    )


if __name__ == "__main__":
    main()
