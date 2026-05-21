# ADR-0004: Dashboard visualization — Apache Superset embedded SDK (with JWT swap path)

## Status

Accepted (2026-05-22)

## Context

The cockpit needs a live KPI visualization surface that the operating partner can read at-a-glance ([README "30-second pitch"](../../README.md#30-second-pitch) — synergy KPIs on cost / revenue / cash-gen / working capital + JP mid-market specific). Four constraints:

1. **Live, not static** — the visualization must reflect KPI snapshot ingestion in near real-time, not require a manual report regeneration.
2. **Embeddable in the cockpit UI** — the dashboard sits inside the cockpit's FastAPI app shell, not on a separate URL the user has to navigate to.
3. **Free + no-credit-card default** — see [Selected under](../../README.md#selected-under). Cannot require a paid BI license (Tableau / Power BI / Looker all violate this).
4. **Customer-deployment swap** — large customers commonly already license Power BI or Tableau; the chosen path must allow swap-out without rewriting the cockpit's anomaly + next-action layers.

## Decision

Apache Superset 6.0+ (Apache-2.0) via its embedded SDK, behind a 1-file swap point ([src/dashboard/superset_embed.py](../../src/dashboard/superset_embed.py)):

- The PoC ships an `about:blank#superset-embed-placeholder` URL builder, with the JWT spec literal in the file but no live Superset instance wired.
- Production wiring is one configuration change: provide `SUPERSET_HOST` + `SUPERSET_GUEST_TOKEN` env vars + a Superset instance reachable on that host. The iframe URL builder + JWT signing spec is already in place.
- A different dashboard tool (Power BI embed, Tableau embed, custom D3) can replace the Superset path at the same `src/dashboard/` swap point; downstream consumers don't change.

## Why Apache Superset specifically

### License + cost fit

Apache-2.0 license; runs free on a single VM or a Docker container; no per-user license; no credit card to register. This is the only mature OSS BI dashboard with a tested embedded SDK at this writing.

### JWT-gated embed is purpose-built

Superset's "guest token" model produces a short-lived JWT scoped to a specific dashboard + row-level filter set. This is exactly what a cockpit-embedded dashboard needs — the cockpit issues the JWT scoped to the current `CockpitProject` and the embedded Superset iframe renders only that project's KPIs.

### Python-native operating model

Superset is Flask under the hood; running it on the same Python ecosystem as the cockpit means a customer-side ops team only learns one runtime.

## Alternatives considered

### Power BI Embedded (rejected)

- **Pros**: industry-standard among PE firms and consulting practices; rich visualization library.
- **Cons**: requires an Azure subscription with a credit card on file; per-capacity licensing model adds non-trivial monthly cost; locks the cockpit's PoC to Microsoft's BI stack.
- **Why rejected**: violates [Selected under](../../README.md#selected-under) zero-credit-card. **Documented as the recommended customer-deployment swap target** when the customer already has Power BI capacity.

### Tableau Embedded (rejected)

- **Pros**: also industry-standard; strong visualization quality.
- **Cons**: Tableau Server license is per-server with a credit-card-required activation; Tableau Cloud is per-creator-per-month. Same constraint violation as Power BI.
- **Why rejected**: cost.

### Looker / Looker Studio (rejected)

- **Pros**: Google Cloud-native; Looker Studio (formerly Data Studio) is free.
- **Cons**: Looker (the paid enterprise version) requires a GCP subscription; Looker Studio (free) does not have a tested embed-with-row-level-security model for stateful PoC dashboards.
- **Why rejected**: the cost-free Looker Studio is feature-incomplete; the paid Looker violates the constraint.

### Metabase (rejected)

- **Pros**: also OSS BI dashboard, AGPL-3 open-core.
- **Cons**: AGPL-3 viral copyleft on the network-service surface — embedding Metabase in the cockpit may obligate AGPL-3 disclosure for the cockpit's own source. The Metabase Enterprise edition removes the AGPL but requires a paid license.
- **Why rejected**: license risk on the open-core boundary.

### Self-built D3.js / Plotly / Chart.js dashboard (rejected)

- **Pros**: full control; no external dependency; no license issues.
- **Cons**: re-implements months of visualization work (drill-down, cross-filter, role-based access, mobile-responsive layouts) that Superset already ships; defeats the cockpit's core thesis of "BI dashboards are the right call for static visualization — we add the anomaly+action loop on top."
- **Why rejected**: scope discipline. The cockpit's wedge is the anomaly-to-action loop, not the dashboard itself.

### Grafana (rejected)

- **Pros**: OSS (AGPL-3 from 2024, but with permissive APIs), strong time-series visualization.
- **Cons**: Grafana's strength is operational metrics (Prometheus / InfluxDB / Loki integration), not BI-style KPI dashboards with drill-down + role-based row filtering. Embedding model is less mature than Superset's guest-token system.
- **Why rejected**: domain mismatch — Grafana for ops, Superset for BI.

## Consequences

### Positive

- PoC reviewer sees the swap point literally — `src/dashboard/superset_embed.py` ships with the JWT builder in place, just the host URL missing. This makes the customer-deployment story checkable, not aspirational.
- License-clean: Apache-2.0 throughout; no AGPL viral surface.
- Customer with existing Power BI / Tableau license can swap at the same boundary without changing the cockpit's anomaly + next-action layers.

### Negative

- PoC visualization is a placeholder iframe (`about:blank#superset-embed-placeholder`); the demo video skips through this scene. Disclosed in [PoC status](../../README.md#poc-status-what-is-live-vs-deferred).
- Superset operations team adds a deploy surface (Superset must be running somewhere for the cockpit to embed). Mitigated by running Superset in the same Docker compose as the cockpit at customer-deployment time.

### Reversibility

The dashboard swap path is a single file (`src/dashboard/superset_embed.py`) returning an iframe URL. Replacing Superset with Power BI Embedded, Tableau Embedded, or a custom dashboard is a per-call swap, not a refactor.

## References

- [Apache Superset documentation](https://superset.apache.org/docs/intro)
- [Apache Superset Embedded SDK](https://github.com/apache-superset/embedded-sdk)
- [Power BI Embedded documentation](https://learn.microsoft.com/en-us/power-bi/developer/embedded/) — recommended paid swap target
- [Tableau Embedded Analytics](https://www.tableau.com/embedded-analytics) — alternative paid swap target
- [Metabase license model](https://www.metabase.com/license/) — AGPL-3 boundary issue
- Code: [src/dashboard/superset_embed.py](../../src/dashboard/superset_embed.py), [README — Configuration (env)](../../README.md#configuration-env)
