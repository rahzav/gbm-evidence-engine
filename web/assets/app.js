const workflows = [
  {id:"gene",name:"Gene Analysis",caption:"Build a single-gene dossier across genomic, functional, spatial, human, translational, literature, and cell-state evidence."},
  {id:"pair",name:"Target Pair Analysis",caption:"Compare two targets through functional, network, spatial, recurrence, translational, and model-relevance evidence."},
  {id:"researcher",name:"Researcher Data",caption:"Add GBM-specific evidence, pathway, and perturbational context to processed gene-level results."},
  {id:"comparison",name:"Gene Set Comparison",caption:"Compare a focused gene set through the same production evidence architecture."},
  {id:"methods",name:"Methods & Data Sources",caption:"Audit the evidence model, provenance, interpretation boundaries, and source availability."},
];
const state={
  view:"research",
  results:{},
  resultTabs:{},
  messages:JSON.parse(localStorage.getItem("glia.messages")||"[]"),
  archives:JSON.parse(localStorage.getItem("glia.archives")||"[]"),
  memory:JSON.parse(localStorage.getItem("glia.memory")||'{"investigated_genes":[],"recent_questions":[],"interaction_count":0}'),
  quote:null,
  sending:false,
};
const $=(s,r=document)=>r.querySelector(s);const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const human=v=>String(v??"N/A").replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const number=(v,d=1)=>v===null||v===undefined?"N/A":typeof v==="number"?v.toFixed(d).replace(/\.0$/,""):v;
const current=()=>state.view==="research"?{id:"research",name:"Glia Deep Research",caption:"Evidence-grounded GBM research intelligence"}:workflows.find(w=>w.id===state.view);
const icon=id=>({gene:"⌁",pair:"⇄",researcher:"↥",comparison:"≋",methods:"§"}[id]);

function persist(){localStorage.setItem("glia.messages",JSON.stringify(state.messages.slice(-40)));localStorage.setItem("glia.archives",JSON.stringify(state.archives.slice(0,12)));localStorage.setItem("glia.memory",JSON.stringify(state.memory))}
function sectionLabel(text){return ["Analysis setup","Data and column mapping","Comparison set","Scientific architecture"].includes(text)?"":`<div class="section-label">${esc(text)}</div>`}
function header(w){return `<header class="tool-heading"><div><small>Research tool</small><h1>${w.name}</h1><p>${w.caption}</p></div><span class="tool-context">Context is available to Glia</span></header>`}
function loading(label){return `<div class="loading"><span class="spinner"></span>${esc(label)}</div>`}
function errorBox(message){return `<div class="error-state"><strong>Analysis could not be completed.</strong><br>${esc(message)}</div>`}
function empty(title,copy){return `<div class="empty-state"><strong>${title}</strong>${copy}</div>`}
async function api(path,body){const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const data=await response.json().catch(()=>({detail:"The server returned an unreadable response."}));if(!response.ok)throw new Error(data.detail||"Request failed.");return data}

