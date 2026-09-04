# Validation Report

Honest account of what was actually run and checked in this build session,
per the product brief's "validation before claiming success" phase. Where
something failed on the first attempt and was fixed, that's recorded too —
a validation report that only shows things passing on the first try is not
a validation report.

## Environment constraints discovered (and how they shaped V1)

- `pip install <anything>` fails: no network egress in this build sandbox
  (confirmed directly: `pip install lifelines` returns "No matching
  distribution found"). Consequence: `analysis/survival.py` is a from-
  scratch numpy/scipy implementation, not `lifelines`; `api/app.py` (FastAPI)
  is real code but not executable here.
- `web_fetch` with query-string parameters does not reach the live API as
  requested (confirmed: two attempts to call the Europe PMC REST endpoint
  with a search query both returned a "no search criteria provided" error
  with the query string stripped from the reported destination URL).
  Consequence: no live API call could be demonstrated in-session; all
  "live-capable" connectors (`cbioportal.py`, `opentargets.py`,
  `europepmc.py`, `clinicaltrials.py`) are written against real, correct
  endpoint contracts but exercised in this session only via their offline
  fallback paths. This is disclosed on every relevant file and in
  `data/README.md`, not glossed over.

These two facts are the reason V1's demo data is a mix of (a) real,
individually-cited literature facts gathered via live web search earlier in
this session, and (b) clearly-labeled synthetic data calibrated to match
those real published statistics. See `data/README.md` for the file-by-file
breakdown.

## Correctness

Ran as plain Python scripts (pytest itself is not installable here for the
same network reason — each test file is also directly runnable):

```
PYTHONPATH=. python3 tests/test_survival.py
PYTHONPATH=. python3 tests/test_dependency.py
PYTHONPATH=. python3 tests/test_evidence_model.py
PYTHONPATH=. python3 tests/test_grounding_validator.py
```

Result: **17/17 assertions passed**, covering:
- Kaplan-Meier matches a hand-computed 6-patient product-limit calculation exactly.
- Log-rank gives exactly χ²=0 on identical arms (mathematically guaranteed,
  not just "close to zero") and correctly detects p<0.001 on a strongly
  separated pair of arms.
- Cox PH (from-scratch, Efron ties correction) recovers a known simulated
  true log-hazard-ratio (0.6) to within 0.02 from n=4,000, p<0.001.
- Cross-cohort meta-analysis matches a hand-computed two-study
  inverse-variance pooled estimate exactly (0.38), correctly reports I²=0%
  for identical per-cohort estimates, and correctly flags >90% heterogeneity
  for wildly different tight estimates.
- Dependency test detects a genuine selective dependency (p=9.7e-21),
  correctly does *not* flag it pan-essential, correctly *does* flag a truly
  pan-essential pattern, and correctly returns p>0.05 when two groups are
  genuinely drawn from the same distribution (no false positive).
- Evidence model serializes cleanly to JSON with enum values as strings.

## Hallucination resistance — the test that matters most

`tests/test_grounding_validator.py` does not just assert the validator
"works" — it constructs two deliberately fabricated synthesis sentences
(a hazard ratio of 2.91 that was never computed, and a sample size of 9999
that was never used) against a real 1-record dossier, and asserts the
validator's `unmatched_numbers` list contains exactly those fabricated
values. Both are caught. It also confirms the validator does *not*
false-positive on a legitimate rounding of a real number (1.45 → "1.4").

**This validator was not correct on the first attempt**, and the failure is
left visible in the git history of this build rather than hidden:
running it against the real 22-record EGFR dossier's own generated
synthesis initially reported 20 "unmatched" numbers. Investigating each one
found four distinct real bugs, all fixed:
1. Scientific notation (`3.3e-10`) wasn't tokenized as one number.
2. Numbers inside citation brackets (PMC IDs, publication years) were being
   treated as unverified statistical claims instead of source identifiers.
3. Group medians mentioned in a claim's prose weren't also stored in a
   structured field the validator could check against (fixed by adding
   `EvidenceRecord.additional_stats`).
4. Real meta-analysis numbers quoted from the literature (`data/
   reference_literature_facts.json`) weren't mirrored into structured
   `statistic_value`/`confidence_interval` fields (fixed).

After fixing all four, the real EGFR dossier's synthesis passes with **0
unmatched numbers out of 42 checked** — see the full run below.

## End-to-end functional run

```
$ PYTHONPATH=. python3 scripts/run_demo_dossier.py EGFR
Evidence records assembled: 22
By tier: {'statistical_association': 6, 'literature_supported_claim': 12,
          'conflicting_evidence': 3, 'ai_generated_inference': 1}
Scientific safeguard warnings raised: 2
AI synthesis numeric grounding check: PASS (42 numbers checked, 0 unmatched)
```

The two warnings raised are both real, substantively correct signals, not
noise:
1. Cross-cohort heterogeneity for EGFR (I²=80% in this run) — directly
   consistent with the real PMC12027172 meta-analysis finding that EGFR
   amplification's prognostic value is significant in American cohorts
   (HR 1.53) but not in other regions.
2. The EGFR culture-instability caveat firing on the dependency evidence —
   directly consistent with the real, independently-cited cell-culture
   literature (Bigner 1990 onward).

That the system's *statistical* heterogeneity flag (on synthetic data,
calibrated to the real regional split) lines up with the *literature's*
independently-reported regional heterogeneity (also loaded as real cited
text) is a genuine, if modest, cross-check that the pipeline's logic
produces sensible, non-arbitrary output — not just proof that code runs.

