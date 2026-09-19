"""Grain and key behavior of the star schema on the fixture."""

import pytest


def rows(con, sql, params=None):
    return con.execute(sql, params or []).fetchall()


def test_header_has_one_row_per_claim_and_segments_are_merged(warehouse) -> None:
    assert rows(warehouse, "select count(*), count(distinct claim_key) from fact_claim_header") == [(37, 37)]  # 18 inpatient + 12 outpatient + 7 carrier, counted by hand
    i15 = rows(warehouse, "select segment_count, payment_amount, from_date, thru_date from fact_claim_header where claim_key = 'inpatient:B09:I15'")
    assert i15 == [(2, 8000, __import__("datetime").date(2009, 9, 1), __import__("datetime").date(2009, 9, 4))]
    o12 = rows(warehouse, "select segment_count, payment_amount from fact_claim_header where claim_key = 'outpatient:B03:O12'")
    assert o12 == [(2, 125)]


def test_exact_duplicate_rows_are_dropped_once(warehouse) -> None:
    assert rows(warehouse, "select payment_amount from fact_claim_header where claim_key = 'inpatient:B03:I06'") == [(7500,)]
    assert rows(warehouse, "select count(*) from stg_ip_all where dup_rank > 1") == [(1,)]


def test_carrier_header_payment_equals_its_line_payments(warehouse) -> None:
    got = rows(warehouse, "select h.claim_id, h.payment_amount, sum(l.line_nch_pmt_amt), count(l.line_num) from fact_claim_header h "
                          "join fact_claim_line l using (claim_key) where h.setting = 'carrier' group by 1, 2 order by 1")
    assert got[0] == ("C01", 80, 80, 3) and got[3] == ("C04", 100, 100, 4)
    assert all(pay == lines for _, pay, lines, _ in got)


def test_claims_are_flagged_not_deleted_when_invalid_or_out_of_window(warehouse) -> None:
    flags = {r[0]: r[1:] for r in rows(warehouse, "select claim_id, date_valid, in_study_window, is_analytic from fact_claim_header "
                                                   "where claim_id in ('I14', 'I16', 'O11', 'I01')")}
    assert flags["I14"] == (False, True, False)   # admit after discharge
    assert flags["I16"] == (True, False, False)   # 2007
    assert flags["O11"] == (True, False, False)
    assert flags["I01"] == (True, True, True)


def test_inpatient_claims_are_dated_by_admission(warehouse) -> None:
    assert rows(warehouse, "select count(*) from fact_claim_header where setting = 'inpatient' and is_analytic and service_date <> admit_date") == [(0,)]


def test_transfer_claims_continue_one_stay(warehouse) -> None:
    b02 = rows(warehouse, "select claim_count, length_of_stay_days, payment_amount from fact_inpatient_stay where beneficiary_id = 'B02'")
    assert b02 == [(2, 9, 21000)]
    assert rows(warehouse, "select count(*) from fact_inpatient_stay") == [(15,)]


def test_stay_keys_and_lengths(warehouse) -> None:
    assert rows(warehouse, "select count(*), count(distinct stay_key), min(length_of_stay_days) from fact_inpatient_stay") == [(15, 15, 1)]
    assert rows(warehouse, "select count(*) from fact_inpatient_stay where admit_date > discharge_date") == [(0,)]


def test_dimension_keys_are_unique_and_complete(warehouse) -> None:
    assert rows(warehouse, "select count(*), count(distinct beneficiary_id) from dim_beneficiary") == [(12, 12)]
    assert rows(warehouse, "select count(*) from fact_claim_header h where not exists (select 1 from dim_beneficiary b where b.beneficiary_id = h.beneficiary_id)") == [(0,)]
    sex = dict(rows(warehouse, "select beneficiary_id, sex from dim_beneficiary"))
    assert sex["B01"] == "Female" and sex["B02"] == "Male"
    prov = rows(warehouse, "select provider_type, count(*) from dim_provider group by 1 order by 1")
    assert prov == [("facility", 6), ("npi", 5)]  # F1 F2 F3 F5 F6 F9; four carrier NPIs plus the inpatient attending NPI


def test_diagnosis_dimension_normalizes_and_labels_every_code(warehouse) -> None:
    dx = {r[0]: r[1:] for r in rows(warehouse, "select diagnosis_code, format_valid, is_mapped, ccs_category_name from dim_diagnosis")}
    assert "25000" in dx and "250.00" not in dx and "V5789" in dx and "v5789" not in dx and "4280" in dx
    assert dx["ABC12"][:2] == (False, False) and dx["ABC12"][2] == "Invalid code format"
    assert dx["99999"][:2] == (True, False) and dx["99999"][2].startswith("Unmapped")
    assert dx["25000"][2] == "Diabetes mellitus without complication"


def test_member_month_eligibility(warehouse) -> None:
    got = dict(rows(warehouse, "select beneficiary_id || ':' || year, count(*) filter (where eligible) from mart_member_month group by 1"))
    assert got["B05:2008"] == 6 and got["B12:2008"] == 6 and got["B11:2009"] == 3 and got["B01:2010"] == 12
    assert rows(warehouse, "select count(*) from mart_member_month") == [(33 * 12,)]


def test_setting_dimension_is_the_only_source_of_settings(warehouse) -> None:
    assert rows(warehouse, "select care_setting from dim_care_setting order by sort_order") == [("inpatient",), ("outpatient",), ("carrier",)]


@pytest.mark.parametrize("table", ["mart_utilization_monthly", "mart_payment_monthly", "mart_provider_performance", "mart_quality_monitoring"])
def test_marts_are_populated(warehouse, table) -> None:
    assert rows(warehouse, f"select count(*) from {table}")[0][0] > 0


def test_padded_carrier_slots_are_not_service_lines(warehouse) -> None:
    """CMS fills unused carrier line slots with 0.00; counting them inflated lines about thirteen-fold."""
    assert rows(warehouse, "select count(*) from fact_claim_line where claim_key = 'carrier:B03:C03'") == [(1,)]
    assert rows(warehouse, "select count(*) from fact_claim_line where setting = 'carrier' and procedure_code is null "
                           "and coalesce(line_nch_pmt_amt, 0) = 0 and performing_npi is null") == [(0,)]
    assert rows(warehouse, "select count(*) from fact_claim_line where setting = 'carrier'") == [(14,)]
