"""Build the DuckDB warehouse: load raw files, then run the numbered SQL files in order."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from medicare_claims.config import Config
from medicare_claims.ingest import extract, load_raw


class PipelineError(RuntimeError):
    """A SQL stage or a blocking reconciliation check failed."""


def sql_params(config: Config) -> dict[str, Any]:
    m = config.metrics
    risk = m["risk_tier"]
    return {
        "study_start": config.study_start.isoformat(),
        "study_end": config.study_end.isoformat(),
        "readmission_days": int(m["readmission_window_days"]),
        "ed_codes": list(m["ed_hcpcs_codes"]),
        "top_share_percent": float(m["top_share_percent"]),
        "peer_min_providers": int(m["review"]["peer_min_providers"]),
        "min_claims": int(m["review"]["min_claims"]),
        "iqr_multiplier": float(m["review"]["iqr_multiplier"]),
        "comorb_low_max": int(risk["comorbidity_points"]["low_max"]),
        "comorb_medium_max": int(risk["comorbidity_points"]["medium_max"]),
        "adm_one": int(risk["admission_points"]["one"]),
        "adm_two_plus": int(risk["admission_points"]["two_plus"]),
        "paid_medium_min": float(risk["paid_points"]["medium_min"]),
        "paid_high_min": float(risk["paid_points"]["high_min"]),
        "tier_low_max": int(risk["tiers"]["low_max"]),
        "tier_medium_max": int(risk["tiers"]["medium_max"]),
    }


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, params: dict[str, Any]) -> None:
    """Run every statement in a SQL file, binding only the named parameters each statement uses."""
    text = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                     if not line.strip().startswith("--"))
    for statement in (part.strip() for part in text.split(";")):
        if statement:
            used = {k: v for k, v in params.items() if f"${k}" in statement}
            try:
                con.execute(statement, used)
            except duckdb.Error as error:
                raise PipelineError(f"{path.name}: {error}\n{statement[:300]}") from error


def load_reference(con: duckdb.DuckDBPyConnection, config: Config) -> None:
    path = config.root / str(config.raw["reference"]["ccs"]["compact_file"])
    con.execute("create or replace table ref_ccs_dx as select icd9_code, ccs_category::integer as ccs_category, "
                "ccs_category_name from read_csv(?, header = true, all_varchar = true)", [str(path)])


def build_warehouse(config: Config, con: duckdb.DuckDBPyConnection | None = None) -> duckdb.DuckDBPyConnection:
    """Extract, load and transform. Returns an open connection to the built warehouse."""
    if config.warehouse != ":memory:":
        Path(config.warehouse).parent.mkdir(parents=True, exist_ok=True)
    con = con or duckdb.connect(config.warehouse)
    extract(config)
    load_raw(con, config)
    load_reference(con, config)
    params = sql_params(config)
    for path in sorted(config.sql_dir.glob("[0-9][0-9]*.sql")):
        run_sql_file(con, path, params)
    return con


def blocking_failures(con: duckdb.DuckDBPyConnection) -> list[tuple[str, float, float]]:
    rows = con.execute("select check_name, expected, actual from reconciliation_results "
                       "where blocking and not passed order by check_name").fetchall()
    return [(str(r[0]), float(r[1]), float(r[2])) for r in rows]
