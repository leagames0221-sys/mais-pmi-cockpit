# MAIS — PMI Cockpit (100-day)

> **Day-1 → Day-100 Synergy KPI live cockpit** with KPI snapshot ingestion, AI driver insight, sentiment analysis, vendor / SaaS overlap detection, and LLM next-action recommendations.

[![tests](https://img.shields.io/badge/tests-96%20passing-brightgreen)]()
[![pip-audit](https://github.com/leagames0221-sys/mais-pmi-cockpit/actions/workflows/pip-audit.yml/badge.svg)](https://github.com/leagames0221-sys/mais-pmi-cockpit/actions/workflows/pip-audit.yml)
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 30-second pitch

The 100 days after deal close are where most M&A value is won or lost. Standard PMI dashboards show the KPI; they don't tell the operating partner what to do next week.

**MAIS PMI Cockpit** closes that loop:
- Synergy KPIs (cost / revenue / cash-gen / working capital + JP mid-market specific) on Apache Superset *(embed wrapper = placeholder; live JWT wiring is a 1-file swap path, see [PoC status](#poc-status-what-is-live-vs-deferred))*
- Isolation Forest + AnomSeer-pattern anomaly detection *(active)*
- LLM rewrites anomalies into ranked next-actions with audience mapping ("what to do, who to tell, by when") *(MockProvider in PoC; Claude/Gemini swap is a 1-file change)*
- Sentiment from Slack / Teams / engagement surveys (multilingual) *(token-heuristic mock active; HF Transformers + Slack/Teams connector active in Week 4)*
- Vendor / SaaS overlap detection (Docling parses contracts, 5-stage hybrid finds duplicates) *(active)*

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Day-1 Cockpit output (sibling input)       │
│  • IntegrationPlan + PlanNodes              │
│  • RiskScore + CommunicationKit             │
│  • JP Day-1 fit pattern hits                │
└────────────────────┬────────────────────────┘
                     │
                     ▼
       ┌─────────────────────────────────┐
       │  CockpitProject (CP-XXXXXX)     │
       │  • inherits IntegrationPlan     │
       └────────────────┬────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌────────────────┐ ┌──────────┐ ┌───────────────────┐
│ KPI snapshot   │ │ Sentiment│ │  Vendor / SaaS    │
│ ingestion      │ │ analysis │ │  overlap detect   │
│                │ │          │ │                   │
│ • cost         │ │ • Slack  │ │ • Docling parse   │
│ • revenue      │ │ • Teams  │ │ • 5-stage retrieve│
│ • cash-gen     │ │ • survey │ │ • JP fit pattern  │
│ • working cap  │ │          │ │                   │
└───────┬────────┘ └────┬─────┘ └─────────┬─────────┘
        │               │                 │
        └───────────────┼─────────────────┘
                        │
                        ▼
            ┌─────────────────────────┐
            │  Isolation Forest +     │
            │  AnomSeer pattern       │
            │  (anomaly detection)    │
            └────────────┬────────────┘
                         │
                         ▼
            ┌─────────────────────────┐
            │  LLM next-action        │
            │  recommender            │
            │  (Claude listwise CoT)  │
            │                         │
            │  Output: 5 ranked       │
            │  actions + audience     │
            │  mapping + citations    │
            └────────────┬────────────┘
                         │
                         ▼
            ┌─────────────────────────┐
            │  Apache Superset embed  │
            │  + KPI alert UI         │
            └─────────────────────────┘
```

---

## What's inside

| Capability | Implementation | PoC status |
|---|---|---|
| **Synergy KPI live dashboard** | Apache Superset 6.0+ embed + custom CSS wrapper for slate-and-amber brand | ⏳ embed wrapper placeholder (`about:blank` URL); JWT swap is 1-file (`src/dashboard/superset_embed.py`) |
| **Anomaly detection** | scikit-learn Isolation Forest + [AnomSeer 2026 pattern](https://openreview.net/forum?id=Jl0QHFcyCl) (MLLM grounding reasoning reinforcement) | ✅ active |
| **LLM next-action** | LLMProvider Protocol + Claude listwise Chain-of-Thought — 5 ranked actions + audience mapping | ⏳ MockProvider active (deterministic, no API key); Claude swap is 1-file (`src/llm/provider.py`) |
| **Driver insight** | 5-stage hybrid retrieval surfaces "KPI driver factor → cash-gen improvement hypothesis" with source citations | ✅ active (Week 3+ stack) |
| **Sentiment analysis** | HuggingFace Transformers (multilingual sentiment base) + Claude API for multi-axis interpretation | ⏳ token-heuristic mock active; transformers + LLM swap deferred to Week 4 (`src/sentiment/analyze_message.py`) |
| **Vendor / SaaS overlap** | Docling parses contracts; 5-stage hybrid + JP mid-market vendor consolidation pattern detector | ✅ active |
| **Vault Pattern** | Contact information (employee + vendor) Fernet-encrypted at rest | ✅ active |

---

## Tech stack

| Layer | Choice | PoC wiring |
|---|---|---|
| Dashboard | Apache Superset 6.0+ (Apache-2.0) — embedded SDK | ⏳ placeholder URL; JWT embed path defined in `superset_embed.py` |
| Anomaly | scikit-learn ≥ 1.4 (BSD-3) Isolation Forest | ✅ live |
| Sentiment | transformers ≥ 4.40 (Apache-2.0) multilingual | ⏳ optional import; mock heuristic is default until Week 4 |
| Orchestrator | LangGraph ≥ 1.2.0 (MIT) — CVE-2026-28277 fixed | ✅ live |
| Graph | NetworkX ≥ 3.x (BSD-3) | ✅ live |
| Citation infra | LlamaIndex core (MIT) | ✅ live |
| Retrieval | rank-bm25 + multilingual-e5-large + cross-encoder/ms-marco-MiniLM-L-12-v2 | ✅ live (Week 3 stack) |
| ANN | faiss-cpu (MIT) | ✅ live |
| Document parsing | docling (MIT) — for vendor contracts | ✅ live |
| Tabular | pandas ≥ 2.2 (BSD-3) | ✅ live |
| Web | FastAPI + uvicorn + Jinja2 (MIT) | ✅ live |
| Schema | Pydantic v2 (MIT) | ✅ live |
| LLM SDK | anthropic ≥ 0.100 (MIT) | ⏳ declared in `requirements-week1.txt`; not yet imported by code (MockProvider active) |
| Crypto | cryptography Fernet (Apache-2.0) | ✅ live |
| Tests | pytest (96 collected) | ✅ live |

---

## ID conventions

| Prefix | Entity |
|---|---|
| `CP-` | CockpitProject (inherits IntegrationPlan) |
| `KP-` | KpiDefinition |
| `KS-` | KpiSnapshot (time-series) |
| `DR-` | DriverInsight (KPI variation root cause) |
| `NA-` | NextAction (LLM-recommended, 5 ranked) |
| `SE-` | SentimentEvent |
| `VC-` | VendorContract |
| `SL-` | SaasLicense |
| `RT-` | RetentionRisk (0-100) |

---

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-week1.txt

# generate synthetic PMI cockpit data + ingest sibling Day-1 output
python -m src.data_gen.generate_synthetic_cockpit

# launch UI
uvicorn src.api.app:app --reload --port 8000
```

---

## Configuration (env)

```bash
ANTHROPIC_API_KEY=sk-ant-...           # required for LLM next-action
VAULT_KEY=<fernet key>                  # contact info vault
SESSION_SECRET=<token_urlsafe>          # FastAPI session
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

---

## PoC status — what is live vs deferred

This is a **PoC portfolio** demonstrating shape + interfaces. The architecture above is the target design. Current implementation status:

**✅ Live in PoC** (active code paths, deterministic, no external API needed):
- KPI snapshot ingestion + Isolation Forest anomaly detection
- 5-stage hybrid retrieval (BM25 + dense + cross-encoder rerank) for driver insight
- Vendor / SaaS overlap detection (Docling + JP mid-market patterns)
- Token-heuristic sentiment + topic tagging
- Fernet vault for contact information
- 96 pytest cases passing

**⏳ Deferred to integration phase** (1-file swap paths defined, contracts stable):
- LLM next-action — `MockProvider` returns deterministic templated outputs; `src/llm/provider.py` ships the `LLMProvider` Protocol with a single `default_provider()` swap point. `anthropic>=0.100` is pinned in `requirements-week1.txt` but no code imports it yet.
- Apache Superset embed — `src/dashboard/superset_embed.py` returns `about:blank#superset-embed-placeholder` until `SUPERSET_GUEST_TOKEN` is provided; the iframe URL builder + JWT spec is literal.
- HF Transformers multilingual sentiment — optional import; activated in Week 4 lock file (`requirements-week3.lock.txt` already pins `transformers==5.8.1` + `sentence-transformers==5.5.0`).
- Slack / Teams connectors — mocked; Week 4 Bot Framework / Slack API integration path defined.

**Rationale**: this scoping lets the repo demonstrate end-to-end shape + tests on a laptop without paid API keys. The 1-file swap pattern (Protocol abstraction) is itself the portfolio claim — adding real Claude / Superset / transformers does not require refactoring callers.

---

## Production deployment notes

- Real KPI / vendor / SaaS data → sandbox (Docker / WSL2 / Codespaces)
- Customer sandbox dry-run + 1-week stability before cutover
- Sweep 2026 advisories for LangGraph, LlamaIndex, Apache Superset, HuggingFace Transformers
- External penetration test recommended for large engagements
- Slack / Teams connectors are mocked in PoC; replace with real Bot Framework / Slack API integrations

---

## Sibling tools (M&A Intelligence Suite)

- [mais-deal-matching](https://github.com/leagames0221-sys/mais-deal-matching) — sourcing
- [mais-dd-workbench](https://github.com/leagames0221-sys/mais-dd-workbench) — DD
- [mais-day1-cockpit](https://github.com/leagames0221-sys/mais-day1-cockpit) — Day-1 readiness
- **[mais-pmi-cockpit](https://github.com/leagames0221-sys/mais-pmi-cockpit)** ← this repo (100-day PMI)
- [mais-pmi-knowledge-base](https://github.com/leagames0221-sys/mais-pmi-knowledge-base) — knowledge layer
- [mais-portfolio](https://github.com/leagames0221-sys/mais-portfolio) — overview

---

## License

MIT. See [LICENSE](LICENSE).
