# GBM Evidence Dossier: EGFR

*Query: Evidence dossier for EGFR in glioblastoma*
*Generated: 2026-09-04T06:14:07.796366+00:00*
*Session ID: session_6e3d8233a57f*

## ⚠️ Scientific safeguards flagged
- Cross-cohort heterogeneity for EGFR survival association is high (I^2=79%) — cohorts disagree on effect size/direction enough that pooling them into one number would be misleading.
- EGFR: EGFR amplification is well documented to be rapidly lost during standard adherent (serum-containing) cell-line culture, and is far better preserved in xenografts, patient-derived spheroid/stem-cell cultures, or serum-free EGF-restricted conditions. A DepMap CRISPR dependency score for EGFR computed from long-established adherent GBM lines may therefore understate EGFR's true importance in EGFR-amplified patient tumors; cross-check against xenograft/PDX-based functional studies before concluding EGFR is 'not a dependency' in GBM.

## AI synthesis
*(grounding check: PASSED)*

Evidence dossier for EGFR: 22 records assembled across 10 sources.
EGFR amplification/high-expression status association with overall survival in TCGA_GBM (hazard_ratio=1.7, p=0.000622, n=300).
EGFR amplification/high-expression status association with overall survival in CGGA (hazard_ratio=0.89, p=0.389, n=350).
EGFR amplification/high-expression status association with overall survival in GLASS_recurrent (hazard_ratio=1.2, p=0.253, n=160).
Cross-cohort meta-analysis of EGFR survival association (random-effects model) (pooled_hazard_ratio=1.2, p=0.319, n=810).
EGFR expression varies across GBM anatomic/histologic zones; highest in pseudopalisading_cells_around_necrosis (H_statistic=72, p=1.92e-13, n=135).
EGFR dependency (CRISPR gene-effect score) in GBM-lineage lines vs. other lineages: median -0.18 vs -0.05 (U_statistic=1e+04, p=0.00324, n=884).
Note — evidence does not agree across cohorts:
  * EGFR survival association is significant in some cohorts but not others (computed in this session on calibrated demo data): TCGA_GBM: HR=1.65, p=0.001, n=300; CGGA: HR=0.89, p=0.389, n=350; GLASS_recurrent: HR=1.24, p=0.253, n=160
  * CONFLICTING/HETEROGENEOUS EVIDENCE: the same meta-analysis found strong regional heterogeneity in EGFR amplification's prognostic value — American cohorts showed a much stronger, clearly significant association (HR = 1.53, 95% CI 1.28 to 1.84, p = 0.001), while other geographic regions did not show a significant prognostic effect. A researcher who only checks a single cohort (commonly TCGA, which is American) risks concluding EGFR amplification is a universally reliable prognostic marker when the evidence is materially region/cohort-dependent.
  * CONFLICTING EVIDENCE: EGFRvIII's prognostic value across the general GBM population was inconclusive in the same meta-analysis (pooled HR = 1.13, 95% CI 0.94 to 1.36, not significant), but a subgroup analysis suggested EGFRvIII becomes more clearly associated with worse outcomes specifically in recurrent GBM.
Literature: Temozolomide: Standard-of-care GBM alkylating agent; well-established CNS/CSF penetration. [Standard GBM pharmacology literature; well documented CNS penetration used to justify its role as first-line GBM chemotherapy.]
Literature: Osimertinib: Third-generation EGFR-TKI with high reported CNS penetration; under evaluation against EGFRvIII+ GBM models. [Chagoya et al., Oncotarget 2020 (PMC7275784); Tsang et al., ACS Med Chem Lett 2020 (JCN037 paper, discussing osimertinib CNS penetration).]
Literature: Erlotinib: First-generation EGFR-TKI; repeatedly implicated in clinical GBM trial failures attributed in part to poor brain penetration. [PMC6380895; PMC7275784; PMC7086303 — all describe erlotinib as poorly brain-penetrant in the GBM clinical-failure literature.]
Suggested follow-up (AI inference, not evidence): Given documented in-vitro instability of EGFR gene amplification / EGFRvIII, prioritize validating EGFR-targeted compounds in patient-derived xenograft or serum-free spheroid models over long-established adherent cell lines.
Scientific safeguards flagged: Cross-cohort heterogeneity for EGFR survival association is high (I^2=79%) — cohorts disagree on effect size/direction enough that pooling them into one number would be misleading.; EGFR: EGFR amplification is well documented to be rapidly lost during standard adherent (serum-containing) cell-line culture, and is far better preserved in xenografts, patient-derived spheroid/stem-cell cultures, or serum-free EGF-restricted conditions. A DepMap CRISPR dependency score for EGFR computed from long-established adherent GBM lines may therefore understate EGFR's true importance in EGFR-amplified patient tumors; cross-check against xenograft/PDX-based functional studies before concluding EGFR is 'not a dependency' in GBM.

