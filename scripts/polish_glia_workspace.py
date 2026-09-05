from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Expected {label} not found")
    return text.replace(old, new, 1)


# glia_interface.py
path = Path("glia_interface.py")
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    '''#glia-selection-action {
  position:fixed; z-index:1000002; display:none;
  border:1px solid color-mix(in srgb, var(--st-text-color, #111) 17%, transparent);
  background:var(--st-background-color, #fff); color:inherit; border-radius:8px;
  box-shadow:0 6px 20px rgba(0,0,0,.16); padding:6px 9px; font-size:.76rem;
  font-weight:720; cursor:pointer;
}
#glia-selection-action.glia-visible { display:block; }

body.glia-panel-open [data-testid="stAppViewBlockContainer"] {
  max-width: calc(100vw - 390px) !important;
  padding-right: 2rem !important;
  margin-left: 0 !important;
  margin-right: auto !important;
}

@media (max-width: 980px) {
  #glia-shell { width:min(92vw, 390px); }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] { max-width:100% !important; padding-right:1rem !important; }
}
''',
    '''#glia-selection-action {
  position:fixed; z-index:1000002; display:none;
  border:1px solid color-mix(in srgb, var(--st-text-color, #111) 24%, transparent);
  background:var(--st-text-color, #111); color:var(--st-background-color, #fff); border-radius:8px;
  box-shadow:0 6px 20px rgba(0,0,0,.18); padding:6px 9px; font-size:.76rem;
  font-weight:720; cursor:pointer;
}
#glia-selection-action.glia-visible { display:block; }

@media (min-width: 981px) {
  body.glia-panel-open [data-testid="stAppViewContainer"] {
    width: calc(100% - 390px) !important;
    max-width: calc(100% - 390px) !important;
  }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] {
    width:100% !important;
    max-width:100% !important;
    padding-right:2rem !important;
  }
}

@media (max-width: 980px) {
  #glia-shell { width:min(92vw, 390px); }
  body.glia-panel-open [data-testid="stAppViewContainer"] { width:100% !important; max-width:100% !important; }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] { max-width:100% !important; padding-right:1rem !important; }
}
''',
    "selection/layout CSS",
)

text = replace_once(
    text,
    '''  const setOpen = (open) => {
    runtime.open = Boolean(open);
    try { localStorage.setItem(UI_KEY, JSON.stringify({open: runtime.open})); } catch (_) {}
    render();
  };

  const memory = data.memory_summary || {};
''',
    '''  const workspaceTarget = () =>
    document.querySelector('[data-testid="stAppViewContainer"]') || document.querySelector('.stApp');
  const syncWorkspaceLayout = () => {
    const target = workspaceTarget();
    if (!target) return;
    if (runtime.open && window.innerWidth > 980) {
      target.style.width = "calc(100% - 390px)";
      target.style.maxWidth = "calc(100% - 390px)";
      target.style.marginRight = "390px";
      target.style.transition = "width .18s ease, max-width .18s ease, margin-right .18s ease";
    } else {
      target.style.removeProperty("width");
      target.style.removeProperty("max-width");
      target.style.removeProperty("margin-right");
      target.style.removeProperty("transition");
    }
  };
  const setOpen = (open) => {
    runtime.open = Boolean(open);
    try { localStorage.setItem(UI_KEY, JSON.stringify({open: runtime.open})); } catch (_) {}
    render();
  };

  const memory = data.memory_summary || {};
''',
    "workspace layout hook",
)

text = replace_once(
    text,
    '''    shell.classList.toggle("glia-closed", !runtime.open);
    launcher.classList.toggle("glia-visible", !runtime.open);
    document.body.classList.toggle("glia-panel-open", runtime.open);

    const geneCount = Number(memory.gene_count || 0);
    const memoryText = geneCount > 0
      ? `Memory on · ${geneCount} gene${geneCount === 1 ? "" : "s"} in your research trail`
      : "Memory on · research context will carry across visits";
''',
    '''    shell.classList.toggle("glia-closed", !runtime.open);
    launcher.classList.toggle("glia-visible", !runtime.open);
    document.body.classList.toggle("glia-panel-open", runtime.open);
    syncWorkspaceLayout();

    const geneCount = Number(memory.gene_count || 0);
    const memoryText = geneCount > 0
      ? `Memory on · ${geneCount} gene${geneCount === 1 ? "" : "s"} remembered`
      : "Memory on · carries across visits";
''',
    "memory copy",
)

text = replace_once(
    text,
    '''${messages.length ? messages.map(renderMessage).join("") : `<div class="glia-empty"><div class="glia-empty-title">Work with the evidence, not around it.</div><div class="glia-empty-copy">Ask about the current analysis, challenge a finding, compare targets, trace a contradiction, or highlight text anywhere in the workspace and choose <b>Ask Glia</b>.</div></div>`}''',
    '''${messages.length ? messages.map(renderMessage).join("") : `<div class="glia-empty"><div class="glia-empty-title">Ask Glia</div><div class="glia-empty-copy">Ask about the current analysis or highlight text and choose <b>Ask Glia</b>.</div></div>`}''',
    "empty-state copy",
)

