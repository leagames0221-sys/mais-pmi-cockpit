# T4 Discovery Brief — MAIS / T4 100 日 PMI cockpit

> Spec-Driven Workflow Stage 1 (Discovery) deliverable。
> user gate 通過済 (2026-05-13、 3 軸 全 OK 受領: scope+stack / ADR+ID prefix / Phase C scaffold 一気 path)。 本 brief 確定後 Stage 2 (Requirements) 移行。

---

## 1. PJ Identity (sibling 位置付け)

- **scope**: M&A advisory engagement 提案 § T4 application — **M&A 成約後 Day-1 → Day-100 期間 Synergy KPI live cockpit AI** PoC 試作
- **target**: プレゼン demo ready、 4 週で動く版完成
- **移植先**: client infrastructure (後日)、 本 repo は試作 only
- **sibling**: mais-deal-matching (T1 マッチング、 完成度 100%) + mais-dd-workbench (T2 DD 自動化、 完成度 100%) + mais-day1-cockpit (T3 Day-1 readiness、 完成度 100%) と MAIS ecosystem 共通基盤 (internal ADR) を citation reference で literal 共有
- **4th sibling 位置付け**: T3 の API output (IntegrationPlan + PlanNode + RiskScore + CommunicationKit + JPDay1Pattern) を T4 が入力として literal 流用、 「DD → Day-1 → Day-100 cockpit」 というoriginal proposal § 5-3 優先順位 (T2 → T3 → T4) に literal 順守

## 2. 機密度 + 取扱方針

- **PII**: 合成 PMI cockpit data only、 実 M&A 案件 / 実 KPI / 実従業員 sentiment / 実 vendor 契約 / 実 SaaS license は literal 一切扱わない
- **credential**: ANTHROPIC_API_KEY のみ (.env、 gitignore 必須、 Week 2 LLM call phase で active 化、 試作期間中は MockProvider で API key 不要)
- **doctrine: sandbox-check**: 試作 scope + 合成データ only のため host PC OK (real KPI / 実 vendor / 実 SaaS 投入時に Docker / sandbox 化必須)

## 3. 採用 stack 10+ 件 (doctrine: prior-art-first + doctrine: external-source-audit 順守、 Week 1 audit gate 通過後 active)

### T4 新規採用 4 件

| # | ひな形 | license | 役割 | red flag | tier |
|---|---|---|---|---|---|
| ① | **Apache Superset 6.0+** | Apache-2.0 | Synergy KPI live dashboard embed (v6 2025-12 / v7 2026 H1 active roadmap、 大規模 BI 業界 standard) | Embedded SDK JWT auth literal 配線必要 | ★★★ (Week 1 audit + pip-audit 通過後 active) |
| ② | **scikit-learn ≥ 1.4** | BSD-3 | Isolation Forest (anomaly detect 業界 standard、 LSTM 不要で consumer laptop OK) | None (Numfocus 母体) | ★★★ |
| ③ | **transformers ≥ 4.40** | Apache-2.0 | sentiment 多言語 model base (Slack / Teams / アンケート LLM 分析) | model license 個別 (Apache-2.0 model 限定採用) | ★★★ |
| ④ | **pandas ≥ 2.2** | BSD-3 | KPI snapshot tabular (時系列 KPI 値 + group-by + rolling window) | None (Numfocus 母体) | ★★★ |

### T1/T2/T3 inherit 6 件 (既 audit 済、 本 PJ で literal reuse のみ)

| # | ひな形 | license | inherit 元 | 役割 |
|---|---|---|---|---|
| ⑤ | LangGraph 1.2.0+ + langgraph-checkpoint 4.1.0+ | MIT | T3 ADR-201 (CVE-2026-28277 元削除済 pin) | DAG-based KPI ingestion → anomaly → driver → next action orchestrator |
| ⑥ | LlamaIndex CitationQueryEngine | MIT | T2 ADR-101 | citation infra (driver insight + next action 文書 link back) |
| ⑦ | sentence-transformers + faiss-cpu + rank-bm25 + cross-encoder | mixed (Apache-2.0 中心) | T1 ADR-005 + T2/T3 inherit | 5-stage hybrid pipeline (driver insight + vendor 統合機会 surface) |
| ⑧ | NetworkX ≥ 3.x | BSD-3 | T3 ADR-201 | KPI driver dependency graph + cyclic 検出 |
| ⑨ | docling | MIT | T2 ADR-101 | vendor 契約 / SaaS license 文書 parsing |
| ⑩ | LLMProvider Protocol + TTS engine 動画 pipeline | (T1 既存) + cross-PJ universal SSoT | T3 inherit | Stage 5 LLM listwise rerank + 機能紹介動画 (cross-PJ SSoT 経由 literal 即適用) |

