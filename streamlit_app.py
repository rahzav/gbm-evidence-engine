"""Streamlit entrypoint for GBM Gene Analysis.

Execute the resource-safe V7 launcher on every Streamlit rerun. Using runpy
avoids Python's module-import cache suppressing the UI after widget interactions.
"""
from pathlib import Path
import runpy

_PAGE = Path(__file__).with_name("streamlit_app_v7_prod.py")
runpy.run_path(str(_PAGE), run_name="__main__")
