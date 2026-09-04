"""FastAPI interface for the research-grade GBM Evidence Engine."""
from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover
    raise ImportError("Install fastapi, uvicorn and pydantic to run the API layer.") from e

from gbm_evidence_engine.research_intelligence_v3 import build_research_profile, rank_gene_list

app = FastAPI(title="GBM Evidence Engine", version="3.0.0")


class GeneQuery(BaseModel):
    gene: str = Field(min_length=1, max_length=30)


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
    return {"status": "ok", "version": "3.0.0", "advanced_layers": ["DepMap", "Ivy GAP", "CGGA", "GLASS"]}
