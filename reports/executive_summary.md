# Executive summary: Medicare claims utilization, payment and quality monitoring

> **CMS synthetic claims - not real patient or provider performance.** A pipeline demonstration on CMS DE-SynPUF synthetic data. Nothing here estimates real Medicare rates, provider performance, savings or prevalence.

**For:** a population-health or payer-operations leader deciding where to point a first review.

## Three computed observations

1. **Payment is concentrated.** In 2009, the top 5% of synthetic beneficiaries (5,727 of 114,538) held 39.2% of the paid amount ($197.9M of $504.8M).
2. **Inpatient stays drive payment, not volume.** In 2009, inpatient claims were 1.1% of claims but 48.6% of the paid amount; carrier (professional) claims carried 32.7% and outpatient 18.7%.
3. **A simple prior-year tier separates utilization.** In 2009, the high utilization risk tier was 17.5% of beneficiaries but 42.7% of the paid amount, with 528 admissions per 1,000 member-years against 91 in the low tier.

## What this would mean operationally

- **Concentrated payment** is where a utilization-management or care-management team would look first: a small share of beneficiaries and mostly inpatient stays.
- **The tier** is a transparent starting list, not a risk model. It uses only prior-year chronic condition flags, admissions and paid amount, and it can be recomputed and challenged by any analyst.
- **Provider review flags** (see `provider_action_list.csv`) are prompts to look at peers with unusual payment per claim or volume. They are not findings about quality or conduct.

## Recommended follow-up analysis

1. Break the concentrated payment down by primary diagnosis category (AHRQ CCS) to see which conditions the top beneficiaries share.
2. Test whether the readmission proxy and tier hold their shape on a real, governed dataset with discharge status and planned-readmission flags.
3. Review flagged providers against peers of the same type before any conclusion.

## Limits

- Synthetic data. The 30-day readmission proxy was 9.9% of eligible index stays overall, ranging from 15.1% in 2008 to 4.3% in 2010. Follow-up is truncated near the end of the source and volumes taper, so no trend can be read from it.
- Inpatient, outpatient and carrier claims only. Prescription drug events are not loaded.
- No savings, impact or outcome is claimed or estimated.

Definitions: [metric dictionary](../docs/metric_dictionary.md). Data quality: [data quality report](data_quality_report.md).