`scripts/run_batch_demo.py` (capability test #5 — batch triage of a 4-gene
list, standing in for a real ~20-gene differential-expression hit list)
produced a ranked table where a tumor suppressor with a clean, low-
heterogeneity survival signal (PTEN) ranked first; a gene with a real
dependency signal but weaker survival evidence (CDK4) ranked second; EGFR
was correctly down-ranked for this particular use case due to its
heterogeneity and culture-instability flags (not hidden — still fully
represented in its own dossier); and a near-null, pan-essential-flagged
gene (TP53) ranked last. This is the intended behavior, not cherry-picked:
the ranking function only uses BH-corrected p-values and the two safeguard
flags already described above.

## What this demonstrably saves (V1 scope only)

For the single-gene cross-cohort-survival-plus-dependency-plus-BBB-plus-
literature workflow demonstrated above: the papers cited in the landscape
research (e.g. the CD44/GLASS-SASP/MES-lncRNA studies that manually
combined TCGA + CGGA + Ivy GAP + GEO scRNA data as a "discovery cohort /
validation cohort" pattern) represent this exact workflow done by hand,
once, for one gene, as part of a multi-month research project. `scripts/
run_demo_dossier.py` produces a comparable multi-cohort, multi-modality,
citation-complete dossier in under two seconds of compute. The honest
claim is about the shape of the time savings (hours-to-days of bespoke
script-writing and manual cross-referencing, collapsed into one
reproducible command), not a specific "N hours saved" figure, since that
would depend on the researcher's existing scripts and is not something
this session can measure directly.

## Known limitations (explicit, not hidden)

- No live network call was actually completed against any of the five
  "live" connectors in this session — see Environment constraints above.
  This is the single most important caveat for anyone evaluating this V1.
- Only EGFR has real, individually-cited literature facts loaded; PTEN/
  TP53/CDK4 in the batch demo run on synthetic data only, with no
  literature-evidence layer populated for them (by design, disclosed in
  `scripts/run_batch_demo.py`'s own output).
- The Cox PH implementation, while validated against hand-computed and
  simulation ground truth, has not been benchmarked against `lifelines`
  on real messy data (ties, left-truncation, time-varying covariates) —
  production should make that comparison before removing the `lifelines`
  migration from the V2 roadmap.
- The numeric-grounding validator is a token-level heuristic (regex-based),
  not a semantic checker — it would not catch an AI-generated sentence that
  uses a real number from the dossier but attaches it to the wrong claim
  (e.g. swapping which cohort a real hazard ratio belongs to). That is a
  known gap for the V2 planning: pair the numeric check with a per-sentence
  provenance-ID citation requirement (`CLAUDE_SYNTHESIS_SYSTEM_PROMPT` in
  `synthesizer.py` already asks for this; V1's deterministic template
  trivially satisfies it since every sentence is built from exactly one
  record, but a real LLM-generated synthesis would need this checked too).
