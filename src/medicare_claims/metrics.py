"""Headline KPIs read from the marts. Definitions live in docs/metric_dictionary.md."""

from __future__ import annotations

from typing import Any

import duckdb

SETTINGS = ("inpatient", "outpatient", "carrier")


def _by_year(con: duckdb.DuckDBPyConnection, sql: str) -> dict[str, Any]:
    return {str(y): v for y, v in con.execute(sql).fetchall()}


def _rate(numerator: float | None, denominator: float | None, scale: float = 1000.0) -> float | None:
    if numerator is None or not denominator:
        return None
    return float(numerator) * scale / float(denominator)


def compute_kpis(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    k: dict[str, Any] = {}
    k["beneficiaries"] = _by_year(con, "select year, max(beneficiaries) from mart_utilization_annual group by 1 order by 1")
    k["member_months"] = _by_year(con, "select year, max(member_months) from mart_utilization_annual group by 1 order by 1")
    my = {y: float(v) / 12.0 for y, v in k["member_months"].items()}
    k["member_years"] = my

    k["claims"] = {s: _by_year(con, f"select year, claims from mart_utilization_annual where setting = '{s}' order by 1")
                   for s in SETTINGS}
    k["claims_total"] = _by_year(con, "select year, sum(claims) from mart_utilization_annual group by 1 order by 1")
    k["payment"] = {s: {str(y): float(v) for y, v in con.execute(
        f"select year, payment_amount from mart_payment_annual where setting = '{s}' order by 1").fetchall()}
        for s in SETTINGS}
    k["payment_total"] = {str(y): float(v) for y, v in con.execute(
        "select year, sum(payment_amount) from mart_payment_annual group by 1 order by 1").fetchall()}
    k["payment_total_all_years"] = float(sum(k["payment_total"].values()))

    k["admissions"] = _by_year(con, "select year, admissions from mart_utilization_annual where setting = 'inpatient' order by 1")
    k["admissions_all_years"] = int(sum(k["admissions"].values()))
    k["admissions_per_1000_member_years"] = {y: _rate(k["admissions"].get(y), my[y]) for y in my}
    k["admissions_per_1000_member_years"]["all"] = _rate(k["admissions_all_years"], sum(my.values()))
    k["claims_per_1000_member_years"] = {y: _rate(k["claims_total"].get(y), my[y]) for y in my}

    ed = _by_year(con, "select year, ed_proxy_visits from mart_utilization_annual where setting = 'outpatient' order by 1")
    k["ed_proxy_visits"] = ed
    k["ed_proxy_per_1000_member_years"] = {y: _rate(ed.get(y), my[y]) for y in my}
    ov = _by_year(con, "select year, outpatient_visits from mart_utilization_annual where setting = 'outpatient' order by 1")
    k["outpatient_visits_per_1000_member_years"] = {y: _rate(ov.get(y), my[y]) for y in my}
    k["carrier_lines"] = _by_year(con, "select year, carrier_service_lines from mart_utilization_annual where setting = 'carrier' order by 1")
    k["unique_beneficiaries"] = {s: _by_year(con, f"select year, unique_beneficiaries from mart_utilization_annual where setting = '{s}' order by 1")
                                 for s in SETTINGS}

    los = {str(y): (float(t), int(n)) for y, t, n in con.execute(
        "select year, total_length_of_stay_days, admissions from mart_utilization_annual where setting = 'inpatient' order by 1").fetchall()}
    k["mean_length_of_stay_days"] = {y: (t / n if n else None) for y, (t, n) in los.items()}
    total_los, total_n = sum(t for t, _ in los.values()), sum(n for _, n in los.values())
    k["mean_length_of_stay_days"]["all"] = total_los / total_n if total_n else None
    k["payment_per_admission"] = {y: (float(k["payment"]["inpatient"].get(y, 0)) / n if n else None)
                                  for y, (_, n) in los.items()}
    k["payment_per_beneficiary"] = {y: k["payment_total"].get(y, 0.0) / b for y, b in k["beneficiaries"].items() if b}
    k["payment_per_claim"] = {y: k["payment_total"].get(y, 0.0) / c for y, c in k["claims_total"].items() if c}

    rd: dict[str, dict[str, int | float | None]] = {}
    for y, e, r, dd, insuf in con.execute(
            "select year, sum(eligible_index_stays), sum(readmitted_stays), sum(excluded_died_in_stay), "
            "sum(excluded_insufficient_followup) from mart_quality_monitoring group by 1 order by 1").fetchall():
        rd[str(y)] = {"eligible_index": int(e), "readmissions": int(r), "excluded_died_in_stay": int(dd),
                      "excluded_insufficient_followup": int(insuf), "rate": (r / e if e else None)}
    all_e = sum(int(v["eligible_index"] or 0) for v in rd.values())
    all_r = sum(int(v["readmissions"] or 0) for v in rd.values())
    rd["all"] = {"eligible_index": all_e, "readmissions": all_r, "rate": (all_r / all_e if all_e else None)}
    k["readmission"] = rd

    k["top_payment_share"] = {str(y): (float(s) if s is not None else None) for y, s in con.execute(
        "select year, top_share from mart_payment_concentration order by 1").fetchall()}
    k["top_payment_beneficiary"] = _by_year(con, "select year, top_beneficiary_id from mart_payment_concentration order by 1")
    tiers: dict[str, dict[str, int]] = {}
    for y, tier, n in con.execute("select year, utilization_risk_tier, count(*) from mart_member_risk group by 1, 2 order by 1, 2").fetchall():
        tiers.setdefault(str(y), {})[str(tier)] = int(n)
    k["risk_tier_counts"] = tiers
    flags: dict[str, dict[str, list[str]]] = {}
    for y, pid, reasons in con.execute(
            "select year, provider_id, reason_codes from mart_provider_performance where review_flag order by 1, 2").fetchall():
        flags.setdefault(str(y), {})[str(pid)] = list(reasons)
    k["review_flags"] = flags
    return k


def compute_data_quality(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Counts behind the data-quality report and the exact data-quality fixture assertions."""
    def by_setting(condition: str) -> dict[str, int]:
        rows = dict(con.execute(f"select setting, count(*) from fact_claim_header where {condition} group by 1").fetchall())
        return {s: int(rows.get(s, 0)) for s in SETTINGS}

    dq: dict[str, Any] = {
        "duplicate_rows_dropped": {
            "inpatient": int(con.execute("select count(*) from stg_ip_all where dup_rank > 1").fetchone()[0]),  # type: ignore[index]
            "outpatient": int(con.execute("select count(*) from stg_op_all where dup_rank > 1").fetchone()[0]),  # type: ignore[index]
            "carrier": int(con.execute("select count(*) from stg_carrier_claim_all where dup_rank > 1").fetchone()[0]),  # type: ignore[index]
        },
        "invalid_date_claims": by_setting("not date_valid"),
        "outside_study_window_claims": by_setting("date_valid and not in_study_window"),
        "negative_payment_claims": by_setting("is_analytic and payment_amount < 0"),
        "multi_segment_claims": by_setting("segment_count > 1 and setting <> 'carrier'"),
    }
    def one(sql: str) -> Any:
        row = con.execute(sql).fetchone()
        return None if row is None else row[0]

    dq["malformed_primary_dx_claims_inpatient"] = int(one(
        "select count(*) from fact_claim_header where setting = 'inpatient' and is_analytic and primary_dx is not null and not primary_dx_valid"))
    dq["unmapped_primary_dx_claims_inpatient"] = int(one(
        "select count(*) from fact_claim_header h left join dim_diagnosis d on d.diagnosis_code = h.primary_dx "
        "where h.setting = 'inpatient' and h.is_analytic and h.primary_dx_valid and d.ccs_category is null"))
    dq["missing_primary_dx_claims_inpatient"] = int(one(
        "select count(*) from fact_claim_header where setting = 'inpatient' and is_analytic and primary_dx is null"))
    dq["excluded_payment_invalid_dates"] = float(one(
        "select coalesce(sum(payment_amount), 0) from fact_claim_header where not date_valid"))
    dq["excluded_payment_outside_window"] = float(one(
        "select coalesce(sum(payment_amount), 0) from fact_claim_header where date_valid and not in_study_window"))
    dq["source_payment_total_deduplicated"] = float(one(
        "select coalesce(sum(payment_amount), 0) from fact_claim_header"))
    dq["source_payment_total_with_duplicates"] = float(one(
        "select (select coalesce(sum(clm_pmt_amt), 0) from stg_ip_all) + (select coalesce(sum(clm_pmt_amt), 0) from stg_op_all) "
        "+ (select coalesce(sum(line_nch_pmt_amt), 0) from stg_carrier_line)"))
    return dq


def condition_rows(con: duckdb.DuckDBPyConnection, year: int, setting: str) -> dict[str, tuple[int, float]]:
    rows = con.execute(
        "select condition_id, claims, payment_amount from mart_condition_summary "
        "where condition_type = 'primary_diagnosis_ccs' and year = ? and setting = ?", [year, setting]).fetchall()
    return {str(c): (int(n), float(p)) for c, n, p in rows}
