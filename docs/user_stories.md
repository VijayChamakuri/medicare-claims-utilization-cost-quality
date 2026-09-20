# User stories and acceptance criteria

> CMS synthetic claims - not real patient or provider performance.

Roles are the documented personas in [business requirements](business_requirements.md) and the [stakeholder question map](stakeholder_question_map.md). They are personas for a demonstration project, not people who were interviewed. Every acceptance criterion ends with the executable check that proves it: a pytest test, a dbt test, or a committed evidence file.

## US-01 Payment concentration

**As a** payer or provider operations leader, **I want** to see how concentrated paid amount is across synthetic beneficiaries, **so that** I can decide which segment gets a first review.

- **Given** a built warehouse, **when** the concentration metric is computed for a year, **then** it reports the top 5 percent group, its paid amount and its share of the total. Check: `test_payment_concentration_top_five_percent`.
- **Given** the same year, **when** the value is recomputed in pandas from the raw files with no shared SQL, **then** the two agree within the documented tolerance. Check: `test_independent_pandas_recomputation_agrees_within_tolerance`; evidence `reports/independent_reconciliation.csv`.
- **Given** the published Tableau workbook, **when** its packaged extract is queried, **then** the concentration KPI equals the mart value. Check: `test_hyper_tieout_passes_for_every_kpi`; evidence `tableau/validation_evidence.csv`.

## US-02 Setting and condition mix

**As a** utilization management analyst, **I want** paid amount split by care setting and primary-diagnosis group, **so that** I can focus authorization or care-management effort.

- **Given** analytic claims, **when** the utilization and payment marts build, **then** claims and paid amount are reported per setting and per AHRQ CCS group. Check: `test_claim_counts_by_setting_and_total`.
- **Given** a primary diagnosis that is missing, malformed or outside CCS 2015, **when** conditions are grouped, **then** each case gets its own condition ID instead of one shared bucket. Check: `test_condition_grouping_uses_cited_ccs_categories`.
- **Given** the care-setting dimension, **when** any mart reports a setting, **then** it comes from that dimension only. Check: `test_setting_dimension_is_the_only_source_of_settings`.

## US-03 Rates with an honest denominator

**As a** payer or provider operations leader, **I want** utilization expressed per 1,000 member-years, **so that** I can compare years with different eligibility.

- **Given** beneficiary summary coverage months and death dates, **when** member months are built, **then** a beneficiary contributes at most their covered months and none after death. Check: `test_member_month_eligibility`.
- **Given** member months, **when** admissions and ED proxy rates are computed, **then** they use member years as the denominator. Check: `test_admissions_and_rates`.

## US-04 Readmission proxy with visible exclusions

**As a** quality monitoring analyst, **I want** the 30-day readmission proxy with its numerator, denominator and exclusions on the page, **so that** I can judge whether to invest in a validated measure.

- **Given** continuous stays, **when** index stays are selected, **then** stays where the beneficiary died and stays without a full 30-day follow-up window are excluded and counted separately. Check: `test_readmission_proxy_index_and_exclusion_logic`.
- **Given** the quality mart, **when** it is compared with a recount from the index table, **then** eligible and readmitted counts match. Check: dbt test `assert_readmission_denominator_matches_index`.
- **Given** the Tableau Quality & Cohorts dashboard, **when** it is opened, **then** it states that the measure is not HEDIS, not CMS-HCC and not a clinical outcome measure. Check: `test_proxy_and_review_disclaimers_are_on_their_dashboards`.

## US-05 Care-management starting list

**As a** care management analyst, **I want** a transparent utilization risk tier, **so that** I can build a starting outreach list I can challenge.

- **Given** prior-year chronic flags, admissions and paid amount, **when** tiers are assigned, **then** the points and cut points follow the published rule and the first study year is not assessed. Check: `test_risk_tier_counts_and_boundaries`.
- **Given** any published view of the tier, **when** it is read, **then** it is labeled descriptive and not CMS-HCC. Check: `test_payment_metrics_are_never_called_cost` guards payment wording; the tier disclaimer is asserted by `test_proxy_and_review_disclaimers_are_on_their_dashboards`.

## US-06 Provider review queue

**As a** provider analytics analyst, **I want** providers compared with same-type peers, **so that** I can decide which providers to look at against peers.

- **Given** provider-year rows, **when** review flags are set, **then** a flag requires the minimum peer count and claim count and a positive interquartile range. Check: `test_provider_review_flags_use_peer_quartiles`.
- **Given** a flagged provider, **when** the action list is written, **then** each row carries reason codes and a synthetic-review label. Check: `test_provider_action_list_carries_reason_codes`; evidence `reports/provider_action_list.csv`.
- **Given** the Tableau Provider Operations dashboard, **when** it is opened, **then** it states that a flag is a prompt to review and not a finding about fraud or quality. Check: `test_proxy_and_review_disclaimers_are_on_their_dashboards`.

## US-07 Release gate on reconciliation

