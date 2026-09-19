# BI upgrade verification

> CMS synthetic claims - not real patient or provider performance.

Starting commit: `aa919dd797a92182bb587b5d33ddc4667bcdd6ae` (main, 2026-09-19). Environment: macOS on Apple silicon, Python 3.12, DuckDB 1.5.5, dbt-core 1.12.5 with dbt-duckdb 1.11.0, Tableau Hyper API, LibreOffice 26 for PDF export, Tableau Public 2026.2.2.

| Command | Result |
|---|---|
| `make fixture-all` | fixture build 41 of 41 reconciliation checks; dbt 100 of 100 tests; 35 of 35 models and 7 of 7 KPIs match legacy |
| `make all` (sample 1, 4 minutes) | 10 files hash-verified; 33 of 41 reconciliation checks (every blocking check passes; 8 informational MEDREIMB tie-outs differ by design); dbt 100 of 100 tests; 35 of 35 models identical to legacy; 7 of 7 KPIs; 42 of 42 independent pandas checks; Excel, PDF, reports, Tableau package, dashboard regenerated |
| `uv run pytest` | 100 passed |
| `ruff check`, `mypy` | pass |
| `medicare-claims readme --check` | README matches `reports/headline_kpis.json` |
| Formula engine on `excel/claims_operations_review.xlsx` | 6,514 formulas, 0 errors, 10 of 10 ties PASS |
| Tableau Hyper tie-out (`tableau/validation_evidence.csv`) | 30 of 30 KPI values match |
| Tableau load check (launch Tableau Public with the `.twbx`, read Tableau's log) | opened, 0 errors |

## Defects found and fixed during the upgrade

- The new dbt grain test found that missing, invalid-format and valid-but-unmapped primary diagnoses shared `condition_id = 'unmapped'`, breaking the condition summary's key. Each now has its own ID; the fixture expectation label changed, the hand-derived count and amount did not.
- The Excel CHECK highlight pointed at the wrong column.
- The executive sheet printed unreadably small and dropped the "&" in the header.

## Not verified yet

- **Tableau package prepared; workbook and publication not verified.** Visual QA of four dashboards, Tableau screenshots and the Tableau Public URL wait on the manual checkpoint (`docs/tableau_public_release.md`).
- Excel open-in-Excel check at 100% zoom.
- Hosted CI result for the final commit is recorded in the pull request.
