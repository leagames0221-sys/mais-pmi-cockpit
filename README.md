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
- Synergy KPIs (cost / revenue / cash-gen / working capital + JP mid-market specific) on Apache Superset
- Isolation Forest + AnomSeer-pattern anomaly detection
- LLM rewrites anomalies into ranked next-actions with audience mapping ("what to do, who to tell, by when")
- Sentiment from Slack / Teams / engagement surveys (multilingual)
- Vendor / SaaS overlap detection (Docling parses contracts, 5-stage hybrid finds duplicates)

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

| Capability | Implementation |
|---|---|
| **Synergy KPI live dashboard** | Apache Superset 6.0+ embed + custom CSS wrapper for slate-and-amber brand |
| **Anomaly detection** | scikit-learn Isolation Forest + [AnomSeer 2026 pattern](https://openreview.net/forum?id=Jl0QHFcyCl) (MLLM grounding reasoning reinforcement) |
| **LLM next-action** | LLMProvider Protocol + Claude listwise Chain-of-Thought — 5 ranked actions + audience mapping |
| **Driver insight** | 5-stage hybrid retrieval surfaces "KPI driver factor → cash-gen improvement hypothesis" with source citations |
| **Sentiment analysis** | HuggingFace Transformers (multilingual sentiment base) + Claude API for multi-axis interpretation |
| **Vendor / SaaS overlap** | Docling parses contracts; 5-stage hybrid + JP mid-market vendor consolidation pattern detector |
| **Vault Pattern** | Contact information (employee + vendor) Fernet-encrypted at rest |

---

## Tech stack

| Layer | Choice |
|---|---|
| Dashboard | Apache Superset 6.0+ (Apache-2.0) — embedded SDK |
| Anomaly | scikit-learn ≥ 1.4 (BSD-3) Isolation Forest |
| Sentiment | transformers ≥ 4.40 (Apache-2.0) multilingual |
| Orchestrator | LangGraph ≥ 1.2.0 (MIT) — CVE-2026-28277 fixed |
| Graph | NetworkX ≥ 3.x (BSD-3) |
| Citation infra | LlamaIndex core (MIT) |
| Retrieval | rank-bm25 + multilingual-e5-large + cross-encoder/ms-marco-MiniLM-L-12-v2 |
| ANN | faiss-cpu (MIT) |
| Document parsing | docling (MIT) — for vendor contracts |
| Tabular | pandas ≥ 2.2 (BSD-3) |
| Web | FastAPI + uvicorn + Jinja2 (MIT) |
| Schema | Pydantic v2 (MIT) |
| Crypto | cryptography Fernet (Apache-2.0) |
| Tests | pytest (96 collected) |

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
