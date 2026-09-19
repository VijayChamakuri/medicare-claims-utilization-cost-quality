"""Every headline KPI, asserted exactly against values derived by hand (tests/fixtures/README.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from medicare_claims.metrics import compute_data_quality, compute_kpis, condition_rows

EXPECTED = json.loads((Path(__file__).parent / "fixtures" / "expected_kpis.json").read_text())
YEARS = ("2008", "2009", "2010")


@pytest.fixture(scope="module")
def kpis(warehouse):
    return compute_kpis(warehouse)


def ratio(spec):  # [numerator, denominator, scale]
    return spec[0] / spec[1] * spec[2]


def test_beneficiaries_and_member_months(kpis) -> None:
    assert {y: int(v) for y, v in kpis["beneficiaries"].items()} == EXPECTED["beneficiaries"]
    assert {y: int(v) for y, v in kpis["member_months"].items()} == EXPECTED["member_months"]


def test_claim_counts_by_setting_and_total(kpis) -> None:
    for setting in ("inpatient", "outpatient", "carrier"):
        assert {y: int(v) for y, v in kpis["claims"][setting].items()} == EXPECTED["claims"][setting]
    assert {y: int(v) for y, v in kpis["claims_total"].items()} == EXPECTED["claims_total"]


def test_payment_amounts_to_the_cent(kpis) -> None:
    for setting in ("inpatient", "outpatient", "carrier"):
        for y in YEARS:
            assert kpis["payment"][setting][y] == pytest.approx(EXPECTED["payment"][setting][y], abs=0.005)
    for y in YEARS:
        assert kpis["payment_total"][y] == pytest.approx(EXPECTED["payment_total"][y], abs=0.005)
    assert kpis["payment_total_all_years"] == pytest.approx(EXPECTED["payment_total_all_years"], abs=0.005)


def test_admissions_and_rates(kpis) -> None:
    assert {y: int(v) for y, v in kpis["admissions"].items()} == EXPECTED["admissions"]
    assert kpis["admissions_all_years"] == EXPECTED["admissions_all_years"]
    for key, spec in EXPECTED["admissions_per_1000_member_years"].items():
        assert kpis["admissions_per_1000_member_years"][key] == pytest.approx(ratio(spec))
    for y, spec in EXPECTED["claims_per_1000_member_years"].items():
        assert kpis["claims_per_1000_member_years"][y] == pytest.approx(ratio(spec))


def test_ed_proxy_and_outpatient_visits_and_carrier_lines(kpis) -> None:
    assert {y: int(v) for y, v in kpis["ed_proxy_visits"].items()} == EXPECTED["ed_proxy_visits"]
    for y, spec in EXPECTED["ed_proxy_per_1000_member_years"].items():
        assert kpis["ed_proxy_per_1000_member_years"][y] == pytest.approx(ratio(spec))
    for y, spec in EXPECTED["outpatient_visits_per_1000_member_years"].items():
        assert kpis["outpatient_visits_per_1000_member_years"][y] == pytest.approx(ratio(spec))
    assert {y: int(v) for y, v in kpis["carrier_lines"].items()} == EXPECTED["carrier_lines"]


def test_unique_beneficiaries_by_setting(kpis) -> None:
    for setting in ("inpatient", "outpatient", "carrier"):
        assert {y: int(v) for y, v in kpis["unique_beneficiaries"][setting].items()} == EXPECTED["unique_beneficiaries"][setting]


def test_length_of_stay_and_payment_ratios(kpis) -> None:
    for y, (total, n) in EXPECTED["length_of_stay"].items():
        assert kpis["mean_length_of_stay_days"][y] == pytest.approx(total / n)
    for y, (num, den) in EXPECTED["payment_per_admission"].items():
        assert kpis["payment_per_admission"][y] == pytest.approx(num / den)
    for y, (num, den) in EXPECTED["payment_per_beneficiary"].items():
        assert kpis["payment_per_beneficiary"][y] == pytest.approx(num / den)
    for y, (num, den) in EXPECTED["payment_per_claim"].items():
        assert kpis["payment_per_claim"][y] == pytest.approx(num / den)


def test_readmission_proxy_index_and_exclusion_logic(kpis) -> None:
    for y, spec in EXPECTED["readmission"].items():
        got = kpis["readmission"][y]
        assert got["eligible_index"] == spec["eligible_index"], y
        assert got["readmissions"] == spec["readmissions"], y
        for key in ("excluded_died_in_stay", "excluded_insufficient_followup"):
            if key in spec:
                assert got[key] == spec[key], (y, key)
    assert kpis["readmission"]["all"]["rate"] == pytest.approx(2 / 13)
    assert kpis["readmission"]["2008"]["rate"] == pytest.approx(2 / 7)


def test_payment_concentration_top_five_percent(kpis) -> None:
    for y, (num, den) in EXPECTED["top_5pct_payment_share"].items():
        assert kpis["top_payment_share"][y] == pytest.approx(num / den)
    assert kpis["top_payment_beneficiary"] == EXPECTED["top_5pct_beneficiary"]


def test_risk_tier_counts_and_boundaries(kpis, warehouse) -> None:
    assert kpis["risk_tier_counts"] == EXPECTED["risk_tier_counts"]
    rows = {(b, y): (s, t) for b, y, s, t in warehouse.execute(
        "select beneficiary_id, year, risk_score, utilization_risk_tier from mart_member_risk").fetchall()}
    assert rows[("B01", 2009)] == (6, "high")
    assert rows[("B05", 2009)] == (3, "medium")      # boundary: score 3 is the top of medium
    assert rows[("B02", 2009)] == (4, "high")        # boundary: score 4 is the bottom of high
    assert rows[("B01", 2010)] == (1, "low")         # boundary: score 1 is the top of low
    assert rows[("B06", 2010)] == (4, "high")        # four flags earn 2 points, negative paid earns 0
    assert rows[("B12", 2008)][1] == "not_assessed"


def test_provider_review_flags_use_peer_quartiles(kpis) -> None:
    assert kpis["review_flags"] == {y: v for y, v in EXPECTED["review_flags"].items() if v}


def test_data_quality_counts_and_excluded_payment(warehouse) -> None:
    dq = compute_data_quality(warehouse)
    for key, expected in EXPECTED["data_quality"].items():
        if isinstance(expected, dict):
            assert dq[key] == expected, key
        else:
            assert dq[key] == pytest.approx(expected, abs=0.005), key


def test_condition_grouping_uses_cited_ccs_categories(warehouse) -> None:
    got = condition_rows(warehouse, 2008, "inpatient")
    for cat, (claims, pay) in EXPECTED["condition_inpatient_2008"].items():
        assert got[cat][0] == claims, cat
        assert got[cat][1] == pytest.approx(pay), cat
    assert set(got) == set(EXPECTED["condition_inpatient_2008"])
