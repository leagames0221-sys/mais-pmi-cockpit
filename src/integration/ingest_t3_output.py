"""T3 API output → T4 CockpitProject + 9 Object Type variant への literal mapping。

mapping rule:
  - T3 IntegrationPlan (IP-XXXXXXXXX) → T4 CockpitProject (CP-XXXXXX) 1:1 inherit
  - T3 PlanNode (PN-XXXXXX、 Day-N task) → T4 KPI 監視 anchor (KpiSnapshot 時系列 anchor 生成)
  - T3 DependencyEdge (DE-XXXXXX) → T4 KPI driver dependency 入力 (DriverInsight driver_factors)
  - T3 RiskScore (RS-XXXXXX、 5 dim 0-100) → T4 NextAction (NA-XXXXXX) priority_rank weight
  - T3 CommunicationKit (CK-XXXXXX、 5 aud) → T4 NextAction audience_mapping literal reference (同 5 audience cascade pattern)
  - T3 JPDay1Pattern (JPD1-XXXXXX、 5 軸) → T4 RetentionRisk (RT-XXXXXX) + VendorContract (VC-XXXXXX) trigger

PII boundary (CLAUDE.md systemPatterns 順守、 doctrine: drift-prevention + module boundary lint で verify):
  T3 API output は T3 /203 で **既 redact 済** literal 前提、 T4 で再 redact 不要。
  ただし T4 operational DB 保存時の PII boundary check は維持。
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.schema.types import (
    CockpitProject,
    DriverInsight,
    KpiDefinition,
    KpiSnapshot,
    NextAction,
    NextActionCandidate,
    RetentionRisk,
    SentimentEvent,
    T4Output,
    VendorContract,
    SaasLicense,
)


# ─── ID generator ───────────────

def _seq_id(prefix: str, n: int) -> str:
    """例: _seq_id('CP', 1) → 'CP-000001'。 link key UUID-style 順守。"""
    return f"{prefix}-{n:06d}"


# ─── T3 output → T4 mapping ─────────────────────────────

def ingest_t3_output(t3_output: dict) -> T4Output:
    """T3 API output dict (IntegrationPlan + PlanNode + DependencyEdge + RiskScore + CommunicationKit + JPDay1Pattern) を受け取り、 T4Output container に literal 変換。

    Args:
        t3_output: T3 `/api/generate` endpoint 返却 JSON または local fixture dict。
                   必須 keys: integration_plan, plan_nodes, dependency_edges, risk_scores,
                   communication_kits, jp_day1_patterns

    Returns:
        T4Output: 9 Object Type literal mapped container。
    """
    # 1. CockpitProject = T3 IntegrationPlan 1:1 inherit
    ip = t3_output["integration_plan"]
    day1 = datetime.fromisoformat(ip["day1_target_date"]).date()
    day100 = day1 + timedelta(days=100)

    cp = CockpitProject(
        cp_id=_seq_id("CP", 1),
        source_t3_ip_id=ip["ip_id"],
        industry=ip.get("industry", "未指定"),
        size_band=ip.get("size_band", "未指定"),
        day1_anchor_date=day1.isoformat(),
        day100_end_date=day100.isoformat(),
        status="initialized",
        generated_at=datetime.now(timezone.utc),
    )

    # 2. KpiDefinition = T4 default Synergy KPI 4 dim
    kpi_defs = _default_kpi_definitions(cp.cp_id)

    # 3. KpiSnapshot = empty (Week 2 で literal 生成、 PlanNode anchor 経由)
    kpi_snapshots: list[KpiSnapshot] = []

    # 4. DriverInsight = empty (Week 2 で literal 生成、 KPI anomaly detect 経由)
    driver_insights: list[DriverInsight] = []

    # 5. NextAction = empty (Week 2 で literal 生成、 anomaly + LLM rerank 経由)
    next_actions: list[NextAction] = []

    # 6. SentimentEvent = empty (Week 3 で literal 生成、 HF Transformers + Claude)
    sentiment_events: list[SentimentEvent] = []

    # 7. VendorContract = empty (Week 3 で literal 生成、 T2 docling reuse)
    vendor_contracts: list[VendorContract] = []

    # 8. SaasLicense = empty (Week 3 で literal 生成)
    saas_licenses: list[SaasLicense] = []

    # 9. RetentionRisk = T3 JPDay1Pattern hit から literal trigger (Week 1 部分実装、 Week 3 完成)
    retention_risks = _trigger_retention_risk_from_jp_patterns(
        cp_id=cp.cp_id,
        jp_patterns=t3_output.get("jp_day1_patterns", []),
    )

    return T4Output(
        cockpit_project=cp,
        kpi_definitions=kpi_defs,
        kpi_snapshots=kpi_snapshots,
        driver_insights=driver_insights,
        next_actions=next_actions,
        sentiment_events=sentiment_events,
        vendor_contracts=vendor_contracts,
        saas_licenses=saas_licenses,
        retention_risks=retention_risks,
    )


def _default_kpi_definitions(cp_id: str) -> list[KpiDefinition]:
    """T4 default Synergy KPI 4 dim。"""
    return [
        KpiDefinition(
            kp_id=_seq_id("KP", 1),
            cp_id=cp_id,
            name="cost 削減率",
            dimension="cost",
            unit="%",
            target=15.0,
            benchmark_band="中堅 PMI 平均 ±5%",
            frequency="weekly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", 2),
            cp_id=cp_id,
            name="revenue 成長率",
            dimension="revenue",
            unit="%",
            target=8.0,
            benchmark_band="中堅 PMI 平均 ±3%",
            frequency="monthly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", 3),
            cp_id=cp_id,
            name="営業 cash flow",
            dimension="cash_gen",
            unit="千万円",
            target=50.0,
            benchmark_band="中堅 PMI 平均 ±15%",
            frequency="weekly",
        ),
        KpiDefinition(
            kp_id=_seq_id("KP", 4),
            cp_id=cp_id,
            name="working capital cycle",
            dimension="working_capital",
            unit="日",
            target=45.0,
            benchmark_band="中堅 PMI 平均 ±10 日",
            frequency="monthly",
        ),
    ]


def _trigger_retention_risk_from_jp_patterns(
    cp_id: str,
    jp_patterns: list[dict],
) -> list[RetentionRisk]:
    """T3 JPDay1Pattern hit (5 軸) から T4 RetentionRisk trigger。

    mapping rule:
      - 「union_relation / family_integration / business_practice」 軸 = RT (organization / culture / business_practice dim)
      - 「bank_relation / trade_custom」 軸 = VC trigger (本関数では RT のみ生成、 VC trigger は Week 3 で literal active)
    """
    RT_AXIS_MAP = {
        "union_relation": "organization",
        "family_integration": "culture",
        "business_practice": "business_practice",
    }
    SEVERITY_TO_SCORE = {"low": 30, "medium": 60, "high": 85}

    risks: list[RetentionRisk] = []
    for i, p in enumerate(jp_patterns, start=1):
        axis = p.get("axis", "")
        if axis not in RT_AXIS_MAP:
            continue # bank_relation / trade_custom = Week 3 で VC trigger 側で処理
        risks.append(RetentionRisk(
            rt_id=_seq_id("RT", i),
            cp_id=cp_id,
            score=SEVERITY_TO_SCORE.get(p.get("severity", "medium"), 60),
            dimension=RT_AXIS_MAP[axis],
            triggered_jp_patterns=[p["jpd1_id"]],
            se_id_refs=[], # Week 3 で literal 連携
            mitigation_recommendation_redacted=p.get("summary_redacted", "(redacted summary)"),
        ))
    return risks


# ─── CLI entry (smoke 用) ──────────────────────────────────────────────

def main(t3_output_path: Optional[str] = None) -> T4Output:
    """`python -m src.integration.ingest_t3_output <t3_output.json>` で smoke 実行。"""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    if t3_output_path is None and len(sys.argv) > 1:
        t3_output_path = sys.argv[1]

    if t3_output_path is None:
        # mock t3 output (smoke 用)
        t3_output = {
            "integration_plan": {
                "ip_id": "IP-000000001",
                "industry": "製造業",
                "size_band": "従業員 100-300 名",
                "day1_target_date": "2026-09-01",
            },
            "plan_nodes": [],
            "dependency_edges": [],
            "risk_scores": [],
            "communication_kits": [],
            "jp_day1_patterns": [
                {"jpd1_id": "JPD1-000001", "axis": "family_integration", "severity": "high",
                 "summary_redacted": "(redacted: 同族統合 risk high)"},
                {"jpd1_id": "JPD1-000002", "axis": "union_relation", "severity": "medium",
                 "summary_redacted": "(redacted: 組合対応 medium)"},
            ],
        }
    else:
        with open(t3_output_path, "r", encoding="utf-8") as f:
            t3_output = json.load(f)

    result = ingest_t3_output(t3_output)
    print(f"[T3→T4] CP: {result.cockpit_project.cp_id} (source IP: {result.cockpit_project.source_t3_ip_id})")
    print(f"[T3→T4] KPI definitions: {len(result.kpi_definitions)}")
    print(f"[T3→T4] RetentionRisk triggered: {len(result.retention_risks)}")
    return result


if __name__ == "__main__":
    main()
