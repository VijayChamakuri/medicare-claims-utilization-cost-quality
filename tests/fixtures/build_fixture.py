"""Write the hand-calculated fixture CSVs. Run: python tests/fixtures/build_fixture.py

The fixture is narrow (only the columns the pipeline reads); the loader fills the rest with NULL.
Every value asserted in tests/test_fixture_kpis.py is derived by hand in tests/fixtures/README.md
from these rows, never from pipeline output.
"""

from __future__ import annotations

import csv
from pathlib import Path

OUT = Path(__file__).resolve().parent / "raw"

BENE_COLS = ["DESYNPUF_ID", "BENE_BIRTH_DT", "BENE_DEATH_DT", "BENE_SEX_IDENT_CD", "BENE_RACE_CD",
             "BENE_ESRD_IND", "BENE_HI_CVRAGE_TOT_MONS", "BENE_SMI_CVRAGE_TOT_MONS",
             "SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR", "SP_COPD", "SP_DEPRESSN", "SP_DIABETES",
             "SP_ISCHMCHT", "SP_OSTEOPRS", "SP_RA_OA", "SP_STRKETIA"]
FLAGS = ["SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR", "SP_COPD", "SP_DEPRESSN", "SP_DIABETES",
         "SP_ISCHMCHT", "SP_OSTEOPRS", "SP_RA_OA", "SP_STRKETIA"]

