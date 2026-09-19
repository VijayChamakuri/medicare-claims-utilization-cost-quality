import json
import re

import pytest

from medicare_claims.dashboard import build_dashboard, build_payload
from medicare_claims.export import datasets


@pytest.fixture(scope="module")
def html(warehouse, config, tmp_path_factory):
    path = build_dashboard(warehouse, config, tmp_path_factory.mktemp("dash") / "index.html")
    return path.read_text(encoding="utf-8")


def test_dashboard_is_one_offline_file(html) -> None:
    for placeholder in ("/*STYLE*/", "/*APP*/", "/*DATA*/"):
        assert placeholder not in html
    assert html.count("<script") == 2
    assert re.search(r"(src|href)=\"https?://", html) is None
    assert re.search(r"fetch\(|XMLHttpRequest|import\(", html) is None


def test_synthetic_banner_and_the_five_pages(html) -> None:
    assert "CMS synthetic claims - not real patient or provider performance." in html
    for page in ("Executive Overview", "Utilization & Payment", "Provider Operations", "Quality & Cohorts", "Data Quality & Definitions"):
        assert page in html


def test_payload_numbers_come_from_the_marts(warehouse, config) -> None:
    payload = build_payload(warehouse, config)
    annual = {r["year"]: r for r in payload["kpi_annual"]}
    assert annual[2008]["claims"] == 16 and annual[2009]["payment_total"] == pytest.approx(81385.0)
    assert annual[2008]["admissions"] == 8
    tiers = {(r["year"], r["utilization_risk_tier"]): r["beneficiaries"] for r in payload["risk_tier_summary"]}
    assert tiers[(2009, "high")] == 3 and tiers[(2010, "high")] == 4
    assert payload["independent"] and all(r["passed"] for r in payload["independent"])
    json.dumps(payload, allow_nan=False)  # JSON-safe for embedding


def test_payload_matches_the_export_datasets(warehouse, config) -> None:
    ds = datasets(warehouse, config)
    payload = build_payload(warehouse, config)
    assert len(payload["monthly_payments"]) == len(ds["monthly_payments"])
    assert len(payload["condition_summary"]) == len(ds["condition_summary"])
    assert {r["provider_type"] for r in payload["provider_review_facility"]} <= {"facility_inpatient", "facility_outpatient"}


def test_no_beneficiary_identifiers_in_the_payload(warehouse, config) -> None:
    ids = {r[0] for r in warehouse.execute("select beneficiary_id from dim_beneficiary").fetchall()}
    text = json.dumps(build_payload(warehouse, config))
    assert not any(f'"{i}"' in text for i in ids)


def test_provider_page_defaults_and_disclaimer(html) -> None:
    assert "iqr: 3.0" in html and "Review flags only" in html and "not evidence of fraud" in html
