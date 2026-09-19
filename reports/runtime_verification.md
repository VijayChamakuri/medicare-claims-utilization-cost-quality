# Runtime verification

> CMS synthetic claims - not real patient or provider performance.

Commands run and what they returned. Environment: macOS on Apple silicon, DuckDB 1.5.5, pandas 2.3.3, openpyxl 3.1.5, `uv` for environments. Dates are 2026-09-19.

## Clean clone, Python 3.11 and 3.12

```bash
git clone <repo> && cd <repo>
UV_PYTHON=3.11 uv sync --extra dev && make test && make fixture && make check-readme
UV_PYTHON=3.12 uv sync --extra dev && make test && make fixture && make check-readme
```

| Check | Python 3.11 | Python 3.12 |
|---|---|---|
| `ruff check src tests scripts` | pass | pass |
| `mypy` (16 source files) | pass | pass |
| `pytest --cov` | 75 passed, 93% coverage | 75 passed, 93% coverage |
| `make fixture` (build, validate, export, Excel, reports, Tableau extracts, dashboard) | pass | pass |
| `make check-readme` | README matches `reports/headline_kpis.json` | same |

The fixture run writes to `build/fixture/` so it never overwrites the real-sample outputs.

## Real CMS sample 1

```bash
uv run python -m medicare_claims all
```

Ten files verified against the manifest (275.5 MB including codebook and FAQ), warehouse rebuilt from scratch, then validated, exported, reported and rendered. Wall time was 2 minutes 9 seconds with the downloads already cached; download time depends on the network and was not re-measured in this run.

| Item | Result |
|---|---|
| Claims in `fact_claim_header` | 5,587,855 |
| Claim lines in `fact_claim_line` | 13,163,019 |
| Diagnosis rows in `fact_claim_diagnosis` | 12,950,443 |
| Continuous inpatient stays | 64,359 |
| Beneficiaries | 116,352 |
| SQL reconciliation | 33 of 41 checks passed; every blocking check passed; the 8 that differ are informational tie-outs of beneficiary-summary MEDREIMB fields to claim payments (differences of 0.2 to 8.6 percent, documented, not used in any metric) |
| Independent pandas recomputation | 42 of 42 checks agree with the warehouse (counts exact, money within half a cent) |
| Excel workbook | 9 sheets; recalculated with an independent formula engine (`formulas` package): 6,514 formulas, 0 errors, all 10 reconciliation ties PASS |
| Dashboard | five pages captured headless and inspected; synthetic banner present on every page |
| README numbers | regenerated from `reports/headline_kpis.json` and drift-checked |

## Defects found by verification and fixed

- Carrier service lines were inflated about 13 times by CMS zero-filled padding slots. The line filter now counts a line only when it has a HCPCS code, an NPI or a non-zero payment. The independent pandas check had the same flaw and now uses the same definition, and a regression fixture covers it.
- Two inpatient stays fell out of the monthly mart when the claim start and admission dates straddled the window start. Service date now uses the admission date for inpatient claims.
- Provider review flags initially flagged about 900 facilities. Peers are now split by inpatient and outpatient settings, a fence is applied only when the interquartile range is positive, and the default multiple is 3.0. Volume flags still mostly track facility size, which is documented.

## Overclaim term audit

Search of all text in the repository for `HIPAA compliant`, `HEDIS`, `CMS-HCC`, `Epic`, `Clarity`, `Caboodle`, `real patients`, `saved`, `reduced`, `Tableau dashboard`, plus `savings` and `fraud`. `saved` and `reduced` do not appear. Every other occurrence is a negation, a limitation, or a contributor rule against adding it. No sentence claims certified HEDIS, CMS-HCC, HIPAA compliance, Epic experience, savings, fraud detection or a Tableau dashboard. No em dashes and no AI attribution appear in the repository.

## Not verified

- No Tableau workbook exists, so nothing was checked in Tableau.

## Hosted CI (GitHub Actions)

- Push run: lint, types, tests and the fixture pipeline passed on Python 3.11 and Python 3.12; README drift check passed.
- Manual dispatch of the full workflow: the same two jobs passed, the official source link check passed (every CMS and AHRQ URL in `config/project.yml` responded), and the real-data job passed. That job downloaded all ten CMS files on the runner, verified hashes, built the warehouse, validated, exported and reported, and `git diff` of `README.md` and `reports/headline_kpis.json` against the committed versions was empty, so the published numbers reproduce from the official files on a clean machine (8 minutes 22 seconds end to end).
- The real-data and link jobs also run weekly on a schedule.
