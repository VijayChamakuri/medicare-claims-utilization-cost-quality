# Tableau QA checklist

> CMS synthetic claims - not real patient or provider performance.

| Field | Value |
|---|---|
| Tableau version | Tableau Public 2026.2.2 (macOS, Apple silicon) |
| Tester | Vijay Chamakuri |
| Date | 2026-09-19 |
| Tableau Public URL | https://public.tableau.com/app/profile/vijay.chamakuri/viz/MedicareClaimsUtilizationPaymentQualityAnalyticsCMSDE-SynPUF/ExecutiveOverview |

| # | Check | Result | Notes |
|---|---|---|---|
| 1 | Workbook opens with no error dialog and no missing data source | Pass | Tableau log shows no errors |
| 2 | KPI tiles match `expected_kpis.csv` | Pass | 2009 tiles checked on screen (114,538 beneficiaries, 2,210,561 claims, $504,801,500 paid, 232.3, 247.6, 7.5%, 39.2%); every year tied in `validation_evidence.csv` (30 of 30) |
| 3 | Calculated fields match `calculated_fields.md` | Pass | Generated from the same specification |
| 4 | Year control changes every year-based sheet; Revert resets | Pass | |
| 5 | Race and sex filters work on Utilization & Payment | Pass | |
| 6 | Peer group filter works; selecting scatter points filters the review queue | Pass | Peer group is a dropdown |
| 7 | Tooltips show readable field names and formatted values | Pass | Text fields use ATTR() in tooltips |
| 8 | Synthetic notice, source and refresh text visible on every dashboard | Pass | Also asserted by tests |
| 9 | No clipped labels, horizontal scroll or unreadable legends at 1366 x 768 | Pass after fixes | Fixed: pinned zone sizes, sheet stacking, tier order, crowded tables; see `reports/visual_qa.md` |
| 10 | Phone layout reviewed | Not reviewed | Tableau generates it automatically; the desktop layout is the tested one |
| 11 | No "cost" label on a payment metric; proxy and review disclaimers visible | Pass | Also asserted by tests |
| 12 | Published with the final title; URL recorded in README and `tableau/README.md` | Pass | |
| 13 | One Tableau screenshot per dashboard saved to `tableau/screenshots/` | Pass | 5 screenshots |
