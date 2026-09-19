"""Python code rules and the SQL macros must agree, including on malformed and unmapped input."""

import duckdb
import pytest

from medicare_claims.codes import hcpcs_group, is_valid_hcpcs, is_valid_icd9, normalize_code
from tests.conftest import REPO

RAW_CODES = ["250.00", "4280 ", "v5789", "ABC12", "", None, " 486", "E8889", "E88890", "V4", "7999", "99999",
             "99213", "G0008", "0001F", "J1100", "36415", "12", "A0428", "Z9999", "0999T"]


@pytest.fixture(scope="module")
def macro_con():
    con = duckdb.connect(":memory:")
    text = (REPO / "sql" / "01_staging.sql").read_text()
    for statement in text.split(";"):
        if "create or replace macro" in statement:
            con.execute("\n".join(line for line in statement.splitlines() if not line.strip().startswith("--")))
    return con


def test_normalization_trims_drops_dots_and_uppercases() -> None:
    assert normalize_code("250.00") == "25000"
    assert normalize_code(" 4280 ") == "4280"
    assert normalize_code("v5789") == "V5789"
    assert normalize_code("") is None and normalize_code("  ") is None and normalize_code(None) is None


def test_icd9_validity_rules() -> None:
    assert all(is_valid_icd9(c) for c in ("25000", "4019", "486", "V5789", "V45", "E8889", "E888"))
    assert not any(is_valid_icd9(c) for c in ("ABC12", "12", "V4", "E88890", "", None))


def test_hcpcs_validity_and_groups() -> None:
    assert is_valid_hcpcs("99213") and is_valid_hcpcs("G0008") and not is_valid_hcpcs("9921") and not is_valid_hcpcs(None)
    assert hcpcs_group("99213") == "Evaluation and management"
    assert hcpcs_group("36415") == "Surgery"
    assert hcpcs_group("80053") == "Pathology and laboratory"
    assert hcpcs_group("71020") == "Radiology"
    assert hcpcs_group("00100") == "Anesthesia"
    assert hcpcs_group("0001F") == "CPT category II and III"
    assert hcpcs_group("J1100") == "Drugs administered other than oral"
    assert hcpcs_group("G0008") == "Temporary procedures and professional services"
    assert hcpcs_group("Z9999") == "Unclassified" and hcpcs_group("12") == "Invalid or missing" and hcpcs_group(None) == "Invalid or missing"


def test_sql_macros_match_python_on_every_sample(macro_con) -> None:
    for raw in RAW_CODES:
        code = normalize_code(raw)
        sql_norm, sql_icd, sql_hcpcs, sql_group = macro_con.execute(
            "select norm_code(?), icd9_valid(norm_code(?)), hcpcs_valid(norm_code(?)), hcpcs_group(norm_code(?))",
            [raw, raw, raw, raw]).fetchone()
        assert sql_norm == code, raw
        assert bool(sql_icd) == is_valid_icd9(code), raw
        assert bool(sql_hcpcs) == is_valid_hcpcs(code), raw
        assert sql_group == hcpcs_group(code), raw


def test_ccs_mapping_is_cited_and_covers_common_codes() -> None:
    from medicare_claims.codes import load_ccs

    ccs = load_ccs(REPO / "reference" / "ccs_icd9_dx_2015.csv")
    assert len(ccs) > 15000 and len({v[0] for v in ccs.values()}) >= 280
    assert ccs["25000"][0] == 49 and ccs["4280"][0] == 108 and ccs["486"][0] == 122
    assert "99999" not in ccs  # well-formed but unmapped codes stay unmapped
