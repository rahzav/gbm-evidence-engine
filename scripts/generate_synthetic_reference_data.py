"""
generate_synthetic_reference_data.py
=====================================

Generates the SYNTHETIC, calibrated demo datasets described in
data/README.md. These are NOT real patient-level TCGA/CGGA/GLASS/DepMap/
Ivy GAP data (this sandbox has no network access to pull the real releases).
They exist only to prove the analysis engine (analysis/survival.py,
dependency.py, spatial.py) runs correctly end-to-end and reacts correctly
to realistic patterns (cross-cohort heterogeneity, pan-essential genes,
anatomic enrichment).

Every "true" parameter used to generate the data is chosen to be broadly
consistent with the REAL published EGFR findings in
data/reference_literature_facts.json (e.g. an American-cohort HR around 1.5
vs. a much weaker non-US-cohort effect) so that re-deriving those numbers
from first-principles code is itself a form of validation, not just a random
demo. Re-run this script any time and it produces the same files (fixed
seed) so the demo is reproducible.
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(20260828)  # seeded on the date this V1 was built
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def make_cohort(n, true_log_hr_amp, true_log_hr_age, name, baseline_median_months=14.0):
    age = RNG.normal(58, 12, size=n).clip(20, 90)
    egfr_amp = RNG.binomial(1, 0.45, size=n)  # ~45% amplification rate, consistent with literature
    age_z = (age - 58) / 12

    linear_pred = true_log_hr_amp * egfr_amp + true_log_hr_age * age_z
    # Weibull-ish proportional-hazards simulation
    baseline_lambda = np.log(2) / baseline_median_months
    u = RNG.uniform(0, 1, size=n)
    event_time = -np.log(u) / (baseline_lambda * np.exp(linear_pred))
    censor_time = RNG.uniform(6, 36, size=n)  # administrative censoring / follow-up cutoff
    time = np.minimum(event_time, censor_time)
    event = (event_time <= censor_time).astype(int)

    return pd.DataFrame({
        "cohort": name,
        "patient_id": [f"{name}_{i:04d}" for i in range(n)],
        "os_months": np.round(time, 2),
        "event": event,
        "egfr_amplified": egfr_amp,
        "age": np.round(age, 1),
    })


def main():
    # Calibration target: American/TCGA-like cohort HR ~1.5 (real meta-analysis: 1.53, CI 1.28-1.84)
    # Non-US/CGGA-like cohort: weak/non-significant (real meta-analysis: not significant outside US)
    # GLASS-like recurrent-only cohort: intermediate, smaller n (real GLASS releases are ~150-360 samples)
    generate_gene_bundle("EGFR", tcga_log_hr=np.log(1.5), cgga_log_hr=np.log(1.08), glass_log_hr=np.log(1.35),
                         gbm_dep_mean=-0.15, other_dep_mean=-0.05,
                         zone_means=[5.0, 5.4, 6.0, 6.8, 7.1, 6.3, 5.6])

    # PTEN: tumor suppressor, loss-of-function broadly associated with worse
    # outcome fairly consistently across cohorts in the literature (less
    # region-dependent heterogeneity than EGFR) -- calibrated accordingly as
    # a *contrast case* to EGFR's heterogeneous pattern, for the batch demo.
    generate_gene_bundle("PTEN", tcga_log_hr=np.log(1.4), cgga_log_hr=np.log(1.35), glass_log_hr=np.log(1.5),
                         gbm_dep_mean=-0.05, other_dep_mean=-0.05,
                         zone_means=[5.5, 5.6, 5.7, 5.8, 5.7, 5.6, 5.5])  # flat -- tumor suppressor, no strong spatial signal in this demo

    # TP53: very frequently mutated in GBM but with a consistently weak/
    # inconsistent prognostic signal in the literature -- calibrated as a
    # near-null case to show the batch triage correctly de-prioritizing it.
    generate_gene_bundle("TP53", tcga_log_hr=np.log(1.05), cgga_log_hr=np.log(0.98), glass_log_hr=np.log(1.1),
                         gbm_dep_mean=-1.15, other_dep_mean=-1.1,  # pan-essential-like pattern (TP53 pathway core)
                         zone_means=[5.0, 5.0, 5.1, 5.0, 5.1, 5.0, 5.0])

    # CDK4: recurrently amplified in a GBM subset; calibrated as a moderate,
    # fairly consistent cross-cohort signal with a real selective-dependency
    # pattern in amplified lines -- a plausible "worth following up" case.
    generate_gene_bundle("CDK4", tcga_log_hr=np.log(1.3), cgga_log_hr=np.log(1.25), glass_log_hr=np.log(1.2),
                         gbm_dep_mean=-0.6, other_dep_mean=-0.1,
                         zone_means=[5.2, 5.5, 6.1, 5.9, 5.7, 6.4, 5.8])


def generate_gene_bundle(gene, tcga_log_hr, cgga_log_hr, glass_log_hr, gbm_dep_mean, other_dep_mean, zone_means):
    tcga_like = make_cohort(300, true_log_hr_amp=tcga_log_hr, true_log_hr_age=0.2, name="TCGA_like_US")
    cgga_like = make_cohort(350, true_log_hr_amp=cgga_log_hr, true_log_hr_age=0.15, name="CGGA_like_nonUS")
    glass_like = make_cohort(160, true_log_hr_amp=glass_log_hr, true_log_hr_age=0.1, name="GLASS_like_recurrent",
                              baseline_median_months=9.0)
    survival_df = pd.concat([tcga_like, cgga_like, glass_like], ignore_index=True)
    survival_df.to_csv(DATA_DIR / f"synthetic_cohort_survival_{gene}.csv", index=False)

    n_gbm, n_other = 34, 850
    gbm_effect = RNG.normal(gbm_dep_mean, 0.25, size=n_gbm)
    other_effect = RNG.normal(other_dep_mean, 0.3, size=n_other)
    dep_df = pd.concat([
        pd.DataFrame({"lineage": "glioblastoma", "cell_line": [f"GBM_{i}" for i in range(n_gbm)], "gene_effect_score": gbm_effect}),
        pd.DataFrame({"lineage": "other", "cell_line": [f"OTHER_{i}" for i in range(n_other)], "gene_effect_score": other_effect}),
    ], ignore_index=True)
    dep_df.to_csv(DATA_DIR / f"synthetic_depmap_effect_scores_{gene}.csv", index=False)

    zones = ["leading_edge", "infiltrating_tumor", "cellular_tumor", "perinecrotic_zone",
             "pseudopalisading_cells_around_necrosis", "microvascular_proliferation",
             "hyperplastic_blood_vessels"]
    rows = []
    for zone, mean in zip(zones, zone_means):
        n_samples = RNG.integers(14, 24)
        vals = RNG.normal(mean, 0.8, size=n_samples)
        for v in vals:
            rows.append({"anatomic_zone": zone, "log2_expression": round(float(v), 3)})
    pd.DataFrame(rows).to_csv(DATA_DIR / f"synthetic_ivygap_zone_expression_{gene}.csv", index=False)
    print(f"Wrote synthetic bundle for {gene}")


if __name__ == "__main__":
    main()
    # Pan-essential negative control used by tests/ -- kept separate from the
    # per-gene bundle loop above since it isn't a real gene query target.
    n_gbm, n_other = 34, 850
    pan_gbm = RNG.normal(-1.1, 0.15, size=n_gbm)
    pan_other = RNG.normal(-1.05, 0.2, size=n_other)
    pan_df = pd.concat([
        pd.DataFrame({"lineage": "glioblastoma", "cell_line": [f"GBM_{i}" for i in range(n_gbm)], "gene_effect_score": pan_gbm}),
        pd.DataFrame({"lineage": "other", "cell_line": [f"OTHER_{i}" for i in range(n_other)], "gene_effect_score": pan_other}),
    ], ignore_index=True)
    pan_df.to_csv(DATA_DIR / "synthetic_depmap_effect_scores_PANESSENTIAL_CONTROL.csv", index=False)
    print("Wrote pan-essential control snapshot")
