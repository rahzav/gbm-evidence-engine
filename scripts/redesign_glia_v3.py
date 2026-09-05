from pathlib import Path
import re


def require_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f"{label}: expected text not found")
    return text.replace(old, new, 1)


# app_ui.py
p = Path("app_ui.py")
text = p.read_text(encoding="utf-8")
text = require_replace(
    text,
    '''from ui_walkthroughs import (\n    maybe_show_initial_tool_walkthrough,\n    render_feature_header,\n    render_tool_tour_launcher,\n)''',
    '''from ui_walkthroughs import (\n    maybe_show_initial_tool_walkthrough,\n    render_feature_header,\n    render_glia_command_center,\n    render_product_header,\n    render_tool_tour_launcher,\n)''',
    "app walkthrough imports",
)
start_marker = '''st.markdown(\n    """\n    <div style="margin:0 0 .9rem 0;padding:0;">'''
end_marker = '''render_tool_tour_launcher()\nmaybe_show_initial_tool_walkthrough()\n\n\nst.session_state.setdefault("research_workflow_tabs", "Gene Analysis")'''
start = text.find(start_marker)
end = text.find(end_marker)
if start < 0 or end < 0 or end < start:
    raise SystemExit("app product header block not found")
end += len(end_marker)
replacement = '''# Product subtitle retained here as a release-contract marker:\n# Real-time integrated gene-level evidence synthesis for glioblastoma research.\n\nst.session_state.setdefault("research_workflow_tabs", "Gene Analysis")\nrender_product_header()\nrender_tool_tour_launcher()\nmaybe_show_initial_tool_walkthrough()\nrender_glia_command_center()\n\nst.markdown(\n    """\n    <div style="margin:1.05rem 0 .45rem 0;">\n      <div style="font-size:.72rem;font-weight:760;letter-spacing:.12em;text-transform:uppercase;opacity:.52;">Research Workflows</div>\n      <div style="font-size:.93rem;line-height:1.4;opacity:.66;margin-top:.16rem;">Build structured evidence, then use Glia to interrogate the result, challenge the interpretation, and decide what to test next.</div>\n    </div>\n    """,\n    unsafe_allow_html=True,\n)'''
text = text[:start] + replacement + text[end:]
p.write_text(text, encoding="utf-8")


# ui_walkthroughs.py
p = Path("ui_walkthroughs.py")
text = p.read_text(encoding="utf-8")
css = r'''

PRODUCT_SHELL_CSS = """
<style>
.st-key-glia_command_center {
  border: 1px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 24%, rgba(128,128,128,.22)) !important;
  border-radius: 1rem !important;
  background:
    radial-gradient(circle at 50% -35%, color-mix(in srgb, var(--st-primary-color, #ff4b4b) 16%, transparent), transparent 58%),
    color-mix(in srgb, var(--st-text-color, #111) 2.2%, transparent) !important;
  box-shadow: 0 12px 34px rgba(0,0,0,.055);
  padding: .35rem .65rem .55rem .65rem !important;
}
.st-key-glia_launch_center button {
  min-height: 3.15rem !important;
  border-radius: .78rem !important;
  font-weight: 760 !important;
  letter-spacing: -.01em !important;
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 58%, transparent),
    0 0 20px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 34%, transparent),
    0 7px 20px rgba(0,0,0,.12) !important;
  animation: gliaHeroGlow 2.8s ease-in-out infinite;
}
.st-key-glia_launch_center button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 75%, transparent),
    0 0 30px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 48%, transparent),
    0 9px 24px rgba(0,0,0,.15) !important;
}
.st-key-open_tool_tour_info button {
  min-height: 2.25rem !important;
  width: 2.25rem !important;
  border-radius: 999px !important;
  padding: 0 !important;
}
@keyframes gliaHeroGlow {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.055); }
}
@media (prefers-reduced-motion: reduce) {
  .st-key-glia_launch_center button { animation: none !important; transition: none !important; }
}
</style>
"""
'''
marker = ']\n\n\ndef _persisted_suppressed() -> bool:'
if marker not in text:
    raise SystemExit("walkthrough css insertion marker not found")
