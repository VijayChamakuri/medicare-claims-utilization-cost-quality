"""Tableau package: governed extracts, the packaged workbook, expected KPIs and a Hyper tie-out.

Everything here is generated from the DuckDB marts. The workbook (``tableau/workbook/medicare_claims_bi.twbx``)
is written by code from the specification in ``build_workbook`` and carries one Tableau Hyper extract per
data source, built from the CSVs in ``tableau/data``. Publishing to Tableau Public is a manual step; see
tableau/README.md. Only aggregated rows and synthetic provider IDs are published: no beneficiary-level field.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import yaml

from medicare_claims.config import Config
from medicare_claims.export import BANNER, datasets, metric_dictionary
from medicare_claims.metrics import compute_data_quality
from medicare_claims.twb import (
    Box,
    Column,
    Dashboard,
    Datasource,
    Filter,
    FilterAction,
    Legend,
    ParamControl,
    Parameter,
    Pill,
    QuickFilter,
    Sheet,
    Text,
    View,
    Workbook,
)

WORKBOOK_TITLE = "Medicare Claims Utilization, Payment & Quality Analytics | CMS DE-SynPUF"
WORKBOOK_FILE = "medicare_claims_bi.twbx"
YEARS = ["2008", "2009", "2010"]
DEFAULT_YEAR = "2009"
# Columns that would identify a beneficiary or a claim. None may appear in a published extract.
DISALLOWED = {"beneficiary_id", "desynpuf_id", "top_beneficiary_id", "claim_id", "claim_key", "stay_key", "bene_birth_dt"}
MONEY = 'c"$"#,##0'
NUM = "n#,##0"
RATE = "n#,##0.0"
PCT = "p0.0%"

CAPTIONS: dict[str, tuple[str, str | None]] = {
    "year": ("Year", None), "setting": ("Care setting", None), "month_start": ("Service date", None),
    "beneficiaries": ("Beneficiaries", NUM), "claims": ("Claims", NUM), "payment_total": ("Paid amount", MONEY),
    "payment_amount": ("Paid amount", MONEY), "payment_per_beneficiary": ("Paid per beneficiary", MONEY),
    "payment_per_claim": ("Paid per claim", MONEY), "payment_per_admission": ("Paid per admission", MONEY),
    "admissions_per_1000_member_years": ("Admissions per 1,000 member-years", RATE),
    "ed_proxy_per_1000_member_years": ("ED proxy per 1,000 member-years", RATE),
    "claims_per_1000_member_years": ("Claims per 1,000 member-years", RATE),
    "claims_per_1000_members": ("Claims per 1,000 members", RATE),
    "readmission_rate": ("Readmission proxy rate", PCT), "top_5pct_payment_share": ("Top 5% payment share", PCT),
    "top_share": ("Top 5% payment share", PCT), "admissions": ("Admissions", NUM), "members": ("Members", NUM),
    "member_years": ("Member-years", RATE), "member_months": ("Member months", NUM),
    "utilization_risk_tier": ("Utilization risk tier", None), "provider_type": ("Peer group", None),
    "provider_id": ("Provider ID (synthetic)", None), "review_flag": ("Review flag", None),
    "reason_codes": ("Reason codes", None), "peer_count": ("Peers", NUM),
    "eligible_index_stays": ("Eligible index stays (denominator)", NUM),
    "readmitted_stays": ("Readmitted within 30 days (numerator)", NUM),
    "excluded_died_in_stay": ("Excluded: died in stay", NUM),
    "excluded_insufficient_followup": ("Excluded: follow-up under 30 days", NUM),
    "condition_name": ("Condition", None), "prevalence": ("Share of beneficiaries", PCT),
    "beneficiary_percentile": ("Top percent of beneficiaries", NUM),
    "cumulative_payment_share": ("Cumulative share of paid amount", PCT),
    "check_name": ("Check", None), "category": ("Category", None), "passed": ("Passed", None),
    "blocking": ("Blocking", None), "difference": ("Difference", "n#,##0.00"),
    "value": ("Value", "n#,##0.00"), "measure": ("Data-quality measure", None),
    "file": ("Source file", None), "retrieved_at": ("Retrieved", None), "bytes": ("Bytes", NUM),
    "name": ("Metric", None), "description": ("Definition", None), "owner_role": ("Owner", None),
    "numerator": ("Numerator", None), "denominator": ("Denominator", None), "known_limits": ("Known limits", None),
    "ed_proxy_visits": ("ED proxy visits", NUM),
}


# ---- extracts ------------------------------------------------------------------------------------------

def _with_month(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "month_start", pd.to_datetime(out["year_month"] + "-01").dt.date.astype(str))
    return out.drop(columns=["year_month"])


def extracts(con: duckdb.DuckDBPyConnection, config: Config) -> dict[str, pd.DataFrame]:
    """Aggregated, governed extracts for Tableau. Every frame is checked for beneficiary-level fields."""
    ds = datasets(con, config)
    q = lambda sql: con.execute(sql).df()  # noqa: E731
    out: dict[str, pd.DataFrame] = {
        "kpi_annual": ds["kpi_annual"],
        "monthly_payments": _with_month(ds["monthly_payments"]),
        "monthly_utilization": _with_month(ds["monthly_utilization"]),
        "annual_by_setting": ds["annual_by_setting"],
        "demographic_summary": ds["demographic_summary"],
        "risk_tier_summary": ds["risk_tier_summary"],
        "payment_concentration": ds["payment_concentration"],
        "readmission_review": ds["readmission_review"],
        "provider_review_facility": ds["provider_review_facility"].assign(
            review_flag=lambda f: f["review_flag"].astype(bool), reason_codes=lambda f: f["reason_codes"].fillna("")),
        "reconciliation_results": ds["reconciliation_results"],
    }
    out["payment_concentration_curve"] = q("""
        with r as (
            select year, payment_amount,
                   row_number() over (partition by year order by payment_amount desc, beneficiary_id) as rnk,
                   count(*) over (partition by year) as n
            from mart_beneficiary_year_summary
        ), b as (
            select year, ceil(rnk * 100.0 / n)::integer as beneficiary_percentile, sum(payment_amount)::double as paid
            from r group by 1, 2
        )
        select year, beneficiary_percentile,
               sum(paid) over (partition by year order by beneficiary_percentile) / sum(paid) over (partition by year)
                   as cumulative_payment_share
        from b order by year, beneficiary_percentile""")
    out["condition_top"] = q("""
        with c as (
            select year, condition_id, any_value(condition_name) as condition_name, sum(claims) as claims,
                   sum(payment_amount)::double as payment_amount
            from mart_condition_summary
            where condition_type = 'primary_diagnosis_ccs'
              and condition_id not in ('missing', 'invalid_format', 'unmapped_valid')
            group by 1, 2
        )
        select * from (
            select *, row_number() over (partition by year order by payment_amount desc, condition_id) as paid_rank from c
        ) where paid_rank <= 15 order by year, paid_rank""")
    out["chronic_prevalence"] = q("""
        select year, condition_name, beneficiaries, denominator_beneficiaries,
               beneficiaries::double / nullif(denominator_beneficiaries, 0) as prevalence
        from mart_condition_summary where condition_type = 'chronic_condition_flag' order by year, prevalence desc""")
    rows = []
    for measure, value in compute_data_quality(con).items():
        if isinstance(value, dict):
            rows += [{"measure": measure.replace("_", " "), "setting": k, "value": float(v)} for k, v in value.items()]
        else:
            rows.append({"measure": measure.replace("_", " "), "setting": "all", "value": float(value)})
    out["data_quality_summary"] = pd.DataFrame(rows)
    out["source_manifest"] = source_manifest(config)
    defs = metric_dictionary(config)
    out["metric_definitions"] = defs[["id", "version", "name", "owner_role", "description", "numerator", "denominator",
                                      "exclusions", "source_model", "known_limits"]]
    for name, frame in out.items():
        bad = DISALLOWED & {c.lower() for c in frame.columns}
        if bad:
            raise ValueError(f"extract {name} contains beneficiary- or claim-level fields: {sorted(bad)}")
    return out


def source_manifest(config: Config) -> pd.DataFrame:
    path = config.manifest_path
    if path is None or not path.exists():
        files = sorted(config.raw_dir.glob("*.csv"))
        return pd.DataFrame([{"file": p.name, "kind": "fixture", "bytes": p.stat().st_size, "retrieved_at": "fixture",
                              "sha256": ""} for p in files])
    data = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame([{"file": name, "kind": str(info.get("kind", "")), "bytes": int(info.get("bytes", 0)),
                          "retrieved_at": str(info.get("retrieved_at", ""))[:10], "sha256": str(info.get("sha256", ""))[:12]}
                         for name, info in sorted(data["files"].items())])


KPI_FIELDS = {"beneficiaries": "beneficiaries", "claims": "claims", "payment_total": "paid_amount",
              "payment_per_beneficiary": "paid_per_beneficiary", "payment_per_claim": "paid_per_claim",
              "payment_per_admission": "paid_per_admission", "admissions_per_1000_member_years": "admissions_per_1000",
              "ed_proxy_per_1000_member_years": "ed_proxy_per_1000", "readmission_rate": "readmission_proxy",
              "top_5pct_payment_share": "top5_payment_share"}
KPI_SHEETS = {"beneficiaries": "KPI Beneficiaries", "claims": "KPI Claims", "payment_total": "KPI Paid amount",
              "payment_per_beneficiary": "KPI Paid per beneficiary", "payment_per_claim": "KPI Paid per claim",
              "payment_per_admission": "KPI Paid per admission",
              "admissions_per_1000_member_years": "KPI Admissions per 1,000 member-years",
              "ed_proxy_per_1000_member_years": "KPI ED proxy per 1,000 member-years",
              "readmission_rate": "KPI Readmission proxy rate", "top_5pct_payment_share": "KPI Top 5% payment share"}


def expected_kpis(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Values each Tableau KPI tile must show, one row per year and tile, with the metric contract ID."""
    ann = frames["kpi_annual"]
    long = ann.melt(id_vars="year", value_vars=list(KPI_FIELDS), var_name="field", value_name="expected_value")
    long["metric_id"] = long["field"].map(KPI_FIELDS)
    long["tableau_sheet"] = long["field"].map(KPI_SHEETS)
    return long[["year", "metric_id", "field", "tableau_sheet", "expected_value"]].sort_values(["year", "tableau_sheet"])


