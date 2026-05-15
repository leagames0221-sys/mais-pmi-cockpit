"""T4 Object Type Pydantic schema SSoT。


  - operational DB: redacted statement / 連絡先 band / pseudonym のみ
  - vault DB: raw statement + 連絡先 + signatory (本 schema では Op 側のみ literal 定義、 vault 側 PII schema は src/vault/ で別途)

ID prefix (T1/T2/T3 非衝突、 CLAUDE.md 命名規則順守):
  CP / KP / KS / DR / NA / SE / VC / SL / RT
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─── ID type aliases ────────────
CockpitProjectId = str # CP-XXXXXX
KpiDefinitionId = str # KP-XXXXXX
KpiSnapshotId = str # KS-XXXXXX
DriverInsightId = str # DR-XXXXXX
NextActionId = str # NA-XXXXXX
SentimentEventId = str # SE-XXXXXX
VendorContractId = str # VC-XXXXXX
SaasLicenseId = str # SL-XXXXXX
RetentionRiskId = str # RT-XXXXXX

# T3 ID prefix
T3IntegrationPlanId = str # IP-XXXXXXXXX
T3CommunicationKitId = str # CK-XXXXXX
T3JPDay1PatternId = str # JPD1-XXXXXX


# ─── 1. CockpitProject (CP-XXXXXX、 PMI 案件 1 件、 T3 IP-XXXXXX inherit) ─

class CockpitProject(BaseModel):
    """PMI 案件 1 件 = 1 CP、 Day-1 → Day-100 期間の cockpit root。 it reference。"""

    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    source_t3_ip_id: T3IntegrationPlanId = Field(..., pattern=r"^IP-[0-9]{9}$")
    industry: str
    size_band: str
    day1_anchor_date: str # ISO 日付 (T3 IntegrationPlan day1_target_date inherit)
    day100_end_date: str # day1 + 100 日 自動算出
    status: Literal["initialized", "monitoring", "completed", "arcinternald"]
    generated_at: datetime


# ─── 2. KpiDefinition (KP-XXXXXX、 Synergy KPI 定義) ─────────────────────

class KpiDefinition(BaseModel):
    """Synergy KPI 定義 (cost / revenue / cash_gen / working_capital + 中堅日本企業特化 KPI)。"""

    kp_id: KpiDefinitionId = Field(..., pattern=r"^KP-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    name: str # 例: "営業 cash flow"
    dimension: Literal["cost", "revenue", "cash_gen", "working_capital", "retention", "vendor_consolidation"]
    unit: str # 例: "千万円" / "%"
    target: float
    benchmark_band: Optional[str] = None # 例: "中堅 PMI 平均 ±15%"
    frequency: Literal["daily", "weekly", "monthly"]


# ─── 3. KpiSnapshot (KS-XXXXXX、 時系列 KPI 値) ──────────────────────────

class KpiSnapshot(BaseModel):
    """時系列 KPI 値 (daily/weekly/monthly granularity)。"""

    ks_id: KpiSnapshotId = Field(..., pattern=r"^KS-[0-9]{6}$")
    kp_id: KpiDefinitionId = Field(..., pattern=r"^KP-[0-9]{6}$")
    observed_at: datetime
    day_n: int = Field(..., ge=1, le=100) # Day-1 起点からの経過日 (1-100)
    value: float
    source_type: Literal["synthetic", "real"] # 試作 = synthetic、 移植時 = real


# ─── 4. DriverInsight (DR-XXXXXX、 KPI 変動 root cause AI surface) ──────

class DriverInsight(BaseModel):
    """KPI 変動 root cause、 AI surface (5-stage hybrid pipeline + Claude LLM)、 citation link back 付き。"""

    dr_id: DriverInsightId = Field(..., pattern=r"^DR-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    ks_id_ref: KpiSnapshotId = Field(..., pattern=r"^KS-[0-9]{6}$")
    statement_redacted: str # 担当者氏名 / 取引先名 / 内部金額 redact 済
    driver_factors: list[str] # 例: ["AR_aging", "trade_term_change"]
    citation_array: list[str] # T2/T3 inherit Citation literal reuse (CIT-XXXXXX)
    confidence: float = Field(..., ge=0.0, le=1.0)


# ─── 5. NextAction (NA-XXXXXX、 KPI falter 時 LLM 推奨) ─────────────────

class NextActionCandidate(BaseModel):
    """NextAction 5 候補 ranked。"""

    rank: int = Field(..., ge=1, le=5)
    action: str
    expected_impact: Literal["低", "中", "高"]


class NextAction(BaseModel):
    """KPI falter 時 LLM 推奨 next action (5 候補 ranked + audience mapping)、 T3 CK-XXXXXX inherit。"""

    na_id: NextActionId = Field(..., pattern=r"^NA-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    dr_id_ref: DriverInsightId = Field(..., pattern=r"^DR-[0-9]{6}$")
    action_statement_redacted: str # 取引先実名 / 担当者氏名 redact 済
    audience_mapping: T3CommunicationKitId = Field(..., pattern=r"^CK-[0-9]{6}$") # T3 CommunicationKit literal reference
    priority_rank: int = Field(..., ge=1, le=5)
    due_day_n: int = Field(..., ge=1, le=100)
    status: Literal["proposed", "approved", "in_progress", "completed", "dismissed"]
    candidates_ranked: list[NextActionCandidate]


# ─── 6. SentimentEvent (SE-XXXXXX、 退職率 / engagement signal) ──────────

class SentimentEvent(BaseModel):
    """退職率 / engagement signal (Slack/Teams/アンケート source、 HF Transformers + Claude 多軸分析)。"""

    se_id: SentimentEventId = Field(..., pattern=r"^SE-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    source_channel: Literal["slack", "teams", "survey"]
    observed_at: datetime
    sentiment_score: float = Field(..., ge=-1.0, le=1.0) # -1.0 (negative) ~ 1.0 (positive)
    topic_tag: list[str] # 例: ["人事制度変更", "不安"]
    excerpt_redacted: str # employee_name / channel_name redact 済


# ─── 7. VendorContract (VC-XXXXXX、 vendor 契約 entity) ─────────────────

class VendorContract(BaseModel):
    """vendor 契約 entity、 重複統合機会 detect 対象。"""

    vc_id: VendorContractId = Field(..., pattern=r"^VC-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    vendor_pseudonym: str # 例: "VENDOR-A" (raw vendor 名は vault)
    industry_tag: str # 例: "クラウド"
    annual_fee_band: str # 例: "1,000-3,000 万円" (raw 金額は vault)
    renewal_day: str # ISO 日付
    overlap_candidate: list[VendorContractId] = Field(default_factory=list) # 他 vc_id list


# ─── 8. SaasLicense (SL-XXXXXX、 SaaS subscription、 VC との overlap detect) ─

class SaasLicense(BaseModel):
    """SaaS subscription entity、 VC との overlap detect 対象 (機能類似度 + 5-stage hybrid 流用)。"""

    sl_id: SaasLicenseId = Field(..., pattern=r"^SL-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    saas_name: str # 例: "SaaS-Y" (実 SaaS 名は vault、 試作 = pseudonym)
    seat_count: int = Field(..., ge=0)
    usage_pct: float = Field(..., ge=0.0, le=100.0)
    annual_fee_band: str # 例: "100-300 万円"
    overlap_candidate: list[SaasLicenseId] = Field(default_factory=list)


# ─── 9. RetentionRisk (RT-XXXXXX、 退職 risk score、 中堅日本企業 fit detector) ─

class RetentionRisk(BaseModel):
    """退職 risk score 0-100 (SentimentEvent + 中堅日本企業 文化 fit detector 連携、 T3 JPDay1Pattern analogical)。"""

    rt_id: RetentionRiskId = Field(..., pattern=r"^RT-[0-9]{6}$")
    cp_id: CockpitProjectId = Field(..., pattern=r"^CP-[0-9]{6}$")
    score: int = Field(..., ge=0, le=100)
    dimension: Literal["organization", "culture", "business_practice"]
    triggered_jp_patterns: list[T3JPDay1PatternId] = Field(default_factory=list) # T3 JPDay1Pattern reference
    se_id_refs: list[SentimentEventId] = Field(default_factory=list) # SentimentEvent reference
    mitigation_recommendation_redacted: str # 担当者氏名 redact 済


# ─── T4Output container ────

class T4Output(BaseModel):
    """T3 API output → T4 ingestion 全 結果の container schema。"""

    cockpit_project: CockpitProject
    kpi_definitions: list[KpiDefinition]
    kpi_snapshots: list[KpiSnapshot]
    driver_insights: list[DriverInsight]
    next_actions: list[NextAction]
    sentiment_events: list[SentimentEvent]
    vendor_contracts: list[VendorContract]
    saas_licenses: list[SaasLicense]
    retention_risks: list[RetentionRisk]