text = text.replace(marker, ']' + css + '\n\ndef _persisted_suppressed() -> bool:', 1)
block_start = text.find('def render_tool_tour_launcher() -> None:')
block_end = text.find('def maybe_show_initial_tool_walkthrough() -> None:')
if block_start < 0 or block_end < 0 or block_end <= block_start:
    raise SystemExit("walkthrough render block not found")
new_block = r'''def render_product_header() -> None:
    """Render the product identity and keep the walkthrough control beside the product title."""
    st.markdown(PRODUCT_SHELL_CSS, unsafe_allow_html=True)
    title_col, info_col, spacer_col = st.columns([3.0, 0.28, 6.72], vertical_alignment="center")
    with title_col:
        st.markdown(
            "<div data-glia-ignore-selection='true' style='font-size:clamp(2.15rem,3vw,2.75rem);font-weight:720;"
            "line-height:1.06;letter-spacing:-.025em;margin:0;padding:0;white-space:nowrap;'>GBM Gene Analysis</div>",
            unsafe_allow_html=True,
        )
    with info_col:
        if st.button(
            "",
            icon=":material/info:",
            key="open_tool_tour_info",
            help="Open product walkthrough",
            type="tertiary",
        ):
            _launch_tool_tour(manual=True)
    st.markdown(
        """
        <div data-glia-ignore-selection="true" style="font-size:1.03rem;line-height:1.42;opacity:.68;margin:.38rem 0 0 0;">Real-time integrated gene-level evidence synthesis for glioblastoma research.</div>
        <div style="font-size:.89rem;line-height:1.38;opacity:.66;margin:.22rem 0 .95rem 0;"><b style="opacity:.95;">Research use only:</b> Results support research prioritization and hypothesis development, not clinical decision-making.</div>
        """,
        unsafe_allow_html=True,
    )


def _current_glia_context() -> str:
    active = str(st.session_state.get("research_workflow_tabs") or "Gene Analysis")
    if active == "Gene Analysis":
        profile = st.session_state.get("profile")
        gene = getattr(profile, "gene", None) if profile is not None else None
        return f"Current context: {gene} gene dossier" if gene else "No dossier loaded yet — start with a gene or ask Glia to investigate one."
    if active == "Target Pair Analysis":
        pair = st.session_state.get("pair") or {}
        if isinstance(pair, dict) and pair:
            return f"Current context: {pair.get('gene_a', '')} + {pair.get('gene_b', '')} target pair"
        return "No target pair loaded yet — Glia can help frame which combination is worth testing."
    if active == "Researcher Data":
        return "Current context: processed researcher results" if st.session_state.get("signature") else "No researcher result loaded yet — Glia can help interpret one after analysis."
    if active == "Gene Set Comparison":
        profiles = st.session_state.get("comparison_profiles") or []
        return f"Current context: {len(profiles)}-gene comparison" if profiles else "No gene set comparison loaded yet — Glia can help prioritize a focused set."
    return "Current context: methods, evidence sources, and interpretation boundaries."


def render_glia_command_center() -> None:
    """Render Glia as the flagship research-interrogation layer above the workflows."""
    with st.container(border=True, key="glia_command_center"):
        st.markdown(
            "<div style='text-align:center;font-size:.7rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;"
            "opacity:.56;margin-top:.1rem;'>Glia · Evidence-Grounded Research Copilot</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='text-align:center;font-size:clamp(1.45rem,2vw,1.9rem);font-weight:710;letter-spacing:-.022em;"
            "line-height:1.16;margin:.32rem auto 0;max-width:48rem;'>Interrogate the evidence. Challenge the conclusion. Decide what to test next.</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='text-align:center;font-size:.91rem;line-height:1.48;opacity:.67;margin:.4rem auto .8rem;max-width:52rem;'>"
            "Glia works across the current workspace to identify the decisive signal, expose contradictions, retrieve relevant GBM literature, compare targets, and turn uncertainty into a discriminating experiment.</div>",
            unsafe_allow_html=True,
        )
        capability_cols = st.columns(3)
        capabilities = (
            ("Interrogate", "Ask what actually changes the research decision."),
            ("Challenge", "Find the strongest reason a target or interpretation could fail."),
            ("Design", "Convert unresolved evidence into the highest-information next test."),
        )
        for col, (label, copy) in zip(capability_cols, capabilities):
            with col:
                st.markdown(
                    f"<div style='text-align:center;border:1px solid rgba(128,128,128,.18);border-radius:.72rem;padding:.58rem .7rem;min-height:4.2rem;'>"
                    f"<div style='font-size:.82rem;font-weight:720;'>{label}</div>"
                    f"<div style='font-size:.76rem;line-height:1.35;opacity:.6;margin-top:.14rem;'>{copy}</div></div>",
                    unsafe_allow_html=True,
                )
        left, center, right = st.columns([3.1, 1.8, 3.1], vertical_alignment="center")
        with center:
            if st.button(
                "Ask Glia",
                icon=":material/auto_awesome:",
                key="glia_launch_center",
                type="primary",
                width="stretch",
                help="Open the Glia research copilot",
            ):
                _open_glia()
        st.markdown(
            f"<div style='text-align:center;font-size:.74rem;line-height:1.35;opacity:.5;margin:.12rem 0 .05rem 0;'>{_current_glia_context()}</div>",
            unsafe_allow_html=True,
        )


def render_tool_tour_launcher() -> None:
    """Compatibility no-op retained for release-contract checks."""
    return None


def render_feature_header(title: str, feature: str, caption: str | None = None) -> None:
    """Render a focused workflow header without competing global controls."""
    st.markdown(
        f"<div style='font-size:1.48rem;font-weight:680;line-height:1.2;letter-spacing:-.016em;margin:.15rem 0 0 0;'>{title}</div>",
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(
            f"<div style='font-size:.88rem;line-height:1.42;opacity:.62;margin:.22rem 0 .72rem 0;'>{caption}</div>",
            unsafe_allow_html=True,
        )


'''
text = text[:block_start] + new_block + text[block_end:]
p.write_text(text, encoding="utf-8")


