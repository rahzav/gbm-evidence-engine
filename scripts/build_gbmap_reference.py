#!/usr/bin/env python3
"""Build a compact gene-by-cell-state GBmap reference for production use.

This is an offline/pre-release build step, never an interactive app request.
It downloads the published Core GBmap H5AD from CELLxGENE, discovers the most
informative cell-state/patient annotation columns, and aggregates expression in
chunks so the full matrix is not materialized in RAM.

Output schema (CSV.GZ):
    gene,state,state_class,n_cells,n_patients,patient_prevalence,
    fraction_expressing,mean_expression,median_expression,
    expression_z_across_states

The script intentionally refuses to invent malignant-state labels. If it cannot
identify a suitable author-provided state annotation, it exits and prints the
available obs columns so a human can map the published schema explicitly.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import os
import shutil
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path

COLLECTION_ID = "999f2a15-3d7e-440b-96ae-2c806799c08c"
API = "https://api.cellxgene.cziscience.com/curation/v1"
USER_AGENT = "GBM-Gene-Analysis-GBmap-Builder/1.0"

STATE_CANDIDATES = [
    "annotation_level_3",
    "annotation_level_2",
    "cell_state",
    "cell_state_simple",
    "state",
    "cell_type",
]
CLASS_CANDIDATES = [
    "malignant",
    "malignancy",
    "cell_type_group",
    "annotation_level_1",
    "cell_compartment",
]
PATIENT_CANDIDATES = ["donor_id", "patient_id", "patient", "sample_patient", "individual"]

MALIGNANT_HINTS = {
    "malignant", "neoplastic", "tumor", "tumour", "cancer",
    "ac-like", "mes-like", "npc-like", "opc-like", "ac", "mes", "npc", "opc",
}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _find_core_dataset() -> dict:
    # Prefer the collection endpoint; fall back to the all-datasets endpoint.
    candidates = []
    try:
        collection = _get_json(f"{API}/collections/{COLLECTION_ID}")
        if isinstance(collection, dict):
            for key in ("datasets", "dataset_versions"):
                value = collection.get(key)
                if isinstance(value, list):
                    candidates.extend(x for x in value if isinstance(x, dict))
    except Exception:
        pass
    if not candidates:
        datasets = _get_json(f"{API}/datasets")
        if isinstance(datasets, list):
            candidates = [
                d for d in datasets
                if isinstance(d, dict) and str(d.get("collection_id") or "") == COLLECTION_ID
            ]
    if not candidates:
        raise RuntimeError("Could not resolve GBmap datasets from CELLxGENE Discover API.")

    def title(d):
        return str(d.get("title") or d.get("name") or "")

    core = [d for d in candidates if "core gbmap" in title(d).lower()]
    if not core:
        core = [d for d in candidates if "gbmap" in title(d).lower()]
    if not core:
        raise RuntimeError(f"GBmap collection resolved but no GBmap dataset was found. Titles: {[title(d) for d in candidates]}")
    return core[0]


def _asset_url(dataset: dict) -> tuple[str, int | None]:
    assets = dataset.get("assets") or dataset.get("dataset_assets") or []
    if isinstance(assets, dict):
        assets = list(assets.values())
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        filetype = str(asset.get("filetype") or asset.get("type") or asset.get("format") or "").lower()
        url = asset.get("url") or asset.get("download_url") or asset.get("uri")
        if url and ("h5ad" in filetype or str(url).lower().endswith(".h5ad")):
            size = asset.get("filesize") or asset.get("file_size") or asset.get("size")
            try:
                size = int(size)
            except (TypeError, ValueError):
                size = None
            return str(url), size

    # Current Discover assets can also be addressed by dataset version id.
    for key in ("dataset_version_id", "version_id", "id"):
        version = dataset.get(key)
        if version:
            return f"https://datasets.cellxgene.cziscience.com/{version}.h5ad", None
    raise RuntimeError(f"No downloadable H5AD asset found in dataset metadata keys={sorted(dataset)}")


def _download(url: str, destination: Path):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)


def _first_existing(columns, candidates):
    lower = {str(c).lower(): c for c in columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def _classify_state(state: str, class_value: str | None) -> str:
    text = f"{state} {class_value or ''}".lower()
    if any(hint in text for hint in MALIGNANT_HINTS):
        return "malignant"
    return "microenvironment"


def _normal_cdf_like(value: float, mean: float, sd: float) -> float:
    return 0.0 if sd <= 0 else (value - mean) / sd


def build(h5ad_path: Path, output: Path, state_column: str | None = None, patient_column: str | None = None, class_column: str | None = None, chunk_size: int = 4096):
    try:
        import anndata as ad
        import numpy as np
        import scipy.sparse as sp
    except ImportError as exc:
        raise RuntimeError("Builder requires anndata, numpy and scipy. Install anndata>=0.10 h5py scipy.") from exc

    data = ad.read_h5ad(h5ad_path, backed="r")
    obs = data.obs
    state_column = state_column or _first_existing(obs.columns, STATE_CANDIDATES)
    patient_column = patient_column or _first_existing(obs.columns, PATIENT_CANDIDATES)
    class_column = class_column or _first_existing(obs.columns, CLASS_CANDIDATES)

    if not state_column or not patient_column:
        raise RuntimeError(
            "Could not safely identify GBmap state/patient annotations. "
            f"obs columns={list(map(str, obs.columns))}. "
            "Re-run with --state-column and --patient-column using published GBmap annotations."
        )

    states = obs[state_column].astype(str).fillna("Unknown").to_numpy()
    patients = obs[patient_column].astype(str).fillna("Unknown").to_numpy()
    classes = obs[class_column].astype(str).fillna("").to_numpy() if class_column else [""] * len(obs)
    unique_patients = {p for p in patients if p and p.lower() not in {"nan", "unknown", "none"}}
    n_total_patients = max(1, len(unique_patients))

    # Map state labels to compact integer buckets.
    state_names = sorted(set(states))
    state_index = {state: idx for idx, state in enumerate(state_names)}
    n_states = len(state_names)
    n_genes = data.n_vars
    gene_names = [str(x) for x in (data.var.get("feature_name", data.var_names))]

    sums = np.zeros((n_states, n_genes), dtype=np.float64)
    nonzero = np.zeros((n_states, n_genes), dtype=np.int64)
    counts = np.zeros(n_states, dtype=np.int64)
    patient_sets = [set() for _ in range(n_states)]
    state_class_votes = [defaultdict(int) for _ in range(n_states)]

    # Median across hundreds of thousands of cells for every gene/state is too
    # expensive for a compact build. We calculate exact state means and
    # expression fractions, while median_expression is intentionally left blank.
    # The runtime/UI labels this explicitly.
    for start in range(0, data.n_obs, chunk_size):
        stop = min(data.n_obs, start + chunk_size)
        x = data.X[start:stop]
        if sp.issparse(x):
            x = x.tocsr()
        else:
            x = np.asarray(x)
        chunk_states = states[start:stop]
        chunk_patients = patients[start:stop]
        chunk_classes = classes[start:stop]
        for local_state in set(chunk_states):
            mask = np.where(chunk_states == local_state)[0]
            idx = state_index[local_state]
            counts[idx] += len(mask)
            for patient in set(chunk_patients[mask]):
                if patient and patient.lower() not in {"nan", "unknown", "none"}:
                    patient_sets[idx].add(patient)
            for class_value in chunk_classes[mask]:
                state_class_votes[idx][_classify_state(local_state, str(class_value))] += 1
            sub = x[mask]
            if sp.issparse(sub):
                sums[idx] += np.asarray(sub.sum(axis=0)).ravel()
                nonzero[idx] += np.asarray((sub != 0).sum(axis=0)).ravel()
            else:
                sums[idx] += sub.sum(axis=0)
                nonzero[idx] += (sub != 0).sum(axis=0)

    means = sums / np.maximum(counts[:, None], 1)
    fractions = nonzero / np.maximum(counts[:, None], 1)
    state_gene_mean = means.mean(axis=0)
    state_gene_sd = means.std(axis=0)

    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", newline="", encoding="utf-8", compresslevel=9) as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "gene", "state", "state_class", "n_cells", "n_patients", "patient_prevalence",
            "fraction_expressing", "mean_expression", "median_expression", "expression_z_across_states",
        ])
        for s_idx, state in enumerate(state_names):
            state_class = max(state_class_votes[s_idx], key=state_class_votes[s_idx].get) if state_class_votes[s_idx] else _classify_state(state, None)
            prevalence = len(patient_sets[s_idx]) / n_total_patients
            for g_idx, gene in enumerate(gene_names):
                if nonzero[s_idx, g_idx] == 0:
                    continue
                z = _normal_cdf_like(float(means[s_idx, g_idx]), float(state_gene_mean[g_idx]), float(state_gene_sd[g_idx]))
                writer.writerow([
                    gene,
                    state,
                    state_class,
                    int(counts[s_idx]),
                    len(patient_sets[s_idx]),
                    round(prevalence, 6),
                    round(float(fractions[s_idx, g_idx]), 6),
                    round(float(means[s_idx, g_idx]), 6),
                    "",
                    round(z, 6),
                ])
    data.file.close()
    return {
        "output": str(output),
        "state_column": str(state_column),
        "patient_column": str(patient_column),
        "class_column": None if class_column is None else str(class_column),
        "n_states": n_states,
        "n_patients": n_total_patients,
        "n_genes": n_genes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/gbmap_gene_state_summary.csv.gz")
    parser.add_argument("--h5ad")
    parser.add_argument("--state-column")
    parser.add_argument("--patient-column")
    parser.add_argument("--class-column")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=4096)
    args = parser.parse_args()

    dataset = _find_core_dataset()
    url, size = _asset_url(dataset)
    metadata = {
        "dataset_title": dataset.get("title") or dataset.get("name"),
        "dataset_id": dataset.get("dataset_id") or dataset.get("id"),
        "asset_url": url,
        "asset_size": size,
        "keys": sorted(dataset),
    }
    print(json.dumps(metadata, indent=2))
    if args.metadata_only:
        return

    if args.h5ad:
        h5ad_path = Path(args.h5ad)
        result = build(
            h5ad_path,
            Path(args.output),
            state_column=args.state_column,
            patient_column=args.patient_column,
            class_column=args.class_column,
            chunk_size=args.chunk_size,
        )
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            h5ad_path = Path(tmpdir) / "gbmap_core.h5ad"
            print(f"Downloading {url} -> {h5ad_path}")
            _download(url, h5ad_path)
            result = build(
                h5ad_path,
                Path(args.output),
                state_column=args.state_column,
                patient_column=args.patient_column,
                class_column=args.class_column,
                chunk_size=args.chunk_size,
            )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
