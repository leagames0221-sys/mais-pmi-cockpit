"""Week 1 schema layer smoke test。"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.schema.types import (
    CockpitProject,
    DriverInsight,
    KpiDefinition,
    KpiSnapshot,
    NextAction,
    NextActionCandidate,
    RetentionRisk,
    SaasLicense,
    SentimentEvent,
    T4Output,
    VendorContract,
)


# ─── 1. CockpitProject ──────────────────────────────────────────────────

def test_cockpit_project_valid():
    cp = CockpitProject(
        cp_id="CP-000001",
        source_t3_ip_id="IP-000000001",
        industry="製造業",
        size_band="従業員 100-300 名",
        day1_anchor_date="2026-09-01",
        day100_end_date="2026-12-10",
        status="monitoring",
        generated_at=datetime(2026, 5, 13, 15, 0, 0, tzinfo=timezone.utc),
    )
    assert cp.cp_id == "CP-000001"
    assert cp.source_t3_ip_id == "IP-000000001"
    assert cp.status == "monitoring"


def test_cockpit_project_invalid_cp_id():
    with pytest.raises(ValidationError):
        CockpitProject(
            cp_id="INVALID",
            source_t3_ip_id="IP-000000001",
            industry="製造業",
            size_band="従業員 100-300 名",
            day1_anchor_date="2026-09-01",
            day100_end_date="2026-12-10",
            status="monitoring",
            generated_at=datetime.now(timezone.utc),
        )


def test_cockpit_project_invalid_status():
    with pytest.raises(ValidationError):
        CockpitProject(
            cp_id="CP-000001",
            source_t3_ip_id="IP-000000001",
            industry="製造業",
            size_band="従業員 100-300 名",
            day1_anchor_date="2026-09-01",
            day100_end_date="2026-12-10",
            status="invalid_state",
            generated_at=datetime.now(timezone.utc),
        )


# ─── 2. KpiDefinition ───────────────────────────────────────────────────

def test_kpi_definition_valid():
    kp = KpiDefinition(
        kp_id="KP-000001",
        cp_id="CP-000001",
        name="営業 cash flow",
        dimension="cash_gen",
        unit="千万円",
        target=50.0,
        benchmark_band="中堅 PMI 平均 ±15%",
        frequency="weekly",
    )
    assert kp.dimension == "cash_gen"
    assert kp.target == 50.0


def test_kpi_definition_invalid_dimension():
    with pytest.raises(ValidationError):
        KpiDefinition(
            kp_id="KP-000001",
            cp_id="CP-000001",
            name="営業 cash flow",
            dimension="invalid_dim",
            unit="千万円",
            target=50.0,
            frequency="weekly",
        )


# ─── 3. KpiSnapshot ─────────────────────────────────────────────────────

def test_kpi_snapshot_valid():
    ks = KpiSnapshot(
        ks_id="KS-000001",
        kp_id="KP-000001",
        observed_at=datetime(2026, 9, 8, 0, 0, 0, tzinfo=timezone.utc),
        day_n=7,
        value=42.3,
        source_type="synthetic",
    )
    assert ks.day_n == 7
    assert ks.source_type == "synthetic"


def test_kpi_snapshot_day_n_out_of_range():
    with pytest.raises(ValidationError):
        KpiSnapshot(
            ks_id="KS-000001",
            kp_id="KP-000001",
            observed_at=datetime.now(timezone.utc),
            day_n=101, # > 100
            value=42.3,
            source_type="synthetic",
        )


# ─── 4. DriverInsight ───────────────────────────────────────────────────

def test_driver_insight_valid():
    dr = DriverInsight(
        dr_id="DR-000001",
        cp_id="CP-000001",
        ks_id_ref="KS-000001",
        statement_redacted="売掛回収遅延が 30 日 → 45 日に拡大",
        driver_factors=["AR_aging", "trade_term_change"],
        citation_array=["CIT-000123", "CIT-000124"],
        confidence=0.87,
    )
    assert dr.confidence == 0.87
    assert len(dr.driver_factors) == 2


def test_driver_insight_invalid_confidence():
    with pytest.raises(ValidationError):
        DriverInsight(
            dr_id="DR-000001",
            cp_id="CP-000001",
            ks_id_ref="KS-000001",
            statement_redacted="(redacted)",
            driver_factors=[],
            citation_array=[],
            confidence=1.5, # > 1.0
        )


# ─── 5. NextAction ──────────────────────────────────────────────────────

def test_next_action_valid():
    na = NextAction(
        na_id="NA-000001",
        cp_id="CP-000001",
        dr_id_ref="DR-000001",
        action_statement_redacted="支払サイト変更要望の取引先 3 社と週内に再交渉",
        audience_mapping="CK-000003",
        priority_rank=1,
        due_day_n=14,
        status="proposed",
        candidates_ranked=[
            NextActionCandidate(rank=1, action="交渉", expected_impact="高"),
            NextActionCandidate(rank=2, action="fund 確保", expected_impact="中"),
            NextActionCandidate(rank=3, action="在庫削減", expected_impact="中"),
        ],
    )
    assert na.priority_rank == 1
    assert len(na.candidates_ranked) == 3


def test_next_action_invalid_audience_mapping():
    with pytest.raises(ValidationError):
        NextAction(
            na_id="NA-000001",
            cp_id="CP-000001",
            dr_id_ref="DR-000001",
            action_statement_redacted="(redacted)",
            audience_mapping="INVALID-XX", # CK-XXXXXX pattern 違反
            priority_rank=1,
            due_day_n=14,
            status="proposed",
            candidates_ranked=[],
        )


# ─── 6. SentimentEvent ──────────────────────────────────────────────────

def test_sentiment_event_valid():
    se = SentimentEvent(
        se_id="SE-000001",
        cp_id="CP-000001",
        source_channel="slack",
        observed_at=datetime(2026, 9, 15, 10, 30, 0, tzinfo=timezone.utc),
        sentiment_score=-0.42,
        topic_tag=["人事制度変更", "不安"],
        excerpt_redacted="(redacted, organization 軸)",
    )
    assert se.source_channel == "slack"
    assert se.sentiment_score == -0.42


def test_sentiment_event_score_out_of_range():
    with pytest.raises(ValidationError):
        SentimentEvent(
            se_id="SE-000001",
            cp_id="CP-000001",
            source_channel="slack",
            observed_at=datetime.now(timezone.utc),
            sentiment_score=2.0, # > 1.0
            topic_tag=[],
            excerpt_redacted="",
        )


# ─── 7. VendorContract ──────────────────────────────────────────────────

def test_vendor_contract_valid():
    vc = VendorContract(
        vc_id="VC-000001",
        cp_id="CP-000001",
        vendor_pseudonym="VENDOR-A",
        industry_tag="クラウド",
        annual_fee_band="1,000-3,000 万円",
        renewal_day="2026-12-31",
        overlap_candidate=["VC-000002", "VC-000005"],
    )
    assert vc.vendor_pseudonym == "VENDOR-A"
    assert len(vc.overlap_candidate) == 2


# ─── 8. SaasLicense ─────────────────────────────────────────────────────

def test_saas_license_valid():
    sl = SaasLicense(
        sl_id="SL-000001",
        cp_id="CP-000001",
        saas_name="SaaS-Y",
        seat_count=50,
        usage_pct=30.0,
        annual_fee_band="100-300 万円",
        overlap_candidate=["SL-000003"],
    )
    assert sl.seat_count == 50
    assert sl.usage_pct == 30.0


def test_saas_license_usage_pct_out_of_range():
    with pytest.raises(ValidationError):
        SaasLicense(
            sl_id="SL-000001",
            cp_id="CP-000001",
            saas_name="SaaS-Y",
            seat_count=50,
            usage_pct=150.0, # > 100
            annual_fee_band="100-300 万円",
        )


# ─── 9. RetentionRisk ───────────────────────────────────────────────────

def test_retention_risk_valid():
    rt = RetentionRisk(
        rt_id="RT-000001",
        cp_id="CP-000001",
        score=67,
        dimension="organization",
        triggered_jp_patterns=["JPD1-000001"],
        se_id_refs=["SE-000001", "SE-000005"],
        mitigation_recommendation_redacted="(redacted summary)",
    )
    assert rt.score == 67
    assert rt.dimension == "organization"
    assert len(rt.triggered_jp_patterns) == 1


def test_retention_risk_score_out_of_range():
    with pytest.raises(ValidationError):
        RetentionRisk(
            rt_id="RT-000001",
            cp_id="CP-000001",
            score=101, # > 100
            dimension="organization",
            mitigation_recommendation_redacted="",
        )


# ─── 10. T4Output container ────────────────────────────────────────────

def test_t4_output_container_empty_lists():
    """T4Output container = empty lists でも valid (Week 1 schema layer の minimal init)。"""
    output = T4Output(
        cockpit_project=CockpitProject(
            cp_id="CP-000001",
            source_t3_ip_id="IP-000000001",
            industry="製造業",
            size_band="従業員 100-300 名",
            day1_anchor_date="2026-09-01",
            day100_end_date="2026-12-10",
            status="initialized",
            generated_at=datetime.now(timezone.utc),
        ),
        kpi_definitions=[],
        kpi_snapshots=[],
        driver_insights=[],
        next_actions=[],
        sentiment_events=[],
        vendor_contracts=[],
        saas_licenses=[],
        retention_risks=[],
    )
    assert output.cockpit_project.cp_id == "CP-000001"
    assert output.kpi_definitions == []
    assert output.retention_risks == []