# ---- workbook specification ----------------------------------------------------------------------------

def _datasource(key: str, caption: str, frame: pd.DataFrame, calcs: list[Column] | None = None,
                strings: tuple[str, ...] = ("year",), dates: tuple[str, ...] = ()) -> Datasource:
    cols = []
    for name, dtype in frame.dtypes.items():
        n = str(name)
        if n in strings:
            dt = "string"
        elif n in dates:
            dt = "date"
        elif pd.api.types.is_bool_dtype(dtype):
            dt = "boolean"
        elif pd.api.types.is_integer_dtype(dtype):
            dt = "integer"
        elif pd.api.types.is_float_dtype(dtype):
            dt = "real"
        else:
            dt = "string"
        caption_fmt = CAPTIONS.get(n)
        role = "dimension" if dt in ("string", "date", "boolean") or n in ("beneficiary_percentile", "paid_rank") else "measure"
        cols.append(Column(n, dt, role=role, caption=caption_fmt[0] if caption_fmt else None,
                           fmt=caption_fmt[1] if caption_fmt and dt in ("integer", "real") else None,
                           type="quantitative" if n == "beneficiary_percentile" else ""))
    year_calc = [Column("in_selected_year", "boolean", role="dimension", caption="In selected year",
                        formula="[year] = [Parameters].[year_param]")] if "year" in frame.columns else []
    return Datasource(key, caption, "Data/Extracts", f"{key}.hyper", cols, year_calc + (calcs or []))


