from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()

old = '''title_col, info_col, spacer_col = st.columns(\n    [3.45, 0.28, 8.27],\n    gap="small",\n    vertical_alignment="center",\n)\nwith title_col:\n    st.title("GBM Gene Analysis")\nwith info_col:\n    st.button(\n        ":material/info:",\n        help="Open walkthrough",\n        key="open_walkthrough",\n        type="tertiary",\n        on_click=_open_walkthrough,\n    )\n'''

new = '''with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):\n    st.markdown(\n        "<div style='font-size:2.75rem;font-weight:700;line-height:1.2;letter-spacing:-0.02em;margin:0;padding:0;'>GBM Gene Analysis</div>",\n        unsafe_allow_html=True,\n        width="content",\n    )\n    st.button(\n        ":material/info:",\n        help="Open walkthrough",\n        key="open_walkthrough",\n        type="tertiary",\n        on_click=_open_walkthrough,\n    )\n'''

if old not in text:
    raise SystemExit("Expected title/info block not found")

text = text.replace(old, new, 1)
path.write_text(text)
