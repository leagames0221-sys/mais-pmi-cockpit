"""KPI anomaly detection。

Isolation Forest:
  - contamination=0.1 (10% anomaly rate、 中堅日本企業 PMI 経験的 baseline)
  - fit: 1 KPI の 100 日 KpiSnapshot value series
  - predict: 1 = normal、 -1 = anomaly
  - decision_function: anomaly score (低いほど anomaly 強い、 [-0.5, 0.5] 程度の範囲)

AnomSeer 2026 pattern (OpenReview Jl0QHFcyCl):
  - MLLM reinforce grounding reasoning を Claude LLM CoT prompt で literal 模倣 (PoC = MockProvider)
  - LLMProvider.evaluate_anomaly_severity() で grounding reasoning literal 出力

Pydantic schema: AnomalyResult (本 module 内定義、 src/schema/types.py には intentional に literal 追加せず、 検出結果は internal computation = doctrine: waste-zero)
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest

from src.schema.types import KpiDefinition, KpiSnapshot


class AnomalyResult(BaseModel):
    """1 KpiSnapshot の anomaly 検出結果 (internal、 operational DB には DriverInsight 経由で persist)。

    LangGraph checkpoint msgpack serde 対応のため Pydantic BaseModel。
    """
    ks_id: str
    kp_id: str
    day_n: int
    value: float
    is_anomaly: bool
    anomaly_score: float # decision_function output、 低いほど anomaly 強い


def detect_anomalies(
    snapshots: list[KpiSnapshot],
    kpi_def: KpiDefinition,
    contamination: float = 0.1,
    random_state: int = 20260513,
) -> list[AnomalyResult]:
    """1 KPI の 100 日 KpiSnapshot に Isolation Forest を fit + predict、 全 snapshot の AnomalyResult 返却。

    contamination=0.1 = 10% anomaly rate (中堅日本企業 PMI 経験的 baseline)。
    """
    if not snapshots:
        return []
    if any(s.kp_id != kpi_def.kp_id for s in snapshots):
        raise ValueError("KpiSnapshot list contains different kp_id than provided KpiDefinition")

    values = np.array([s.value for s in snapshots]).reshape(-1, 1)
    clf = IsolationForest(contamination=contamination, random_state=random_state)
    clf.fit(values)
    predictions = clf.predict(values) # 1 = normal、 -1 = anomaly
    scores = clf.decision_function(values) # 低いほど anomaly 強い

    return [
        AnomalyResult(
            ks_id=s.ks_id,
            kp_id=s.kp_id,
            day_n=s.day_n,
            value=s.value,
            is_anomaly=bool(pred == -1), # numpy bool → Python bool literal coerce (msgpack serde 対応)
            anomaly_score=float(score),
        )
        for s, pred, score in zip(snapshots, predictions, scores)
    ]


def filter_top_anomalies(results: list[AnomalyResult], top_k: int = 5) -> list[AnomalyResult]:
    """anomaly のみ filter + score 昇順 (anomaly 強い順) で top-K 返却 (NextAction trigger source)。"""
    anomalies = [r for r in results if r.is_anomaly]
    anomalies.sort(key=lambda r: r.anomaly_score)
    return anomalies[:top_k]