def build_workbook(frames: dict[str, pd.DataFrame], refresh: str) -> Workbook:
    year = Parameter("year_param", "Year", "string", DEFAULT_YEAR, members=list(YEARS))
    wb = Workbook(WORKBOOK_TITLE, params=[year])
    sel = Filter("in_selected_year", ["true"])

    kpi = _datasource("kpi_annual", "KPIs by year", frames["kpi_annual"])
    mpay = _datasource("monthly_payments", "Monthly payments", frames["monthly_payments"], dates=("month_start",))
    mutil = _datasource("monthly_utilization", "Monthly utilization", frames["monthly_utilization"], dates=("month_start",))
    setting = _datasource("annual_by_setting", "Annual by setting", frames["annual_by_setting"])
    demo = _datasource("demographic_summary", "Demographic summary", frames["demographic_summary"], calcs=[
        Column("paid_per_beneficiary", "real", caption="Paid per beneficiary", fmt=MONEY,
               formula="SUM([payment_amount]) / SUM([beneficiaries])")])
    tier = _datasource("risk_tier_summary", "Risk tiers", frames["risk_tier_summary"])
    curve = _datasource("payment_concentration_curve", "Payment concentration curve", frames["payment_concentration_curve"])
    prov = _datasource("provider_review_facility", "Provider review (facilities)", frames["provider_review_facility"],
                       strings=("year", "provider_id"))
    readm = _datasource("readmission_review", "Readmission proxy", frames["readmission_review"], calcs=[
        Column("readmission_proxy", "real", caption="Readmission proxy rate", fmt=PCT,
               formula="SUM([readmitted_stays]) / SUM([eligible_index_stays])")])
    cond = _datasource("condition_top", "Top conditions", frames["condition_top"])
    chronic = _datasource("chronic_prevalence", "Chronic condition flags", frames["chronic_prevalence"])
    recon = _datasource("reconciliation_results", "Reconciliation checks", frames["reconciliation_results"])
    dq = _datasource("data_quality_summary", "Data-quality counts", frames["data_quality_summary"])
    src = _datasource("source_manifest", "Source manifest", frames["source_manifest"])
    defs = _datasource("metric_definitions", "Metric definitions", frames["metric_definitions"],
                       strings=("id", "name", "owner_role", "description", "numerator", "denominator", "exclusions",
                                "source_model", "known_limits"))
    wb.datasources = [kpi, mpay, mutil, setting, demo, tier, curve, prov, readm, cond, chronic, recon, dq, src, defs]

    def tile(field: str, title: str) -> Sheet:
        return Sheet(KPI_SHEETS[field], kpi, "Text", text=[Pill(field, "Sum")], filters=[sel], title=title,
                     label_text="{v}", font_size=20)

    overview_tiles = [("beneficiaries", "Beneficiaries"), ("claims", "Claims"), ("payment_total", "Paid amount"),
                      ("admissions_per_1000_member_years", "Admissions per 1,000"),
                      ("ed_proxy_per_1000_member_years", "ED proxy per 1,000"),
                      ("readmission_rate", "Readmission proxy"), ("top_5pct_payment_share", "Top 5% payment share")]
    s: list[Sheet] = [tile(f, t) for f, t in overview_tiles]
    s += [tile("payment_per_beneficiary", "Paid per beneficiary"), tile("payment_per_claim", "Paid per claim"),
          tile("payment_per_admission", "Paid per admission")]
    s.append(Sheet("Monthly paid by setting", mpay, "Bar", cols=[Pill("month_start", "Month-Trunc")],
                   rows=[Pill("payment_amount", "Sum")], color=Pill("setting"),
                   title="Monthly paid amount by care setting, 2008-2010"))
    s.append(Sheet("Monthly claims per 1,000 members", mutil, "Line", cols=[Pill("month_start", "Month-Trunc")],
                   rows=[Pill("claims_per_1000_members", "Sum")], color=Pill("setting"),
                   title="Claims per 1,000 members by month and setting"))
    s.append(Sheet("Paid by setting", setting, "Bar", rows=[Pill("setting")], cols=[Pill("payment_amount", "Sum")],
                   color=Pill("setting"), label=[Pill("payment_amount", "Sum")], filters=[sel],
                   sort=(Pill("setting"), Pill("payment_amount", "Sum"), "DESC"), title="Paid amount by setting"))
    s.append(Sheet("Paid per claim by setting", setting, "Bar", rows=[Pill("setting")], cols=[Pill("payment_per_claim", "Sum")],
                   color=Pill("setting"), label=[Pill("payment_per_claim", "Sum")], filters=[sel],
                   title="Paid per claim by setting"))
    s.append(Sheet("Paid per beneficiary by age band", demo, "Bar", rows=[Pill("age_band")], cols=[Pill("paid_per_beneficiary")],
                   color=Pill("sex"), label=[Pill("paid_per_beneficiary")],
                   filters=[sel, Filter("race", group=21), Filter("sex", group=22)],
                   title="Paid per beneficiary by age band and sex"))
    s.append(Sheet("Risk tier paid per beneficiary", tier, "Bar", rows=[Pill("utilization_risk_tier")],
                   cols=[Pill("payment_per_beneficiary", "Sum")], label=[Pill("payment_per_beneficiary", "Sum")], filters=[sel],
                   mark_color="#1f3a5f", title="Paid per beneficiary by utilization risk tier (descriptive, not CMS-HCC)"))
    s.append(Sheet("Payment concentration curve", curve, "Line", cols=[Pill("beneficiary_percentile")],
                   rows=[Pill("cumulative_payment_share", "Sum")], filters=[sel], mark_color="#1f3a5f",
                   title="Cumulative share of paid amount by top percent of beneficiaries"))
    prov_filters = [sel, Filter("provider_type", ["facility_inpatient"], group=31)]
    s.append(Sheet("Provider volume vs paid per claim", prov, "Circle", cols=[Pill("claims", "Sum")],
                   rows=[Pill("payment_per_claim", "Sum")], color=Pill("review_flag"),
                   detail=[Pill("provider_id")], tooltip=[Pill("reason_codes"), Pill("peer_count", "Sum")],
                   filters=prov_filters, title="Facility volume vs paid per claim (select points to filter the queue)"))
    s.append(Sheet("Review flags by reason", prov, "Bar", rows=[Pill("reason_codes")], cols=[Pill("provider_id", "CountD")],
                   label=[Pill("provider_id", "CountD")], mark_color="#c0392b",
                   filters=prov_filters + [Filter("review_flag", ["true"])], title="Flagged facilities by reason code"))
    s.append(Sheet("Provider action queue", prov, "Text", rows=[Pill("provider_id"), Pill("reason_codes")],
                   text=[Pill("claims", "Sum")], tooltip=[Pill("payment_amount", "Sum")],
                   filters=prov_filters + [Filter("review_flag", ["true"])],
                   sort=(Pill("provider_id"), Pill("claims", "Sum"), "DESC"),
                   title="Review queue: flagged facilities by claims (synthetic IDs, review prompts only)"))
    s.append(Sheet("Readmission proxy by tier", readm, "Bar", rows=[Pill("utilization_risk_tier")], cols=[Pill("readmission_proxy")],
                   label=[Pill("readmission_proxy")], filters=[sel], mark_color="#1f3a5f",
                   title="30-day readmission proxy by risk tier"))
    s.append(Sheet("Readmission numerator and denominator", readm, "Text", rows=[Pill("utilization_risk_tier")],
                   text=[Pill("readmitted_stays", "Sum"), Pill("eligible_index_stays", "Sum"),
                         Pill("excluded_died_in_stay", "Sum"), Pill("excluded_insufficient_followup", "Sum")],
                   filters=[sel], title="Numerator, denominator and exclusions by risk tier"))
    s.append(Sheet("Risk tier admissions per 1,000", tier, "Bar", rows=[Pill("utilization_risk_tier")],
                   cols=[Pill("admissions_per_1000_member_years", "Sum")], label=[Pill("admissions_per_1000_member_years", "Sum")],
                   filters=[sel], mark_color="#2a9d8f", title="Admissions per 1,000 member-years by risk tier"))
    s.append(Sheet("Top conditions by paid amount", cond, "Bar", rows=[Pill("condition_name")], cols=[Pill("payment_amount", "Sum")],
                   label=[Pill("payment_amount", "Sum")], filters=[sel], mark_color="#1f3a5f",
                   sort=(Pill("condition_name"), Pill("payment_amount", "Sum"), "DESC"),
                   title="Top 15 primary-diagnosis groups by paid amount (AHRQ CCS 2015)"))
    s.append(Sheet("Chronic condition prevalence", chronic, "Bar", rows=[Pill("condition_name")], cols=[Pill("prevalence", "Sum")],
                   label=[Pill("prevalence", "Sum")], filters=[sel], mark_color="#2a9d8f",
                   sort=(Pill("condition_name"), Pill("prevalence", "Sum"), "DESC"),
                   title="Chronic condition flags, share of beneficiaries"))
    s.append(Sheet("Reconciliation status", recon, "Bar", rows=[Pill("category")], cols=[Pill("check_name", "CountD")],
                   color=Pill("passed"), label=[Pill("check_name", "CountD")],
                   title="Reconciliation checks by category (red = not passed; informational checks do not block)"))
    s.append(Sheet("Reconciliation detail", recon, "Text", rows=[Pill("category"), Pill("check_name"), Pill("blocking"), Pill("passed")],
                   text=[Pill("difference", "Sum")], title="Every reconciliation check and its difference"))
    s.append(Sheet("Data-quality counts", dq, "Text", rows=[Pill("measure"), Pill("setting")], text=[Pill("value", "Sum")],
                   title="Invalid, duplicate, out-of-window and negative-payment counts"))
    s.append(Sheet("Source manifest", src, "Text", rows=[Pill("file"), Pill("retrieved_at")], text=[Pill("bytes", "Sum")],
                   title="Source files (hash-verified on download)"))
    s.append(Sheet("Metric definitions", defs, "Text", rows=[Pill("name"), Pill("description")], text=[Pill("version", "Sum")],
                   title="Metric definitions and contract version (config/metric_dictionary.yml)"))
    wb.sheets = s

    notice = f"{BANNER} DE-SynPUF volume tapers from mid-2009, so trends are not interpretable."
    footer = f"Source: CMS 2008-2010 DE-SynPUF sample 1. {refresh}. Definitions: Data Quality & Definitions page."

    def header(title: str, subtitle: str) -> Box:
        return Box("vert", [Text(title, 16, True, "#1f3a5f"), Text(notice, 10, True, "#9c0006"),
                            Text(subtitle, 9, False, "#555555")], [4, 2, 2])

    def foot(extra: str = "") -> Text:
        return Text(footer + (" " + extra if extra else ""), 8, False, "#555555")

    def year_ctrl() -> ParamControl:
        return ParamControl("year_param", "compact", "Year")

    def reset() -> Text:
        return Text("Reset: set Year to 2009 and use Revert on the toolbar to clear selections.", 8, False, "#555555")

    wb.dashboards = [
        Dashboard("Executive Overview", 1366, 768, Box("vert", [
            header("Executive overview", "Paid amount is the CMS payment field (CLM_PMT_AMT, LINE_NCH_PMT_AMT), not cost."),
            Box("horz", [year_ctrl(), Legend("Monthly paid by setting", "setting"), reset()], [2, 3, 5]),
            Box("horz", [View(KPI_SHEETS[f]) for f, _ in overview_tiles]),
            Box("horz", [View("Monthly paid by setting"), View("Monthly claims per 1,000 members")], [3, 2]),
            foot()], [9, 3, 7, 26, 2])),
        Dashboard("Utilization & Payment", 1366, 768, Box("vert", [
            header("Utilization and payment", "Paid per beneficiary includes beneficiaries with no claims."),
            Box("horz", [year_ctrl(), QuickFilter("Paid per beneficiary by age band", "race"),
                         QuickFilter("Paid per beneficiary by age band", "sex"), reset()], [1, 1, 1, 3]),
            Box("horz", [View(KPI_SHEETS["payment_per_beneficiary"]), View(KPI_SHEETS["payment_per_claim"]),
                         View(KPI_SHEETS["payment_per_admission"])]),
            Box("horz", [View("Paid by setting"), View("Paid per claim by setting"), View("Payment concentration curve")]),
            Box("horz", [View("Paid per beneficiary by age band"), View("Risk tier paid per beneficiary")]),
            foot()], [9, 3, 6, 13, 13, 2])),
        Dashboard("Provider Operations", 1366, 768, Box("vert", [
            header("Provider operations", "Review flags: above Q3 + 3.0 x IQR of same-type peers (min 20 peers, 30 claims). "
                   "A flag is a prompt to review, not a finding about fraud or quality. Provider IDs are synthetic."),
            Box("horz", [year_ctrl(), QuickFilter("Provider volume vs paid per claim", "provider_type", mode="radiolist"),
                         Legend("Provider volume vs paid per claim", "review_flag"), reset()], [2, 3, 2, 3]),
            Box("horz", [View("Provider volume vs paid per claim"),
                         Box("vert", [View("Review flags by reason"), View("Provider action queue")], [1, 2])], [3, 2]),
            foot("Volume flags mostly track facility size on this synthetic data.")], [9, 3, 34, 2])),
        Dashboard("Quality & Cohorts", 1366, 768, Box("vert", [
            header("Quality and cohorts", "Measure-inspired proxies. Not HEDIS, not CMS-HCC, not a clinical outcome measure. "
                   "Index stay: valid dates, alive at discharge, full 30-day follow-up."),
            Box("horz", [year_ctrl(), reset()], [2, 8]),
            Box("horz", [View(KPI_SHEETS["readmission_rate"]), View("Readmission numerator and denominator")], [1, 3]),
            Box("horz", [View("Readmission proxy by tier"), View("Risk tier admissions per 1,000")]),
            Box("horz", [View("Top conditions by paid amount"), View("Chronic condition prevalence")], [3, 2]),
            foot()], [9, 3, 7, 11, 18, 2])),
        Dashboard("Data Quality & Definitions", 1366, 768, Box("vert", [
            header("Data quality and definitions", "Blocking reconciliation failures stop the pipeline. "
                   "Informational MEDREIMB tie-outs differ by design and are not used in any metric."),
            Box("horz", [Box("vert", [View("Reconciliation status"), Legend("Reconciliation status", "passed")], [5, 1]),
                         View("Data-quality counts")], [1, 1]),
            Box("horz", [View("Reconciliation detail"), Box("vert", [View("Source manifest"), View("Metric definitions")], [1, 2])],
                [1, 1]),
            foot()], [9, 10, 26, 2])),
    ]
    wb.actions = [FilterAction("Filter queue by selected facilities", "Provider Operations",
                               "Provider volume vs paid per claim", ["Provider action queue"], "provider_id")]
    return wb


