"""Run the dbt layer and prove it matches the legacy SQL build.

The legacy path (``medicare-claims build``) loads raw files and runs sql/ into schema ``main``. dbt reads
the same raw tables and writes its generated models to schema ``dbt`` in the same DuckDB file. The
equivalence check compares every model with its legacy table: row counts, and a two-way ``EXCEPT ALL``
so a single differing value in any column fails. Headline KPIs are then recomputed from the dbt schema.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pandas as pd

from medicare_claims.config import Config
from medicare_claims.model import sql_params

DBT_DIR = "dbt"
KPI_SQL = {
    "claims": "select count(*) from {s}.fact_claim_header where is_analytic",
    "paid_amount": "select sum(payment_amount) from {s}.fact_claim_header where is_analytic",
    "inpatient_stays": "select count(*) from {s}.fact_inpatient_stay",
    "readmission_eligible_index": "select sum(eligible_index_stays) from {s}.mart_quality_monitoring",
    "readmitted_stays": "select sum(readmitted_stays) from {s}.mart_quality_monitoring",
    "top_payment": "select sum(top_payment) from {s}.mart_payment_concentration",
    "provider_review_flags": "select count(*) from {s}.mart_provider_performance where review_flag",
}


def dbt_executable() -> str:
    found = shutil.which("dbt")
    if not found:
        raise RuntimeError("dbt is not installed; run `uv sync --extra dev`")
    return found


def run_dbt(config: Config, command: str = "build") -> subprocess.CompletedProcess[str]:
    """Run ``dbt <command>`` against the active profile's warehouse with the profile's parameters."""
    if config.warehouse == ":memory:":
        raise ValueError("dbt needs a warehouse file; build the profile with a file-backed warehouse first")
    project = config.root / DBT_DIR
    env = dict(os.environ, CLAIMS_DUCKDB=str(Path(config.warehouse).resolve()))
    args = [dbt_executable(), command, "--project-dir", str(project), "--profiles-dir", str(project),
            "--vars", json.dumps(sql_params(config))]
    return subprocess.run(args, cwd=project, env=env, text=True, capture_output=True, check=False)


def model_names(con: duckdb.DuckDBPyConnection) -> list[str]:
    rows = con.execute("select table_name from information_schema.tables where table_schema = 'dbt' "
                       "order by table_name").fetchall()
    return [str(r[0]) for r in rows]


def equivalence(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """One row per dbt model: legacy rows, dbt rows, rows only in either side, and a pass flag."""
    rows = []
    for name in model_names(con):
        legacy = int(con.execute(f"select count(*) from main.{name}").fetchone()[0])  # type: ignore[index]
        built = int(con.execute(f"select count(*) from dbt.{name}").fetchone()[0])  # type: ignore[index]
        only_legacy = int(con.execute(
            f"select count(*) from (select * from main.{name} except all select * from dbt.{name})").fetchone()[0])  # type: ignore[index]
        only_dbt = int(con.execute(
            f"select count(*) from (select * from dbt.{name} except all select * from main.{name})").fetchone()[0])  # type: ignore[index]
        rows.append({"model": name, "legacy_rows": legacy, "dbt_rows": built, "rows_only_in_legacy": only_legacy,
                     "rows_only_in_dbt": only_dbt, "passed": legacy == built and only_legacy == 0 and only_dbt == 0})
    return pd.DataFrame(rows)


def kpi_equivalence(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    rows = []
    for kpi, sql in KPI_SQL.items():
        legacy = con.execute(sql.format(s="main")).fetchone()[0]  # type: ignore[index]
        built = con.execute(sql.format(s="dbt")).fetchone()[0]  # type: ignore[index]
        rows.append({"kpi": kpi, "legacy": float(legacy or 0), "dbt": float(built or 0),
                     "passed": float(legacy or 0) == float(built or 0)})
    return pd.DataFrame(rows)


def write_equivalence(config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    with duckdb.connect(config.warehouse, read_only=True) as con:
        models, kpis = equivalence(con), kpi_equivalence(con)
    out = config.reports_dir
    out.mkdir(parents=True, exist_ok=True)
    models.to_csv(out / "dbt_equivalence.csv", index=False)
    kpis.to_csv(out / "dbt_kpi_equivalence.csv", index=False)
    return models, kpis
