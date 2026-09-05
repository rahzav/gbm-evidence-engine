"""Integrated Glia copilot UI, selection bridge, and browser-persistent research memory."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

import streamlit as st

from gbm_evidence_engine.research_agent import ResearchAgentError, configured_model, run_agent_turn


GLIA_MEMORY_VERSION = 1
GLIA_STORAGE_KEY = "gbm_glia_workspace_v1"
MAX_PERSISTED_MESSAGES = 40
MAX_MEMORY_GENES = 40
MAX_RECENT_QUESTIONS = 12
MAX_RECENT_QUOTES = 8


GLIA_HTML = """
<div id="glia-component-anchor" aria-hidden="true"></div>
"""


GLIA_CSS = """
#glia-component-anchor { height: 0; width: 0; overflow: hidden; }

#glia-shell, #glia-shell * { box-sizing: border-box; }
#glia-shell {
  position: fixed;
  z-index: 1000000;
  top: 0;
  right: 0;
  width: 390px;
  height: 100vh;
  background: var(--st-background-color, #fff);
  color: var(--st-text-color, #111);
  border-left: 1px solid color-mix(in srgb, var(--st-text-color, #111) 14%, transparent);
  box-shadow: -12px 0 32px rgba(0,0,0,.08);
  display: flex;
  flex-direction: column;
  transform: translateX(0);
  transition: transform .18s ease, opacity .18s ease;
}
#glia-shell.glia-closed { transform: translateX(100%); pointer-events: none; opacity: 0; }

#glia-header {
  padding: 14px 14px 11px;
  border-bottom: 1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent);
  background: var(--st-background-color, #fff);
}
.glia-header-row {
  display:grid;
  grid-template-columns:40px minmax(0,1fr) 30px 30px 30px;
  align-items:center;
  column-gap:7px;
}
.glia-mark {
  width:40px; height:40px; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  border:1px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 48%, transparent);
  background:color-mix(in srgb, var(--st-primary-color, #ff4b4b) 9%, var(--st-background-color, #fff));
  color:var(--st-primary-color, #ff4b4b);
}
.glia-mark svg { width:25px; height:25px; display:block; }
.glia-title-wrap {
  min-width:0; display:flex; flex-direction:column; justify-content:center;
  padding-left:2px;
}
.glia-title { font-weight:780; font-size:1.08rem; letter-spacing:-.015em; line-height:1.08; }
.glia-context { font-size:.78rem; opacity:.60; margin-top:3px; line-height:1.15; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.glia-icon-btn {
  border:0; background:transparent; color:inherit; opacity:.62; cursor:pointer;
  width:30px; height:30px; border-radius:8px; font-size:17px;
}
.glia-icon-btn:hover { background: color-mix(in srgb, var(--st-text-color, #111) 7%, transparent); opacity:.9; }
.glia-memory-line { display:flex; align-items:center; gap:7px; margin:8px 0 0 49px; font-size:.73rem; opacity:.66; }
.glia-memory-dot { width:6px; height:6px; border-radius:50%; background: var(--st-primary-color, #ff4b4b); }

#glia-memory-panel {
  display:none; padding:11px 14px 12px 16px;
  border-bottom:1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent);
  background: color-mix(in srgb, var(--st-text-color, #111) 2.5%, transparent);
  font-size:.78rem;
}
#glia-memory-panel.glia-visible { display:block; }
.glia-memory-heading { font-weight:700; margin-bottom:5px; }
.glia-memory-copy { opacity:.68; line-height:1.4; }
.glia-memory-actions { margin-top:9px; display:flex; gap:8px; }
.glia-small-btn {
  border:1px solid color-mix(in srgb, var(--st-text-color, #111) 18%, transparent);
  background:transparent; color:inherit; border-radius:8px; padding:5px 8px;
  font-size:.73rem; cursor:pointer;
}
.glia-small-btn:hover { background:color-mix(in srgb, var(--st-text-color, #111) 6%, transparent); }

#glia-messages { flex:1; overflow-y:auto; padding:14px 14px 10px 14px; }
.glia-empty { padding:24px 8px 8px; }
.glia-empty-title { font-size:1rem; font-weight:720; margin-bottom:7px; }
.glia-empty-copy { font-size:.82rem; line-height:1.48; opacity:.66; }
.glia-message { margin: 0 0 14px; }
.glia-role { font-size:.69rem; text-transform:uppercase; letter-spacing:.055em; font-weight:720; opacity:.48; margin:0 0 5px 2px; }
.glia-bubble {
  border-radius:12px; padding:10px 11px; font-size:.84rem; line-height:1.5;
  border:1px solid color-mix(in srgb, var(--st-text-color, #111) 9%, transparent);
  background: color-mix(in srgb, var(--st-text-color, #111) 2.5%, transparent);
}
.glia-message.glia-user .glia-bubble {
  background: color-mix(in srgb, var(--st-primary-color, #ff4b4b) 7%, var(--st-background-color, #fff));
  border-color: color-mix(in srgb, var(--st-primary-color, #ff4b4b) 18%, transparent);
}
.glia-quote {
  border-left:3px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 65%, transparent);
  padding:7px 9px; margin:0 0 8px; border-radius:0 7px 7px 0;
  background:color-mix(in srgb, var(--st-text-color, #111) 4%, transparent);
  font-size:.78rem; line-height:1.4; opacity:.82;
}
.glia-quote-label { font-size:.66rem; font-weight:700; opacity:.58; margin-bottom:3px; text-transform:uppercase; letter-spacing:.04em; }
.glia-warning { margin-top:7px; font-size:.72rem; opacity:.74; }
.glia-refs { margin-top:8px; font-size:.72rem; }
.glia-refs summary { cursor:pointer; opacity:.66; }
.glia-ref { margin-top:5px; line-height:1.35; }
.glia-ref a { color:inherit; text-decoration:underline; text-underline-offset:2px; }
.glia-thinking { display:flex; gap:5px; align-items:center; font-size:.79rem; opacity:.62; padding:5px 2px 14px; }
.glia-thinking span { width:5px; height:5px; border-radius:50%; background:currentColor; animation:gliaPulse 1.1s infinite ease-in-out; }
.glia-thinking span:nth-child(2){animation-delay:.13s}.glia-thinking span:nth-child(3){animation-delay:.26s}
@keyframes gliaPulse { 0%,80%,100%{opacity:.25;transform:translateY(0)} 40%{opacity:1;transform:translateY(-2px)} }

#glia-quick-actions { padding:0 14px 9px; display:flex; gap:6px; flex-wrap:wrap; }
.glia-quick {
  border:1px solid color-mix(in srgb, var(--st-text-color, #111) 14%, transparent);
  background:transparent; color:inherit; border-radius:999px; padding:5px 8px;
  font-size:.71rem; cursor:pointer; opacity:.78;
}
.glia-quick:hover { opacity:1; background:color-mix(in srgb, var(--st-text-color, #111) 5%, transparent); }

#glia-composer-wrap {
  border-top:1px solid color-mix(in srgb, var(--st-text-color, #111) 10%, transparent);
  padding:10px 12px 12px; background:var(--st-background-color, #fff);
}
#glia-draft-quote {
  display:none; position:relative; margin-bottom:8px; border-radius:9px; padding:8px 31px 8px 9px;
  background:color-mix(in srgb, var(--st-text-color, #111) 4%, transparent);
  border-left:3px solid color-mix(in srgb, var(--st-primary-color, #ff4b4b) 65%, transparent);
  font-size:.75rem; line-height:1.36; max-height:92px; overflow:auto;
}
#glia-draft-quote.glia-visible { display:block; }
#glia-remove-quote { position:absolute; top:4px; right:5px; border:0; background:transparent; color:inherit; opacity:.5; cursor:pointer; font-size:15px; }
.glia-composer {
  display:flex; align-items:flex-end; gap:7px; border:1px solid color-mix(in srgb, var(--st-text-color, #111) 17%, transparent);
  border-radius:12px; padding:7px 7px 7px 10px; background:var(--st-background-color, #fff);
}
#glia-input { flex:1; resize:none; border:0; outline:0; background:transparent; color:inherit; font:inherit; font-size:.83rem; line-height:1.4; min-height:38px; max-height:120px; }
#glia-send { width:34px; height:34px; border-radius:9px; border:0; cursor:pointer; color:white; background:var(--st-primary-color, #ff4b4b); font-weight:800; }
#glia-send:disabled { opacity:.38; cursor:not-allowed; }
.glia-footer-note { font-size:.66rem; opacity:.48; margin:6px 2px 0; line-height:1.35; }

#glia-launcher {
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
#glia-launcher.glia-visible { display:flex; }
.glia-launcher-mark {
  width:27px; height:27px; border-radius:9px; display:flex; align-items:center; justify-content:center;
  background:rgba(255,255,255,.18); color:#fff;
}
.glia-launcher-mark svg { width:18px; height:18px; display:block; }

#glia-selection-action {
  position:fixed; z-index:1000002; display:none;
  border:1px solid #171717;
  background:#171717; color:#fff; border-radius:8px;
  box-shadow:0 6px 20px rgba(0,0,0,.20); padding:7px 10px; font-size:.76rem;
  font-weight:740; cursor:pointer;
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
  #glia-launcher {
    top:auto; right:16px; bottom:76px; transform:none;
    border-radius:999px; padding:10px 15px 10px 10px;
    box-shadow:0 10px 28px rgba(0,0,0,.20);
  }
  #glia-launcher:hover { padding-right:15px; }
  #glia-shell { width:min(92vw, 390px); }
  body.glia-panel-open [data-testid="stAppViewContainer"] { width:100% !important; max-width:100% !important; }
  body.glia-panel-open [data-testid="stAppViewBlockContainer"] { max-width:100% !important; padding-right:1rem !important; }
}
"""


GLIA_JS = r"""
export default function(component) {
  const { data, setTriggerValue, setStateValue } = component;
  const STORAGE_KEY = data.storage_key || "gbm_glia_workspace_v1";
  const UI_KEY = STORAGE_KEY + ":ui";
  const runtime = window.__gbmGliaRuntime || {
    open: true,
    memoryOpen: false,
    draftQuote: null,
    hydrationSent: false,
    lastPayloadRevision: null,
    lastForceOpenNonce: null,
  };
  window.__gbmGliaRuntime = runtime;

  const safeParse = (raw, fallback) => {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  };
  const uiStored = safeParse(localStorage.getItem(UI_KEY), {});
  if (typeof uiStored.open === "boolean" && runtime.uiLoaded !== true) runtime.open = uiStored.open;
  runtime.uiLoaded = true;

  const forceOpenNonce = Number(data.force_open_nonce || 0);
  if (forceOpenNonce && forceOpenNonce !== runtime.lastForceOpenNonce) {
    runtime.open = true;
    runtime.lastForceOpenNonce = forceOpenNonce;
    try { localStorage.setItem(UI_KEY, JSON.stringify({open: true})); } catch (_) {}
  }

  if (!data.hydrated && !runtime.hydrationSent) {
    const stored = safeParse(localStorage.getItem(STORAGE_KEY), {messages: [], memory: {}});
    runtime.hydrationSent = true;
    setStateValue("persisted", stored);
  }

  if (data.hydrated && data.persist_payload && data.persist_revision !== runtime.lastPayloadRevision) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data.persist_payload));
      runtime.lastPayloadRevision = data.persist_revision;
    } catch (_) {}
  }

  const oldShell = document.getElementById("glia-shell");
  const oldLauncher = document.getElementById("glia-launcher");
  const oldSelection = document.getElementById("glia-selection-action");
  if (oldShell) oldShell.remove();
  if (oldLauncher) oldLauncher.remove();
  if (oldSelection) oldSelection.remove();

  const shell = document.createElement("aside");
  shell.id = "glia-shell";
  shell.setAttribute("aria-label", "Glia research copilot");
  document.body.appendChild(shell);

  const gliaGlyph = `<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">
    <g fill="none" stroke="currentColor" stroke-width="2.15" stroke-linecap="round" stroke-linejoin="round">
      <path d="M16 10.2 10.4 6.4M16 10.2l5.8-4M16 20.9l-6 4.2M16 20.9l6.3 3.7M11.2 15.5H5.8M20.8 15.5h5.4"/>
      <circle cx="16" cy="15.5" r="5.4" fill="currentColor" fill-opacity=".16"/>
      <circle cx="10.1" cy="6.2" r="1.8" fill="currentColor"/>
      <circle cx="22.1" cy="6" r="1.8" fill="currentColor"/>
      <circle cx="9.7" cy="25.3" r="1.8" fill="currentColor"/>
      <circle cx="22.6" cy="24.8" r="1.8" fill="currentColor"/>
      <circle cx="5.3" cy="15.5" r="1.7" fill="currentColor"/>
      <circle cx="26.7" cy="15.5" r="1.7" fill="currentColor"/>
    </g>
  </svg>`;

  const launcher = document.createElement("button");
  launcher.id = "glia-launcher";
  launcher.type = "button";
  launcher.innerHTML = `<span class="glia-launcher-mark">${gliaGlyph}</span><span>Ask Glia</span>`;
  document.body.appendChild(launcher);

  const selectionAction = document.createElement("button");
  selectionAction.id = "glia-selection-action";
  selectionAction.type = "button";
  selectionAction.textContent = "Ask Glia";
  document.body.appendChild(selectionAction);

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

  const formatText = (value) => {
    let html = escapeHtml(value || "");
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\n/g, "<br>");
    return html;
  };

  const isSafeUrl = (value) => /^https?:\/\//i.test(String(value || ""));
  const workspaceTarget = () =>
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
  const messages = Array.isArray(data.messages) ? data.messages : [];

  function renderReferenceList(refs) {
    if (!Array.isArray(refs) || !refs.length) return "";
    const rows = refs.slice(0, 16).map((ref) => {
      const label = escapeHtml(ref.label || ref.source || ref.token || "Evidence source");
      const source = escapeHtml(ref.source || "");
      if (isSafeUrl(ref.url)) {
        return `<div class="glia-ref"><a href="${escapeHtml(ref.url)}" target="_blank" rel="noopener noreferrer">${label}</a>${source ? ` — ${source}` : ""}</div>`;
      }
      return `<div class="glia-ref">${label}${source ? ` — ${source}` : ""}</div>`;
    }).join("");
    return `<details class="glia-refs"><summary>Evidence references (${refs.length})</summary>${rows}</details>`;
  }

  function renderMessage(message) {
    const role = message.role === "user" ? "user" : "assistant";
    const quote = message.quote ? `<div class="glia-quote"><div class="glia-quote-label">${escapeHtml(message.section || "Selected context")}</div>${formatText(message.quote)}</div>` : "";
    const warning = message.grounding_ok === false ? '<div class="glia-warning">Verify unsupported quantitative phrasing against the cited evidence before use.</div>' : "";
    const refs = role === "assistant" ? renderReferenceList(message.references || []) : "";
    return `<div class="glia-message glia-${role}"><div class="glia-role">${role === "user" ? "You" : "Glia"}</div><div class="glia-bubble">${quote}${formatText(message.content || "")}${warning}${refs}</div></div>`;
  }

  function render() {
    shell.classList.toggle("glia-closed", !runtime.open);
    launcher.classList.toggle("glia-visible", !runtime.open);
    document.body.classList.toggle("glia-panel-open", runtime.open);
    syncWorkspaceLayout();

    const geneCount = Number(memory.gene_count || 0);
    const memoryText = geneCount > 0
      ? `Memory on · ${geneCount} gene${geneCount === 1 ? "" : "s"} remembered`
      : "Memory on · carries across visits";

    shell.innerHTML = `
      <div id="glia-header">
        <div class="glia-header-row">
          <div class="glia-mark">${gliaGlyph}</div>
          <div class="glia-title-wrap">
            <div class="glia-title">Glia</div>
            <div class="glia-context">${escapeHtml(data.active_workflow || "GBM workspace")}</div>
          </div>
          <button class="glia-icon-btn" id="glia-new-thread" title="New thread" aria-label="New thread">＋</button>
          <button class="glia-icon-btn" id="glia-memory-toggle" title="Research memory" aria-label="Research memory">◉</button>
          <button class="glia-icon-btn" id="glia-close" title="Close Glia" aria-label="Close Glia">×</button>
        </div>
        <div class="glia-memory-line"><span class="glia-memory-dot"></span><span>${escapeHtml(memoryText)}</span></div>
      </div>
      <div id="glia-memory-panel" class="${runtime.memoryOpen ? "glia-visible" : ""}">
        <div class="glia-memory-heading">Research memory</div>
        <div class="glia-memory-copy">Glia keeps a bounded research trail in this browser so prior questions, investigated genes, and workflow context can inform later sessions. It does not train the underlying model.</div>
        <div class="glia-memory-actions"><button class="glia-small-btn" id="glia-clear-memory">Clear memory</button></div>
      </div>
      <div id="glia-messages">
        ${messages.length ? messages.map(renderMessage).join("") : `<div class="glia-empty"><div class="glia-empty-title">Ask Glia</div><div class="glia-empty-copy">Ask about the current analysis or highlight text and choose <b>Ask Glia</b>.</div></div>`}
        ${data.processing ? '<div class="glia-thinking">Glia is working<span></span><span></span><span></span></div>' : ""}
      </div>
      <div id="glia-quick-actions"></div>
      <div id="glia-composer-wrap">
        <div id="glia-draft-quote" class="${runtime.draftQuote ? "glia-visible" : ""}">${runtime.draftQuote ? `<button id="glia-remove-quote" type="button" aria-label="Remove selected context">×</button><div class="glia-quote-label">${escapeHtml(runtime.draftQuote.section || "Selected context")}</div>${formatText(runtime.draftQuote.text || "")}` : ""}</div>
        <div class="glia-composer">
          <textarea id="glia-input" rows="1" placeholder="Ask Glia about this workspace…" ${data.configured ? "" : "disabled"}></textarea>
          <button id="glia-send" type="button" aria-label="Send" ${data.configured && !data.processing ? "" : "disabled"}>↑</button>
        </div>
        <div class="glia-footer-note">${data.configured ? "Research use only · grounded against retrieved evidence and current analyses" : "Glia is not configured on this deployment."}</div>
      </div>`;

    const quickWrap = shell.querySelector("#glia-quick-actions");
    (data.quick_actions || []).slice(0, 4).forEach((label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "glia-quick";
      button.textContent = label;
      button.onclick = () => {
        const input = shell.querySelector("#glia-input");
        if (input) { input.value = label; input.focus(); resizeInput(input); }
      };
      quickWrap.appendChild(button);
    });

    const messagesBox = shell.querySelector("#glia-messages");
    if (messagesBox) messagesBox.scrollTop = messagesBox.scrollHeight;

    shell.querySelector("#glia-close").onclick = () => setOpen(false);
    shell.querySelector("#glia-memory-toggle").onclick = () => { runtime.memoryOpen = !runtime.memoryOpen; render(); };
    shell.querySelector("#glia-new-thread").onclick = () => {
      setTriggerValue("new_thread", {id: `${Date.now()}-${Math.random()}`});
    };
    const clearMemory = shell.querySelector("#glia-clear-memory");
    if (clearMemory) clearMemory.onclick = () => {
      if (window.confirm("Clear Glia's saved research memory in this browser?")) {
        setTriggerValue("clear_memory", {id: `${Date.now()}-${Math.random()}`});
      }
    };
    const removeQuote = shell.querySelector("#glia-remove-quote");
    if (removeQuote) removeQuote.onclick = () => { runtime.draftQuote = null; render(); };

    const input = shell.querySelector("#glia-input");
    const send = shell.querySelector("#glia-send");
    if (input) {
      input.oninput = () => resizeInput(input);
      input.onkeydown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendPrompt();
        }
      };
    }
    if (send) send.onclick = sendPrompt;
  }

  function resizeInput(input) {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  }

  function sendPrompt() {
    if (!data.configured || data.processing) return;
    const input = shell.querySelector("#glia-input");
    const text = String(input?.value || "").trim();
    if (!text && !runtime.draftQuote) return;
    const payload = {
      id: `${Date.now()}-${Math.random()}`,
      message: text,
      quote: runtime.draftQuote?.text || null,
      section: runtime.draftQuote?.section || null,
      workflow: runtime.draftQuote?.workflow || data.active_workflow || null,
      ts: Date.now(),
    };
    if (input) input.value = "";
    runtime.draftQuote = null;
    shell.querySelector("#glia-send")?.setAttribute("disabled", "disabled");
    setTriggerValue("prompt", payload);
  }

  launcher.onclick = () => setOpen(true);

  function nearestSection(rect) {
    let label = data.active_workflow || "Current workspace";
    let nearestTop = -Infinity;
    document.querySelectorAll("h1,h2,h3,h4,h5").forEach((heading) => {
      if (heading.closest("#glia-shell")) return;
      const box = heading.getBoundingClientRect();
      if (box.top <= rect.top + 4 && box.top > nearestTop) {
        const text = String(heading.innerText || heading.textContent || "").trim();
        if (text) { label = text; nearestTop = box.top; }
      }
    });
    return label;
  }

  function selectionTouchesIgnoredArea(selection) {
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
      const text = String(selection?.toString() || "").replace(/\s+/g, " ").trim();
      if (!selection || selection.rangeCount === 0 || text.length < 3 || text.length > 1800) {
        selectionAction.classList.remove("glia-visible");
        return;
      }
      const rect = selection.getRangeAt(0).getBoundingClientRect();
      if (!rect || (!rect.width && !rect.height)) return;
      const top = Math.min(window.innerHeight - 42, Math.max(8, rect.bottom + 7));
      const left = Math.min(window.innerWidth - 92, Math.max(8, rect.right - 78));
      selectionAction.style.top = `${top}px`;
      selectionAction.style.left = `${left}px`;
      selectionAction.classList.add("glia-visible");
      selectionAction.onclick = (clickEvent) => {
        clickEvent.preventDefault();
        clickEvent.stopPropagation();
        runtime.draftQuote = {
          text,
          section: nearestSection(rect),
          workflow: data.active_workflow || "Current workspace",
        };
        selectionAction.classList.remove("glia-visible");
        setOpen(true);
        window.setTimeout(() => shell.querySelector("#glia-input")?.focus(), 0);
      };
    }, 0);
  }

  function onMouseDown(event) {
    if (!event.target?.closest?.("#glia-selection-action")) selectionAction.classList.remove("glia-visible");
  }

  document.addEventListener("mouseup", onMouseUp, true);
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
    document.getElementById("glia-shell")?.remove();
    document.getElementById("glia-launcher")?.remove();
    document.getElementById("glia-selection-action")?.remove();
  };
}
"""


GLIA_COMPONENT = st.components.v2.component(
    "glia_workspace_copilot",
    html=GLIA_HTML,
    css=GLIA_CSS,
    js=GLIA_JS,
    isolate_styles=False,
)


def _secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    value = value or os.getenv(name)
    return str(value).strip() if value else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_memory() -> dict[str, Any]:
    return {
        "version": GLIA_MEMORY_VERSION,
        "investigated_genes": [],
        "visited_workflows": [],
        "recent_questions": [],
        "recent_quotes": [],
        "interaction_count": 0,
        "last_active_workflow": "Gene Analysis",
        "updated_at": None,
    }


def _bounded_unique(values: list[str], value: str, limit: int) -> list[str]:
    clean = str(value or "").strip()
    if not clean:
        return values[-limit:]
    out = [item for item in values if item != clean]
    out.append(clean)
    return out[-limit:]


def _normalize_memory(raw: Any) -> dict[str, Any]:
    memory = _default_memory()
    if isinstance(raw, dict):
        for key in memory:
            if key in raw:
                memory[key] = raw[key]
    memory["investigated_genes"] = [str(x).upper() for x in (memory.get("investigated_genes") or []) if str(x).strip()][-MAX_MEMORY_GENES:]
    memory["visited_workflows"] = [str(x) for x in (memory.get("visited_workflows") or []) if str(x).strip()][-12:]
    memory["recent_questions"] = [str(x)[:1200] for x in (memory.get("recent_questions") or []) if str(x).strip()][-MAX_RECENT_QUESTIONS:]
    memory["recent_quotes"] = [str(x)[:900] for x in (memory.get("recent_quotes") or []) if str(x).strip()][-MAX_RECENT_QUOTES:]
    try:
        memory["interaction_count"] = max(0, int(memory.get("interaction_count") or 0))
    except Exception:
        memory["interaction_count"] = 0
    return memory


def _normalize_messages(raw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for item in raw[-MAX_PERSISTED_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        message: dict[str, Any] = {
            "role": role,
            "content": content[:12000],
        }
        if item.get("quote"):
            message["quote"] = str(item.get("quote"))[:1800]
        if item.get("section"):
            message["section"] = str(item.get("section"))[:200]
        if role == "assistant":
            message["references"] = list(item.get("references") or [])[:20]
            message["grounding_ok"] = item.get("grounding_ok", True)
            message["tools_used"] = list(item.get("tools_used") or [])[:12]
        out.append(message)
    return out


def _add_gene(memory: dict[str, Any], gene: Any) -> None:
    clean = str(gene or "").strip().upper()
    if clean:
        memory["investigated_genes"] = _bounded_unique(
            list(memory.get("investigated_genes") or []), clean, MAX_MEMORY_GENES
        )


def _update_memory_from_context(memory: dict[str, Any], context: dict[str, Any], active_workflow: str) -> None:
    memory["visited_workflows"] = _bounded_unique(
        list(memory.get("visited_workflows") or []), active_workflow, 12
    )
    memory["last_active_workflow"] = active_workflow

    profile = context.get("profile")
    if profile is not None:
        _add_gene(memory, getattr(profile, "gene", None))

    pair = context.get("pair") or {}
    if isinstance(pair, dict):
        _add_gene(memory, pair.get("gene_a"))
        _add_gene(memory, pair.get("gene_b"))

    for profile_item in (context.get("comparison_profiles") or []):
        _add_gene(memory, getattr(profile_item, "gene", None))

    signature = context.get("signature") or {}
    if isinstance(signature, dict):
        for row in (signature.get("top_genes_profiled") or [])[:10]:
            if isinstance(row, dict):
                _add_gene(memory, row.get("gene") or row.get("Gene"))

    memory["updated_at"] = _utc_now()


def _memory_for_model(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "investigated_genes": list(memory.get("investigated_genes") or [])[-24:],
        "visited_workflows": list(memory.get("visited_workflows") or [])[-8:],
        "recent_questions": list(memory.get("recent_questions") or [])[-8:],
        "recent_selected_context": list(memory.get("recent_quotes") or [])[-4:],
        "interaction_count": int(memory.get("interaction_count") or 0),
        "last_active_workflow": memory.get("last_active_workflow"),
    }


def _quick_actions(active_workflow: str) -> list[str]:
    mapping = {
        "Gene Analysis": [
            "Explain the strongest finding",
            "Where does the evidence conflict?",
            "What experiment would reduce uncertainty most?",
        ],
        "Target Pair Analysis": [
            "Challenge this target pair",
            "What evidence supports testing this combination?",
            "Design the cleanest validation sequence",
        ],
        "Researcher Data": [
            "Interpret the highest-priority signals",
            "What patterns are most biologically interesting?",
            "What should I validate first?",
        ],
        "Gene Set Comparison": [
            "Which target is best supported and why?",
            "Where do these genes diverge biologically?",
            "Which comparison is most worth testing?",
        ],
        "Methods & Data Sources": [
            "Explain this method in plain language",
            "Why is this evidence source used?",
            "What are the main limitations here?",
        ],
    }
    return mapping.get(active_workflow, ["Explain what I am looking at", "Find the main uncertainty", "What should I investigate next?"])


def _context_summary(context: dict[str, Any]) -> str:
    labels: list[str] = []
    profile = context.get("profile")
    if profile is not None:
        labels.append(f"Gene {getattr(profile, 'gene', '')}".strip())
    pair = context.get("pair") or {}
    if isinstance(pair, dict) and pair:
        labels.append(f"{pair.get('gene_a')} + {pair.get('gene_b')}")
    if context.get("signature") is not None:
        labels.append("Researcher Data")
    if context.get("comparison_profiles"):
        labels.append("Gene Set Comparison")
    return " · ".join(label for label in labels if label)


def render_glia_layer() -> None:
    """Mount Glia across the application and process one pending copilot event."""
    active_workflow = str(st.session_state.get("research_workflow_tabs") or "Gene Analysis")
    context = {
        "profile": st.session_state.get("profile"),
        "pair": st.session_state.get("pair"),
        "signature": st.session_state.get("signature"),
        "comparison_profiles": st.session_state.get("comparison_profiles"),
    }

    st.session_state.setdefault("glia_hydrated", False)
    st.session_state.setdefault("glia_messages", [])
    st.session_state.setdefault("glia_memory", _default_memory())
    st.session_state.setdefault("glia_revision", 0)
    st.session_state.setdefault("glia_last_event_id", None)
    st.session_state.setdefault("glia_processing", False)
    st.session_state.setdefault("glia_force_open_nonce", 0)

    memory = _normalize_memory(st.session_state.get("glia_memory"))
    _update_memory_from_context(memory, context, active_workflow)
    st.session_state["glia_memory"] = memory
    messages = _normalize_messages(st.session_state.get("glia_messages"))
    st.session_state["glia_messages"] = messages

    api_key = _secret("GROQ_API_KEY")
    model = _secret("GROQ_MODEL") or configured_model()

    result = GLIA_COMPONENT(
        data={
            "storage_key": GLIA_STORAGE_KEY,
            "hydrated": bool(st.session_state.get("glia_hydrated")),
            "configured": bool(api_key),
            "active_workflow": active_workflow,
            "context_summary": _context_summary(context),
            "force_open_nonce": int(st.session_state.get("glia_force_open_nonce") or 0),
            "messages": messages,
            "processing": bool(st.session_state.get("glia_processing")),
            "quick_actions": _quick_actions(active_workflow),
            "memory_summary": {
                "gene_count": len(memory.get("investigated_genes") or []),
                "interaction_count": memory.get("interaction_count", 0),
            },
            "persist_payload": {"messages": messages, "memory": memory},
            "persist_revision": int(st.session_state.get("glia_revision") or 0),
        },
        key="glia_workspace_shell",
        on_persisted_change=lambda: None,
        on_prompt_change=lambda: None,
        on_new_thread_change=lambda: None,
        on_clear_memory_change=lambda: None,
    )

    if not st.session_state.get("glia_hydrated"):
        persisted = getattr(result, "persisted", None)
        if persisted is None:
            return
        if isinstance(persisted, dict):
            st.session_state["glia_messages"] = _normalize_messages(persisted.get("messages"))
            st.session_state["glia_memory"] = _normalize_memory(persisted.get("memory"))
        st.session_state["glia_hydrated"] = True
        st.session_state["glia_revision"] = int(st.session_state.get("glia_revision") or 0) + 1
        st.rerun()

    new_thread = getattr(result, "new_thread", None)
    if isinstance(new_thread, dict) and new_thread.get("id") != st.session_state.get("glia_last_event_id"):
        st.session_state["glia_last_event_id"] = new_thread.get("id")
        st.session_state["glia_messages"] = []
        st.session_state["glia_revision"] += 1
        st.rerun()

    clear_memory = getattr(result, "clear_memory", None)
    if isinstance(clear_memory, dict) and clear_memory.get("id") != st.session_state.get("glia_last_event_id"):
        st.session_state["glia_last_event_id"] = clear_memory.get("id")
        st.session_state["glia_memory"] = _default_memory()
        st.session_state["glia_revision"] += 1
        st.rerun()

    event = getattr(result, "prompt", None)
    if not isinstance(event, dict):
        return
    event_id = event.get("id")
    if not event_id or event_id == st.session_state.get("glia_last_event_id"):
        return
    st.session_state["glia_last_event_id"] = event_id

    question = str(event.get("message") or "").strip()
    quote = str(event.get("quote") or "").strip()
    section = str(event.get("section") or "").strip()
    workflow = str(event.get("workflow") or active_workflow).strip()
    if not question and quote:
        question = "Explain the significance of this selected context."
    if not question:
        return

    memory = _normalize_memory(st.session_state.get("glia_memory"))
    memory["recent_questions"] = _bounded_unique(
        list(memory.get("recent_questions") or []), question, MAX_RECENT_QUESTIONS
    )
    if quote:
        memory["recent_quotes"] = _bounded_unique(
            list(memory.get("recent_quotes") or []), quote, MAX_RECENT_QUOTES
        )
    memory["interaction_count"] = int(memory.get("interaction_count") or 0) + 1
    memory["last_active_workflow"] = workflow or active_workflow
    memory["updated_at"] = _utc_now()
    st.session_state["glia_memory"] = memory

    prior_history = [
        {"role": item.get("role"), "content": item.get("content", "")}
        for item in _normalize_messages(st.session_state.get("glia_messages"))[-10:]
    ]
    user_message: dict[str, Any] = {"role": "user", "content": question}
    if quote:
        user_message["quote"] = quote
        user_message["section"] = section or workflow or "Selected context"
    st.session_state["glia_messages"].append(user_message)
    st.session_state["glia_messages"] = _normalize_messages(st.session_state["glia_messages"])
    st.session_state["glia_processing"] = True
    st.session_state["glia_revision"] += 1

    agent_context = {
        **context,
        "active_workflow": workflow or active_workflow,
        "selected_section": section or None,
        "selected_quote": quote or None,
    }

    if not api_key:
        st.session_state["glia_messages"].append(
            {"role": "assistant", "content": "Glia is not configured on this deployment yet.", "references": [], "grounding_ok": True}
        )
        st.session_state["glia_processing"] = False
        st.session_state["glia_revision"] += 1
        st.rerun()

    try:
        result_payload = run_agent_turn(
            question,
            history=prior_history,
            session_context=agent_context,
            persistent_memory=_memory_for_model(memory),
            api_key=api_key,
            model=model,
        )
        st.session_state["glia_messages"].append(
            {
                "role": "assistant",
                "content": result_payload.text,
                "references": result_payload.references,
                "tools_used": result_payload.tools_used,
                "grounding_ok": result_payload.grounding_ok,
            }
        )
    except ResearchAgentError as exc:
        st.session_state["glia_messages"].append(
            {"role": "assistant", "content": str(exc), "references": [], "grounding_ok": True}
        )
    finally:
        st.session_state["glia_messages"] = _normalize_messages(st.session_state["glia_messages"])
        st.session_state["glia_processing"] = False
        st.session_state["glia_revision"] += 1
        st.rerun()