def workbook_manifest(wb: Workbook) -> dict[str, Any]:
    return {
        "workbook_title": wb.title,
        "file": f"tableau/workbook/{WORKBOOK_FILE}",
        "tableau_version_tested": "Tableau Public 2026.2.2 (macOS, Apple silicon)",
        "size": {"width": 1366, "height": 768, "mode": "fixed"},
        "parameters": [p.caption for p in wb.params],
        "data_sources": [{"name": d.caption, "extract": d.hyper_path, "csv": f"tableau/data/{d.key}.csv"} for d in wb.datasources],
        "worksheets": [s.name for s in wb.sheets],
        "dashboards": [{"name": d.name, "worksheets": d.sheet_names()} for d in wb.dashboards],
        "actions": [{"name": x.name, "dashboard": x.dashboard, "source": x.source, "targets": x.targets} for x in wb.actions],
    }


def hyper_tieout(twbx: Path, expected: pd.DataFrame) -> pd.DataFrame:
    """Read the packaged kpi_annual Hyper extract and compare every expected KPI with it."""
    import tempfile
    import zipfile

    from tableauhyperapi import Connection, HyperProcess, Telemetry

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(twbx) as z:
            z.extract("Data/Extracts/kpi_annual.hyper", tmp)
        with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hp:
            with Connection(hp.endpoint, str(Path(tmp) / "Data/Extracts/kpi_annual.hyper")) as con:
                rows = []
                for r in expected.itertuples():
                    got = con.execute_scalar_query(
                        f'SELECT SUM("{r.field}") FROM "Extract"."Extract" WHERE "year" = \'{r.year}\'')
                    value = float(got) if got is not None else float("nan")
                    exp = float(r.expected_value)
                    both_empty = pd.isna(value) and pd.isna(exp)  # e.g. no eligible index stays in a year
                    ok = both_empty or abs(value - exp) <= max(0.005, abs(exp) * 1e-12)
                    rows.append({"year": r.year, "metric_id": r.metric_id, "tableau_sheet": r.tableau_sheet,
                                 "expected_value": exp, "extract_value": value, "passed": ok})
    return pd.DataFrame(rows)


