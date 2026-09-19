"""Build excel/claims_operations_review.xlsx from the DuckDB marts.

Counts and amounts come from the marts as values; every rate, variance and check is a live Excel
formula. Tables are flat and pivot-ready. No beneficiary-level rows are written.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.pagebreak import Break
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet

from medicare_claims.config import Config
from medicare_claims.export import BANNER, datasets
from medicare_claims.metrics import compute_data_quality, compute_kpis
from medicare_claims.quality import code_quality

SHEETS = ["Executive_Summary", "Monthly_Utilization", "Monthly_Payments", "Provider_Review",
          "Readmission_Review", "Member_Risk_Tiers", "Data_Quality", "Metric_Dictionary", "Reconciliation"]
HEADER_FILL = PatternFill("solid", start_color="1F3A5F")
HEADER_FONT = Font(bold=True, color="FFFFFF")
WARN_FILL = PatternFill("solid", start_color="FFE599")
BAD_FILL = PatternFill("solid", start_color="F4B6B6")
GOOD_FILL = PatternFill("solid", start_color="C6E0B4")
BANNER_FONT = Font(bold=True, color="9C0006")
MONEY = '#,##0.00;[Red]-#,##0.00'
INT = "#,##0"
PCT = "0.0%"
RATE = "#,##0.0"
HEADER_ROW = 4


def _banner(ws: Worksheet, title: str, note: str = "") -> None:
    ws["A1"], ws["A1"].font = BANNER, BANNER_FONT
    ws["A2"], ws["A2"].font = title, Font(bold=True, size=13)
    if note:
        ws["A3"] = note


def _table(ws: Worksheet, frame: pd.DataFrame, name: str, formats: dict[str, str] | None = None,
           formulas: dict[str, str] | None = None) -> tuple[int, int]:
    """Write a header at HEADER_ROW and rows below it as an Excel table. Returns (first_row, last_row).

    ``formulas`` maps a new column name to a template using ``{r}`` for the row number and ``{col:name}``
    for another column's letter.
    """
    formats = formats or {}
    formulas = formulas or {}
    columns = list(frame.columns) + list(formulas)
    letters = {c: get_column_letter(i) for i, c in enumerate(columns, start=1)}
    for i, column in enumerate(columns, start=1):
        cell = ws.cell(HEADER_ROW, i, column)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(34, len(column) + 4))
    first = HEADER_ROW + 1
    for offset, row in enumerate(frame.itertuples(index=False)):
        r = first + offset
        for i, value in enumerate(row, start=1):
            if pd.isna(value):
                continue
            cell = ws.cell(r, i, value.item() if hasattr(value, "item") else value)
            fmt = formats.get(columns[i - 1])
            if fmt:
                cell.number_format = fmt
        for j, (formula_name, template) in enumerate(formulas.items(), start=len(frame.columns) + 1):
            text = template.format(r=r, **{f"c_{c}": letters[c] for c in letters})
            cell = ws.cell(r, j, text)
            fmt = formats.get(formula_name)
            if fmt:
                cell.number_format = fmt
    last = first + max(len(frame), 1) - 1
    table = Table(displayName=name, ref=f"A{HEADER_ROW}:{get_column_letter(len(columns))}{last}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = f"A{first}"
    return first, last


PRINT_TITLE = "Medicare Claims Utilization, Payment && Quality Analytics"  # && is a literal & in header codes


def _print_setup(ws: Worksheet, refresh: str, one_page: bool = False) -> None:
    """Landscape, one page wide, header row repeated, and a header/footer carrying the synthetic notice."""
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_setup.fitToWidth = 2 if one_page else 1
    ws.page_setup.fitToHeight = 1 if one_page else 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.6
    ws.print_options.horizontalCentered = True
    if ws.max_row > HEADER_ROW:
        ws.print_title_rows = f"{HEADER_ROW}:{HEADER_ROW}"
    ws.print_area = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
    header, footer = ws.oddHeader, ws.oddFooter
    assert header is not None and footer is not None
    header.left.text, header.left.size = PRINT_TITLE, 9
    header.right.text, header.right.size = ws.title.replace("_", " "), 9
    footer.left.text, footer.left.size = BANNER, 8
    footer.center.text, footer.center.size = refresh, 8
    footer.right.text, footer.right.size = "Page &P of &N", 8


def _wrap_row(ws: Worksheet, row: int, last_col: int, text: str, height: float, bold: bool = False) -> None:
    ws.cell(row, 1, text)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    ws.cell(row, 1).alignment = Alignment(wrap_text=True, vertical="top")
    if bold:
        ws.cell(row, 1).font = Font(bold=True)
    ws.row_dimensions[row].height = height


def _executive(ws: Worksheet, ds: dict[str, pd.DataFrame], kpis: dict[str, Any], manifest_date: str) -> None:
    _banner(ws, "Executive summary", f"Data: {manifest_date}. Definitions: see Metric_Dictionary. Rates are formulas; the Pipeline columns hold the warehouse values they must equal.")
    ann = ds["kpi_annual"].copy()
    conc = ds["payment_concentration"].set_index("year")
    frame = pd.DataFrame({
        "Year": ann["year"], "Beneficiaries": ann["beneficiaries"], "Member years": ann["member_years"],
        "Claims": ann["claims"], "Paid amount (CLM_PMT_AMT + LINE_NCH_PMT_AMT)": ann["payment_total"],
        "Admissions": ann["admissions"], "ED proxy visits": ann["ed_proxy_visits"],
        "Readmission eligible index stays": ann["readmission_eligible_index"], "Readmission events": ann["readmission_events"],
        "Top 5% paid amount": ann["year"].map(conc["top_payment"]),
        "Year (rates)": ann["year"],
        "Pipeline: admissions per 1,000": ann["admissions_per_1000_member_years"],
        "Pipeline: readmission proxy": ann["readmission_rate"],
        "Pipeline: top 5% share": ann["top_5pct_payment_share"],
    })
    frame.columns = ["Year", "Beneficiaries", "Member_years", "Claims", "Paid_amount", "Admissions", "ED_proxy_visits",
                     "Readmission_eligible", "Readmission_events", "Top5_paid_amount", "Year_(rates)", "Pipeline_admissions_per_1000",
                     "Pipeline_readmission_proxy", "Pipeline_top5_share"]
    formats = {"Member_years": RATE, "Paid_amount": MONEY, "Top5_paid_amount": MONEY, "Beneficiaries": INT, "Claims": INT,
               "Admissions": INT, "ED_proxy_visits": INT, "Readmission_eligible": INT, "Readmission_events": INT,
               "Pipeline_admissions_per_1000": RATE, "Pipeline_readmission_proxy": PCT, "Pipeline_top5_share": PCT,
               "Paid_per_beneficiary": MONEY, "Admissions_per_1000_member_years": RATE, "ED_proxy_per_1000_member_years": RATE,
               "Readmission_proxy": PCT, "Top5_payment_share": PCT}
    formulas = {
        "Paid_per_beneficiary": "=IF({c_Beneficiaries}{r}>0,{c_Paid_amount}{r}/{c_Beneficiaries}{r},\"\")",
        "Admissions_per_1000_member_years": "=IF({c_Member_years}{r}>0,{c_Admissions}{r}/{c_Member_years}{r}*1000,\"\")",
        "ED_proxy_per_1000_member_years": "=IF({c_Member_years}{r}>0,{c_ED_proxy_visits}{r}/{c_Member_years}{r}*1000,\"\")",
        "Readmission_proxy": "=IF({c_Readmission_eligible}{r}>0,{c_Readmission_events}{r}/{c_Readmission_eligible}{r},\"\")",
        "Top5_payment_share": "=IF({c_Paid_amount}{r}<>0,{c_Top5_paid_amount}{r}/{c_Paid_amount}{r},\"\")",
        "Check_vs_pipeline": ("=IF(AND(ABS({c_Admissions_per_1000_member_years}{r}-{c_Pipeline_admissions_per_1000}{r})<0.000001,"
                             "ABS({c_Top5_payment_share}{r}-{c_Pipeline_top5_share}{r})<0.000001),\"OK\",\"CHECK\")"),
    }
    first, last = _table(ws, frame, "ExecutiveKpis", formats, formulas)
    width = len(frame.columns) + len(formulas)
    check_col = get_column_letter(width)
    ws.conditional_formatting.add(f"A{first}:{check_col}{last}",
                                  FormulaRule(formula=[f'${check_col}{first}="CHECK"'], fill=BAD_FILL))
    # Display labels with spaces so headers wrap at word boundaries when printed. Formulas use cell letters.
    for col in range(1, width + 1):
        cell = ws.cell(HEADER_ROW, col)
        cell.value = str(cell.value).replace("Top5", "Top 5%").replace("top5", "top 5%").replace("_", " ")
    n = last + 3
    notes = [
        "What this workbook is: an operations review of CMS DE-SynPUF synthetic Medicare claims. It demonstrates a pipeline; it does not describe real Medicare.",
        "Not included: prescription drug events; any beneficiary-level rows; any claim of savings, fraud, or provider quality.",
        "Utilization risk tier is a transparent descriptive stratification, not CMS-HCC or any official risk adjustment.",
        "The 30-day readmission proxy is measure-inspired, not a certified measure. 2010 volumes are lower in the source, so year-to-year trends are not interpretable.",
    ]
    # Print as two landscape pages: page 1 holds the pipeline counts (A:J), page 2 the rates and checks.
    page_one = list(frame.columns).index("Year_(rates)")
    note = str(ws["A3"].value or "")
    _wrap_row(ws, 3, page_one, note, 30)
    ws.cell(n, 1, "Limitations").font = Font(bold=True)
    for i, text in enumerate(notes, start=1):
        _wrap_row(ws, n + i, page_one, text, 30)
    for col in range(1, width + 1):
        ws.column_dimensions[get_column_letter(col)].width = 9 if col in (1, page_one + 1) else 14
        ws.cell(HEADER_ROW, col).alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ws.row_dimensions[HEADER_ROW].height = 48
    ws.col_breaks.append(Break(id=page_one))


def _monthly_utilization(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> tuple[int, int]:
    _banner(ws, "Monthly utilization by care setting", "Claims per 1,000 members is a formula: claims / members x 1,000.")
    frame = ds["monthly_utilization"].drop(columns=["claims_per_1000_members"])
    frame.columns = ["Year_month", "Year", "Setting", "Members", "Claims", "Unique_beneficiaries", "Admissions",
                     "ED_proxy_visits", "Outpatient_visits", "Carrier_service_lines"]
    return _table(ws, frame, "MonthlyUtilization",
                  {c: INT for c in ("Members", "Claims", "Unique_beneficiaries", "Admissions", "ED_proxy_visits", "Outpatient_visits", "Carrier_service_lines")}
                  | {"Claims_per_1000_members": RATE},
                  {"Claims_per_1000_members": "=IF({c_Members}{r}>0,{c_Claims}{r}/{c_Members}{r}*1000,\"\")"})


def _monthly_payments(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> tuple[int, int]:
    _banner(ws, "Monthly payments by care setting", "Payment fields keep their CMS names; negative amounts are payment adjustments and are included.")
    frame = ds["monthly_payments"].drop(columns=["payment_per_claim"])
    frame.columns = ["Year_month", "Year", "Setting", "Payment_source_field", "Claims", "Payment_amount",
                     "Negative_payment_claims", "Zero_payment_claims"]
    return _table(ws, frame, "MonthlyPayments",
                  {"Payment_amount": MONEY, "Claims": INT, "Negative_payment_claims": INT, "Zero_payment_claims": INT, "Payment_per_claim": MONEY},
                  {"Payment_per_claim": "=IF({c_Claims}{r}>0,{c_Payment_amount}{r}/{c_Claims}{r},\"\")"})


def _provider_review(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> None:
    _banner(ws, "Provider review list (SYNTHETIC flags only)",
            "Review flags are prompts to compare peers. They are not fraud, quality or performance findings. Provider IDs are synthetic.")
    fac = ds["provider_review_facility"].copy()
    npi = ds["provider_review_professional_top"].assign(provider_type="professional_npi")
    fac = pd.concat([g[g["review_flag"] | (g["payment_amount"].rank(ascending=False, method="first") <= 100)] for _, g in fac.groupby(["year", "provider_type"])])
    frame = pd.concat([fac, npi], ignore_index=True)[["year", "provider_type", "provider_id", "claims", "beneficiaries", "payment_amount",
                                                     "peer_count", "review_flag", "reason_codes"]]
    frame["review_flag"] = frame["review_flag"].map({True: "REVIEW", False: ""})
    frame["reason_codes"] = frame["reason_codes"].fillna("")
    frame.columns = ["Year", "Provider_type", "Provider_id", "Claims", "Beneficiaries", "Payment_amount", "Peer_count", "Review_flag", "Reason_codes"]
    first, last = _table(ws, frame, "ProviderReview", {"Payment_amount": MONEY, "Claims": INT, "Beneficiaries": INT, "Payment_per_claim": MONEY},
                         {"Payment_per_claim": "=IF({c_Claims}{r}>0,{c_Payment_amount}{r}/{c_Claims}{r},\"\")"})
    ws.conditional_formatting.add(f"A{first}:J{last}", FormulaRule(formula=[f'$H{first}="REVIEW"'], fill=WARN_FILL))


def _readmission(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> None:
    _banner(ws, "30-day readmission proxy by year and utilization risk tier",
            "Measure-inspired proxy, not a certified measure. Rate is a formula: readmitted / eligible index stays.")
    frame = ds["readmission_review"].drop(columns=["readmission_rate"])
    frame.columns = ["Year", "Utilization_risk_tier", "Eligible_index_stays", "Readmitted_stays", "Excluded_died_in_stay",
                     "Excluded_insufficient_followup", "Stays_considered"]
    first, last = _table(ws, frame, "ReadmissionReview", {c: INT for c in frame.columns if c not in ("Year", "Utilization_risk_tier")} | {"Readmission_rate": PCT},
                         {"Readmission_rate": "=IF({c_Eligible_index_stays}{r}>0,{c_Readmitted_stays}{r}/{c_Eligible_index_stays}{r},\"\")"})


def _risk_tiers(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> None:
    _banner(ws, "Utilization risk tiers (descriptive stratification)",
            "Not CMS-HCC, RAF or official risk adjustment. Tier uses prior-year information only. Aggregates only, no beneficiary rows.")
    frame = ds["risk_tier_summary"][["year", "utilization_risk_tier", "beneficiaries", "member_years", "payment_amount", "admissions"]]
    frame.columns = ["Year", "Utilization_risk_tier", "Beneficiaries", "Member_years", "Payment_amount", "Admissions"]
    _table(ws, frame, "RiskTiers", {"Beneficiaries": INT, "Member_years": RATE, "Payment_amount": MONEY, "Admissions": INT,
                                    "Payment_per_beneficiary": MONEY, "Admissions_per_1000_member_years": RATE},
           {"Payment_per_beneficiary": "=IF({c_Beneficiaries}{r}>0,{c_Payment_amount}{r}/{c_Beneficiaries}{r},\"\")",
            "Admissions_per_1000_member_years": "=IF({c_Member_years}{r}>0,{c_Admissions}{r}/{c_Member_years}{r}*1000,\"\")"})


def _data_quality(ws: Worksheet, con: duckdb.DuckDBPyConnection) -> None:
    _banner(ws, "Data quality", "Counts from the pipeline. Duplicates, impossible dates and out-of-window claims are excluded from metrics and reported here.")
    counts, codes = compute_data_quality(con), code_quality(con)
    rows: list[tuple[str, str, float]] = []
    for label, key in (("Exact duplicate rows dropped", "duplicate_rows_dropped"), ("Impossible or missing dates", "invalid_date_claims"),
                       ("Outside study window", "outside_study_window_claims"), ("Negative payment claims", "negative_payment_claims"),
                       ("Multi-segment claims merged", "multi_segment_claims")):
        for setting, n in counts[key].items():
            rows.append((label, setting, n))
    rows += [("Payment excluded: invalid dates", "all", counts["excluded_payment_invalid_dates"]),
             ("Payment excluded: outside window", "all", counts["excluded_payment_outside_window"]),
             ("Diagnosis rows with invalid format", "all", codes["diagnosis_invalid_format"]),
             ("Diagnosis rows valid but unmapped", "all", codes["diagnosis_unmapped_valid"]),
             ("Claims dated after death", "all", codes["claims_after_death"]),
             ("Orphan claims (beneficiary missing)", "all", codes["orphan_claims"])]
    frame = pd.DataFrame(rows, columns=["Check", "Setting", "Value"])
    _table(ws, frame, "DataQuality", {"Value": "#,##0.00"})


def _dictionary(ws: Worksheet, ds: dict[str, pd.DataFrame]) -> None:
    _banner(ws, "Metric dictionary", "Single source: config/metric_dictionary.yml.")
    cols = ["id", "version", "name", "owner_role", "description", "grain", "source_model", "calculation", "numerator",
            "denominator", "exclusions", "unit", "known_limits"]
    frame = ds["metric_dictionary"][cols]
    frame.columns = ["Metric_ID", "Version", "Metric", "Owner_role", "Description", "Grain", "Source_model", "Calculation",
                     "Numerator", "Denominator", "Exclusions", "Unit", "Known_limits"]
    _table(ws, frame, "MetricDictionary")
    for col, width in zip("ABCDEFGHIJKLM", (22, 9, 30, 22, 60, 18, 26, 44, 40, 30, 40, 24, 60), strict=True):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=HEADER_ROW + 1):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _reconciliation(ws: Worksheet, kpis: dict[str, Any], ranges: dict[str, tuple[str, int, int]]) -> None:
    _banner(ws, "Reconciliation: workbook totals versus DuckDB",
            "Workbook column: a formula over this workbook's own tables. DuckDB column: value read from the marts. Tolerance: half a cent for money, zero for counts.")
    def total(sheet: str, column: str) -> str:
        table, first, last = ranges[sheet]
        return f"=SUM({sheet}!{column}{first}:{column}{last})"

    claims_total = sum(int(v) for v in kpis["claims_total"].values())
    admissions_total = int(kpis["admissions_all_years"])
    member_months = sum(int(v) for v in kpis["member_months"].values())
    rows = [
        ("Monthly claims (all settings)", total("Monthly_Utilization", "E"), claims_total, 0.0),
        ("Monthly admissions", total("Monthly_Utilization", "G"), admissions_total, 0.0),
        ("Monthly ED proxy visits", total("Monthly_Utilization", "H"), sum(int(v) for v in kpis["ed_proxy_visits"].values()), 0.0),
        ("Monthly paid amount", total("Monthly_Payments", "F"), float(kpis["payment_total_all_years"]), 0.005),
        ("Monthly payment claims", total("Monthly_Payments", "E"), claims_total, 0.0),
        ("Executive: claims", f"=SUM(Executive_Summary!D{ranges['Executive_Summary'][1]}:D{ranges['Executive_Summary'][2]})", claims_total, 0.0),
        ("Executive: paid amount", f"=SUM(Executive_Summary!E{ranges['Executive_Summary'][1]}:E{ranges['Executive_Summary'][2]})", float(kpis["payment_total_all_years"]), 0.005),
        ("Executive: admissions", f"=SUM(Executive_Summary!F{ranges['Executive_Summary'][1]}:F{ranges['Executive_Summary'][2]})", admissions_total, 0.0),
        ("Executive: member years x 12", f"=SUM(Executive_Summary!C{ranges['Executive_Summary'][1]}:C{ranges['Executive_Summary'][2]})*12", member_months, 0.000001),
        ("Readmission stays considered", total("Readmission_Review", "G"), sum(int(v.get("eligible_index", 0)) + int(v.get("excluded_died_in_stay", 0)) + int(v.get("excluded_insufficient_followup", 0))
                                                                                for k, v in kpis["readmission"].items() if k != "all"), 0.0),
    ]
    frame = pd.DataFrame([(name, None, dw, tol) for name, _, dw, tol in rows], columns=["Check", "Workbook", "DuckDB", "Tolerance"])
    frame = frame.drop(columns=["Workbook"])
    first, last = _table(ws, frame, "ReconciliationChecks", {"DuckDB": "#,##0.00", "Tolerance": "0.000000", "Workbook_value": "#,##0.00", "Variance": "#,##0.000000"},
                         {"Workbook_value": "=0", "Variance": "=ABS({c_Workbook_value}{r}-{c_DuckDB}{r})",
                          "Status": "=IF({c_Variance}{r}<={c_Tolerance}{r},\"PASS\",\"FAIL\")"})
    for offset, (_, formula, _, _) in enumerate(rows):
        ws.cell(first + offset, 4, formula).number_format = "#,##0.00"  # column D: Workbook_value
    ws.conditional_formatting.add(f"A{first}:F{last}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=BAD_FILL))
    ws.conditional_formatting.add(f"A{first}:F{last}", CellIsRule(operator="equal", formula=['"PASS"'], fill=GOOD_FILL))
    ws.cell(last + 2, 1, "Overall").font = Font(bold=True)
    ws.cell(last + 2, 2, f'=IF(COUNTIF(F{first}:F{last},"FAIL")=0,"ALL CHECKS PASS","REVIEW")').font = Font(bold=True)


def _retrieved_date(config: Config) -> str:
    import json

    manifest = json.loads((config.root / "data" / "data_manifest.json").read_text(encoding="utf-8"))
    dates = sorted({str(f.get("retrieved_at", ""))[:10] for f in manifest.get("files", {}).values() if isinstance(f, dict)})
    return dates[-1] if dates and dates[-1] else "see data/data_manifest.json"


def build_workbook(con: duckdb.DuckDBPyConnection, config: Config, path: Path | None = None) -> Path:
    ds = datasets(con, config)
    kpis = compute_kpis(con)
    manifest_date = "fixture data" if config.is_fixture else "CMS DE-SynPUF sample 1, retrieved per data/data_manifest.json"
    wb = Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    sheets = {name: wb.create_sheet(name) for name in SHEETS}
    _executive(sheets["Executive_Summary"], ds, kpis, manifest_date)
    ranges = {"Executive_Summary": ("ExecutiveKpis", HEADER_ROW + 1, HEADER_ROW + len(ds["kpi_annual"]))}
    for name, fn in (("Monthly_Utilization", _monthly_utilization), ("Monthly_Payments", _monthly_payments)):
        first, last = fn(sheets[name], ds)
        ranges[name] = (name, first, last)
    _provider_review(sheets["Provider_Review"], ds)
    _readmission(sheets["Readmission_Review"], ds)
    ranges["Readmission_Review"] = ("ReadmissionReview", HEADER_ROW + 1, HEADER_ROW + len(ds["readmission_review"]))
    _risk_tiers(sheets["Member_Risk_Tiers"], ds)
    _data_quality(sheets["Data_Quality"], con)
    _dictionary(sheets["Metric_Dictionary"], ds)
    _reconciliation(sheets["Reconciliation"], kpis, ranges)
    refresh = "Fixture data" if config.is_fixture else f"Data retrieved {_retrieved_date(config)}"
    for name, ws in sheets.items():
        _print_setup(ws, refresh, one_page=name == "Executive_Summary")  # two pages wide, one tall
    target = path or config.artifacts_root / "excel" / "claims_operations_review.xlsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target)
    return target
