#!/usr/bin/env python3
"""Canonical offline builder for the compact GBmap production reference.

This builder is intentionally expensive once so production queries remain cheap.
It converts the published Core GBmap H5AD into a compact gene-by-state summary
using the authors' annotation hierarchy:

- annotation_level_1: Neoplastic / Non-neoplastic
- annotation_level_3: harmonized cell state/type
- patient: patient identifier

For each gene/state it calculates cell-level expression breadth, mean normalized
expression, and *gene-specific* patient prevalence among patients represented in
that state. Patient prevalence is therefore not a proxy for state abundance.

The full atlas is never used by the interactive Streamlit process.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import sys
import tempfile
from pathlib import Path

# Allow execution as ``python scripts/build_gbmap_reference_v3.py``.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_gbmap_reference as source  # noqa: E402

STATE_COLUMN = "annotation_level_3"
CLASS_COLUMN = "annotation_level_1"
PATIENT_COLUMN = "patient"


def _class_label(value: str) -> str:
    cleaned = str(value or "").strip().lower().replace("_", "-")
    if cleaned in {"neoplastic", "malignant"}:
        return "malignant"
    if cleaned in {"non-neoplastic", "nonneoplastic", "non-neoplastic cell", "nonneoplastic cell"}:
        return "microenvironment"
    raise ValueError(f"Unrecognized GBmap annotation_level_1 value: {value!r}")


def _safe_patient(value: str) -> str | None:
    value = str(value or "").strip()
    if not value or value.lower() in {"nan", "none", "unknown", "na"}:
        return None
    return value


def build(h5ad_path: Path, output: Path, metadata_output: Path, chunk_size: int = 2048) -> dict:
    try:
        import anndata as ad
        import numpy as np
        import scipy.sparse as sp
    except ImportError as exc:
        raise RuntimeError("GBmap build requires anndata, numpy, scipy and h5py.") from exc

    data = ad.read_h5ad(h5ad_path, backed="r")
    obs = data.obs
    required = {STATE_COLUMN, CLASS_COLUMN, PATIENT_COLUMN}
    missing = sorted(required - set(map(str, obs.columns)))
    if missing:
        available = list(map(str, obs.columns))
        raise RuntimeError(
            f"Published Core GBmap is missing expected annotation columns {missing}. "
            f"Available obs columns: {available}"
        )

    states = obs[STATE_COLUMN].astype(str).fillna("Unknown").to_numpy()
    classes_raw = obs[CLASS_COLUMN].astype(str).fillna("").to_numpy()
    patients_raw = obs[PATIENT_COLUMN].astype(str).fillna("").to_numpy()

    # Validate the author's level-1 classes before touching expression data.
    class_by_state: dict[str, str] = {}
    for state, class_value in zip(states, classes_raw):
        label = _class_label(class_value)
        prior = class_by_state.get(state)
        if prior is not None and prior != label:
            raise RuntimeError(
                f"GBmap state {state!r} maps to both malignant and microenvironment level-1 classes; refusing ambiguous build."
            )
        class_by_state[state] = label

    patient_values = sorted({p for raw in patients_raw if (p := _safe_patient(raw)) is not None})
    patient_index = {p: idx for idx, p in enumerate(patient_values)}
    if not patient_values:
        raise RuntimeError("No valid patient identifiers were found in the published Core GBmap metadata.")

    state_names = sorted(set(states))
    state_index = {state: idx for idx, state in enumerate(state_names)}
    n_states = len(state_names)
    n_patients = len(patient_values)
    n_genes = int(data.n_vars)
    gene_series = data.var.get("feature_name") if "feature_name" in data.var.columns else None
    gene_names = [str(x) for x in (gene_series.to_numpy() if gene_series is not None else data.var_names)]

    # Core aggregate arrays remain modest. The state/patient/gene boolean cube
    # is the largest structure but is still far smaller than the full atlas and
    # lets us calculate true gene-specific patient breadth without retaining cells.
    sums = np.zeros((n_states, n_genes), dtype=np.float64)
    nonzero_cells = np.zeros((n_states, n_genes), dtype=np.int64)
    state_cell_counts = np.zeros(n_states, dtype=np.int64)
    state_patient_present = np.zeros((n_states, n_patients), dtype=np.bool_)
    patient_gene_present = np.zeros((n_states, n_patients, n_genes), dtype=np.bool_)

    for start in range(0, int(data.n_obs), int(chunk_size)):
        stop = min(int(data.n_obs), start + int(chunk_size))
        x = data.X[start:stop]
        if sp.issparse(x):
            x = x.tocsr()
        else:
            x = np.asarray(x)
        chunk_states = states[start:stop]
        chunk_patients = patients_raw[start:stop]

        # State-level cell means and fractions.
        for state in set(chunk_states):
            s_idx = state_index[state]
            cell_idx = np.where(chunk_states == state)[0]
            state_cell_counts[s_idx] += len(cell_idx)
            sub = x[cell_idx]
            if sp.issparse(sub):
                sums[s_idx] += np.asarray(sub.sum(axis=0)).ravel()
                nonzero_cells[s_idx] += np.asarray((sub != 0).sum(axis=0)).ravel()
            else:
                sums[s_idx] += np.asarray(sub).sum(axis=0)
                nonzero_cells[s_idx] += (np.asarray(sub) != 0).sum(axis=0)

            # Patient breadth for this gene/state. Because a patient's cells may
            # span chunks, booleans are OR-ed rather than counted repeatedly.
            local_patients = {_safe_patient(chunk_patients[i]) for i in cell_idx}
            local_patients.discard(None)
            for patient in local_patients:
                p_idx = patient_index[patient]
                state_patient_present[s_idx, p_idx] = True
                p_cells = [i for i in cell_idx if _safe_patient(chunk_patients[i]) == patient]
                p_sub = x[p_cells]
                if sp.issparse(p_sub):
                    present = np.asarray((p_sub != 0).sum(axis=0)).ravel() > 0
                else:
                    present = (np.asarray(p_sub) != 0).any(axis=0)
                patient_gene_present[s_idx, p_idx] |= present

        if start == 0 or stop == int(data.n_obs) or (start // int(chunk_size)) % 20 == 0:
            print(f"GBmap aggregation: {stop:,}/{int(data.n_obs):,} cells", flush=True)

    means = sums / np.maximum(state_cell_counts[:, None], 1)
    fractions = nonzero_cells / np.maximum(state_cell_counts[:, None], 1)
    gene_mean_across_states = means.mean(axis=0)
    gene_sd_across_states = means.std(axis=0)

    output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with gzip.open(output, "wt", newline="", encoding="utf-8", compresslevel=9) as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "gene", "state", "state_class", "n_cells", "n_state_patients",
            "n_expressing_patients", "patient_prevalence", "fraction_expressing",
            "mean_expression", "expression_z_across_states",
        ])
        for s_idx, state in enumerate(state_names):
            state_patient_count = int(state_patient_present[s_idx].sum())
            if state_patient_count == 0:
                continue
            patient_counts = patient_gene_present[s_idx].sum(axis=0)
            for g_idx, gene in enumerate(gene_names):
                if nonzero_cells[s_idx, g_idx] == 0:
                    continue
                sd = float(gene_sd_across_states[g_idx])
                z = 0.0 if sd <= 0 else (
                    float(means[s_idx, g_idx]) - float(gene_mean_across_states[g_idx])
                ) / sd
                n_expressing_patients = int(patient_counts[g_idx])
                writer.writerow([
                    gene,
                    state,
                    class_by_state[state],
                    int(state_cell_counts[s_idx]),
                    state_patient_count,
                    n_expressing_patients,
                    round(n_expressing_patients / state_patient_count, 6),
                    round(float(fractions[s_idx, g_idx]), 6),
                    round(float(means[s_idx, g_idx]), 6),
                    round(z, 6),
                ])
                rows_written += 1

    try:
        data.file.close()
    except Exception:
        pass

    result = {
        "reference_schema_version": "1.0.0",
        "source_collection_id": source.COLLECTION_ID,
        "state_column": STATE_COLUMN,
        "class_column": CLASS_COLUMN,
        "patient_column": PATIENT_COLUMN,
        "n_cells": int(len(states)),
        "n_patients": n_patients,
        "n_states": n_states,
        "n_genes": n_genes,
        "rows_written": rows_written,
        "output": str(output),
        "semantics": {
            "patient_prevalence": "n patients with >=1 expressing cell / n patients represented in that state",
            "fraction_expressing": "expressing cells / cells in that state",
            "mean_expression": "mean value of published Core GBmap X matrix within state",
            "expression_z_across_states": "z-score of state mean across annotation_level_3 states for the same gene",
        },
        "caveat": "Expression breadth and enrichment are contextual; they do not establish dependency, causality, drug response or clinical utility.",
    }
    metadata_output.parent.mkdir(parents=True, exist_ok=True)
    metadata_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/gbmap_gene_state_summary.csv.gz")
    parser.add_argument("--metadata-output", default="data/gbmap_reference_metadata.json")
    parser.add_argument("--h5ad")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=2048)
    args = parser.parse_args()

    dataset = source._find_core_dataset()
    url, size = source._asset_url(dataset)
    remote = {
        "dataset_title": dataset.get("title") or dataset.get("name"),
        "dataset_id": dataset.get("dataset_id") or dataset.get("id"),
        "dataset_version_id": dataset.get("dataset_version_id"),
        "asset_url": url,
        "asset_size": size,
        "cell_count": dataset.get("cell_count"),
        "published_at": dataset.get("published_at"),
        "schema_version": dataset.get("schema_version"),
    }
    print(json.dumps(remote, indent=2), flush=True)
    if args.metadata_only:
        return

    output = Path(args.output)
    metadata_output = Path(args.metadata_output)
    if args.h5ad:
        result = build(Path(args.h5ad), output, metadata_output, chunk_size=args.chunk_size)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            h5ad_path = Path(tmpdir) / "core_gbmap.h5ad"
            print(f"Downloading published Core GBmap ({size or 'unknown'} bytes)...", flush=True)
            source._download(url, h5ad_path)
            result = build(h5ad_path, output, metadata_output, chunk_size=args.chunk_size)
    result["source_dataset"] = remote
    metadata_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
