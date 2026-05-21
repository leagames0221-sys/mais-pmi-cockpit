# ADR-0001: Stack choice — Python 3.11+ + FastAPI + LangGraph + Pydantic v2

## Status

Accepted (2026-05-22)

## Context

`mais-pmi-cockpit` is the 100-day post-merger integration cockpit member of the MAIS suite — a live dashboard that ingests synergy KPI snapshots, runs anomaly detection (Isolation Forest + AnomSeer pattern), produces LLM-driven next-action recommendations, parses vendor / SaaS contracts (Docling), analyzes sentiment from Slack / Teams / surveys, and embeds an Apache Superset visualization layer. Five constraints frame the stack:

1. **ML / NLP ecosystem fit** — scikit-learn (Isolation Forest), HuggingFace Transformers (sentiment), Docling, LlamaIndex, sentence-transformers, faiss-cpu are all Python-native.
2. **Stateful orchestrator** — KPI ingestion → anomaly detection → driver insight → next-action recommendation is a multi-node stateful pipeline; LangGraph fits.
3. **Type-safe boundary contracts** — `CockpitProject`, `KpiSnapshot`, `NextAction`, `RetentionRisk`, `VendorContract` flow across modules and ID-prefixed entities; Pydantic v2 carries them.
4. **Free + no-credit-card default** — see [Selected under](../../README.md#selected-under).
5. **Dashboard embed surface** — Apache Superset is Python-native (Flask under the hood); its embedded SDK is the closest off-the-shelf primitive for "consultant-grade live dashboard with JWT-gated embed."

## Decision

| Layer | Selection | Free + no-CC verified |
| --- | --- | --- |
| Language | Python 3.11+ | ✅ |
| Web framework | FastAPI (MIT) | ✅ |
| ASGI server | uvicorn (BSD-3) | ✅ |
| Templating | Jinja2 (BSD-3) | ✅ |
| Schema | Pydantic v2 (MIT) | ✅ |
| Orchestrator | LangGraph 1.2.0+ (MIT) | ✅ |
| Tabular | pandas 2.2+ (BSD-3) | ✅ |
| Anomaly detection | scikit-learn 1.4+ Isolation Forest (BSD-3) — see [ADR-0003](0003-anomaly-detection.md) | ✅ |
| Sentiment | HuggingFace Transformers 4.40+ (Apache-2.0) | ✅ |
| Document parsing | Docling (MIT) | ✅ |
| Citation infra | LlamaIndex core (MIT) | ✅ |
| Retrieval | rank-bm25 + multilingual-e5-large + cross-encoder MS-MARCO — see [ADR-0005](0005-five-stage-hybrid-retrieval.md) | ✅ |
| ANN | faiss-cpu (MIT) | ✅ |
| Dashboard | Apache Superset 6.0+ embedded SDK (Apache-2.0) — see [ADR-0004](0004-superset-embed.md) | ✅ |
| LLM provider | `LLMProvider` Protocol — see [ADR-0002](0002-llm-provider-protocol-3tier-swap.md) | ✅ |
| Crypto | cryptography Fernet (Apache-2.0) | ✅ |
| Tests | pytest (96 collected) | ✅ |

## Rationale

The ML / NLP ecosystem fit argument is the same as in the sibling repo (see [mais-pmi-knowledge-base ADR-0001](https://github.com/leagames0221-sys/mais-pmi-knowledge-base/blob/main/docs/adr/0001-stack-choice.md)). Cockpit-specific drivers:

- **scikit-learn Isolation Forest** is the canonical lightweight anomaly detector for tabular KPI time-series; no language other than Python ships it as a first-class library.
- **Apache Superset** is the only mature OSS BI dashboard with a tested JWT-embed SDK and a permissive license; it is Python-native (Flask backend).
- **LangGraph** carries the stateful KPI → anomaly → next-action pipeline as a typed DAG; Python is its primary runtime.

## Alternatives considered

### Node.js / TypeScript (rejected)

- **Pros**: shared stack with the security-tool sibling repos (mcp-guard / sbom-pilot / agentic-appsec-pilot).
- **Cons**: no first-class binding for scikit-learn (Isolation Forest would need a pyo3 or subprocess wrap), Apache Superset embed assumes Python-side identity, HF Transformers JS port lags. LlamaIndex.ts is feature-incomplete vs the Python original.
- **Why rejected**: rebinding the entire anomaly + sentiment + retrieval stack exceeds the value of stack uniformity.

### Go (rejected)

- **Pros**: single-binary deploy, strong concurrency.
- **Cons**: nearly the entire ML / NLP / dashboard stack would need reimplementation. No Go-native Isolation Forest at production maturity in 2026.
- **Why rejected**: ecosystem-fit argument as above, more severe.

### Python + Django / Flask without FastAPI (rejected)

- **Pros**: simpler frameworks; Django's admin is useful.
- **Cons**: FastAPI's Pydantic-native request/response model removes a serialization layer; Apache Superset already runs on Flask, but the cockpit's API surface is not Superset's — coexistence is fine.
- **Why rejected**: FastAPI strictly dominates given the Pydantic v2 boundary-contract decision.

## Consequences

### Positive

- All ML/NLP primitives used as-published; no FFI / subprocess overhead.
- Pydantic v2 boundaries flow from HTTP request through orchestrator nodes to anomaly detector + LLM provider, removing glue layers.
- The 3-tier LLM swap (see [ADR-0002](0002-llm-provider-protocol-3tier-swap.md)) is one Protocol with three implementations behind a single `default_provider()` switch.

### Negative

- Not single-binary distribution; customer deploy uses containers (Docker / Podman / WSL2) — see [Production deployment notes](../../README.md#production-deployment-notes).
- Cold start latency from model loading; amortized by long-running uvicorn.

### Reversibility

The Pydantic schemas in `src/schema/types.py` are language-agnostic in shape; a language pivot would require rebinding the entire ML stack, which is the original cost argument.

## References

- [Python 3.11 release notes](https://docs.python.org/3/whatsnew/3.11.html)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [LangGraph documentation](https://langchain-ai.github.io/langgraph/)
- [scikit-learn Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Apache Superset documentation](https://superset.apache.org/docs/intro)
- [Docling project](https://github.com/docling-project/docling)
- [README — Tech stack](../../README.md#tech-stack)
