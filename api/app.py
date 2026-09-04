"""FastAPI interface for GBM Gene Analysis."""
from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover
    raise ImportError("Install fastapi, uvicorn and pydantic to run the API layer.") from e

from gbm_evidence_engine.research_intelligence_v5 import build_research_profile, rank_gene_list

app = FastAPI(title="GBM Gene Analysis", version="5.0.0")


class GeneQuery(BaseModel):
    gene: str = Field(min_length=1, max_length=40)


class BatchGeneQuery(BaseModel):
    genes: list[str] = Field(min_length=1, max_length=10)


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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "5.0.0",
        "scored_layers": ["TCGA/cBioPortal", "Open Targets", "ClinicalTrials.gov", "Europe PMC", "DepMap", "Ivy GAP", "CGGA", "GLASS"],
        "context_layers": ["MyGene.info", "Human Protein Atlas", "STRING", "B3DB", "GBmap reference"],
    }
