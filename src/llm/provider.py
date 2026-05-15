"""LLMProvider Protocol (T1/T2/T3 inherit pattern、 ADR-304 順守)。

3 method:
  - generate_kpi_driver_insight: KPI anomaly + 関連 factor から driver_insight statement 生成
  - generate_next_action_candidates: DriverInsight → 5 候補 ranked NextAction
  - evaluate_anomaly_severity: Isolation Forest 結果 + Claude CoT grounding reasoning (AnomSeer pattern)

試作 = MockProvider (deterministic、 API key 不要、 数 ms 応答)、 移植時 = Claude / Gemini 1 file swap。
"""
from __future__ import annotations

from typing import Optional, Protocol

from src.schema.types import NextActionCandidate


class LLMProvider(Protocol):
    """LLM call abstraction、 試作 = MockProvider / 移植時 = Claude / Gemini / Ollama swap path。"""

    def generate_kpi_driver_insight(
        self,
        kpi_name: str,
        kpi_dimension: str,
        observed_value: float,
        target_value: float,
        day_n: int,
        anomaly_score: float,
    ) -> tuple[str, list[str], float]:
        """KPI anomaly から driver insight statement 生成。 Returns: (statement_redacted, driver_factors, confidence)。"""
        ...

    def generate_next_action_candidates(
        self,
        driver_statement: str,
        driver_factors: list[str],
        kpi_dimension: str,
    ) -> list[NextActionCandidate]:
        """DriverInsight から 5 候補 ranked NextAction 生成 (listwise CoT)。"""
        ...

    def evaluate_anomaly_severity(
        self,
        kpi_dimension: str,
        anomaly_score: float,
    ) -> str:
        """Isolation Forest 結果 + AnomSeer grounding reasoning。 Returns: severity reasoning text。"""
        ...


class MockProvider:
    """deterministic mock (試作期間中の default、 ANTHROPIC_API_KEY 不要)。"""

    DRIVER_FACTORS_BY_DIM = {
        "cost": ["fixed_cost_overrun", "headcount_excess", "vendor_pricing_unfavorable"],
        "revenue": ["channel_attrition", "promotion_inefficiency", "customer_acquisition_cost_up"],
        "cash_gen": ["AR_aging", "inventory_buildup", "AP_acceleration", "trade_term_change"],
        "working_capital": ["DSO_extension", "DIO_extension", "DPO_compression"],
        "retention": ["sentiment_negative", "compensation_gap", "succession_uncertainty"],
        "vendor_consolidation": ["duplicate_contracts", "low_seat_utilization", "renewal_cluster"],
    }

    CANDIDATE_TEMPLATES_BY_DIM = {
        "cost": [
            ("固定 cost 棚卸し + 30 日 review", "高"),
            ("vendor 価格交渉 5 件 trigger", "中"),
            ("業務外注 review (in-house path 検討)", "中"),
            ("月次予算 check 週次化", "低"),
            ("経費 KPI dashboard 全社展開", "低"),
        ],
        "revenue": [
            ("既存顧客 cross-sell campaign launch", "高"),
            ("離反 risk 顧客 retention call 5 件", "中"),
            ("新規 channel test (1 ヶ月 pilot)", "中"),
            ("価格改定 simulation 起草", "中"),
            ("顧客 NPS 緊急調査", "低"),
        ],
        "cash_gen": [
            ("支払サイト変更要望の取引先 3 社と週内に再交渉", "高"),
            ("回収サイト短縮の sales channel review", "高"),
            ("在庫 SKU TOP 10 削減 trigger", "中"),
            ("入金 fund 短期融資調達 path 検討", "中"),
            ("経費 余剰検出 + 30 日 fund 確保", "中"),
        ],
        "working_capital": [
            ("DSO 短縮 (回収 KPI 週次化)", "高"),
            ("DIO 短縮 (在庫 SKU 削減)", "中"),
            ("DPO 延伸交渉 (vendor 5 件 trigger)", "中"),
            ("運転資金 line review", "低"),
            ("CCC (cash conversion cycle) 全社可視化", "低"),
        ],
        "retention": [
            ("人事面談 緊急 trigger (組織 dim 全社員)", "高"),
            ("給与 / 待遇 review meeting 設定", "中"),
            ("組合対応 / 取引銀行折衝 escalation", "中"),
            ("中長期 vision communication 再徹底", "中"),
            ("退職率 KPI 週次 dashboard 化", "低"),
        ],
        "vendor_consolidation": [
            ("重複 vendor 契約 5 件 統合交渉", "高"),
            ("SaaS license 未使用 seat 30% 削減", "高"),
            ("vendor 一覧 棚卸し (Docling parse 全件)", "中"),
            ("renewal cluster 期日前 60 日 review", "中"),
            ("vendor リスト 中堅 PMI 平均比較 surface", "低"),
        ],
    }

    def generate_kpi_driver_insight(
        self,
        kpi_name: str,
        kpi_dimension: str,
        observed_value: float,
        target_value: float,
        day_n: int,
        anomaly_score: float,
    ) -> tuple[str, list[str], float]:
        deviation_pct = abs((observed_value - target_value) / target_value * 100) if target_value else 0
        direction = "下振れ" if observed_value < target_value else "上振れ"
        statement = (
            f"Day-{day_n} 時点で {kpi_name} (dimension={kpi_dimension}) が target {target_value:.2f} "
            f"に対し {observed_value:.2f} = {deviation_pct:.1f}% {direction}。 anomaly_score={anomaly_score:.3f}。"
        )
        # PII redacted: 担当者氏名 / 取引先名 / 内部金額 mention literal 無し
        factors = self.DRIVER_FACTORS_BY_DIM.get(kpi_dimension, ["unspecified_factor"])
        confidence = min(0.95, 0.5 + abs(anomaly_score) * 0.5)
        return statement, factors, round(confidence, 2)

    def generate_next_action_candidates(
        self,
        driver_statement: str,
        driver_factors: list[str],
        kpi_dimension: str,
    ) -> list[NextActionCandidate]:
        templates = self.CANDIDATE_TEMPLATES_BY_DIM.get(
            kpi_dimension,
            [("KPI dashboard 拡充", "中")] * 5,
        )
        return [
            NextActionCandidate(rank=i + 1, action=action, expected_impact=impact)
            for i, (action, impact) in enumerate(templates[:5])
        ]

    def evaluate_anomaly_severity(
        self,
        kpi_dimension: str,
        anomaly_score: float,
    ) -> str:
        # AnomSeer pattern grounding: anomaly_score 範囲別 reasoning literal 出力
        if anomaly_score < -0.5:
            return f"[{kpi_dimension}] severe anomaly (score={anomaly_score:.3f}): 即時 escalation 推奨"
        elif anomaly_score < -0.2:
            return f"[{kpi_dimension}] medium anomaly (score={anomaly_score:.3f}): 来週 review 起草"
        else:
            return f"[{kpi_dimension}] mild deviation (score={anomaly_score:.3f}): 週次 monitor 継続"


def default_provider() -> LLMProvider:
    """ENV var LLM_PROVIDER に従い provider 選択 (default = mock)。 移植時 Claude/Gemini swap path。"""
    import os
    name = os.environ.get("LLM_PROVIDER", "mock").lower()
    if name == "mock":
        return MockProvider()
    # 移植時に Claude / Gemini provider literal 追加
    raise NotImplementedError(f"LLM_PROVIDER={name} not yet implemented (Week 2 PoC = mock のみ literal active)")
