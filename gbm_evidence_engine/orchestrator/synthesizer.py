"""
orchestrator/synthesizer.py
=============================

This is where the product brief's hardest requirement lives:

    "Do not let the LLM fabricate computations."
    "Every important conclusion must expose its evidence."

Design: the synthesis step is only ever allowed to READ an already-assembled
Dossier (whose every number was produced by analysis/*.py or copied verbatim
from a Provenance-tracked source) and WRITE prose that cites those numbers.
It is never handed raw data and asked to compute or estimate anything itself.

In a networked production deployment, `generate_synthesis()` below would
call the Claude API with a strict system prompt (shown in
CLAUDE_SYNTHESIS_SYSTEM_PROMPT) and the full dossier JSON as the only
permitted source of facts. This sandbox has no network access to the
Anthropic API, so V1 here ships a deterministic template renderer instead —
it produces the same kind of grounded, citation-anchored prose, just via
string formatting rather than a language model. Critically, the enforcement
mechanism — `validate_numeric_grounding()` — is independent of which of the
two generates the text: it re-parses whatever prose comes out and rejects
any numeric claim that cannot be traced back to a real EvidenceRecord. That
validator is what should run in front of an LLM-generated synthesis in
production, and tests/test_grounding_validator.py proves it actually catches
a fabricated number, not just a hypothetical one.
"""

from __future__ import annotations
import re
from dataclasses import dataclass

from gbm_evidence_engine.evidence_model import Dossier, EvidenceTier

CLAUDE_SYNTHESIS_SYSTEM_PROMPT = """\
You are the synthesis layer of a GBM research evidence engine. You will be
given a JSON evidence dossier. Write a short (150-250 word) plain-language
synthesis for a researcher.

Hard rules:
1. Every number you state (a hazard ratio, a p-value, a percentage, a sample
   size) MUST appear verbatim in the dossier JSON you were given. Do not
   round, do not recompute, do not estimate.
2. Never state a claim from a tier other than what the dossier assigns it
   (do not describe an AI_GENERATED_INFERENCE as if it were observed data).
3. If cohorts disagree, say so explicitly and do not average away the
   disagreement into a single confident sentence.
4. If you want to suggest a follow-up experiment, prefix it with
   "Suggested follow-up (AI inference, not evidence):".
5. Do not cite a source that is not present in the dossier's evidence list.
"""


def _fmt(x, digits=2):
    if x is None:
        return "N/A"
    if isinstance(x, float):
        return f"{x:.{digits}g}"
    return str(x)


def generate_synthesis(dossier: Dossier) -> str:
    """Deterministic V1 stand-in for the Claude-API call described above.
    Every sentence is built directly from dossier.evidence values, so by
    construction it passes validate_numeric_grounding() — see
    tests/test_grounding_validator.py for what happens when it doesn't."""
    lines = []
    stat_records = dossier.by_tier(EvidenceTier.STATISTICAL_ASSOCIATION)
    lit_records = dossier.by_tier(EvidenceTier.LITERATURE_SUPPORTED_CLAIM)
    conflict_records = dossier.by_tier(EvidenceTier.CONFLICTING_EVIDENCE)
    ai_records = dossier.by_tier(EvidenceTier.AI_GENERATED_INFERENCE)

    lines.append(f"Evidence dossier for {dossier.target}: {len(dossier.evidence)} records assembled "
                 f"across {len({e.provenance.source_dataset for e in dossier.evidence})} sources.")

    for rec in stat_records:
        if rec.p_value is not None:
            lines.append(f"{rec.claim_text} ({rec.statistic_name}={_fmt(rec.statistic_value)}, "
                         f"p={_fmt(rec.p_value, 3)}, n={rec.provenance.sample_size}).")

    if conflict_records:
        lines.append("Note — evidence does not agree across cohorts:")
        for rec in conflict_records:
            lines.append(f"  * {rec.claim_text}")

    for rec in lit_records[:3]:
        lines.append(f"Literature: {rec.claim_text} [{rec.provenance.citation}]")

    for rec in ai_records:
        lines.append(f"Suggested follow-up (AI inference, not evidence): {rec.claim_text}")

    if dossier.warnings:
        lines.append("Scientific safeguards flagged: " + "; ".join(dossier.warnings))

    return "\n".join(lines)


