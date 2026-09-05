"""Native GBmap cell-state context from a compact precomputed reference.

Production never downloads the full GBmap atlas for an interactive query. The
canonical offline builder converts the published Core GBmap into a compact
state/patient summary. These statistics are contextual and non-scoring:
expression enrichment or prevalence does not establish dependency, causality,
drug sensitivity, or clinical benefit.
"""
from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Iterable

REFERENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "gbmap_gene_state_summary.csv.gz"
METADATA_PATH = Path(__file__).resolve().parents[2] / "data" / "gbmap_reference_metadata.json"
COLLECTION_ID = "999f2a15-3d7e-440b-96ae-2c806799c08c"
COLLECTION_URL = f"https://cellxgene.cziscience.com/collections/{COLLECTION_ID}"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _rows_for_gene(gene: str, path: Path = REFERENCE_PATH) -> list[dict]:
    if not path.exists():
        return []
    gene = gene.strip().upper()
    rows: list[dict] = []
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if str(row.get("gene") or "").upper() == gene:
                rows.append(row)
    return rows


def _duplicate_features_for_gene(gene: str, path: Path) -> list[str]:
    """Return all published feature IDs for an ambiguous symbol.

    Duplicate identity is taken from builder metadata rather than inferred from
    non-zero expression rows. A published feature can have zero retained
    expression and therefore be absent from the sparse compact table.
    """
    if path != REFERENCE_PATH or not METADATA_PATH.exists():
        return []
    try:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    mapping = metadata.get("duplicate_gene_features") or {}
    return [str(x) for x in mapping.get(gene.upper(), []) if str(x).strip()]


def summarize_gene_cell_states(gene: str, path: Path = REFERENCE_PATH) -> dict:
    gene = gene.strip().upper()

    duplicate_features = _duplicate_features_for_gene(gene, path)
    if len(duplicate_features) > 1:
        return {
            "ok": False,
            "gene": gene,
            "status": "ambiguous_gene_symbol",
            "feature_ids": duplicate_features,
            "error": (
                f"Core GBmap contains {len(duplicate_features)} distinct Ensembl features labeled {gene}. "
                "They are preserved separately rather than combined into a single expression profile."
            ),
            "source": "GBmap compact reference derived from CELLxGENE Core GBmap",
            "source_url": COLLECTION_URL,
        }

    rows = _rows_for_gene(gene, path=path)
    if not rows:
        return {
            "ok": False,
            "gene": gene,
            "status": "reference_unavailable" if not path.exists() else "gene_not_found",
            "error": (
                "The compact GBmap reference has not been generated on this deployment."
                if not path.exists()
                else f"{gene} is not present in the compact GBmap reference."
            ),
            "source": "GBmap / CELLxGENE",
            "source_url": COLLECTION_URL,
        }

    feature_ids = sorted({
        str(row.get("feature_id") or "").strip()
        for row in rows
        if str(row.get("feature_id") or "").strip()
    })
    if len(feature_ids) > 1:
        # Defensive fallback for a custom/reference file without metadata.
        return {
            "ok": False,
            "gene": gene,
            "status": "ambiguous_gene_symbol",
            "feature_ids": feature_ids,
            "error": (
                f"The reference contains {len(feature_ids)} distinct Ensembl features labeled {gene}. "
                "They are preserved separately rather than combined into a single expression profile."
            ),
            "source": "GBmap compact reference derived from CELLxGENE Core GBmap",
            "source_url": COLLECTION_URL,
        }

    state_rows: list[dict] = []
    for row in rows:
        # V1 test fixtures used n_patients; the canonical reference uses
        # explicit numerator/denominator fields. Supporting both keeps the
        # connector deterministic while preserving the stronger semantics.
        n_expressing = _int(row.get("n_expressing_patients"))
        if n_expressing is None:
            n_expressing = _int(row.get("n_patients"))
        n_state_patients = _int(row.get("n_state_patients"))
        state_rows.append({
            "feature_id": row.get("feature_id") or (feature_ids[0] if feature_ids else None),
            "state": row.get("state"),
            "state_class": row.get("state_class"),
            "n_cells": _int(row.get("n_cells")),
            "n_state_patients": n_state_patients,
            "n_expressing_patients": n_expressing,
            "patient_prevalence": _float(row.get("patient_prevalence")),
            "fraction_expressing": _float(row.get("fraction_expressing")),
            "mean_expression": _float(row.get("mean_expression")),
            "expression_z_across_states": _float(row.get("expression_z_across_states")),
        })

    state_rows.sort(
        key=lambda r: (
            r.get("expression_z_across_states") is not None,
            r.get("expression_z_across_states") or float("-inf"),
            r.get("fraction_expressing") or 0.0,
        ),
        reverse=True,
    )
    malignant = [r for r in state_rows if str(r.get("state_class") or "").lower() == "malignant"]
    microenvironment = [r for r in state_rows if str(r.get("state_class") or "").lower() != "malignant"]
    top_malignant = malignant[0] if malignant else None
    top_overall = state_rows[0] if state_rows else None

    malignant_patient_prevalence = None if top_malignant is None else top_malignant.get("patient_prevalence")
    malignant_expression_breadth = None if top_malignant is None else top_malignant.get("fraction_expressing")

    return {
        "ok": True,
        "gene": gene,
        "feature_id": feature_ids[0] if len(feature_ids) == 1 else None,
        "states": state_rows,
        "top_state": top_overall,
        "top_malignant_state": top_malignant,
        "malignant_patient_prevalence": malignant_patient_prevalence,
        "malignant_fraction_expressing": malignant_expression_breadth,
        "n_states": len(state_rows),
        "n_malignant_states": len(malignant),
        "n_microenvironment_states": len(microenvironment),
        "patient_prevalence_definition": (
            "For each state: patients with >=1 expressing cell divided by patients represented in that state. "
            "The summary patient-prevalence and expression-breadth values refer to the displayed top malignant state."
        ),
        "source": "GBmap compact reference derived from CELLxGENE Core GBmap",
        "source_url": COLLECTION_URL,
        "interpretation": (
            "GBmap cell-state statistics quantify where a gene is expressed and how broadly it is observed across patients represented in each state. "
            "Uneven cell-type capture across studies remains a limitation. These results do not establish selective dependency, causal function, drug response, or clinical utility."
        ),
    }


def state_vector(summary: dict, malignant_only: bool = True) -> dict[str, float]:
    """Return a normalized malignant-state expression vector for pair context."""
    if not summary.get("ok"):
        return {}
    rows: Iterable[dict] = summary.get("states") or []
    selected = [
        r for r in rows
        if (not malignant_only or str(r.get("state_class") or "").lower() == "malignant")
    ]
    raw = {
        str(r.get("state")): max(0.0, _float(r.get("mean_expression")) or 0.0)
        * max(0.0, min(1.0, _float(r.get("patient_prevalence")) or 0.0))
        for r in selected
        if r.get("state")
    }
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {k: v / total for k, v in raw.items()}
