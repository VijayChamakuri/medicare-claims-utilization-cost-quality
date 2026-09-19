# Source to target mapping

> CMS synthetic claims - not real patient or provider performance.

Grain, key and row counts for every table are in the generated [table inventory](table_inventory.md). This page states how source fields become target columns, the null policy and the limits.

| Target | Source | Rule | Null and invalid policy |
|---|---|---|---|
| `fact_claim_header.claim_key` | `DESYNPUF_ID`, `CLM_ID`, setting | `setting:beneficiary:claim` | Rows with a null ID stop the run |
| `fact_claim_header.from_date`, `thru_date` | `CLM_FROM_DT`, `CLM_THRU_DT` | Earliest from, latest thru across segments | Null or `from > thru`: `date_valid = false`, excluded from metrics, kept and counted |
| `fact_claim_header.service_date` | `CLM_ADMSN_DT` (inpatient), `CLM_FROM_DT` (other) | Inpatient dated by admission | Falls back to from date |
| `fact_claim_header.payment_amount` | `CLM_PMT_AMT` (segments summed) or `LINE_NCH_PMT_AMT_1..13` (lines summed) | Sum, negative adjustments kept | Null payment treated as 0 and counted; a claim with no payment value stops the run |
| `fact_claim_header.primary_dx` | `ICD9_DGNS_CD_1` | Normalized (trim, drop dots and spaces, upper-case), first non-null across segments | Missing or malformed kept as is and reported |
| `fact_claim_header.is_analytic` | derived | `date_valid` and service date in 2008-01-01 to 2010-12-31 | Non-analytic claims stay in facts with a reason; their payment is reported separately |
| `fact_claim_line` (carrier) | `HCPCS_CD_n`, `PRF_PHYSN_NPI_n`, `LINE_*_n` | One row per slot that has a code, a non-zero payment or a performing NPI | Padded slots (0.00, no code, no NPI) dropped |
| `fact_claim_line` (institutional) | `HCPCS_CD_1..45` | One row per non-null HCPCS position, numbered across segments | No line-level payment exists |
| `fact_claim_diagnosis` | all diagnosis columns | Distinct code per claim | Null dropped |
| `fact_inpatient_stay` | analytic inpatient claims | Claims merge into one stay when admit is on or before the earlier stay's discharge | Invalid or out-of-window claims never form stays |
| `fact_beneficiary_year.member_months` | `BENE_HI_CVRAGE_TOT_MONS`, `BENE_DEATH_DT` | `min(coverage months, months alive)` | Null coverage counts as 0 |
| `dim_beneficiary` | beneficiary files | Latest year's sex, race, state; earliest birth date; latest death date | none |
| `dim_diagnosis.ccs_category` | `reference/ccs_icd9_dx_2015.csv` | Join on normalized code | Valid format but absent from CCS: "Unmapped"; bad format: "Invalid code format" |
| `dim_procedure.procedure_group` | HCPCS code | CPT section ranges and HCPCS Level II letters | Bad format: "Invalid or missing" |
| `mart_member_risk` | prior-year `fact_beneficiary_year` and `mart_beneficiary_year_summary` | Points from prior-year information only | No prior year: `not_assessed` |
| `mart_readmission_index` | `fact_inpatient_stay`, `dim_beneficiary.death_date` | See the metric dictionary | Died in stay and insufficient follow-up excluded and counted |
| `mart_provider_performance` | analytic claims and lines | Provider-year aggregates, peer quartiles by type and year | Groups with too few peers or no spread are not flagged |

## Limits of the mapping

- CMS gives a *count* of coverage months, not which months. Member months are placed from January (an assumption, tested).
- `SEGMENT` is documented only as up to two records of one claim; continuation records carry no dates in the source.
- The 2008 beneficiary file is the only one with 2008 IDs by construction. A claim for a beneficiary absent from every summary file would be reported as an orphan (none exist in sample 1).
