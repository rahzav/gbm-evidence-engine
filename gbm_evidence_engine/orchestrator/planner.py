"""
orchestrator/planner.py
========================

Decides WHICH connectors and analyses to run for a given query. In V1 this
is deliberately a deterministic, hand-written planner (a plain function), not
an LLM — see docs/ARCHITECTURE.md "AI layer" for why: query decomposition
for a single-gene evidence dossier has a small, well-understood set of
branches, and a deterministic planner is trivially reproducible (same query
-> same plan, forever) and impossible to hallucinate a wrong task list. The
brief's roadmap (V2-V4) calls for graduating to an LLM-based planner once
the query space is broad enough (free-text hypotheses, multi-gene set logic,
"what should I check next") that hand-written branches stop scaling — at
that point the LLM's job is still only to CHOOSE among the same deterministic
task primitives defined here, never to invent a new one on the fly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    CROSS_COHORT_SURVIVAL = "cross_cohort_survival"
    SPATIAL_ENRICHMENT = "spatial_enrichment"
    DEPENDENCY_SELECTIVITY = "dependency_selectivity"
    KNOWN_DRUGS = "known_drugs"
    BBB_LOOKUP = "bbb_lookup"
    TRIAL_LANDSCAPE = "trial_landscape"
    LITERATURE_SUPPORT = "literature_support"


@dataclass
class QueryPlan:
    target: str
    target_type: str  # "gene" | "gene_set" | "pathway"
    tasks: list[TaskType] = field(default_factory=list)
    cohorts: list[str] = field(default_factory=list)


DEFAULT_COHORTS = ["TCGA_GBM", "CGGA", "GLASS_recurrent"]


def plan_single_gene_dossier(gene: str, cohorts: list[str] | None = None) -> QueryPlan:
    """The V1 plan: every single-gene query runs the full evidence-layer set.
    (A V2 planner would let a researcher ask for a subset, e.g. "just survival
    across cohorts" — omitted here to keep V1's contract simple and complete.)"""
    return QueryPlan(
        target=gene,
        target_type="gene",
        tasks=[
            TaskType.CROSS_COHORT_SURVIVAL,
            TaskType.SPATIAL_ENRICHMENT,
            TaskType.DEPENDENCY_SELECTIVITY,
            TaskType.KNOWN_DRUGS,
            TaskType.BBB_LOOKUP,
            TaskType.TRIAL_LANDSCAPE,
            TaskType.LITERATURE_SUPPORT,
        ],
        cohorts=cohorts or DEFAULT_COHORTS,
    )


def plan_batch_dossier(genes: list[str], cohorts: list[str] | None = None) -> list[QueryPlan]:
    """High-value capability test #5: batch triage of a researcher's own
    differential-expression gene list. Same per-gene plan, just fanned out,
    with Benjamini-Hochberg correction applied across the batch afterward
    (see analysis/multiple_testing.py and orchestrator/synthesizer.py)."""
    return [plan_single_gene_dossier(g, cohorts) for g in genes]
