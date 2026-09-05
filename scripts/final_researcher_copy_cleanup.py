from pathlib import Path

path = Path("streamlit_app_v5.py")
text = path.read_text()

replacements = {
    '"credentials required": "Credentials required",': '"credentials required": "Unavailable",\n        "open live api": "Available",\n        "live api": "Available",',
    '"GLASS GBM-specific longitudinal analysis requires an authorized Synapse token. Until credentials are configured, this dimension remains unscored and evidence coverage is reduced."': '"GLASS longitudinal evidence is unavailable for this analysis. This dimension remains unscored and evidence coverage is reduced."',
    'st.caption("Therapeutic and clinical-development context is separated from the underlying biological evidence.")': 'st.caption("Therapeutic and clinical-development evidence.")',
    'st.caption("Detailed provenance, raw evidence records, source availability, and exports live here so they do not interrupt the main research workflow.")': 'st.caption("Detailed provenance, source availability, and research-profile exports.")',
    'st.warning("Gene set comparison is limited to 6 genes per run to maintain reasonable load on public research sources.")': 'st.warning("Gene set comparison is limited to 6 genes per run.")',
    'lines += ["", "## Data Source Status"] + [f"- **{k}:** {v}" for k, v in profile.source_status.items()]': 'lines += ["", "## Data Source Status"] + [\n        f"- **{str(k).replace(\'_\', \' \').title()}:** {display_status(v)}"\n        for k, v in profile.source_status.items()\n    ]',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"Missing copy target: {old}")
    text = text.replace(old, new, 1)

# Additional source-status normalization for backend-style availability labels.
old = 'return mapping.get(raw.lower(), raw[:1].upper() + raw[1:])'
new = '''normalized = raw.lower()
    if normalized in mapping:
        return mapping[normalized]
    if "credentials" in normalized or "token" in normalized:
        return "Unavailable"
    if "live api" in normalized or normalized in {"open", "public"}:
        return "Available"
    return raw[:1].upper() + raw[1:]'''
if old not in text:
    raise SystemExit("Missing display_status return")
text = text.replace(old, new, 1)

for forbidden in [
    "authorized Synapse token",
    "credentials are configured",
    "maintain reasonable load on public research sources",
    "so they do not interrupt the main research workflow",
]:
    if forbidden in text:
        raise SystemExit(f"Researcher-facing cleanup incomplete: {forbidden}")

path.write_text(text)
print("final researcher-facing copy cleanup applied")
