"""
analysis/survival.py
=====================

Deterministic survival statistics. Nothing here calls an LLM. Every function
takes arrays in, returns numbers + a method/parameter record out, so that the
caller can wrap the result directly in an EvidenceRecord with full provenance.

Implemented from first principles (product/log-rank/Cox partial likelihood)
because the sandbox this was authored in has no network access to install
`lifelines` or `scikit-survival`. For a production deployment we STRONGLY
recommend swapping this module for `lifelines` (Davidson-Pilon) — it is
more thoroughly tested for edge cases (ties, left-truncation, etc.). See
requirements.txt and docs/ARCHITECTURE.md for the swap plan. The functions
below are validated in tests/test_survival.py against closed-form textbook
examples so they are safe to use for V1, not because they should be
preferred long-term over a peer-reviewed library.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy import stats, optimize


@dataclass
class KaplanMeierResult:
    timeline: np.ndarray
    survival_prob: np.ndarray
    n_at_risk_start: int
    n_events: int


def kaplan_meier(durations: np.ndarray, events: np.ndarray) -> KaplanMeierResult:
    """Standard product-limit estimator. events=1 -> death/progression, 0 -> censored."""
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    order = np.argsort(durations)
    durations, events = durations[order], events[order]

    unique_times = np.unique(durations[events == 1])
    surv = 1.0
    probs = []
    n_at_risk_start = len(durations)
    for t in unique_times:
        n_at_risk = np.sum(durations >= t)
        d_events = np.sum((durations == t) & (events == 1))
        if n_at_risk > 0:
            surv *= (1 - d_events / n_at_risk)
        probs.append(surv)
    return KaplanMeierResult(
        timeline=unique_times,
        survival_prob=np.array(probs),
        n_at_risk_start=n_at_risk_start,
        n_events=int(events.sum()),
    )


@dataclass
class LogRankResult:
    chi_square: float
    p_value: float
    n_group_a: int
    n_group_b: int


def log_rank_test(duration_a, event_a, duration_b, event_b) -> LogRankResult:
    """Two-group log-rank test (Mantel-Cox), standard textbook formula."""
    duration_a, event_a = np.asarray(duration_a, float), np.asarray(event_a, int)
    duration_b, event_b = np.asarray(duration_b, float), np.asarray(event_b, int)

    all_times = np.concatenate([duration_a, duration_b])
    all_events_time = np.unique(np.concatenate([duration_a[event_a == 1], duration_b[event_b == 1]]))

    O_a = E_a = V = 0.0
    for t in all_events_time:
        n_a = np.sum(duration_a >= t)
        n_b = np.sum(duration_b >= t)
        n = n_a + n_b
        d_a = np.sum((duration_a == t) & (event_a == 1))
        d_b = np.sum((duration_b == t) & (event_b == 1))
        d = d_a + d_b
        if n <= 1 or d == 0:
            continue
        e_a = d * n_a / n
        v = d * (n_a / n) * (n_b / n) * ((n - d) / (n - 1))
        O_a += d_a
        E_a += e_a
        V += v

    chi2 = ((O_a - E_a) ** 2) / V if V > 0 else 0.0
    p = 1 - stats.chi2.cdf(chi2, df=1)
    return LogRankResult(chi_square=float(chi2), p_value=float(p),
                          n_group_a=len(duration_a), n_group_b=len(duration_b))


@dataclass
class CoxPHResult:
    coefficients: dict[str, float]
    hazard_ratios: dict[str, float]
    standard_errors: dict[str, float]
    p_values: dict[str, float]
    log_hr_ci95: dict[str, tuple[float, float]]
    n: int
    n_events: int
    converged: bool


def cox_ph(durations, events, covariates: dict[str, np.ndarray]) -> CoxPHResult:
    """
    Cox proportional-hazards model fit by maximizing the Efron partial
    likelihood (handles tied event times, which real cohort data always has).

    covariates: dict of {name: array}, e.g. {"gene_high": [...], "age": [...], "idh_mut": [...]}
    The FIRST covariate is treated as the variable of scientific interest;
    the rest are adjustment covariates.
    """
    durations = np.asarray(durations, dtype=float)
    events = np.asarray(events, dtype=int)
    names = list(covariates.keys())
    X = np.column_stack([np.asarray(covariates[k], dtype=float) for k in names])
    n, p = X.shape

    order = np.argsort(-durations)  # descending, so risk sets are prefixes
    durations, events, X = durations[order], events[order], X[order]

    unique_event_times = np.unique(durations[events == 1])

    def neg_log_partial_likelihood(beta):
        eta = X @ beta
        exp_eta = np.exp(eta)
        ll = 0.0
        for t in unique_event_times:
            risk_set = durations >= t
            event_set = (durations == t) & (events == 1)
            d = event_set.sum()
            if d == 0:
                continue
            sum_risk = exp_eta[risk_set].sum()
            sum_events_x = eta[event_set].sum()
            # Efron correction for ties
            sum_events_exp = exp_eta[event_set].sum()
            correction = 0.0
            for l in range(int(d)):
                correction += math.log(max(sum_risk - (l / d) * sum_events_exp, 1e-12))
            ll += sum_events_x - correction
        return -ll

    beta0 = np.zeros(p)
    res = optimize.minimize(neg_log_partial_likelihood, beta0, method="BFGS")
    beta_hat = res.x

    # Numerical Hessian -> standard errors
    eps = 1e-4
    hess = np.zeros((p, p))
    f0 = neg_log_partial_likelihood(beta_hat)
    for i in range(p):
        for j in range(p):
            bpp = beta_hat.copy(); bpp[i] += eps; bpp[j] += eps
            bpm = beta_hat.copy(); bpm[i] += eps; bpm[j] -= eps
            bmp = beta_hat.copy(); bmp[i] -= eps; bmp[j] += eps
            bmm = beta_hat.copy(); bmm[i] -= eps; bmm[j] -= eps
            hess[i, j] = (neg_log_partial_likelihood(bpp) - neg_log_partial_likelihood(bpm)
                          - neg_log_partial_likelihood(bmp) + neg_log_partial_likelihood(bmm)) / (4 * eps ** 2)
    try:
        cov = np.linalg.inv(hess)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(p, np.nan)

    coefficients, hazard_ratios, standard_errors, p_values, cis = {}, {}, {}, {}, {}
    for i, name in enumerate(names):
        b, s = beta_hat[i], se[i]
        z = b / s if s and not np.isnan(s) else np.nan
        pv = 2 * (1 - stats.norm.cdf(abs(z))) if not np.isnan(z) else np.nan
        coefficients[name] = float(b)
        hazard_ratios[name] = float(np.exp(b))
        standard_errors[name] = float(s) if not np.isnan(s) else None
        p_values[name] = float(pv) if not np.isnan(pv) else None
        if not np.isnan(s):
            cis[name] = (float(b - 1.96 * s), float(b + 1.96 * s))
        else:
            cis[name] = (None, None)

    return CoxPHResult(
        coefficients=coefficients, hazard_ratios=hazard_ratios,
        standard_errors=standard_errors, p_values=p_values,
        log_hr_ci95=cis, n=n, n_events=int(events.sum()), converged=res.success,
    )


@dataclass
class MetaAnalysisResult:
    pooled_log_hr: float
    pooled_hr: float
    pooled_ci95: tuple[float, float]
    pooled_p_value: float
    i_squared: float
    q_statistic: float
    q_p_value: float
    model: str  # "fixed" or "random" (auto-selected on heterogeneity)
    per_cohort: list[dict]


def cross_cohort_meta_analysis(cohort_results: list[dict]) -> MetaAnalysisResult:
    """
    Inverse-variance meta-analysis across independent cohorts.

    cohort_results: list of {"cohort": str, "log_hr": float, "se": float, "n": int}
    Uses DerSimonian-Laird random-effects if I^2 > 50% (substantial heterogeneity),
    otherwise fixed-effect. This is exactly the step a researcher currently does
    by hand (copy HRs from TCGA/CGGA/GLASS papers into a forest-plot spreadsheet).
    """
    log_hrs = np.array([c["log_hr"] for c in cohort_results], dtype=float)
    ses = np.array([c["se"] for c in cohort_results], dtype=float)
    weights_fixed = 1 / (ses ** 2)

    pooled_fixed = np.sum(weights_fixed * log_hrs) / np.sum(weights_fixed)
    Q = np.sum(weights_fixed * (log_hrs - pooled_fixed) ** 2)
    df = len(cohort_results) - 1
    q_p = 1 - stats.chi2.cdf(Q, df) if df > 0 else 1.0
    i_squared = max(0.0, (Q - df) / Q) * 100 if Q > 0 and df > 0 else 0.0

    if i_squared > 50 and df > 0:
        C = np.sum(weights_fixed) - np.sum(weights_fixed ** 2) / np.sum(weights_fixed)
        tau2 = max(0.0, (Q - df) / C) if C > 0 else 0.0
        weights = 1 / (ses ** 2 + tau2)
        model = "random"
    else:
        weights = weights_fixed
        model = "fixed"

    pooled_log_hr = np.sum(weights * log_hrs) / np.sum(weights)
    pooled_se = math.sqrt(1 / np.sum(weights))
    z = pooled_log_hr / pooled_se
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))
    ci = (pooled_log_hr - 1.96 * pooled_se, pooled_log_hr + 1.96 * pooled_se)

    return MetaAnalysisResult(
        pooled_log_hr=float(pooled_log_hr),
        pooled_hr=float(math.exp(pooled_log_hr)),
        pooled_ci95=(float(math.exp(ci[0])), float(math.exp(ci[1]))),
        pooled_p_value=float(p_value),
        i_squared=float(i_squared),
        q_statistic=float(Q),
        q_p_value=float(q_p),
        model=model,
        per_cohort=cohort_results,
    )
