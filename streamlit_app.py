"""Streamlit entrypoint for GBM Gene Analysis.

Execute the guarded V6 page script on every Streamlit rerun. Using runpy avoids
Python's module-import cache suppressing the UI after widget interactions.
"""
from pathlib import Path
import runpy

_PAGE = Path(__file__).with_name("streamlit_app_v6_guarded.py")
runpy.run_path(str(_PAGE), run_name="__main__")
