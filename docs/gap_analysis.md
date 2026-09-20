# Gap analysis

> CMS synthetic claims - not real patient or provider performance.

As-is is the manual process in [process_map.md](process_map.md); to-be is what this repository does today. Every number comes from a committed artifact. Where nothing was measured, the row says "not measured" instead of estimating a benefit.

| Area | As-is (manual process) | To-be (this repository) | Measured delta | Evidence |
|---|---|---|---|---|
| Source integrity | Files downloaded by hand, no version recorded | URL, retrieval date, byte size and SHA-256 recorded for every file; a changed file stops the run | 10 source files pinned and verified per run | `data/data_manifest.json`, `tests/test_download.py::test_a_changed_source_file_stops_the_run_until_refreshed` |
| Claim grain | Claim segments and duplicate rows counted more than once | Segments merged into one claim, exact duplicates dropped once | 5,587,855 claims at a tested grain | `docs/table_inventory.md`, `tests/test_claim_grain.py::test_header_has_one_row_per_claim_and_segments_are_merged` |
| Definitions | Each analyst carries their own definition | One versioned contract generates the dictionary, the Excel sheet and the Tableau fields | 17 KPIs with owner, grain, numerator, denominator, inclusions, exclusions, quality checks and known limits | `config/metric_dictionary.yml`, `tests/test_metric_contract.py::test_every_metric_has_every_required_field` |
| Release control | Numbers reach slides before anyone checks them | Blocking reconciliation stops the pipeline; informational tie-outs never block | 41 checks per build; every blocking check passes on sample 1; 8 informational MEDREIMB tie-outs differ by design | `reports/data_quality_report.md`, `reports/runtime_verification.md` |
| Second opinion | None | Independent pandas recomputation from the raw files, sharing no SQL | 42 of 42 checks agree; money to the cent | `reports/independent_reconciliation.csv` |
| Transformation layer | Ad hoc queries | dbt models generated from the validated SQL, with grain, key, relationship and reconciliation tests | 35 models match the legacy tables row for row; 100 dbt tests | `reports/dbt_equivalence.csv` |
| Offline reporting | Copy-paste spreadsheet roll-up | Generated workbook whose totals tie to the warehouse and whose executive summary prints | 6,514 formulas recalculated with no errors, 10 of 10 ties pass; 2-page executive PDF | `reports/runtime_verification.md`, `reports/claims_executive_summary.pdf` |
| BI delivery | Static slides without lineage | Published Tableau workbook generated from the governed marts | 5 dashboards; 30 of 30 packaged KPI values tie to the marts | `tableau/validation_evidence.csv`, `tableau/README.md` |
| Disclosure control | Row-level extracts shared casually | Aggregates only, with a guard that fails the build on any beneficiary or claim identifier | 0 identifiers in any export or extract | `tests/test_tableau_package.py::test_no_published_extract_contains_a_beneficiary_or_claim_identifier` |
| Documentation drift | Numbers in documents age silently | README numbers are generated and drift-checked in CI | README matches `reports/headline_kpis.json` on every run | `tests/test_readme.py`, `Makefile` target `check-readme` |
| Analyst time to answer a question | Not measured | Not measured | Not measured | No timing was recorded; this project does not estimate time savings |
| Financial impact | Not measured | Not measured | Not measured | Synthetic data cannot support a savings or ROI claim ([limitations](limitations.md)) |

## Remaining gaps

- The ED visit and readmission measures stay proxies: DE-SynPUF has no revenue center, place of service, discharge status or planned-readmission flag.
- Provider review flags mostly track facility size on this data; payment-per-claim flags are rare because CMS synthesized payments in a narrow range.
- Monthly volume tapers from mid-2009, so no trend can be read from the series.
- Phone layouts for the Tableau workbook are not reviewed; the 1366 x 768 desktop layout is the tested one.