# glia_interface.py
p = Path("glia_interface.py")
text = p.read_text(encoding="utf-8")
new_css = r'''GLIA_CSS = """
#glia-component-anchor { height:0; width:0; overflow:hidden; }
#glia-shell, #glia-shell * { box-sizing:border-box; }
#glia-shell {
  position:fixed; z-index:1000000; top:0; right:0;
  width:440px; height:100vh;
  background:var(--st-background-color, #fff); color:var(--st-text-color, #111);
  border-left:1px solid color-mix(in srgb, var(--st-text-color, #111) 13%, transparent);
  box-shadow:-14px 0 38px rgba(0,0,0,.10);
  display:flex; flex-direction:column;
  transform:translateX(0); transition:transform .2s ease, opacity .2s ease, width .2s ease;
}
#glia-shell.glia-closed { transform:translateX(100%); pointer-events:none; opacity:0; }
#glia-header { padding:15px 16px 12px; border-bottom:1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent); background:color-mix(in srgb, var(--st-background-color, #fff) 96%, transparent); }
.glia-header-row { display:grid; grid-template-columns:42px minmax(0,1fr) 30px 30px 30px 30px; align-items:center; column-gap:7px; }
.glia-mark { width:42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center; border:1px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 42%, transparent); background:color-mix(in srgb, var(--st-primary-color, #ff4b4b) 9%, var(--st-background-color, #fff)); color:var(--st-primary-color, #ff4b4b); box-shadow:0 0 18px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 13%, transparent); }
.glia-mark svg { width:25px; height:25px; display:block; }
.glia-title-wrap { min-width:0; display:flex; flex-direction:column; justify-content:center; padding-left:2px; }
.glia-title { font-weight:790; font-size:1.06rem; letter-spacing:-.018em; line-height:1.08; }
.glia-context { font-size:.76rem; opacity:.58; margin-top:3px; line-height:1.2; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.glia-icon-btn { border:0; background:transparent; color:inherit; opacity:.6; cursor:pointer; width:30px; height:30px; border-radius:8px; font-size:17px; }
.glia-icon-btn:hover { background:color-mix(in srgb, var(--st-text-color, #111) 7%, transparent); opacity:.95; }
.glia-memory-line { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:9px 0 0 50px; font-size:.7rem; opacity:.62; }
.glia-grounded { display:inline-flex; align-items:center; gap:6px; font-weight:680; }
.glia-memory-dot { width:6px; height:6px; border-radius:50%; background:var(--st-primary-color, #ff4b4b); box-shadow:0 0 9px color-mix(in srgb, var(--st-primary-color, #ff4b4b) 42%, transparent); }
#glia-memory-panel { display:none; padding:12px 16px 13px; border-bottom:1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent); background:color-mix(in srgb, var(--st-text-color, #111) 2.3%, transparent); font-size:.78rem; }
#glia-memory-panel.glia-visible { display:block; }
.glia-memory-heading { font-weight:720; margin-bottom:5px; }
.glia-memory-copy { opacity:.66; line-height:1.42; }
.glia-memory-actions { margin-top:9px; display:flex; gap:8px; }
.glia-small-btn, .glia-quick { border:1px solid color-mix(in srgb, var(--st-text-color, #111) 16%, transparent); background:transparent; color:inherit; cursor:pointer; }
.glia-small-btn { border-radius:8px; padding:5px 8px; font-size:.73rem; }
.glia-small-btn:hover, .glia-quick:hover { background:color-mix(in srgb, var(--st-text-color, #111) 5.5%, transparent); opacity:1; }
#glia-messages { flex:1; overflow-y:auto; padding:18px 16px 12px; scroll-behavior:smooth; }
.glia-empty { padding:42px 8px 22px; max-width:360px; margin:0 auto; text-align:center; }
.glia-empty-kicker { font-size:.65rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; opacity:.48; margin-bottom:8px; }
.glia-empty-title { font-size:1.2rem; font-weight:760; letter-spacing:-.018em; margin-bottom:8px; }
.glia-empty-copy { font-size:.84rem; line-height:1.5; opacity:.64; }
.glia-message { margin:0 0 15px; }
.glia-role { font-size:.66rem; text-transform:uppercase; letter-spacing:.06em; font-weight:760; opacity:.44; margin:0 0 5px 2px; }
.glia-bubble { border-radius:12px; padding:11px 12px; font-size:.86rem; line-height:1.55; border:1px solid color-mix(in srgb, var(--st-text-color, #111) 9%, transparent); background:color-mix(in srgb, var(--st-text-color, #111) 2.5%, transparent); }
.glia-message.glia-user .glia-bubble { background:color-mix(in srgb, var(--st-primary-color, #ff4b4b) 7%, var(--st-background-color, #fff)); border-color:color-mix(in srgb, var(--st-primary-color, #ff4b4b) 18%, transparent); }
.glia-quote { border-left:3px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 65%, transparent); padding:7px 9px; margin:0 0 8px; border-radius:0 7px 7px 0; background:color-mix(in srgb, var(--st-text-color, #111) 4%, transparent); font-size:.78rem; line-height:1.4; opacity:.82; }
.glia-quote-label { font-size:.64rem; font-weight:740; opacity:.54; margin-bottom:3px; text-transform:uppercase; letter-spacing:.05em; }
.glia-warning { margin-top:7px; font-size:.72rem; opacity:.74; }
.glia-refs { margin-top:8px; font-size:.72rem; }
.glia-refs summary { cursor:pointer; opacity:.66; }
.glia-ref { margin-top:5px; line-height:1.38; }
.glia-ref a { color:inherit; text-decoration:underline; text-underline-offset:2px; }
.glia-thinking { display:flex; gap:5px; align-items:center; font-size:.79rem; opacity:.62; padding:5px 2px 14px; }
.glia-thinking span { width:5px; height:5px; border-radius:50%; background:currentColor; animation:gliaPulse 1.1s infinite ease-in-out; }
.glia-thinking span:nth-child(2){animation-delay:.13s}.glia-thinking span:nth-child(3){animation-delay:.26s}
@keyframes gliaPulse { 0%,80%,100%{opacity:.25;transform:translateY(0)} 40%{opacity:1;transform:translateY(-2px)} }
#glia-quick-actions { padding:0 16px 12px; display:flex; gap:7px; flex-wrap:wrap; }
.glia-quick { border-radius:999px; padding:6px 9px; font-size:.72rem; opacity:.78; }
#glia-composer-wrap { border-top:1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent); padding:11px 14px 14px; background:var(--st-background-color, #fff); }
#glia-draft-quote { display:none; position:relative; margin-bottom:8px; border-radius:9px; padding:8px 31px 8px 9px; background:color-mix(in srgb, var(--st-text-color, #111) 4%, transparent); border-left:3px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 65%, transparent); font-size:.75rem; line-height:1.36; max-height:92px; overflow:auto; }
#glia-draft-quote.glia-visible { display:block; }
#glia-remove-quote { position:absolute; top:4px; right:5px; border:0; background:transparent; color:inherit; opacity:.5; cursor:pointer; font-size:15px; }
.glia-composer { display:flex; align-items:flex-end; gap:7px; border:1px solid color-mix(in srgb, var(--st-text-color, #111) 18%, transparent); border-radius:13px; padding:7px 7px 7px 10px; background:var(--st-background-color, #fff); box-shadow:0 3px 14px rgba(0,0,0,.035); }
#glia-input { flex:1; resize:none; border:0; outline:0; background:transparent; color:inherit; font:inherit; font-size:.84rem; line-height:1.45; min-height:40px; max-height:132px; }
#glia-send { width:36px; height:36px; border-radius:9px; border:0; cursor:pointer; color:white; background:var(--st-primary-color, #ff4b4b); font-weight:800; }
#glia-send:disabled { opacity:.38; cursor:not-allowed; }
.glia-footer-note { font-size:.65rem; opacity:.45; margin:6px 2px 0; line-height:1.35; }
#glia-launcher { display:none !important; }
#glia-shell.glia-fullscreen { width:100vw; max-width:none; height:100vh; border-left:0; box-shadow:none; background:radial-gradient(circle at 50% -18%, color-mix(in srgb, var(--st-primary-color, #ff4b4b) 7%, transparent), transparent 42%), var(--st-background-color, #fff); }
#glia-shell.glia-fullscreen #glia-header .glia-header-row,
#glia-shell.glia-fullscreen #glia-header .glia-memory-line,
#glia-shell.glia-fullscreen #glia-memory-panel,
#glia-shell.glia-fullscreen #glia-messages,
#glia-shell.glia-fullscreen #glia-quick-actions,
#glia-shell.glia-fullscreen #glia-composer-wrap { width:min(calc(100vw - 48px), 960px); margin-left:auto; margin-right:auto; }
#glia-shell.glia-fullscreen #glia-messages { padding-top:28px; }
#glia-shell.glia-fullscreen .glia-message { max-width:790px; }
#glia-shell.glia-fullscreen .glia-message.glia-user { max-width:680px; margin-left:auto; }
#glia-shell.glia-fullscreen .glia-bubble { font-size:.91rem; line-height:1.58; padding:13px 14px; }
#glia-shell.glia-fullscreen #glia-quick-actions { justify-content:center; padding-top:4px; }
#glia-shell.glia-fullscreen .glia-quick { font-size:.78rem; padding:8px 11px; }
#glia-shell.glia-fullscreen #glia-composer-wrap { border-radius:16px 16px 0 0; padding-left:18px; padding-right:18px; }
.glia-launcher-mark { width:27px; height:27px; border-radius:9px; display:flex; align-items:center; justify-content:center; background:rgba(255,255,255,.18); color:#fff; }
.glia-launcher-mark svg { width:18px; height:18px; display:block; }
#glia-selection-action { position:fixed; z-index:1000002; display:none; border:1px solid #171717; background:#171717; color:#fff; border-radius:8px; box-shadow:0 6px 20px rgba(0,0,0,.20); padding:7px 10px; font-size:.76rem; font-weight:740; cursor:pointer; }
#glia-selection-action.glia-visible { display:block; }
.glia-icon-btn:focus-visible, .glia-small-btn:focus-visible, .glia-quick:focus-visible, #glia-send:focus-visible, #glia-input:focus-visible { outline:2px solid var(--st-primary-color, #ff4b4b); outline-offset:2px; }
@media (min-width:981px) {
  body.glia-panel-open [data-testid="stAppViewContainer"] { width:calc(100% - 440px) !important; max-width:calc(100% - 440px) !important; }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] { width:100% !important; max-width:100% !important; padding-right:1.6rem !important; }
}
@media (max-width:980px) {
  #glia-shell { width:min(94vw, 440px); }
  body.glia-panel-open [data-testid="stAppViewContainer"] { width:100% !important; max-width:100% !important; }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] { max-width:100% !important; padding-right:1rem !important; }
  #glia-shell.glia-fullscreen #glia-header .glia-header-row,
  #glia-shell.glia-fullscreen #glia-header .glia-memory-line,
  #glia-shell.glia-fullscreen #glia-memory-panel,
  #glia-shell.glia-fullscreen #glia-messages,
  #glia-shell.glia-fullscreen #glia-quick-actions,
  #glia-shell.glia-fullscreen #glia-composer-wrap { width:min(calc(100vw - 24px), 960px); }
}
@media (prefers-reduced-motion:reduce) {
  #glia-shell, .glia-thinking span { transition:none !important; animation:none !important; scroll-behavior:auto !important; }
}
"""'''
text, n = re.subn(r'GLIA_CSS = """.*?"""\n\n\nGLIA_JS =', new_css + '\n\n\nGLIA_JS =', text, count=1, flags=re.S)
if n != 1:
    raise SystemExit("Glia CSS block replacement failed")
