"""T4 Apache Superset embed module (PoC mock + 移植時 SUPERSET_GUEST_TOKEN 経由 literal embed)。

 採用 stack 4 件中 ① Apache Superset 6.0 の T4 wrapper layer。
PoC 段階 = iframe URL builder (mock placeholder)、 移植時 = JWT auth + dashboard config wiring。

Apache Superset embed flow:
1. Superset 6.0 server に Dashboard 起草 (KPI time-series + DriverInsight overlay + NextAction trigger)
2. SUPERSET_GUEST_TOKEN issuance (Superset SDK / API)
3. iframe src = `<SUPERSET_URL>/embedded/<dashboard_id>?token=<JWT>`
4. parent page (T4 dashboard_view.html) で iframe embed + JS で resize handle

PoC 段階の本 module = embed URL spec + mock placeholder string 返却、 移植時 swap-out point literal 1 関数。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from src.schema.types import CockpitProject, KpiDefinition, KpiSnapshot


@dataclass(frozen=True)
class SupersetEmbedSpec:
    """Superset embed iframe 用 spec (移植時の literal blueprint)。"""

    superset_base_url: str # 例: https://superset.mais.internal
    dashboard_id: str # Superset 側 dashboard UUID
    guest_token: Optional[str] # JWT (移植時)、 PoC = None
    cp_id: str # T4 CockpitProject 識別 (filter parameter)
    time_range_days: int # 100 (Day-1 → Day-100)

    @property
    def iframe_src(self) -> str:
        """iframe src URL を literal 組立 (移植時 active、 PoC = placeholder)。"""
        if self.guest_token is None:
            return f"about:blank#superset-embed-placeholder-cp={self.cp_id}"
        return (
            f"{self.superset_base_url}/embedded/{self.dashboard_id}"
            f"?token={self.guest_token}"
            f"&filter_cp_id={self.cp_id}"
            f"&time_range={self.time_range_days}d"
        )


def build_embed_spec(
    cp: CockpitProject,
    kpi_defs: list[KpiDefinition], # noqa: ARG001、 移植時 dashboard config 連動で使用
    *,
    superset_base_url: Optional[str] = None,
    dashboard_id: Optional[str] = None,
    guest_token: Optional[str] = None,
) -> SupersetEmbedSpec:
    """T4 CockpitProject + KPI definition から Superset embed spec を literal build。

    PoC 段階 = env literal lookup + None fallback、 移植時 = JWT issuer 連動。
    """
    base = superset_base_url or os.environ.get("SUPERSET_BASE_URL", "https://superset.example.com")
    dash = dashboard_id or os.environ.get("SUPERSET_DASHBOARD_ID", "t4-pmi-cockpit-mock")
    token = guest_token or os.environ.get("SUPERSET_GUEST_TOKEN") # PoC 段階 = None expected

    return SupersetEmbedSpec(
        superset_base_url=base,
        dashboard_id=dash,
        guest_token=token,
        cp_id=cp.cp_id,
        time_range_days=100,
    )


def aggregate_kpi_for_dashboard(
    snapshots: list[KpiSnapshot], kpi_defs: list[KpiDefinition]
) -> dict[str, dict]:
    """KpiSnapshot を Superset embed 用 aggregate 形式に変換 (PoC = dim 別 latest + mean)。

    移植時 = Superset 側で SQL aggregate、 PoC = Python aggregate で literal placeholder data 提供。
    dimension は KpiDefinition から kp_id 経由で literal lookup (KpiSnapshot は kp_id のみ持つ schema)。
    """
    dim_by_kp_id = {kp.kp_id: kp.dimension for kp in kpi_defs}
    by_dim: dict[str, list[KpiSnapshot]] = {}
    for snap in snapshots:
        dim = dim_by_kp_id.get(snap.kp_id)
        if dim is None:
            continue
        by_dim.setdefault(dim, []).append(snap)

    agg: dict[str, dict] = {}
    for dim, items in by_dim.items():
        sorted_items = sorted(items, key=lambda s: s.observed_at)
        if not sorted_items:
            continue
        values = [s.value for s in sorted_items if s.value is not None]
        agg[dim] = {
            "count": len(sorted_items),
            "latest_value": sorted_items[-1].value if sorted_items else None,
            "latest_observed_at": sorted_items[-1].observed_at.isoformat() if sorted_items else None,
            "mean": sum(values) / len(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return agg
