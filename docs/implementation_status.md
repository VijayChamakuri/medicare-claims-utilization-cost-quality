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
| Nine-sheet Excel workbook reconciles to marts | Met | [`excel/claims_operations_review.xlsx`](../excel/claims_operations_review.xlsx): 9 sheets, live formulas, Reconciliation sheet. Recalculated with an independent formula engine: 6,514 formulas, no errors, all 10 ties PASS. `tests/test_excel.py` ties workbook values to DuckDB. |
| Offline dashboard exists and is visually checked | Met | [`dashboard/index.html`](../dashboard/index.html) (one file, five pages) and five captured screenshots in `dashboard/screenshots/`, each inspected for labels, clipping, color, filters and the synthetic banner. `tests/test_dashboard.py`. |
| Tableau package exists; Tableau claim only with a real workbook or Public URL | Package met; workbook not built | [`tableau/`](../tableau/README.md) has extracts, field dictionary, calculated fields, build guide, expected KPIs and QA checklist. **No workbook or URL exists, and no document claims one.** Manual checkpoint for Vijay is in `tableau/README.md`. |
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
