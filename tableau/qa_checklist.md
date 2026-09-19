# Tableau QA checklist

Nothing below is complete until a person has opened the workbook in Tableau. Mark items only after checking them visually. Status of every item today: **pending** (no workbook exists).

| Item | Status | Evidence |
|---|---|---|
| Workbook (`.twbx`) checked in or Tableau Public URL recorded in `README.md` | Pending | |
| Every KPI tile matches `expected_kpis.csv` for 2008, 2009 and 2010 | Pending | |
| Rates are aggregate calculated fields, not averages of row rates | Pending | |
| Denominator is not tripled when summing `member_years` across settings | Pending | |
| Year, setting, condition and demographic filters change only intended worksheets | Pending | |
| Provider outlier parameters (`IQR multiplier`, `Min claims`, `Top N`) update flags and list | Pending | |
| Provider drill-through and dashboard actions work and can be reset | Pending | |
| Tooltips show numerator, denominator and caveat | Pending | |
| Synthetic banner visible on every page and in every screenshot | Pending | |
| Screenshots checked for clipping, labels, color and legends before use | Pending | |
| No screenshot or README text calls the workbook complete before it exists | Pending | |