## Evidence tier: statistical_association
### EGFR amplification/high-expression status association with overall survival in TCGA_GBM
- **Statistics:** hazard_ratio=1.6503469430689475, p=0.000622, 95% CI [1.24, 2.2]
- **Source:** cBioPortal (TCGA-GBM and other public studies) (synthetic_illustrative) — access: synthetic_illustrative
- **n:** 300
- **Method:** Cox proportional hazards (Efron ties correction), adjusted for age
- **Citation:** Public studies are CC0/open for research use; no API key needed.
- **Confidence:** moderate

### EGFR amplification/high-expression status association with overall survival in CGGA
- **Statistics:** hazard_ratio=0.8911177032862995, p=0.389, 95% CI [0.686, 1.16]
- **Source:** Chinese Glioma Genome Atlas (synthetic_illustrative) — access: synthetic_illustrative
- **n:** 350
- **Method:** Cox proportional hazards (Efron ties correction), adjusted for age
- **Citation:** Free for academic research after registration; do not re-host raw matrices.
- **Confidence:** moderate

### EGFR amplification/high-expression status association with overall survival in GLASS_recurrent
- **Statistics:** hazard_ratio=1.2408078431907545, p=0.253, 95% CI [0.857, 1.8]
- **Source:** GLASS Consortium (Glioma Longitudinal AnalySiS) (synthetic_illustrative) — access: synthetic_illustrative
- **n:** 160
- **Method:** Cox proportional hazards (Efron ties correction), adjusted for age
- **Citation:** Open research-use data once registered; do not re-host raw matrices.
- **Confidence:** moderate

### Cross-cohort meta-analysis of EGFR survival association (random-effects model)
- **Statistics:** pooled_hazard_ratio=1.2170485087864042, p=0.319, 95% CI [0.827, 1.79]
- **Source:** Pooled: TCGA_GBM, CGGA, GLASS_recurrent (computed in this session) — access: synthetic_illustrative
- **n:** 810
- **Method:** Inverse-variance meta-analysis; DerSimonian-Laird random-effects if I^2 > 50%
- **Confidence:** low
- ⚠️ **Caveat:** High cross-cohort heterogeneity (I^2=79%) — do NOT treat the pooled estimate as a single reliable number; report per-cohort results separately.

### EGFR expression varies across GBM anatomic/histologic zones; highest in pseudopalisading_cells_around_necrosis
- **Statistics:** H_statistic=71.59899724328596, p=1.92e-13
- **Source:** Ivy Glioblastoma Atlas Project (SYNTHETIC demo snapshot (see data/README.md) — not the real Ivy GAP release) — access: synthetic_illustrative
- **n:** 135
- **Method:** Kruskal-Wallis H-test across 7 laser-microdissected anatomic zones
- **Confidence:** moderate
- ⚠️ **Caveat:** Demo run on SYNTHETIC calibrated zone data, not the real Ivy GAP release — see data/README.md. Do not treat 'top_zone' as a real biological claim about this gene.

