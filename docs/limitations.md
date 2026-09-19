# Limitations

> CMS synthetic claims - not real patient or provider performance.

**Every result is a pipeline demonstration on synthetic data.** DE-SynPUF was built for development and training. It cannot estimate real Medicare rates, provider performance, savings or prevalence.

## Data

- **Synthetic volumes taper.** Monthly claim volume and paid amount fall steadily from mid-2009 to the end of 2010. Year-over-year and monthly trends are not interpretable. The 30-day readmission proxy also falls each year, for the same reason and because follow-up is truncated near the study end.
- **Beneficiary summary payments do not tie to claims.** The `MEDREIMB_*` annual fields differ from claim payments by 0.2 to 8.6 percent. Claim payments are used for every metric. See the [data quality report](../reports/data_quality_report.md).
- **No place of service, revenue center, discharge status or planned-readmission flag.** This limits the ED proxy and the readmission proxy.
- **Coverage months are counts.** Member months assume coverage runs from January.
- **Prescription drug events are not loaded.** Pharmacy claims are out of scope for this version.
- **Provider attributes.** Only IDs exist: no specialty, geography or ownership.

## Metrics

- **Readmission proxy** is measure-inspired, not certified. Any stay can be both an index and a readmission. Transfers are merged into one stay, which is a rule, not a fact.
- **Utilization risk tier** is a transparent descriptive stratification. It is not CMS-HCC, RAF or official risk adjustment and has not been validated for prediction.
- **Provider review flags** compare providers against peers of the same type and year with a fence of Q3 plus a multiple of the interquartile range. On this data, payment-per-claim outliers are rare (CMS synthesized payments in a narrow range) and volume flags mostly track facility size. Flags never indicate fraud or quality.
- **Concentration** is descriptive. It says nothing about why payment is concentrated.

## Claims and scope

- No claim of savings, return on investment, outcomes, HIPAA compliance, HEDIS certification, Epic or EHR experience, or Tableau delivery is made anywhere in this repository. See `tableau/README.md` for the Tableau status.
- One documented sample (sample 1). Samples 2 to 20 are a configuration change but have not been run.
