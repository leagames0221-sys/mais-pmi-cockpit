"""T4 FastAPI Web UI (Week 4 PoC demo、 5 endpoint、 Jinja2 templates)。

dit 済 stack literal reuse。
T3 src/api/app.py pattern literal inherit + T4 specific 5 軸 view (KPI / DriverInsight /
NextAction / Sentiment / Vendor) 拡張 + Superset embed dashboard。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.data_gen.generate_synthetic_cockpit import generate_synthetic_cockpit

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="MAIS PMI Cockpit")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _build_demo_t4_output() -> Any:
    """PoC demo: 合成 T4Output 1 件 (seed=0 で literal deterministic、 合成データ only)。

    実際の use case は T3 → T4 ingestion + orchestrator DAG 経由、 demo では data_gen 直接呼出。
    """
    outputs = generate_synthetic_cockpit(n_projects=1, days=100, seed=0)
    return outputs[0]


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> Any:
    return TEMPLATES.TemplateResponse(
        request=request,
        name="landing.html",
        context={"title": "MAIS PMI Cockpit"},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "mais-pmi-cockpit", "version": "0.4.0"}


@app.post("/generate", response_class=HTMLResponse)
async def generate_cockpit(request: Request) -> Any:
    """PoC demo: 合成 T4Output 生成 + cockpit_view literal render (5 軸機能 表示)。"""
    out = _build_demo_t4_output()
    return TEMPLATES.TemplateResponse(
        request=request,
        name="cockpit_view.html",
        context={
            "cp": out.cockpit_project,
            "kpi_definitions": out.kpi_definitions,
            "kpi_snapshots": out.kpi_snapshots,
            "driver_insights": out.driver_insights,
            "next_actions": out.next_actions,
            "sentiment_events": out.sentiment_events,
            "vendor_contracts": out.vendor_contracts,
            "saas_licenses": out.saas_licenses,
            "retention_risks": out.retention_risks,
        },
    )


@app.get("/api/generate")
async def generate_cockpit_json() -> Any:
    """JSON API: T4 demo run の literal full output (T4Output schema 順守)。"""
    out = _build_demo_t4_output()
    return JSONResponse(content=out.model_dump(mode="json"))


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Any:
    """Superset embed dashboard (PoC = mock iframe、 移植時 = SUPERSET_GUEST_TOKEN 経由 literal embed)。"""
    out = _build_demo_t4_output()
    return TEMPLATES.TemplateResponse(
        request=request,
        name="dashboard_view.html",
        context={
            "cp": out.cockpit_project,
            "kpi_definitions": out.kpi_definitions,
            "kpi_snapshots_count": len(out.kpi_snapshots),
            "driver_insights_count": len(out.driver_insights),
            "next_actions_count": len(out.next_actions),
        },
    )
