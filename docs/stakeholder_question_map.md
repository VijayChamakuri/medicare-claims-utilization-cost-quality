# Stakeholder question map

> CMS synthetic claims - not real patient or provider performance.

| Tableau page | Audience | Questions it answers | Metrics (contract IDs) | Excel sheet |
|---|---|---|---|---|
| Executive Overview | Payer or provider operations leader | How much was paid, where, and how is it spread over time? How concentrated is it? | `beneficiaries`, `claims`, `paid_amount`, `admissions_per_1000`, `ed_proxy_per_1000`, `readmission_proxy`, `top5_payment_share` | Executive_Summary, Monthly_Utilization, Monthly_Payments |
| Utilization & Payment | Operations leader, finance analyst | Which settings, demographic groups and risk tiers carry payment? What is paid per beneficiary, claim and admission? | `paid_per_beneficiary`, `paid_per_claim`, `paid_per_admission`, `utilization_risk_tier` | Monthly_Payments, Member_Risk_Tiers |
| Provider Operations | Operations leader, provider relations | Which facilities sit far above same-type peers and belong in a review queue? | `provider_review_flag` | Provider_Review |
| Quality & Cohorts | Quality analyst | How is the readmission proxy built, and how does it vary by risk tier? Which conditions carry payment? | `readmission_proxy`, `admissions_per_1000`, `utilization_risk_tier` | Readmission_Review, Member_Risk_Tiers |
| Data Quality & Definitions | Data owner | Did the load reconcile? What was excluded and why? Which source files and definitions were used? | all, through the contract | Data_Quality, Metric_Dictionary, Reconciliation |

The executive summary (`reports/executive_summary.md`) is written for the same three audiences and answers what stands out, what to consider, the evidence, what cannot be concluded, and what to validate on real data first.
