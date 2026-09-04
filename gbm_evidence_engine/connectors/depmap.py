"""DepMap functional-dependency connector.

Production queries use DepMap's public Breadbox REST API rather than pulling the
full quarterly matrices. The strict GBM group is the current OncoTree subtype
``Glioblastoma, IDH-Wildtype``; all other scored models form the comparator.
V6 also reports NextGen 3D/model-format context when current model metadata
exposes it, without changing the validated dependency score.

Synthetic CSVs are retained only for backwards-compatible method tests and are
never used by :func:`summarize_gene_dependency`.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

from gbm_evidence_engine.analysis.dependency import selective_dependency_test
from gbm_evidence_engine.evidence_model import AccessTier

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BREADBOX_BASE = "https://depmap.org/portal/breadbox"
DEPENDENCY_DATASET = "Chronos_Combined"
METADATA_DATASET = "depmap_model_metadata"
STRICT_GBM_SUBTYPE = "Glioblastoma, IDH-Wildtype"
USER_AGENT = "GBM-Gene-Analysis/6.0 (+https://github.com/rahzav/gbm-evidence-engine)"


@dataclass
class GeneEffectData:
    gene: str
    gbm_scores: "pd.Series"
    other_scores: "pd.Series"
    access_tier: AccessTier
    dataset_version: str


def _post_json(endpoint: str, payload: dict, timeout: int = 90, retries: int = 4):
    url = f"{BREADBOX_BASE}/{endpoint.lstrip('/')}"
    body = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code < 500:
                break
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"DepMap Breadbox request failed: {last_error or 'unknown error'}")


def _column_mapping_to_rows(raw: dict) -> dict[str, dict]:
    """Convert Breadbox's {column: {model_id: value}} metadata shape to rows."""
    out: dict[str, dict] = {}
    for column, values in (raw or {}).items():
        if not isinstance(values, dict):
            continue
        for model_id, value in values.items():
            out.setdefault(model_id, {})[column] = value
    return out


def _merge_metadata(base: dict[str, dict], extra: dict[str, dict]) -> dict[str, dict]:
    out = {key: dict(value) for key, value in base.items()}
    for model_id, values in extra.items():
        out.setdefault(model_id, {}).update(values)
    return out


def _nextgen_flag(row: dict) -> bool:
    model_type = str(row.get("ModelType") or "").casefold()
    growth = str(row.get("GrowthPattern") or row.get("CellFormat") or "").casefold()
    return "organoid" in model_type or growth in {"spheroid", "dome"}


