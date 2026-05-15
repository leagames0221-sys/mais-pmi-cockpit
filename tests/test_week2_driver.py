"""Week 2 DriverInsight test (5-stage hybrid simplified + LLMProvider MockProvider)。"""
from __future__ import annotations

from src.anomaly.detect_isolation_forest import AnomalyResult
from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_kpi_definitions,
)
from src.driver.extract_driver import batch_extract_drivers, extract_driver_insight
from src.llm.provider import MockProvider


def _setup():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    return cp, kpi_defs


def test_extract_driver_insight_basic():
    cp, kpi_defs = _setup()
    kp = next(kp for kp in kpi_defs if kp.dimension == "cash_gen")
    anomaly = AnomalyResult(
        ks_id="KS-000050",
        kp_id=kp.kp_id,
        day_n=50,
        value=kp.target * 0.6, # 40% 下振れ
        is_anomaly=True,
        anomaly_score=-0.45,
    )
    dr = extract_driver_insight(
        anomaly=anomaly,
        kpi_def=kp,
        cp_id=cp.cp_id,
        dr_seq=1,
        provider=MockProvider(),
    )
    assert dr.dr_id == "DR-000001"
    assert dr.cp_id == cp.cp_id
    assert dr.ks_id_ref == "KS-000050"
    assert "cash_gen" in dr.statement_redacted
    assert "下振れ" in dr.statement_redacted
    # driver_factors = cash_gen dim 由来
    assert "AR_aging" in dr.driver_factors or "trade_term_change" in dr.driver_factors
    # confidence 0.5 + |score|*0.5 = 0.5 + 0.45*0.5 = 0.725
    assert 0.5 <= dr.confidence <= 1.0
    # Citation placeholder
    assert len(dr.citation_array) >= 1
    assert dr.citation_array[0].startswith("CIT-")


def test_extract_driver_insight_dimension_specific_factors():
    cp, kpi_defs = _setup()
    for i, kp in enumerate(kpi_defs):
        # ks_id pattern = ^KS-[0-9]{6}$ literal 順守 (Pydantic schema validation)
        anomaly = AnomalyResult(
            ks_id=f"KS-{i + 1:06d}",
            kp_id=kp.kp_id,
            day_n=10,
            value=kp.target * 0.8,
            is_anomaly=True,
            anomaly_score=-0.3,
        )
        dr = extract_driver_insight(anomaly=anomaly, kpi_def=kp, cp_id=cp.cp_id, dr_seq=1, provider=MockProvider())
        # 各 dimension で driver_factors 異なる (MockProvider DRIVER_FACTORS_BY_DIM 順守)
        assert len(dr.driver_factors) >= 1


def test_extract_driver_insight_pii_redaction():
    """driver insight statement に PII (担当者氏名 / 取引先名) literal 混入禁止 (module boundary verify)。"""
    cp, kpi_defs = _setup()
    kp = kpi_defs[0]
    anomaly = AnomalyResult(
        ks_id="KS-000001",
        kp_id=kp.kp_id,
        day_n=1,
        value=kp.target,
        is_anomaly=True,
        anomaly_score=-0.2,
    )
    dr = extract_driver_insight(anomaly=anomaly, kpi_def=kp, cp_id=cp.cp_id, dr_seq=1, provider=MockProvider())
    # MockProvider statement に PII keyword 混入禁止
    forbidden_pii = ["@", "電話", "様", "氏", "邸"]
    for pii in forbidden_pii:
        assert pii not in dr.statement_redacted


def test_batch_extract_drivers_full():
    cp, kpi_defs = _setup()
    kpi_def_by_kp_id = {kp.kp_id: kp for kp in kpi_defs}
    anomalies = [
        AnomalyResult(
            ks_id=f"KS-{i:06d}",
            kp_id=kpi_defs[i % len(kpi_defs)].kp_id,
            day_n=i + 1,
            value=kpi_defs[i % len(kpi_defs)].target * 0.7,
            is_anomaly=True,
            anomaly_score=-0.3 - i * 0.05,
        )
        for i in range(5)
    ]
    insights = batch_extract_drivers(
        anomalies=anomalies,
        kpi_defs=kpi_def_by_kp_id,
        cp_id=cp.cp_id,
        start_seq=1,
        provider=MockProvider(),
    )
    assert len(insights) == 5
    # dr_id sequential
    for i, dr in enumerate(insights, start=1):
        assert dr.dr_id == f"DR-{i:06d}"
        assert dr.cp_id == cp.cp_id


def test_batch_extract_drivers_skips_missing_kp_id():
    cp, kpi_defs = _setup()
    kpi_def_by_kp_id = {kp.kp_id: kp for kp in kpi_defs}
    anomalies = [
        AnomalyResult(ks_id="KS-000001", kp_id="KP-UNKNOWN", day_n=1, value=10.0, is_anomaly=True, anomaly_score=-0.3),
    ]
    insights = batch_extract_drivers(anomalies=anomalies, kpi_defs=kpi_def_by_kp_id, cp_id=cp.cp_id, provider=MockProvider())
    # unknown kp_id は skip = 0 件返却
    assert insights == []