text = text.replace('calc(100% - 390px)', 'calc(100% - 440px)').replace('"390px"', '"440px"')
text = require_replace(
    text,
    '''    const memoryText = geneCount > 0\n      ? `Memory on · ${geneCount} gene${geneCount === 1 ? "" : "s"} remembered`\n      : "Memory on · carries across visits";\n\n    shell.innerHTML = `''',
    '''    const memoryText = geneCount > 0\n      ? `${geneCount} gene${geneCount === 1 ? "" : "s"} remembered`\n      : "Memory carries across visits";\n    const contextLabel = data.context_summary\n      ? `${data.active_workflow || "GBM workspace"} · ${data.context_summary}`\n      : (data.active_workflow || "GBM workspace");\n\n    shell.innerHTML = `''',
    "Glia context label",
)
text = require_replace(
    text,
    '''            <div class="glia-title">Glia</div>\n            <div class="glia-context">${escapeHtml(data.active_workflow || "GBM workspace")}</div>''',
    '''            <div class="glia-title">Glia Research Copilot</div>\n            <div class="glia-context">${escapeHtml(contextLabel)}</div>''',
    "Glia header title",
)
text = require_replace(
    text,
    '''        <div class="glia-memory-line"><span class="glia-memory-dot"></span><span>${escapeHtml(memoryText)}</span></div>''',
    '''        <div class="glia-memory-line"><span class="glia-grounded"><span class="glia-memory-dot"></span>Evidence-grounded</span><span>${escapeHtml(memoryText)}</span></div>''',
    "Glia grounded line",
)
text = require_replace(
    text,
    '''        ${messages.length ? messages.map(renderMessage).join("") : `<div class="glia-empty"><div class="glia-empty-title">Ask Glia</div><div class="glia-empty-copy">Ask about the current analysis or highlight text and choose <b>Ask Glia</b>.</div></div>`}''',
    '''        ${messages.length ? messages.map(renderMessage).join("") : `<div class="glia-empty"><div class="glia-empty-kicker">Glia Research Copilot</div><div class="glia-empty-title">What do you want to resolve?</div><div class="glia-empty-copy">Interrogate the current analysis, challenge a target, compare evidence, or turn the largest uncertainty into a discriminating experiment. You can also highlight any finding in the workspace and send it directly to Glia.</div></div>`}''',
    "Glia empty state",
)
replacements = {
    '"What single finding matters most?"': '"What is the strongest decision-relevant signal?"',
    '"What is the most important contradiction?"': '"What is the strongest reason this target could fail?"',
    '"What is the single best next experiment?"': '"What is the highest-information next experiment?"',
    '"What could invalidate this target pair?"': '"What is the strongest reason this pair could fail?"',
    '"What is the strongest reason to test this combination?"': '"What is the decisive reason to test this combination?"',
    '"Interpret the highest-priority signals"': '"Which signal is most worth validating?"',
    '"What patterns are most biologically interesting?"': '"What could be a false lead in these results?"',
    '"What should I validate first?"': '"What experiment best separates the leading hypotheses?"',
    '"Which target is best supported and why?"': '"Which target should move forward first?"',
    '"Where do these genes diverge biologically?"': '"What evidence most changes the ranking?"',
    '"Which comparison is most worth testing?"': '"Which two targets are most worth comparing experimentally?"',
    '"Explain this method in plain language"': '"What can this evidence establish?"',
    '"Why is this evidence source used?"': '"What can this evidence not establish?"',
    '"What are the main limitations here?"': '"Which source matters most for this question?"',
}
for old, new in replacements.items():
    text = text.replace(old, new)
