"""Extract CMS zips and load raw CSVs into DuckDB as all-text tables.

Raw tables keep every source value as text so no information is lost before staging. A fixture
CSV may carry only the columns it needs; missing columns load as NULL, and files that lack a
column the pipeline requires are rejected with a clear message.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import duckdb

from medicare_claims.config import Config

BENEFICIARY_COLUMNS = [
    "DESYNPUF_ID", "BENE_BIRTH_DT", "BENE_DEATH_DT", "BENE_SEX_IDENT_CD", "BENE_RACE_CD",
    "BENE_ESRD_IND", "SP_STATE_CODE", "BENE_COUNTY_CD", "BENE_HI_CVRAGE_TOT_MONS",
    "BENE_SMI_CVRAGE_TOT_MONS", "BENE_HMO_CVRAGE_TOT_MONS", "PLAN_CVRG_MOS_NUM",
    "SP_ALZHDMTA", "SP_CHF", "SP_CHRNKIDN", "SP_CNCR", "SP_COPD", "SP_DEPRESSN", "SP_DIABETES",
    "SP_ISCHMCHT", "SP_OSTEOPRS", "SP_RA_OA", "SP_STRKETIA", "MEDREIMB_IP", "BENRES_IP",
    "PPPYMT_IP", "MEDREIMB_OP", "BENRES_OP", "PPPYMT_OP", "MEDREIMB_CAR", "BENRES_CAR", "PPPYMT_CAR",
]


def _series(prefix: str, count: int) -> list[str]:
    return [f"{prefix}{i}" for i in range(1, count + 1)]


INSTITUTIONAL_COMMON = [
    "DESYNPUF_ID", "CLM_ID", "SEGMENT", "CLM_FROM_DT", "CLM_THRU_DT", "PRVDR_NUM", "CLM_PMT_AMT",
    "NCH_PRMRY_PYR_CLM_PD_AMT", "AT_PHYSN_NPI", "OP_PHYSN_NPI", "OT_PHYSN_NPI",
    "ADMTNG_ICD9_DGNS_CD",
]
INPATIENT_COLUMNS = (
    INSTITUTIONAL_COMMON + ["CLM_ADMSN_DT", "CLM_UTLZTN_DAY_CNT", "NCH_BENE_DSCHRG_DT", "CLM_DRG_CD"]
    + _series("ICD9_DGNS_CD_", 10) + _series("ICD9_PRCDR_CD_", 6) + _series("HCPCS_CD_", 45)
)
OUTPATIENT_COLUMNS = (
    INSTITUTIONAL_COMMON + _series("ICD9_DGNS_CD_", 10) + _series("ICD9_PRCDR_CD_", 6)
    + _series("HCPCS_CD_", 45)
)
CARRIER_COLUMNS = (
    ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_THRU_DT"] + _series("ICD9_DGNS_CD_", 8)
    + _series("PRF_PHYSN_NPI_", 13) + _series("TAX_NUM_", 13) + _series("HCPCS_CD_", 13)
    + _series("LINE_NCH_PMT_AMT_", 13) + _series("LINE_BENE_PTB_DDCTBL_AMT_", 13)
    + _series("LINE_BENE_PRMRY_PYR_PD_AMT_", 13) + _series("LINE_COINSRNC_AMT_", 13)
    + _series("LINE_ALOWD_CHRG_AMT_", 13) + _series("LINE_PRCSG_IND_CD_", 13)
    + _series("LINE_ICD9_DGNS_CD_", 13)
)
EXPECTED = {
    "beneficiary": BENEFICIARY_COLUMNS,
    "inpatient": INPATIENT_COLUMNS,
    "outpatient": OUTPATIENT_COLUMNS,
    "carrier": CARRIER_COLUMNS,
}
REQUIRED = {
    "beneficiary": ["DESYNPUF_ID", "BENE_BIRTH_DT", "BENE_SEX_IDENT_CD"],
    "inpatient": ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_PMT_AMT", "NCH_BENE_DSCHRG_DT"],
    "outpatient": ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "CLM_PMT_AMT"],
    "carrier": ["DESYNPUF_ID", "CLM_ID", "CLM_FROM_DT", "LINE_NCH_PMT_AMT_1"],
}


class IngestError(RuntimeError):
    """A source file is missing or lacks columns the pipeline requires."""


def extract(config: Config) -> list[Path]:
    """Unzip source archives into the interim folder (skipped when the CSV already exists)."""
    interim = config.interim_dir
    if interim is None:
        return []
    interim.mkdir(parents=True, exist_ok=True)
    written = []
    for kind in ("beneficiary", "inpatient", "outpatient", "carrier"):
        for item in config.files(kind):
            target = interim / str(item["csv"])
            if not target.exists():
                archive = config.raw_dir / str(item["name"])
                if not archive.exists():
                    raise IngestError(f"Missing {archive}. Run `medicare-claims download` first.")
                with zipfile.ZipFile(archive) as zf:
                    member = next((n for n in zf.namelist() if n.lower().endswith(str(item["csv"]).lower())), None)
                    if member is None:
                        raise IngestError(f"{archive.name} does not contain {item['csv']}")
                    with zf.open(member) as src, target.open("wb") as dst:
                        while chunk := src.read(1 << 20):
                            dst.write(chunk)
            written.append(target)
    return written


def _select_list(con: duckdb.DuckDBPyConnection, path: Path, kind: str) -> str:
    present = {row[0].upper() for row in con.execute(
        "describe select * from read_csv(?, all_varchar = true, sample_size = 5000)", [str(path)]).fetchall()}
    missing = [c for c in REQUIRED[kind] if c not in present]
    if missing:
        raise IngestError(f"{path.name} is missing required columns {missing} for {kind} claims")
    return ", ".join(f'"{c}"' if c in present else f'NULL::VARCHAR AS "{c}"' for c in EXPECTED[kind])


def load_raw(con: duckdb.DuckDBPyConnection, config: Config) -> dict[str, int]:
    """Create raw_<kind> tables with a source_file column (and bene_year for beneficiaries)."""
    counts: dict[str, int] = {}
    for kind in ("beneficiary", "inpatient", "outpatient", "carrier"):
        parts = []
        for item in config.files(kind):
            path = config.csv_path(item)
            if not path.exists():
                raise IngestError(f"Missing {path}")
            year = f", {int(item['year'])}::INTEGER AS bene_year" if kind == "beneficiary" else ""
            parts.append(
                f"select {_select_list(con, path, kind)}, '{path.name}' as source_file{year} "
                f"from read_csv('{path}', all_varchar = true, header = true)")
        con.execute(f"create or replace table raw_{kind} as " + " union all ".join(parts))
        counts[kind] = int(con.execute(f"select count(*) from raw_{kind}").fetchone()[0])  # type: ignore[index]
    return counts
