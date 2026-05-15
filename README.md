# MAIS — PMI Cockpit (100-day)

> **M&A Intelligence Suite (MAIS)** の 4 番目のツール。
> M&A 成約後 **Day-1 → Day-100 期間の Synergy KPI live cockpit** を
> **KPI snapshot ingestion + AI driver insight + sentiment 分析 + vendor / SaaS 統合機会自動抽出 + LLM next action 推奨** で自動化する PoC。

[![pip-audit](https://img.shields.io/badge/pip--audit-0%20CVE-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-PoC%20demo-lightgrey)]()

---

## 何ができるか

| 機能 | 内容 |
|---|---|
| **Synergy KPI live dashboard** | cost / revenue / cash gen / working capital + 中堅日本企業特化 KPI を Apache Superset embed で live 化 |
| **AI driver insight** | 売掛 / 買掛 / 在庫 / 経費から cash gen 改善余地を 5-stage hybrid pipeline で AI surface |
| **Sentiment 分析** | 退職率 / engagement の sentiment (Slack / Teams / アンケート mock connector) |
| **Vendor / SaaS overlap detect** | 重複 vendor 契約 / 価格交渉余地 / SaaS license 統合機会を Docling + 5-stage hybrid + 中堅 pattern detector で自動抽出 |
| **LLM next action 推奨** | KPI falter 時に AI が「来週何をすべきか」level で 5 候補 ranked + audience mapping |
| **Anomaly detection** | scikit-learn Isolation Forest + AnomSeer 2026 pattern (MLLM reinforce grounding reasoning) |
| **黒×金 brand UI** | FastAPI + Jinja2 + Apache Superset embed + KPI alert |

---

## 想定ユースケース

- **M&A advisory firm** の post-deal team が cockpit を顧客 dashboard として deploy
- **コーポレート M&A 部門** の 100-day 進捗管理
- **PE / VC** の portfolio company KPI live monitoring

---

## tech stack

| 層 | 採用 | source |
|---|---|---|
| KPI live dashboard | **Apache Superset 6.0+** embed + 黒×金 brand custom CSS wrapper | https://superset.apache.org/ |
| Anomaly detection | **scikit-learn Isolation Forest** + **AnomSeer 2026 pattern** | https://openreview.net/forum?id=Jl0QHFcyCl |
| LLM next action | LLMProvider Protocol + Claude listwise CoT (5 候補 ranked + audience mapping) | (本 suite 共通) |
| Driver insight | 5-stage hybrid (BM25 + dense + RRF + cross-encoder + LLM listwise) | (本 suite 共通) |
| Sentiment 分析 | HuggingFace Transformers (multilingual sentiment) + Claude API LLM 多軸分析 + Slack/Teams mock connector | https://huggingface.co/transformers |
| Vendor / SaaS overlap | Docling (Excel/Word/PPT/PDF parser) + 5-stage hybrid + 中堅日本企業特有 vendor 統合 pattern detector | (sibling tool 共通) |
| Orchestrator | **LangGraph 1.2.0+** (CVE-2026-28277 元削除済) | https://www.langchain.com/langgraph |
| Web UI | FastAPI + uvicorn + Jinja2 + Superset embed wrapper | MIT |
| Security | python-ml-stack 5-layer 防御 + Vault Pattern (担当者連絡先 + vendor 連絡先 vault) | (本 suite 共通) |

---

## 期待効果

- **PMI 案件管理工数の reduction** ★★
- **cash gen の improvement** ★★
- **2026 industry benchmark**: post-deal AI 採用率 **2024 年 18% → 2026 年 27%** (top-tier PMI advisory firm research)

---

## Day-1 ↔ PMI Cockpit 入出力契約 (sibling tool 連携)

Day-1 Cockpit (mais-day1-cockpit) の API output:
- **IntegrationPlan** (IP-XXXXXX、 100 日 plan root)
- **PlanNode** (PN-XXXXXX、 4 軸統合 task: organization / process / system / culture、 Day 1/30/100)
- **DependencyEdge** (DE-XXXXXX、 NetworkX dep graph edge)
- **RiskScore** (RS-XXXXXX、 5 dim 0-100 score)
- **CommunicationKit** (CK-XXXXXX、 5 audience cascade)
- **JP Day-1 fit pattern hits** (5 軸 detector: 組合対応 / 取引銀行折衝 / 同族統合 / 商習慣 / 取引慣行)

PMI Cockpit が **入力として literal 流用**:
- IntegrationPlan → CockpitProject (CP-XXXXXX) inherit reference (1:1 mapping、 Day-100 終了後 = 100 日 cockpit start)
- PlanNode (Day-1/30/100 task) → KPI 監視 anchor (Day-1 plan 達成評価)
- RiskScore → NextAction (NA-XXXXXX) 入力 weight
- CommunicationKit → NextAction audience mapping
- JP fit hits → RetentionRisk (RT-XXXXXX) + VendorContract (VC-XXXXXX) trigger

---

## 4-Week roadmap (PoC scope)

| Week | scope | deliverable |
|---|---|---|
| **Week 0** | Discovery → Requirements → Design → Tasks、 GitHub PRIVATE repo + drift CI install、 採用 OSS audit gate | scaffold + design doc |
| **Week 1** | 合成 PMI cockpit data 生成 (KpiDefinition + KpiSnapshot 時系列 + VendorContract / SaaSLicense 各 5 件、 中堅日本企業 KPI benchmark 入り) + Day-1 output ingestion + LangGraph state graph 設計 | 1 commandlet で Day-1 output → CockpitProject literal 動作 |
| **Week 2** | KpiSnapshot ingestion + DriverInsight 5-stage hybrid 抽出 + NextAction recommender (Isolation Forest + Claude LLM CoT) | KPI anomaly detect + next action surface smoke |
| **Week 3** | SentimentEvent (HF Transformers + Claude、 Slack/Teams/アンケート mock connector) + VendorContract / SaaSLicense overlap detect + Citation link back | 5 audience cascade NextAction + vendor 統合機会 surface |
| **Week 4** | FastAPI/Jinja UI (Apache Superset embed + KPI alert + 黒×金 brand) + Vault Pattern + e2e_smoke | 実機 demo (Cloudflare quick tunnel) |

---

## 環境設定

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-week0.txt
```

### 必須 env var

```bash
ANTHROPIC_API_KEY=sk-ant-...           # Week 2+ で active
VAULT_KEY=<fernet key>                  # vault PII 暗号化
SESSION_SECRET=<token_urlsafe>          # FastAPI session
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

---

## 制約 (PoC scope)

- **無料 + クレカ不要範囲** で完走
- **consumer laptop** で完走前提
- **合成 PMI cockpit data only** — 実 KPI / 実 vendor / 実 SaaS / 実 sentiment 一切扱わない
- **vendor lock-in ZERO**

---

## 移植段階の追加要件

- 実 KPI / 実 vendor 投入時 = sandbox (Docker / WSL2) + 顧客 sandbox dry-run + 1 週間 stability
- LangGraph + LlamaIndex + Apache Superset + HF Transformers の 2026 advisory 履歴 sweep
- 大型案件 = external pentesting 推奨

---

## related tools (M&A Intelligence Suite)

- **mais-deal-matching** — sourcing stage
- **mais-dd-workbench** — Due Diligence automation
- **mais-day1-cockpit** — Day-1 readiness
- **mais-pmi-cockpit** ← 本リポジトリ (100-day PMI dashboard)
- **mais-pmi-knowledge-base** — knowledge layer (全 tool 共通参照)

---

## license

PoC demo — 設計思想 + コード構造を portfolio 公開、 合成データのみ含む。 商用 deploy は別途相談。