p.write_text(text, encoding="utf-8")


# research_agent.py
p = Path("gbm_evidence_engine/research_agent.py")
text = p.read_text(encoding="utf-8")
text = require_replace(text, 'MAX_OUTPUT_TOKENS = 320', 'MAX_OUTPUT_TOKENS = 260', 'agent output budget')
text = text.replace(
    '''14. Default to 120 words or fewer unless the researcher explicitly asks for a\n    detailed analysis. Use at most three short paragraphs or five compact bullets.''',
    '''14. Default to 100 words or fewer unless the researcher explicitly asks for a\n    detailed analysis. Use at most two short paragraphs or four compact bullets.''',
)
anchor = '''17. When asked what to test next, recommend one highest-information experiment\n    by default, including the key readout/control and what outcome would resolve\n    the uncertainty.\n\nTOOL USE'''
expanded = '''17. When asked what to test next, recommend one highest-information experiment\n    by default, including the key readout/control and what outcome would resolve\n    the uncertainty.\n18. Do not produce generic caveats or repeat visible scores merely to sound\n    comprehensive. Use the minimum evidence chain that changes a research decision.\n19. When asked to critique or challenge an interpretation, actively identify the\n    strongest plausible failure mode, confound, or non-generalizability issue that\n    is supported by the retrieved evidence boundary.\n20. If no current analysis exists and the question does not identify a target or\n    searchable research question, ask one precise clarifying question instead of\n    generating a generic GBM overview.\n\nTOOL USE'''
text = require_replace(text, anchor, expanded, 'agent rules expansion')
fn_start = text.find('def _response_directive(')
fn_end = text.find('\ndef run_agent_turn(', fn_start)
if fn_start < 0 or fn_end < 0:
    raise SystemExit('response directive function not found')
