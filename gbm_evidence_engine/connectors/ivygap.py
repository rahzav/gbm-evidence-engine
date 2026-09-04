"""Ivy Glioblastoma Atlas Project spatial-expression connector.

The normalized RNA-seq release is an open Allen Institute ZIP containing a
270-column FPKM matrix, gene metadata and laser-microdissection structure
metadata. The file is downloaded once into the local cache, then individual
genes are streamed from the matrix so per-gene queries do not load ~86 MB of
text into memory.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
import io
import math
from pathlib import Path
import threading
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from gbm_evidence_engine.analysis.spatial import IVYGAP_ANATOMIC_ZONES, anatomic_enrichment_test
from gbm_evidence_engine.evidence_model import AccessTier
from .base import CACHE_DIR

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
IVY_DIR = CACHE_DIR / "ivygap"
IVY_DIR.mkdir(parents=True, exist_ok=True)
IVY_ZIP = IVY_DIR / "normalized_rnaseq.zip"
IVY_URL = "https://glioblastoma.alleninstitute.org/api/v2/well_known_file_download/305873915"
USER_AGENT = "GBM-Evidence-Engine/3.0 (+https://github.com/rahzav/gbm-evidence-engine)"
_DOWNLOAD_LOCK = threading.Lock()


@dataclass
class ZoneExpressionData:
    gene: str
    zone_expression: dict
    access_tier: AccessTier
    dataset_version: str


def _download_snapshot() -> Path:
    if IVY_ZIP.exists() and IVY_ZIP.stat().st_size > 1_000_000:
        return IVY_ZIP
    with _DOWNLOAD_LOCK:
        if IVY_ZIP.exists() and IVY_ZIP.stat().st_size > 1_000_000:
            return IVY_ZIP
        tmp = IVY_ZIP.with_suffix(".tmp")
        req = urllib.request.Request(IVY_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if tmp.stat().st_size < 1_000_000 or not zipfile.is_zipfile(tmp):
            tmp.unlink(missing_ok=True)
            raise RuntimeError("Ivy GAP normalized RNA-seq download was incomplete or invalid.")
        tmp.replace(IVY_ZIP)
    return IVY_ZIP


def _zone_from_structure(abbrev: str) -> str | None:
    value = (abbrev or "").strip()
    # Match the specific CT-derived histologic zones before generic CT.
    if value.startswith("CTpnz"):
        return "perinecrotic_zone"
    if value.startswith("CTpan"):
        return "pseudopalisading_cells_around_necrosis"
    if value.startswith("CTmvp"):
        return "microvascular_proliferation"
    if value.startswith("CThbv"):
        return "hyperplastic_blood_vessels"
    if value.startswith("LE"):
        return "leading_edge"
    if value.startswith("IT"):
        return "infiltrating_tumor"
    if value.startswith("CT"):
        return "cellular_tumor"
    return None


def _read_live_gene(gene: str) -> tuple[dict[str, np.ndarray], dict]:
    path = _download_snapshot()
    gene = gene.upper().strip()
    with zipfile.ZipFile(path) as zf:
        # Resolve symbol -> stable row gene_id.
        gene_id = None
        with zf.open("rows-genes.csv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            for row in reader:
                if (row.get("gene_symbol") or "").upper() == gene:
                    gene_id = str(row.get("gene_id"))
                    break
        if not gene_id:
            raise KeyError(f"{gene} is not present in the Ivy GAP normalized RNA-seq gene table.")

        # Column order is keyed by rna_well_id.
        with zf.open("columns-samples.csv") as raw:
            samples = list(csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")))
        sample_by_well = {str(row["rna_well_id"]): row for row in samples}

        values_by_well = None
        with zf.open("fpkm_table.csv") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
            reader = csv.reader(text)
            header = next(reader)
            wells = [str(x) for x in header[1:]]
            for row in reader:
                if row and str(row[0]) == gene_id:
                    vals = []
                    for value in row[1:]:
                        try:
                            vals.append(float(value))
                        except (TypeError, ValueError):
                            vals.append(float("nan"))
                    values_by_well = dict(zip(wells, vals))
                    break
        if values_by_well is None:
            raise KeyError(f"{gene} resolved in Ivy metadata but not in the FPKM matrix.")

    grouped: dict[str, list[float]] = {z: [] for z in IVYGAP_ANATOMIC_ZONES}
    for well, fpkm in values_by_well.items():
        if not math.isfinite(fpkm):
            continue
        meta = sample_by_well.get(well)
        if not meta:
            continue
        zone = _zone_from_structure(meta.get("structure_abbreviation", ""))
        if zone:
            grouped[zone].append(math.log2(max(0.0, fpkm) + 1.0))

    arrays = {zone: np.asarray(vals, dtype=float) for zone, vals in grouped.items()}
    metadata = {
        "gene_id": gene_id,
        "n_matrix_samples": len(values_by_well),
        "zone_counts": {zone: len(vals) for zone, vals in grouped.items()},
    }
    return arrays, metadata


def summarize_spatial_expression(gene: str) -> dict:
    gene = gene.upper().strip()
    try:
        zones, meta = _read_live_gene(gene)
        result = anatomic_enrichment_test(gene, zones)
        medians = result.zone_medians
        spread = max(medians.values()) - min(medians.values()) if medians else None
        return {
            "ok": True,
            "gene": gene,
            "dataset": "Ivy GAP normalized RNA-seq (FPKM)",
            "download_id": "305873915",
            "transform": "log2(FPKM + 1)",
            "n_samples": result.n_samples_total,
            "n_matrix_samples": meta["n_matrix_samples"],
            "zone_counts": meta["zone_counts"],
            "zone_medians": medians,
            "top_zone": result.top_zone,
            "median_range": float(spread) if spread is not None else None,
            "kruskal_h": result.h_statistic,
            "p_value": result.p_value,
            "access_tier": AccessTier.OPEN_BULK_DOWNLOAD.value,
        }
    except Exception as exc:
        return {"ok": False, "gene": gene, "error": str(exc)}


def load_zone_expression(gene: str) -> ZoneExpressionData:
    """Backward-compatible synthetic loader used only by method tests."""
    path = DATA_DIR / f"synthetic_ivygap_zone_expression_{gene}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No synthetic Ivy GAP method-test snapshot for {gene}.")
    df = pd.read_csv(path)
    zone_expression = {
        zone: df.loc[df.anatomic_zone == zone, "log2_expression"].to_numpy()
        for zone in IVYGAP_ANATOMIC_ZONES
    }
    return ZoneExpressionData(
        gene=gene,
        zone_expression=zone_expression,
        access_tier=AccessTier.SYNTHETIC_ILLUSTRATIVE,
        dataset_version="SYNTHETIC method-test snapshot — not the Ivy GAP release",
    )
