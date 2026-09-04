"""Production launcher for frozen-scope GBM Gene Analysis V7.

The presentation module imports from ``research_intelligence_v7``. Replace the
public callables with the production facade first so target-pair analysis reuses
exactly two full profiles instead of performing redundant builds.
"""
from pathlib import Path
import runpy

from gbm_evidence_engine import research_intelligence_v7 as core
from gbm_evidence_engine import research_intelligence_v7_prod as prod

core.build_research_profile = prod.build_research_profile
core.rank_gene_list = prod.rank_gene_list
core.evaluate_gene_pair = prod.evaluate_gene_pair
core.analyze_researcher_signature = prod.analyze_researcher_signature

_PAGE = Path(__file__).with_name("streamlit_app_v7.py")
runpy.run_path(str(_PAGE), run_name="__main__")
