"""Guarded Streamlit launcher for GBM Gene Analysis V6.

The V6 page remains presentation-only. Before executing it, replace the public
V6 discovery callables with the production facade that applies stricter
scientific hypothesis guardrails and trims oversized pair-analysis payloads.
"""
from pathlib import Path
import runpy

from gbm_evidence_engine import research_intelligence_v6 as core
from gbm_evidence_engine import research_discovery as guarded

core.build_research_profile = guarded.build_research_profile
core.rank_gene_list = guarded.rank_gene_list
core.evaluate_gene_pair = guarded.evaluate_gene_pair
core.analyze_researcher_signature = guarded.analyze_researcher_signature

_PAGE = Path(__file__).with_name("streamlit_app_v6.py")
runpy.run_path(str(_PAGE), run_name="__main__")
