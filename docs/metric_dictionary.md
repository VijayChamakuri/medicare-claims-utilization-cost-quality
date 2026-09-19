# Metric dictionary

> CMS synthetic claims - not real patient or provider performance.

Generated from `config/metric_dictionary.yml`, the single source for this page, the Excel `Metric_Dictionary` sheet and the Tableau notes. Payment fields keep their CMS names and are never called "cost".

## Beneficiaries

*Category:* Population. *Unit:* beneficiaries.

Synthetic beneficiaries with a row in the year's beneficiary summary file.

- **Numerator:** Count of beneficiary-year rows
- **Denominator:** n/a
- **Exclusions:** none
- **Source fields:** DESYNPUF_ID (beneficiary summary)
- **Caveat:** Synthetic people. DE-SynPUF is a 5 percent synthetic sample of 2008 beneficiaries.

## Member months

*Category:* Population. *Unit:* member months.

Months a beneficiary contributes to rates. A beneficiary-year contributes min(Part A coverage months, months alive in the year), placed from January.

- **Numerator:** Sum over beneficiary-years of min(BENE_HI_CVRAGE_TOT_MONS, months alive)
- **Denominator:** n/a
- **Exclusions:** Deceased beneficiaries stop after the month of BENE_DEATH_DT
- **Source fields:** BENE_HI_CVRAGE_TOT_MONS, BENE_DEATH_DT
- **Caveat:** CMS gives a count of covered months, not which months. Placing them from January is an assumption.

## Claims per 1,000 member-years

*Category:* Utilization. *Unit:* claims per 1,000 member-years.

Analytic claims divided by member years, times 1,000.

- **Numerator:** Analytic claims (beneficiary + CLM_ID within a setting, segments merged)
- **Denominator:** Member months divided by 12
- **Exclusions:** Claims with invalid dates, claims dated outside 2008-01-01 to 2010-12-31, duplicate rows
- **Source fields:** DESYNPUF_ID, CLM_ID, CLM_FROM_DT, CLM_THRU_DT, SEGMENT
- **Caveat:** Inpatient claims are dated by admission date.

## Inpatient admissions per 1,000 member-years

*Category:* Utilization. *Unit:* admissions per 1,000 member-years.

Continuous inpatient stays per 1,000 member-years. A claim admitted on or before the discharge date of the beneficiary's earlier stay continues that stay.

- **Numerator:** Inpatient stays by admission date
- **Denominator:** Member years
- **Exclusions:** Invalid or out-of-window inpatient claims
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, CLM_FROM_DT, CLM_THRU_DT
- **Caveat:** Transfers are merged; no discharge status field exists to identify them directly.

## ED visit proxy per 1,000 member-years

*Category:* Utilization. *Unit:* ED proxy visits per 1,000 member-years.

Outpatient claims carrying at least one HCPCS code from 99281 to 99285, per 1,000 member-years.

- **Numerator:** Analytic outpatient claims with an ED evaluation and management code
- **Denominator:** Member years
- **Exclusions:** none beyond analytic-claim rules
- **Source fields:** HCPCS_CD_1 to HCPCS_CD_45 (outpatient)
- **Caveat:** DE-SynPUF has no revenue center codes, so this is a code-based proxy, not a validated ED measure.

## Outpatient visits per 1,000 member-years

*Category:* Utilization. *Unit:* claims per 1,000 member-years.

Analytic outpatient claims per 1,000 member-years.

- **Numerator:** Analytic outpatient claims
- **Denominator:** Member years
- **Exclusions:** analytic-claim rules
- **Source fields:** outpatient claims file
- **Caveat:** A claim is not necessarily a distinct visit.

## Carrier service lines

*Category:* Utilization. *Unit:* lines.

Carrier line items (up to 13 per claim) that have a HCPCS code, a non-zero payment or a performing NPI. CMS pads unused slots with a 0.00 payment; those padded slots are not lines.

- **Numerator:** Analytic carrier lines
- **Denominator:** n/a
- **Exclusions:** analytic-claim rules
- **Source fields:** HCPCS_CD_1..13, LINE_NCH_PMT_AMT_1..13, PRF_PHYSN_NPI_1..13
- **Caveat:** Line-level payment is the only carrier payment field.

## Total claim payment amount

*Category:* Payment. *Unit:* US dollars (synthetic).

