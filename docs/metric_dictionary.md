# Metric dictionary

> CMS synthetic claims - not real patient or provider performance.

Generated from `config/metric_dictionary.yml` (contract version 2), the single source for this page, the Excel `Metric_Dictionary` sheet, the Tableau field dictionary and `tableau/expected_kpis.csv`. Change rules: [metric governance](metric_governance.md).

## Beneficiaries

- **ID and version:** `beneficiaries` v1 (headline KPI)
- **Business question:** How many synthetic beneficiaries are in the population each year?
- **Owner role:** Data owner
- **Description:** Synthetic beneficiaries with a row in the year's beneficiary summary file.
- **Grain:** beneficiary-year
- **Source model:** `fact_beneficiary_year`
- **Calculation:** count(*) of beneficiary-year rows
- **Numerator:** Count of beneficiary-year rows
- **Denominator:** n/a
- **Inclusions:** every beneficiary summary row for the year
- **Exclusions:** none
- **Valid dimensions:** year, sex, race, age_band, utilization_risk_tier
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** key_unique_beneficiary_year, dbt unique_combination fact_beneficiary_year
- **Unit:** beneficiaries
- **Source fields:** DESYNPUF_ID (beneficiary summary)
- **Known limits:** Synthetic people. DE-SynPUF is a 5 percent synthetic sample of 2008 beneficiaries.
- **Tableau field:** `beneficiaries`

## Member months

- **ID and version:** `member_months` v1
- **Business question:** How much eligibility exposure do rates use as their denominator?
- **Owner role:** Data owner
- **Description:** Months a beneficiary contributes to rates. A beneficiary-year contributes min(Part A coverage months, months alive in the year), placed from January.
- **Grain:** beneficiary-year-month
- **Source model:** `mart_member_month`
- **Calculation:** count(*) of member-month rows
- **Numerator:** Sum over beneficiary-years of min(BENE_HI_CVRAGE_TOT_MONS, months alive)
- **Denominator:** n/a
- **Inclusions:** months within Part A coverage and before death
- **Exclusions:** Deceased beneficiaries stop after the month of BENE_DEATH_DT
- **Valid dimensions:** year, month, sex, race, age_band
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** key_unique_member_month, eligibility reconciliation
- **Unit:** member months
- **Source fields:** BENE_HI_CVRAGE_TOT_MONS, BENE_DEATH_DT
- **Known limits:** CMS gives a count of covered months, not which months. Placing them from January is an assumption.
- **Tableau field:** `member_months`

## Analytic claims

- **ID and version:** `claims` v1 (headline KPI)
- **Business question:** How many claims are in scope for analysis?
- **Owner role:** Payer operations leader
- **Description:** Claims that pass the analytic rules: valid dates inside the study window, duplicates removed, segments merged.
- **Grain:** claim
- **Source model:** `fact_claim_header`
- **Calculation:** count(*) where is_analytic
- **Numerator:** Analytic claims (beneficiary + CLM_ID within a setting, segments merged)
- **Denominator:** n/a
- **Inclusions:** analytic claims (valid dates inside the study window, deduplicated, segments merged)
- **Exclusions:** Claims with invalid dates, claims dated outside 2008-01-01 to 2010-12-31, duplicate rows
- **Valid dimensions:** year, month, setting
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_mart claim counts, independent pandas claim counts
- **Unit:** claims
- **Source fields:** DESYNPUF_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, SEGMENT
- **Known limits:** Inpatient claims are dated by admission date.
- **Tableau field:** `claims`

## Claims per 1,000 member-years

- **ID and version:** `claims_per_1000` v1 (headline KPI)
- **Business question:** How much claim volume is there relative to eligible exposure?
- **Owner role:** Payer operations leader
- **Description:** Analytic claims divided by member years, times 1,000.
- **Grain:** year x setting
- **Source model:** `mart_utilization_annual`
- **Calculation:** claims / (member_months / 12) * 1000
- **Numerator:** Analytic claims (beneficiary + CLM_ID within a setting, segments merged)
- **Denominator:** Member months divided by 12
- **Inclusions:** analytic claims (valid dates inside the study window, deduplicated, segments merged)
- **Exclusions:** Claims with invalid dates, claims dated outside 2008-01-01 to 2010-12-31, duplicate rows
- **Valid dimensions:** year, setting, month
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_mart claim counts, independent pandas claim counts
- **Unit:** claims per 1,000 member-years
- **Source fields:** DESYNPUF_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, SEGMENT
- **Known limits:** Inpatient claims are dated by admission date.
- **Tableau field:** `claims_per_1000_member_years`

## Inpatient admissions per 1,000 member-years

