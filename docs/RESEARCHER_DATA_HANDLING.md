# Researcher Data Handling

GBM Gene Analysis accepts **processed gene-level research results** for the Researcher Data workflow. It is not designed to ingest raw sequencing files, imaging data, clinical records, or identifiable patient data.

## What the application accepts

Supported researcher inputs are tabular, gene-level results such as:

- gene symbol;
- signed effect size (for example log2 fold-change, model coefficient, or differential CRISPR effect);
- optional p-value;
- optional FDR/q-value.

The application parses uploaded CSV/TSV content in the running application process and uses those values to build the requested research dossier. The application code does **not** write uploaded tables to this repository, the bundled `data/` directory, or an application database.

## What researchers should not upload

Do not upload:

- names, medical-record numbers, dates of birth, addresses, or other direct identifiers;
- protected health information (PHI) or personally identifiable information (PII);
- raw or patient-level genomic data subject to a data-use agreement;
- controlled-access datasets unless the deployment has been specifically approved for that use;
- secrets, API tokens, credentials, or unpublished confidential material that cannot be processed by the deployment host.

Use de-identified, processed gene-level summaries whenever possible.

## Research Assistant boundary

The Research Assistant does not receive the raw uploaded or pasted researcher table. If a researcher asks the assistant to inspect the current Researcher Data analysis, the application sends only the derived result-dossier context needed for that question, such as prioritized genes, pathway results, perturbational-reversal results, and summary counts. The message and retrieved derived context are processed through the configured OpenAI API deployment and are therefore subject to that deployment's applicable data controls and retention settings. Do not use the assistant with PHI, identifiable patient information, controlled raw genomic data, credentials, or restricted material that is not approved for that environment.

## Hosting and retention boundary

The repository itself does not implement persistent storage for researcher uploads. However, a deployed copy runs on third-party infrastructure. Uploaded content is therefore processed by the host environment and may be subject to that provider's infrastructure, logging, security, and retention policies. Researchers should review the policies of the specific deployment before submitting sensitive or restricted information.

## Local/private deployment

For restricted research data, use a controlled local or institutional deployment and confirm that the environment meets the applicable IRB, data-use agreement, institutional security, and privacy requirements.

## Scope

The Researcher Data workflow is intended for molecular research prioritization and hypothesis development. It does not provide clinical recommendations and should not be used to make patient-care decisions.
