"""Evidence-grounded conversational research agent for GBM Gene Analysis.

The agent is deliberately a coordination layer over the validated V7 production
workflows. It may retrieve or summarize existing evidence, run existing
analyses, and propose clearly labeled hypotheses. It does not create new
scientific measurements, scores, or evidence records from model reasoning.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import re
from typing import Any, Callable

from gbm_evidence_engine.connectors import europepmc
from gbm_evidence_engine.research_intelligence_v7_prod import (
    SOFTWARE_VERSION,
    build_research_profile,
    evaluate_gene_pair,
    rank_gene_list,
)

try:  # Keep non-agent workflows importable if the optional client is absent.
    from openai import OpenAI
except Exception:  # pragma: no cover - exercised only in reduced environments.
    OpenAI = None


DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
AGENT_VERSION = "1.0.0"
MAX_TOOL_ROUNDS = 3
MAX_EVIDENCE_RECORDS = 6
MAX_HISTORY_MESSAGES = 3
MAX_HISTORY_CHARS = 900
MAX_MEMORY_CHARS = 1400
MAX_TOOL_OUTPUT_CHARS = 6500
MAX_PUBLICATION_ABSTRACT_CHARS = 700
MAX_OUTPUT_TOKENS = 500


SYSTEM_INSTRUCTIONS = """\
You are Glia, the integrated research copilot inside GBM Gene Analysis, a
glioblastoma research evidence-synthesis system. Your job is to help a researcher interrogate the
software's evidence, compare targets, inspect processed researcher-result
analyses, retrieve relevant GBM publications, identify contradictions, and turn
remaining uncertainty into defensible next experiments.

NON-NEGOTIABLE GROUNDING RULES
1. For any substantive GBM factual claim or quantitative conclusion, use at
   least one provided tool on the current turn. Do not answer from model memory.
2. Treat tool output as the factual boundary. Never invent a measurement,
   statistic, source, trial result, paper, dataset result, score, or citation.
3. Evidence records include citation tokens such as [EV:...]. Publication search
   results include [PUB:...]. Computed application analyses include [AN:...], and
   current-session processed-result context can include [CTX:...]. Cite the
   relevant token immediately after important factual claims.
4. Preserve evidence type. Association is not causation; expression is not
   dependency; a target-pair rationale is not synergy; a perturbational reversal
   hypothesis is not GBM efficacy; database absence is not negative biology.
5. Clearly label your own interpretation as "Inference" and proposed work as
   "Proposed experiment". Neither is retrieved evidence.
6. If evidence conflicts, surface the conflict rather than averaging it away.
   If evidence is missing, say what is missing.
7. Do not recompute or silently modify Target Priority, Evidence Coverage,
   confidence, pair rationale, or any other production score.
8. Never give clinical treatment recommendations or patient-specific advice.
   The product is for research prioritization and hypothesis development only.
9. Do not request or encourage PHI, identifiable patient data, raw controlled
   genomic data, credentials, or restricted material.
10. Be concise and researcher-facing. Prefer a direct answer followed by the
    evidence that drives it and, when useful, the next experiment that would
    reduce uncertainty.
11. Persistent research memory is continuity context, not scientific evidence.
    Use it to remember prior questions, investigated targets, and research
    direction, but retrieve current evidence before making substantive GBM claims.

TOOL USE
- build_gene_dossier: full single-gene evidence synthesis.
- compare_target_pair: existing two-target rationale workflow.
- compare_gene_set: existing bounded side-by-side target comparison.
- search_gbm_publications: live biomedical literature title/abstract retrieval.
- inspect_current_analysis: retrieves analysis already created in the user's
  current application session, including processed Researcher Data results.

