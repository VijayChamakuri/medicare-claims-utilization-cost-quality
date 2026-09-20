"""The canonical KPI contract: required fields, unique names, real source models, headline coverage."""

import re

import yaml

from medicare_claims.export import metric_dictionary
from medicare_claims.reports import metric_dictionary_doc
from tests.conftest import REPO

REQUIRED = ["id", "name", "version", "business_question", "owner_role", "description", "grain", "source_model",
            "calculation", "numerator", "denominator", "inclusions", "exclusions", "valid_dimensions", "time_basis",
            "refresh_expectation", "quality_checks", "known_limits"]
CONTRACT = yaml.safe_load((REPO / "config" / "metric_dictionary.yml").read_text())
MODELS = {p.stem for p in (REPO / "dbt" / "models").rglob("*.sql")}


def test_every_metric_has_every_required_field() -> None:
    for m in CONTRACT["metrics"]:
        missing = [f for f in REQUIRED if m.get(f) in (None, "", [])]
        assert not missing, (m.get("name"), missing)


def test_names_and_ids_are_unique() -> None:
    ids = [m["id"] for m in CONTRACT["metrics"]]
    names = [m["name"] for m in CONTRACT["metrics"]]
    assert len(ids) == len(set(ids)) and len(names) == len(set(names))


def test_duplicate_names_would_be_caught() -> None:
    metrics = CONTRACT["metrics"] + [dict(CONTRACT["metrics"][0])]
    assert len({m["name"] for m in metrics}) < len(metrics)


def test_source_models_exist_in_the_dbt_project() -> None:
    for m in CONTRACT["metrics"]:
        assert m["source_model"] in MODELS, (m["id"], m["source_model"])


def test_headline_kpis_are_all_in_the_contract() -> None:
    headline = {m["id"] for m in CONTRACT["metrics"] if m["headline"]}
    assert {"beneficiaries", "claims", "paid_amount", "paid_per_beneficiary", "admissions_per_1000",
            "ed_proxy_per_1000", "readmission_proxy", "top5_payment_share"} <= headline


def test_generated_dictionary_uses_every_definition_and_version(config) -> None:
    doc = metric_dictionary_doc(config)
    for m in CONTRACT["metrics"]:
        assert m["description"] in doc and f"`{m['id']}` v{m['version']}" in doc
    assert (REPO / "docs" / "metric_dictionary.md").read_text() == doc


def test_excel_and_tableau_read_the_same_contract(config) -> None:
    frame = metric_dictionary(config)
    assert list(frame["id"]) == [m["id"] for m in CONTRACT["metrics"]]
    assert (frame["contract_version"] == CONTRACT["contract_version"]).all()


def test_payment_metrics_are_described_as_payment_not_cost() -> None:
    for m in CONTRACT["metrics"]:
        text = " ".join(str(m[f]) for f in ("name", "description", "calculation", "unit"))
        assert not re.search(r"\bcosts?\b", text, flags=re.I), m["id"]