Medicare trust fund payment on analytic claims. Institutional claims use CLM_PMT_AMT (segments summed); carrier claims use LINE_NCH_PMT_AMT_1..13 (lines summed). Negative amounts are payment adjustments and are included.

- **Numerator:** Sum of payment on analytic claims
- **Denominator:** n/a
- **Exclusions:** Invalid-date and out-of-window claims are reported separately
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Caveat:** Not a cost, charge or allowed amount. Beneficiary summary MEDREIMB_* fields do not tie to claim payments and are not used.

## Payment per beneficiary

*Category:* Payment. *Unit:* US dollars per beneficiary (synthetic).

Total claim payment amount divided by beneficiaries in the year.

- **Numerator:** Total claim payment amount
- **Denominator:** Beneficiary summary rows in the year
- **Exclusions:** analytic-claim rules
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Caveat:** Includes beneficiaries with no claims.

## Payment per admission

*Category:* Payment. *Unit:* US dollars per admission (synthetic).

Inpatient payment divided by inpatient stays.

- **Numerator:** Inpatient CLM_PMT_AMT on analytic claims
- **Denominator:** Inpatient stays by admission year
- **Exclusions:** analytic-claim rules
- **Source fields:** CLM_PMT_AMT
- **Caveat:** Payment on a claim dated by admission is attributed to the admission year.

## Payment concentration (top 5 percent)

*Category:* Payment. *Unit:* share.

Share of a year's payment held by the highest-paid ceil(5 percent of beneficiaries) beneficiaries.

- **Numerator:** Payment of the top ceil(5 percent x N) beneficiaries
- **Denominator:** Total payment in the year
- **Exclusions:** none
- **Source fields:** CLM_PMT_AMT, LINE_NCH_PMT_AMT_1..13
- **Caveat:** Ties are broken by beneficiary ID.

## 30-day readmission proxy

*Category:* Quality monitoring. *Unit:* share of index stays.

Share of eligible index stays followed by another stay beginning after the index discharge date and within 30 days.

- **Numerator:** Eligible index stays with a later stay in the window
- **Denominator:** Eligible index stays
- **Exclusions:** Invalid dates; beneficiary died between admit and discharge; discharge within 30 days of the end of the study period
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT, BENE_DEATH_DT
- **Caveat:** Measure-inspired proxy, not a certified measure. No planned-readmission or discharge-status field is available. Any stay can be both an index and a readmission.

## Mean length of stay

*Category:* Utilization. *Unit:* days.

Mean of discharge date minus admission date over stays.

- **Numerator:** Sum of stay days
- **Denominator:** Stays
- **Exclusions:** analytic-claim rules
- **Source fields:** CLM_ADMSN_DT, NCH_BENE_DSCHRG_DT
- **Caveat:** About 5 percent of source stays disagree with CLM_UTLZTN_DAY_CNT; the date difference is used.

## Utilization risk tier

*Category:* Quality monitoring. *Unit:* tier.

Transparent points from prior-year information only. Comorbidity points from chronic condition flags (0-1 conditions 0, 2-3 conditions 1, 4 or more 2), admission points (0 stays 0, 1 stay 2, 2 or more 3), paid points (under 1,000 dollars 0, 1,000 to under 5,000 dollars 1, 5,000 or more 2). Score 0-1 low, 2-3 medium, 4 or more high.

- **Numerator:** n/a
- **Denominator:** n/a
- **Exclusions:** Beneficiaries with no prior-year row are not assessed
- **Source fields:** SP_* chronic condition flags, claim payments, inpatient stays
- **Caveat:** Descriptive portfolio stratification. Not CMS-HCC, RAF or any official risk adjustment.

## Provider review flag

*Category:* Provider operations. *Unit:* flag with reason codes.

A provider-year whose payment per claim or claim volume exceeds Q3 plus a multiple (default 3, Tukey far-out fence) of the interquartile range of its peers (same provider type, setting for facilities, and year), with a minimum claim count and peer count. The fence applies only when peers vary (IQR above zero).

- **Numerator:** n/a
- **Denominator:** n/a
- **Exclusions:** Groups with too few peers or claims, or with no spread among peers, are not flagged
- **Source fields:** PRVDR_NUM, PRF_PHYSN_NPI_1..13
- **Caveat:** A prompt for review only. It is not evidence of fraud, poor quality or provider performance.
