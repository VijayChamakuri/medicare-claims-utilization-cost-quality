# Contributing

```bash
uv sync --extra dev
make test         # ruff, mypy, pytest with coverage
make fixture      # hand-calculated fixture pipeline (writes to build/fixture)
make all          # real sample 1: download, build, validate, export, Excel, reports, Tableau extracts, dashboard
make check-readme # README numbers must match reports/headline_kpis.json
```

Requires Python 3.11 or 3.12 and `uv`.

- **Definitions first.** A new metric needs an entry in `config/metric_dictionary.yml` (numerator, denominator, exclusions, unit, source fields, caveat) before it appears anywhere else.
- **Hand-derive, then test.** Add a case to `tests/fixtures/build_fixture.py`, derive the expected value by hand in `tests/fixtures/README.md` and `expected_kpis.json`, and only then run the pipeline. Never copy a value from pipeline output into an expected value.
- **Independent check.** A new headline KPI also gets an independent pandas computation in `validation.py`.
- **README numbers** live in generated blocks. Change `src/medicare_claims/reports.py` and run `make readme`; do not edit a block by hand.
- **Payment fields keep CMS names.** Do not rename payment to "cost".
- **Synthetic only.** Never add real patient or provider data or any direct identifier. Every artifact carries the synthetic banner.
- **No overclaims.** Do not add claims of HIPAA compliance, HEDIS or CMS-HCC, fraud detection, savings, Epic experience or a Tableau dashboard unless the supporting artifact exists.
- **No AI attribution in git.** Commits carry only the author's identity.