### T4 自作 1 件 (競合優位 core)

| # | ひな形 | license | 役割 |
|---|---|---|---|
| ⑪ | MAIS 自作 **中堅日本企業 PMI KPI benchmark + 退職率 sentiment pattern 5 軸 detector** | MAIS 内部 | 中堅 PMI 平均比較 / 退職率 prediction / 取引銀行折衝 KPI 連携 (original proposal § T4 line 448 literal 主張点 = 競合優位 core) |

## 4. 2026.5 deeper scan 結論

### KPI live dashboard 採用 — **Apache Superset 6.0** literal 確定

OSS 「1:1 一致」 100 日 PMI cockpit generator は **literal ZERO** (GitHub / PyPI 全 scan、 2 round)。 商用 / コンサル提供のみ (top-tier consulting firm X / top-tier PMI advisor / Torii / BetterCloud / Tropic)。 業界 standard 構造 (Synergy KPI 4 dim × 時系列 × dashboard + driver insight + next action) は **decomposed prior art** として literal inherit、 BI 層 = Apache Superset、 anomaly 層 = sklearn、 sentiment 層 = transformers、 vendor 層 = T2 Docling reuse、 next action 層 = Claude LLM listwise。

### Anomaly detection 採用 — **Isolation Forest + AnomSeer 2026 pattern** literal 確定

2026 SOTA = MLLM (Multimodal LLM) reinforce for time-series anomaly (AnomSeer / OpenReview Jl0QHFcyCl)。 ただし consumer laptop で重い → classical Isolation Forest (sklearn) を base + AnomSeer pattern (grounding reasoning) を Claude CoT prompt で literal 模倣。 detection rate ★★★ + 説明可能性 ★★★ で受託 deploy ready path 確保。

### Sentiment 分析 採用 — **HF Transformers + Claude LLM** literal 確定

商用 (Lattice / Achievers / Blix) と feature parity 確保のため OSS combination 採用: multilingual sentiment base (transformers) + LLM 多軸分析 (Claude、 「組合対応」 「同族統合」 等の T3 JPDay1Pattern 軸 analogical) + Slack/Teams mock connector (移植時 real API)。

### Vendor / SaaS overlap detect 採用 — **T2 Docling + 5-stage hybrid + 自作 detector** literal 確定

商用 SMP (Torii / BetterCloud) と feature parity 確保のため OSS combination 採用: Docling parse (T2 inherit) + 5-stage hybrid 機能類似度 (T1 inherit) + 中堅日本企業 vendor 統合 pattern detector 自作 (differentiation core、 ゼロ生成立証責任ここに literal 集中)。

## 5. internal ADR 共通 doctrine 6 component inherit (citation reference のみ、 重複起草禁止)

1. brand identity — MAIS / T4 100-Day、 黒金 / Noto Serif JP / 年輪 SVG / tagline 「経営の責務を、 次の人へ。」
2. visual identity — 金 (`#d4af37` 等) × 黒、 motif + layout literal 不変
3. data 共通 doctrine — 会員制 two-sided + **PII/Op 分離** (T4 PII = 担当者連絡先・vendor 連絡先・SaaS holder、 Op = redact 済 KPI snapshot / driver insight / next action / sentiment excerpt / vendor pseudonym) + 7-layer security
4. AI pipeline 共通 doctrine — 5-stage hybrid + LLMProvider Protocol (T4 = driver insight + vendor 統合機会 + next action retrieval)
5. 動画 pipeline 共通 doctrine — TTS engine まお おちついた + auto-sync + 90s timeout (cross-PJ universal SSoT、 2026-05-13 完成)
6. infra / drift 防止 共通 doctrine — drift CI + pip-audit + Dependabot + e2e_smoke + internal knowledge base 5 file

## 6. T4 固有拡張 (ADR-300+、 重複起草禁止)

- **ADR-300**: T4 PJ scope 確定 (本 brief literal 反映、 完了)
- **ADR-301**: 採用 OSS 10+ 件 audit + Week 1 requirements (EARS 形式)
- **ADR-302**: T3 → T4 入出力契約 schema (T3 6 schema → T4 mapping、 起草完了)
- **ADR-303**: T4 Object Type 9 件 (`CockpitProject` / `KpiDefinition` / `KpiSnapshot` / `DriverInsight` / `NextAction` / `SentimentEvent` / `VendorContract` / `SaasLicense` / `RetentionRisk`、 internal ADR § 3 PII/Op 分離 pattern 適用、 Week 1 起草)
- **ADR-304**: LangGraph state graph 設計 (KPI ingestion → anomaly → driver → next action) + Isolation Forest + LLM next action + MCP future-proof path (Week 2 起草)
- **ADR-305**: 中堅日本企業 PMI KPI benchmark + 退職率 sentiment pattern library 5 軸 (組合対応 / 取引銀行折衝 / 同族統合 / 商習慣 / 取引慣行 = T3 JPDay1Pattern analogical) (Week 3 起草)

