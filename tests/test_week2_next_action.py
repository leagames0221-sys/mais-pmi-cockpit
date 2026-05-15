"""Week 2 NextAction recommender test (Claude LLM listwise CoT + 5 候補 ranked + T3 CK audience mapping)。"""
from __future__ import annotations

import pytest

from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_kpi_definitions,
)
from src.llm.provider import MockProvider
from src.next_action.recommend import (
    _due_day_n,
    _mock_ck_id_for_dim,
    batch_recommend_with_kpi_map,
    recommend_next_action,
)
from src.schema.types import DriverInsight


def _make_driver_insight(cp_id: str, dr_id: str, ks_id_ref: str, dimension: str) -> DriverInsight:
    """test fixture: DriverInsight literal 構築。"""
    return DriverInsight(
        dr_id=dr_id,
        cp_id=cp_id,
        ks_id_ref=ks_id_ref,
        statement_redacted=f"[{dimension}] anomaly detected",
        driver_factors=["test_factor"],
        citation_array=["CIT-000001"],
        confidence=0.8,
    )


def _setup():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    return cp, kpi_defs


# ─── _mock_ck_id_for_dim helper ────────────────────────────────────────

def test_mock_ck_id_for_dim_default():
    assert _mock_ck_id_for_dim("cost") == "CK-000001"
    assert _mock_ck_id_for_dim("revenue") == "CK-000002"
    assert _mock_ck_id_for_dim("cash_gen") == "CK-000003"
    assert _mock_ck_id_for_dim("working_capital") == "CK-000004"


def test_mock_ck_id_for_dim_unknown_default_to_cost():
    """未定義 dimension は default = CK-000001 (cost) に literal fallback。"""
    assert _mock_ck_id_for_dim("unknown") == "CK-000001"


# ─── _due_day_n helper ─────────────────────────────────────────────────

def test_due_day_n_cash_gen_short_buffer():
    """cash_gen / retention は 7 日 buffer (高 urgency)。"""
    assert _due_day_n(current_day_n=10, dimension="cash_gen") == 17
    assert _due_day_n(current_day_n=10, dimension="retention") == 17


def test_due_day_n_clip_to_100():
    """due_day_n は max 100 に literal clip。"""
    assert _due_day_n(current_day_n=95, dimension="cost") == 100 # 95 + 14 → 100 clip


def test_due_day_n_default_14_days():
    assert _due_day_n(current_day_n=20, dimension="cost") == 34


# ─── recommend_next_action ─────────────────────────────────────────────

def test_recommend_next_action_5_candidates():
    cp, kpi_defs = _setup()
    kp = next(kp for kp in kpi_defs if kp.dimension == "cash_gen")
    dr = _make_driver_insight(cp.cp_id, "DR-000001", "KS-000010", "cash_gen")
    na = recommend_next_action(
        driver_insight=dr,
        kpi_def=kp,
        current_day_n=10,
        na_seq=1,
        priority_rank=1,
        provider=MockProvider(),
    )
    assert na.na_id == "NA-000001"
    assert len(na.candidates_ranked) == 5
    assert na.priority_rank == 1
    assert na.status == "proposed"
    # audience_mapping = cash_gen → CK-000003
    assert na.audience_mapping == "CK-000003"
    # due_day_n = 10 + 7 (cash_gen high urgency) = 17
    assert na.due_day_n == 17


def test_recommend_next_action_pii_redaction():
    """NextAction action_statement に PII (取引先名 / 担当者氏名) literal 混入禁止。"""
    cp, kpi_defs = _setup()
    kp = kpi_defs[0]
    dr = _make_driver_insight(cp.cp_id, "DR-000001", "KS-000001", kp.dimension)
    na = recommend_next_action(driver_insight=dr, kpi_def=kp, current_day_n=1, na_seq=1, priority_rank=1, provider=MockProvider())
    forbidden_pii = ["@", "電話", "様", "氏", "邸"]
    for pii in forbidden_pii:
        assert pii not in na.action_statement_redacted


def test_recommend_next_action_rank_priority_clip():
    """priority_rank は 1-5 範囲 literal 強制 (Pydantic schema validation)。"""
    cp, kpi_defs = _setup()
    kp = kpi_defs[0]
    dr = _make_driver_insight(cp.cp_id, "DR-000001", "KS-000001", kp.dimension)
    # priority_rank=6 → Pydantic validation error
    with pytest.raises(Exception):
        recommend_next_action(driver_insight=dr, kpi_def=kp, current_day_n=1, na_seq=1, priority_rank=6, provider=MockProvider())


# ─── batch_recommend_with_kpi_map ──────────────────────────────────────

def test_batch_recommend_with_kpi_map_full():
    cp, kpi_defs = _setup()
    pairs = [
        (_make_driver_insight(cp.cp_id, "DR-000001", "KS-000001", kpi_defs[0].dimension), kpi_defs[0], 5),
        (_make_driver_insight(cp.cp_id, "DR-000002", "KS-000002", kpi_defs[1].dimension), kpi_defs[1], 10),
        (_make_driver_insight(cp.cp_id, "DR-000003", "KS-000003", kpi_defs[2].dimension), kpi_defs[2], 30),
    ]
    actions = batch_recommend_with_kpi_map(pairs=pairs, start_seq=1, provider=MockProvider())
    assert len(actions) == 3
    for i, na in enumerate(actions, start=1):
        assert na.na_id == f"NA-{i:06d}"
        assert na.priority_rank == i
        assert len(na.candidates_ranked) == 5
