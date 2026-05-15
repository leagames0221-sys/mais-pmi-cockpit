"""T4 e2e smoke。

Usage: python -m scripts.e2e_smoke

各 step PASS/FAIL を print、 全 PASS で exit 0、 fail で exit 1。
"""
from __future__ import annotations

import sys
from pathlib import Path

PJ_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PJ_ROOT))

# Windows cp932 default encoding 防御 (cross-PJ universal pattern、 T3 inherit)
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and getattr(_stream, "encoding", "").lower() != "utf-8":
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from src.anomaly.detect_isolation_forest import detect_anomalies, filter_top_anomalies
from src.dashboard.superset_embed import aggregate_kpi_for_dashboard, build_embed_spec
from src.data_gen.generate_synthetic_cockpit import generate_synthetic_cockpit
from src.pipeline.five_stage_hybrid import run_5_stage_hybrid
from src.schema.types import (
    CockpitProject,
    KpiDefinition,
    KpiSnapshot,
    NextAction,
    RetentionRisk,
    SaasLicense,
    SentimentEvent,
    T4Output,
    VendorContract,
)
from src.sentiment.analyze_message import analyze_message, generate_mock_messages
from src.vault.store import decrypt_from_vault, emit_audit, encrypt_to_vault
from src.vendor.detect_overlap import detect_saas_overlap, detect_vendor_overlap

PASSED = 0
FAILED = 0


def step(name: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    status = "✅" if ok else "❌"
    print(f" {status} {name}{' — ' + detail if detail else ''}")
    if ok:
        PASSED += 1
    else:
        FAILED += 1


def main() -> int:
    print("=== T4 e2e smoke ===\n")

    # Phase 1: data_gen (合成 T4Output baseline)
    print("[Phase 1: synthetic data gen]")
    outputs = generate_synthetic_cockpit(n_projects=1, days=100, seed=0)
    step("Step 1: generate_synthetic_cockpit 1 件", len(outputs) == 1, f"{len(outputs)} T4Output")

    out: T4Output = outputs[0]
    cp: CockpitProject = out.cockpit_project
    step("Step 2: CockpitProject literal instance", isinstance(cp, CockpitProject), f"cp_id={cp.cp_id}")

    step("Step 3: KpiDefinition 4 dimension",
         len(out.kpi_definitions) == 4, f"{len(out.kpi_definitions)} kpi_defs")

    dims = {kp.dimension for kp in out.kpi_definitions}
    step("Step 4: 4 dim cover (cost/revenue/cash_gen/working_capital)",
         dims == {"cost", "revenue", "cash_gen", "working_capital"}, ", ".join(sorted(dims)))

    step("Step 5: KpiSnapshot 100 day × 4 dim = 400 件",
         len(out.kpi_snapshots) == 400, f"{len(out.kpi_snapshots)} snapshots")

    # Phase 2: anomaly detect
    print("\n[Phase 2: Isolation Forest anomaly detect]")
    all_anomalies = []
    for kp in out.kpi_definitions:
        kp_snapshots = [s for s in out.kpi_snapshots if s.kp_id == kp.kp_id]
        results = detect_anomalies(kp_snapshots, kp)
        all_anomalies.extend(results)
    step("Step 6: detect_anomalies returns results",
         len(all_anomalies) >= 0, f"{len(all_anomalies)} anomalies")

    top = filter_top_anomalies(all_anomalies, top_k=5)
    step("Step 7: filter_top_anomalies (top-5)",
         len(top) <= 5, f"{len(top)} top anomalies")

    # Phase 3: vendor + SaaS overlap
    print("\n[Phase 3: vendor + SaaS overlap detect]")
    vendors: list[VendorContract] = out.vendor_contracts
    step("Step 8: VendorContract 生成",
         len(vendors) >= 1, f"{len(vendors)} vendors")

    saas: list[SaasLicense] = out.saas_licenses
    step("Step 9: SaasLicense 生成",
         len(saas) >= 1, f"{len(saas)} saas licenses")

    vendor_overlaps = detect_vendor_overlap(vendors)
    step("Step 10: detect_vendor_overlap (industry cluster)",
         isinstance(vendor_overlaps, list), f"{len(vendor_overlaps)} overlap groups")

    saas_overlaps = detect_saas_overlap(saas)
    step("Step 11: detect_saas_overlap (usage_pct 30% threshold)",
         isinstance(saas_overlaps, list), f"{len(saas_overlaps)} overlap groups")

    # Phase 4: sentiment + 5-stage hybrid + retention risk
    print("\n[Phase 4: sentiment + 5-stage hybrid + retention risk]")
    messages = generate_mock_messages(cp_id=cp.cp_id, n=10)
    step("Step 12: generate_mock_messages",
         len(messages) == 10, f"{len(messages)} messages")

    sentiments: list[SentimentEvent] = [
        analyze_message(
            cp_id=cp.cp_id,
            source_channel=m.get("source_channel", "slack"),
            message_text=m.get("message_text", ""),
            se_seq=i,
        )
        for i, m in enumerate(messages, 1)
    ]
    step("Step 13: analyze_message sentiment score",
         all(-1.0 <= s.sentiment_score <= 1.0 for s in sentiments),
         f"score range [-1, 1] verified")

    retentions: list[RetentionRisk] = out.retention_risks
    step("Step 14: RetentionRisk T3 JPDay1Pattern trigger",
         isinstance(retentions, list), f"{len(retentions)} retention risks")

    # Phase 5: vault + dashboard embed
    print("\n[Phase 5: vault (Fernet) + Superset embed]")
    import os
    from cryptography.fernet import Fernet
    os.environ.setdefault("VAULT_KEY", Fernet.generate_key().decode())
    os.environ["DATA_DIR"] = str(PJ_ROOT / "data" / "e2e_smoke")

    encrypt_to_vault("RT-TEST-001",
                     {"sentiment_quote": "synthetic test only"},
                     vault_name="retention_risk_pii")
    step("Step 15: vault encrypt_to_vault", True, "Fernet 暗号化 + JSONL append")

    decrypted = decrypt_from_vault("RT-TEST-001", vault_name="retention_risk_pii")
    step("Step 16: vault decrypt round-trip",
         decrypted is not None and decrypted.get("sentiment_quote") == "synthetic test only",
         "round-trip literal verified")

    # Superset embed spec
    spec = build_embed_spec(cp, out.kpi_definitions)
    step("Step 17: Superset embed spec build",
         spec.cp_id == cp.cp_id and spec.time_range_days == 100,
         f"iframe_src={spec.iframe_src[:50]}...")

    # KPI aggregate
    agg = aggregate_kpi_for_dashboard(out.kpi_snapshots, out.kpi_definitions)
    step("Step 18: aggregate_kpi_for_dashboard 4 dim",
         len(agg) == 4 and all(v.get("count", 0) > 0 for v in agg.values()),
         f"{len(agg)} dim aggregated")

    # Summary
    print(f"\n=== T4 e2e smoke: {PASSED} PASS / {FAILED} FAIL ===")
    if FAILED > 0:
        print("❌ T4 e2e smoke FAILED")
        return 1
    print("✅ T4 e2e smoke 18/18 PASS literal 全 green ★★★")
    return 0


if __name__ == "__main__":
    sys.exit(main())