function renderNav(){
  $("#tool-navigation").innerHTML=workflows.map(w=>`<button class="nav-item ${w.id===state.view?"active":""}" data-view="${w.id}"><span class="nav-icon">${icon(w.id)}</span><span>${w.name}</span></button>`).join("");
  $$("[data-view]").forEach(b=>{b.classList.toggle("active",b.dataset.view===state.view);b.onclick=()=>switchView(b.dataset.view)});
  renderHistory();
}
function switchView(id){
  state.view=id;
  const w=current();
  $("#view-title").textContent=w.name;
  $("#view-subtitle").textContent=w.caption;
  $("#return-research").classList.toggle("hidden",id==="research");
  renderNav();
  renderWorkspace();
  $("#sidebar").classList.remove("open");
  $("#mobile-scrim").classList.remove("visible");
  $("#main-view").focus();
}
function renderWorkspace(){
  const w=current();
  let content="";
  if(w.id==="research") content=researchView();
  else {
    content=`<section class="tool-view">${header(w)}`;
    if(w.id==="gene")content+=geneView();
    if(w.id==="pair")content+=pairView();
    if(w.id==="researcher")content+=researcherView();
    if(w.id==="comparison")content+=comparisonView();
    if(w.id==="methods")content+=methodsView();
    content+="</section>";
  }
  $("#main-view").innerHTML=content;
  bindWorkspace();
}
function researchView(){
  const messages=state.messages.length?state.messages.map(messageMarkup).join(""):`<div class="research-empty"><div class="empty-mark"><svg aria-hidden="true"><use href="#glia-symbol" /></svg><span>Glia Deep Research</span></div><h1>What are you investigating?</h1><p>Ask a consequential GBM research question. Glia can build and interrogate evidence, challenge a conclusion, compare targets, or identify the experiment that best reduces uncertainty.</p><div class="starter-list"><button data-prompt="What is the strongest evidence for EGFR as a GBM target?"><small>Interrogate evidence</small><span>Assess the case for a target</span></button><button data-prompt="Compare EGFR and CDK4 and identify the decisive evidence gap."><small>Compare alternatives</small><span>Determine what separates two targets</span></button><button data-prompt="What experiment would most reduce uncertainty around a GBM target?"><small>Design a study</small><span>Find the highest-information next test</span></button></div></div>`;
  return `<section class="research-view"><div class="conversation" id="conversation">${messages}${state.sending?'<div class="message assistant"><div class="message-heading">Glia</div><div class="thinking"><i></i>Interrogating the evidence…</div></div>':""}</div>${composerMarkup()}</section>`;
}
function messageMarkup(m){
  const refs=(m.references||[]).map(r=>r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.label||r.source)}</a>`:`<span>${esc(r.label||r.source)}</span>`).join("");
  return `<article class="message ${m.role}"><div class="message-heading">${m.role==="user"?"You":"Glia"}</div><div class="message-body">${m.quote?`<div class="message-quote">${esc(m.quote)}</div>`:""}${esc(m.content)}${refs?`<div class="message-refs">${refs}</div>`:""}</div></article>`;
}
function composerMarkup(){
  const menu=workflows.map(w=>`<button type="button" data-tool="${w.id}">${w.name}</button>`).join("");
  return `<div class="composer-dock"><form id="composer"><div class="composer"><div class="quote-context ${state.quote?"visible":""}" id="quote-context"><button type="button" id="remove-quote">×</button><small>${esc(state.quote?.section||"Selected context")}</small><p>${esc(state.quote?.text||"")}</p></div><textarea id="glia-input" rows="1" placeholder="Ask Glia a research question…" aria-label="Ask Glia"></textarea><div class="composer-toolbar"><div class="tool-menu-wrap"><button class="composer-tool" id="tools-button" type="button">＋ Research tools</button><div class="tool-menu" id="tools-menu">${menu}</div></div><span class="mode-label">Deep research</span><button class="send-button" type="submit" aria-label="Send">↑</button></div></div><p class="composer-note">Glia separates retrieved evidence from inference and preserves citations and provenance.</p></form></div>`;
}
function geneView(){return `${sectionLabel("Analysis setup")}<form class="control-surface form-grid" id="gene-form"><div class="field"><label for="gene-input">Gene symbol <span class="field-help">HGNC-approved symbol or known alias</span></label><input id="gene-input" value="EGFR" placeholder="EGFR, PTEN, TERT, CDK6" autocomplete="off"></div><button class="button button-primary" type="submit">Build dossier</button></form><div id="gene-output">${state.results.gene?profileResult(state.results.gene):""}</div>`}
function pairView(){return `${sectionLabel("Analysis setup")}<form class="control-surface form-grid three" id="pair-form"><div class="field"><label for="gene-a">Target A</label><input id="gene-a" value="EGFR"></div><div class="field"><label for="gene-b">Target B</label><input id="gene-b" value="CDK4"></div><button class="button button-primary" type="submit">Build pair dossier</button></form><div id="pair-output">${state.results.pair?pairResult(state.results.pair):""}</div>`}
function researcherView(){return `${sectionLabel("Data and column mapping")}<form class="control-surface" id="researcher-form"><label class="dropzone"><input id="signature-file" type="file" accept=".csv,.tsv,.txt"><strong>Upload a processed CSV or TSV</strong><span>Gene, signed effect, and optional p-value/FDR columns</span></label><div class="or-divider">OR PASTE RESULTS</div><div class="field"><label for="signature-data">Processed gene-level table</label><textarea id="signature-data">gene,effect,p_value,fdr\nEGFR,2.4,0.0001,0.002\nSOX2,1.8,0.001,0.01\nSTAT3,1.5,0.004,0.02\nCDK6,1.2,0.01,0.04\nOLIG2,-1.1,0.02,0.05\nGFAP,-1.4,0.001,0.01\nCDKN1A,-1.7,0.0005,0.005\nBAX,-2.0,0.0001,0.002</textarea></div><div class="field-row"><div class="field"><label>Gene column</label><input id="col-gene" value="gene"></div><div class="field"><label>Signed effect</label><input id="col-effect" value="effect"></div><div class="field"><label>p-value <span class="field-help">optional</span></label><input id="col-p" value="p_value"></div><div class="field"><label>FDR <span class="field-help">optional</span></label><input id="col-fdr" value="fdr"></div></div><button class="button button-primary" style="margin-top:14px" type="submit">Build result dossier</button></form><div id="researcher-output">${state.results.researcher?signatureResult(state.results.researcher):""}</div>`}
function comparisonView(){return `${sectionLabel("Comparison set")}<form class="control-surface form-grid" id="comparison-form"><div class="field"><label for="gene-set">Gene symbols <span class="field-help">Maximum 6 genes</span></label><input id="gene-set" value="EGFR, PTEN, TP53, CDK4"></div><button class="button button-primary" type="submit">Build comparison</button></form><div id="comparison-output">${state.results.comparison?comparisonResult(state.results.comparison):""}</div>`}

function metrics(items){return `<div class="metrics">${items.map(x=>`<div class="metric"><div class="metric-label">${esc(x[0])}</div><div class="metric-value">${esc(x[1])}</div>${x[2]?`<div class="metric-note">${esc(x[2])}</div>`:""}</div>`).join("")}</div>`}
function tabs(id,labels,panels){const active=state.resultTabs[id]||0;return `<div class="result-tabs">${labels.map((x,i)=>`<button class="result-tab ${i===active?"active":""}" data-result-tab="${id}:${i}">${x}</button>`).join("")}</div><div class="tab-panel">${panels[active]}</div>`}
function findings(profile){const list=profile.live?.key_findings||[];const consistency=profile.live?.evidence_consistency||{};return `<div class="content-grid"><section class="evidence-panel"><h3>Decision-relevant findings</h3>${list.length?`<ul>${list.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:"<p>No concise findings were generated from the available evidence.</p>"}</section><section class="evidence-panel"><h3>Evidence consistency</h3><p><strong>${esc(human(consistency.status||"Not assessed"))}</strong></p>${(consistency.flags||[]).length?`<ul>${consistency.flags.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:`<p>${esc(consistency.note||"No cross-source conflict was flagged.")}</p>`}</section></div>`}
function dimensionTable(profile){const dims=profile.score?.dimensions||{};return table(["Evidence dimension","Score","Weight","Primary source","Interpretation"],Object.entries(dims).map(([name,d])=>[human(name),d.score==null?"Not scored":`${number(d.score)}/100`,`${Math.round((d.weight||0)*100)}%`,d.source||"—",d.rationale||"—"]),1)}
function sourceTable(profile){return table(["Data source","Status"],Object.entries(profile.source_status||{}).map(([k,v])=>[human(k),`<span class="status ${String(v).toLowerCase().includes("available")||String(v).toLowerCase()==="ok"?"available":"unavailable"}">${esc(human(v))}</span>`]),-1,true)}
function evidenceSummary(profile){const live=profile.live||{};const rows=[
  ["TCGA mutation",live.cbioportal?.mutation?.frequency==null?"N/A":`${number(live.cbioportal.mutation.frequency*100)}%`],
  ["DepMap selectivity",number(live.depmap?.median_selectivity_delta,2)],
  ["CGGA cohorts",number(live.cgga?.n_usable_cohorts,0)],
  ["Active GBM trials",number(live.clinical_trials?.active,0)],
  ["Literature records",number(live.literature?.count,0)],
  ["B3DB matches",number(live.bbb_candidates?.matched_count,0)],
];return table(["Evidence signal","Current result"],rows)}
function profileResult(p){const score=p.score||{};const confidence=p.live?.overall_evidence_confidence?.level||p.live?.overall_evidence_confidence?.label||"Not assessed";const panels=[findings(p),dimensionTable(p),evidenceSummary(p),sourceTable(p)];return `${sectionLabel("Evidence dossier")}<div class="result-header"><div class="result-title"><h2>${esc(p.gene)}${p.live?.gene_identity?.name?` · ${esc(p.live.gene_identity.name)}`:""}</h2><p>${esc(human(score.label||"Research profile"))}. Read priority together with coverage and confidence.</p></div><div class="result-actions"><button class="button button-secondary" data-export="gene-json">Export JSON</button><button class="button button-secondary" data-ask-result>Ask Glia</button></div></div>${metrics([["Target Priority",score.overall==null?"N/A":`${number(score.overall)}/100`],["Evidence Coverage",`${number(score.evidence_coverage_pct)}%`],["Evidence Confidence",human(confidence)],["Active GBM Trials",number(p.live?.clinical_trials?.active,0)]])}${tabs("gene",["Overview","Score composition","Evidence","Sources & export"],panels)}`}
function pairResult(p){const components=p.components||{};const rationale=`<div class="content-grid"><section class="evidence-panel"><h3>Supporting rationale</h3><ul>${(p.why_test_it||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ul></section><section class="evidence-panel"><h3>Limitations</h3>${(p.risks||[]).length?`<ul>${p.risks.map(x=>`<li>${esc(x)}</li>`).join("")}</ul>`:"<p>No pair-specific limitation was generated.</p>"}</section></div>`;const validation=`<section class="evidence-panel"><h3>Validation sequence</h3><ol>${(p.validation_sequence||[]).map(x=>`<li>${esc(x)}</li>`).join("")}</ol></section>`;return `${sectionLabel("Pair evidence")}<div class="result-header"><div class="result-title"><h2>${esc(p.gene_a||"Target A")} + ${esc(p.gene_b||"Target B")}</h2><p>Combination rationale prioritizes experiments; it is not a synergy or efficacy prediction.</p></div><button class="button button-secondary" data-ask-result>Ask Glia</button></div>${metrics([["Combination Rationale",`${number(p.combination_rationale_score)}/100`],["Evidence Coverage",`${number(p.evidence_coverage_pct)}%`],["Pair Confidence",human(p.pair_evidence_confidence?.level||p.pair_evidence_confidence||"Not assessed")]])}${tabs("pair",["Rationale components","Interpretation","Validation sequence"],[table(["Component","Score"],Object.entries(components).map(([k,v])=>[human(k),number(v)])),rationale,validation])}`}
function signatureResult(s){return `${sectionLabel("Result dossier")}<div class="result-header"><div class="result-title"><h2>Processed result dossier</h2><p>GBM context applied to the submitted signed gene-level results.</p></div><button class="button button-secondary" data-export="signature-json">Export JSON</button></div>${metrics([["Input genes",number(s.n_input_genes,0)],["Statistically supported",s.statistics_provided?number(s.n_statistically_supported,0):"Not supplied"]])}${tabs("researcher",["Prioritized signals","Pathway enrichment","Perturbational reversal"],[tableFromObjects(s.top_genes_profiled||[]),`<div class="content-grid"><section class="evidence-panel"><h3>Upregulated program</h3>${tableFromObjects(s.up_pathway_enrichment?.results||[])}</section><section class="evidence-panel"><h3>Downregulated program</h3>${tableFromObjects(s.down_pathway_enrichment?.results||[])}</section></div>`,tableFromObjects(s.l1000_reversal?.top_drugs||[])])}`}
function comparisonResult(c){const profiles=c.results||[];const rows=profiles.map(p=>[p.gene,number(p.score?.overall),`${number(p.score?.evidence_coverage_pct)}%`,human(p.live?.overall_evidence_confidence?.level||"Not assessed"),human(p.live?.model_relevance?.level||"Unknown"),number(p.live?.clinical_trials?.active,0)]);return `${sectionLabel("Comparative evidence")}<div class="result-header"><div class="result-title"><h2>${profiles.length} target comparison</h2><p>Each target is evaluated through the same V7 evidence architecture.</p></div><button class="button button-secondary" data-ask-result>Ask Glia</button></div>${table(["Gene","Target Priority","Coverage","Confidence","Model relevance","Active trials"],rows)}`}
function table(headers,rows,scoreCol=-1,raw=false){if(!rows.length)return `<p class="empty-state">No results available.</p>`;return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map((v,i)=>`<td>${raw?v:esc(v)}${i===scoreCol&&parseFloat(v)>=0?`<div class="score-track"><i style="width:${Math.min(100,parseFloat(v))}%"></i></div>`:""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`}
function tableFromObjects(rows){if(!rows.length)return `<p>No supported results were returned.</p>`;const headers=Object.keys(rows[0]).slice(0,7);return table(headers.map(human),rows.slice(0,20).map(row=>headers.map(h=>typeof row[h]==="object"?JSON.stringify(row[h]):row[h])))}

function methodsView(){return `${sectionLabel("Scientific architecture")}<div class="methods-grid"><nav class="methods-index"><a href="#scope">Research scope</a><a href="#score">Scored evidence model</a><a href="#confidence">Confidence framework</a><a href="#researcher-method">Researcher data</a><a href="#provenance">Provenance & validation</a></nav><article class="prose"><h2 id="scope">Research scope</h2><p>Glia integrates molecular evidence for research prioritization, processed-result interpretation, target-pair evaluation, evidence interrogation, and experimental planning. It is built for glioblastoma molecular research rather than clinical treatment selection.</p><h2 id="score">Scored evidence model</h2><p>The V7 Target Priority Score integrates TCGA genomic signal, Open Targets disease relevance and druggability, clinical translation, literature context, DepMap functional dependency, Ivy GAP spatial expression, CGGA independent human validation, and GLASS longitudinal recurrence. Missing sources reduce Evidence Coverage rather than counting as negative biology.</p>${table(["Scored dimension","Weight"],[['TCGA GBM genomic signal','16.9%'],['Open Targets relevance','13.2%'],['Druggability','13.2%'],['Clinical translation','11.3%'],['Literature/context depth','9.4%'],['DepMap functional dependency','15.0%'],['Ivy GAP spatial context','7.5%'],['CGGA human validation','7.5%'],['GLASS recurrence','6.0%']])}<h2 id="confidence">Confidence, model relevance, and cell state</h2><p>Evidence Confidence remains separate from Target Priority. Functional Model Relevance describes dependency-model context. GBmap provides patient-aware malignant and microenvironment cell-state expression from the compact published Core GBmap reference.</p><h2 id="researcher-method">Processed researcher results</h2><p>Signed gene-level effects may include p-values or FDR/q-values. Glia adds GBM evidence prioritization, pathway enrichment, and L1000 perturbational-reversal context without processing raw sequencing files.</p><h2 id="provenance">Provenance and validation</h2><p>Quantitative evidence retains source, method, retrieval metadata, confidence, and citation information. Deterministic scientific tests, grounding checks, behavioral benchmarks, and production interaction tests remain separate from biological validation.</p></article></div>`}

function bindWorkspace(){
  const forms={"gene-form":runGene,"pair-form":runPair,"researcher-form":runResearcher,"comparison-form":runComparison};
  Object.entries(forms).forEach(([id,fn])=>{const f=$("#"+id);if(f)f.onsubmit=e=>{e.preventDefault();fn()}});
  $$("[data-result-tab]").forEach(b=>b.onclick=()=>{const[id,i]=b.dataset.resultTab.split(":");state.resultTabs[id]=Number(i);renderWorkspace()});
  $$("[data-ask-result]").forEach(b=>b.onclick=()=>{switchView("research");setComposer("What is the single most decision-relevant finding in the current analysis?")});
  $$("[data-export]").forEach(b=>b.onclick=()=>downloadJSON(b.dataset.export.startsWith("gene")?state.results.gene:state.results.researcher));
  const file=$("#signature-file");if(file)file.onchange=async()=>{if(file.files[0])$("#signature-data").value=await file.files[0].text()};
  const composer=$("#composer");
  if(composer) composer.onsubmit=e=>{e.preventDefault();const input=$("#glia-input"),message=input.value.trim();if(message&&!state.sending){input.value="";sendGlia(message)}};
  const input=$("#glia-input");
  if(input) input.oninput=e=>{e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,180)+"px"};
  const tools=$("#tools-button");
  if(tools) tools.onclick=()=>$("#tools-menu").classList.toggle("open");
  $$("[data-tool]").forEach(b=>b.onclick=()=>switchView(b.dataset.tool));
  $$("[data-prompt]").forEach(b=>b.onclick=()=>setComposer(b.dataset.prompt));
  const remove=$("#remove-quote");if(remove)remove.onclick=()=>{state.quote=null;renderWorkspace();setTimeout(()=>$("#glia-input")?.focus(),0)};
  if(state.view==="research"&&state.messages.length) requestAnimationFrame(()=>{const main=$("#main-view");main.scrollTop=main.scrollHeight});
}
function setComposer(value){const input=$("#glia-input");if(input){input.value=value;input.focus()}}
async function runGene(){const gene=$("#gene-input").value.trim();if(!gene)return;const out=$("#gene-output");out.innerHTML=loading(`Building the ${gene.toUpperCase()} evidence dossier…`);try{state.results.gene=await api("/profile",{gene});state.memory.investigated_genes=[...new Set([...(state.memory.investigated_genes||[]),state.results.gene.gene])].slice(-12);persist();out.innerHTML=profileResult(state.results.gene);bindWorkspace()}catch(e){out.innerHTML=errorBox(e.message)}}
async function runPair(){const gene_a=$("#gene-a").value.trim(),gene_b=$("#gene-b").value.trim(),out=$("#pair-output");out.innerHTML=loading(`Comparing ${gene_a.toUpperCase()} + ${gene_b.toUpperCase()}…`);try{state.results.pair=await api("/combination",{gene_a,gene_b});out.innerHTML=pairResult(state.results.pair);bindWorkspace()}catch(e){out.innerHTML=errorBox(e.message)}}
function parseDelimited(text){const lines=text.trim().split(/\r?\n/).filter(Boolean);const delimiter=lines[0].includes("\t")?"\t":",";const heads=lines[0].split(delimiter).map(x=>x.trim());return lines.slice(1).map(line=>Object.fromEntries(line.split(delimiter).map((x,i)=>[heads[i],x.trim()]))) }
async function runResearcher(){const rows=parseDelimited($("#signature-data").value),g=$("#col-gene").value,e=$("#col-effect").value,p=$("#col-p").value,f=$("#col-fdr").value,out=$("#researcher-output");const nullable=(v)=>v===""||v==null?null:Number(v);const body={genes:rows.map(r=>r[g]),values:rows.map(r=>Number(r[e])),p_values:p?rows.map(r=>nullable(r[p])):null,fdr_values:f?rows.map(r=>nullable(r[f])):null};out.innerHTML=loading("Building the processed result dossier…");try{state.results.researcher=await api("/signature",body);out.innerHTML=signatureResult(state.results.researcher);bindWorkspace()}catch(err){out.innerHTML=errorBox(err.message)}}
async function runComparison(){const genes=$("#gene-set").value.split(/[\s,]+/).filter(Boolean).slice(0,6),out=$("#comparison-output");out.innerHTML=loading(`Comparing ${genes.length} targets…`);try{state.results.comparison=await api("/profile/batch",{genes});out.innerHTML=comparisonResult(state.results.comparison);bindWorkspace()}catch(e){out.innerHTML=errorBox(e.message)}}
function downloadJSON(data){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));a.download="glia-research-dossier.json";a.click();URL.revokeObjectURL(a.href)}

async function sendGlia(message){
  const entry={role:"user",content:message,...(state.quote?{quote:state.quote.text,section:state.quote.section}:{})};
  state.messages.push(entry);
  state.memory.recent_questions=[...(state.memory.recent_questions||[]),message].slice(-8);
  state.memory.interaction_count=(state.memory.interaction_count||0)+1;
  state.quote=null;state.sending=true;persist();renderWorkspace();
  const context={active_workflow:current().name,profile:state.results.gene||null,pair:state.results.pair||null,signature:state.results.researcher||null,comparison_profiles:state.results.comparison?.results||null};
  try{
    const result=await api("/glia/chat",{message,history:state.messages.slice(-11,-1).map(x=>({role:x.role,content:x.content})),context,memory:state.memory,selected_quote:entry.quote||null,selected_section:entry.section||null});
    state.messages.push({role:"assistant",content:result.text,references:result.references,grounding_ok:result.grounding_ok});
  }catch(e){state.messages.push({role:"assistant",content:e.message,references:[]})}
  state.sending=false;persist();renderWorkspace();renderNav();
}
function archiveCurrent(){
  if(!state.messages.length)return;
  const first=state.messages.find(m=>m.role==="user")?.content||"Untitled research";
  state.archives.unshift({id:String(Date.now()),title:first.slice(0,58),messages:state.messages,updatedAt:new Date().toISOString()});
  state.archives=state.archives.slice(0,12);
}
function newResearch(){archiveCurrent();state.messages=[];state.quote=null;persist();switchView("research")}
function renderHistory(){
  const list=$("#thread-list");
  list.innerHTML=state.archives.length?state.archives.map(a=>`<button class="thread-item" data-thread="${esc(a.id)}" title="${esc(a.title)}">${esc(a.title)}</button>`).join(""):'<div class="empty-history">No saved research yet</div>';
  $$("[data-thread]",list).forEach(b=>b.onclick=()=>{archiveCurrent();const i=state.archives.findIndex(a=>a.id===b.dataset.thread);if(i<0)return;const [thread]=state.archives.splice(i,1);state.messages=thread.messages;persist();switchView("research")});
}

const tour=[
  ["01 · Deep Research","Start with the research question","Glia is the primary workspace. Ask it to interrogate evidence, compare alternatives, expose a failure mode, or design the next experiment.","Responses use the current research context, distinguish evidence from inference, and preserve source references."],
  ["02 · Research tools","Build structured evidence","Open a specialized tool from the sidebar or the composer. Gene, pair, researcher-data, gene-set, and methods workspaces use the validated V7 architecture.","Tool outputs remain available to Glia as structured context; scientific scoring semantics do not change."],
  ["03 · Context","Move between analysis and reasoning","Return to Deep Research after building evidence, or highlight any result and choose Ask Glia.","The selected passage and active structured analysis travel together into the conversation."],
  ["04 · Continuity","Continue the investigation","New research threads are saved in Recent research. Bounded research memory keeps investigated targets and recent questions available across visits.","Everything stays in this browser unless you clear it from Research memory."],
];let tourIndex=0;
function renderTour(){const t=tour[tourIndex];$("#walkthrough-step").innerHTML=`<small>${t[0]}</small><h2>${t[1]}</h2><p>${t[2]}</p><div class="walkthrough-preview">${t[3]}</div>`;$("#walkthrough-back").disabled=tourIndex===0;$("#walkthrough-next").textContent=tourIndex===tour.length-1?"Close":"Next"}
function openTour(){tourIndex=0;renderTour();$("#walkthrough").showModal()}

$("#new-research").onclick=newResearch;
$("#return-research").onclick=()=>switchView("research");
$("#mobile-menu").onclick=()=>{$("#sidebar").classList.add("open");$("#mobile-scrim").classList.add("visible")};
$("#mobile-scrim").onclick=()=>{$("#sidebar").classList.remove("open");$("#mobile-scrim").classList.remove("visible")};
$("#memory-button").onclick=()=>{
  $("#memory-summary").innerHTML=`<div><strong>${(state.memory.investigated_genes||[]).length}</strong><span>Investigated targets</span></div><div><strong>${state.memory.interaction_count||0}</strong><span>Research questions</span></div>`;
  $("#memory-dialog").showModal();
};
$$("[data-close-memory]").forEach(b=>b.onclick=()=>$("#memory-dialog").close());
$("#clear-memory").onclick=()=>{state.memory={investigated_genes:[],recent_questions:[],interaction_count:0};persist();$("#memory-dialog").close();$("#memory-status").textContent="Available"};
$$(".walkthrough-trigger").forEach(b=>b.onclick=openTour);
$("#close-walkthrough").onclick=()=>$("#walkthrough").close();
$("#walkthrough-back").onclick=()=>{tourIndex=Math.max(0,tourIndex-1);renderTour()};
$("#walkthrough-next").onclick=()=>{if(tourIndex===tour.length-1)$("#walkthrough").close();else{tourIndex++;renderTour()}};
$("#hide-walkthrough").onchange=e=>localStorage.setItem("glia.hideWalkthrough",e.target.checked?"1":"0");
document.addEventListener("mouseup",e=>{
  if(e.target.closest("input,textarea,button,dialog"))return;
  setTimeout(()=>{
    const sel=window.getSelection(),text=sel?.toString().trim(),action=$("#selection-action");
    if(text&&text.length>3&&text.length<1800){
      const rect=sel.getRangeAt(0).getBoundingClientRect();
      state.quote={text,section:current().name};
      action.style.left=Math.max(8,Math.min(innerWidth-85,rect.left+rect.width/2-36))+"px";
      action.style.top=Math.max(8,rect.top-39)+"px";
      action.classList.add("visible");
    }else action.classList.remove("visible");
  },0);
});
$("#selection-action").onclick=()=>{switchView("research");$("#selection-action").classList.remove("visible");setTimeout(()=>$("#glia-input")?.focus(),0)};
document.addEventListener("keydown",e=>{if(e.key==="Escape"){$("#tools-menu")?.classList.remove("open");$("#sidebar").classList.remove("open");$("#mobile-scrim").classList.remove("visible")}});
renderNav();renderWorkspace();
if(localStorage.getItem("glia.hideWalkthrough")!=="1")setTimeout(openTour,450);