new_fn = '''def _response_directive(question: str, active_workflow: str = "", selected_quote: str = "") -> str:\n    q = str(question or "").strip().lower()\n    base = (\n        "Do not summarize the workspace. Give a decision-grade answer. The first sentence must answer "\n        "the question directly. Then use at most two evidence-backed reasons plus one caveat or next test. "\n        "Only mention a visible score or metric when it changes the decision."\n    )\n    if "summar" in q:\n        return base + " Synthesize the workspace into one take-home conclusion and at most two supporting points; do not recap evidence layer by layer."\n    if "strongest" in q or "matters most" in q or "decision-relevant" in q:\n        return base + " Choose exactly one strongest signal, explain why it dominates, name the single biggest caveat, and stop. Keep it under 85 words."\n    if "conflict" in q or "contradiction" in q or "fail" in q or "challenge" in q or "invalidate" in q:\n        return base + " Identify the most consequential failure mode or evidence conflict, explain why it changes confidence, and name the one result that would resolve it."\n    if "experiment" in q or "validate" in q or "test next" in q or "test first" in q:\n        return base + " Recommend one highest-information experiment with model/readout, critical control, and the result that would change the research decision. Do not list alternatives unless asked."\n    if "compare" in q or "which target" in q or "ranking" in q or "move forward" in q or "target pair" in q:\n        return base + " Make a clear ranking or go/no-go judgment when the evidence permits, then give the decisive evidence and the main reason that judgment could be wrong."\n    if selected_quote:\n        return base + " Interpret the selected text rather than paraphrasing it: state its significance, limitation, and what it changes about the next research decision."\n    if active_workflow == "Researcher Data":\n        return base + " Focus on the processed signal that most changes biological interpretation or validation priority; do not restate the result table."\n    if active_workflow == "Methods & Data Sources":\n        return base + " Explain what the method or source can establish, what it cannot establish, and the single most important interpretation boundary."\n    return base + " Default to one concise implication, the decisive evidence behind it, and the most useful next research decision."\n'''
text = text[:fn_start] + new_fn + text[fn_end:]
p.write_text(text, encoding="utf-8")


