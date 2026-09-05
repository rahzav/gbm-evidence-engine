# Production Release Validation

This document separates software validation from scientific validation for the Glia V7 evidence engine.

## Release gate

The production release should not be merged until all of the following pass on the final integration branch:

1. production entrypoint resolves only to `app_ui.py`;
2. API health reports `7.0.0` and imports the production V7 facade;
3. Gene Analysis, Target Pair Analysis, Researcher Data, and Gene Set Comparison are present in the shipped UI;
4. the primary gene action is **Build dossier**;
5. deterministic scientific/statistical tests pass;
6. the compact GBmap reference passes schema, coverage, ambiguity, and representative-gene checks;
7. benchmark cases include known-positive, known-negative, and context-dependent behavior;
8. Streamlit loads, reruns, walkthrough state, and production controls pass AppTest smoke tests;
9. API validation rejects malformed request lengths and invalid pair inputs;
10. release metadata, citation metadata, license, and researcher-data handling documentation are present.

## Integrated QA matrix

The final QA pass covers the following behaviors:

| Workflow / condition | Required check |
|---|---|
| Gene Analysis | Build a representative dossier and confirm score, coverage, confidence, publications, source status, and export metadata |
| Target Pair Analysis | Build a representative pair dossier and confirm rationale, confidence, cell-state component, model relevance, and guardrail language |
| Researcher Data | Parse valid processed CSV/TSV data, optional p/FDR fields, malformed tables, missing numeric effects, and export metadata |
| Gene Set Comparison | Compare a bounded gene list and enforce the production size limit |
| Invalid genes | Fail clearly without fabricating evidence |
| Unavailable sources | Reduce coverage / report source gaps rather than treating missing data as negative evidence |
| Partial evidence | Preserve the available dimensions and confidence state without imputing missing biology |
| Publications | Return linked publication metadata when Europe PMC is available |
| Reruns | Preserve a usable Streamlit page after widget interaction |
| Walkthrough | Open on first use, dismiss, and reopen from the title control |
| API | Validate `/health`, `/profile`, `/profile/batch`, `/combination`, and `/signature` contracts |
| Exports | Include software version `7.0.0` in structured profile, pair, and researcher-signature outputs |

## Benchmark status

The bundled benchmark is a **current-data regression benchmark**. It uses a fixed balanced set of known-positive, known-negative, and context-dependent GBM cases to test whether established evidence patterns and scientific safeguards are preserved by the current system. It must not be described as retrospective discovery validation.

Because several benchmark inputs are live public sources, source availability is evaluated separately from scientific behavior. A biological threshold that depends on an unavailable upstream source is reported as **not evaluable** for that run and is excluded from pass/fail accuracy; it is never silently counted as a pass. The report separately exposes source-limited cases and checks. This prevents a transient API outage from being mislabeled as a scientific regression while retaining the fixed biological threshold whenever the source is available.

True retrospective evaluation requires evidence snapshots frozen to a declared historical date. Prospective evaluation requires hypotheses to be registered before later experimental or external evidence becomes available.

## External researcher validation

External researcher evaluation is intentionally a separate release phase. Software tests cannot substitute for expert assessment of whether the dossiers improve real research decisions.

Recommended evaluation protocol:

1. recruit independent GBM researchers who did not build the system;
2. give each researcher a fixed set of target, pair, and processed-signature tasks;
3. collect blinded ratings for evidence completeness, traceability, usefulness, misleadingness, and actionability;
4. record whether the dossier changes the proposed next experiment and why;
5. log concrete missing evidence or workflow friction as post-release issues;
6. pre-register prospective hypotheses only after this usability/credibility pass.

The project should not claim demonstrated research utility until that external evaluation has been completed and reported.

## Performance and concurrency

Release testing should include a small host-level concurrency check after deployment to `main`. The objective is not load testing at scale; it is to confirm that bounded concurrency, caching, and memory behavior remain stable for a small number of simultaneous researcher sessions on the actual deployment host.

The repository includes `scripts/host_smoke.py` for this purpose. Example:

```bash
python scripts/host_smoke.py https://YOUR-DEPLOYED-HOST --requests 12 --concurrency 3
```

This host-level check must be run against the actual deployment URL after the final code is live; repository CI cannot substitute for the behavior of the production hosting environment.
