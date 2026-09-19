# Tableau package

**Status: no Tableau workbook has been built or published. There is no `.twb`, no `.twbx` and no Tableau Public URL in this repository, so nothing here claims a Tableau dashboard.** The reproducible BI artifact today is the offline HTML dashboard in [`../dashboard/`](../dashboard/index.html) and the Excel workbook in [`../excel/`](../excel/).

This folder prepares everything needed to build the workbook, and to check it once built:

| File | Purpose |
|---|---|
| `data/*.csv` | Aggregated extracts generated from the DuckDB marts by `medicare-claims tableau` (no beneficiary rows) |
| `field_dictionary.md` | Generated dictionary of every field in every extract |
| `calculated_fields.md` | Version-controlled Tableau calculated fields and parameters |
| `build_guide.md` | Five pages, filters, actions and tooltips to build |
| `expected_kpis.csv` | Values each KPI worksheet must reproduce |
| `qa_checklist.md` | Checks to complete before any Tableau claim |

Hyper extracts are not produced (the Tableau Hyper API is not a dependency). Connect to the CSVs; Tableau creates its own extract.

## Manual checkpoint (Vijay)

1. Open Tableau Desktop or Tableau Public on macOS and connect the CSVs in `data/`.
2. Build the five pages from `build_guide.md` using the fields in `calculated_fields.md`.
3. Compare every KPI with `expected_kpis.csv` and complete `qa_checklist.md`.
4. Save the workbook as `.twbx` in this folder, or publish to Tableau Public.
5. Only then add the workbook path or public URL to this README and update the main README to say a Tableau dashboard exists. Until then, do not claim one.