text = replace_once(
    text,
    '''  function onMouseUp(event) {
    if (event.target?.closest?.("#glia-shell, #glia-launcher, #glia-selection-action, input, textarea, button")) return;
    window.setTimeout(() => {
      const selection = window.getSelection();
      const text = String(selection?.toString() || "").replace(/\\s+/g, " ").trim();
''',
    '''  function selectionTouchesIgnoredArea(selection) {
    if (!selection || selection.rangeCount === 0) return false;
    const nodes = [selection.anchorNode, selection.focusNode];
    const endpointInsideIgnored = nodes.some((node) => {
      const element = node?.nodeType === Node.ELEMENT_NODE ? node : node?.parentElement;
      return Boolean(element?.closest?.('[data-glia-ignore-selection="true"]'));
    });
    if (endpointInsideIgnored) return true;
    return Array.from(document.querySelectorAll('[data-glia-ignore-selection="true"]'))
      .some((element) => selection.containsNode(element, true));
  }

  function onMouseUp(event) {
    if (event.target?.closest?.("#glia-shell, #glia-launcher, #glia-selection-action, input, textarea, button")) return;
    window.setTimeout(() => {
      const selection = window.getSelection();
      if (selectionTouchesIgnoredArea(selection)) {
        selectionAction.classList.remove("glia-visible");
        return;
      }
      const text = String(selection?.toString() || "").replace(/\\s+/g, " ").trim();
''',
    "selection exclusion handler",
)

text = replace_once(
    text,
    '''  document.addEventListener("mouseup", onMouseUp, true);
  document.addEventListener("mousedown", onMouseDown, true);
  render();

  return () => {
    document.removeEventListener("mouseup", onMouseUp, true);
    document.removeEventListener("mousedown", onMouseDown, true);
    document.body.classList.remove("glia-panel-open");
''',
    '''  document.addEventListener("mouseup", onMouseUp, true);
  document.addEventListener("mousedown", onMouseDown, true);
  window.addEventListener("resize", syncWorkspaceLayout);
  render();

  return () => {
    document.removeEventListener("mouseup", onMouseUp, true);
    document.removeEventListener("mousedown", onMouseDown, true);
    window.removeEventListener("resize", syncWorkspaceLayout);
    const target = workspaceTarget();
    if (target) {
      target.style.removeProperty("width");
      target.style.removeProperty("max-width");
      target.style.removeProperty("margin-right");
      target.style.removeProperty("transition");
    }
    document.body.classList.remove("glia-panel-open");
''',
    "layout cleanup",
)
path.write_text(text, encoding="utf-8")


# app_ui.py
path = Path("app_ui.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '<div style="font-size:2.75rem;font-weight:700;line-height:1.08;letter-spacing:-0.02em;margin:0;padding:0;">GBM Gene Analysis</div>',
    '<div data-glia-ignore-selection="true" style="font-size:2.75rem;font-weight:700;line-height:1.08;letter-spacing:-0.02em;margin:0;padding:0;">GBM Gene Analysis</div>',
    "main title",
)
text = replace_once(
    text,
    '<div style="font-size:1.04rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;padding:0;">Real-time integrated gene-level evidence synthesis for glioblastoma research.</div>',
    '<div data-glia-ignore-selection="true" style="font-size:1.04rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;padding:0;">Real-time integrated gene-level evidence synthesis for glioblastoma research.</div>',
    "main description",
)
path.write_text(text, encoding="utf-8")


# tests/test_glia_interface.py
path = Path("tests/test_glia_interface.py")
text = path.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''        "glia-panel-open",
        "Research memory",
    ):
        assert required in source, required


if __name__ == "__main__":
''',
    '''        "glia-panel-open",
        "Research memory",
        "selectionTouchesIgnoredArea",
        "syncWorkspaceLayout",
        "Memory on · carries across visits",
        "background:var(--st-text-color, #111); color:var(--st-background-color, #fff)",
    ):
        assert required in source, required


def test_main_header_is_excluded_from_ask_glia_selection():
    source = Path("app_ui.py").read_text(encoding="utf-8")
    assert source.count('data-glia-ignore-selection="true"') >= 2


if __name__ == "__main__":
''',
    "Glia source assertions",
)
text = replace_once(
    text,
    '    test_component_contains_required_integrated_interactions()\n    print("GLIA INTERFACE TESTS OK")',
    '    test_component_contains_required_integrated_interactions()\n    test_main_header_is_excluded_from_ask_glia_selection()\n    print("GLIA INTERFACE TESTS OK")',
    "Glia test runner",
)
path.write_text(text, encoding="utf-8")
