# Build guide: five pages

Banner on every page: `CMS synthetic claims - not real patient or provider performance.` (a text object pinned at the top).

Global filters: **Year**, **Care setting**, **Condition** (`condition_name`), **Demographic** (`sex`, `race`, `age_band`). Apply year and setting to all worksheets that carry those fields.

| Page | Data | Worksheets |
|---|---|---|
| 1. Executive Overview | `kpi_annual`, `monthly_payments`, `monthly_utilization` | Seven KPI tiles for the selected year (beneficiaries, claims, paid amount, paid per beneficiary, admissions per 1,000, readmission proxy, top 5% share); monthly paid amount stacked by setting; monthly claims per 1,000 members line |
| 2. Utilization & Payment | `annual_by_setting`, `condition_summary`, `demographic_summary` | Setting mix (share of claims versus share of paid amount); top 15 conditions by paid amount; demographic table; year filter |
| 3. Provider Operations | `provider_review_facility` | Scatter of `claims` (log axis) versus `payment_per_claim`, colored by the parameterized review flag; top N list; provider drill-through (dashboard action from the list or scatter to a per-year table) |
| 4. Quality & Cohorts | `readmission_review`, `risk_tier_summary`, `payment_concentration` | Readmission proxy by tier with numerator, denominator and exclusions; tier table; concentration table |
| 5. Data Quality & Definitions | `field_dictionary.md`, `reconciliation_results` (from `../exports`) | Source, refresh date, reconciliation status, definitions, synthetic banner |

## Actions

- Provider list to scatter: highlight action on `provider_id`.
- Provider list to per-year table: filter action on `provider_id` (drill-through).
- Condition table to demographic table: filter action on `condition_name`.

## Tooltips

Every rate tooltip states the numerator, the denominator and one caveat (see `calculated_fields.md`).

## Colors

Use a color-blind-safe palette (for example blue, orange, green for the three settings) and never rely on color alone: flagged providers also use a larger mark and a text label.
