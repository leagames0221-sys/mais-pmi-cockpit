"""合成 PMI cockpit data generator (Faker + 業種テンプレ、 CP N 案件 × KPI 4 dim × 100 日 timeline)。

scope (ADR-300 順守):
  - 合成 PMI cockpit data only、 実 KPI / 実 vendor / 実 SaaS / 実 sentiment 一切扱わない
  - seed 固定で再現性確保 (SYNTHETIC_SEED 環境変数、 doctrine: verify-priority 順守)

生成 entity (Week 1 minimal):
  - CockpitProject × N (default 5)
  - KpiDefinition × 4 dim per CP (cost / revenue / cash_gen / working_capital)
  - KpiSnapshot × 100 日 timeline per KPI (Faker random walk + dimension-specific 中堅日本企業 KPI benchmark)
  - VendorContract × random 3-7 per CP (vendor_pseudonym + industry_tag + annual_fee_band)
  - SaasLicense × random 5-10 per CP (saas_name + seat_count + usage_pct)

Week 3 で literal 追加 (本 module 未実装):
  - SentimentEvent (HF Transformers + Claude pipeline 統合後)
  - DriverInsight (5-stage hybrid 統合後)
  - NextAction (Claude LLM listwise rerank 統合後)
  - RetentionRisk (JPDay1Pattern trigger 経由は integration module 側で生成済)
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

from src.schema.types import (
    CockpitProject,
    KpiDefinition,
    KpiSnapshot,
    SaasLicense,
    T4Output,
    VendorContract,
)


# ─── 業種テンプレ + KPI benchmark (中堅日本企業特化、 ADR-301 順守) ────

INDUSTRIES = [
    {"industry": "製造業", "size_band": "従業員 100-300 名", "cost_baseline": 100.0, "revenue_baseline": 50.0},
    {"industry": "小売", "size_band": "従業員 50-100 名", "cost_baseline": 80.0, "revenue_baseline": 120.0},
    {"industry": "サービス業", "size_band": "従業員 30-80 名", "cost_baseline": 60.0, "revenue_baseline": 70.0},
    {"industry": "卸売", "size_band": "従業員 80-200 名", "cost_baseline": 90.0, "revenue_baseline": 150.0},
    {"industry": "出版", "size_band": "従業員 30-50 名", "cost_baseline": 40.0, "revenue_baseline": 45.0},
]

VENDOR_INDUSTRY_TAGS = ["クラウド", "印刷", "物流", "人材", "通信", "コンサル", "ソフトウェア"]
SAAS_NAMES = ["SaaS-A", "SaaS-B", "SaaS-C", "SaaS-D", "SaaS-E", "SaaS-F", "SaaS-G", "SaaS-H", "SaaS-I", "SaaS-J"]


# ─── ID generator (integration module と同 pattern) ────────────────────

def _seq_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n:06d}"


# ─── 合成 data gen entry (re-export for test) ─────────────────────────

def get_seed() -> int:
    """SYNTHETIC_SEED 環境変数 read、 default 20260513。"""
    return int(os.environ.get("SYNTHETIC_SEED", "20260513"))


def generate_cockpit_projects(n: int = 5, seed: int | None = None) -> list[CockpitProject]:
    """合成 CockpitProject N 件生成 (default 5)、 IP-XXXXXXXXX → CP-XXXXXX inherit。"""
    if seed is None:
        seed = get_seed()
    rng = random.Random(seed)

    projects: list[CockpitProject] = []
    day1_base = datetime(2026, 9, 1, tzinfo=timezone.utc).date()
    for i in range(1, n + 1):
        ind = rng.choice(INDUSTRIES)
        day1 = day1_base + timedelta(days=rng.randint(0, 60))
        day100 = day1 + timedelta(days=100)
        projects.append(CockpitProject(
            cp_id=_seq_id("CP", i),
            source_t3_ip_id=f"IP-{i:09d}",
            industry=ind["industry"],
            size_band=ind["size_band"],
            day1_anchor_date=day1.isoformat(),
            day100_end_date=day100.isoformat(),
            status="initialized",
            generated_at=datetime.now(timezone.utc),
        ))
    return projects


def generate_kpi_definitions(cp: CockpitProject, start_n: int = 1) -> list[KpiDefinition]:
    """1 CP につき 4 dim Synergy KPI literal 生成 (cost / revenue / cash_gen / working_capital)。"""
    industry_data = next((d for d in INDUSTRIES if d["industry"] == cp.industry), INDUSTRIES[0])
    return [
        KpiDefinition(
            kp_id=_seq_id("KP", start_n),
            cp_id=cp.cp_id,
            name="cost 削減率",
            dimension="cost",
            unit="%",
            target=15.0,
            benchmark_band="中堅 PMI 平均 ±5%",
            frequency="weekly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", start_n + 1),
            cp_id=cp.cp_id,
            name="revenue 成長率",
            dimension="revenue",
            unit="%",
            target=8.0,
            benchmark_band="中堅 PMI 平均 ±3%",
            frequency="monthly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", start_n + 2),
            cp_id=cp.cp_id,
            name="営業 cash flow",
            dimension="cash_gen",
            unit="千万円",
            target=industry_data["revenue_baseline"] * 0.1,
            benchmark_band="中堅 PMI 平均 ±15%",
            frequency="weekly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", start_n + 3),
            cp_id=cp.cp_id,
            name="working capital cycle",
            dimension="working_capital",
            unit="日",
            target=45.0,
            benchmark_band="中堅 PMI 平均 ±10 日",
            frequency="monthly",
        ),
    ]


def generate_kpi_snapshots(
    cp: CockpitProject,
    kp: KpiDefinition,
    start_n: int,
    days: int = 100,
    seed_offset: int = 0,
) -> list[KpiSnapshot]:
    """1 KPI につき 100 日 timeline daily snapshot literal 生成 (random walk + dimension-specific baseline)。

    random walk 設計: target value ± 30% noise + day_n 経過で trend (Week 2 anomaly detect の literal input)。
    """
    rng = random.Random(get_seed() + seed_offset + hash(kp.kp_id) % 10000)
    snapshots: list[KpiSnapshot] = []
    day1 = datetime.fromisoformat(cp.day1_anchor_date)
    current_value = kp.target * rng.uniform(0.7, 1.3)
    for d in range(1, days + 1):
        observed = day1 + timedelta(days=d - 1)
        noise = rng.gauss(0, kp.target * 0.05)  # 5% std noise
        trend = (d / days) * kp.target * 0.1 * rng.choice([-1, 1])  # mild trend
        current_value += noise + trend / days
        snapshots.append(KpiSnapshot(
            ks_id=_seq_id("KS", start_n + d - 1),
            kp_id=kp.kp_id,
            observed_at=observed.replace(tzinfo=timezone.utc),
            day_n=d,
            value=round(current_value, 2),
            source_type="synthetic",
        ))
    return snapshots


def generate_vendor_contracts(cp: CockpitProject, start_n: int, n: int | None = None) -> list[VendorContract]:
    """1 CP につき random 3-7 件 VendorContract literal 生成 (vendor_pseudonym + industry_tag + annual_fee_band)。"""
    rng = random.Random(get_seed() + hash(cp.cp_id) % 10000)
    if n is None:
        n = rng.randint(3, 7)
    contracts: list[VendorContract] = []
    for i in range(1, n + 1):
        contracts.append(VendorContract(
            vc_id=_seq_id("VC", start_n + i - 1),
            cp_id=cp.cp_id,
            vendor_pseudonym=f"VENDOR-{chr(64 + i)}",  # A, B, C, ...
            industry_tag=rng.choice(VENDOR_INDUSTRY_TAGS),
            annual_fee_band=rng.choice(["100-500 万円", "500-1,000 万円", "1,000-3,000 万円", "3,000-5,000 万円"]),
            renewal_day=(datetime.fromisoformat(cp.day100_end_date) + timedelta(days=rng.randint(30, 365))).date().isoformat(),
            overlap_candidate=[],  # Week 3 で literal 算出
        ))
    return contracts


def generate_saas_licenses(cp: CockpitProject, start_n: int, n: int | None = None) -> list[SaasLicense]:
    """1 CP につき random 5-10 件 SaasLicense literal 生成 (saas_name + seat_count + usage_pct)。"""
    rng = random.Random(get_seed() + hash(cp.cp_id) % 10000 + 1)
    if n is None:
        n = rng.randint(5, 10)
    licenses: list[SaasLicense] = []
    for i in range(1, n + 1):
        seat = rng.randint(10, 200)
        usage = round(rng.uniform(10.0, 95.0), 1)
        licenses.append(SaasLicense(
            sl_id=_seq_id("SL", start_n + i - 1),
            cp_id=cp.cp_id,
            saas_name=SAAS_NAMES[(i - 1) % len(SAAS_NAMES)],
            seat_count=seat,
            usage_pct=usage,
            annual_fee_band=rng.choice(["50-100 万円", "100-300 万円", "300-500 万円", "500-1,000 万円"]),
            overlap_candidate=[],  # Week 3 で literal 算出
        ))
    return licenses


def generate_synthetic_cockpit(n_projects: int = 5, days: int = 100, seed: int | None = None) -> list[T4Output]:
    """合成 PMI cockpit dataset 全 entity literal 生成 (N 案件 × 4 KPI × 100 日 + vendor + SaaS)。

    Returns: T4Output list (1 CP につき 1 T4Output)。
    """
    projects = generate_cockpit_projects(n=n_projects, seed=seed)
    outputs: list[T4Output] = []

    kp_seq = 1
    ks_seq = 1
    vc_seq = 1
    sl_seq = 1
    for cp in projects:
        kpi_defs = generate_kpi_definitions(cp, start_n=kp_seq)
        kp_seq += len(kpi_defs)

        kpi_snapshots: list[KpiSnapshot] = []
        for kp in kpi_defs:
            snapshots = generate_kpi_snapshots(cp, kp, start_n=ks_seq, days=days)
            kpi_snapshots.extend(snapshots)
            ks_seq += len(snapshots)

        vcs = generate_vendor_contracts(cp, start_n=vc_seq)
        vc_seq += len(vcs)

        sls = generate_saas_licenses(cp, start_n=sl_seq)
        sl_seq += len(sls)

        outputs.append(T4Output(
            cockpit_project=cp,
            kpi_definitions=kpi_defs,
            kpi_snapshots=kpi_snapshots,
            driver_insights=[],  # Week 2 で literal 生成
            next_actions=[],  # Week 2 で literal 生成
            sentiment_events=[],  # Week 3 で literal 生成
            vendor_contracts=vcs,
            saas_licenses=sls,
            retention_risks=[],  # T3 JPDay1Pattern trigger 経由は integration module 側
        ))
    return outputs


# ─── CLI entry (smoke 用) ──────────────────────────────────────────────

def main() -> None:
    """`python -m src.data_gen.generate_synthetic_cockpit` で smoke 実行。"""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    outputs = generate_synthetic_cockpit(n_projects=5, days=100)
    for o in outputs:
        cp = o.cockpit_project
        print(f"[CP] {cp.cp_id} {cp.industry} ({cp.size_band}) day1={cp.day1_anchor_date}")
        print(f"  KPI defs: {len(o.kpi_definitions)} / snapshots: {len(o.kpi_snapshots)} / vendors: {len(o.vendor_contracts)} / SaaS: {len(o.saas_licenses)}")


if __name__ == "__main__":
    main()
