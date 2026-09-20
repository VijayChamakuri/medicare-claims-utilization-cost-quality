# Build guide

The workbook is not built by hand. `uv run python -m medicare_claims tableau` (part of `make all`):

1. Builds the governed extracts from the DuckDB marts (`src/medicare_claims/tableau.py`, `extracts`) and rejects any extract with a beneficiary or claim identifier.
2. Writes the workbook XML from the specification in `build_workbook`: 15 data sources, one Year parameter, 31 worksheets, five dashboards at 1366 x 768 and one filter action.
3. Builds one Hyper extract per data source with the Tableau Hyper API and packages them with the workbook as `workbook/medicare_claims_bi.twbx`.
4. Writes `workbook_manifest.yml`, `calculated_fields.md`, `field_dictionary.md` and `expected_kpis.csv`.
5. Reopens the packaged kpi_annual Hyper extract and ties every expected KPI to it (`validation_evidence.csv`).

To change a view, edit `build_workbook` and rerun; do not edit the `.twbx` in Tableau and commit it, because the next run overwrites it.

## Opening and checking

Open the `.twbx` in Tableau Public 2026.2.2 or later (File > Open). The load was checked by launching Tableau with the file and reading Tableau's own log for schema or load errors (none). Then follow `qa_checklist.md`.
