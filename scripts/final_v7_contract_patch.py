#!/usr/bin/env python3
from pathlib import Path

p = Path("gbm_evidence_engine/research_intelligence_v7.py")
t = p.read_text()
old = '    pub_count = int(lit.get("gbm_publication_count") or lit.get("total") or 0)\n'
new = '    pub_count = int(lit.get("hit_count") or lit.get("gbm_publication_count") or lit.get("total") or 0)\n'
if old in t:
    t = t.replace(old, new, 1)
elif new not in t:
    raise SystemExit("Literature confidence field contract drifted")
p.write_text(t)

p = Path("tests/test_research_intelligence_v7.py")
t = p.read_text()
t = t.replace('"literature": {"ok": True, "gbm_publication_count": 150},', '"literature": {"ok": True, "hit_count": 150},')
p.write_text(t)
