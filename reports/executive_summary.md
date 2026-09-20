# Executive summary: Medicare claims utilization, payment and quality monitoring

> **CMS synthetic claims - not real patient or provider performance.** A pipeline demonstration on CMS DE-SynPUF synthetic data. Nothing here estimates real Medicare rates, provider performance, savings or prevalence.

**Audiences:** a payer or provider operations leader (trend, concentration, review queue), a quality analyst (proxy logic, cohorts, exclusions) and the data owner (completeness, reconciliation, failed checks).

## 1. What stands out

1. **Payment is concentrated.** In 2009, the top 5% of synthetic beneficiaries (5,727 of 114,538) held 39.2% of the paid amount ($197.9M of $504.8M).
2. **Inpatient stays drive payment, not volume.** In 2009, inpatient claims were 1.1% of claims but 48.6% of the paid amount; carrier (professional) claims carried 32.7% and outpatient 18.7%.
3. **A simple prior-year tier separates utilization.** In 2009, the high utilization risk tier was 17.5% of beneficiaries but 42.7% of the paid amount, with 528 admissions per 1,000 member-years against 91 in the low tier.

## 2. What action should be considered

- **Operations leader:** point a first utilization or care-management review at the small group of beneficiaries that holds most of the paid amount, and at inpatient stays, which carry about half of it.
- **Operations leader:** work the provider review queue (`provider_action_list.csv`, Tableau Provider Operations) against same-type peers. A flag is a prompt to look, not a finding about quality or conduct.
- **Quality analyst:** treat the readmission proxy and the utilization risk tier as starting lists to validate, not as measures to report.
- **Data owner:** keep the blocking reconciliation gate and the dbt tests as release criteria for any refresh.

## 3. What evidence supports it

- Every number above is generated from the DuckDB marts and tied out three ways: blocking SQL reconciliation, an independent pandas recomputation from the raw files, and a dbt build that matches the legacy tables row for row.
- The Excel review and the Tableau workbook tie their KPI values back to the same marts (`excel/claims_operations_review.xlsx` Reconciliation sheet, `tableau/validation_evidence.csv`).
- Definitions, grains and quality checks for each KPI: [metric dictionary](../docs/metric_dictionary.md).

## 4. What cannot be concluded from synthetic DE-SynPUF

- Synthetic data. The 30-day readmission proxy was 9.9% of eligible index stays overall, ranging from 15.1% in 2008 to 4.3% in 2010. Follow-up is truncated near the end of the source and volumes taper, so no trend can be read from it.
- No real Medicare rate, provider performance, prevalence or trend. Monthly volume tapers in the source from mid-2009.
- The ED measure and the readmission measure are proxies: there is no revenue center, place of service, discharge status or planned-readmission flag. They are not HEDIS measures, and the risk tier is not CMS-HCC.
- Inpatient, outpatient and carrier claims only. Prescription drug events are not loaded.
- No savings, impact or outcome is claimed or estimated.

## 5. What must be validated on real, governed data before any action

1. Rebuild the same metrics on a governed claims extract and confirm the concentration and inpatient share hold.
2. Replace the readmission and ED proxies with discharge-status, planned-readmission and revenue-center logic, and compare with any certified measure the organization reports.
3. Calibrate provider review thresholds with clinical and payment-integrity reviewers before any flag is acted on.
4. Confirm access controls, minimum-necessary fields and small-cell suppression (see the privacy and governance note).

Definitions: [metric dictionary](../docs/metric_dictionary.md). Data quality: [data quality report](data_quality_report.md).
