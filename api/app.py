"""FastAPI interface for GBM Gene Analysis."""
from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover
    raise ImportError("Install fastapi, uvicorn and pydantic to run the API layer.") from e

from gbm_evidence_engine.research_discovery import (
    analyze_researcher_signature,
    build_research_profile,
    evaluate_gene_pair,
    rank_gene_list,
)

app = FastAPI(title="GBM Gene Analysis", version="6.0.0")


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


@app.post("/profile")
def get_profile(query: GeneQuery):
    try:
        return build_research_profile(query.gene).to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/profile/batch")
def get_batch(query: BatchGeneQuery):
    try:
        profiles = rank_gene_list(query.genes, max_workers=2)
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
    try:
        return analyze_researcher_signature(query.genes, query.values)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "6.0.0",
        "scored_layers": [
            "TCGA/cBioPortal", "Open Targets", "ClinicalTrials.gov", "Europe PMC",
            "DepMap", "Ivy GAP", "CGGA", "GLASS",
        ],
        "context_layers": [
            "MyGene.info", "Human Protein Atlas", "STRING", "B3DB",
            "DepMap NextGen model context", "GBmap reference",
        ],
        "discovery_layers": [
            "cross-source research opportunities",
            "guarded falsifiable mechanistic hypotheses",
            "uncertainty-reduction experiment prioritization",
            "target-pair rationale analysis",
            "researcher signature interpretation",
            "LINCS/L1000 perturbational reversal and combination hypotheses",
        ],
    }