### EGFR dependency (CRISPR gene-effect score) in GBM-lineage lines vs. other lineages: median -0.18 vs -0.05
- **Statistics:** U_statistic=10475.0, p=0.00324
- **Source:** DepMap (CRISPR gene-effect scores, public release) (SYNTHETIC demo snapshot (see data/README.md) — not a real DepMap release) — access: synthetic_illustrative
- **n:** 884
- **Method:** One-sided Mann-Whitney U test (GBM more dependent), rank-biserial effect size
- **Confidence:** low
- ⚠️ **Caveat:** EGFR amplification is well documented to be rapidly lost during standard adherent (serum-containing) cell-line culture, and is far better preserved in xenografts, patient-derived spheroid/stem-cell cultures, or serum-free EGF-restricted conditions. A DepMap CRISPR dependency score for EGFR computed from long-established adherent GBM lines may therefore understate EGFR's true importance in EGFR-amplified patient tumors; cross-check against xenograft/PDX-based functional studies before concluding EGFR is 'not a dependency' in GBM.

## Evidence tier: literature_supported_claim
### Temozolomide: Standard-of-care GBM alkylating agent; well-established CNS/CSF penetration.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** Standard GBM pharmacology literature; well documented CNS penetration used to justify its role as first-line GBM chemotherapy.
- **Confidence:** moderate

### Osimertinib: Third-generation EGFR-TKI with high reported CNS penetration; under evaluation against EGFRvIII+ GBM models.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** Chagoya et al., Oncotarget 2020 (PMC7275784); Tsang et al., ACS Med Chem Lett 2020 (JCN037 paper, discussing osimertinib CNS penetration).
- **Confidence:** moderate

### Erlotinib: First-generation EGFR-TKI; repeatedly implicated in clinical GBM trial failures attributed in part to poor brain penetration.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** PMC6380895; PMC7275784; PMC7086303 — all describe erlotinib as poorly brain-penetrant in the GBM clinical-failure literature.
- **Confidence:** moderate

### Gefitinib: First-generation EGFR-TKI; same poor-brain-penetration pattern as erlotinib in GBM trial-failure literature.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** PMC6380895; PMC7275784.
- **Confidence:** moderate

### Lapatinib: Dual EGFR/HER2 TKI; included among agents cited for poor GBM brain penetration.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** PMC6380895; PMC7275784.
- **Confidence:** moderate

### Afatinib: Irreversible EGFR-TKI; some preclinical brain-penetrant activity reported (BTSC models) but clinical GBM trials still criticized for inadequate confirmation of brain exposure.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** PMC7086303 (afatinib decreases BTSC growth in vitro/in vivo); PMC6380895 (afatinib GBM trial critiqued for not confirming brain exposure).
- **Confidence:** moderate

### JCN037: Purpose-built brain-penetrant EGFR TKI (research compound, not yet approved) designed specifically to address the brain-exposure failures of first-generation EGFR-TKIs in GBM.
- **Source:** B3DB blood-brain barrier permeability database (hand-curated real subset, see data/README.md) — access: open_bulk_download
- **Citation:** Tsang et al., ACS Med Chem Lett 2020 (chem.ucla.edu/~jung/pdfs/366.pdf).
- **Confidence:** moderate

### EGFR gene amplification is present in roughly 40 to 60% of primary (IDH-wildtype) glioblastomas.
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** Multiple concordant reports, e.g. PMC9844636 (23.9%-50% range across cohorts, NGS-detected 40-50%); s11010-022-04435-y ("almost 60% of primary GBM"); classic astrocytic-glioma cohort study s00109-005-0700-2 (41% of 160 GBM by Southern blot/qPCR).
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9844636/
- **Confidence:** high

### EGFRvIII (the constitutively active exon 2 to 7 deletion variant) is found in roughly a fifth to a quarter of all GBM, and in about half of EGFR-amplified tumors.
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** PMC9844636 (EGFRvIII positivity in 21% of EGFR-amplified GBM); PMC7275784 / scholars.duke.edu 1448361 ("occurs in over 20% of GBMs"); s00109-005-0700-2 (EGFRvIII in 54% of amplified GBM in a 160-patient cohort).
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9844636/
- **Confidence:** high

