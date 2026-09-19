"""Independent reconciliation: recompute the headline KPIs in pandas from the raw CSVs and compare them
with the warehouse. No SQL and no staging table is shared with the pipeline, so agreement is evidence
that the SQL logic matches the written definitions.
"""

from __future__ import annotations

import math
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from medicare_claims.config import Config
from medicare_claims.metrics import compute_kpis

MONEY_TOLERANCE = 0.005
RATE_TOLERANCE = 1e-9


def _read(path: Any, columns: list[str]) -> pd.DataFrame:
    """Read only the wanted columns that exist in the file, as text."""
    header = pd.read_csv(path, nrows=0).columns
    use = [c for c in columns if c in header]
    frame = pd.read_csv(path, dtype=str, usecols=use, keep_default_na=False, na_values=[""])
    for missing in set(columns) - set(use):
        frame[missing] = pd.Series([None] * len(frame), dtype="object")
    return frame


def _dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%Y%m%d", errors="coerce")


def _analytic_header(frame: pd.DataFrame, config: Config, inpatient: bool) -> pd.DataFrame:
    frame = frame.drop_duplicates(subset=["DESYNPUF_ID", "CLM_ID", "SEGMENT"] if "SEGMENT" in frame else ["DESYNPUF_ID", "CLM_ID"])
    frame = frame.assign(pay=pd.to_numeric(frame["CLM_PMT_AMT"], errors="coerce"),
                         frm=_dates(frame["CLM_FROM_DT"]), thru=_dates(frame["CLM_THRU_DT"]))
    agg = {"pay": ("pay", "sum"), "frm": ("frm", "min"), "thru": ("thru", "max")}
    if inpatient:
        frame = frame.assign(adm=_dates(frame["CLM_ADMSN_DT"]), dsch=_dates(frame["NCH_BENE_DSCHRG_DT"]))
        agg.update({"adm": ("adm", "min"), "dsch": ("dsch", "max")})
    claims = frame.groupby(["DESYNPUF_ID", "CLM_ID"], as_index=False).agg(**agg)
    valid = claims["frm"].notna() & claims["thru"].notna() & (claims["frm"] <= claims["thru"])
    if inpatient:
        valid &= claims["adm"].notna() & claims["dsch"].notna() & (claims["adm"] <= claims["dsch"])
        claims["service"] = claims["adm"].fillna(claims["frm"])
    else:
        claims["service"] = claims["frm"]
    start, end = pd.Timestamp(config.study_start), pd.Timestamp(config.study_end)
    claims = claims[valid & claims["service"].between(start, end)].copy()
    claims["year"] = claims["service"].dt.year
    return claims


