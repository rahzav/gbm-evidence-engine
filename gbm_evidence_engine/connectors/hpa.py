"""Human Protein Atlas connector for normal-tissue and brain expression context."""
from __future__ import annotations

import urllib.parse
from typing import Any

from .base import http_get_json

BASE = "https://www.proteinatlas.org/api/search_download.php"
COLUMNS = [
    "g", "gs", "eg", "gd", "pc",
    "rnats", "rnatd", "rnatss",
    "rnascs", "rnascd", "rnascss",
    "rnasnbs", "rnasnbd", "rnasnbss",
    "rnabrs", "rnabrd", "rnabrss",
    "t_RNA_cerebral_cortex", "t_RNA_white_matter", "t_RNA_basal_ganglia",
    "t_RNA_hippocampal_formation", "t_RNA_cerebellum",
]


def _first(row: dict[str, Any], *keys: str):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_gene_context(gene: str) -> dict:
    gene = gene.strip().upper()
    params = urllib.parse.urlencode({
        "search": gene,
        "format": "json",
        "columns": ",".join(COLUMNS),
        "compress": "no",
    })
    data = http_get_json(f"{BASE}?{params}", timeout=20)
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        return {"ok": False, "gene": gene, "error": "Human Protein Atlas unavailable."}

    row = next((r for r in rows if str(_first(r, "Gene", "gene", "g") or "").upper() == gene), rows[0] if rows else None)
    if not isinstance(row, dict):
        return {"ok": False, "gene": gene, "error": "Human Protein Atlas returned no matching gene."}

    brain_fields = {
        "Cerebral cortex": _float(_first(row, "Tissue RNA - cerebral cortex [nTPM]", "Tissue RNA - cerebral cortex [NX]", "t_RNA_cerebral_cortex")),
        "White matter": _float(_first(row, "Tissue RNA - white matter [nTPM]", "Tissue RNA - white matter [NX]", "t_RNA_white_matter")),
        "Basal ganglia": _float(_first(row, "Tissue RNA - basal ganglia [nTPM]", "Tissue RNA - basal ganglia [NX]", "t_RNA_basal_ganglia")),
        "Hippocampal formation": _float(_first(row, "Tissue RNA - hippocampal formation [nTPM]", "Tissue RNA - hippocampal formation [NX]", "t_RNA_hippocampal_formation")),
        "Cerebellum": _float(_first(row, "Tissue RNA - cerebellum [nTPM]", "Tissue RNA - cerebellum [NX]", "t_RNA_cerebellum")),
    }
    brain_fields = {k: v for k, v in brain_fields.items() if v is not None}

    return {
        "ok": True,
        "gene": gene,
        "ensembl_id": _first(row, "Ensembl", "eg"),
        "description": _first(row, "Gene description", "gd"),
        "protein_class": _first(row, "Protein class", "pc"),
        "tissue_specificity": _first(row, "RNA tissue specificity", "rnats"),
        "tissue_distribution": _first(row, "RNA tissue distribution", "rnatd"),
        "tissue_specificity_score": _float(_first(row, "RNA tissue specificity score", "rnatss")),
        "single_cell_specificity": _first(row, "RNA single cell type specificity", "rnascs"),
        "single_cell_distribution": _first(row, "RNA single cell type distribution", "rnascd"),
        "single_cell_specificity_score": _float(_first(row, "RNA single cell type specificity score", "rnascss")),
        "single_nuclei_brain_specificity": _first(row, "RNA single nuclei brain specificity", "rnasnbs"),
        "single_nuclei_brain_distribution": _first(row, "RNA single nuclei brain distribution", "rnasnbd"),
        "single_nuclei_brain_specificity_score": _float(_first(row, "RNA single nuclei brain specificity score", "rnasnbss")),
        "brain_regional_specificity": _first(row, "RNA brain regional specificity", "rnabrs"),
        "brain_regional_distribution": _first(row, "RNA brain regional distribution", "rnabrd"),
        "brain_regional_specificity_score": _float(_first(row, "RNA brain regional specificity score", "rnabrss")),
        "brain_region_expression": brain_fields,
        "normal_brain_max_expression": max(brain_fields.values()) if brain_fields else None,
        "source_url": f"https://www.proteinatlas.org/{_first(row, 'Ensembl', 'eg')}" if _first(row, "Ensembl", "eg") else "https://www.proteinatlas.org/",
        "interpretation": "Normal-tissue context only. Expression in normal brain or other tissues may indicate target-liability considerations but does not by itself establish toxicity or lack of therapeutic window.",
    }
