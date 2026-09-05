#!/usr/bin/env python3
"""Patch the GBmap builder/runtime to preserve duplicate-symbol feature identity."""
from pathlib import Path


# Builder: preserve every published Ensembl feature and record duplicate labels.
p = Path("scripts/build_gbmap_reference_v3.py")
t = p.read_text()
if "from collections import Counter" not in t:
    t = t.replace("import csv\n", "import csv\nfrom collections import Counter\n", 1)

old = '''        gene_names = _read_var_names(var)\n        n_genes = len(gene_names)\n        if len(set(gene_names)) != len(gene_names):\n            duplicates = len(gene_names) - len(set(gene_names))\n            raise RuntimeError(\n                f"Core GBmap feature names contain {duplicates} duplicate gene label(s). "\n                "Refusing to create ambiguous gene-level summaries."\n            )\n'''
new = '''        gene_names = _read_var_names(var)\n        n_genes = len(gene_names)  # published feature columns, not unique symbols\n        feature_id_column = _decode_scalar(var.attrs.get("_index", "_index"))\n        if feature_id_column not in var:\n            raise RuntimeError(\n                f"Could not resolve Core GBmap feature IDs from var index {feature_id_column!r}. "\n                f"var keys={sorted(var.keys())}"\n            )\n        feature_ids = [str(x).strip() for x in _read_dataframe_column(var, feature_id_column)]\n        if len(feature_ids) != n_genes or len(set(feature_ids)) != len(feature_ids):\n            raise RuntimeError("Core GBmap feature IDs are missing or non-unique; refusing ambiguous feature-level aggregation.")\n        label_counts = Counter(gene_names)\n        duplicate_labels = sorted(label for label, count in label_counts.items() if count > 1)\n        duplicate_gene_features = {\n            label: [feature_ids[idx] for idx, value in enumerate(gene_names) if value == label]\n            for label in duplicate_labels\n        }\n        if duplicate_gene_features:\n            print("Preserving duplicate gene labels as distinct Ensembl features:", duplicate_gene_features, flush=True)\n'''
if old in t:
    t = t.replace(old, new, 1)
elif "duplicate_gene_features" not in t:
    raise SystemExit("Builder duplicate-feature block drifted")

old = '''        writer.writerow([\n            "gene", "state", "state_class", "n_cells", "n_state_patients",\n            "n_expressing_patients", "patient_prevalence", "fraction_expressing",\n            "mean_expression", "expression_z_across_states",\n        ])\n'''
new = '''        writer.writerow([\n            "gene", "feature_id", "state", "state_class", "n_cells", "n_state_patients",\n            "n_expressing_patients", "patient_prevalence", "fraction_expressing",\n            "mean_expression", "expression_z_across_states",\n        ])\n'''
if old in t:
    t = t.replace(old, new, 1)
elif '"feature_id", "state"' not in t:
    raise SystemExit("Builder output header drifted")

old = '''                writer.writerow([\n                    gene,\n                    state,\n'''
new = '''                writer.writerow([\n                    gene,\n                    feature_ids[g_idx],\n                    state,\n'''
if old in t:
    t = t.replace(old, new, 1)
elif "feature_ids[g_idx]" not in t:
    raise SystemExit("Builder output row drifted")

old = '''        "n_states": n_states,\n        "n_genes": n_genes,\n        "rows_written": rows_written,\n'''
new = '''        "n_states": n_states,\n        "n_features": n_genes,\n        "n_genes": len(label_counts),\n        "n_unique_gene_labels": len(label_counts),\n        "n_duplicate_gene_labels": len(duplicate_gene_features),\n        "duplicate_gene_features": duplicate_gene_features,\n        "rows_written": rows_written,\n'''
if old in t:
    t = t.replace(old, new, 1)
elif '"duplicate_gene_features": duplicate_gene_features' not in t:
    raise SystemExit("Builder metadata block drifted")

t = t.replace('"reference_schema_version": "1.1.0"', '"reference_schema_version": "1.2.0"', 1)
p.write_text(t)


# Runtime: never merge two distinct Ensembl features that share a symbol.
p = Path("gbm_evidence_engine/connectors/gbmap.py")
t = p.read_text()
marker = '''    if not rows:\n        return {\n            "ok": False,\n            "gene": gene,\n            "status": "reference_unavailable" if not path.exists() else "gene_not_found",\n            "error": (\n                "The compact GBmap reference has not been generated on this deployment."\n                if not path.exists()\n                else f"{gene} is not present in the compact GBmap reference."\n            ),\n            "source": "GBmap / CELLxGENE",\n            "source_url": COLLECTION_URL,\n        }\n\n    state_rows: list[dict] = []\n'''
replacement = '''    if not rows:\n        return {\n            "ok": False,\n            "gene": gene,\n            "status": "reference_unavailable" if not path.exists() else "gene_not_found",\n            "error": (\n                "The compact GBmap reference has not been generated on this deployment."\n                if not path.exists()\n                else f"{gene} is not present in the compact GBmap reference."\n            ),\n            "source": "GBmap / CELLxGENE",\n            "source_url": COLLECTION_URL,\n        }\n\n    feature_ids = sorted({str(row.get("feature_id") or "").strip() for row in rows if str(row.get("feature_id") or "").strip()})\n    if len(feature_ids) > 1:\n        return {\n            "ok": False,\n            "gene": gene,\n            "status": "ambiguous_gene_symbol",\n            "feature_ids": feature_ids,\n            "error": (\n                f"Core GBmap contains {len(feature_ids)} distinct Ensembl features labeled {gene}. "\n                "The features are preserved separately and are not merged because the published expression scale cannot be safely collapsed without changing its semantics."\n            ),\n            "source": "GBmap compact reference derived from CELLxGENE Core GBmap",\n            "source_url": COLLECTION_URL,\n        }\n\n    state_rows: list[dict] = []\n'''
if marker in t:
    t = t.replace(marker, replacement, 1)
elif "ambiguous_gene_symbol" not in t:
    raise SystemExit("GBmap runtime insertion marker drifted")

old = '''        state_rows.append({\n            "state": row.get("state"),\n'''
new = '''        state_rows.append({\n            "feature_id": row.get("feature_id") or (feature_ids[0] if feature_ids else None),\n            "state": row.get("state"),\n'''
if old in t:
    t = t.replace(old, new, 1)
elif '"feature_id": row.get("feature_id")' not in t:
    raise SystemExit("GBmap state row block drifted")

old = '''        "gene": gene,\n        "states": state_rows,\n'''
new = '''        "gene": gene,\n        "feature_id": feature_ids[0] if len(feature_ids) == 1 else None,\n        "states": state_rows,\n'''
if old in t:
    t = t.replace(old, new, 1)
elif '"feature_id": feature_ids[0]' not in t:
    raise SystemExit("GBmap summary feature-id block drifted")
p.write_text(t)
