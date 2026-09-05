#!/usr/bin/env python3
"""Canonical offline builder for the compact GBmap production reference.

This is intentionally an expensive one-time/pre-release build step. The live
Streamlit app never opens the full Core GBmap atlas.

The published CELLxGENE H5AD contains additional dense layers that can require
>30 GiB if anndata materializes them even in backed mode. This builder therefore
reads the HDF5 structures directly and touches only:

- ``obs/annotation_level_1``: Neoplastic / Non-neoplastic
- ``obs/annotation_level_3``: harmonized GBM cell state/type
- ``obs/patient`` (preferred) or standardized ``obs/donor_id``
- ``var/feature_name`` (or the var index as fallback)
- ``X``: the published expression matrix

For every gene/state it calculates cell-level expression breadth, mean published
X expression, and gene-specific patient prevalence among patients represented in
that state. Expression context is non-scoring and never treated as dependency,
causality, drug response, or clinical evidence.
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

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_gbmap_reference as source  # noqa: E402

STATE_COLUMN = "annotation_level_3"
CLASS_COLUMN = "annotation_level_1"
PATIENT_CANDIDATES = ("patient", "donor_id")


def _decode_scalar(value) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _decode_array(values):
    return [_decode_scalar(v) for v in values]


def _read_dataframe_column(group, name: str):
    """Read one H5AD dataframe column without materializing unrelated nodes."""
    import h5py
    import numpy as np

    node = group[name]
    if isinstance(node, h5py.Dataset):
        return np.asarray(_decode_array(node[()]), dtype=object)

    if isinstance(node, h5py.Group) and "codes" in node and "categories" in node:
        codes = node["codes"][()]
        categories = _decode_array(node["categories"][()])
        out = np.empty(len(codes), dtype=object)
        for idx, code in enumerate(codes):
            code = int(code)
            out[idx] = "" if code < 0 else categories[code]
        return out

    raise RuntimeError(
        f"Unsupported H5AD encoding for column {name!r}. "
        f"Node type={type(node).__name__}, keys={list(node.keys()) if hasattr(node, 'keys') else 'N/A'}"
    )


def _read_var_names(var_group):
    columns = set(var_group.keys())
    if "feature_name" in columns:
        names = _read_dataframe_column(var_group, "feature_name")
    else:
        index_name = var_group.attrs.get("_index", "_index")
        index_name = _decode_scalar(index_name)
        if index_name not in columns:
            for candidate in ("_index", "feature_id", "gene_id"):
                if candidate in columns:
                    index_name = candidate
                    break
        if index_name not in columns:
            raise RuntimeError(f"Could not resolve GBmap var names. var keys={sorted(columns)}")
        names = _read_dataframe_column(var_group, index_name)
    return [str(x).strip() for x in names]


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


def _sparse_encoding(node) -> str:
    raw = node.attrs.get("encoding-type", "")
    return _decode_scalar(raw).lower()


def _read_x_rows(x_node, start: int, stop: int, n_genes: int):
    """Read only an X row slice from dense or CSR-encoded H5AD storage."""
    import h5py
    import numpy as np
    import scipy.sparse as sp

    if isinstance(x_node, h5py.Dataset):
        return np.asarray(x_node[start:stop, :])

    if not isinstance(x_node, h5py.Group):
        raise RuntimeError(f"Unsupported GBmap X node type: {type(x_node).__name__}")

    encoding = _sparse_encoding(x_node)
    required = {"data", "indices", "indptr"}
    if not required.issubset(set(x_node.keys())):
        raise RuntimeError(f"Unsupported GBmap X sparse structure. encoding={encoding!r}, keys={sorted(x_node.keys())}")
    if "csr" not in encoding:
        raise RuntimeError(
            f"Core GBmap X is encoded as {encoding!r}; the memory-safe builder currently requires row-oriented CSR. "
            "Refusing to materialize a full CSC matrix."
        )

    indptr = x_node["indptr"][start : stop + 1]
    data_start = int(indptr[0])
    data_stop = int(indptr[-1])
    data = x_node["data"][data_start:data_stop]
    indices = x_node["indices"][data_start:data_stop]
    local_indptr = indptr.astype("int64", copy=True) - data_start
    return sp.csr_matrix((data, indices, local_indptr), shape=(stop - start, n_genes))


def build(h5ad_path: Path, output: Path, metadata_output: Path, chunk_size: int = 4096) -> dict:
    try:
        import h5py
        import numpy as np
        import scipy.sparse as sp
    except ImportError as exc:
        raise RuntimeError("GBmap build requires h5py, numpy and scipy.") from exc

    with h5py.File(h5ad_path, "r") as handle:
        if "obs" not in handle or "var" not in handle or "X" not in handle:
            raise RuntimeError(f"Published Core GBmap H5AD is missing obs/var/X. root keys={sorted(handle.keys())}")
        obs = handle["obs"]
        var = handle["var"]
        obs_columns = set(obs.keys())
        required = {STATE_COLUMN, CLASS_COLUMN}
        missing = sorted(required - obs_columns)
        if missing:
            raise RuntimeError(
                f"Published Core GBmap is missing expected annotation columns {missing}. "
                f"Available obs columns: {sorted(obs_columns)}"
            )
        patient_column = next((x for x in PATIENT_CANDIDATES if x in obs_columns), None)
        if patient_column is None:
            raise RuntimeError(
                f"Published Core GBmap has no supported patient identifier {PATIENT_CANDIDATES}. "
                f"Available obs columns: {sorted(obs_columns)}"
            )

        states = _read_dataframe_column(obs, STATE_COLUMN)
        classes_raw = _read_dataframe_column(obs, CLASS_COLUMN)
        patients_raw = _read_dataframe_column(obs, patient_column)
        if not (len(states) == len(classes_raw) == len(patients_raw)):
            raise RuntimeError("GBmap obs annotation lengths are inconsistent.")

        class_by_state: dict[str, str] = {}
        for state_raw, class_value in zip(states, classes_raw):
            state = str(state_raw)
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
            raise RuntimeError("No valid patient identifiers were found in Core GBmap metadata.")

        state_names = sorted({str(x) for x in states})
        state_index = {state: idx for idx, state in enumerate(state_names)}
        n_states = len(state_names)
        n_patients = len(patient_values)
        gene_names = _read_var_names(var)
        n_genes = len(gene_names)
        if len(set(gene_names)) != len(gene_names):
            duplicates = len(gene_names) - len(set(gene_names))
            raise RuntimeError(
                f"Core GBmap feature names contain {duplicates} duplicate gene label(s). "
                "Refusing to create ambiguous gene-level summaries."
            )

        n_cells = len(states)
        x_node = handle["X"]
        x_shape = tuple(int(x) for x in x_node.shape) if hasattr(x_node, "shape") and x_node.shape else None
        if x_shape is None and isinstance(x_node, h5py.Group):
            shape_attr = x_node.attrs.get("shape")
            if shape_attr is not None:
                x_shape = tuple(int(x) for x in shape_attr)
        if x_shape and x_shape != (n_cells, n_genes):
            raise RuntimeError(f"GBmap X shape {x_shape} does not match obs/var {(n_cells, n_genes)}")

        state_ids = np.fromiter((state_index[str(x)] for x in states), dtype=np.int16, count=n_cells)
        patient_ids = np.fromiter(
            (patient_index.get(_safe_patient(x), -1) for x in patients_raw),
            dtype=np.int32,
            count=n_cells,
        )

        sums = np.zeros((n_states, n_genes), dtype=np.float64)
        nonzero_cells = np.zeros((n_states, n_genes), dtype=np.int64)
        state_cell_counts = np.zeros(n_states, dtype=np.int64)
        state_patient_present = np.zeros((n_states, n_patients), dtype=np.bool_)
        patient_gene_present = np.zeros((n_states, n_patients, n_genes), dtype=np.bool_)

        for start in range(0, n_cells, int(chunk_size)):
            stop = min(n_cells, start + int(chunk_size))
            x = _read_x_rows(x_node, start, stop, n_genes)
            chunk_states = state_ids[start:stop]
            chunk_patients = patient_ids[start:stop]

            for s_idx in np.unique(chunk_states):
                cell_idx = np.flatnonzero(chunk_states == s_idx)
                state_cell_counts[s_idx] += len(cell_idx)
                sub = x[cell_idx]
                if sp.issparse(sub):
                    sums[s_idx] += np.asarray(sub.sum(axis=0)).ravel()
                    nonzero_cells[s_idx] += np.asarray(sub.getnnz(axis=0)).ravel()
                else:
                    dense = np.asarray(sub)
                    sums[s_idx] += dense.sum(axis=0)
                    nonzero_cells[s_idx] += (dense != 0).sum(axis=0)

                valid_patients = np.unique(chunk_patients[cell_idx])
                valid_patients = valid_patients[valid_patients >= 0]
                for p_idx in valid_patients:
                    state_patient_present[s_idx, p_idx] = True
                    p_cells = cell_idx[chunk_patients[cell_idx] == p_idx]
                    p_sub = x[p_cells]
                    if sp.issparse(p_sub):
                        present = np.asarray(p_sub.getnnz(axis=0)).ravel() > 0
                    else:
                        present = (np.asarray(p_sub) != 0).any(axis=0)
                    patient_gene_present[s_idx, p_idx] |= present

            if start == 0 or stop == n_cells or (start // int(chunk_size)) % 20 == 0:
                print(f"GBmap aggregation: {stop:,}/{n_cells:,} cells", flush=True)

    means = sums / np.maximum(state_cell_counts[:, None], 1)
    fractions = nonzero_cells / np.maximum(state_cell_counts[:, None], 1)
    gene_mean_across_states = means.mean(axis=0)
    gene_sd_across_states = means.std(axis=0)

    output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with gzip.open(output, "wt", newline="", encoding="utf-8", compresslevel=9) as out_handle:
        writer = csv.writer(out_handle)
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

    result = {
        "reference_schema_version": "1.1.0",
        "source_collection_id": source.COLLECTION_ID,
        "state_column": STATE_COLUMN,
        "class_column": CLASS_COLUMN,
        "patient_column": patient_column,
        "n_cells": n_cells,
        "n_patients": n_patients,
        "n_states": n_states,
        "n_genes": n_genes,
        "rows_written": rows_written,
        "output": str(output),
        "builder": "direct_hdf5_memory_safe",
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
    parser.add_argument("--chunk-size", type=int, default=4096)
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