When a question can be answered from current session context, inspect that
context instead of asking the user to paste it again. Manual publication
retrieval can supplement a dossier, but distinguish retrieved publication
metadata/abstract content from evidence already integrated into the scored
model.
"""


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "name": "build_gene_dossier",
        "description": "Build the existing production V7 GBM evidence dossier for one gene and return its score, findings, evidence records, gaps, and linked publications.",
        "parameters": {
            "type": "object",
            "properties": {
                "gene": {"type": "string", "description": "Human gene symbol, for example EGFR."},
            },
            "required": ["gene"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_target_pair",
        "description": "Run the existing production target-pair analysis for two different genes. The result is a rationale for experimental testing, not a synergy prediction.",
        "parameters": {
            "type": "object",
            "properties": {
                "gene_a": {"type": "string"},
                "gene_b": {"type": "string"},
            },
            "required": ["gene_a", "gene_b"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_gene_set",
        "description": "Compare up to six genes through the same production evidence architecture used by Gene Set Comparison.",
        "parameters": {
            "type": "object",
            "properties": {
                "genes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 6,
                },
            },
            "required": ["genes"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_gbm_publications",
        "description": "Search live biomedical literature title/abstract fields for publications about a gene in glioblastoma, optionally narrowed by disease context and keywords.",
        "parameters": {
            "type": "object",
            "properties": {
                "gene": {"type": "string"},
                "context": {
                    "type": "string",
                    "enum": [
                        "none",
                        "recurrent",
                        "treatment_resistance",
                        "IDH",
                        "MGMT",
                        "single_cell",
                        "spatial",
                        "blood_brain_barrier",
                    ],
                },
                "terms": {
                    "type": "string",
                    "description": "Optional additional title/abstract keywords. Use an empty string when not needed.",
                },
            },
            "required": ["gene", "context", "terms"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "inspect_current_analysis",
        "description": "Inspect analysis results already present in the user's current GBM Gene Analysis session instead of asking the user to paste them again.",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["all", "gene", "pair", "researcher_data", "comparison"],
                },
            },
            "required": ["scope"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


@dataclass
class AgentReference:
    token: str
    label: str
    source: str
    url: str | None = None
    kind: str = "evidence"


@dataclass
class AgentResult:
    text: str
    references: list[dict[str, Any]]
    tools_used: list[str]
    model: str
    grounding_ok: bool
    unmatched_numbers: list[str]


class ResearchAgentError(RuntimeError):
    pass


def configured_model(explicit_model: str | None = None) -> str:
    return (explicit_model or os.getenv("GROQ_MODEL") or DEFAULT_MODEL).strip()


def has_api_key(explicit_key: str | None = None) -> bool:
    return bool((explicit_key or os.getenv("GROQ_API_KEY") or "").strip())


def _register_reference(
    registry: dict[str, AgentReference],
    token: str,
    label: str,
    source: str,
    *,
    url: str | None = None,
    kind: str = "evidence",
) -> str:
    clean = token.strip().strip("[]")
    registry.setdefault(
        clean,
        AgentReference(token=clean, label=label, source=source, url=url, kind=kind),
    )
    return f"[{clean}]"


def _safe_text(value: Any, limit: int = 2200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _compact_for_model(value: Any, *, depth: int = 0) -> Any:
    """Bound nested tool context before it is sent to the language model."""
    if depth >= 4:
        return _safe_text(value, 320)
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in list(value.items())[:28]:
            out[str(key)] = _compact_for_model(item, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [_compact_for_model(item, depth=depth + 1) for item in list(value)[:8]]
    if isinstance(value, str):
        return value[:900]
    return value


def _bounded_json(value: Any, limit: int = MAX_TOOL_OUTPUT_CHARS) -> str:
    compacted = _compact_for_model(value)
    encoded = json.dumps(compacted, default=str, separators=(",", ":"))
    if len(encoded) <= limit:
        return encoded
    summary = encoded[: max(400, limit - 120)]
    return json.dumps({"truncated_for_model": True, "summary": summary}, separators=(",", ":"))


def _record_payload(record: Any, registry: dict[str, AgentReference]) -> dict[str, Any]:
    provenance = record.provenance
    citation = _register_reference(
        registry,
        f"EV:{record.id}",
        record.claim_text,
        provenance.source_dataset,
        url=provenance.citation_url,
        kind="evidence_record",
    )
    caveats = record.caveats
    if isinstance(caveats, (list, tuple)):
        caveats = [_safe_text(item, 280) for item in caveats[:3]]
    else:
        caveats = _safe_text(caveats, 500)
    return {
        "citation": citation,
        "claim": _safe_text(record.claim_text, 700),
        "tier": record.tier.value,
        "statistic_name": record.statistic_name,
        "statistic_value": record.statistic_value,
        "p_value": record.p_value,
        "corrected_p_value": record.corrected_p_value,
        "effect_size": record.effect_size,
        "confidence_interval": record.confidence_interval,
        "confidence": record.confidence.value,
        "source_dataset": provenance.source_dataset,
        "sample_size": provenance.sample_size,
        "caveats": caveats,
    }


def _publication_token(paper: dict[str, Any]) -> str:
    if paper.get("pmid"):
        return f"PUB:PMID:{paper['pmid']}"
    if paper.get("pmcid"):
        return f"PUB:PMCID:{paper['pmcid']}"
    if paper.get("doi"):
        return "PUB:DOI:" + re.sub(r"[^A-Za-z0-9._/-]+", "", str(paper["doi"]))
    fallback = re.sub(r"[^A-Za-z0-9]+", "-", str(paper.get("id") or paper.get("title") or "record"))
    return f"PUB:EPMC:{fallback[:72]}"


def _publication_payload(paper: dict[str, Any], registry: dict[str, AgentReference]) -> dict[str, Any]:
    token = _publication_token(paper)
    citation = _register_reference(
        registry,
        token,
        _safe_text(paper.get("title"), 400) or "Biomedical publication",
        "Biomedical literature",
        url=paper.get("url"),
        kind="publication",
    )
    return {
        "citation": citation,
        "title": _safe_text(paper.get("title"), 400),
        "authors": _safe_text(paper.get("authors"), 320),
        "journal": _safe_text(paper.get("journal"), 180),
        "year": paper.get("year"),
        "pmid": paper.get("pmid"),
        "pmcid": paper.get("pmcid"),
        "doi": paper.get("doi"),
        "cited_by": paper.get("cited_by"),
        "url": paper.get("url"),
        "abstract": _safe_text(paper.get("abstract"), MAX_PUBLICATION_ABSTRACT_CHARS),
        "publication_types": (paper.get("publication_types") or [])[:4],
    }


def _profile_payload(
    profile: Any,
    registry: dict[str, AgentReference],
    *,
    include_evidence: bool = True,
) -> dict[str, Any]:
    live = profile.live
    analysis_citation = _register_reference(
        registry,
        f"AN:GENE:{profile.gene.upper()}",
        f"Production GBM Gene Analysis dossier for {profile.gene}",
        f"GBM Gene Analysis {SOFTWARE_VERSION}",
        kind="analysis",
    )
    evidence = []
    if include_evidence:
        records = list(profile.dossier.evidence)[:MAX_EVIDENCE_RECORDS]
        evidence = [_record_payload(record, registry) for record in records]

    papers = [
        _publication_payload(paper, registry)
        for paper in (live.get("literature", {}).get("top_papers") or [])[:4]
    ]
    return {
        "analysis_citation": analysis_citation,
        "gene": profile.gene,
        "target_priority_score": profile.score.overall,
        "priority_classification": profile.score.label,
        "evidence_coverage_pct": profile.score.evidence_coverage_pct,
        "overall_evidence_confidence": live.get("overall_evidence_confidence"),
        "functional_model_relevance": live.get("model_relevance"),
        "key_findings": (live.get("key_findings") or [])[:6],
        "evidence_consistency": live.get("evidence_consistency") or {},
        "research_opportunities": (live.get("research_opportunities") or [])[:4],
        "mechanistic_hypotheses": (live.get("mechanistic_hypotheses") or [])[:3],
        "evidence_gaps": list(profile.evidence_gaps)[:6],
        "next_experiments": list(profile.next_experiments)[:5],
        "evidence_records": evidence,
        "relevant_publications": papers,
        "source_status": _compact_for_model(profile.source_status),
        "score_caveat": profile.score.caveat,
        "software_version": SOFTWARE_VERSION,
    }


def _pair_payload(pair: dict[str, Any], registry: dict[str, AgentReference]) -> dict[str, Any]:
    gene_a = str(pair.get("gene_a") or "A").upper()
    gene_b = str(pair.get("gene_b") or "B").upper()
    citation = _register_reference(
        registry,
        f"AN:PAIR:{gene_a}-{gene_b}",
        f"Production target-pair analysis for {gene_a} + {gene_b}",
        f"GBM Gene Analysis {pair.get('software_version') or SOFTWARE_VERSION}",
        kind="analysis",
    )
    compacted = _compact_for_model(pair)
    return {"analysis_citation": citation, **(compacted if isinstance(compacted, dict) else {})}


def _signature_payload(signature: dict[str, Any], registry: dict[str, AgentReference]) -> dict[str, Any]:
    citation = _register_reference(
        registry,
        "CTX:RESEARCHER_DATA",
        "Processed Researcher Data result dossier in the current session",
        f"GBM Gene Analysis {signature.get('software_version') or SOFTWARE_VERSION}",
        kind="session_context",
    )
    # Send derived analysis context only. The raw uploaded/pasted table is never
    # included in the agent payload by this function.
    return {
        "analysis_citation": citation,
        "n_input_genes": signature.get("n_input_genes"),
        "n_statistically_supported": signature.get("n_statistically_supported"),
        "statistics_provided": signature.get("statistics_provided"),
        "top_genes_profiled": (signature.get("top_genes_profiled") or [])[:10],
        "up_pathway_enrichment": _compact_for_model(signature.get("up_pathway_enrichment")),
        "down_pathway_enrichment": _compact_for_model(signature.get("down_pathway_enrichment")),
        "l1000_reversal": _compact_for_model(signature.get("l1000_reversal")),
        "interpretation": _safe_text(signature.get("interpretation"), 900),
        "software_version": signature.get("software_version") or SOFTWARE_VERSION,
    }


def _comparison_payload(profiles: list[Any], registry: dict[str, AgentReference]) -> dict[str, Any]:
    genes = [profile.gene for profile in profiles]
    token = "CTX:COMPARISON:" + "-".join(g.upper() for g in genes[:6])
    citation = _register_reference(
        registry,
        token,
        "Gene Set Comparison result in the current session",
        f"GBM Gene Analysis {SOFTWARE_VERSION}",
        kind="session_context",
    )
    rows = []
    for profile in profiles[:6]:
        live = profile.live
        rows.append(
            {
                "gene": profile.gene,
                "target_priority_score": profile.score.overall,
                "evidence_coverage_pct": profile.score.evidence_coverage_pct,
                "priority_classification": profile.score.label,
                "evidence_confidence": live.get("overall_evidence_confidence"),
                "model_relevance": live.get("model_relevance"),
                "key_findings": (live.get("key_findings") or [])[:3],
            }
        )
    return {"analysis_citation": citation, "genes": genes, "results": rows}


def available_session_context(session_context: dict[str, Any] | None) -> list[str]:
    context = session_context or {}
    labels = []
    if context.get("profile") is not None:
        labels.append("gene")
    if context.get("pair") is not None:
        labels.append("pair")
    if context.get("signature") is not None:
        labels.append("researcher_data")
    if context.get("comparison_profiles"):
        labels.append("comparison")
    return labels


def _inspect_session(
    scope: str,
    session_context: dict[str, Any],
    registry: dict[str, AgentReference],
) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    if scope in {"all", "gene"} and session_context.get("profile") is not None:
        selected["gene"] = _profile_payload(
            session_context["profile"], registry, include_evidence=(scope == "gene")
        )
    if scope in {"all", "pair"} and session_context.get("pair") is not None:
        selected["pair"] = _pair_payload(session_context["pair"], registry)
    if scope in {"all", "researcher_data"} and session_context.get("signature") is not None:
        selected["researcher_data"] = _signature_payload(session_context["signature"], registry)
    if scope in {"all", "comparison"} and session_context.get("comparison_profiles"):
        selected["comparison"] = _comparison_payload(session_context["comparison_profiles"], registry)
    return {
        "ok": bool(selected),
        "requested_scope": scope,
        "available_scopes": available_session_context(session_context),
        "analysis": selected,
        "note": "Only derived analysis results are returned; raw uploaded researcher tables are not sent by this tool.",
    }


def _dispatch_tool(
    name: str,
    arguments: dict[str, Any],
    session_context: dict[str, Any],
    registry: dict[str, AgentReference],
) -> dict[str, Any]:
    if name == "build_gene_dossier":
        gene = str(arguments.get("gene") or "").strip()
        if not gene:
            raise ValueError("A gene symbol is required.")
        return _profile_payload(build_research_profile(gene), registry, include_evidence=True)

    if name == "compare_target_pair":
        result = evaluate_gene_pair(
            str(arguments.get("gene_a") or ""),
            str(arguments.get("gene_b") or ""),
        )
        return _pair_payload(result, registry)

    if name == "compare_gene_set":
        genes = list(dict.fromkeys(str(g).strip() for g in (arguments.get("genes") or []) if str(g).strip()))[:6]
        if not genes:
            raise ValueError("At least one gene symbol is required.")
        profiles = rank_gene_list(genes, max_workers=1)
        return _comparison_payload(profiles, registry)

    if name == "search_gbm_publications":
        context = str(arguments.get("context") or "none")
        result = europepmc.search_publications(
            str(arguments.get("gene") or "").strip(),
            context_key=None if context == "none" else context,
            terms=str(arguments.get("terms") or ""),
            page_size=8,
            cursor_mark=None,
        )
        papers = [_publication_payload(paper, registry) for paper in (result.get("papers") or [])[:6]]
        return {
            "ok": result.get("ok"),
            "query": result.get("query"),
            "hit_count": result.get("hit_count"),
            "papers": papers,
            "error": result.get("error"),
            "source": "Europe PMC",
        }

    if name == "inspect_current_analysis":
        return _inspect_session(
            str(arguments.get("scope") or "all"),
            session_context,
            registry,
        )

    raise ValueError(f"Unknown research-agent tool: {name}")


def _history_input(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in (history or [])[-MAX_HISTORY_MESSAGES:]:
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        out.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return out


def _response_output_items(response: Any) -> list[Any]:
    return list(getattr(response, "output", None) or [])


def _function_calls(response: Any) -> list[Any]:
    return [item for item in _response_output_items(response) if getattr(item, "type", None) == "function_call"]


def _reference_dicts(registry: dict[str, AgentReference], text: str) -> list[dict[str, Any]]:
    used = []
    for token, ref in registry.items():
        if f"[{token}]" in text:
            used.append(asdict(ref))
    # If the model failed to inline citations, still expose consulted sources so
    # the user can audit the answer rather than hiding the retrieval trail.
    if not used and registry:
        used = [asdict(ref) for ref in registry.values()]
    return used


_BRACKETED_CITATION_RE = re.compile(r"\[(?:EV|PUB|AN|CTX):[^\]]+\]")
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?%?")


def _numeric_tokens(value: Any) -> set[str]:
    text = json.dumps(value, default=str, sort_keys=True)
    numbers: set[str] = set()
    for token in _NUMBER_RE.findall(text):
        raw = token.rstrip("%")
        try:
            number = float(raw)
        except ValueError:
            continue
        numbers.add(raw)
        if number == int(number):
            numbers.add(str(int(number)))
        for digits in (1, 2, 3, 4):
            numbers.add(f"{number:.{digits}f}".rstrip("0").rstrip("."))
            numbers.add(f"{number:.{digits}g}")
    return numbers


def validate_quantitative_grounding(text: str, tool_payloads: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Check nontrivial quantitative claims against values returned by tools.

    Small bare integers are ignored because they commonly enumerate prose
    ("two reasons", "three steps"). Percentages and larger/statistical values
    remain checked. Citation identifiers are removed before scanning.
    """
    allowed: set[str] = set()
    for payload in tool_payloads:
        allowed |= _numeric_tokens(payload)
    cleaned = _BRACKETED_CITATION_RE.sub(" ", text)
    unmatched: list[str] = []
    for token in _NUMBER_RE.findall(cleaned):
        is_percent = token.endswith("%")
        raw = token.rstrip("%")
        try:
            number = float(raw)
        except ValueError:
            continue
        if not is_percent and number.is_integer() and abs(number) <= 10:
            continue
        variants = {raw, raw.rstrip("0").rstrip(".")}
        if not (variants & allowed):
            unmatched.append(token)
    return not unmatched, list(dict.fromkeys(unmatched))