## 7. 4 週 PoC roadmap

| Week | 着手 task | deliverable |
|---|---|---|
| **Week 0** | GitHub PRIVATE repo 作成 + scaffold 全 file + drift CI / pip-audit / Dependabot active + ADR-300/301/302 起草 | green CI / internal knowledge base 5 file / 本 Discovery brief literal 採択 |
| **Week 1** | 採用 10+ stack audit (Superset advisory scan + sklearn/transformers/pandas audit + T1/T2/T3 inherit verify) + Requirements (EARS) + Object Type 9 件 ADR-303 + Design File Structure Plan | ADR-301/302/303 / `src/` 12 module dir + `tests/` |
| **Week 2** | LangGraph state graph 実装 (KPI ingestion → anomaly → driver → next action) + Isolation Forest + Claude LLM listwise CoT + T3 API output 流用 ingestion | ADR-304 / state graph + anomaly + next action recommender literal 動作 + smoke test |
| **Week 3** | SentimentEvent (HF Transformers + Claude、 Slack/Teams/アンケート mock connector) + VendorContract/SaaSLicense overlap detect (Docling reuse + 5-stage hybrid + 中堅日本企業 pattern 自作) + Citation link back | ADR-305 / sentiment + vendor 統合機会 + retention risk literal |
| **Week 4** | Apache Superset embed (FastAPI/Jinja wrapper + 黒金 brand CSS) + Vault Pattern (担当者連絡先 + vendor 連絡先 vault) + e2e_smoke + 動画 pipeline (SCENES T4 版、 cross-PJ SSoT 経由 literal 即適用、 16 scene 程度) | `out_video/mais_mantle_demo.mp4` (T4) + e2e_smoke 18+ step PASS + プレゼン ready |

## 8. T3 → T4 入出力契約 (sibling 連携 literal 設計、 ADR-302 reference)

T3 (Day-1 readiness、 完成度 100%) の literal 完成 API output:
- **IntegrationPlan** (IP-XXXXXXXXX、 100 日 plan root)
- **PlanNode** (PN-XXXXXX、 4 軸統合 task、 Day-N)
- **DependencyEdge** (DE-XXXXXX)
- **RiskScore** (RS-XXXXXX、 5 dim 0-100)
- **CommunicationKit** (CK-XXXXXX、 5 audience cascade)
- **JPDay1Pattern** (JPD1-XXXXXX、 5 軸 detector)

T4 が **入力として literal 流用**:
- T3 IntegrationPlan → T4 `CockpitProject` (CP-XXXXXX) inherit reference (1:1 mapping)
- T3 PlanNode → T4 KPI 監視 anchor (KpiSnapshot 時系列で達成評価)
- T3 RiskScore → T4 NextAction (NA-XXXXXX) 入力 weight
- T3 CommunicationKit → T4 NextAction audience mapping (5 audience cascade 同 pattern)
- T3 JPDay1Pattern → T4 RetentionRisk (RT-XXXXXX) + VendorContract (VC-XXXXXX) trigger

→ T3 と T4 は **MAIS Ontology 共通基盤** で literal 連携 (original proposal line 310 順守)。

## 9. 制約 (T1/T2/T3 と同)

- ✅ 無料 + クレカ不要範囲のみ
- ✅ 合成データ only (実 KPI / 実 vendor / 実 SaaS / 実 sentiment literal 不在)
- ✅ consumer laptop 完走前提 (doctrine: consumer-hw)
- ✅ ADR-300+ で T4 固有起草、 internal ADR 重複禁止
- ✅ T3 API output literal 流用設計

## 10. 受託 deploy 前 ★★★ 化 残 task (T1/T2/T3/T4 共通、 後日)

- TTS engine 1 週間 stability dry-run
- default model `22e8ed77-94fe-4ef2-871f-a86f94e9a579` literal 商用 license 確認
- 顧客案件 sandbox dry-run (doctrine: client-no-recovery)
- LangGraph + LlamaIndex + Apache Superset + HF Transformers の 2026 advisory 履歴 sweep (doctrine: external-source-audit)
- 大型案件 = external pentesting 推奨
