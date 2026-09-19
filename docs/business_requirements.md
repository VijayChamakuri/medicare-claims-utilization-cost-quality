# Business requirements

> CMS synthetic claims - not real patient or provider performance.

**Decision question.** Where are utilization and paid-amount patterns concentrated across synthetic beneficiaries, care settings, conditions and providers, and which operational segments should a payer or provider analytics team review first?

This is an analytics and BI project, not a modeling contest. The only model is a transparent utilization risk tier.

| Stakeholder | Question | Metric | Where to see it | Decision it informs |
|---|---|---|---|---|
| Population-health or payer-operations leader | Where is payment concentrated? | Payment concentration (top 5 percent), payment per beneficiary | Dashboard page 1 and 4; Excel `Executive_Summary` | Which segment gets a first review |
| Utilization management | Which settings and conditions drive paid amount? | Setting mix, payment by primary diagnosis (CCS), paid per claim | Dashboard page 2; Excel `Monthly_Payments` | Where to focus authorization or care-management effort |
| Care management | Who should be looked at first? | Utilization risk tier, admissions per 1,000 by tier | Dashboard page 4; Excel `Member_Risk_Tiers` | Building a starting outreach list |
| Quality monitoring | How often are stays followed by another stay within 30 days? | 30-day readmission proxy and its exclusions | Dashboard page 4; Excel `Readmission_Review` | Whether to invest in a validated readmission measure |
| Provider analytics | Which providers sit far from their peers? | Provider review flags with reason codes | Dashboard page 3; `reports/provider_action_list.csv` | Which providers to compare against peers |
| Data owner | Can these numbers be trusted? | Reconciliation, data-quality counts, independent recomputation | Dashboard page 5; `reports/data_quality_report.md` | Whether to release a metric |

## Out of scope

Prescription drug events, savings or return-on-investment estimates, official risk adjustment (CMS-HCC), certified HEDIS measures, fraud detection, Epic or EHR data, and any claim about real Medicare.
