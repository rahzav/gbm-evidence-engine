"""Streamlit entrypoint for GBM Gene Analysis.

Execute the V5 page script on every Streamlit rerun. Importing the page module
once is not sufficient because Python caches imported modules between widget
reruns, which can leave the app blank after an interaction.
"""
from pathlib import Path
import runpy

_PAGE = Path(__file__).with_name("streamlit_app_v5.py")
runpy.run_path(str(_PAGE), run_name="__main__")
