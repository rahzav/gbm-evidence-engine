"""
run_demo_dossier.py
=====================

The single command that proves the V1 vertical slice works end to end:

    PYTHONPATH=. python3 scripts/run_demo_dossier.py EGFR

Produces:
  - out/EGFR_dossier.json    (full machine-readable evidence dossier)
  - out/EGFR_report.md       (human-readable version, ready for a lab meeting)

and prints a validation summary (record count, grounding check, warnings)
to stdout, matching the "Functional validation results" milestone in the
product brief.
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from gbm_evidence_engine.orchestrator import build_single_gene_dossier, generate_synthesis, validate_numeric_grounding
from gbm_evidence_engine.evidence_model import EvidenceTier

OUT_DIR = Path(__file__).resolve().parent.parent / "out"
OUT_DIR.mkdir(exist_ok=True)


def render_markdown(dossier) -> str:
    lines = [f"# GBM Evidence Dossier: {dossier.target}", "",
             f"*Query: {dossier.query}*", f"*Generated: {dossier.generated_at}*",
             f"*Session ID: {dossier.session_id}*", ""]

    if dossier.warnings:
        lines.append("## ⚠️ Scientific safeguards flagged")
        for w in dossier.warnings:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## AI synthesis")
    lines.append(f"*(grounding check: {'PASSED' if dossier.ai_synthesis_grounding_ok else 'FAILED — see below'})*")
    lines.append("")
    lines.append(dossier.ai_synthesis or "*(none generated)*")
    lines.append("")

    for tier in EvidenceTier:
        records = dossier.by_tier(tier)
        if not records:
            continue
        lines.append(f"## Evidence tier: {tier.value}")
        for r in records:
            lines.append(f"### {r.claim_text}")
            meta = []
            if r.statistic_name:
                meta.append(f"{r.statistic_name}={r.statistic_value}")
            if r.p_value is not None:
                meta.append(f"p={r.p_value:.3g}")
            if r.confidence_interval and r.confidence_interval[0] is not None:
                meta.append(f"95% CI [{r.confidence_interval[0]:.3g}, {r.confidence_interval[1]:.3g}]")
            if meta:
                lines.append("- **Statistics:** " + ", ".join(meta))
            lines.append(f"- **Source:** {r.provenance.source_dataset} ({r.provenance.dataset_version}) "
                         f"— access: {r.provenance.access_tier.value}")
            if r.provenance.sample_size:
                lines.append(f"- **n:** {r.provenance.sample_size}")
            if r.provenance.method:
                lines.append(f"- **Method:** {r.provenance.method}")
            if r.provenance.citation:
                lines.append(f"- **Citation:** {r.provenance.citation}")
            if r.provenance.citation_url:
                lines.append(f"- **Link:** {r.provenance.citation_url}")
            lines.append(f"- **Confidence:** {r.confidence.value}")
            for c in r.caveats:
                lines.append(f"- ⚠️ **Caveat:** {c}")
            lines.append("")
    return "\n".join(lines)


def main():
    gene = sys.argv[1] if len(sys.argv) > 1 else "EGFR"
    print(f"Building evidence dossier for {gene}...")
    dossier = build_single_gene_dossier(gene)

    synthesis = generate_synthesis(dossier)
    check = validate_numeric_grounding(synthesis, dossier)
    dossier.ai_synthesis = synthesis
    dossier.ai_synthesis_grounding_ok = check.ok

    json_path = OUT_DIR / f"{gene}_dossier.json"
    md_path = OUT_DIR / f"{gene}_report.md"
    json_path.write_text(dossier.to_json())
    md_path.write_text(render_markdown(dossier))

    print(f"\n=== VALIDATION SUMMARY for {gene} ===")
    print(f"Evidence records assembled: {len(dossier.evidence)}")
    tier_counts = {t.value: len(dossier.by_tier(t)) for t in EvidenceTier if dossier.by_tier(t)}
    print(f"By tier: {tier_counts}")
    print(f"Scientific safeguard warnings raised: {len(dossier.warnings)}")
    print(f"AI synthesis numeric grounding check: {'PASS' if check.ok else 'FAIL'} "
          f"({check.total_numbers_checked} numbers checked, {len(check.unmatched_numbers)} unmatched)")
    print(f"\nWrote: {json_path}")
    print(f"Wrote: {md_path}")


if __name__ == "__main__":
    main()
