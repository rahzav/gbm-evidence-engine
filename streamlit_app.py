"""Streamlit entrypoint for Glia."""
from pathlib import Path
import runpy

_PAGE = Path(__file__).with_name("app_ui.py")
runpy.run_path(str(_PAGE), run_name="__main__")