- **ID and version:** `admissions_per_1000` v1 (headline KPI)
- **Business question:** How often are synthetic beneficiaries admitted, relative to exposure?
- **Owner role:** Payer operations leader
- **Description:** Continuous inpatient stays per 1,000 member-years. A claim admitted on or before the discharge date of the beneficiary's earlier stay continues that stay.
- **Grain:** year
- **Source model:** `mart_utilization_annual`
- **Calculation:** continuous stays by admission year / member years * 1000
- **Numerator:** Inpatient stays by admission date
- **Denominator:** Member years
- **Inclusions:** analytic inpatient claims merged into continuous stays
- **Exclusions:** Invalid or out-of-window inpatient claims
- **Valid dimensions:** year, month, utilization_risk_tier, sex, race, age_band
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_fact stays, independent pandas admissions
- **Unit:** admissions per 1,000 member-years
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, CLM_FROM_DT, CLM_THRU_DT
- **Known limits:** Transfers are merged; no discharge status field exists to identify them directly.
- **Tableau field:** `admissions_per_1000_member_years`

## ED visit proxy per 1,000 member-years

- **ID and version:** `ed_proxy_per_1000` v1 (headline KPI)
- **Business question:** How much emergency department use is there, as far as outpatient codes can show it?
- **Owner role:** Quality analyst
- **Description:** Outpatient claims carrying at least one HCPCS code from 99281 to 99285, per 1,000 member-years.
- **Grain:** year
- **Source model:** `mart_utilization_annual`
- **Calculation:** outpatient claims with HCPCS 99281-99285 / member years * 1000
- **Numerator:** Analytic outpatient claims with an ED evaluation and management code
- **Denominator:** Member years
- **Inclusions:** analytic outpatient claims with at least one ED evaluation and management code
- **Exclusions:** none beyond analytic-claim rules
- **Valid dimensions:** year, month
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** independent pandas ED proxy
- **Unit:** ED proxy visits per 1,000 member-years
- **Source fields:** HCPCS_CD_1 to HCPCS_CD_45 (outpatient)
- **Known limits:** DE-SynPUF has no revenue center codes, so this is a code-based proxy, not a validated ED measure.
- **Tableau field:** `ed_proxy_per_1000_member_years`

## Outpatient visits per 1,000 member-years

- **ID and version:** `outpatient_per_1000` v1
- **Business question:** How much outpatient claim volume is there relative to exposure?
- **Owner role:** Payer operations leader
- **Description:** Analytic outpatient claims per 1,000 member-years.
- **Grain:** year
- **Source model:** `mart_utilization_annual`
- **Calculation:** analytic outpatient claims / member years * 1000
- **Numerator:** Analytic outpatient claims
- **Denominator:** Member years
- **Inclusions:** analytic outpatient claims
- **Exclusions:** analytic-claim rules
- **Valid dimensions:** year, month
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_mart claim counts
- **Unit:** claims per 1,000 member-years
- **Source fields:** outpatient claims file
- **Known limits:** A claim is not necessarily a distinct visit.
- **Tableau field:** `outpatient_visits_per_1000_member_years`

## Carrier service lines

- **ID and version:** `carrier_service_lines` v1
- **Business question:** How many professional service lines were billed?
- **Owner role:** Payer operations leader
- **Description:** Carrier line items (up to 13 per claim) that have a HCPCS code, a non-zero payment or a performing NPI. CMS pads unused slots with a 0.00 payment; those padded slots are not lines.
- **Grain:** claim line
- **Source model:** `fact_claim_line`
- **Calculation:** count of carrier lines with a HCPCS code, an NPI or a non-zero payment
- **Numerator:** Analytic carrier lines
- **Denominator:** n/a
- **Inclusions:** carrier line slots that carry content
- **Exclusions:** analytic-claim rules
- **Valid dimensions:** year, month
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** header_line reconciliation, padded-slot regression test
- **Unit:** lines
- **Source fields:** HCPCS_CD_1..13, LINE_NCH_PMT_AMT_1..13, PRF_PHYSN_NPI_1..13
- **Known limits:** Line-level payment is the only carrier payment field.
- **Tableau field:** `carrier_service_lines`

## Total claim payment amount

