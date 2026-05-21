# MAIS — PMI Cockpit (100-day)

> **Day-1 → Day-100 Synergy KPI live cockpit** with KPI snapshot ingestion, AI driver insight, sentiment analysis, vendor / SaaS overlap detection, and LLM next-action recommendations.

[![tests](https://img.shields.io/badge/tests-96%20passing-brightgreen)]()
[![pip-audit](https://github.com/leagames0221-sys/mais-pmi-cockpit/actions/workflows/pip-audit.yml/badge.svg)](https://github.com/leagames0221-sys/mais-pmi-cockpit/actions/workflows/pip-audit.yml)
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Constraint: zero credit card](https://img.shields.io/badge/Constraint-zero%20credit%20card-blue)](#selected-under)
[![Constraint: local LLM (default)](https://img.shields.io/badge/Constraint-local%20LLM%20%28default%29-blue)](#selected-under)
[![Constraint: free / OSS only](https://img.shields.io/badge/Constraint-free%20%2F%20OSS%20only-blue)](#selected-under)
[![Constraint: security defense-in-depth](https://img.shields.io/badge/Constraint-security%20defense--in--depth-blue)](#selected-under)

---

## Selected under

> **The 4-constraint set** (applied across the full portfolio — verified consistent across all 11 portfolio repos):
>
> 1. **Zero credit card** — no paid API / cloud service required for the default path. A reviewer can clone, install, and run with $0 spend and no payment method on file.
> 2. **Local LLM (default)** — when an LLM is involved, the default path is local (Ollama / similar) or deterministic mock. Paid cloud LLM is opt-in via env var, never default.
> 3. **Free / OSS only** — every runtime dependency is permissively-licensed open source (MIT / Apache-2.0 / BSD-3); no proprietary SDK at build time.
> 4. **Security defense-in-depth** — secrets-scan CI + `.gitignore` hardening, encrypted-at-rest where PII is involved, append-only audit logging where applicable, dep-vuln gating (`pip-audit` / `pnpm audit`), paid-API constructor gate where applicable.

This repo specifically demonstrates: 100-day PMI cockpit with Fernet-vaulted contact info, MockProvider LLM default (Claude/Gemini/Ollama swap = 1-file change), and the [Configuration (env)](#configuration-env) section's 3-tier swap path showing exactly where paid APIs enter the system (tier 3 only).

---

## 🎬 Demo walkthrough (2-minute narrated video)

End-to-end demo of the cockpit — landing → 5 feature panels (Synergy KPI / Driver Insight / Next Action / Retention Risk / Vendor Overlap) → POST /generate → cockpit_view scrolls through CockpitProject meta, KPI 4-dim, KpiSnapshot time-series, NextAction recommendations, RetentionRisk + Sentiment, VendorContract / SaasLicense overlap → dashboard view. Japanese narration by [AivisSpeech](https://aivis-project.com/) (まお おちついた, Style-Bert-VITS2), 1920×1080 H.264.

> [▶️ **mais_pmi_cockpit_demo.mp4**](out_video/mais_pmi_cockpit_demo.mp4) — 119.10 s · 8.8 MB · 16 scenes with burned-in SRT subtitles.

<video src="out_video/mais_pmi_cockpit_demo.mp4" controls width="100%"></video>

**Reproducible pipeline** ([scripts/produce_video.py](scripts/produce_video.py), [requirements-video.txt](requirements-video.txt)) — action-then-narration timing model: each scene measures Playwright action elapsed time then plays narration on the settled destination page, so audio and video stay synchronized even when retrieval / DB operations take variable wall-clock. All synthetic data, zero real PII, zero paid API.

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

## Why this is distinct (existing alternatives + delta)

Standard 100-day PMI tooling splits into two camps in 2026, and neither closes the "what next" loop the operating partner actually owns:

- **BI-style KPI dashboards** (Power BI / Tableau / Looker) display synergy KPIs as charts but stop at visualization — they require a human consultant to read the chart and decide the action.
- **M&A integration platforms** (Devensoft / Midaxo / DealRoom) track integration workstreams + RACI but treat KPIs as static fields, not as anomaly signals feeding next-action recommendations.

MAIS PMI Cockpit closes the loop: Isolation Forest + AnomSeer-pattern anomaly detection on the synergy KPIs, then an LLM rewrites anomalies into ranked next-actions with audience mapping (what to do, who to tell, by when).

**Target user**: PE operating partners + post-merger integration consultants who own the 100-day integration plan and need actionable next-week guidance, not just KPI visualization.

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
| LLM (PoC) | MockProvider (deterministic templated) | ✅ active — zero cost, zero key, runs offline |
| LLM (local swap) | Ollama (e.g. qwen2.5:7b) — env-gated via `LLM_PROVIDER=ollama` | ⏳ swap path defined; still zero cost, still no credit card |
| LLM (production swap) | anthropic ≥ 0.100 (MIT) — env-gated via `LLM_PROVIDER=claude` | ⏳ declared in `requirements-week1.txt`; only place a paid API key enters the system |
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

The cockpit ships with a **3-tier LLM swap path**. Pick the tier that matches your environment — no env edits are needed for tier 1 (PoC default).

### Tier 1 — PoC default (zero cost, zero credit card, runs offline)

```bash
# No LLM env vars required. MockProvider is the default; outputs are deterministic
# templated next-actions so the full UI + Isolation Forest + Superset placeholder
# all work without any external API call.
VAULT_KEY=<fernet key>                  # contact info vault (always required)
SESSION_SECRET=<token_urlsafe>          # FastAPI session (always required)
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

### Tier 2 — Local LLM swap (still zero cost, zero credit card; uses your own GPU/CPU)

For developers / customers who want real LLM next-actions without paid APIs. Requires [Ollama](https://ollama.com/) running locally with a model pulled (e.g. `ollama pull qwen2.5:7b`).

```bash
LLM_PROVIDER=ollama                     # switches default_provider() to Ollama (1-file swap point: src/llm/provider.py)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama default
OLLAMA_MODEL=qwen2.5:7b                 # any local model the cockpit prompt format supports
# ... plus the always-required vars from tier 1
```

### Tier 3 — Customer / production swap (paid API; the only tier that touches credit-card-backed services)

For customer deployments where multi-tenant scale or hosted-model SLA is required. **This is the only place credit-card-backed services enter the system** — paste the customer's key here and nothing else changes.

```bash
LLM_PROVIDER=claude                     # or "gemini" / future provider
ANTHROPIC_API_KEY=sk-ant-...            # paste customer's key here (PoC + tier 2 never read this var)
ANTHROPIC_MODEL=claude-sonnet-4-6       # whichever model the engagement contract specifies
# ... plus the always-required vars from tier 1
```

The swap point is literally one function — `default_provider()` in `src/llm/provider.py` (currently raises `NotImplementedError` for non-mock until tier 2/3 providers land per the Week 2+ phase plan). Callers (`src/anomaly/`, `src/next_action/`, etc.) never import a specific SDK — they import the `LLMProvider` Protocol, so wiring real Claude or Ollama is one file changed, zero refactor.

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

## What this exercise validated

Three things turned out to be worth defending in this PoC.

**First, the 1-file LLM swap pattern is the portfolio claim, not the LLM choice itself.** The cockpit ships with three concrete swap tiers (MockProvider for offline PoC, Ollama for local-LLM zero-CC, Claude / Gemini for customer production) and a single `default_provider()` function in `src/llm/provider.py` carries all three. Callers under `src/anomaly/` and `src/next_action/` never import a specific SDK — they import the `LLMProvider` Protocol, so wiring a real provider is one file changed, zero refactor across the rest of the codebase. This is the architectural commitment behind the "customer paid API plugs in here" claim in Tier 3 of the Configuration section.

**Second, the cockpit is shaped by the PMI consultant's workflow, not by tooling availability.** The Architecture diagram traces synergy KPI ingestion through anomaly detection → driver insight → ranked next-action with audience mapping. Each output entity carries an ID prefix (`CP-` / `KP-` / `KS-` / `DR-` / `NA-` / `RT-`) that mirrors the consultant's report structure, so a senior PMI partner can read the cockpit top-down without learning a new vocabulary. The Apache Superset embed is the visualization layer the customer typically already has; swapping to a different dashboard tool is documented as a placeholder URL → JWT swap path.

**Third, the PoC stops where the maintained alternatives start.** Power BI / Tableau / Looker remain the right call for static KPI visualization. Devensoft / Midaxo / DealRoom remain the right call for integration-workstream management. What MAIS PMI Cockpit adds is the anomaly-detection-to-action loop on top of synergy KPIs — wired and tested at 96 pytest cases against synthetic PMI data, runnable on a consumer laptop with zero monthly cost. The PoC status section above is explicit about which integration points (Superset embed, Claude swap, HF Transformers sentiment) are live versus deferred.

---

## Production deployment notes

- Real KPI / vendor / SaaS data → sandbox (Docker / WSL2 / Codespaces)
- Customer sandbox dry-run + 1-week stability before cutover
- Sweep 2026 advisories for LangGraph, LlamaIndex, Apache Superset, HuggingFace Transformers
- External penetration test recommended for large engagements
- Slack / Teams connectors are mocked in PoC; replace with real Bot Framework / Slack API integrations

---

## Design history (ADR set)

Architecture decisions for this repo are recorded under [`docs/adr/`](docs/adr/) using the Nygard pattern (Context / Decision / Alternatives considered / Consequences / References). The five load-bearing decisions are:

- [ADR-0001 — Stack choice (Python 3.11+ + FastAPI + LangGraph + Pydantic v2)](docs/adr/0001-stack-choice.md)
- [ADR-0002 — LLMProvider Protocol 3-tier swap (Mock / Ollama-local / paid API)](docs/adr/0002-llm-provider-protocol-3tier-swap.md)
- [ADR-0003 — Anomaly detection: Isolation Forest + AnomSeer 2026 pattern](docs/adr/0003-anomaly-detection.md)
- [ADR-0004 — Dashboard: Apache Superset embedded SDK (vs Power BI / Tableau / Metabase)](docs/adr/0004-superset-embed.md)
- [ADR-0005 — Driver-insight + vendor-overlap five-stage hybrid retrieval](docs/adr/0005-five-stage-hybrid-retrieval.md)

Each ADR records the alternatives considered (with pros / cons) and the consequences (positive + negative + reversibility), so the design path is replayable end-to-end.

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
