"""Chinese Glioma Genome Atlas external-cohort validation.

CGGA's current download site exposes the mRNAseq_693 and mRNAseq_325 RSEM-gene
matrices plus clinical tables as public ZIP downloads. Raw files are cached
locally and never committed or re-hosted. For GBM target validation we use a
strict adult primary WHO-IV histologic GBM, IDH-wildtype subset and fit a
continuous-expression Cox model (HR per 1 SD) independently in each cohort,
then meta-analyse the log hazard ratios when both cohorts are usable.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import io
import math
from pathlib import Path
import threading
import urllib.request
import zipfile

import numpy as np
import pandas as pd

from gbm_evidence_engine.analysis.survival import cox_ph, cross_cohort_meta_analysis
from gbm_evidence_engine.evidence_model import AccessTier
from .base import CACHE_DIR

CGGA_DIR = CACHE_DIR / "cgga"
CGGA_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = "GBM-Evidence-Engine/3.0 (+https://github.com/rahzav/gbm-evidence-engine)"
_LOCK_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.Lock] = {}

BASE_DOWNLOAD = "https://www.cgga.org.cn/download"
COHORTS = {
    "CGGA_mRNAseq_693": {
        "clinical_url": BASE_DOWNLOAD + "?file=download%2F20200506%2FCGGA.mRNAseq_693_clinical.20200506.txt.zip&time=20200506&type=mRNAseq_693_clinical",
        "expression_url": BASE_DOWNLOAD + "?file=download%2F20200506%2FCGGA.mRNAseq_693.RSEM-genes.20200506.txt.zip&time=20200506&type=mRNAseq_693",
        "clinical_member": "CGGA.mRNAseq_693_clinical.20200506.txt",
        "expression_member": "CGGA.mRNAseq_693.RSEM-genes.20200506.txt",
    },
    "CGGA_mRNAseq_325": {
        "clinical_url": BASE_DOWNLOAD + "?file=download%2F20200506%2FCGGA.mRNAseq_325_clinical.20200506.txt.zip&time=20200506&type=mRNAseq_325_clinical",
        "expression_url": BASE_DOWNLOAD + "?file=download%2F20200506%2FCGGA.mRNAseq_325.RSEM-genes.20200506.txt.zip&time=20200506&type=mRNAseq_325",
        "clinical_member": "CGGA.mRNAseq_325_clinical.20200506.txt",
        "expression_member": "CGGA.mRNAseq_325.RSEM-genes.20200506.txt",
    },
}


def _path_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCK_GUARD:
        return _PATH_LOCKS.setdefault(key, threading.Lock())


def _ensure_zip(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 1000 and zipfile.is_zipfile(path):
        return path
    with _path_lock(path):
        if path.exists() and path.stat().st_size > 1000 and zipfile.is_zipfile(path):
            return path
        tmp = path.with_suffix(path.suffix + ".tmp")
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=150) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if not zipfile.is_zipfile(tmp):
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"CGGA download for {path.name} was not a valid ZIP archive.")
        tmp.replace(path)
    return path


def _read_clinical(path: Path, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf, zf.open(member) as raw:
        return pd.read_csv(raw, sep="\t", dtype=str)


def _read_gene_row(path: Path, member: str, gene: str) -> dict[str, float]:
    gene = gene.upper().strip()
    with zipfile.ZipFile(path) as zf, zf.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        header = text.readline().rstrip("\r\n").split("\t")
        sample_ids = header[1:]
        for line in text:
            parts = line.rstrip("\r\n").split("\t")
            if parts and parts[0].upper() == gene:
                out = {}
                for sid, value in zip(sample_ids, parts[1:]):
                    try:
                        x = float(value)
                    except (TypeError, ValueError):
                        continue
                    if math.isfinite(x):
                        out[sid] = x
                return out
    raise KeyError(f"{gene} was not found in {member}.")


def _strict_gbm_frame(clin: pd.DataFrame, expression: dict[str, float]) -> pd.DataFrame:
    df = clin.copy()
    df["CGGA_ID"] = df["CGGA_ID"].astype(str)
    df["expression_fpkm"] = df["CGGA_ID"].map(expression)
    for col in ["Age", "OS", "Censor (alive=0; dead=1)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    mask = (
        df["PRS_type"].fillna("").str.strip().str.lower().eq("primary")
        & df["Histology"].fillna("").str.strip().str.upper().eq("GBM")
        & df["Grade"].fillna("").str.strip().str.upper().eq("WHO IV")
        & df["IDH_mutation_status"].fillna("").str.strip().str.lower().eq("wildtype")
        & (df["Age"] >= 18)
        & (df["OS"] > 0)
        & df["Censor (alive=0; dead=1)"].isin([0, 1])
        & df["expression_fpkm"].notna()
    )
    return df.loc[mask].copy()


def _analyse_cohort(name: str, config: dict, gene: str) -> dict:
    safe = name.lower()
    # The two cohort workers use distinct cache paths, so their source downloads
    # can proceed in parallel without racing on a shared temporary file.
    clin_zip = _ensure_zip(config["clinical_url"], CGGA_DIR / f"{safe}_clinical.zip")
    expr_zip = _ensure_zip(config["expression_url"], CGGA_DIR / f"{safe}_expression.zip")
    clin = _read_clinical(clin_zip, config["clinical_member"])
    expression = _read_gene_row(expr_zip, config["expression_member"], gene)
    df = _strict_gbm_frame(clin, expression)
    if len(df) < 20 or int(df["Censor (alive=0; dead=1)"].sum()) < 8:
        return {
            "ok": False,
            "cohort": name,
            "n": int(len(df)),
            "error": "Strict adult primary IDH-wildtype GBM subset is too small for stable survival estimation.",
        }

    log_expr = np.log2(df["expression_fpkm"].to_numpy(float) + 1.0)
    sd = float(np.std(log_expr, ddof=1))
    if not math.isfinite(sd) or sd <= 1e-12:
        return {"ok": False, "cohort": name, "n": int(len(df)), "error": "Expression has near-zero variance."}
    expr_z = (log_expr - float(np.mean(log_expr))) / sd
    durations = df["OS"].to_numpy(float)
    events = df["Censor (alive=0; dead=1)"].to_numpy(int)

    result = cox_ph(durations, events, {"expression_z": expr_z})
    log_hr = result.coefficients.get("expression_z")
    se = result.standard_errors.get("expression_z")
    p_value = result.p_values.get("expression_z")
    hr = result.hazard_ratios.get("expression_z")
    ci_log = result.log_hr_ci95.get("expression_z", (None, None))
    ci_hr = None
    if ci_log[0] is not None and ci_log[1] is not None:
        ci_hr = (math.exp(ci_log[0]), math.exp(ci_log[1]))
    return {
        "ok": log_hr is not None and se is not None,
        "cohort": name,
        "gene": gene,
        "subset": "adult primary WHO-IV histologic GBM, IDH-wildtype",
        "n": int(result.n),
        "events": int(result.n_events),
        "log_hr_per_sd": log_hr,
        "hr_per_sd": hr,
        "se_log_hr": se,
        "p_value": p_value,
        "ci95_hr": ci_hr,
        "converged": bool(result.converged),
        "median_fpkm": float(np.median(df["expression_fpkm"].to_numpy(float))),
        "access_tier": AccessTier.OPEN_BULK_DOWNLOAD.value,
    }


def _safe_analyse(item: tuple[str, dict], gene: str) -> dict:
    name, config = item
    try:
        return _analyse_cohort(name, config, gene)
    except Exception as exc:
        return {"ok": False, "cohort": name, "error": str(exc)}


def summarize_external_validation(gene: str) -> dict:
    """Run both independent CGGA GBM validations concurrently, then meta-analyse."""
    gene = gene.upper().strip()
    items = list(COHORTS.items())
    with ThreadPoolExecutor(max_workers=2) as ex:
        cohort_results = list(ex.map(lambda item: _safe_analyse(item, gene), items))

    errors = [f"{r.get('cohort')}: {r.get('error', 'unavailable')}" for r in cohort_results if not r.get("ok")]
    usable = [r for r in cohort_results if r.get("ok") and r.get("se_log_hr") not in (None, 0)]
    meta = None
    if len(usable) >= 2:
        m = cross_cohort_meta_analysis([
            {"cohort": r["cohort"], "log_hr": r["log_hr_per_sd"], "se": r["se_log_hr"], "n": r["n"]}
            for r in usable
        ])
        meta = {
            "pooled_log_hr": m.pooled_log_hr,
            "pooled_hr": m.pooled_hr,
            "pooled_ci95": m.pooled_ci95,
            "pooled_p_value": m.pooled_p_value,
            "i_squared": m.i_squared,
            "q_p_value": m.q_p_value,
            "model": m.model,
        }

    signs = [np.sign(r["log_hr_per_sd"]) for r in usable if r.get("log_hr_per_sd") is not None]
    direction_consistent = len(signs) >= 2 and len(set(signs)) == 1
    return {
        "ok": bool(usable),
        "gene": gene,
        "cohorts": cohort_results,
        "n_usable_cohorts": len(usable),
        "direction_consistent": bool(direction_consistent),
        "meta_analysis": meta,
        "errors": errors,
        "access_tier": AccessTier.OPEN_BULK_DOWNLOAD.value,
        "source": "CGGA mRNAseq_693 + mRNAseq_325",
    }


def registration_reminder() -> str:
    return "CGGA's current download page exposes the mRNAseq_693 and mRNAseq_325 research cohorts as public bulk ZIPs; this connector caches them locally and does not re-host raw matrices."
