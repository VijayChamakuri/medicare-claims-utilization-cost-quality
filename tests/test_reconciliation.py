"""Reconciliation must pass on good data and fail loudly when the warehouse is wrong."""

import pytest

from medicare_claims.model import blocking_failures, build_warehouse, run_sql_file, sql_params
from medicare_claims.validation import compare
from tests.conftest import fixture_config


def test_blocking_checks_pass_on_the_fixture(warehouse) -> None:
    assert blocking_failures(warehouse) == []
    row = warehouse.execute("select count(*), count(*) filter (where blocking) from reconciliation_results").fetchone()
    assert row[0] >= 30 and row[1] >= 28


def test_independent_pandas_recomputation_agrees_within_tolerance(warehouse, config) -> None:
    result = compare(warehouse, config)
    assert len(result) >= 40
    assert result["passed"].all(), result[~result["passed"]].to_string()
    assert result.loc[result["check"].str.startswith("payment_"), "tolerance"].eq(0.005).all()  # money: half a cent


def test_a_payment_dropped_from_the_warehouse_is_caught_by_sql_reconciliation() -> None:
    config = fixture_config()
    con = build_warehouse(config)
    con.execute("update fact_claim_header set payment_amount = payment_amount - 100 where claim_key = 'inpatient:B01:I01'")
    run_sql_file(con, config.sql_dir / "08_reconciliation.sql", sql_params(config))
    failed = {name for name, _, _ in blocking_failures(con)}
    assert "payment_source_to_header_total" in failed


def test_a_wrong_mart_value_is_caught_by_the_independent_recomputation() -> None:
    config = fixture_config()
    con = build_warehouse(config)
    con.execute("update mart_payment_annual set payment_amount = payment_amount + 1 where setting = 'inpatient' and year = 2008")
    bad = compare(con, config)
    failed = set(bad.loc[~bad["passed"], "check"])
    assert failed == {"payment_inpatient_2008"}


def test_a_dropped_stay_is_caught(config) -> None:
    con = build_warehouse(fixture_config())
    con.execute("delete from fact_inpatient_stay where beneficiary_id = 'B03' and stay_seq = 1")
    run_sql_file(con, config.sql_dir / "08_reconciliation.sql", sql_params(config))
    failed = {name for name, _, _ in blocking_failures(con)}
    assert {"stays_to_utilization_mart", "stay_claims_to_inpatient_claims"} & failed


def test_informational_tie_outs_never_block(warehouse) -> None:
    rows = warehouse.execute("select blocking from reconciliation_results where category = 'informational'").fetchall()
    assert all(not b for (b,) in rows)


@pytest.mark.parametrize("key", ["claim_key", "stay_key"])
def test_primary_keys_are_checked(warehouse, key) -> None:
    n = warehouse.execute("select count(*) from reconciliation_results where check_name like ? and passed", ["key_unique_%"]).fetchone()[0]
    assert n >= 10
