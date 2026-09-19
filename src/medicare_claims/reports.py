"""Generated stakeholder artifacts and the README numeric blocks (checked for drift in CI)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import duckdb
import pandas as pd

from medicare_claims.config import Config
from medicare_claims.export import BANNER, datasets, provider_action_list
from medicare_claims.metrics import compute_kpis
from medicare_claims.quality import all_quality
from medicare_claims.validation import compare

MARK = re.compile(r"(<!-- BEGIN generated:(?P<name>[a-z_]+) -->\n)(?P<body>.*?)(<!-- END generated:(?P=name) -->)", re.S)


def money(x: float, digits: int = 1) -> str:
    return f"${x / 1e6:,.{digits}f}M"


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def headline(con: duckdb.DuckDBPyConnection, config: Config) -> dict[str, Any]:
    """Computed numbers that the README, executive summary and drift check all read."""
    ds = datasets(con, config)
    kpis = compute_kpis(con)
    annual = ds["kpi_annual"].set_index("year")
    tiers = ds["risk_tier_summary"]
    pay = ds["annual_by_setting"]
    years = [int(y) for y in annual.index]
    focus = 2009 if 2009 in years else years[-1]
    conc = ds["payment_concentration"].set_index("year").loc[focus]
    setting_pay = pay[pay["year"] == focus].set_index("setting")
    total_pay = float(setting_pay["payment_amount"].sum())
    total_claims = float(setting_pay["claims"].sum())
    t = tiers[(tiers["year"] == focus) & (tiers["utilization_risk_tier"] != "not_assessed")].set_index("utilization_risk_tier")
    high, low = (t.loc["high"], t.loc["low"]) if {"high", "low"} <= set(t.index) else (None, None)
    return {
        "profile": config.profile_name,
        "focus_year": focus,
        "years": years,
        "kpi_annual": json.loads(annual.reset_index().to_json(orient="records")),
        "concentration": {"year": focus, "top_count": int(conc["top_count"]), "beneficiaries": int(conc["beneficiaries"]),
                          "top_payment": float(conc["top_payment"]), "total_payment": float(conc["total_payment"]),
                          "top_share": float(conc["top_share"])},
        "setting_mix": {"year": focus, "inpatient_payment_share": float(setting_pay.loc["inpatient", "payment_amount"] / total_pay),
                        "inpatient_claim_share": float(setting_pay.loc["inpatient", "claims"] / total_claims),
                        "carrier_payment_share": float(setting_pay.loc["carrier", "payment_amount"] / total_pay),
                        "outpatient_payment_share": float(setting_pay.loc["outpatient", "payment_amount"] / total_pay)},
        "risk_tier": None if high is None or low is None else {
            "year": focus, "high_beneficiaries": int(high["beneficiaries"]),
            "high_share_of_beneficiaries": float(high["beneficiaries"] / t["beneficiaries"].sum()),
            "high_share_of_payment": float(high["payment_amount"] / t["payment_amount"].sum()),
            "high_admissions_per_1000": float(high["admissions_per_1000_member_years"]),
            "low_admissions_per_1000": float(low["admissions_per_1000_member_years"]),
            "high_payment_per_beneficiary": float(high["payment_per_beneficiary"]),
            "low_payment_per_beneficiary": float(low["payment_per_beneficiary"])},
        "readmission": {y: kpis["readmission"][y] for y in kpis["readmission"]},
        "flagged_providers": int(con.execute("select count(*) from mart_provider_performance where review_flag").fetchone()[0]),  # type: ignore[index]
    }


def _observations(h: dict[str, Any]) -> list[str]:
    c, m, r = h["concentration"], h["setting_mix"], h["risk_tier"]
    out = [
        f"**Payment is concentrated.** In {c['year']}, the top 5% of synthetic beneficiaries ({c['top_count']:,} of "
        f"{c['beneficiaries']:,}) held {pct(c['top_share'])} of the paid amount ({money(c['top_payment'])} of {money(c['total_payment'])}).",
        f"**Inpatient stays drive payment, not volume.** In {m['year']}, inpatient claims were {pct(m['inpatient_claim_share'])} of claims "
        f"but {pct(m['inpatient_payment_share'])} of the paid amount; carrier (professional) claims carried "
        f"{pct(m['carrier_payment_share'])} and outpatient {pct(m['outpatient_payment_share'])}.",
    ]
    if r:
        out.append(
            f"**A simple prior-year tier separates utilization.** In {r['year']}, the high utilization risk tier was "
            f"{pct(r['high_share_of_beneficiaries'])} of beneficiaries but {pct(r['high_share_of_payment'])} of the paid amount, with "
            f"{r['high_admissions_per_1000']:,.0f} admissions per 1,000 member-years against {r['low_admissions_per_1000']:,.0f} in the low tier.")
    return out


def _readmission_sentence(rd: dict[str, Any], years: list[int]) -> str:
    defined = [(y, rd[str(y)]["rate"]) for y in years if rd.get(str(y), {}).get("rate") is not None]
    overall = rd["all"]["rate"]
    if overall is None or not defined:
        return "The 30-day readmission proxy is undefined because no index stays are eligible."
    span = f", ranging from {pct(defined[0][1])} in {defined[0][0]} to {pct(defined[-1][1])} in {defined[-1][0]}" if len(defined) > 1 else ""
    return (f"The 30-day readmission proxy was {pct(overall)} of eligible index stays overall{span}. "
            "Follow-up is truncated near the end of the source and volumes taper, so no trend can be read from it.")


def executive_summary(h: dict[str, Any]) -> str:
    obs = _observations(h)
    rd = h["readmission"]
    lines = [
        "# Executive summary: Medicare claims utilization, payment and quality monitoring", "",
        f"> **{BANNER}** A pipeline demonstration on CMS DE-SynPUF synthetic data. Nothing here estimates real Medicare rates, provider performance, savings or prevalence.", "",
        "**For:** a population-health or payer-operations leader deciding where to point a first review.", "",
        "## Three computed observations", "",
        *[f"{i}. {text}" for i, text in enumerate(obs, start=1)], "",
        "## What this would mean operationally", "",
        "- **Concentrated payment** is where a utilization-management or care-management team would look first: a small share of beneficiaries and mostly inpatient stays.",
        "- **The tier** is a transparent starting list, not a risk model. It uses only prior-year chronic condition flags, admissions and paid amount, and it can be recomputed and challenged by any analyst.",
        "- **Provider review flags** (see `provider_action_list.csv`) are prompts to look at peers with unusual payment per claim or volume. They are not findings about quality or conduct.", "",
        "## Recommended follow-up analysis", "",
        "1. Break the concentrated payment down by primary diagnosis category (AHRQ CCS) to see which conditions the top beneficiaries share.",
        "2. Test whether the readmission proxy and tier hold their shape on a real, governed dataset with discharge status and planned-readmission flags.",
        "3. Review flagged providers against peers of the same type before any conclusion.", "",
        "## Limits", "",
        f"- Synthetic data. {_readmission_sentence(rd, h['years'])}",
        "- Inpatient, outpatient and carrier claims only. Prescription drug events are not loaded.",
        "- No savings, impact or outcome is claimed or estimated.", "",
        "Definitions: [metric dictionary](../docs/metric_dictionary.md). Data quality: [data quality report](data_quality_report.md).", "",
    ]
    return "\n".join(lines)


def data_quality_report(con: duckdb.DuckDBPyConnection, config: Config, independent: pd.DataFrame | None) -> str:
    q = all_quality(con)
    c, k = q["counts"], q["codes"]
    recon = con.execute("select check_name, category, expected, actual, difference, blocking, passed from reconciliation_results "
                        "order by category, check_name").df()
    blocking = recon[recon["blocking"]]
    independent_text = ("not run" if independent is None
                        else f"{int(independent['passed'].sum())} of {len(independent)} checks agree")
    lines = ["# Data quality report", "", f"> {BANNER}", "",
             f"Profile: `{config.profile_name}`. Generated by `medicare-claims reports`.", "",
             "## Reconciliation", "",
             f"- Blocking checks: {int(blocking['passed'].sum())} of {len(blocking)} passed.",
             f"- Independent pandas recomputation: {independent_text}.", ""]
    info = recon[recon["category"] == "informational"]
    if len(info) and info["expected"].notna().any():
        lines += ["Informational tie-out of the beneficiary summary `MEDREIMB_*` annual fields to claim payments (not used in any metric):", "",
                  "| Check | Summary field | Claim payment | Difference |", "|---|---:|---:|---:|"]
        for r in info.dropna(subset=["expected"]).itertuples():
            lines.append(f"| {r.check_name} | {r.expected:,.0f} | {r.actual:,.0f} | {r.difference / r.expected * 100:.1f}% |")
        lines += ["", "The summary fields and claim payments were synthesized separately by CMS and do not tie. All payment metrics use claim payment fields.", ""]
    lines += ["## Claim-level checks", "", "| Check | Inpatient | Outpatient | Carrier |", "|---|---:|---:|---:|"]
    for label, key in (("Exact duplicate rows dropped", "duplicate_rows_dropped"), ("Impossible or missing dates", "invalid_date_claims"),
                       ("Dated outside the study window", "outside_study_window_claims"), ("Negative payment (adjustment) claims", "negative_payment_claims"),
                       ("Multi-segment claims merged", "multi_segment_claims")):
        d = c[key]
        lines.append(f"| {label} | {d['inpatient']:,} | {d['outpatient']:,} | {d['carrier']:,} |")
    lines += ["", f"Payment excluded for invalid dates: ${c['excluded_payment_invalid_dates']:,.2f}. Payment excluded as outside the window: ${c['excluded_payment_outside_window']:,.2f}.", "",
              "## Codes", "",
              f"- Diagnosis codes: {k['distinct_diagnosis_codes']:,} distinct; {k['diagnosis_invalid_format']:,} of {k['diagnosis_rows']:,} claim-diagnosis rows have an invalid ICD-9-CM format; {k['diagnosis_unmapped_valid']:,} are valid but not in CCS 2015.",
              f"- HCPCS codes: {k['distinct_procedure_codes']:,} distinct; {k['procedure_invalid_format']:,} with an invalid format.",
              "- Claims missing a primary diagnosis: " + ", ".join(f"{s} {n:,} of {k['claims_by_setting'].get(s, 0):,}" for s, n in sorted(k['claims_missing_primary_dx'].items())) + ".", "",
              "## Other observations", "",
              f"- Inpatient stays whose source `CLM_UTLZTN_DAY_CNT` disagrees with discharge minus admission: {k['stays_source_utilization_day_mismatch']:,} of {k['stays_with_source_utilization_days']:,}. The date difference is used.",
              f"- Analytic claims with zero payment: {k['zero_payment_claims']:,}. Claims whose beneficiary is absent from the summary files: {k['orphan_claims']:,}. Claims dated after the beneficiary's death date: {k['claims_after_death']:,}.", ""]
    return "\n".join(lines)


GRAIN = {
    "dim_date": ("one row per calendar day", "date_key"),
    "dim_beneficiary": ("one row per synthetic beneficiary", "beneficiary_id"),
    "dim_provider": ("one row per provider ID and type (facility PRVDR_NUM or NPI)", "provider_type, provider_id"),
    "dim_diagnosis": ("one row per normalized ICD-9-CM code seen on a claim", "diagnosis_code"),
    "dim_procedure": ("one row per normalized HCPCS code seen on a claim", "procedure_code"),
    "dim_care_setting": ("one row per care setting", "care_setting"),
    "fact_claim_header": ("one row per claim (beneficiary + CLM_ID within a setting, segments merged)", "claim_key"),
    "fact_claim_line": ("one row per carrier line, or per institutional HCPCS position", "claim_key, line_num"),
    "fact_claim_diagnosis": ("one row per claim and distinct diagnosis code", "claim_key, diagnosis_code"),
    "fact_inpatient_stay": ("one row per continuous inpatient stay", "stay_key"),
    "fact_beneficiary_year": ("one row per beneficiary and year", "beneficiary_id, year"),
    "mart_member_month": ("one row per beneficiary, year and month", "beneficiary_id, year, month"),
    "mart_utilization_monthly": ("one row per month and care setting", "month_start, setting"),
    "mart_utilization_annual": ("one row per year and care setting", "year, setting"),
    "mart_payment_monthly": ("one row per month, setting and payment field", "month_start, setting"),
    "mart_payment_annual": ("one row per year, setting and payment field", "year, setting"),
    "mart_beneficiary_year_summary": ("one row per beneficiary and year", "beneficiary_id, year"),
    "mart_payment_concentration": ("one row per year", "year"),
    "mart_demographic_summary": ("one row per year, sex, race and age band", "year, sex, race, age_band"),
    "mart_member_risk": ("one row per beneficiary and year", "beneficiary_id, year"),
    "mart_readmission_index": ("one row per inpatient stay considered as an index", "stay_key"),
    "mart_quality_monitoring": ("one row per discharge year and risk tier", "year, utilization_risk_tier"),
    "mart_condition_summary": ("one row per condition, year and setting", "condition_type, year, setting, condition_id"),
    "mart_provider_performance": ("one row per provider, provider type and year", "provider_type, provider_id, year"),
    "reconciliation_results": ("one row per reconciliation check", "check_name"),
}


def table_inventory(con: duckdb.DuckDBPyConnection, config: Config) -> str:
    lines = ["# Table inventory", "", f"> Generated by `medicare-claims reports` for profile `{config.profile_name}`. Row counts are from that build.", "",
             "| Table | Grain | Key | Rows |", "|---|---|---|---:|"]
    for table, (grain, key) in GRAIN.items():
        n = int(con.execute(f"select count(*) from {table}").fetchone()[0])  # type: ignore[index]
        lines.append(f"| `{table}` | {grain} | `{key}` | {n:,} |")
    return "\n".join(lines) + "\n"


def metric_dictionary_doc(config: Config) -> str:
    from medicare_claims.export import metric_dictionary

    frame = metric_dictionary(config)
    lines = ["# Metric dictionary", "", f"> {BANNER}", "",
             f"Generated from `config/metric_dictionary.yml` (contract version {int(frame['contract_version'].iloc[0])}), the single "
             "source for this page, the Excel `Metric_Dictionary` sheet, the Tableau field dictionary and "
             "`tableau/expected_kpis.csv`. Change rules: [metric governance](metric_governance.md).", ""]
    for r in frame.itertuples():
        lines += [f"## {r.name}", "",
                  f"- **ID and version:** `{r.id}` v{r.version}" + (" (headline KPI)" if r.headline else ""),
                  f"- **Business question:** {r.business_question}",
                  f"- **Owner role:** {r.owner_role}",
                  f"- **Description:** {r.description}",
                  f"- **Grain:** {r.grain}",
                  f"- **Source model:** `{r.source_model}`",
                  f"- **Calculation:** {r.calculation}",
                  f"- **Numerator:** {r.numerator}",
                  f"- **Denominator:** {r.denominator}",
                  f"- **Inclusions:** {r.inclusions}",
                  f"- **Exclusions:** {r.exclusions}",
                  f"- **Valid dimensions:** {r.valid_dimensions}",
                  f"- **Time basis:** {r.time_basis}",
                  f"- **Refresh expectation:** {r.refresh_expectation}",
                  f"- **Quality checks:** {r.quality_checks}",
                  f"- **Unit:** {r.unit}",
                  f"- **Source fields:** {r.source_fields}",
                  f"- **Known limits:** {r.known_limits}",
                  f"- **Tableau field:** `{r.tableau_field}`", ""]
    return "\n".join(lines)

def write_reports(con: duckdb.DuckDBPyConnection, config: Config, run_independent: bool = True) -> dict[str, Any]:
    out_dir = config.reports_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = config.artifacts_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "table_inventory.md").write_text(table_inventory(con, config), encoding="utf-8")
    (docs_dir / "metric_dictionary.md").write_text(metric_dictionary_doc(config), encoding="utf-8")
    independent = compare(con, config) if run_independent else None
    h = headline(con, config)
    (out_dir / "headline_kpis.json").write_text(json.dumps(h, indent=2, sort_keys=True, default=float) + "\n", encoding="utf-8")
    (out_dir / "executive_summary.md").write_text(executive_summary(h), encoding="utf-8")
    (out_dir / "data_quality_report.md").write_text(data_quality_report(con, config, independent), encoding="utf-8")
    provider_action_list(con, config).to_csv(out_dir / "provider_action_list.csv", index=False)
    if independent is not None:
        independent.to_csv(out_dir / "independent_reconciliation.csv", index=False)
    return h


# ---- README generated blocks -------------------------------------------------------------------

def block_results(h: dict[str, Any]) -> str:
    return "\n".join(f"{i}. {t}" for i, t in enumerate(_observations(h), start=1))


def block_kpis(h: dict[str, Any]) -> str:
    rows = ["| Year | Beneficiaries | Claims | Paid amount | Admissions per 1,000 | ED proxy per 1,000 | Readmission proxy | Top 5% payment share |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in h["kpi_annual"]:
        rows.append(f"| {r['year']} | {r['beneficiaries']:,} | {r['claims']:,.0f} | {money(r['payment_total'])} | "
                    f"{r['admissions_per_1000_member_years']:,.0f} | {r['ed_proxy_per_1000_member_years']:,.0f} | "
                    f"{pct(r['readmission_rate']) if r['readmission_rate'] is not None else 'n/a'} | {pct(r['top_5pct_payment_share'])} |")
    return "\n".join(rows)


BLOCKS: dict[str, Callable[[dict[str, Any]], str]] = {"results": block_results, "kpis": block_kpis}


def render_blocks(h: dict[str, Any]) -> dict[str, str]:
    return {name: fn(h).strip() for name, fn in BLOCKS.items()}


def write_readme(config: Config) -> None:
    h = json.loads((config.reports_dir / "headline_kpis.json").read_text(encoding="utf-8"))
    rendered = render_blocks(h)
    path = config.readme_path
    text = path.read_text(encoding="utf-8")
    path.write_text(MARK.sub(lambda m: f"{m.group(1)}{rendered.get(m.group('name'), m.group('body').strip())}\n{m.group(4)}", text), encoding="utf-8")


def check_readme(config: Config) -> list[str]:
    h = json.loads((config.reports_dir / "headline_kpis.json").read_text(encoding="utf-8"))
    rendered = render_blocks(h)
    text = config.readme_path.read_text(encoding="utf-8")
    found = {m.group("name"): m.group("body").strip() for m in MARK.finditer(text)}
    return [f"block '{n}' is {'missing from' if n not in found else 'out of sync with'} README.md"
            for n, body in rendered.items() if found.get(n) != body]
