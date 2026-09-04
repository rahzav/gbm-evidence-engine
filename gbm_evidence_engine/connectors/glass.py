"""GLASS longitudinal glioma connector.

The current GLASS gene-TPM matrix is a controlled Synapse file. This module is
fully operational when ``SYNAPSE_AUTH_TOKEN`` belongs to a user who has accepted
the applicable GLASS access terms. Without authorized access it returns a
structured credentials-required state; it never substitutes synthetic values.

The matrix itself contains diffuse-glioma samples. Until a compatible controlled
clinical table is also configured, paired TP->R1 expression is surfaced as
longitudinal glioma context and is deliberately excluded from the GBM target
priority score.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import re

import numpy as np
from scipy import stats

from gbm_evidence_engine.evidence_model import AccessTier
from .base import CACHE_DIR, SOURCE_REGISTRY

GLASS_META = SOURCE_REGISTRY["glass"]
GLASS_TPM_ENTITY = "syn57367276"
GLASS_DIR = CACHE_DIR / "glass"
GLASS_DIR.mkdir(parents=True, exist_ok=True)


def _sample_identity(label: str) -> tuple[str, str] | None:
    """Parse GLASS sample labels into patient + time point when TP/R# is encoded."""
    value = str(label).strip()
    match = re.search(r"^(.*?)-(TP|R\d+)(?:-|$)", value, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1), match.group(2).upper()


def _read_gene_row(path: Path, gene: str) -> tuple[list[str], np.ndarray]:
    gene = gene.upper().strip()
    with open(path, "rt", encoding="utf-8-sig", errors="replace") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        samples = header[1:]
        for line in f:
            parts = line.rstrip("\r\n").split("\t")
            if parts and parts[0].upper() == gene:
                vals = []
                for x in parts[1:]:
                    try:
                        vals.append(float(x))
                    except (TypeError, ValueError):
                        vals.append(float("nan"))
                return samples, np.asarray(vals, dtype=float)
    raise KeyError(f"{gene} was not found in the GLASS TPM matrix.")


def summarize_longitudinal_expression(gene: str) -> dict:
    gene = gene.upper().strip()
    token = os.getenv("SYNAPSE_AUTH_TOKEN", "").strip()
    if not token:
        return {
            "ok": False,
            "status": "credentials_required",
            "gene": gene,
            "entity_id": GLASS_TPM_ENTITY,
            "error": "Set SYNAPSE_AUTH_TOKEN for an authorized Synapse account with GLASS download access.",
            "access_tier": AccessTier.REGISTRATION_GATED.value,
        }
    try:
        import synapseclient

        syn = synapseclient.login(authToken=token, silent=True)
        entity = syn.get(GLASS_TPM_ENTITY, downloadLocation=str(GLASS_DIR))
        path = Path(entity.path)
        samples, raw = _read_gene_row(path, gene)

        by_patient: dict[str, dict[str, list[float]]] = {}
        for label, tpm in zip(samples, raw):
            if not math.isfinite(float(tpm)):
                continue
            parsed = _sample_identity(label)
            if not parsed:
                continue
            patient, timepoint = parsed
            by_patient.setdefault(patient, {}).setdefault(timepoint, []).append(math.log2(max(0.0, float(tpm)) + 1.0))

        paired = []
        for patient, points in by_patient.items():
            if not points.get("TP"):
                continue
            recurrent_keys = sorted((k for k in points if re.fullmatch(r"R\d+", k)), key=lambda x: int(x[1:]))
            if not recurrent_keys:
                continue
            recurrent_key = recurrent_keys[0]
            tp = float(np.median(points["TP"]))
            rec = float(np.median(points[recurrent_key]))
            paired.append({"patient": patient, "primary": tp, "recurrent": rec, "delta": rec - tp, "recurrence": recurrent_key})

        if len(paired) < 5:
            return {
                "ok": False,
                "status": "insufficient_pairs",
                "gene": gene,
                "entity_id": GLASS_TPM_ENTITY,
                "n_pairs": len(paired),
                "error": "Fewer than five primary/recurrent pairs could be resolved from the matrix labels.",
                "access_tier": AccessTier.REGISTRATION_GATED.value,
            }

        primary = np.asarray([x["primary"] for x in paired])
        recurrent = np.asarray([x["recurrent"] for x in paired])
        delta = recurrent - primary
        try:
            test = stats.wilcoxon(recurrent, primary, alternative="two-sided", zero_method="wilcox")
            statistic, p_value = float(test.statistic), float(test.pvalue)
        except ValueError:
            statistic, p_value = 0.0, 1.0
        return {
            "ok": True,
            "status": "authorized",
            "gene": gene,
            "entity_id": GLASS_TPM_ENTITY,
            "entity_version": getattr(entity, "versionNumber", None),
            "scope": "GLASS diffuse-glioma TPM matrix; not yet subtype-filtered to GBM",
            "transform": "log2(TPM + 1)",
            "n_pairs": len(paired),
            "median_primary": float(np.median(primary)),
            "median_recurrent": float(np.median(recurrent)),
            "median_delta": float(np.median(delta)),
            "fraction_increased": float(np.mean(delta > 0)),
            "wilcoxon_statistic": statistic,
            "p_value": p_value,
            "pairs": paired[:20],
            "access_tier": AccessTier.REGISTRATION_GATED.value,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "access_or_parse_error",
            "gene": gene,
            "entity_id": GLASS_TPM_ENTITY,
            "error": str(exc),
            "access_tier": AccessTier.REGISTRATION_GATED.value,
        }


def registration_reminder() -> str:
    return (
        "GLASS uses controlled Synapse access. Add a SYNAPSE_AUTH_TOKEN from an account that has accepted "
        f"the GLASS access conditions; the current TPM matrix is {GLASS_TPM_ENTITY}."
    )
