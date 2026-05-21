# ADR-0003: Anomaly detection on synergy KPIs — Isolation Forest + AnomSeer 2026 pattern

## Status

Accepted (2026-05-22)

## Context

The cockpit's anomaly-to-next-action loop ([README "30-second pitch"](../../README.md#30-second-pitch)) needs an anomaly detector on multi-dimensional synergy KPI time-series (cost / revenue / cash-gen / working-capital plus JP mid-market specific fields). Four constraints frame the algorithm choice:

1. **Tabular, not image / text** — KPI snapshots are numeric vectors with timestamps; the detector must handle small-N, multi-dimensional, time-series tabular data.
2. **Low-label regime** — there is no labelled "this KPI movement is an anomaly / not an anomaly" historical corpus for the PoC; the detector must be unsupervised or weakly-supervised.
3. **Interpretable to the operating partner** — a black-box deep model that flags an anomaly but cannot say *which KPI dimension drove it* defeats the [next-action recommendation](../../README.md#whats-inside) downstream consumer.
4. **Consumer-laptop runtime** — must run on a single CPU machine, no GPU, no managed service.

## Decision

A two-stage anomaly detector ([src/anomaly/](../../src/anomaly/)):

1. **scikit-learn `IsolationForest`** as the primary detector on the KPI vector. Returns an anomaly score per snapshot.
2. **AnomSeer 2026 pattern (MLLM grounding reasoning reinforcement)** layered on top: when Isolation Forest flags an anomaly, an LLM (via the [LLMProvider Protocol](0002-llm-provider-protocol-3tier-swap.md)) is asked to ground the anomaly in the KPI dimension space — "which dimension(s) drove this score, and what plausible causal hypothesis explains the movement." The LLM output is consumed by the downstream next-action recommender, not the dashboard directly.

The two stages are sequential and independently swappable behind the `LLMProvider` Protocol.

## Why Isolation Forest specifically (not OCSVM / LOF / autoencoder)

### Isolation Forest fits the regime

`IsolationForest` from scikit-learn 1.4+ ([BSD-3](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)) is unsupervised, runs in linear time, handles small-N (the PoC casebook is dozens of KPI snapshots per project), and produces a continuous anomaly score that downstream code can threshold. It is the algorithm Liu, Ting, & Zhou (2008) introduced specifically for the "low-N, multi-dimensional, unsupervised" regime — exactly this cockpit's setup.

### AnomSeer pattern adds the interpretability layer

The AnomSeer 2026 paper introduces a "MLLM grounding reasoning reinforcement" pattern for anomaly explanation: after a numeric anomaly detector fires, an LLM produces a grounded explanation tied to the input dimensions. This pattern is the *interpretability* step Isolation Forest alone does not provide. The cockpit borrows the pattern (not the code) and adapts it to KPI tabular data instead of images.

## Alternatives considered

### One-Class SVM (OCSVM) (rejected)

- **Pros**: well-established unsupervised anomaly detector; theoretically grounded.
- **Cons**: cubic training-time in the number of samples; kernel choice (RBF γ) is sensitive and needs tuning; does not produce dimension-attribution naturally.
- **Why rejected**: Isolation Forest matches or beats OCSVM on tabular benchmarks at lower compute cost; both lack interpretability, so adding AnomSeer-style grounding is needed in either case.

### Local Outlier Factor (LOF) (rejected)

- **Pros**: density-based, works on local-neighborhood anomalies.
- **Cons**: requires choosing the neighborhood-size hyperparameter `n_neighbors`, which is data-dependent; on small-N PoC casebooks the choice is fragile.
- **Why rejected**: hyperparameter sensitivity at PoC-scale N.

### Autoencoder reconstruction error (rejected)

- **Pros**: handles arbitrary feature shapes; popular in 2024+ anomaly-detection literature.
- **Cons**: requires training; no labelled corpus; PoC scale of KPI snapshots is far below what an autoencoder needs to learn a useful manifold; GPU adds compute cost.
- **Why rejected**: scale + label mismatch.

### Pure statistical control charts (Shewhart / EWMA / CUSUM) (rejected)

- **Pros**: well-understood industrial control charts; interpretable directly.
- **Cons**: assume known distribution + are univariate; the cockpit's synergy KPI is multi-dimensional with cross-dimension correlations (a healthy cost reduction with simultaneous revenue drop is an anomaly the univariate per-KPI chart cannot see).
- **Why rejected**: multi-dimensional setting.

### Pure LLM-driven anomaly classification (no statistical detector) (rejected)

- **Pros**: simplest architecture; just ask the LLM "is this KPI snapshot anomalous?"
- **Cons**: expensive (LLM call per snapshot), non-reproducible (LLM stochasticity), no probability calibration; defeats the [Selected under](../../README.md#selected-under) zero-CC default since the PoC would need a paid LLM to even score basic anomalies.
- **Why rejected**: cost + reproducibility.

## Consequences

### Positive

- Isolation Forest is cheap, deterministic, and runs on the consumer-laptop CPU without GPU.
- AnomSeer-pattern LLM grounding gives the operating partner the per-dimension attribution they need ("cost-savings dimension drove this score; the revenue dimension is also weakly anomalous"), feeding the next-action recommendation downstream.
- Both stages are swappable behind the `LLMProvider` Protocol — adding a stronger anomaly detector (e.g., XGBoost-based supervised when labels arrive at customer deployment) does not change the next-action layer.

### Negative

- AnomSeer-pattern grounding quality is bounded by the chosen LLM tier (see [ADR-0002](0002-llm-provider-protocol-3tier-swap.md)). MockProvider returns templated grounding suitable for shape demos only; Claude Sonnet at tier 3 produces deployment-grade grounding.
- Isolation Forest's score scale is not directly comparable across projects with different KPI distributions; the threshold needs per-project tuning. Acceptable since each `CockpitProject` is independent.

### Reversibility

The detector is isolated to [src/anomaly/](../../src/anomaly/) behind a fixed input contract (`KpiSnapshot` → anomaly score). Replacing Isolation Forest with a different algorithm is a single-file change. The AnomSeer-style grounding step calls the `LLMProvider` Protocol and is independent of the detector choice.

## References

- [Liu, Ting, & Zhou, "Isolation Forest" (ICDM 2008)](https://ieeexplore.ieee.org/document/4781136)
- [scikit-learn `IsolationForest` documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [AnomSeer 2026 (OpenReview)](https://openreview.net/forum?id=Jl0QHFcyCl) — MLLM grounding reasoning reinforcement pattern
- [Breunig et al., "LOF: Identifying Density-Based Local Outliers" (SIGMOD 2000)](https://dl.acm.org/doi/10.1145/342009.335388) — LOF alternative considered
- [Schölkopf et al., "Estimating the Support of a High-Dimensional Distribution" (2001)](https://direct.mit.edu/neco/article-abstract/13/7/1443/6529) — OCSVM origin
- Code: [src/anomaly/](../../src/anomaly/), [README — What's inside](../../README.md#whats-inside)