# id, birth, death, sex, race, HI months by year, chronic flags (2008), flags changes in 2009
BENES = {
    "B01": ("19400305", "", "2", "1", {2008: 12, 2009: 12, 2010: 12}, {"SP_CHF", "SP_DIABETES"}),
    "B02": ("19350719", "", "1", "1", {2008: 12, 2009: 12, 2010: 12}, {"SP_ISCHMCHT"}),
    "B03": ("19500110", "", "2", "2", {2008: 12, 2009: 12, 2010: 12}, {"SP_DIABETES"}),
    "B04": ("19450930", "", "1", "1", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B05": ("19600502", "", "2", "5", {2008: 6, 2009: 12, 2010: 12}, set()),
    "B06": ("19551215", "", "1", "2", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B07": ("19480820", "", "2", "1", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B08": ("19420411", "", "1", "3", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B09": ("19530627", "", "2", "1", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B10": ("19380102", "", "1", "1", {2008: 12, 2009: 12, 2010: 12}, set()),
    "B11": ("19430914", "20090310", "2", "1", {2008: 12, 2009: 3}, set()),
    "B12": ("19390523", "20080615", "1", "1", {2008: 6}, set()),
}
FLAGS_2009_EXTRA = {"B04": {"SP_COPD", "SP_CHF"}, "B06": {"SP_ALZHDMTA", "SP_CHF", "SP_COPD", "SP_DIABETES"}}


def write(name: str, columns: list[str], rows: list[dict[str, str]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def beneficiaries() -> None:
    for year in (2008, 2009, 2010):
        rows = []
        for bid, (birth, death, sex, race, hi, flags) in BENES.items():
            if year not in hi:
                continue
            active = set(flags) | (FLAGS_2009_EXTRA.get(bid, set()) if year >= 2009 else set())
            row = {"DESYNPUF_ID": bid, "BENE_BIRTH_DT": birth, "BENE_DEATH_DT": death,
                   "BENE_SEX_IDENT_CD": sex, "BENE_RACE_CD": race, "BENE_ESRD_IND": "0",
                   "BENE_HI_CVRAGE_TOT_MONS": str(hi[year]), "BENE_SMI_CVRAGE_TOT_MONS": str(hi[year])}
            for f in FLAGS:
                row[f] = "1" if f in active else "2"
            rows.append(row)
        write(f"beneficiary_{year}.csv", BENE_COLS, rows)


IP_COLS = ["DESYNPUF_ID", "CLM_ID", "SEGMENT", "CLM_FROM_DT", "CLM_THRU_DT", "PRVDR_NUM", "CLM_PMT_AMT",
           "AT_PHYSN_NPI", "CLM_ADMSN_DT", "NCH_BENE_DSCHRG_DT", "CLM_UTLZTN_DAY_CNT", "CLM_DRG_CD",
           "ICD9_DGNS_CD_1"]


def inpatient() -> None:
    def ip(bene, clm, frm, thru, fac, pmt, dx, seg="1", admit=None, dsch=None):
        return {"DESYNPUF_ID": bene, "CLM_ID": clm, "SEGMENT": seg, "CLM_FROM_DT": frm, "CLM_THRU_DT": thru,
                "PRVDR_NUM": fac, "CLM_PMT_AMT": pmt, "AT_PHYSN_NPI": "1000000001",
                "CLM_ADMSN_DT": admit if admit is not None else frm,
                "NCH_BENE_DSCHRG_DT": dsch if dsch is not None else thru, "CLM_UTLZTN_DAY_CNT": "", "CLM_DRG_CD": "100",
                "ICD9_DGNS_CD_1": dx}

    rows = [
        ip("B01", "I01", "20080201", "20080205", "F1", "10000.00", "4280"),
        ip("B01", "I02", "20080220", "20080225", "F1", "8000.00", "4280"),
        ip("B01", "I03", "20080410", "20080412", "F2", "5000.00", "4019"),
        ip("B02", "I04", "20080501", "20080504", "F2", "12000.00", "41401"),
        ip("B02", "I05", "20080504", "20080510", "F3", "9000.00", "41401"),
        ip("B03", "I06", "20081115", "20081120", "F1", "7500.00", "250.00"),
        ip("B03", "I06", "20081115", "20081120", "F1", "7500.00", "250.00"),  # exact duplicate row
        ip("B03", "I07", "20081210", "20081215", "F1", "6000.00", "25000"),
        ip("B04", "I08", "20090110", "20090113", "F3", "4000.00", "4280 "),
        ip("B04", "I09", "20090220", "20090221", "F3", "500.00", "486"),
        ip("B06", "I10", "20090601", "20090603", "F2", "-2000.00", ""),
        ip("B12", "I11", "20080610", "20080615", "F2", "15000.00", "486"),
        ip("B11", "I12", "20090225", "20090301", "F1", "9500.00", "v5789"),
        ip("B07", "I13", "20101210", "20101215", "F3", "6500.00", "4019"),
        ip("B08", "I14", "20090710", "20090705", "F2", "3000.00", "4019", admit="20090710", dsch="20090705"),
        ip("B09", "I15", "20090901", "20090904", "F1", "6000.00", "ABC12"),
        ip("B09", "I15", "", "", "F1", "2000.00", "", seg="2", admit="", dsch=""),
        ip("B10", "I16", "20071220", "20071230", "F2", "4500.00", "486"),
        ip("B05", "I17", "20080315", "20080318", "F3", "3500.00", "99999"),
        ip("B10", "I18", "20091005", "20091008", "F9", "60000.00", "486"),
    ]
    write("inpatient.csv", IP_COLS, rows)


OP_COLS = ["DESYNPUF_ID", "CLM_ID", "SEGMENT", "CLM_FROM_DT", "CLM_THRU_DT", "PRVDR_NUM", "CLM_PMT_AMT",
           "ICD9_DGNS_CD_1", "HCPCS_CD_1", "HCPCS_CD_2"]


def outpatient() -> None:
    def op(bene, clm, frm, fac, pmt, h1, h2="", seg="1", dx=""):
        return {"DESYNPUF_ID": bene, "CLM_ID": clm, "SEGMENT": seg, "CLM_FROM_DT": frm,
                "CLM_THRU_DT": frm, "PRVDR_NUM": fac, "CLM_PMT_AMT": pmt, "ICD9_DGNS_CD_1": dx,
                "HCPCS_CD_1": h1, "HCPCS_CD_2": h2}

    rows = [
        op("B01", "O01", "20080305", "F5", "600.00", "99283"),
        op("B02", "O02", "20080306", "F5", "400.00", "99281", "71020"),
        op("B03", "O03", "20090401", "F6", "350.00", "99285"),
        op("B04", "O04", "20090402", "F6", "200.00", "99213"),
        op("B05", "O05", "20080215", "F5", "150.00", "80053"),
        op("B06", "O06", "20100505", "F6", "300.00", "G0008"),
        op("B07", "O07", "20091111", "F5", "-50.00", "99213"),
        op("B08", "O08", "20100115", "F6", "0.00", "99213"),
        op("B09", "O09", "20091201", "F5", "500.00", "99284"),
        op("B10", "O10", "20080707", "F6", "250.00", "36415"),
        op("B10", "O11", "20071215", "F6", "700.00", "99213"),
        op("B03", "O12", "20090615", "F6", "100.00", "99213"),
        {**op("B03", "O12", "", "F6", "25.00", "", seg="2"), "CLM_THRU_DT": ""},
    ]
    write("outpatient.csv", OP_COLS, rows)


def carrier() -> None:
    cols = ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_THRU_DT", "ICD9_DGNS_CD_1"]
    for i in range(1, 5):
        cols += [f"HCPCS_CD_{i}", f"LINE_NCH_PMT_AMT_{i}", f"PRF_PHYSN_NPI_{i}"]

    def ca(bene, clm, frm, dx, lines):
        row = {c: "" for c in cols}
        row.update({"DESYNPUF_ID": bene, "CLM_ID": clm, "CLM_FROM_DT": frm, "CLM_THRU_DT": frm,
                    "ICD9_DGNS_CD_1": dx})
        for i, (h, pmt, npi) in enumerate(lines, start=1):
            row[f"HCPCS_CD_{i}"], row[f"LINE_NCH_PMT_AMT_{i}"], row[f"PRF_PHYSN_NPI_{i}"] = h, pmt, npi
        return row

    rows = [
        ca("B01", "C01", "20080301", "25000", [("99213", "60.00", "N1"), ("85025", "15.00", "N1"), ("36415", "5.00", "N2")]),
        ca("B02", "C02", "20080601", "41401", [("99214", "100.00", "N2"), ("71020", "40.00", "N3")]),
        ca("B03", "C03", "20090115", "25000", [("99214", "90.00", "N3"), ("", "0.00", "")]),  # second slot is CMS padding, not a line
        ca("B04", "C04", "20090303", "4019", [("99213", "20.00", "N1"), ("99213", "30.00", "N1"), ("80053", "40.00", "N4"), ("36415", "10.00", "N4")]),
        ca("B05", "C05", "20080415", "4019", [("99213", "25.00", "N4")]),
        ca("B06", "C06", "20100202", "4019", [("99213", "55.00", "N2"), ("99214", "45.00", "N2")]),
        ca("B10", "C07", "20090808", "486", [("99213", "70.00", "N3")]),
    ]
    write("carrier.csv", cols, rows)


if __name__ == "__main__":
    beneficiaries()
    inpatient()
    outpatient()
    carrier()
    print("fixture written to", OUT)