def _create_response(client: Any, *, model: str, input_items: list[Any], tools: list[dict[str, Any]]) -> Any:
    kwargs: dict[str, Any] = {
        "model": model,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": input_items,
        "tools": tools,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "store": False,
    }
    if model.startswith("openai/gpt-oss-"):
        kwargs["reasoning"] = {"effort": "low"}
    return client.responses.create(**kwargs)


def run_agent_turn(
    user_message: str,
    *,
    history: list[dict[str, Any]] | None = None,
    session_context: dict[str, Any] | None = None,
    persistent_memory: dict[str, Any] | None = None,
    api_key: str | None = None,
    model: str | None = None,
    client: Any | None = None,
    tool_dispatcher: Callable[[str, dict[str, Any], dict[str, Any], dict[str, AgentReference]], dict[str, Any]] | None = None,
) -> AgentResult:
    """Run one grounded conversational turn with bounded function calling."""
    question = str(user_message or "").strip()
    if not question:
        raise ResearchAgentError("Enter a research question.")

    selected_model = configured_model(model)
    if client is None:
        key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
        if not key:
            raise ResearchAgentError("Glia is not configured yet.")
        if OpenAI is None:
            raise ResearchAgentError("The API client dependency is unavailable.")
        client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)

    context = session_context or {}
    available = available_session_context(context)
    context_note = (
        "Current application analyses available to inspect: " + ", ".join(available)
        if available
        else "No prior application analysis is currently available in this session."
    )
    active_workflow = str(context.get("active_workflow") or "").strip()
    selected_section = str(context.get("selected_section") or "").strip()
    selected_quote = str(context.get("selected_quote") or "").strip()[:1800]
    memory = persistent_memory if isinstance(persistent_memory, dict) else {}
    continuity_note = json.dumps(memory, default=str, sort_keys=True)[:MAX_MEMORY_CHARS] if memory else "No saved research continuity yet."
    ui_notes = []
    if active_workflow:
        ui_notes.append(f"Active workflow: {active_workflow}.")
    if selected_section:
        ui_notes.append(f"Selected section: {selected_section}.")
    if selected_quote:
        ui_notes.append(
            "Selected on-screen context (use as question context, not as independent scientific evidence): "
            + selected_quote
        )
    input_items: list[Any] = _history_input(history)
    input_items.append(
        {
            "role": "user",
            "content": (
                question
                + "\n\nApplication context note: "
                + context_note
                + ("\n" + " ".join(ui_notes) if ui_notes else "")
                + "\nPersistent research continuity: "
                + continuity_note
            ),
        }
    )

    registry: dict[str, AgentReference] = {}
    tools_used: list[str] = []
    tool_payloads: list[dict[str, Any]] = []
    dispatch = tool_dispatcher or _dispatch_tool

    try:
        response = _create_response(client, model=selected_model, input_items=input_items, tools=TOOL_DEFINITIONS)
        for _ in range(MAX_TOOL_ROUNDS):
            calls = _function_calls(response)
            if not calls:
                break
            input_items.extend(_response_output_items(response))
            for call in calls:
                name = str(call.name)
                tools_used.append(name)
                try:
                    arguments = json.loads(call.arguments or "{}")
                    payload = dispatch(name, arguments, context, registry)
                except Exception as exc:
                    payload = {
                        "ok": False,
                        "error": f"{type(exc).__name__}: {exc}",
                        "tool": name,
                    }
                tool_payloads.append(payload)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": _bounded_json(payload),
                    }
                )
            response = _create_response(client, model=selected_model, input_items=input_items, tools=TOOL_DEFINITIONS)
        else:
            raise ResearchAgentError("The assistant reached its tool-call limit. Narrow the question and try again.")
    except ResearchAgentError:
        raise
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        message = str(exc)
        lowered = message.lower()
        if (
            status_code == 413
            or "request too large" in lowered
            or "rate_limit_exceeded" in lowered and "tokens per minute" in lowered
        ):
            raise ResearchAgentError(
                "Glia could not fit this request within the current free-tier context limit. "
                "Try again; if it repeats, start a new thread or ask a narrower question."
            ) from exc
        if status_code == 429 or "rate limit" in lowered or "too many requests" in lowered:
            raise ResearchAgentError(
                "Glia is temporarily at capacity on the shared Groq free tier. Please try again later."
            ) from exc
        if status_code in {401, 403}:
            raise ResearchAgentError(
                "Glia could not authenticate with Groq. Check the deployment API key."
            ) from exc
        raise ResearchAgentError(f"Glia request failed: {exc}") from exc

    text = str(getattr(response, "output_text", None) or "").strip()
    if not text:
        raise ResearchAgentError("The assistant returned no answer.")

    grounding_ok, unmatched = validate_quantitative_grounding(text, tool_payloads)
    if not grounding_ok and tool_payloads:
        # One bounded correction pass: the model gets the exact grounded tool
        # context already accumulated and must remove unsupported quantities.
        input_items.extend(_response_output_items(response))
        input_items.append(
            {
                "role": "user",
                "content": (
                    "Grounding correction: rewrite the answer without introducing any quantitative value "
                    f"that is not present in the tool evidence. Unsupported values detected: {', '.join(unmatched)}. "
                    "Preserve valid citation tokens and the scientific meaning."
                ),
            }
        )
        try:
            corrected = _create_response(client, model=selected_model, input_items=input_items, tools=[])
            corrected_text = str(getattr(corrected, "output_text", None) or "").strip()
            if corrected_text:
                text = corrected_text
                grounding_ok, unmatched = validate_quantitative_grounding(text, tool_payloads)
        except Exception:
            pass

    return AgentResult(
        text=text,
        references=_reference_dicts(registry, text),
        tools_used=list(dict.fromkeys(tools_used)),
        model=selected_model,
        grounding_ok=grounding_ok,
        unmatched_numbers=unmatched,
    )
