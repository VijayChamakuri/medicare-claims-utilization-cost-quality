# Data dictionary

> CMS synthetic claims - not real patient or provider performance.

Source: CMS 2008-2010 DE-SynPUF, sample 1. Field names are exactly as CMS publishes them (see the [codebook](https://www.cms.gov/files/document/de-10-codebook.pdf-0)). Dates are `YYYYMMDD` text. Files, URLs, sizes and SHA-256 hashes: [`data/data_manifest.json`](../data/data_manifest.json).

## Files

| File | Grain | Rows (sample 1) | Notes |
|---|---|---:|---|
| Beneficiary summary 2008, 2009, 2010 | beneficiary and year | 116,352 / 114,538 / 112,754 | The 2010 zip is linked by CMS as `sample_20`; the CSV inside is Sample 1 and every ID also appears in 2008 |
| Inpatient claims | claim segment | 66,773 | At most two `SEGMENT` records per `CLM_ID` |
| Outpatient claims | claim segment | 790,790 | Same |
| Carrier claims | claim | 4,741,335 | Up to 13 lines per claim in wide columns; unused slots padded with 0.00 |

## Fields used

| Field | File | Meaning | Used as |
|---|---|---|---|
| `DESYNPUF_ID` | all | Synthetic beneficiary code | Beneficiary key |
| `BENE_BIRTH_DT`, `BENE_DEATH_DT` | beneficiary | Synthetic birth and death dates | Age band, member months, readmission exclusion |
| `BENE_SEX_IDENT_CD`, `BENE_RACE_CD` | beneficiary | Sex (1 male, 2 female), race (1 White, 2 Black, 3 Other, 5 Hispanic) | Demographic filters |
| `BENE_HI_CVRAGE_TOT_MONS` | beneficiary | Months of Part A coverage in the year | Member months |
| `SP_ALZHDMTA`, `SP_CHF`, `SP_CHRNKIDN`, `SP_CNCR`, `SP_COPD`, `SP_DEPRESSN`, `SP_DIABETES`, `SP_ISCHMCHT`, `SP_OSTEOPRS`, `SP_RA_OA`, `SP_STRKETIA` | beneficiary | Chronic condition flags (1 yes, 2 no) | Comorbidity count, condition prevalence |
| `MEDREIMB_IP/OP/CAR` | beneficiary | Annual reimbursement in the summary | Informational tie-out only |
| `CLM_ID`, `SEGMENT` | institutional | Claim ID and segment | Claim key |
| `CLM_FROM_DT`, `CLM_THRU_DT` | all claims | Claim dates | Validity, window, month |
| `CLM_ADMSN_DT`, `NCH_BENE_DSCHRG_DT` | inpatient | Admission and discharge dates | Stays, length of stay, readmission |
| `CLM_UTLZTN_DAY_CNT` | inpatient | Source utilization days | Compared with the date difference only |
| `PRVDR_NUM` | institutional | Facility provider number | Facility provider |
| `AT_PHYSN_NPI`, `OP_PHYSN_NPI`, `OT_PHYSN_NPI` | institutional | Physician NPIs | Provider dimension only |
| `CLM_PMT_AMT` | institutional | Payment from the Medicare trust fund | Payment |
| `ICD9_DGNS_CD_1..10`, `ADMTNG_ICD9_DGNS_CD` | institutional | ICD-9-CM diagnoses | Primary diagnosis, condition grouping |
| `HCPCS_CD_1..45` | institutional | HCPCS codes | ED proxy, procedure dimension |
| `ICD9_DGNS_CD_1..8` | carrier | Claim diagnoses | Primary diagnosis |
| `HCPCS_CD_1..13`, `PRF_PHYSN_NPI_1..13`, `TAX_NUM_1..13` | carrier | Line code, performing NPI, tax number | Lines, provider |
| `LINE_NCH_PMT_AMT_1..13` | carrier | Line payment | Payment |
| `LINE_BENE_PTB_DDCTBL_AMT`, `LINE_BENE_PRMRY_PYR_PD_AMT`, `LINE_COINSRNC_AMT`, `LINE_ALOWD_CHRG_AMT`, `LINE_PRCSG_IND_CD`, `LINE_ICD9_DGNS_CD` | carrier | Other line amounts and codes | Kept on `fact_claim_line`, not used in metrics |

Not loaded: prescription drug events, ICD-9 procedure codes, revenue and other institutional fields not listed.
