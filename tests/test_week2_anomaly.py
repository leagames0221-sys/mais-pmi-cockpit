"""Week 2 anomaly detection test (Isolation Forest + threshold + AnomalyResult schema verify)。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.anomaly.detect_isolation_forest import (
    AnomalyResult,
    detect_anomalies,
    filter_top_anomalies,
)
from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_kpi_definitions,
    generate_kpi_snapshots,
)


def _setup_kpi_with_snapshots(days: int = 100):
    """1 CP × 4 KPI × N 日 snapshot literal 生成 (test fixture)。"""
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    cash_gen_kp = next(kp for kp in kpi_defs if kp.dimension == "cash_gen")
    snapshots = generate_kpi_snapshots(cp, cash_gen_kp, start_n=1, days=days)
    return cash_gen_kp, snapshots


def test_detect_anomalies_returns_one_result_per_snapshot():
    kp, snapshots = _setup_kpi_with_snapshots(days=100)
    results = detect_anomalies(snapshots, kp)
    assert len(results) == len(snapshots)


def test_detect_anomalies_contamination_10pct_yields_anomalies():
    """contamination=0.1 で 100 件 snapshot → 約 10% (10 件前後) anomaly literal 検出。"""
    kp, snapshots = _setup_kpi_with_snapshots(days=100)
    results = detect_anomalies(snapshots, kp)
    anomalies = [r for r in results if r.is_anomaly]
    # 10% contamination = 10 件 ± 5 件範囲 (random walk + Isolation Forest 経験的 tolerance)
    assert 5 <= len(anomalies) <= 15


def test_detect_anomalies_empty_input():
    kp, _ = _setup_kpi_with_snapshots()
    results = detect_anomalies([], kp)
    assert results == []


def test_detect_anomalies_kp_id_mismatch_raises():
    kp, snapshots = _setup_kpi_with_snapshots()
    # 別 kp_id を持つ snapshot で fit attempt → ValueError
    projects = generate_cockpit_projects(n=2)
    other_kp = generate_kpi_definitions(projects[1], start_n=10)[0]
    with pytest.raises(ValueError):
        detect_anomalies(snapshots, other_kp)


def test_filter_top_anomalies_returns_top_k():
    kp, snapshots = _setup_kpi_with_snapshots(days=100)
    results = detect_anomalies(snapshots, kp)
    top = filter_top_anomalies(results, top_k=5)
    # top-K = 5 件以下
    assert len(top) <= 5
    # 全件 is_anomaly = True
    assert all(r.is_anomaly for r in top)
    # anomaly_score 昇順 (anomaly 強い順)
    scores = [r.anomaly_score for r in top]
    assert scores == sorted(scores)


def test_filter_top_anomalies_fewer_than_k():
    """anomaly が k 未満の時、 存在する anomaly 全件 返却。"""
    # mock results with only 2 anomalies
    results = [
        AnomalyResult(ks_id="KS-000001", kp_id="KP-000001", day_n=1, value=10.0, is_anomaly=False, anomaly_score=0.1),
        AnomalyResult(ks_id="KS-000002", kp_id="KP-000001", day_n=2, value=11.0, is_anomaly=True, anomaly_score=-0.3),
        AnomalyResult(ks_id="KS-000003", kp_id="KP-000001", day_n=3, value=9.0, is_anomaly=True, anomaly_score=-0.5),
    ]
    top = filter_top_anomalies(results, top_k=5)
    assert len(top) == 2
    # score 昇順
    assert top[0].anomaly_score < top[1].anomaly_score