def independent_kpis(config: Config) -> dict[str, Any]:
    cols_common = ["DESYNPUF_ID", "CLM_ID", "SEGMENT", "CLM_FROM_DT", "CLM_THRU_DT", "CLM_PMT_AMT"]
    ip_raw = pd.concat([_read(config.csv_path(f), cols_common + ["CLM_ADMSN_DT", "NCH_BENE_DSCHRG_DT"])
                        for f in config.files("inpatient")], ignore_index=True)
    ip = _analytic_header(ip_raw, config, inpatient=True)

    hcpcs = [f"HCPCS_CD_{i}" for i in range(1, 46)]
    op_frames = [_read(config.csv_path(f), cols_common + hcpcs) for f in config.files("outpatient")]
    op_raw = pd.concat(op_frames, ignore_index=True)
    ed_codes = set(config.metrics["ed_hcpcs_codes"])
    op_raw = op_raw.drop_duplicates(subset=["DESYNPUF_ID", "CLM_ID", "SEGMENT"])
    op_raw["is_ed"] = op_raw[hcpcs].apply(lambda col: col.astype('string').str.strip().str.upper().isin(ed_codes)).any(axis=1)
    op = _analytic_header(op_raw, config, inpatient=False)
    ed_keys = op_raw.loc[op_raw["is_ed"], ["DESYNPUF_ID", "CLM_ID"]].drop_duplicates()
    op = op.merge(ed_keys.assign(is_ed=True), on=["DESYNPUF_ID", "CLM_ID"], how="left")
    op["is_ed"] = op["is_ed"].eq(True)

    pay_cols = [f"LINE_NCH_PMT_AMT_{i}" for i in range(1, 14)]
    code_cols = [f"HCPCS_CD_{i}" for i in range(1, 14)]
    npi_cols = [f"PRF_PHYSN_NPI_{i}" for i in range(1, 14)]
    ca_raw = pd.concat([_read(config.csv_path(f), ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_THRU_DT"] + pay_cols + code_cols + npi_cols)
                        for f in config.files("carrier")], ignore_index=True)
    ca_raw = ca_raw.drop_duplicates(subset=["DESYNPUF_ID", "CLM_ID"])
    amounts = ca_raw[pay_cols].apply(pd.to_numeric, errors="coerce")
    has_code = ca_raw[code_cols].apply(lambda col: col.astype("string").str.strip().replace("", pd.NA).notna()).to_numpy()
    has_npi = ca_raw[npi_cols].apply(lambda col: col.astype("string").str.strip().replace("", pd.NA).notna()).to_numpy()
    # A real line has a code, a non-zero payment or a performing NPI; CMS pads unused slots with 0.00.
    real_line = has_code | has_npi | (amounts.fillna(0).to_numpy() != 0)
    ca = pd.DataFrame({"DESYNPUF_ID": ca_raw["DESYNPUF_ID"], "CLM_ID": ca_raw["CLM_ID"],
                       "pay": amounts.sum(axis=1), "lines": real_line.sum(axis=1),
                       "frm": _dates(ca_raw["CLM_FROM_DT"]), "thru": _dates(ca_raw["CLM_THRU_DT"])})
    keep = ca["frm"].notna() & ca["thru"].notna() & (ca["frm"] <= ca["thru"]) & ca["frm"].between(
        pd.Timestamp(config.study_start), pd.Timestamp(config.study_end))
    ca = ca[keep].copy()
    ca["year"] = ca["frm"].dt.year

    bene = pd.concat([_read(config.csv_path(f), ["DESYNPUF_ID", "BENE_DEATH_DT", "BENE_HI_CVRAGE_TOT_MONS"]).assign(year=int(f["year"]))
                      for f in config.files("beneficiary")], ignore_index=True)
    death = _dates(bene["BENE_DEATH_DT"]).groupby(bene["DESYNPUF_ID"]).max()
    bene["hi"] = pd.to_numeric(bene["BENE_HI_CVRAGE_TOT_MONS"], errors="coerce").fillna(0)
    d = bene["DESYNPUF_ID"].map(death)
    alive = np.where(d.isna() | (d.dt.year > bene["year"]), 12, np.where(d.dt.year < bene["year"], 0, d.dt.month.fillna(0)))
    bene["member_months"] = np.maximum(0, np.minimum(bene["hi"], alive))

    # Stays: merge claims whose admission is on or before the discharge of the beneficiary's earlier stay.
    ip = ip.sort_values(["DESYNPUF_ID", "adm", "CLM_ID"]).reset_index(drop=True)
    prior_max = ip.groupby("DESYNPUF_ID")["dsch"].transform(lambda s: s.cummax().shift())
    ip["new_stay"] = prior_max.isna() | (ip["adm"] > prior_max)
    ip["stay_seq"] = ip.groupby("DESYNPUF_ID")["new_stay"].cumsum()
    stays = ip.groupby(["DESYNPUF_ID", "stay_seq"], as_index=False).agg(
        adm=("adm", "min"), dsch=("dsch", "max"), pay=("pay", "sum"))
    stays["year"] = stays["adm"].dt.year
    stays["los"] = (stays["dsch"] - stays["adm"]).dt.days

    end = pd.Timestamp(config.study_end)
    window = pd.to_timedelta(int(config.metrics["readmission_window_days"]), unit="D")
    stays = stays.sort_values(["DESYNPUF_ID", "adm"]).reset_index(drop=True)
    next_adm = stays.groupby("DESYNPUF_ID")["adm"].shift(-1)
    stays["death"] = stays["DESYNPUF_ID"].map(death)
    stays["died"] = stays["death"].notna() & (stays["death"] >= stays["adm"]) & (stays["death"] <= stays["dsch"])
    stays["short"] = stays["dsch"] > end - window
    stays["eligible"] = ~stays["died"] & ~stays["short"]
    stays["readmit"] = stays["eligible"] & next_adm.notna() & (next_adm > stays["dsch"]) & (
        next_adm <= stays["dsch"] + window)
    stays["dyear"] = stays["dsch"].dt.year

    out: dict[str, Any] = {"claims": {}, "payment": {}}
    for name, frame in (("inpatient", ip), ("outpatient", op), ("carrier", ca)):
        out["claims"][name] = {str(y): int(n) for y, n in frame.groupby("year").size().items()}
        out["payment"][name] = {str(y): float(v) for y, v in frame.groupby("year")["pay"].sum().items()}
    out["admissions"] = {str(y): int(n) for y, n in stays.groupby("year").size().items()}
    out["ed_proxy_visits"] = {str(y): int(n) for y, n in op[op["is_ed"]].groupby("year").size().items()}
    out["carrier_lines"] = {str(y): int(n) for y, n in ca.groupby("year")["lines"].sum().items()}
    out["member_months"] = {str(y): int(n) for y, n in bene.groupby("year")["member_months"].sum().items()}
    out["readmission"] = {"eligible_index": int(stays["eligible"].sum()), "readmissions": int(stays["readmit"].sum())}
    out["readmission_by_year"] = {str(y): {"eligible_index": int(g["eligible"].sum()), "readmissions": int(g["readmit"].sum())}
                                  for y, g in stays.groupby("dyear")}
    out["mean_los"] = float(stays["los"].mean()) if len(stays) else None

    allpay = pd.concat([ip[["DESYNPUF_ID", "year", "pay"]], op[["DESYNPUF_ID", "year", "pay"]], ca[["DESYNPUF_ID", "year", "pay"]]])
    per_bene = allpay.groupby(["year", "DESYNPUF_ID"])["pay"].sum()
    n_bene = bene.groupby("year")["DESYNPUF_ID"].nunique()
    share = {}
    pct = float(config.metrics["top_share_percent"])
    for year, n in n_bene.items():
        paid = per_bene.get(year, pd.Series(dtype=float)).sort_values(ascending=False)
        top = math.ceil(n * pct / 100.0)
        total = float(paid.sum())
        share[str(year)] = float(paid.iloc[:top].sum() / total) if total else None
    out["top_payment_share"] = share
    return out


def compare(con: duckdb.DuckDBPyConnection, config: Config) -> pd.DataFrame:
    """Rows of (check, warehouse value, independent value, difference, tolerance, passed)."""
    sql, pdk = compute_kpis(con), independent_kpis(config)
    rows: list[dict[str, Any]] = []

    def add(name: str, warehouse: float | None, independent: float | None, tolerance: float) -> None:
        w, i = (0.0 if v is None else float(v) for v in (warehouse, independent))
        diff = abs(w - i)
        rows.append({"check": name, "warehouse": w, "independent_pandas": i, "difference": diff,
                     "tolerance": tolerance, "passed": diff <= tolerance})

    years = sorted(set(sql["beneficiaries"]) | set(pdk["member_months"]))
    for setting in ("inpatient", "outpatient", "carrier"):
        for y in years:
            add(f"claims_{setting}_{y}", sql["claims"][setting].get(y, 0), pdk["claims"][setting].get(y, 0), 0)
            add(f"payment_{setting}_{y}", sql["payment"][setting].get(y, 0), pdk["payment"][setting].get(y, 0), MONEY_TOLERANCE)
    for y in years:
        add(f"admissions_{y}", sql["admissions"].get(y, 0), pdk["admissions"].get(y, 0), 0)
        add(f"ed_proxy_visits_{y}", (sql["ed_proxy_visits"] or {}).get(y, 0), pdk["ed_proxy_visits"].get(y, 0), 0)
        add(f"carrier_lines_{y}", sql["carrier_lines"].get(y, 0), pdk["carrier_lines"].get(y, 0), 0)
        add(f"member_months_{y}", sql["member_months"].get(y, 0), pdk["member_months"].get(y, 0), 0)
        add(f"top_payment_share_{y}", sql["top_payment_share"].get(y), pdk["top_payment_share"].get(y), RATE_TOLERANCE)
        rd = sql["readmission"].get(y, {})
        pr = pdk["readmission_by_year"].get(y, {})
        add(f"readmission_eligible_{y}", rd.get("eligible_index", 0), pr.get("eligible_index", 0), 0)
        add(f"readmission_events_{y}", rd.get("readmissions", 0), pr.get("readmissions", 0), 0)
    add("readmission_eligible_all", sql["readmission"]["all"]["eligible_index"], pdk["readmission"]["eligible_index"], 0)
    add("readmission_events_all", sql["readmission"]["all"]["readmissions"], pdk["readmission"]["readmissions"], 0)
    add("mean_length_of_stay_all", sql["mean_length_of_stay_days"]["all"], pdk["mean_los"], RATE_TOLERANCE)
    return pd.DataFrame(rows)
