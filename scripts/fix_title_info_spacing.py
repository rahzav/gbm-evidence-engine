from pathlib import Path

path = Path('streamlit_app_v5.py')
text = path.read_text()
old = '''with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):\n    st.title("GBM Gene Analysis")\n    st.button(\n'''
new = '''with st.container(horizontal=True, vertical_alignment="center", gap="xxsmall"):\n    st.title("GBM Gene Analysis", width="content")\n    st.button(\n'''
if old not in text:
    raise SystemExit('Expected title block not found')
text = text.replace(old, new, 1)
path.write_text(text)
