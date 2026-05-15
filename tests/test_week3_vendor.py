"""Week 3 Vendor / SaaS overlap detect test (中堅日本企業 industry cluster + 5-stage hybrid 機能類似度)。"""
from __future__ import annotations

import pytest

from src.data_gen.generate_synthetic_cockpit import (
    generate_cockpit_projects,
    generate_saas_licenses,
    generate_vendor_contracts,
)
from src.schema.types import SaasLicense, VendorContract
from src.vendor.detect_overlap import (
    INDUSTRY_OVERLAP_CLUSTERS,
    detect_saas_overlap,
    detect_vendor_overlap,
    detect_vendor_overlap_with_5stage,
    try_docling_available,
)


def _sample_contracts() -> list[VendorContract]:
    """test fixture: 5 vendor contracts (industry mix)。"""
    return [
        VendorContract(
            vc_id=f"VC-{i:06d}",
            cp_id="CP-000001",
            vendor_pseudonym=f"VENDOR-{chr(64 + i)}",
            industry_tag=tag,
            annual_fee_band="100-500 万円",
            renewal_day="2026-12-31",
            overlap_candidate=[],
        )
        for i, tag in enumerate(["クラウド", "クラウド", "通信", "印刷", "人材"], start=1)
    ]


def _sample_licenses() -> list[SaasLicense]:
    """test fixture: 5 SaaS licenses (usage_pct mix)。"""
    licenses = []
    for i, usage in enumerate([20.0, 25.0, 80.0, 90.0, 10.0], start=1):
        licenses.append(SaasLicense(
            sl_id=f"SL-{i:06d}",
            cp_id="CP-000001",
            saas_name=f"SaaS-{chr(64 + i)}",
            seat_count=50,
            usage_pct=usage,
            annual_fee_band="100-300 万円",
            overlap_candidate=[],
        ))
    return licenses


# ─── 中堅日本企業 industry cluster pattern ────────────────────────────

def test_industry_overlap_clusters_defined():
    """ADR-305 SSoT: industry cluster literal 定義 (IT インフラ / 紙系 / 知的サービス群)。"""
    assert {"クラウド", "通信", "ソフトウェア"} in INDUSTRY_OVERLAP_CLUSTERS
    assert {"印刷", "物流"} in INDUSTRY_OVERLAP_CLUSTERS


# ─── detect_vendor_overlap ────────────────────────────────────────────

def test_detect_vendor_overlap_same_industry():
    contracts = _sample_contracts()
    updated = detect_vendor_overlap(contracts)
    # VC-000001 (クラウド) と VC-000002 (クラウド) は overlap
    vc1 = next(vc for vc in updated if vc.vc_id == "VC-000001")
    assert "VC-000002" in vc1.overlap_candidate


def test_detect_vendor_overlap_industry_cluster():
    contracts = _sample_contracts()
    updated = detect_vendor_overlap(contracts)
    # VC-000001 (クラウド) と VC-000003 (通信) は cluster overlap (IT インフラ群)
    vc1 = next(vc for vc in updated if vc.vc_id == "VC-000001")
    assert "VC-000003" in vc1.overlap_candidate


def test_detect_vendor_overlap_no_cluster():
    contracts = _sample_contracts()
    updated = detect_vendor_overlap(contracts)
    # VC-000005 (人材) と他 (クラウド / 通信 / 印刷) は cluster なし → overlap 0 件
    vc5 = next(vc for vc in updated if vc.vc_id == "VC-000005")
    assert vc5.overlap_candidate == []


# ─── detect_saas_overlap ──────────────────────────────────────────────

def test_detect_saas_overlap_low_usage_grouped():
    licenses = _sample_licenses()
    updated = detect_saas_overlap(licenses, usage_threshold=30.0)
    # SL-000001 (20%) と SL-000002 (25%) と SL-000005 (10%) は low usage
    sl1 = next(sl for sl in updated if sl.sl_id == "SL-000001")
    assert "SL-000002" in sl1.overlap_candidate
    assert "SL-000005" in sl1.overlap_candidate
    assert "SL-000001" not in sl1.overlap_candidate  # 自分自身 exclude


def test_detect_saas_overlap_high_usage_sees_low_candidates():
    licenses = _sample_licenses()
    updated = detect_saas_overlap(licenses, usage_threshold=30.0)
    # SL-000003 (80%、 high usage) は overlap_candidate に low usage 3 件 literal 持つ
    sl3 = next(sl for sl in updated if sl.sl_id == "SL-000003")
    assert set(sl3.overlap_candidate) == {"SL-000001", "SL-000002", "SL-000005"}


# ─── 5-stage hybrid integration ───────────────────────────────────────

def test_detect_vendor_overlap_with_5stage():
    contracts = _sample_contracts()
    updated = detect_vendor_overlap_with_5stage(contracts)
    # 同 industry overlap は維持 (VC-000001 vs VC-000002)
    vc1 = next(vc for vc in updated if vc.vc_id == "VC-000001")
    assert "VC-000002" in vc1.overlap_candidate


# ─── try_docling_available ────────────────────────────────────────────

def test_try_docling_available():
    """docling import 可能性 verify (Week 4 で full active 確認用)。"""
    result = try_docling_available()
    assert isinstance(result, bool)


# ─── integration with data_gen ────────────────────────────────────────

def test_detect_overlap_with_synthetic_data():
    """合成 data 経由で literal end-to-end (data_gen → detect_vendor_overlap)。"""
    projects = generate_cockpit_projects(n=1)
    cp = projects[0]
    vendors = generate_vendor_contracts(cp, start_n=1)
    licenses = generate_saas_licenses(cp, start_n=1)
    updated_vendors = detect_vendor_overlap(vendors)
    updated_licenses = detect_saas_overlap(licenses)
    # 全 input が literal 同 件数で返却
    assert len(updated_vendors) == len(vendors)
    assert len(updated_licenses) == len(licenses)