### A 2024/2025 systematic review and meta-analysis of 32 studies (4,208 GBM patients) found EGFR amplification significantly associated with worse overall survival, pooled HR = 1.27 (95% CI 1.03 to 1.57).
- **Statistics:** hazard_ratio=1.27, 95% CI [1.03, 1.57]
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **n:** 4208
- **Citation:** PMC12027172 (systematic review and meta-analysis, EGFR amplification and EGFRvIII prognostic significance in GBM).
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12027172/
- **Confidence:** high

### Multiple independent clinical trials of first- and second-generation EGFR tyrosine kinase inhibitors (erlotinib, gefitinib, lapatinib, afatinib) failed to show efficacy in GBM; a recurring explanation across the literature is that these agents have poor blood-brain-barrier penetration, compounded in some trials by not stratifying patients by EGFR/EGFRvIII activation status.
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** PMC6380895 (explicit critique of trial design flaws: unselected patients + poor brain penetration); PMC7275784 (osimertinib rationale explicitly cites poor BBB penetration of afatinib/erlotinib/gefitinib/lapatinib); PMC7086303 (same conclusion, proposes afatinib+pacritinib combination).
- **Link:** https://pmc.ncbi.nlm.nih.gov/articles/PMC6380895
- **Confidence:** high

### GBM cell lines are well documented to rapidly lose EGFR gene amplification during standard adherent (serum-containing) culture, a phenomenon first reported in 1990 and repeatedly confirmed since; amplification is much better preserved in xenografts and in serum-free spheroid/stem-cell culture. This is a documented reason to treat cell-line-based dependency screens (e.g. DepMap) for EGFR with caution.
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** Bigner et al., Cancer Res 1990 (scholars.duke.edu/publication/675273); PMC5608330 (EGFR amplification maintained only under serum-free, EGF-modulated conditions); PMC4468289 (review of EGFR amplification loss in conventional GBM cell lines vs. preservation in GS-cells).
- **Link:** https://scholars.duke.edu/publication/675273
- **Confidence:** high

## Evidence tier: conflicting_evidence
### EGFR survival association is significant in some cohorts but not others (computed in this session on calibrated demo data): TCGA_GBM: HR=1.65, p=0.001, n=300; CGGA: HR=0.89, p=0.389, n=350; GLASS_recurrent: HR=1.24, p=0.253, n=160
- **Source:** Cross-cohort comparison (this session) (computed) — access: synthetic_illustrative
- **Method:** Direct comparison of per-cohort Cox p-values at alpha=0.05
- **Confidence:** moderate

### CONFLICTING/HETEROGENEOUS EVIDENCE: the same meta-analysis found strong regional heterogeneity in EGFR amplification's prognostic value — American cohorts showed a much stronger, clearly significant association (HR = 1.53, 95% CI 1.28 to 1.84, p = 0.001), while other geographic regions did not show a significant prognostic effect. A researcher who only checks a single cohort (commonly TCGA, which is American) risks concluding EGFR amplification is a universally reliable prognostic marker when the evidence is materially region/cohort-dependent.
- **Statistics:** hazard_ratio=1.53, p=0.001, 95% CI [1.28, 1.84]
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** PMC12027172.
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12027172/
- **Confidence:** high

### CONFLICTING EVIDENCE: EGFRvIII's prognostic value across the general GBM population was inconclusive in the same meta-analysis (pooled HR = 1.13, 95% CI 0.94 to 1.36, not significant), but a subgroup analysis suggested EGFRvIII becomes more clearly associated with worse outcomes specifically in recurrent GBM.
- **Statistics:** hazard_ratio=1.13, 95% CI [0.94, 1.36]
- **Source:** Literature (Europe PMC-indexed sources, retrieved via live web search this session) (see source_urls) — access: open_live_api
- **Citation:** PMC12027172.
- **Link:** https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12027172/
- **Confidence:** high

## Evidence tier: ai_generated_inference
### Given documented in-vitro instability of EGFR gene amplification / EGFRvIII, prioritize validating EGFR-targeted compounds in patient-derived xenograft or serum-free spheroid models over long-established adherent cell lines.
- **Source:** AI synthesis layer (this session) (n/a) — access: synthetic_illustrative
- **Method:** Rule-triggered suggestion: culture-instability flag present for this gene
- **Confidence:** low