def summarize_gene_dependency(gene: str) -> dict:
    """Return a live, GBM-specific Chronos dependency summary for one gene."""
    gene = gene.upper().strip()
    try:
        raw_scores = _post_json(
            f"datasets/matrix/{DEPENDENCY_DATASET}",
            {"features": [gene], "feature_identifier": "label"},
        )
        values = raw_scores.get(gene) if isinstance(raw_scores, dict) else None
        if values is None and isinstance(raw_scores, dict) and raw_scores:
            values = next(iter(raw_scores.values()))
        if not isinstance(values, dict) or not values:
            return {"ok": False, "gene": gene, "error": "Gene was not returned by the DepMap dependency matrix."}

        raw_meta = _post_json(
            f"datasets/tabular/{METADATA_DATASET}",
            {"columns": ["CellLineName", "OncotreeLineage", "OncotreePrimaryDisease", "OncotreeSubtype"]},
        )
        metadata = _column_mapping_to_rows(raw_meta if isinstance(raw_meta, dict) else {})

        # 26Q1 introduced NextGen CNS models and richer model metadata. Because
        # Breadbox schemas may change, request these columns separately and
        # degrade gracefully if a deployment does not expose them.
        nextgen_metadata_available = False
        try:
            raw_extra = _post_json(
                f"datasets/tabular/{METADATA_DATASET}",
                {"columns": ["ModelType", "GrowthPattern", "SerumFreeMedia"]},
                timeout=45,
                retries=1,
            )
            extra = _column_mapping_to_rows(raw_extra if isinstance(raw_extra, dict) else {})
            if extra:
                metadata = _merge_metadata(metadata, extra)
                nextgen_metadata_available = True
        except Exception:
            pass

        gbm, other = [], []
        gbm_models = []
        nextgen_scores: list[float] = []
        conventional_scores: list[float] = []
        for model_id, raw_value in values.items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(value):
                continue
            row = metadata.get(model_id, {})
            subtype = str(row.get("OncotreeSubtype") or "")
            if subtype == STRICT_GBM_SUBTYPE:
                is_nextgen = _nextgen_flag(row)
                gbm.append(value)
                if is_nextgen:
                    nextgen_scores.append(value)
                else:
                    conventional_scores.append(value)
                gbm_models.append({
                    "model_id": model_id,
                    "cell_line": row.get("CellLineName"),
                    "dependency": value,
                    "model_type": row.get("ModelType"),
                    "growth_pattern": row.get("GrowthPattern"),
                    "serum_free_media": row.get("SerumFreeMedia"),
                    "nextgen_3d_context": is_nextgen,
                })
            else:
                other.append(value)

        if len(gbm) < 3 or len(other) < 20:
            return {
                "ok": False,
                "gene": gene,
                "error": f"Insufficient strict GBM models for a selective-dependency test (GBM n={len(gbm)}).",
                "n_gbm": len(gbm),
                "n_other": len(other),
            }

        result = selective_dependency_test(gene, np.asarray(gbm), np.asarray(other))
        delta = result.median_effect_other - result.median_effect_gbm
        gbm_models.sort(key=lambda row: row["dependency"])
        nextgen_context = {
            "metadata_available": nextgen_metadata_available,
            "n_nextgen_3d_gbm": len(nextgen_scores),
            "n_conventional_gbm": len(conventional_scores),
            "median_nextgen_3d_chronos": float(np.median(nextgen_scores)) if nextgen_scores else None,
            "median_conventional_chronos": float(np.median(conventional_scores)) if conventional_scores else None,
            "interpretation": (
                "NextGen/model-format stratification is contextual. Differences between 3D and conventional models may reflect biology, culture conditions, library composition, or sample selection and are not separately scored."
            ),
        }
        return {
            "ok": True,
            "gene": gene,
            "dataset_id": DEPENDENCY_DATASET,
            "gbm_definition": STRICT_GBM_SUBTYPE,
            "n_gbm": result.n_gbm_lines,
            "n_other": result.n_other_lines,
            "median_effect_gbm": result.median_effect_gbm,
            "median_effect_other": result.median_effect_other,
            "median_selectivity_delta": float(delta),
            "u_statistic": result.u_statistic,
            "p_value": result.p_value,
            "rank_biserial_effect_size": result.rank_biserial_effect_size,
            "pan_essential": result.pan_essential,
            "gbm_fraction_below_minus_0_5": float(np.mean(np.asarray(gbm) < -0.5)),
            "other_fraction_below_minus_0_5": float(np.mean(np.asarray(other) < -0.5)),
            "most_dependent_gbm_models": gbm_models[:10],
            "nextgen_model_context": nextgen_context,
            "access_tier": AccessTier.OPEN_LIVE_API.value,
            "source": "DepMap Breadbox / Chronos_Combined",
        }
    except Exception as exc:
        return {"ok": False, "gene": gene, "error": str(exc)}


def load_gene_effect_scores(gene: str) -> GeneEffectData:
    """Backward-compatible method-test loader; never used by live prioritisation."""
    synthetic_path = DATA_DIR / f"synthetic_depmap_effect_scores_{gene}.csv"
    if not synthetic_path.exists():
        raise FileNotFoundError(f"No synthetic dependency method-test snapshot for {gene}.")
    df = pd.read_csv(synthetic_path)
    gbm = df.loc[df.lineage == "glioblastoma", "gene_effect_score"]
    other = df.loc[df.lineage == "other", "gene_effect_score"]
    return GeneEffectData(
        gene=gene,
        gbm_scores=gbm,
        other_scores=other,
        access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
        dataset_version="SYNTHETIC method-test snapshot — not a DepMap release",
    )
