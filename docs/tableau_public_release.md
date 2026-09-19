# Tableau Public release checklist

> CMS synthetic claims - not real patient or provider performance.

Status: **Tableau package prepared; workbook generated and load-checked in Tableau Public 2026.2.2; visual QA and publication not yet verified.** Until the steps below are complete, no document may call this a published Tableau dashboard.

## Release steps (manual, Vijay)

1. `make all` (or `uv run python -m medicare_claims tableau`) to regenerate `tableau/data`, `tableau/workbook/medicare_claims_bi.twbx`, `expected_kpis.csv` and `validation_evidence.csv`. Every row of the evidence file must say `True`.
2. Open the `.twbx` in Tableau Public (File > Open). It must open with no error dialog.
3. Complete `tableau/qa_checklist.md` for all five dashboards, including every KPI tile against `expected_kpis.csv` for 2008, 2009 and 2010.
4. Sign in to Tableau Public and publish (File > Save to Tableau Public As) with the title **Medicare Claims Utilization, Payment & Quality Analytics | CMS DE-SynPUF**.
5. Copy the exact Tableau Public URL into `README.md` and `tableau/README.md`.
6. Capture one screenshot per dashboard from Tableau into `tableau/screenshots/`.
7. Rerun `make test` and commit the URL, screenshots and completed checklist.

## Known Tableau Public limitations

- Tableau Public requires extracts; the workbook ships Hyper extracts built from the governed CSVs.
- Everything published is public. Only aggregated extracts and synthetic provider IDs are included; tests fail on any beneficiary or claim identifier.
- Tableau Public has no image or PDF export in the desktop app, so screenshots are screen captures.
- The published workbook is a snapshot. A refresh means regenerating and republishing it.
- Phone layouts are generated automatically by Tableau; the fixed 1366 x 768 desktop layout is the tested one.
