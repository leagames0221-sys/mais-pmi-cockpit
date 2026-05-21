# ADR-0002: LLMProvider Protocol — 3-tier swap (Mock / Ollama-local / paid API)

## Status

Accepted (2026-05-22)

## Context

The cockpit's value claim in [README "What this exercise validated"](../../README.md#what-this-exercise-validated) is that *the 1-file LLM swap pattern is the portfolio claim, not the LLM choice itself*. A PoC reviewer needs to verify:

1. The PoC runs end-to-end with no API key and no internet (so the [Selected under](../../README.md#selected-under) "zero credit card" + "local LLM (default)" constraint pair literally hold for the default code path).
2. A customer can plug in a paid Claude / Gemini / OpenAI key in exactly one place, with no refactor across callers.
3. An intermediate operator can run a local Ollama model for self-hosted PoC realism without a paid key.

The shape of this swap — where it sits, what callers depend on, what gets re-imported when swapped — is the load-bearing architectural decision.

## Decision

A single `LLMProvider` Python `Protocol` ([src/llm/provider.py](../../src/llm/provider.py)) carries three concrete implementations behind a single `default_provider()` factory. Callers (`src/anomaly/`, `src/next_action/`, `src/sentiment/`, `src/driver_insight/`) import only the Protocol — never a concrete SDK.

| Tier | Provider | Env trigger | Cost / surface |
| --- | --- | --- | --- |
| **1 — PoC default** | `MockProvider` (deterministic templated outputs) | None (default) | Zero cost, zero credit card, runs offline |
| **2 — Local LLM swap** | `OllamaProvider` (e.g. `qwen2.5:7b`) | `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL` + `OLLAMA_MODEL` | Still zero cost, still no credit card, uses customer's GPU/CPU |
| **3 — Customer / production swap** | `ClaudeProvider` / `GeminiProvider` | `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` | Only tier that touches credit-card-backed services |

The factory contract: `default_provider()` reads `LLM_PROVIDER` (default `mock`) and returns the matching implementation. Callers do `provider = default_provider()` once and then `provider.generate(...)` everywhere. SDK imports (`import anthropic`, `import ollama`) live inside the concrete provider class — they never leak into business-logic modules.

## Why a Protocol and not an abstract base class

Python 3.8+ `typing.Protocol` is structural — any class with `generate(...)` and `count_tokens(...)` methods satisfies it without inheritance. This means mock providers in tests can be one-off `class _Stub:` declarations rather than ABC subclasses; the test friction collapses.

## Alternatives considered

### Single hardcoded provider (Claude / Anthropic SDK only) (rejected)

- **Pros**: simplest; no abstraction layer; production-ready output quality from day one.
- **Cons**: forces every PoC reviewer to procure an Anthropic key + register a credit card to exercise the cockpit; violates the [Selected under](../../README.md#selected-under) zero-credit-card default; makes the demo video impossible without a sponsored key.
- **Why rejected**: defeats the portfolio's defining constraint.

### LangChain `BaseLLM` / `BaseChatModel` (rejected)

- **Pros**: industry-standard abstraction; LangGraph integrates natively.
- **Cons**: LangChain's `BaseLLM` ships with assumed token-counting / streaming / message-formatting semantics that vary across LangChain releases (1.0 → 2.0 broke chat-model interfaces). Pinning LangChain to a specific minor is a stability cost. Also, LangChain's mock provider depends on `langchain-core` ≥ 0.3 which pulls in 30+ transitive packages.
- **Why rejected**: too much surface area for a 3-tier swap. The Protocol with 2 methods is sufficient.

### `litellm` (LLM-provider-routing library) (rejected)

- **Pros**: unifies 100+ providers behind one API; well-maintained.
- **Cons**: pulls a heavyweight dependency tree (HTTP clients, retry libraries, multiple SDK adapters) for a 3-provider need; surface area exceeds what the cockpit uses.
- **Why rejected**: scope mismatch. Protocol + 3 concrete classes = same outcome, ~50 lines total.

### Pluggy / `entry_points`-based discovery (rejected)

- **Pros**: external providers can register without modifying the cockpit codebase.
- **Cons**: extension surface the cockpit does not need; the 3 tiers are fixed by the [Selected under](../../README.md#selected-under) constraints (mock / local / paid).
- **Why rejected**: over-engineered for a closed set.

## Consequences

### Positive

- PoC reviewer flow: `git clone` → `pip install` → `uvicorn ...` works with zero env vars and zero key, exercising the full UI + Isolation Forest + Superset placeholder.
- Customer flow: paste `ANTHROPIC_API_KEY=...` + set `LLM_PROVIDER=claude`, zero refactor across `src/anomaly/`, `src/next_action/`, `src/sentiment/`.
- Test fixtures use one-off `_Stub` classes (no ABC inheritance), keeping test suite at 96 pytest cases without provider-mocking framework overhead.
- The single `default_provider()` swap point is what the README ["What this exercise validated"](../../README.md#what-this-exercise-validated) calls out as the architectural commitment.

### Negative

- The `MockProvider` outputs are deterministic templated — they do not capture LLM stochasticity, so the PoC reviewer does not see the actual LLM quality until tier 2 or 3 is wired. Documented in [PoC status](../../README.md#poc-status-what-is-live-vs-deferred).
- Provider feature parity is partial: token-counting semantics differ across Anthropic / Ollama, so the `count_tokens()` method returns provider-specific estimates rather than canonical counts. Acceptable since the cockpit does not bill on token counts.

### Reversibility

Adding a fourth tier (e.g., a customer's self-hosted LLM gateway) is a single new class implementing the Protocol + one line in `default_provider()`. Removing a tier is symmetric.

## References

- [PEP 544 — Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Ollama Python client](https://github.com/ollama/ollama-python)
- [LangChain `BaseChatModel`](https://python.langchain.com/docs/concepts/chat_models/) — heavyweight alternative considered
- [litellm](https://github.com/BerriAI/litellm) — provider-routing alternative considered
- Code: [src/llm/provider.py](../../src/llm/provider.py), [README — Configuration (env)](../../README.md#configuration-env)