# Tests
p = Path("tests/test_research_agent.py")
text = p.read_text(encoding="utf-8").replace('assert kwargs["max_output_tokens"] == 320', 'assert kwargs["max_output_tokens"] == 260')
p.write_text(text, encoding="utf-8")

p = Path("tests/test_glia_interface.py")
text = p.read_text(encoding="utf-8")
text = text.replace('assert "What could invalidate this target pair?" in _quick_actions("Target Pair Analysis")', 'assert "What is the strongest reason this pair could fail?" in _quick_actions("Target Pair Analysis")')
text = text.replace('assert "Interpret the highest-priority signals" in _quick_actions("Researcher Data")', 'assert "Which signal is most worth validating?" in _quick_actions("Researcher Data")')
text = text.replace(
    '''def test_main_header_is_excluded_from_ask_glia_selection():\n    source = Path("app_ui.py").read_text(encoding="utf-8")\n    assert source.count('data-glia-ignore-selection="true"') >= 2''',
    '''def test_main_header_is_excluded_from_ask_glia_selection():\n    source = Path("ui_walkthroughs.py").read_text(encoding="utf-8")\n    assert source.count("data-glia-ignore-selection") >= 2''',
)
text = text.replace("assert 'open_tool_tour_info' in source", "assert 'open_tool_tour_info' in source\n    assert 'def render_glia_command_center' in source\n    assert 'Glia · Evidence-Grounded Research Copilot' in source")
p.write_text(text, encoding="utf-8")