def build_package(con: duckdb.DuckDBPyConnection, config: Config, directory: Path | None = None) -> Path:
    target = directory or config.artifacts_root / "tableau"
    data = target / "data"
    if data.exists():
        shutil.rmtree(data)
    data.mkdir(parents=True, exist_ok=True)
    frames = extracts(con, config)
    for name, frame in frames.items():
        frame.to_csv(data / f"{name}.csv", index=False)
    expected = expected_kpis(frames)
    expected.to_csv(target / "expected_kpis.csv", index=False)
    (target / "field_dictionary.md").write_text(field_dictionary(frames, config), encoding="utf-8")
    refresh = "Fixture data" if config.is_fixture else f"Data retrieved {frames['source_manifest']['retrieved_at'].max()}"
    wb = build_workbook(frames, refresh)
    workbook_dir = target / "workbook"
    workbook_dir.mkdir(parents=True, exist_ok=True)
    twbx = workbook_dir / WORKBOOK_FILE
    wb.package(twbx, {d.key: data / f"{d.key}.csv" for d in wb.datasources}, config.root / "build" / "hyper")
    (target / "workbook_manifest.yml").write_text(
        "# Generated by `medicare-claims tableau`. Lists what the packaged workbook contains.\n"
        + yaml.safe_dump(workbook_manifest(wb), sort_keys=False), encoding="utf-8")
    hyper_tieout(twbx, expected).to_csv(target / "validation_evidence.csv", index=False)
    return target


def field_dictionary(frames: dict[str, pd.DataFrame], config: Config) -> str:
    defs = metric_dictionary(config).drop_duplicates("tableau_field").set_index("tableau_field")
    lines = ["# Field dictionary", "", f"> {BANNER}", "",
             "Generated by `medicare-claims tableau` from the extracts in `tableau/data/` and the metric contract "
             "`config/metric_dictionary.yml`. Each extract is packaged as a Hyper extract in the workbook. Aggregates "
             "and synthetic provider IDs only: no beneficiary- or claim-level field.", ""]
    for name, frame in frames.items():
        lines += [f"## {name}", "", f"{len(frame):,} rows.", "", "| Field | Caption | Type | Definition |", "|---|---|---|---|"]
        for column, dtype in frame.dtypes.items():
            c = str(column)
            kind = "boolean" if pd.api.types.is_bool_dtype(dtype) else "number" if pd.api.types.is_numeric_dtype(dtype) else "text"
            caption = CAPTIONS.get(c, (c, None))[0]
            definition = str(defs.loc[c, "description"]) if c in defs.index else ""
            lines.append(f"| `{c}` | {caption} | {kind} | {definition} |")
        lines.append("")
    return "\n".join(lines)
