"""
tests/test_survival.py
=======================

Validates analysis/survival.py three ways:

1. Kaplan-Meier against a fully hand-computed 6-patient example (exact match).
2. Log-rank against two mathematically-guaranteed invariants: identical arms
   MUST give chi2 == 0 (no ambiguity — if both arms are literally the same
   data, observed always equals expected at every event time), and a
   dramatically separated pair of arms MUST give a very small p-value.
3. Cox PH against ground truth recovered from a large simulation with a
   KNOWN true log-hazard-ratio (a standard way to validate a from-scratch
   implementation without needing to trust a possibly-misremembered
   published benchmark number).
4. Cross-cohort meta-analysis against a hand-computed two-study
   inverse-variance pooling, plus the I^2=0 (identical estimates) and
   high-I^2 (wildly different estimates, tiny SEs) edge cases.

Run with: PYTHONPATH=. python3 tests/test_survival.py  (pytest is not
installable in this offline sandbox — see README.md — so this file uses
plain assert statements and prints PASS/FAIL, runnable with bare python3).
"""
import sys
import math
import numpy as np

sys.path.insert(0, ".")
from gbm_evidence_engine.analysis.survival import (
    kaplan_meier, log_rank_test, cox_ph, cross_cohort_meta_analysis
)


def test_kaplan_meier_hand_computed():
    # 6 patients, times: 2,3,4(cens),5,6,8(cens). Events at t=2,3,5,6.
    durations = [2, 3, 4, 5, 6, 8]
    events =    [1, 1, 0, 1, 1, 0]
    result = kaplan_meier(np.array(durations), np.array(events))
    # By hand: S(2) = 1 - 1/6 = 5/6
    #          S(3) = 5/6 * (1 - 1/5) = 5/6 * 4/5 = 4/6 = 2/3
    #          (t=4 is censored, drops out of risk set, no event contribution)
    #          S(5) = 2/3 * (1 - 1/3) = 2/3 * 2/3 = 4/9   [n_at_risk=3 at t=5: patients at 5,6,8]
    #          S(6) = 4/9 * (1 - 1/2) = 4/9 * 1/2 = 2/9
    expected = [5/6, 2/3, 4/9, 2/9]
    assert len(result.survival_prob) == 4, result.survival_prob
    for got, exp in zip(result.survival_prob, expected):
        assert math.isclose(got, exp, rel_tol=1e-9), (got, exp)
    assert result.n_events == 4
    print("PASS: kaplan_meier matches hand-computed product-limit values")


def test_log_rank_identical_arms_gives_zero():
    rng = np.random.default_rng(1)
    durations = rng.exponential(10, size=40)
    events = rng.binomial(1, 0.8, size=40)
    result = log_rank_test(durations, events, durations, events)  # literally the same data twice
    assert math.isclose(result.chi_square, 0.0, abs_tol=1e-8), result.chi_square
    print("PASS: log-rank on identical arms gives chi2 == 0 (mathematically guaranteed)")


def test_log_rank_detects_strong_separation():
    rng = np.random.default_rng(2)
    short_surv = rng.exponential(2, size=60)   # fast events
    long_surv = rng.exponential(50, size=60)   # slow events
    events_a = np.ones(60, dtype=int)
    events_b = np.ones(60, dtype=int)
    result = log_rank_test(short_surv, events_a, long_surv, events_b)
    assert result.p_value < 0.001, result.p_value
    print(f"PASS: log-rank detects strong separation (p={result.p_value:.2e})")


def test_cox_ph_recovers_known_ground_truth():
    rng = np.random.default_rng(3)
    n = 4000
    true_log_hr = 0.6  # HR = e^0.6 ~= 1.82
    group = rng.binomial(1, 0.5, size=n)
    baseline_lambda = 0.05
    u = rng.uniform(0, 1, size=n)
    event_time = -np.log(u) / (baseline_lambda * np.exp(true_log_hr * group))
    censor_time = rng.uniform(1, 40, size=n)
    time = np.minimum(event_time, censor_time)
    event = (event_time <= censor_time).astype(int)

    result = cox_ph(time, event, {"group": group})
    recovered = result.coefficients["group"]
    assert abs(recovered - true_log_hr) < 0.1, (recovered, true_log_hr)
    assert result.p_values["group"] < 0.001
    print(f"PASS: cox_ph recovers true log-HR={true_log_hr} from n={n} simulation "
          f"(recovered={recovered:.3f}, p={result.p_values['group']:.2e})")


def test_meta_analysis_hand_computed_fixed_effect():
    # Two studies, hand-computed inverse-variance pooling:
    # study1: log_hr=0.40, se=0.10 -> weight=100
    # study2: log_hr=0.30, se=0.20 -> weight=25
    # pooled_log_hr = (100*0.40 + 25*0.30) / (125) = (40+7.5)/125 = 0.38
    result = cross_cohort_meta_analysis([
        {"cohort": "A", "log_hr": 0.40, "se": 0.10, "n": 100},
        {"cohort": "B", "log_hr": 0.30, "se": 0.20, "n": 50},
    ])
    assert math.isclose(result.pooled_log_hr, 0.38, abs_tol=1e-6), result.pooled_log_hr
    print(f"PASS: meta-analysis fixed-effect pooling matches hand calculation "
          f"(pooled_log_hr={result.pooled_log_hr:.4f}, expected 0.38)")


def test_meta_analysis_zero_heterogeneity_when_estimates_identical():
    result = cross_cohort_meta_analysis([
        {"cohort": "A", "log_hr": 0.5, "se": 0.1, "n": 100},
        {"cohort": "B", "log_hr": 0.5, "se": 0.15, "n": 80},
        {"cohort": "C", "log_hr": 0.5, "se": 0.12, "n": 90},
    ])
    assert result.i_squared < 1e-6, result.i_squared
    assert result.model == "fixed"
    print("PASS: identical per-cohort estimates give I^2 == 0 and fixed-effect model")


def test_meta_analysis_flags_high_heterogeneity():
    result = cross_cohort_meta_analysis([
        {"cohort": "A", "log_hr": 1.5, "se": 0.02, "n": 500},
        {"cohort": "B", "log_hr": -0.8, "se": 0.02, "n": 500},
    ])
    assert result.i_squared > 90, result.i_squared
    assert result.model == "random"
    print(f"PASS: wildly different tight estimates correctly flagged as high heterogeneity "
          f"(I^2={result.i_squared:.1f}%, random-effects model selected)")


if __name__ == "__main__":
    test_kaplan_meier_hand_computed()
    test_log_rank_identical_arms_gives_zero()
    test_log_rank_detects_strong_separation()
    test_cox_ph_recovers_known_ground_truth()
    test_meta_analysis_hand_computed_fixed_effect()
    test_meta_analysis_zero_heterogeneity_when_estimates_identical()
    test_meta_analysis_flags_high_heterogeneity()
    print("\nALL survival.py TESTS PASSED")
