"""Public LINCS/L1000CDS2 perturbational-signature connector.

This connector is intentionally used for hypothesis generation, not for target
priority scoring. It searches drug-induced L1000 signatures for perturbations
predicted to reverse a researcher-provided expression signature and can return
pairwise combination hypotheses exposed by L1000CDS2.

L1000CDS2 contains historical compound labels that are sometimes placeholders.
Live queries therefore resolve placeholder labels against PubChem when a CID is
available and keep unresolved compounds explicitly labeled as unannotated.

The source is a historical LINCS-derived resource. Results require independent
validation in contemporary GBM models and must not be presented as clinical
treatment recommendations.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable

API_URL = "https://maayanlab.cloud/L1000CDS2/query"
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
USER_AGENT = "GBM-Gene-Analysis/6.0 (+https://github.com/rahzav/gbm-evidence-engine)"


def _clean_genes(values: Iterable[str], limit: int = 150) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        gene = str(value).strip().upper()
        if not gene or gene in seen:
            continue
        seen.add(gene)
        out.append(gene)
        if len(out) >= limit:
            break
    return out


def _post(payload: dict, timeout: int = 60) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise RuntimeError("L1000CDS2 returned a non-object response.")
        return data
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"L1000CDS2 HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"L1000CDS2 request failed: {exc}") from exc


def _placeholder_name(name: str) -> bool:
    value = str(name or "").strip()
    if not value:
        return True
    if value in {"-666", "666", "NA", "N/A", "UNKNOWN", "UNDEFINED"}:
        return True
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
        return True
    return False


def _pubchem_title(cid: object, timeout: int = 12) -> str | None:
    value = str(cid or "").strip()
    if not value or not value.isdigit():
        return None
    url = f"{PUBCHEM_BASE}/compound/cid/{urllib.parse.quote(value)}/description/JSON"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        info = ((data.get("InformationList") or {}).get("Information") or []) if isinstance(data, dict) else []
        if info and isinstance(info[0], dict):
            title = str(info[0].get("Title") or "").strip()
            return title or None
    except Exception:
        return None
    return None


def _display_drug_name(raw_name: str, pubchem_id: object, cache: dict[str, str | None] | None) -> tuple[str | None, bool]:
    name = str(raw_name or "").strip()
    if not _placeholder_name(name):
        return name, True
    cid = str(pubchem_id or "").strip()
    if cid and cache is not None:
        if cid not in cache:
            cache[cid] = _pubchem_title(cid)
        resolved = cache.get(cid)
        if resolved:
            return resolved, True
    if cid:
        return f"Unannotated compound (PubChem CID {cid})", False
    return None, False


def _summarize_response(raw: dict, max_results: int = 20, *, resolve_pubchem: bool = False) -> dict:
    rows = raw.get("topMeta") or []
    if not isinstance(rows, list):
        rows = []

    title_cache: dict[str, str | None] | None = {} if resolve_pubchem else None
    top_signatures: list[dict] = []
    sig_to_drug: dict[str, str] = {}
    by_drug: dict[str, dict] = {}
    unannotated_count = 0

    for row in rows[:50]:
        if not isinstance(row, dict):
            continue
        source_name = str(row.get("pert_desc") or row.get("pert_iname") or "").strip()
        pubchem_id = row.get("pubchem_id")
        drug, annotated = _display_drug_name(source_name, pubchem_id, title_cache)
        if not annotated:
            unannotated_count += 1
        sig_id = str(row.get("sig_id") or "").strip()
        if sig_id and drug:
            sig_to_drug[sig_id] = drug
        score = row.get("score")
        entry = {
            "drug": drug,
            "source_compound_label": source_name or None,
            "compound_annotated": annotated,
            "score": score,
            "cell_line": row.get("cell_id"),
            "dose": row.get("pert_dose"),
            "dose_unit": row.get("pert_dose_unit"),
            "time": row.get("pert_time"),
            "time_unit": row.get("pert_time_unit"),
            "signature_id": sig_id or None,
            "pubchem_id": pubchem_id,
            "drugbank_id": row.get("drugchem_id"),
            "overlap": row.get("overlap"),
        }
        top_signatures.append(entry)
        if drug:
            key = drug.casefold()
            current = by_drug.get(key)
            try:
                numeric_score = float(score)
            except (TypeError, ValueError):
                numeric_score = None
            if current is None:
                by_drug[key] = {
                    "drug": drug,
                    "compound_annotated": annotated,
                    "best_reverse_score": numeric_score,
                    "supporting_signatures": 1,
                    "cell_lines": [row.get("cell_id")] if row.get("cell_id") else [],
                    "pubchem_ids": [str(pubchem_id)] if pubchem_id else [],
                }
            else:
                current["supporting_signatures"] += 1
                current["compound_annotated"] = bool(current["compound_annotated"] or annotated)
                if row.get("cell_id") and row.get("cell_id") not in current["cell_lines"]:
                    current["cell_lines"].append(row.get("cell_id"))
                if pubchem_id and str(pubchem_id) not in current["pubchem_ids"]:
                    current["pubchem_ids"].append(str(pubchem_id))
                if numeric_score is not None and (
                    current["best_reverse_score"] is None or numeric_score > current["best_reverse_score"]
                ):
                    current["best_reverse_score"] = numeric_score

    all_drugs = sorted(
        by_drug.values(),
        key=lambda item: (
            bool(item.get("compound_annotated")),
            item["best_reverse_score"] is not None,
            item["best_reverse_score"] or float("-inf"),
        ),
        reverse=True,
    )
    # Prefer chemically annotated candidates in the primary table. If annotation
    # services are unavailable, keep explicitly labeled unannotated compounds as
    # a fallback rather than silently deleting source results.
    annotated_drugs = [row for row in all_drugs if row.get("compound_annotated")]
    top_drugs = (annotated_drugs or all_drugs)[:max_results]

    combinations: list[dict] = []
    for combo in (raw.get("combinations") or [])[:200]:
        if not isinstance(combo, dict):
            continue
        sig1 = str(combo.get("X1") or "")
        sig2 = str(combo.get("X2") or "")
        drug1 = sig_to_drug.get(sig1)
        drug2 = sig_to_drug.get(sig2)
        if not drug1 or not drug2 or drug1.casefold() == drug2.casefold():
            continue
        try:
            value = float(combo.get("value"))
        except (TypeError, ValueError):
            continue
        combinations.append({
            "drug_1": drug1,
            "drug_2": drug2,
            "combination_score": value,
            "signature_1": sig1 or None,
            "signature_2": sig2 or None,
        })
    combinations.sort(key=lambda item: item["combination_score"], reverse=True)

    return {
        "ok": bool(top_signatures),
        "top_drugs": top_drugs,
        "top_signatures": top_signatures[:max_results],
        "combinations": combinations[:max_results],
        "unannotated_signature_count": unannotated_count,
        "share_id": raw.get("shareId"),
        "source": "L1000CDS2 / LINCS L1000 characteristic-direction signatures",
        "source_url": "https://maayanlab.cloud/L1000CDS2/",
        "interpretation": (
            "Reverse-connectivity results are perturbational hypotheses from historical LINCS-derived cell-line signatures. "
            "Placeholder compound labels are resolved through PubChem when possible. Results do not establish GBM efficacy, "
            "CNS exposure, combination synergy, safety, or patient benefit."
        ),
    }


def reverse_gene_sets(
    up_genes: Iterable[str],
    down_genes: Iterable[str],
    *,
    combinations: bool = True,
    max_results: int = 20,
) -> dict:
    """Find perturbations whose signatures oppose supplied up/down gene sets."""
    up = _clean_genes(up_genes)
    down = _clean_genes(down_genes)
    if len(up) < 3 or len(down) < 3:
        return {
            "ok": False,
            "error": "At least 3 upregulated and 3 downregulated genes are required for a gene-set reversal query.",
            "source": "L1000CDS2",
        }
    payload = {
        "data": {"upGenes": up, "dnGenes": down},
        "config": {
            "aggravate": False,
            "searchMethod": "geneSet",
            "share": False,
            "combination": bool(combinations),
            "db-version": "latest",
        },
        "meta": [{"key": "Tag", "value": "GBM Gene Analysis reverse-signature query"}],
    }
    try:
        result = _summarize_response(_post(payload), max_results=max_results, resolve_pubchem=True)
        result.update({"query_type": "gene_set", "n_up": len(up), "n_down": len(down)})
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc), "source": "L1000CDS2"}


def reverse_weighted_signature(
    genes: Iterable[str],
    values: Iterable[float],
    *,
    combinations: bool = True,
    max_results: int = 20,
) -> dict:
    """Reverse a signed researcher-provided expression signature via cosine search."""
    clean_genes: list[str] = []
    clean_values: list[float] = []
    seen: set[str] = set()
    for gene_raw, value_raw in zip(genes, values):
        gene = str(gene_raw).strip().upper()
        if not gene or gene in seen:
            continue
        try:
            value = float(value_raw)
        except (TypeError, ValueError):
            continue
        if value == 0:
            continue
        seen.add(gene)
        clean_genes.append(gene)
        clean_values.append(value)
        if len(clean_genes) >= 300:
            break
    if len(clean_genes) < 6:
        return {
            "ok": False,
            "error": "At least 6 genes with non-zero signed values are required for a weighted reversal query.",
            "source": "L1000CDS2",
        }
    payload = {
        "data": {"genes": clean_genes, "vals": clean_values},
        "config": {
            "aggravate": False,
            "searchMethod": "CD",
            "share": False,
            "combination": bool(combinations),
            "db-version": "latest",
        },
        "meta": [{"key": "Tag", "value": "GBM Gene Analysis researcher-signature query"}],
    }
    try:
        result = _summarize_response(_post(payload), max_results=max_results, resolve_pubchem=True)
        result.update({"query_type": "weighted_signature", "n_genes": len(clean_genes)})
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc), "source": "L1000CDS2"}
