from pathlib import Path

path = Path("glia_interface.py")
text = path.read_text(encoding="utf-8")
old = '''#glia-launcher {
  position:fixed; z-index:1000001; right:20px; bottom:72px;
  border:0;
  background:var(--st-primary-color, #ff4b4b); color:#fff; border-radius:999px;
  box-shadow:0 10px 28px rgba(0,0,0,.20); padding:10px 16px 10px 11px;
  display:none; align-items:center; gap:8px; font-weight:760; cursor:pointer;
  letter-spacing:-.01em;
}
#glia-launcher:hover { filter:brightness(.96); transform:translateY(-1px); }
'''
new = '''#glia-launcher {
  position:fixed; z-index:1000001; right:0; top:48%;
  transform:translateY(-50%);
  border:0;
  background:var(--st-primary-color, #ff4b4b); color:#fff;
  border-radius:14px 0 0 14px;
  box-shadow:-6px 8px 24px rgba(0,0,0,.18); padding:10px 14px 10px 10px;
  display:none; align-items:center; gap:8px; font-weight:760; cursor:pointer;
  letter-spacing:-.01em;
}
#glia-launcher:hover { filter:brightness(.96); padding-right:17px; }
'''
if old not in text:
    raise SystemExit("Expected current Glia launcher CSS not found")
text = text.replace(old, new, 1)
marker = '''@media (max-width: 980px) {
  #glia-shell { width:min(92vw, 390px); }
'''
replacement = '''@media (max-width: 980px) {
  #glia-launcher {
    top:auto; right:16px; bottom:76px; transform:none;
    border-radius:999px; padding:10px 15px 10px 10px;
    box-shadow:0 10px 28px rgba(0,0,0,.20);
  }
  #glia-launcher:hover { padding-right:15px; }
  #glia-shell { width:min(92vw, 390px); }
'''
if marker not in text:
    raise SystemExit("Expected responsive Glia block not found")
path.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
