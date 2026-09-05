from pathlib import Path

path = Path('streamlit_app_v5.py')
text = path.read_text()
old = '''st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")
st.write(
    "Enter a gene symbol to evaluate its relevance in GBM across complementary biological and translational evidence. Results are organized to support target prioritization, evidence review, and experimental planning."
)
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")
'''
new = '''st.caption("Integrated gene-level evidence synthesis for glioblastoma research.")
st.caption("Note: Results are intended for research prioritization and hypothesis development, not clinical decision-making.")
'''
if old not in text:
    raise SystemExit('Expected intro block not found')
text = text.replace(old, new)
path.write_text(text)
