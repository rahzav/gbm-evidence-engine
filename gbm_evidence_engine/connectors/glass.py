"""GLASS longitudinal GBM connector.

Controlled GLASS RNA expression is queried only for users with authorized
Synapse access. The connector joins TPM samples to GLASS surgery-level clinical
metadata and only marks a result ``gbm_specific=True`` when primary/recurrent
pairs are explicitly verified as IDH-wildtype glioblastoma. Diffuse-glioma-wide
fallbacks are never allowed to contribute to the priority score.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from gbm_evidence_engine.evidence_model import AccessTier
from .base import CACHE_DIR, SOURCE_REGISTRY

GLASS_META = SOURCE_REGISTRY["glass"]
GLASS_PROJECT = "syn17038081"
GLASS_TPM_ENTITY = "syn57367276"
GLASS_DIR = CACHE_DIR / "glass"
GLASS_DIR.mkdir(parents=True, exist_ok=True)

# Explicit entity overrides are preferred for reproducible deployments. When
# absent, the connector searches the authorized GLASS project by entity name.
SURGERIES_ENTITY_ENV = "GLASS_CLINICAL_SURGERIES_ENTITY"
CASES_ENTITY_ENV = "GLASS_CLINICAL_CASES_ENTITY"


def _sample_identity(label: str) -> tuple[str, str] | None:
    """Parse a GLASS label into patient + time point (TP/R#)."""
    value = str(label).strip()
    match = re.search(r"^(.*?)-(TP|R\d+)(?:-|$)", value, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1), match.group(2).upper()


def _sample_barcode(label: str) -> str | None:
    """Extract the surgery/sample barcode from an RNA aliquot or sample label."""
    value = str(label).strip().upper()
    match = re.search(r"(GLSS-[A-Z0-9]+-[A-Z0-9]+-(?:TP|R\d+))(?:-|$)", value)
    return match.group(1) if match else None


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


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _first_present(row: pd.Series, aliases: Iterable[str]):
    lookup = {_norm(c): c for c in row.index}
    for alias in aliases:
        key = _norm(alias)
        if key in lookup:
            value = row.get(lookup[key])
            if pd.notna(value):
                return value
    return None


def _is_idh_wildtype(row: pd.Series) -> bool:
    value = _norm(_first_present(row, [
        "idh_status", "idh mutation status", "idh_mutation_status", "idh", "idh_status_old",
    ]))
    return value in {"idhwt", "wildtype", "wt", "idhwildtype"} or "idhwildtype" in value


def _is_gbm(row: pd.Series) -> bool:
    histology = _norm(_first_present(row, ["histology", "diagnosis", "tumor_type", "histologic_diagnosis"]))
    who = _norm(_first_present(row, ["who_classification", "who classification", "integrated_diagnosis"]))
    grade = _norm(_first_present(row, ["grade", "who_grade", "tumor_grade"]))
    explicit = ("glioblastoma" in histology or histology == "gbm" or
                "glioblastoma" in who or who == "gbm")
    grade_iv = grade in {"iv", "4", "whoiv", "whogradeiv", "whograde4"}
    # Histologic GBM is sufficient. Grade IV alone is accepted only when a
    # glioma-like diagnosis is present; this avoids silently classifying other
    # grade-IV entities as GBM.
    glioma_like = any(term in histology for term in ("glioma", "astrocyt")) or any(
        term in who for term in ("glioma", "astrocyt", "glioblast")
    )
    return explicit or (grade_iv and glioma_like)


def _clinical_sample_column(df: pd.DataFrame) -> str | None:
    aliases = ["sample_barcode", "sample barcode", "sample_id", "sample id", "tumor_barcode"]
    lookup = {_norm(c): c for c in df.columns}
    for alias in aliases:
        if _norm(alias) in lookup:
            return lookup[_norm(alias)]
    return None


def _clinical_case_column(df: pd.DataFrame) -> str | None:
    aliases = ["case_barcode", "case barcode", "case_id", "patient_id", "subject_id"]
    lookup = {_norm(c): c for c in df.columns}
    for alias in aliases:
        if _norm(alias) in lookup:
            return lookup[_norm(alias)]
    return None


def _verified_gbm_samples(surgeries: pd.DataFrame) -> tuple[set[str], dict[str, str]]:
    """Return sample barcodes explicitly verified as IDH-wt GBM."""
    if surgeries is None or surgeries.empty:
        return set(), {}
    sample_col = _clinical_sample_column(surgeries)
    case_col = _clinical_case_column(surgeries)
    if not sample_col:
        raise ValueError("GLASS surgery metadata has no recognizable sample_barcode column.")
    verified: set[str] = set()
    sample_to_case: dict[str, str] = {}
    for _, row in surgeries.iterrows():
        sample = str(row.get(sample_col) or "").strip().upper()
        if not sample:
            continue
        if _is_gbm(row) and _is_idh_wildtype(row):
            verified.add(sample)
            case = str(row.get(case_col) or "").strip().upper() if case_col else ""
            if case:
                sample_to_case[sample] = case
    return verified, sample_to_case


def _entity_name(child: dict) -> str:
    return str(child.get("name") or child.get("displayName") or "")


def _walk_project(syn, parent_id: str, depth: int = 2):
    """Yield authorized Synapse child metadata with a shallow recursive walk."""
    queue = [(parent_id, 0)]
    seen = set()
    while queue:
        parent, level = queue.pop(0)
        if parent in seen:
            continue
        seen.add(parent)
        try:
            children = list(syn.getChildren(parent=parent))
        except Exception:
            continue
        for child in children:
            yield child
            child_type = _norm(child.get("type") or child.get("concreteType"))
            if level < depth and "folder" in child_type:
                cid = child.get("id")
                if cid:
                    queue.append((cid, level + 1))


def _find_entity(syn, explicit_id: str | None, name_terms: list[str]) -> str | None:
    if explicit_id:
        return explicit_id.strip()
    ranked = []
    for child in _walk_project(syn, GLASS_PROJECT, depth=3):
        name = _norm(_entity_name(child))
        if not name:
            continue
        score = sum(1 for term in name_terms if _norm(term) in name)
        if score:
            ranked.append((score, len(name), child.get("id")))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked[0][2] if ranked else None


def _entity_to_dataframe(syn, entity_id: str) -> pd.DataFrame:
    """Load either a Synapse Table or delimited File into a DataFrame."""
    entity = syn.get(entity_id, downloadLocation=str(GLASS_DIR))
    concrete = _norm(getattr(entity, "concreteType", ""))
    if "table" in concrete:
        return syn.tableQuery(f"select * from {entity_id}").asDataFrame()
    path = getattr(entity, "path", None)
    if not path:
        raise ValueError(f"Synapse entity {entity_id} is neither a downloadable file nor a queryable table.")
    path = Path(path)
    # Sniff common tabular formats without guessing biological fields.
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    try:
        return pd.read_csv(path, sep=None, engine="python", dtype=str)
    except Exception as exc:
        raise ValueError(f"Could not parse GLASS clinical entity {entity_id}: {exc}") from exc


def _load_surgeries(syn) -> tuple[pd.DataFrame, str]:
    entity_id = _find_entity(
        syn,
        os.getenv(SURGERIES_ENTITY_ENV),
        ["clinical", "surger"],
    )
    if not entity_id:
        raise RuntimeError(
            "Could not discover GLASS surgery-level clinical metadata. Set "
            f"{SURGERIES_ENTITY_ENV} to the authorized Synapse entity ID."
        )
    return _entity_to_dataframe(syn, entity_id), entity_id


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
            "gbm_specific": False,
        }
    try:
        import synapseclient

        syn = synapseclient.login(authToken=token, silent=True)
        expression_entity = syn.get(GLASS_TPM_ENTITY, downloadLocation=str(GLASS_DIR))
        samples, raw = _read_gene_row(Path(expression_entity.path), gene)
        surgeries, surgeries_entity = _load_surgeries(syn)
        verified, sample_to_case = _verified_gbm_samples(surgeries)
        if not verified:
            return {
                "ok": False,
                "status": "clinical_filter_empty",
                "gene": gene,
                "entity_id": GLASS_TPM_ENTITY,
                "clinical_entity_id": surgeries_entity,
                "error": "No samples were explicitly verified as IDH-wildtype GBM in the resolved GLASS surgery metadata.",
                "access_tier": AccessTier.REGISTRATION_GATED.value,
                "gbm_specific": False,
            }

        by_patient: dict[str, dict[str, list[float]]] = {}
        sample_trace: dict[tuple[str, str], set[str]] = {}
        for label, tpm in zip(samples, raw):
            if not math.isfinite(float(tpm)):
                continue
            sample = _sample_barcode(label)
            parsed = _sample_identity(label)
            if not sample or not parsed or sample not in verified:
                continue
            patient_from_label, timepoint = parsed
            patient = sample_to_case.get(sample) or patient_from_label.upper()
            by_patient.setdefault(patient, {}).setdefault(timepoint, []).append(
                math.log2(max(0.0, float(tpm)) + 1.0)
            )
            sample_trace.setdefault((patient, timepoint), set()).add(sample)

        paired = []
        for patient, points in by_patient.items():
            if not points.get("TP"):
                continue
            recurrent_keys = sorted(
                (k for k in points if re.fullmatch(r"R\d+", k)),
                key=lambda x: int(x[1:]),
            )
            if not recurrent_keys:
                continue
            recurrent_key = recurrent_keys[0]
            tp = float(np.median(points["TP"]))
            rec = float(np.median(points[recurrent_key]))
            paired.append({
                "patient": patient,
                "primary": tp,
                "recurrent": rec,
                "delta": rec - tp,
                "recurrence": recurrent_key,
                "primary_samples": sorted(sample_trace.get((patient, "TP"), set())),
                "recurrent_samples": sorted(sample_trace.get((patient, recurrent_key), set())),
            })

        if len(paired) < 5:
            return {
                "ok": False,
                "status": "insufficient_gbm_pairs",
                "gene": gene,
                "entity_id": GLASS_TPM_ENTITY,
                "clinical_entity_id": surgeries_entity,
                "n_pairs": len(paired),
                "error": "Fewer than five clinically verified IDH-wildtype GBM primary/recurrent RNA pairs were available.",
                "access_tier": AccessTier.REGISTRATION_GATED.value,
                "gbm_specific": True,
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
            "status": "authorized_gbm_specific",
            "gbm_specific": True,
            "gene": gene,
            "entity_id": GLASS_TPM_ENTITY,
            "entity_version": getattr(expression_entity, "versionNumber", None),
            "clinical_entity_id": surgeries_entity,
            "scope": "Clinically verified GLASS IDH-wildtype glioblastoma, primary to first recurrence",
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
            "gbm_specific": False,
        }


def registration_reminder() -> str:
    return (
        "GLASS uses controlled Synapse access. Add SYNAPSE_AUTH_TOKEN from an account that has accepted the GLASS "
        f"access conditions. The RNA TPM matrix is {GLASS_TPM_ENTITY}; set {SURGERIES_ENTITY_ENV} explicitly if "
        "automatic clinical-table discovery cannot resolve the current surgery metadata entity."
    )
