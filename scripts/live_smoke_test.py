"""Network smoke test for deployment environments. Does not run in offline unit CI."""
from gbm_evidence_engine.research_intelligence import build_research_profile

p = build_research_profile("EGFR")
print("gene:", p.gene)
print("score:", p.score.overall, "coverage:", p.score.evidence_coverage_pct)
print("sources:", p.source_status)
live_count = sum(v == "live" for v in p.source_status.values())
assert live_count >= 2, f"Too few public live sources responded: {p.source_status}"
assert len(p.dossier.evidence) >= 1, "No live evidence records were assembled"
print("LIVE SMOKE TEST PASSED")
