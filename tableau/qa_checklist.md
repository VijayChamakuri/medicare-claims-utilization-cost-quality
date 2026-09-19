# Tableau QA checklist

> CMS synthetic claims - not real patient or provider performance.

Complete in Tableau before any document calls this a published Tableau dashboard. Record each result.

| Field | Value |
|---|---|
| Tableau version | |
| Tester | |
| Date | |
| Workbook commit | |

| # | Check | Result (pass/fail) | Notes |
|---|---|---|---|
| 1 | Workbook opens with no error dialog and no missing data source | | Automated load check: pass, Tableau Public 2026.2.2, 2026-09-19 (log shows no errors) |
| 2 | Every KPI tile matches `expected_kpis.csv` for 2008, 2009 and 2010 (switch the Year control) | | Extract tie-out: 30 of 30 pass (`validation_evidence.csv`) |
| 3 | Calculated fields match `calculated_fields.md` | | |
| 4 | Year control changes every year-based sheet; Revert resets selections | | |
| 5 | Race and sex filters work on Utilization & Payment | | |
| 6 | Peer group filter works; selecting scatter points filters the review queue | | |
| 7 | Tooltips show readable field names and formatted values | | |
| 8 | Synthetic notice, source and refresh text visible on every dashboard | | Also asserted by `tests/test_tableau_package.py` |
| 9 | No clipped labels, horizontal scroll or unreadable legends at 1366 x 768 | | |
| 10 | Phone layout reviewed | | |
| 11 | No "cost" label on a payment metric; proxy and review disclaimers visible | | Also asserted by tests |
| 12 | Published to Tableau Public with the final title; URL recorded in README and `tableau/README.md` | | |
| 13 | One Tableau screenshot per dashboard saved to `tableau/screenshots/` | | |