**As a** data owner, **I want** the build to stop when a blocking reconciliation fails, **so that** no untrusted metric is released.

- **Given** a warehouse build, **when** any blocking check fails, **then** the pipeline raises and the run stops. Check: `test_blocking_checks_pass_on_the_fixture` and `test_a_payment_dropped_from_the_warehouse_is_caught_by_sql_reconciliation`.
- **Given** informational tie-outs that differ by design, **when** they fail, **then** they never block the build. Check: `test_informational_tie_outs_never_block`.

## US-08 Independent recomputation

**As a** data owner, **I want** headline numbers recomputed by a second method, **so that** a SQL mistake cannot pass unnoticed.

- **Given** the raw files, **when** claims, payments, admissions, ED proxy, readmission proxy and concentration are recomputed in pandas, **then** money agrees to the cent and counts agree exactly. Check: `test_payment_amounts_to_the_cent`; evidence `reports/independent_reconciliation.csv`.
- **Given** a tampered mart value, **when** the recomputation runs, **then** it fails. Check: `test_a_wrong_mart_value_is_caught_by_the_independent_recomputation`.

## US-09 One definition per metric

**As a** data owner, **I want** one governed definition per KPI, **so that** Excel, Tableau and the documentation cannot disagree.

- **Given** the metric contract, **when** a metric is added or changed, **then** it carries owner, grain, source model, numerator, denominator, inclusions, exclusions, quality checks and known limits. Check: `test_every_metric_has_every_required_field`.
- **Given** the contract, **when** the dictionary, Excel sheet and Tableau fields are generated, **then** they read the same source. Check: `test_excel_and_tableau_read_the_same_contract` and `test_generated_dictionary_uses_every_definition_and_version`.

## US-10 Excel workbook that ties out

**As a** payer or provider operations leader, **I want** an Excel review whose totals tie to the warehouse, **so that** I can work offline without losing the audit trail.

- **Given** the workbook, **when** the reconciliation sheet is evaluated, **then** every tie equals the warehouse value. Check: `test_reconciliation_sheet_ties_workbook_totals_to_duckdb`.
- **Given** the workbook, **when** rates are inspected, **then** they are live formulas and counts are values. Check: `test_rates_are_formulas_and_counts_are_values`.
- **Given** the executive summary sheet, **when** it is printed, **then** it fits two landscape pages with repeated headers and the synthetic notice. Check: `test_print_settings_keep_the_executive_summary_readable`; evidence `reports/claims_executive_summary.pdf`.

## US-11 Published dashboards that match the marts

**As a** payer or provider operations leader, **I want** the Tableau workbook to show the same numbers as the warehouse, **so that** I can quote them without re-checking.

- **Given** the packaged workbook, **when** every expected KPI is queried from its Hyper extract, **then** all values match the marts. Check: `test_hyper_tieout_passes_for_every_kpi`; evidence `tableau/validation_evidence.csv`.
- **Given** the workbook manifest, **when** it lists sheets, dashboards and extracts, **then** each one exists in the package. Check: `test_manifest_references_only_what_the_workbook_contains`.
- **Given** any dashboard, **when** it is opened, **then** the synthetic notice, the source and the refresh date are visible. Check: `test_every_dashboard_carries_the_synthetic_notice_source_and_refresh`.

## US-12 Nothing beneficiary-level leaves the warehouse

**As a** data owner, **I want** only aggregates published, **so that** the habit holds when the same pipeline meets real claims.

- **Given** any export, **when** its columns are inspected, **then** no beneficiary-level row or identifier is present. Check: `test_no_beneficiary_level_rows_are_exported` and `test_exports_are_aggregates_only_and_match_hand_values`.
- **Given** any Tableau extract, **when** its columns are inspected, **then** beneficiary and claim identifiers are absent, and a leak attempt fails the build. Check: `test_no_published_extract_contains_a_beneficiary_or_claim_identifier` and `test_extract_guard_rejects_a_beneficiary_identifier`.

## US-13 Payment language stays accurate

**As a** data owner, **I want** CMS payment fields never relabeled as cost, **so that** the numbers are not over-read.

- **Given** the metric contract, **when** a payment metric is described, **then** the word cost does not appear. Check: `test_payment_metrics_are_described_as_payment_not_cost`.
- **Given** the Tableau workbook, **when** labels and captions are read, **then** no payment metric is labeled cost. Check: `test_payment_metrics_are_never_called_cost`.

## US-14 Reproducible source of record

**As a** data owner, **I want** the source files pinned and verified, **so that** a silent upstream change cannot alter results.

- **Given** the manifest, **when** a download runs, **then** URL, retrieval date, size and SHA-256 are recorded for every file. Check: `test_manifest_records_url_date_size_and_hash`.
- **Given** a changed source file, **when** the pipeline runs, **then** it stops until the manifest is refreshed deliberately. Check: `test_a_changed_source_file_stops_the_run_until_refreshed`.
