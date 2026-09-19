# Decision log

> CMS synthetic claims - not real patient or provider performance.

| Decision | Chosen | Rejected and why |
|---|---|---|
| Transformation engine | DuckDB SQL files run by a small Python runner | Spark or a cloud warehouse: 5.6 million claims fit comfortably in one DuckDB file, and the portfolio claim is about SQL and modeling, not infrastructure. |
| dbt adoption | Generate dbt models from the validated SQL and prove equivalence | Rewriting the SQL by hand for dbt: two copies of the logic would drift. A thin wrapper that only selects from legacy tables: it would test nothing. |
| Default build path | Keep the legacy SQL runner as the default; dbt runs after it and must match | Switching the default to dbt immediately: the legacy path carries the fixture history; switch only after equivalence has held across releases. |
| Payment naming | CMS field names, "paid amount" | "Cost": the fields are Medicare payments, not cost or charges. |
| Readmission and ED measures | Labeled proxies with visible numerator, denominator and exclusions | Calling them HEDIS or official measures: DE-SynPUF lacks discharge status, planned-readmission flags and revenue centers. |
| Risk stratification | Transparent points tier from prior-year information | CMS-HCC or a trained model: no licensed coefficients, and a black box would add nothing on synthetic data. |
| Provider flags | Peer quartile fence, split by setting, IQR > 0, multiplier 3.0 | A single peer group and multiplier 1.5: it flagged about 900 facilities, which is noise, not a review queue. |
| Tableau workbook | Generated as XML with Hyper extracts from code, then opened and checked in Tableau Public | Building it by hand: not reproducible and not reviewable in a diff. Live CSV connections: Tableau Public requires extracts. |
| Published data | Aggregates and synthetic provider IDs only | Beneficiary-level extracts: not needed for any view, and they would be the wrong habit for real claims data. |
| Condition grouping ID | Separate IDs for missing, invalid-format and valid-but-unmapped primary diagnoses | One shared `unmapped` ID: the new dbt grain test showed it broke the table's key. |
| Offline HTML dashboard | Kept as a secondary, offline demo | Deleting it: it still documents the same metrics without a Tableau install. No new HTML artifacts are added. |
