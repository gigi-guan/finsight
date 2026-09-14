# Offline categorization RESULTS

Generated: `2026-09-14T00:07:28Z` (UTC)

**Status: offline experiment only — not integrated into the FinSight API.**

## Caveats

- Real trusted labels are currently insufficient for training/integration.
- Synthetic fixture results are for pipeline demonstration only.
- Synthetic **description** text carries much of the TF-IDF signal and may
  not resemble noisy real bank-feed descriptors.
- The **rule baseline is not an independent benchmark**: keyword rules
  overlap the synthetic fixture vocabulary.
- Prefer **merchant-grouped** metrics over random splits; random splits can
  look optimistic when the same merchant appears in train and test.
- Grouped metrics below are **mean ± sample std** over seeds
  `[42, 7, 11, 19, 23]`.

## Real data

- Usable labeled rows: **3**
- Classes: `['dining', 'groceries']`
- Conclusion: **not enough data** for meaningful real-data ML evaluation.

## Synthetic fixture (LogReg class_weight=balanced)

- Rows: **130**, merchants: **110**
- Rule baseline (full set): accuracy=0.8, macro_f1=0.7925566551424673 (not independent)
- Random stratified: accuracy=0.6363636363636364, macro_f1=0.6235209235209235
- Merchant-grouped multi-seed:
  - accuracy: **0.517 ± 0.141**
  - macro_precision: **0.511 ± 0.073**
  - macro_recall: **0.474 ± 0.107**
  - macro_f1: **0.442 ± 0.103**
  - weighted_f1: **0.535 ± 0.154**

## Reproduction

```bash
cd backend
pip install -e ".[ml,dev]"
python -m app.ml.categorization.train
```

Heavy `.joblib` artifacts remain gitignored; this file and `results_metrics.json` are the committed evidence.
