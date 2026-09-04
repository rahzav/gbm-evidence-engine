"""
run_batch_demo.py
===================

High-value capability test #5 from the product brief: a researcher has a
hit list of genes (here: a 4-gene stand-in for a real 20-gene differential-
expression list) and wants a ranked, translationally-prioritized triage
table instead of checking each one by hand across 5+ tools.

Run with: PYTHONPATH=. python3 scripts/run_batch_demo.py
"""
import sys
sys.path.insert(0, ".")

from gbm_evidence_engine.orchestrator import build_single_gene_dossier
from gbm_evidence_engine.analysis.multiple_testing import benjamini_hochberg
from gbm_evidence_engine.evidence_model import EvidenceTier

GENES = ["EGFR", "PTEN", "TP53", "CDK4"]


def main():
    rows = []
    for gene in GENES:
        dossier = build_single_gene_dossier(gene)
        meta = next((e for e in dossier.evidence if e.statistic_name == "pooled_hazard_ratio"), None)
        dep = next((e for e in dossier.by_tier(EvidenceTier.STATISTICAL_ASSOCIATION)
                    if e.statistic_name == "U_statistic"), None)
        pan_essential = any("pan-essential" in c for e in dossier.evidence for c in e.caveats)
        culture_flag = any("culture" in c.lower() for e in dossier.evidence for c in e.caveats)
        rows.append({
            "gene": gene,
            "pooled_hr": meta.statistic_value if meta else None,
            "pooled_p": meta.p_value if meta else None,
            "heterogeneity_i2_pct": meta.effect_size if meta else None,
            "dependency_p": dep.p_value if dep else None,
            "dependency_effect": dep.effect_size if dep else None,
            "pan_essential_flag": pan_essential,
            "culture_instability_flag": culture_flag,
            "n_warnings": len(dossier.warnings),
        })

    valid_p = [r["pooled_p"] for r in rows if r["pooled_p"] is not None]
    corrected = benjamini_hochberg(valid_p)
    ci = iter(corrected)
    for r in rows:
        r["pooled_p_BH_corrected"] = next(ci) if r["pooled_p"] is not None else None

    # Simple translatability ranking: significant after correction, not
    # pan-essential (so a dependency finding would be GBM-selective), and
    # low cross-cohort heterogeneity (so the survival signal is trustworthy).
    def rank_key(r):
        sig = (r["pooled_p_BH_corrected"] or 1) < 0.05
        clean_dependency = not r["pan_essential_flag"]
        low_heterogeneity = (r["heterogeneity_i2_pct"] or 100) < 50
        return (-int(sig), -int(clean_dependency), -int(low_heterogeneity), r["pooled_p_BH_corrected"] or 1)

    rows.sort(key=rank_key)

    header = ["rank", "gene", "pooled_HR", "pooled_p", "BH_p", "I2%", "dep_p", "dep_effect", "pan_ess", "culture_flag"]
    print(" | ".join(header))
    print("-" * 110)
    for i, r in enumerate(rows, 1):
        print(" | ".join(str(x) for x in [
            i, r["gene"],
            f"{r['pooled_hr']:.2f}" if r["pooled_hr"] else "-",
            f"{r['pooled_p']:.3f}" if r["pooled_p"] is not None else "-",
            f"{r['pooled_p_BH_corrected']:.3f}" if r["pooled_p_BH_corrected"] is not None else "-",
            f"{r['heterogeneity_i2_pct']:.0f}" if r["heterogeneity_i2_pct"] is not None else "-",
            f"{r['dependency_p']:.3f}" if r["dependency_p"] is not None else "-",
            f"{r['dependency_effect']:.2f}" if r["dependency_effect"] is not None else "-",
            r["pan_essential_flag"], r["culture_instability_flag"],
        ]))

    print("\n(All statistics computed on SYNTHETIC calibrated demo data -- see data/README.md. "
          "BH = Benjamini-Hochberg FDR-corrected p-value across the batch.)")


if __name__ == "__main__":
    main()
