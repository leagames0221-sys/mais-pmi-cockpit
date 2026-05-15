"""Week 1 data gen test (合成 PMI cockpit data generator smoke、 seed 固定 + 件数 + 範囲 verify)。"""
from __future__ import annotations

import pytest

from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_kpi_definitions,
    generate_kpi_snapshots,
    generate_saas_licenses,
    generate_synthetic_cockpit,
    generate_vendor_contracts,
)


# ─── Test: CockpitProject 件数 + ID prefix ────────────────────────────

def test_generate_cockpit_projects_default_n5():
    projects = generate_cockpit_projects()
    assert len(projects) == 5
    for i, cp in enumerate(projects, start=1):
        assert cp.cp_id == f"CP-{i:06d}"
        assert cp.source_t3_ip_id.startswith("IP-")
        assert cp.status == "initialized"


def test_generate_cockpit_projects_custom_n():
    projects = generate_cockpit_projects(n=3)
    assert len(projects) == 3


def test_generate_cockpit_projects_seed_repeatable():
    projects_a = generate_cockpit_projects(n=5, seed=42)
    projects_b = generate_cockpit_projects(n=5, seed=42)
    for a, b in zip(projects_a, projects_b):
        assert a.industry == b.industry
        assert a.day1_anchor_date == b.day1_anchor_date


# ─── Test: KpiDefinition 4 dim per CP ────────────────────────────────

def test_generate_kpi_definitions_4_dim():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    assert len(kpi_defs) == 4
    dimensions = {kp.dimension for kp in kpi_defs}
    assert dimensions == {"cost", "revenue", "cash_gen", "working_capital"}


# ─── Test: KpiSnapshot 100 日 timeline ───────────────────────────────

def test_generate_kpi_snapshots_100_days():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    snapshots = generate_kpi_snapshots(cp, kpi_defs[0], start_n=1, days=100)
    assert len(snapshots) == 100
    # day_n = 1, 2, ..., 100
    assert snapshots[0].day_n == 1
    assert snapshots[-1].day_n == 100
    # source_type = "synthetic" 全件
    assert all(s.source_type == "synthetic" for s in snapshots)


def test_generate_kpi_snapshots_custom_days():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    kpi_defs = generate_kpi_definitions(cp, start_n=1)
    snapshots = generate_kpi_snapshots(cp, kpi_defs[0], start_n=1, days=30)
    assert len(snapshots) == 30


# ─── Test: VendorContract 件数範囲 (3-7) ──────────────────────────────

def test_generate_vendor_contracts_range():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    contracts = generate_vendor_contracts(cp, start_n=1)
    assert 3 <= len(contracts) <= 7
    for vc in contracts:
        assert vc.vendor_pseudonym.startswith("VENDOR-")
        assert vc.cp_id == cp.cp_id


# ─── Test: SaasLicense 件数範囲 (5-10) ────────────────────────────────

def test_generate_saas_licenses_range():
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    licenses = generate_saas_licenses(cp, start_n=1)
    assert 5 <= len(licenses) <= 10
    for sl in licenses:
        assert 0 <= sl.usage_pct <= 100.0
        assert sl.seat_count >= 0


# ─── Test: 全 entity integration (generate_synthetic_cockpit) ────────

def test_generate_synthetic_cockpit_full():
    outputs = generate_synthetic_cockpit(n_projects=3, days=50)
    assert len(outputs) == 3
    for o in outputs:
        # 1 CP につき 4 KPI def
        assert len(o.kpi_definitions) == 4
        # 1 CP につき 4 KPI × 50 日 = 200 snapshot
        assert len(o.kpi_snapshots) == 4 * 50
        # vendor 3-7、 SaaS 5-10
        assert 3 <= len(o.vendor_contracts) <= 7
        assert 5 <= len(o.saas_licenses) <= 10
        # Week 1 では empty
        assert o.driver_insights == []
        assert o.next_actions == []
        assert o.sentiment_events == []
        assert o.retention_risks == []


def test_generate_synthetic_cockpit_id_uniqueness():
    """CP / KP / KS / VC / SL 全 ID literal unique を verify (越境衝突防止)。"""
    outputs = generate_synthetic_cockpit(n_projects=5, days=100)
    all_cp_ids: list[str] = [o.cockpit_project.cp_id for o in outputs]
    all_kp_ids: list[str] = [kp.kp_id for o in outputs for kp in o.kpi_definitions]
    all_ks_ids: list[str] = [ks.ks_id for o in outputs for ks in o.kpi_snapshots]
    all_vc_ids: list[str] = [vc.vc_id for o in outputs for vc in o.vendor_contracts]
    all_sl_ids: list[str] = [sl.sl_id for o in outputs for sl in o.saas_licenses]
    assert len(set(all_cp_ids)) == len(all_cp_ids)
    assert len(set(all_kp_ids)) == len(all_kp_ids)
    assert len(set(all_ks_ids)) == len(all_ks_ids)
    assert len(set(all_vc_ids)) == len(all_vc_ids)
    assert len(set(all_sl_ids)) == len(all_sl_ids)
