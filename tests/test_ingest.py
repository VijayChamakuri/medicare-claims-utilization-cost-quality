import shutil

import duckdb
import pytest

from medicare_claims.ingest import IngestError, load_raw
from tests.conftest import fixture_config


def test_fixture_loads_every_file_and_fills_missing_columns(config) -> None:
    con = duckdb.connect(":memory:")
    counts = load_raw(con, config)
    assert counts == {"beneficiary": 33, "inpatient": 20, "outpatient": 13, "carrier": 7}
    assert con.execute("select count(*) from raw_inpatient where \"ICD9_DGNS_CD_10\" is not null").fetchone()[0] == 0
    assert set(con.execute("select distinct bene_year from raw_beneficiary").fetchall()) == {(2008,), (2009,), (2010,)}
    assert con.execute("select count(distinct source_file) from raw_beneficiary").fetchone()[0] == 3


def test_all_values_are_loaded_as_text_without_loss(config) -> None:
    con = duckdb.connect(":memory:")
    load_raw(con, config)
    assert con.execute("select typeof(\"CLM_PMT_AMT\") from raw_inpatient limit 1").fetchone()[0] == "VARCHAR"
    assert con.execute("select \"ICD9_DGNS_CD_1\" from raw_inpatient where \"CLM_ID\" = 'I08'").fetchone()[0] == "4280 "  # not trimmed


def test_a_file_missing_a_required_column_is_rejected(tmp_path) -> None:
    cfg = fixture_config()
    raw = tmp_path / "raw"
    shutil.copytree(cfg.raw_dir, raw)
    (raw / "inpatient.csv").write_text("DESYNPUF_ID,CLM_ID\nB01,X1\n")
    cfg.raw["profiles"]["fixture"]["raw_dir"] = str(raw)
    with pytest.raises(IngestError, match="missing required columns"):
        load_raw(duckdb.connect(":memory:"), cfg)


def test_a_missing_file_is_reported_by_name(tmp_path) -> None:
    cfg = fixture_config()
    cfg.raw["profiles"]["fixture"]["raw_dir"] = str(tmp_path / "nowhere")
    with pytest.raises(IngestError, match="Missing"):
        load_raw(duckdb.connect(":memory:"), cfg)
