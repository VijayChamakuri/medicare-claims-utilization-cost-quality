# Privacy and governance

> CMS synthetic claims - not real patient or provider performance.

- **Data.** CMS 2008-2010 DE-SynPUF is synthetic public data intended for development and training. It contains no real protected health information (PHI). Beneficiary and provider identifiers are synthetic codes.
- **Synthetic data avoids PHI exposure but does not prove HIPAA compliance.** Nothing in this repository demonstrates, certifies or implies that a HIPAA obligation has been met. HHS describes the Privacy Rule at [hhs.gov](https://www.hhs.gov/hipaa/for-professionals/privacy/laws-regulations/index.html).
- **No direct identifiers may be added.** Contributions must not introduce real names, real identifiers, dates of service tied to a real person, or any real patient or provider data.
- **Screenshots and exports remain synthetic.** Every screenshot, workbook and CSV carries the synthetic banner, and exports are aggregates only (no beneficiary-level rows).

## What a real deployment would need

These controls are described, not implemented here:

| Control | What it would involve |
|---|---|
| Role-based access control | Analysts see only the minimum tables and columns their role requires |
| Minimum necessary | Limit fields, rows and time ranges to the stated purpose |
| Encryption | At rest and in transit, with managed keys |
| Audit logs | Who queried or exported which data, and when |
| Retention | Documented retention and disposal schedules |
| Approved disclosure | A defined approval path before data or aggregates leave the environment |
| Small-cell suppression | Suppress or combine counts below a set threshold before sharing |
| Incident process | A written process for suspected exposure |

## Small cells

This synthetic data set is large enough that no reported cell is small. A real deployment should suppress or combine cells under a policy threshold (commonly 10) in every extract, dashboard and workbook.

## Provider and beneficiary flags

Provider review flags and utilization risk tiers describe synthetic data only. In a real setting a flag would need clinical and compliance review before any action, must not be used as evidence of fraud or poor quality on its own, and should be monitored for disparate impact across groups.