- **ID and version:** `paid_amount` v1 (headline KPI)
- **Business question:** How much did Medicare pay on these synthetic claims, and where?
- **Owner role:** Payer operations leader
- **Description:** Medicare trust fund payment on analytic claims. Institutional claims use CLM_PMT_AMT (segments summed); carrier claims use LINE_NCH_PMT_AMT_1..13 (lines summed). Negative amounts are payment adjustments and are included.
- **Grain:** claim
- **Source model:** `fact_claim_header`
- **Calculation:** sum(CLM_PMT_AMT) for institutional claims + sum(LINE_NCH_PMT_AMT) for carrier lines
- **Numerator:** Sum of payment on analytic claims
- **Denominator:** n/a
- **Inclusions:** analytic claims; negative adjustments included
- **Exclusions:** Invalid-date and out-of-window claims are reported separately
- **Valid dimensions:** year, month, setting, sex, race, age_band, utilization_risk_tier
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** header_line payment tie-out, independent pandas payments to the cent, Excel reconciliation sheet
- **Unit:** US dollars (synthetic)
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Known limits:** Not a cost, charge or allowed amount. Beneficiary summary MEDREIMB_* fields do not tie to claim payments and are not used.
- **Tableau field:** `payment_amount`

## Payment per beneficiary

- **ID and version:** `paid_per_beneficiary` v1 (headline KPI)
- **Business question:** What is the average paid amount per synthetic beneficiary?
- **Owner role:** Payer operations leader
- **Description:** Total claim payment amount divided by beneficiaries in the year.
- **Grain:** year
- **Source model:** `mart_payment_annual`
- **Calculation:** paid amount / beneficiaries (all beneficiaries, including those with no claims)
- **Numerator:** Total claim payment amount
- **Denominator:** Beneficiary summary rows in the year
- **Inclusions:** all beneficiaries in the year
- **Exclusions:** analytic-claim rules
- **Valid dimensions:** year, sex, race, age_band, utilization_risk_tier
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_mart payment totals
- **Unit:** US dollars per beneficiary (synthetic)
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Known limits:** Includes beneficiaries with no claims.
- **Tableau field:** `payment_per_beneficiary`

## Payment per claim

- **ID and version:** `paid_per_claim` v1
- **Business question:** What is the average paid amount per analytic claim?
- **Owner role:** Payer operations leader
- **Description:** Paid amount divided by analytic claims.
- **Grain:** year x setting
- **Source model:** `mart_payment_annual`
- **Calculation:** paid amount / analytic claims
- **Numerator:** Paid amount (CLM_PMT_AMT + LINE_NCH_PMT_AMT)
- **Denominator:** Analytic claims
- **Inclusions:** analytic claims; negative adjustments included
- **Exclusions:** Invalid-date and out-of-window claims are reported separately
- **Valid dimensions:** year, setting
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** header_line payment tie-out, independent pandas payments to the cent, Excel reconciliation sheet
- **Unit:** dollars per claim
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Known limits:** Not a cost, charge or allowed amount. Beneficiary summary MEDREIMB_* fields do not tie to claim payments and are not used.
- **Tableau field:** `payment_per_claim`

## Payment per admission

- **ID and version:** `paid_per_admission` v1
- **Business question:** What is the average inpatient paid amount per continuous stay?
- **Owner role:** Payer operations leader
- **Description:** Inpatient payment divided by inpatient stays.
- **Grain:** year
- **Source model:** `fact_inpatient_stay`
- **Calculation:** inpatient paid amount / continuous stays
- **Numerator:** Inpatient CLM_PMT_AMT on analytic claims
- **Denominator:** Inpatient stays by admission year
- **Inclusions:** continuous inpatient stays
- **Exclusions:** analytic-claim rules
- **Valid dimensions:** year
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** fact_to_fact stay payments
- **Unit:** US dollars per admission (synthetic)
- **Source fields:** CLM_PMT_AMT
- **Known limits:** Payment on a claim dated by admission is attributed to the admission year.
- **Tableau field:** `payment_per_admission`

## Payment concentration (top 5 percent)

- **ID and version:** `top5_payment_share` v1 (headline KPI)
- **Business question:** How concentrated is payment among the highest-paid beneficiaries?
- **Owner role:** Payer operations leader
- **Description:** Share of a year's payment held by the highest-paid ceil(5 percent of beneficiaries) beneficiaries.
- **Grain:** year
- **Source model:** `mart_payment_concentration`
- **Calculation:** paid amount of the top ceil(5% of beneficiaries) / total paid amount
- **Numerator:** Payment of the top ceil(5 percent x N) beneficiaries
- **Denominator:** Total payment in the year
- **Inclusions:** all beneficiaries in the year, ranked by paid amount
- **Exclusions:** none
- **Valid dimensions:** year
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** independent pandas concentration
- **Unit:** share
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Known limits:** Ties are broken by beneficiary ID.
- **Tableau field:** `top_share`

## 30-day readmission proxy

