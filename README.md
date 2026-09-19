# Medicare Claims Utilization, Cost & Quality Analytics | CMS DE-SynPUF

[![CI](https://github.com/VijayChamakuri/medicare-claims-utilization-cost-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/VijayChamakuri/medicare-claims-utilization-cost-quality/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](pyproject.toml)

> **CMS synthetic claims - not real patient or provider performance.** Every result here is a pipeline demonstration on CMS DE-SynPUF synthetic data.

## Business problem

Where are utilization and paid-amount patterns concentrated across synthetic beneficiaries, care settings, conditions and providers, and which operational segments should a payer or provider analytics team review first?

This is an analytics and BI project, not a modeling contest. It turns synthetic Medicare inpatient, outpatient and carrier claims into a tested SQL star schema, written metric definitions, an Excel operations workbook, an offline dashboard and a Tableau data package. Payment fields keep their CMS names (`CLM_PMT_AMT`, `LINE_NCH_PMT_AMT`); they are Medicare trust fund payments, not costs or charges.

![Executive Overview page of the dashboard with monthly paid amount by setting and utilization KPIs](dashboard/screenshots/01_executive_overview.png)

Open [`dashboard/index.html`](dashboard/index.html) in a browser (one offline file, five pages). Screenshots: [utilization](dashboard/screenshots/02_utilization_payment.png), [provider operations](dashboard/screenshots/03_provider_operations.png), [quality and cohorts](dashboard/screenshots/04_quality_cohorts.png), [data quality and definitions](dashboard/screenshots/05_data_quality_definitions.png).

## Three verified synthetic-sample results

Computed from CMS DE-SynPUF sample 1 (about 5.6 million claims). Each is checked by the reconciliation and independent recomputation described below.

<!-- BEGIN generated:results -->
1. **Payment is concentrated.** In 2009, the top 5% of synthetic beneficiaries (5,727 of 114,538) held 39.2% of the paid amount ($197.9M of $504.8M).
2. **Inpatient stays drive payment, not volume.** In 2009, inpatient claims were 1.1% of claims but 48.6% of the paid amount; carrier (professional) claims carried 32.7% and outpatient 18.7%.
3. **A simple prior-year tier separates utilization.** In 2009, the high utilization risk tier was 17.5% of beneficiaries but 42.7% of the paid amount, with 528 admissions per 1,000 member-years against 91 in the low tier.
<!-- END generated:results -->

<!-- BEGIN generated:kpis -->
| Year | Beneficiaries | Claims | Paid amount | Admissions per 1,000 | ED proxy per 1,000 | Readmission proxy | Top 5% payment share |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2008 | 116,352 | 2,025,978 | $483.3M | 245 | 210 | 15.1% | 48.5% |
| 2009 | 114,538 | 2,210,561 | $504.8M | 232 | 248 | 7.5% | 39.2% |
| 2010 | 112,754 | 1,350,500 | $286.7M | 128 | 132 | 4.3% | 43.1% |
<!-- END generated:kpis -->

Monthly volume in the synthetic source tapers from mid-2009, so year-over-year comparisons are not interpretable. Read the table as a demonstration of the metrics, not as a trend.

## Data source and caveat

Official CMS 2008-2010 [DE-SynPUF](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf), sample 1: beneficiary summaries for three years plus inpatient, outpatient and carrier claims. URLs, retrieval date, sizes and SHA-256 hashes for every file, the codebook and the FAQ are in [`data/data_manifest.json`](data/data_manifest.json); downloads are verified and a changed file stops the run. Diagnosis grouping uses AHRQ CCS 2015 for ICD-9-CM (2008 to 2010 claims are ICD-9 era).

DE-SynPUF is synthetic and intended for development and training. It cannot estimate real Medicare rates, provider performance, savings or prevalence.

## Architecture

```mermaid
flowchart LR
    A[CMS zips] --> B[raw text tables] --> C[staging] --> D[star schema] --> E[marts]
    E --> F{reconciliation}
    A --> G[independent pandas recomputation] --> F
    E --> H[Excel] & I[Dashboard] & J[Tableau extracts]
```

Star schema: `dim_beneficiary`, `dim_date`, `dim_provider`, `dim_diagnosis`, `dim_procedure`, `dim_care_setting`; `fact_claim_header` (one row per claim), `fact_claim_line`, `fact_claim_diagnosis`, `fact_inpatient_stay`, `fact_beneficiary_year`; utilization, payment, quality, condition and provider marts. Grain and keys for every table: [table inventory](docs/table_inventory.md). Detail: [architecture](docs/architecture.md), [source to target mapping](docs/source_to_target_mapping.md).

## Reproduce

```bash
git clone https://github.com/VijayChamakuri/medicare-claims-utilization-cost-quality.git && cd medicare-claims-utilization-cost-quality
uv sync --extra dev
make fixture      # hand-calculated fixture pipeline, no download, under a minute
```

For the real sample (about 275 MB download including the codebook and FAQ, roughly 2 to 3 minutes to build on an Apple silicon laptop):

```bash
make all          # download and verify, build, validate, export, Excel, reports, Tableau extracts, dashboard
```

Requires Python 3.11 or 3.12 and `uv`. Stages can run alone: `download`, `build`, `validate`, `export`, `excel`, `reports`, `tableau`, `dashboard`, `readme`. Switching to another CMS sample is a change to `config/project.yml`.

## Model and metrics

Definitions, numerators, denominators, exclusions and caveats live in the [metric dictionary](docs/metric_dictionary.md) (generated from `config/metric_dictionary.yml`).

- **Utilization:** claims, inpatient admissions (continuous stays), an ED visit proxy (HCPCS 99281 to 99285), outpatient visits and carrier service lines, per 1,000 member-years.
- **Payment:** paid amount by setting, per beneficiary, per claim and per admission, and payment concentration in the top 5 percent of beneficiaries.
- **Quality monitoring:** a measure-inspired 30-day all-cause readmission proxy with explicit index and exclusion logic. Not a certified measure.
- **Risk tier:** a transparent points score from prior-year chronic condition flags, admissions and paid amount. It is a descriptive stratification, not CMS-HCC or any official risk adjustment.
- **Provider review flags:** a provider sitting above the interquartile fence of same-type peers. A prompt to review, never a finding about fraud or quality.

## Tableau and Excel artifacts

- **Excel:** [`excel/claims_operations_review.xlsx`](excel/claims_operations_review.xlsx) has nine sheets built from the marts, with live formulas for every rate, filters, freeze panes, conditional flags and a reconciliation sheet that ties workbook totals to DuckDB. No beneficiary rows.
- **Tableau:** there is **no Tableau workbook and no Tableau Public URL** in this repository. [`tableau/`](tableau/README.md) holds the data extracts, a field dictionary, calculated fields, a build guide and a QA checklist so a workbook can be built and checked. The reproducible BI artifact is the HTML dashboard above.
- **Stakeholder outputs:** [executive summary](reports/executive_summary.md), [provider action list](reports/provider_action_list.csv) (synthetic review flags), [data quality report](reports/data_quality_report.md).

## Tests and validation

- **Hand-calculated fixture.** Twelve beneficiaries, three settings, with transfers, deaths, readmissions inside and outside 30 days, duplicate rows, two-segment claims, malformed codes, negative payments and out-of-window claims. Every headline KPI is asserted exactly against values derived by hand ([derivation](tests/fixtures/README.md)), never from pipeline output.
- **SQL reconciliation.** Raw to staging to facts to marts, header to lines, keys and dates, with blocking checks that stop the run.
- **Independent recomputation.** [`validation.py`](src/medicare_claims/validation.py) recomputes claims, payments, admissions, ED proxy, readmission proxy and concentration in pandas from the raw CSVs, sharing no SQL. Money agrees to the cent. Tests tamper with the warehouse and confirm the checks fail.
- **CI** on Python 3.11 and 3.12 runs Ruff, mypy, pytest, the fixture end-to-end run, Excel structure and reconciliation, and README drift. `make test` runs the same checks locally.

## Limitations

Synthetic data throughout. Monthly volume tapers in the source, so trends are not interpretable. The beneficiary summary reimbursement fields do not tie to claim payments and are not used. There is no discharge status, place of service or planned-readmission flag, so the readmission and ED measures are proxies. Prescription drug events are not loaded. Provider flags mostly reflect facility size on this data. No claim of savings, outcomes, fraud detection, HEDIS or CMS-HCC, HIPAA compliance, Epic experience or a Tableau dashboard is made. See [limitations](docs/limitations.md), [code mapping and limits](docs/code_mapping_and_limits.md) and [privacy and governance](docs/privacy_and_governance.md).

Code is MIT licensed. See [CONTRIBUTING](CONTRIBUTING.md).
