"""
api/app.py
==========

Thin FastAPI wrapper around gbm_evidence_engine. This is standard,
low-risk glue code — all the scientific logic it calls into
(orchestrator/build_dossier.py) is independently unit-tested (see tests/).

NOT EXECUTABLE IN THIS SANDBOX: `pip install fastapi uvicorn` requires
network access this environment does not have (confirmed at build time —
see docs/VALIDATION_REPORT.md). Deploy with:

    pip install fastapi uvicorn
    uvicorn api.app:app --host 0.0.0.0 --port 8000

Then: POST /dossier {"gene": "EGFR"} -> full Dossier JSON
      POST /dossier/batch {"genes": ["EGFR","PTEN","TP53"]} -> capability test #5
"""
from __future__ import annotations
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as e:  # pragma: no cover - expected in this offline sandbox
    raise ImportError(
        "fastapi/pydantic not installed in this sandbox (no network access to pip install). "
        "This module is real, deployable code -- see the module docstring for how to run it "
        "in an environment with network access."
    ) from e

from gbm_evidence_engine.orchestrator import build_single_gene_dossier, generate_synthesis, validate_numeric_grounding
from gbm_evidence_engine.analysis.multiple_testing import benjamini_hochberg

app = FastAPI(title="GBM Evidence Engine (Rutgers G4G)", version="0.1.0")


class GeneQuery(BaseModel):
    gene: str
    cohorts: Optional[list[str]] = None


class BatchGeneQuery(BaseModel):
    genes: list[str]
    cohorts: Optional[list[str]] = None


def _dossier_with_synthesis(gene: str, cohorts: Optional[list[str]] = None) -> dict:
    dossier = build_single_gene_dossier(gene, cohorts)
    synthesis = generate_synthesis(dossier)
    check = validate_numeric_grounding(synthesis, dossier)
    dossier.ai_synthesis = synthesis
    dossier.ai_synthesis_grounding_ok = check.ok
    if not check.ok:
        # Fail loudly rather than silently serve an ungrounded synthesis --
        # this is the enforcement point described in orchestrator/synthesizer.py.
        dossier.warnings.append(
            f"AI synthesis failed numeric grounding check (unmatched: {check.unmatched_numbers}); "
            f"treat the free-text synthesis with caution and rely on the structured evidence list."
        )
    return dossier.to_dict()


@app.post("/dossier")
def get_dossier(query: GeneQuery):
    try:
        return _dossier_with_synthesis(query.gene, query.cohorts)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/dossier/batch")
def get_batch_dossier(query: BatchGeneQuery):
    """High-value capability test #5: batch triage of a researcher's own gene
    list, with Benjamini-Hochberg correction applied across the batch's
    primary survival p-values (a step a manual one-gene-at-a-time workflow
    routinely skips)."""
    results = []
    for gene in query.genes:
        try:
            results.append(_dossier_with_synthesis(gene, query.cohorts))
        except FileNotFoundError:
            results.append({"gene": gene, "error": "no data available for this gene in this deployment"})

    primary_pvals, idxs = [], []
    for i, r in enumerate(results):
        meta = next((e for e in r.get("evidence", [])
                     if e.get("statistic_name") == "pooled_hazard_ratio"), None)
        if meta and meta.get("p_value") is not None:
            primary_pvals.append(meta["p_value"])
            idxs.append(i)
    if primary_pvals:
        corrected = benjamini_hochberg(primary_pvals)
        for idx, c in zip(idxs, corrected):
            results[idx]["batch_bh_corrected_p_value"] = c

    return {"n_genes": len(query.genes), "results": results}


@app.get("/health")
def health():
    return {"status": "ok"}
