from pathlib import Path

# Add a stable release identifier to exported profiles.
p = Path('gbm_evidence_engine/research_intelligence.py')
t = p.read_text(encoding='utf-8')
old = '    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())\n\n    def to_dict(self) -> dict:\n        return {\n            "gene": self.gene,\n            "generated_at": self.generated_at,\n'
new = '    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())\n    software_version: str = "7.0.0"\n\n    def to_dict(self) -> dict:\n        return {\n            "gene": self.gene,\n            "generated_at": self.generated_at,\n            "software_version": self.software_version,\n'
if old in t:
    t = t.replace(old, new, 1)
elif '"software_version": self.software_version' not in t:
    raise SystemExit('ResearchProfile release metadata marker drifted')
p.write_text(t, encoding='utf-8')

# Remove implementation-version wording from researcher-visible source status.
p = Path('gbm_evidence_engine/research_intelligence_v7.py')
t = p.read_text(encoding='utf-8')
t = t.replace(
    'profile.source_status["V7 confidence/model relevance"] = "active; contextual and non-scoring"',
    'profile.source_status["Confidence and model relevance"] = "active; contextual and non-scoring"',
)
p.write_text(t, encoding='utf-8')

# Keep runtime dependency comments product-facing.
p = Path('requirements.txt')
t = p.read_text(encoding='utf-8')
t = t.replace(
    '# Web UI. V7 production audits and rerun regression tests are validated on this runtime.',
    '# Web UI. Production interaction and rerun tests are validated on this runtime.',
)
p.write_text(t, encoding='utf-8')

# Researcher-facing UI should not expose internal version labels.
ui = Path('app_ui.py').read_text(encoding='utf-8')
for label in ('V5', 'V6', 'V7'):
    if label in ui:
        raise SystemExit(f'Internal implementation label remains in app_ui.py: {label}')

print('FINAL PRODUCT METADATA POLISH OK')
