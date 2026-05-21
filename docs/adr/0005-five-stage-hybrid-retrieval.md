# ADR-0005: Driver-insight + vendor-overlap retrieval — five-stage hybrid (BM25 + dense + cross-encoder + LLM rerank + citation engine)

## Status

Accepted (2026-05-22)

## Context

Two cockpit features need retrieval that goes beyond exact-match search:

1. **Driver insight** ([README "What's inside"](../../README.md#whats-inside)) — surfaces "this KPI movement is plausibly explained by …" hypotheses by retrieving similar past synergy-KPI snapshot patterns and their attributed driver factors. Output: candidate explanations with `[1]/[2]` citations back to the source snapshot or workstream note.
2. **Vendor / SaaS overlap detection** ([README "What's inside"](../../README.md#whats-inside)) — Docling parses vendor contracts and SaaS licenses, then retrieval finds duplicate or overlapping vendor relationships across the merged entity's combined contract corpus.

Both features need:

- High recall on the first stage over a small-to-medium corpus (hundreds of contracts, hundreds of KPI snapshots per project).
- High precision after rerank (the operating partner sees a top-5 list; noise drowns the signal).
- Citation link-back to source artefact IDs (`KS-` / `VC-` / `SL-` per [README "ID conventions"](../../README.md#id-conventions)).
- Japanese + English bilingual handling (vendor contracts are predominantly Japanese for JP mid-market integrations; SaaS licenses predominantly English).
- Run in the default $0 / no-credit-card path.

## Decision

A five-stage retrieval pipeline shared between driver-insight and vendor-overlap, with stage-specific role:

| Stage | Component | License | Role |
| --- | --- | --- | --- |
| 1 — lexical recall | `rank-bm25` | Apache-2.0 | Tokenized BM25; recovers exact-term anchors (vendor codenames, KPI dimension labels). |
| 2 — dense recall | `multilingual-e5-large` via `sentence-transformers`, served from `faiss-cpu` | MIT + MIT | Semantic recall; handles JP↔EN paraphrase and synonym variation in contract wording. |
| 3 — cross-encoder rerank | `cross-encoder/ms-marco-MiniLM-L-12-v2` | Apache-2.0 | Pairwise (query, candidate) scoring; filters stage-1+2 union by domain-textual relevance. |
| 4 — LLM listwise CoT rerank | [`LLMProvider` Protocol](0002-llm-provider-protocol-3tier-swap.md) | MIT | Listwise chain-of-thought rerank for the top-K of stage 3. Used only when tier 2 / 3 LLM is active; skipped under the MockProvider default. |
| 5 — citation-grounded retrieval | `LlamaIndex CitationQueryEngine` | MIT | Wraps the final ranking in a citation-array shape; `[1]/[2]` markers carry source IDs (`KS-` / `VC-` / `SL-`). |

The pipeline is invoked from the orchestrator LangGraph at the driver-insight node and the vendor-overlap node, with the same stage shape but feature-specific query construction.

## Why this composition (and not single-stage)

### Stage 1 + 2 together

BM25 alone misses paraphrase ("post-merger integration" vs "PMI"); dense alone misses exact-term anchors (vendor codenames, KPI labels, ISIN codes). Their union recovers both. The argument is the same as in the sibling repo's retrieval ADR ([`mais-pmi-knowledge-base ADR-0003`](https://github.com/leagames0221-sys/mais-pmi-knowledge-base/blob/main/docs/adr/0003-five-stage-hybrid-retrieval.md)).

### Cross-encoder before LLM rerank

The cross-encoder filter is ~100× cheaper per (query, candidate) pair than an LLM call; reserving the LLM for listwise rerank over the cross-encoder top-K is the cost / quality balance.

### Stage 5 last

LlamaIndex CitationQueryEngine bundles answer-synthesis with citation-array construction; running it last preserves the rerank order.

## Alternatives considered

### Reciprocal Rank Fusion (RRF) without cross-encoder rerank (rejected)

- **Pros**: lighter; RRF is a well-known fusion baseline.
- **Cons**: RRF only reorders the union of stages 1+2; no per-(query, candidate) semantic signal. Empirically, RRF top-5 on the vendor-contract corpus included off-domain candidates the cross-encoder filtered out.
- **Why rejected**: precision at K=5 is the surface — a noisier top-5 directly degrades the operating partner's signal.

### Dense only (rejected)

- **Pros**: simpler pipeline.
- **Cons**: misses vendor-codename and KPI-label exact-term anchors; dense-only recall has known weaknesses on rare entities.
- **Why rejected**: stage 1 lexical anchor is load-bearing.

### BM25 only (rejected)

- **Pros**: deterministic, no model load.
- **Cons**: misses paraphrase + JP↔EN cross-language matching.
- **Why rejected**: insufficient recall on bilingual contracts.

### Cohere Rerank / paid managed rerank API (rejected)

- **Pros**: high reranking quality with no local model overhead.
- **Cons**: paid managed service requires credit card; violates [Selected under](../../README.md#selected-under) zero-CC default.
- **Why rejected**: incompatible with the default path. Tier 3 customer-paid swap is available via [ADR-0002](0002-llm-provider-protocol-3tier-swap.md) but is not the default.

### LLM-only retrieval (let the LLM read the whole contract corpus per query) (rejected)

- **Pros**: simplest structurally.
- **Cons**: blows context window beyond a few dozen contracts; no citation link-back; cost scales linearly with corpus per query.
- **Why rejected**: does not scale; defeats citation-link-back.

## Consequences

### Positive

- Same retrieval stack used in two features (driver insight + vendor overlap); test fixtures, model load, ANN index are shared.
- Degrades gracefully — when the tier-2/3 LLM is offline, stages 1–3 + 5 still produce citation-grounded retrieval (stage 4 skipped). This is what makes the local-LLM-default constraint hold without losing the feature.
- Citation chunk IDs (`KS-` / `VC-` / `SL-`) flow through the schema and arrive intact at the cockpit response.

### Negative

- Cold start loads three model sets (e5 + MS-MARCO cross-encoder + Ollama backend if tier-2); amortized by long-running uvicorn process.
- Stage 4 LLM rerank quality is bounded by the chosen `LLMProvider` tier; MockProvider's rerank is a no-op pass-through.

### Reversibility

Each stage is behind an interface in [src/retrieval/](../../src/retrieval/). Component swaps inside a stage are local edits. Dropping a stage (e.g., skipping the cross-encoder on low-RAM customer deployments) is a config switch.

## References

- [Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond"](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf)
- [Wang et al., "Multilingual E5 Text Embeddings"](https://arxiv.org/abs/2402.05672)
- [MS MARCO Cross-Encoders](https://www.sbert.net/docs/cross_encoder/pretrained_models.html)
- [LlamaIndex CitationQueryEngine](https://docs.llamaindex.ai/en/stable/examples/query_engine/citation_query_engine/)
- [Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — RRF alternative considered
- Code: [src/retrieval/](../../src/retrieval/), [src/driver_insight/](../../src/driver_insight/), [src/vendor_overlap/](../../src/vendor_overlap/)
