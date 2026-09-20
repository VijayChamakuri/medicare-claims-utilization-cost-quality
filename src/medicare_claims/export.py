"""Aggregated datasets for the dashboard, Excel workbook and Tableau package.

Nothing exported here is beneficiary-level: every table is an aggregate of synthetic claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from medicare_claims.config import Config
from medicare_claims.metrics import compute_kpis

BANNER = "CMS synthetic claims - not real patient or provider performance."


def metric_dictionary(config: Config) -> pd.DataFrame:
    path = config.root / "config" / "metric_dictionary.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    frame = pd.DataFrame(data["metrics"])
    frame["contract_version"] = int(data["contract_version"])
    # Short aliases kept for the dashboard's definitions page and the Excel sheet.
    frame["definition"] = frame["description"]
    frame["caveat"] = frame["known_limits"]
    for column in ("valid_dimensions", "quality_checks"):
        frame[column] = frame[column].map(lambda v: ", ".join(v) if isinstance(v, list) else v)
    return frame


def kpi_annual(kpis: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for year in sorted(kpis["beneficiaries"]):
        rd = kpis["readmission"].get(year, {})
        rows.append({
            "year": int(year),
            "beneficiaries": kpis["beneficiaries"][year],
            "member_months": kpis["member_months"][year],
            "member_years": kpis["member_years"][year],
            "claims": kpis["claims_total"].get(year, 0),
            "payment_total": kpis["payment_total"].get(year, 0.0),
            "payment_per_beneficiary": kpis["payment_per_beneficiary"].get(year),
            "payment_per_claim": kpis["payment_per_claim"].get(year),
            "claims_per_1000_member_years": kpis["claims_per_1000_member_years"].get(year),
            "admissions": kpis["admissions"].get(year, 0),
            "admissions_per_1000_member_years": kpis["admissions_per_1000_member_years"].get(year),
            "payment_per_admission": kpis["payment_per_admission"].get(year),
            "mean_length_of_stay_days": kpis["mean_length_of_stay_days"].get(year),
            "ed_proxy_visits": kpis["ed_proxy_visits"].get(year, 0),
            "ed_proxy_per_1000_member_years": kpis["ed_proxy_per_1000_member_years"].get(year),
            "outpatient_visits_per_1000_member_years": kpis["outpatient_visits_per_1000_member_years"].get(year),
            "readmission_eligible_index": rd.get("eligible_index"),
            "readmission_events": rd.get("readmissions"),
            "readmission_rate": rd.get("rate"),
            "top_5pct_payment_share": kpis["top_payment_share"].get(year),
        })
    return pd.DataFrame(rows)


def datasets(con: duckdb.DuckDBPyConnection, config: Config) -> dict[str, pd.DataFrame]:
    q = lambda sql: con.execute(sql).df()  # noqa: E731
    kpis = compute_kpis(con)
    top_n = int(config.metrics["review"]["top_n"])
    out: dict[str, pd.DataFrame] = {"kpi_annual": kpi_annual(kpis)}
    out["monthly_utilization"] = q(
        "select strftime(month_start, '%Y-%m') as year_month, extract(year from month_start)::integer as year, setting, "
        "members, claims, unique_beneficiaries, admissions, ed_proxy_visits, outpatient_visits, carrier_service_lines, "
        "claims_per_1000_members from mart_utilization_monthly order by month_start, setting")
    out["monthly_payments"] = q(
        "select strftime(month_start, '%Y-%m') as year_month, extract(year from month_start)::integer as year, setting, "
        "payment_source_field, claims, payment_amount::double as payment_amount, negative_payment_claims, zero_payment_claims, "
        "payment_amount::double / nullif(claims, 0) as payment_per_claim from mart_payment_monthly order by month_start, setting")
    out["annual_by_setting"] = q(
        "select u.year, u.setting, u.beneficiaries, u.member_years, u.claims, u.unique_beneficiaries, u.admissions, "
        "u.ed_proxy_visits, u.outpatient_visits, u.carrier_service_lines, p.payment_source_field, "
        "p.payment_amount::double as payment_amount, p.payment_amount::double / nullif(u.claims, 0) as payment_per_claim "
        "from mart_utilization_annual u left join mart_payment_annual p on p.year = u.year and p.setting = u.setting "
        "order by u.year, u.setting")
    out["condition_summary"] = q(
        "select condition_type, year, setting, condition_id, condition_name, claims, beneficiaries, "
        "payment_amount::double as payment_amount, denominator_beneficiaries, "
        "case when denominator_beneficiaries > 0 then beneficiaries::double / denominator_beneficiaries end as prevalence "
        "from mart_condition_summary order by year, condition_type, setting, payment_amount desc nulls last")
    out["provider_review_facility"] = q(
        "select year, provider_type, provider_id, claims, beneficiaries, payment_amount::double as payment_amount, payment_per_claim::double as payment_per_claim, "
        "peer_count, payment_per_claim_q1::double as payment_per_claim_q1, payment_per_claim_q3::double as payment_per_claim_q3, "
        "claims_q1::double as claims_q1, claims_q3::double as claims_q3, review_flag, array_to_string(reason_codes, ';') as reason_codes "
        "from mart_provider_performance where provider_type like 'facility%' order by year, provider_type, payment_amount desc")
    out["provider_review_professional_top"] = q(
        f"select year, provider_id, claims, beneficiaries, payment_amount::double as payment_amount, payment_per_claim::double as payment_per_claim, "
        f"peer_count, review_flag, array_to_string(reason_codes, ';') as reason_codes from ("
        f"select *, row_number() over (partition by year order by payment_amount desc) as rnk from mart_provider_performance "
        f"where provider_type = 'npi') where rnk <= {top_n * 20} or review_flag order by year, payment_amount desc")
    out["readmission_review"] = q(
        "select year, utilization_risk_tier, eligible_index_stays, readmitted_stays, readmission_rate, excluded_died_in_stay, "
        "excluded_insufficient_followup, stays_considered from mart_quality_monitoring order by year, utilization_risk_tier")
    out["risk_tier_summary"] = q(
        "select r.year, r.utilization_risk_tier, count(*) as beneficiaries, sum(s.member_months) / 12.0 as member_years, "
        "sum(s.payment_amount)::double as payment_amount, sum(s.payment_amount)::double / count(*) as payment_per_beneficiary, "
        "sum(s.admissions) as admissions, sum(s.admissions) * 1000.0 / nullif(sum(s.member_months) / 12.0, 0) as admissions_per_1000_member_years "
        "from mart_member_risk r join mart_beneficiary_year_summary s using (beneficiary_id, year) "
        "group by 1, 2 order by 1, 2")
    out["payment_concentration"] = q(
        "select year, beneficiaries, top_count, top_payment::double as top_payment, total_payment::double as total_payment, top_share "
        "from mart_payment_concentration order by year")
    out["reconciliation_results"] = q(
        "select check_name, category, expected, actual, difference, tolerance, blocking, passed, detail "
        "from reconciliation_results order by category, check_name")
    out["demographic_summary"] = q(
        "select year, sex, race, age_band, beneficiaries, member_months, claims, payment_amount::double as payment_amount, "
        "admissions from mart_demographic_summary order by year, sex, race, age_band")
    out["metric_dictionary"] = metric_dictionary(config)
    return out


def provider_action_list(con: duckdb.DuckDBPyConnection, config: Config) -> pd.DataFrame:
    """Review-flagged providers with reason codes. Every row is a synthetic review flag."""
    top_n = int(config.metrics["review"]["top_n"])
    frame = con.execute(
        "select * from (select provider_type, provider_id, year, claims, beneficiaries, payment_amount::double as payment_amount, "
        "payment_per_claim::double as payment_per_claim, peer_count, array_to_string(reason_codes, ';') as reason_codes, "
        "row_number() over (partition by provider_type, year order by payment_amount desc) as rank_in_group "
        "from mart_provider_performance where review_flag) where rank_in_group <= ? order by year, provider_type, rank_in_group",
        [top_n]).df()
    frame["note"] = "SYNTHETIC review flag only; not fraud, quality or performance evidence"
    return frame


def write_exports(con: duckdb.DuckDBPyConnection, config: Config, directory: Path | None = None) -> dict[str, Path]:
    target = directory or config.exports_dir
    target.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, frame in datasets(con, config).items():
        path = target / f"{name}.csv"
        frame.to_csv(path, index=False)
        written[name] = path
    return written


def kpi_json(con: duckdb.DuckDBPyConnection) -> str:
    return json.dumps(compute_kpis(con), indent=2, sort_keys=True, default=float)
