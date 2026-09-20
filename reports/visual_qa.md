# Visual QA

> CMS synthetic claims - not real patient or provider performance.

Actual pixels inspected, with viewport, artifact, date, issue and disposition. Automated checks do not replace this review.

| Date | Artifact | Viewport | Issue found | Disposition |
|---|---|---|---|---|
| 2026-09-19 | Tableau Executive Overview (real sample 1), Tableau Public 2026.2.2 | Presentation mode, about 1366 x 768 | Axis title read "Month of Month" | Fixed: caption "Service date" |
| 2026-09-19 | Tableau Executive Overview | Same | Setting colors were Tableau defaults; no legend | Legend added; default palette kept (consistent across sheets) |
| 2026-09-19 | Tableau Executive Overview | Same | KPI title "30-day readmission proxy" wrapped and pushed the value down | Fixed: shorter title |
| 2026-09-19 | Tableau Executive Overview | Same | After fixes: tiles match 2009 pipeline values; banner, source and refresh visible; no clipping | Pass |
| 2026-09-19 | Tableau, all five dashboards | Presentation mode on a 2560 x 1440 display | Scatter, peer filter and legend missing (text field in a tooltip without ATTR) | Fixed |
| 2026-09-19 | Tableau Utilization & Payment | Same | Paid-per-sex ratios were stacked; tiers sorted alphabetically; raw field name as header | Fixed: side-by-side bars, value sort, captions |
| 2026-09-19 | Tableau, all dashboards | Same | Tableau ignored proportional zone sizes: KPI values hidden, tables crushed, controls too wide | Fixed: zones now carry fixed pixel sizes |
| 2026-09-19 | Tableau Quality & Cohorts, Data Quality & Definitions | Same | Four counts stacked in one cell; bar chart too short; legend wording wrong | Fixed: long-format table, resized rows, corrected title |
| 2026-09-19 | Tableau, all five dashboards (final) | Same | No clipping, readable tables and legends, banner and source on every page | Pass; screenshots in `tableau/screenshots/`; published |
| 2026-09-19 | `reports/claims_executive_summary.pdf` (real sample) | Letter landscape, 75 dpi render | First draft: 19 columns on one page were unreadable; headers split mid-word; "&" dropped from header; page 2 repeated clipped column A text | Fixed: two pages at a column break, spaced headers, `&&` escape, Year column at the start of page 2. Final: 2 readable pages, no clipping |
| 2026-09-19 | Excel full-workbook PDF export (LibreOffice) | Letter landscape | Previously 312 pages with horizontal pagination | Now 165 pages, one page wide; length is detail rows (provider review list) |
| 2026-09-19 | Excel workbook at 100% zoom | Not captured in this pass | Values and formulas verified by tests and the formula engine | **Open**: open in Excel or LibreOffice and review key sheets |
| 2026-09-19 | README screenshot | GitHub width | Now the Tableau Executive Overview | Pass |
