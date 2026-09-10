"""FastAPI interface for the Glia evidence engine."""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover
    raise ImportError("Install fastapi, uvicorn and pydantic to run the API layer.") from e

from gbm_evidence_engine.research_intelligence_v7_prod import (
    analyze_researcher_signature,
    build_research_profile,
    evaluate_gene_pair,
    rank_gene_list,
)
from gbm_evidence_engine.research_agent import ResearchAgentError, run_agent_turn

app = FastAPI(title="Glia Evidence Engine", version="7.0.0")


class GeneQuery(BaseModel):
    gene: str = Field(min_length=1, max_length=40)


class BatchGeneQuery(BaseModel):
    genes: list[str] = Field(min_length=1, max_length=10)


class GenePairQuery(BaseModel):
    gene_a: str = Field(min_length=1, max_length=40)
    gene_b: str = Field(min_length=1, max_length=40)


class SignatureQuery(BaseModel):
    genes: list[str] = Field(min_length=6, max_length=500)
    values: list[float] = Field(min_length=6, max_length=500)
    p_values: list[float | None] | None = Field(default=None, max_length=500)
    fdr_values: list[float | None] | None = Field(default=None, max_length=500)


class GliaQuery(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    context: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    selected_quote: str | None = Field(default=None, max_length=1800)
    selected_section: str | None = Field(default=None, max_length=120)


@app.post("/profile")
def get_profile(query: GeneQuery):
    try:
        return build_research_profile(query.gene).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/profile/batch")
def get_batch(query: BatchGeneQuery):
    try:
        profiles = rank_gene_list(query.genes, max_workers=1)
        return {"n_genes": len(profiles), "results": [p.to_dict() for p in profiles]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/combination")
def get_combination(query: GenePairQuery):
    try:
        return evaluate_gene_pair(query.gene_a, query.gene_b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/signature")
def get_signature(query: SignatureQuery):
    if len(query.genes) != len(query.values):
        raise HTTPException(status_code=400, detail="genes and values must have the same length")
    if query.p_values is not None and len(query.p_values) != len(query.genes):
        raise HTTPException(status_code=400, detail="p_values must have the same length as genes when provided")
    if query.fdr_values is not None and len(query.fdr_values) != len(query.genes):
        raise HTTPException(status_code=400, detail="fdr_values must have the same length as genes when provided")
    try:
        return analyze_researcher_signature(
            query.genes,
            query.values,
            p_values=query.p_values,
            fdr_values=query.fdr_values,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "7.0.0",
        "scored_layers": [
            "TCGA/cBioPortal", "Open Targets", "ClinicalTrials.gov", "Europe PMC",
            "DepMap", "Ivy GAP", "CGGA", "GLASS",
        ],
        "context_layers": [
            "MyGene.info", "Human Protein Atlas", "STRING", "B3DB",
            "DepMap model context", "native compact GBmap cell-state reference",
        ],
        "decision_support_layers": [
            "cross-source research opportunities",
            "guarded falsifiable mechanistic hypotheses",
            "uncertainty-reduction experiment prioritization",
            "explicit evidence confidence",
            "model-relevance grading",
            "state-aware target-pair rationale",
            "significance-aware researcher signature interpretation",
            "LINCS/L1000 perturbational reversal and combination hypotheses",
        ],
        "scope": "GBM molecular research decision support; not clinical decision-making",
    }


@app.post("/glia/chat")
def glia_chat(query: GliaQuery):
    context = dict(query.context)
    context["selected_quote"] = query.selected_quote
    context["selected_section"] = query.selected_section
    try:
        result = run_agent_turn(
            query.message,
            history=query.history[-10:],
            session_context=context,
            persistent_memory=query.memory,
        )
    except ResearchAgentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "text": result.text,
        "references": result.references,
        "tools_used": result.tools_used,
        "grounding_ok": result.grounding_ok,
    }


WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
if WEB_ROOT.exists():
    app.mount("/assets", StaticFiles(directory=WEB_ROOT / "assets"), name="web-assets")

    @app.get("/", include_in_schema=False)
    def web_app():
        return FileResponse(WEB_ROOT / "index.html")
