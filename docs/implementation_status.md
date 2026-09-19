# Implementation status

Each acceptance criterion, the evidence that supports it, and the honest gaps. Commands and results are recorded in [`reports/runtime_verification.md`](../reports/runtime_verification.md).

| Criterion | Status | Evidence |
|---|---|---|
| Fresh clone runs the fixture pipeline with one documented command | Met | `make fixture` (README, Reproduce). Verified from a fresh clone; see runtime verification. |
| CMS URLs, file names, hashes, retrieval date and codebook version recorded | Met | [`data/data_manifest.json`](../data/data_manifest.json) holds URL, retrieval date, byte size, SHA-256 and zip members for every file, the codebook and the FAQ. `download.py` stops on a changed hash; `tests/test_download.py`. Reference file hashes in [`reference/README.md`](../reference/README.md). |
| Documented grain and passing key tests for every warehouse table | Met | [`table_inventory.md`](table_inventory.md) (generated, with row counts) and the `keys` category of `sql/08_reconciliation.sql` (10 of 10 pass on sample 1); `tests/test_reconciliation.py`. |
| Beneficiary, claims, provider, utilization, payment and quality marts generated | Met | `sql/04` to `sql/07`; row counts in the table inventory. |
| At least one official sample processes end to end | Met | CMS DE-SynPUF sample 1 (5,587,855 claims, 64,359 inpatient stays): download, verify, build, validate, export, Excel, reports, Tableau extracts, dashboard, in about 2 minutes once files are cached. |
| Every headline KPI has exact fixture coverage | Met | `tests/test_fixture_kpis.py` asserts every KPI in `tests/fixtures/expected_kpis.json` exactly. Values were derived by hand in [`tests/fixtures/README.md`](../tests/fixtures/README.md) before the pipeline ran. |
| Independent reconciliation passes within documented tolerance | Met | `validation.py` recomputes claims, payments, admissions, ED proxy, readmission proxy and concentration in pandas without SQL: 42 of 42 checks agree on sample 1 ([`reports/independent_reconciliation.csv`](../reports/independent_reconciliation.csv)). Money tolerance is half a cent; counts are exact. Tamper tests prove the checks can fail. |
| Nine-sheet Excel workbook reconciles to marts; executive PDF readable | Met | [`excel/claims_operations_review.xlsx`](../excel/claims_operations_review.xlsx): 9 sheets, live formulas, Reconciliation sheet. Recalculated with an independent formula engine: 6,514 formulas, no errors, all 10 ties PASS. `tests/test_excel.py` ties workbook values to DuckDB and checks print settings. `reports/claims_executive_summary.pdf` is two readable landscape pages; the full-workbook PDF fell from 312 to 165 pages with no horizontal pagination. |
| Offline HTML dashboard (secondary demo) | Met | [`dashboard/index.html`](../dashboard/index.html) (one file, five pages) and five captured screenshots in `dashboard/screenshots/`, each inspected for labels, clipping, color, filters and the synthetic banner. `tests/test_dashboard.py`. |
| Real Tableau workbook with five checked dashboards and a Tableau Public URL | **Not complete** | `tableau/workbook/medicare_claims_bi.twbx` is generated from code with Hyper extracts; it opens in Tableau Public 2026.2.2 with no errors, and 30 of 30 KPI values in its extract tie to the marts. The Executive Overview was inspected on real data in Tableau. Pixel QA of the other four dashboards, Tableau screenshots and publication are the manual checkpoint in `docs/tableau_public_release.md`. **Tableau package prepared; workbook and publication not verified.** |
| Synthetic and nonproduction caveats in README, dashboard, workbook and report | Met | README banner, red dashboard banner on every page, banner rows on every workbook sheet, banner in every generated report. Asserted in `test_dashboard.py`, `test_excel.py`. |
| No claim of real outcomes, official HEDIS, official CMS-HCC, Epic, fraud detection or HIPAA compliance | Met | Final term audit recorded in runtime verification. Each remaining occurrence is a negation or a limitation statement. |
| CI passes on Python 3.11 and 3.12 | See runtime verification | `.github/workflows/ci.yml`: Ruff, mypy, pytest with coverage, fixture end-to-end run, README drift, on both versions. A scheduled job runs the official link check and the real-data pipeline. Result of the first hosted run is recorded in runtime verification. |

## Known gaps and limits

- No Tableau workbook (manual checkpoint).
- Monthly volume in the synthetic source tapers from mid-2009, so trends and the year-to-year readmission proxy are not interpretable.
- ED visit and readmission are proxies: the data has no place of service, revenue center, discharge status or planned-readmission flag.
- Provider review flags mostly track facility size on this data; payment-per-claim flags are rare because CMS synthesized payments in a narrow range.
- Eight informational tie-outs of beneficiary-summary reimbursement fields to claim payments differ by 0.2 to 8.6 percent. Those fields are not used in any metric.
- Prescription drug events are not loaded.
- The workbook stores formulas without cached results; Excel and LibreOffice calculate them when opened, but a file previewer may show blanks.
| dbt build and tests pass on the fixture warehouse | Met | 100 of 100 dbt tests (`make fixture-all`, CI). |
| dbt and legacy marts match on rows, keys and headline KPIs | Met | 35 of 35 models identical row for row and 7 of 7 KPIs on the fixture and on sample 1 (`reports/dbt_equivalence.csv`, `reports/dbt_kpi_equivalence.csv`). The legacy runner stays the default path. |
| Canonical metric contract generates downstream definitions without drift | Met | `config/metric_dictionary.yml` (17 KPIs, full field set, versioned); `tests/test_metric_contract.py`. |
| Published Tableau data are aggregated with no beneficiary-level identifier | Met | Extract guard in `tableau.py` plus `tests/test_tableau_package.py`. |
| Payment, not cost, in titles and payment metrics | Met | README H1, dashboard title, workbook title; tests fail on "cost" labels. The repository slug is unchanged to keep links working. |
| Interview prep in the repository | Not in scope | Removed at the owner's request; not a public artifact. |
