#!/usr/bin/env python3
"""Print exact Core GBmap features sharing the same feature_name label."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import h5py

from build_gbmap_reference_v3 import _decode_scalar, _read_dataframe_column


def optional_column(var, name):
    if name not in var:
        return None
    try:
        return _read_dataframe_column(var, name)
    except Exception as exc:
        print(f"Could not read optional var column {name}: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("h5ad")
    args = parser.parse_args()

    with h5py.File(Path(args.h5ad), "r") as handle:
        var = handle["var"]
        print("VAR_KEYS", sorted(var.keys()))
        names = [str(x).strip() for x in _read_dataframe_column(var, "feature_name")]
        counts = Counter(names)
        dup_names = sorted(name for name, count in counts.items() if count > 1)
        print("DUPLICATE_LABEL_COUNT", len(dup_names))

        index_name = _decode_scalar(var.attrs.get("_index", "_index"))
        feature_ids = optional_column(var, index_name) if index_name in var else optional_column(var, "feature_id")
        biotypes = optional_column(var, "feature_biotype")
        gene_ids = optional_column(var, "gene_id")

        positions = defaultdict(list)
        for idx, name in enumerate(names):
            if name in dup_names:
                positions[name].append(idx)

        for name in dup_names:
            print(f"DUPLICATE {name!r}")
            for idx in positions[name]:
                print({
                    "column_index": idx,
                    "feature_id": None if feature_ids is None else str(feature_ids[idx]),
                    "gene_id": None if gene_ids is None else str(gene_ids[idx]),
                    "feature_biotype": None if biotypes is None else str(biotypes[idx]),
                })


if __name__ == "__main__":
    main()