- **ID and version:** `readmission_proxy` v1 (headline KPI)
- **Business question:** How often is a continuous inpatient stay followed by another admission within 30 days?
- **Owner role:** Quality analyst
- **Description:** Share of eligible index stays followed by another stay beginning after the index discharge date and within 30 days.
- **Grain:** index stay
- **Source model:** `mart_quality_monitoring`
- **Calculation:** readmitted eligible index stays / eligible index stays
- **Numerator:** Eligible index stays with a later stay in the window
- **Denominator:** Eligible index stays
- **Inclusions:** continuous stays with valid dates and a full 30-day follow-up window
- **Exclusions:** Invalid dates; beneficiary died between admit and discharge; discharge within 30 days of the end of the study period
- **Valid dimensions:** year, utilization_risk_tier
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** dbt assert_readmission_denominator_matches_index, independent pandas readmission proxy
- **Unit:** share of index stays
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, BENE_DEATH_DT
- **Known limits:** Measure-inspired proxy, not a certified measure. No planned-readmission or discharge-status field is available. Any stay can be both an index and a readmission.
- **Tableau field:** `readmission_rate`

## Mean length of stay

- **ID and version:** `mean_los` v1
- **Business question:** How long are continuous inpatient stays on average?
- **Owner role:** Quality analyst
- **Description:** Mean of discharge date minus admission date over stays.
- **Grain:** stay
- **Source model:** `fact_inpatient_stay`
- **Calculation:** avg(discharge date - admission date)
- **Numerator:** Sum of stay days
- **Denominator:** Stays
- **Inclusions:** continuous stays with valid dates
- **Exclusions:** analytic-claim rules
- **Valid dimensions:** year
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** dates reconciliation (no negative length of stay)
- **Unit:** days
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT
- **Known limits:** About 5 percent of source stays disagree with CLM_UTLZTN_DAY_CNT; the date difference is used.
- **Tableau field:** `mean_length_of_stay_days`

## Utilization risk tier

- **ID and version:** `utilization_risk_tier` v1
- **Business question:** Which synthetic beneficiaries had heavy prior-year utilization, as a transparent starting list?
- **Owner role:** Quality analyst
- **Description:** Transparent points from prior-year information only. Comorbidity points from chronic condition flags (0-1 conditions 0, 2-3 conditions 1, 4 or more 2), admission points (0 stays 0, 1 stay 2, 2 or more 3), paid points (under 1,000 dollars 0, 1,000 to under 5,000 dollars 1, 5,000 or more 2). Score 0-1 low, 2-3 medium, 4 or more high.
- **Grain:** beneficiary-year
- **Source model:** `mart_member_risk`
- **Calculation:** points from prior-year chronic flags, admissions and paid amount, cut into low/medium/high
- **Numerator:** n/a
- **Denominator:** n/a
- **Inclusions:** beneficiary-years with a prior study year
- **Exclusions:** Beneficiaries with no prior-year row are not assessed
- **Valid dimensions:** year
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** dbt unique_combination mart_member_risk, fixture tier assertions
- **Unit:** tier
- **Source fields:** SP_* chronic condition flags, claim payments, inpatient stays
- **Known limits:** Descriptive portfolio stratification. Not CMS-HCC, RAF or any official risk adjustment.
- **Tableau field:** `utilization_risk_tier`

## Provider review flag

- **ID and version:** `provider_review_flag` v1
- **Business question:** Which facilities or NPIs sit far above same-type peers and should be looked at first?
- **Owner role:** Payer operations leader
- **Description:** A provider-year whose payment per claim or claim volume exceeds Q3 plus a multiple (default 3, Tukey far-out fence) of the interquartile range of its peers (same provider type, setting for facilities, and year), with a minimum claim count and peer count. The fence applies only when peers vary (IQR above zero).
- **Grain:** provider-type-year
- **Source model:** `mart_provider_performance`
- **Calculation:** claims or paid per claim above Q3 + 3.0 x IQR of peers, with at least 20 peers and 30 claims and IQR > 0
- **Numerator:** n/a
- **Denominator:** n/a
- **Inclusions:** providers meeting the minimum claim count in peer groups of the minimum size
- **Exclusions:** Groups with too few peers or claims, or with no spread among peers, are not flagged
- **Valid dimensions:** year, provider_type
- **Time basis:** calendar year of service (inpatient: admission date); monthly views use the month of service
- **Refresh expectation:** rebuilt on every pipeline run from the pinned CMS sample; the source is static, so the refresh is on code change, not on a schedule
- **Quality checks:** key_unique_provider_year, fixture provider flag assertions
- **Unit:** flag with reason codes
- **Source fields:** PRVDR_NUM, PRF_PHYSN_NPI_1..13
- **Known limits:** A prompt for review only. It is not evidence of fraud, poor quality or provider performance.
- **Tableau field:** `review_flag`