@dataclass
class GroundingCheck:
    ok: bool
    unmatched_numbers: list[str]
    total_numbers_checked: int


_NUMBER_RE = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")
_BRACKETED_CITATION_RE = re.compile(r"\[[^\]]*\]")


def _add_roundings(numbers: set[str], val: float) -> None:
    for digits in (0, 1, 2, 3, 4):
        numbers.add(f"{val:.{digits}f}".rstrip("0").rstrip("."))
        numbers.add(f"{val:.{digits}g}")
    numbers.add(str(val))


def _collect_dossier_numbers(dossier: Dossier) -> set[str]:
    """Every number that legitimately appears anywhere in the dossier's
    evidence, at a couple of common roundings, so a validator comparing
    formatted text doesn't false-positive on '1.5' vs '1.50'.

    Includes two categories beyond per-record statistics:
    - `additional_stats`: supplementary numbers (e.g. group medians) a claim
      references beyond its primary statistic_value.
    - dossier-level structural counts (record/source counts): these are true
      by construction (re-derivable by calling len()/set() on the dossier
      itself), so a sentence stating them is grounded even though they don't
      live inside any single EvidenceRecord's statistic fields.
    """
    numbers = set()
    for rec in dossier.evidence:
        for val in (rec.statistic_value, rec.p_value, rec.corrected_p_value, rec.effect_size):
            if val is None:
                continue
            _add_roundings(numbers, val)
        for val in rec.additional_stats.values():
            _add_roundings(numbers, val)
        if rec.confidence_interval:
            for v in rec.confidence_interval:
                if v is None:
                    continue
                _add_roundings(numbers, v)
        if rec.provenance.sample_size is not None:
            numbers.add(str(rec.provenance.sample_size))

    # Structural counts, true by construction -- see docstring above.
    numbers.add(str(len(dossier.evidence)))
    numbers.add(str(len({e.provenance.source_dataset for e in dossier.evidence})))
    return numbers


def validate_numeric_grounding(synthesis_text: str, dossier: Dossier) -> GroundingCheck:
    """Extracts every number-looking token from the synthesis text and checks
    it is traceable to something actually in the dossier. This is the concrete,
    runnable version of the brief's 'hallucination resistance' validation
    requirement — see tests/test_grounding_validator.py for a case where it
    correctly REJECTS a synthesis containing a fabricated statistic.

    Bracketed citations (e.g. "[PMC7275784]", "[Smith et al. 2020]") are
    stripped before scanning: a PMC ID, DOI fragment, or publication year is
    a source reference, not a numeric claim about data, and treating it as
    one would make every correctly-cited sentence look "unmatched"."""
    allowed = _collect_dossier_numbers(dossier)
    text_without_citations = _BRACKETED_CITATION_RE.sub(" ", synthesis_text)
    found = _NUMBER_RE.findall(text_without_citations)
    unmatched = []
    for tok in found:
        try:
            f = float(tok)
        except ValueError:
            continue
        # small integers (0, 1) are common as generic language, not statistics -- skip.
        # 95 is skipped only as the "95% CI" convention token, never as a general
        # percentage: a claimed prevalence like "45%" still must be grounded normally.
        if f in (0, 1):
            continue
        if f == 95 and tok + "%" in text_without_citations:
            continue
        normalized_variants = {tok, tok.rstrip("0").rstrip(".")}
        if not (normalized_variants & allowed):
            unmatched.append(tok)
    return GroundingCheck(ok=(len(unmatched) == 0), unmatched_numbers=unmatched,
                           total_numbers_checked=len(found))
