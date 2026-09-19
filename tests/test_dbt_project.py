"""The dbt layer stays generated from sql/ and keeps its vars in step with config/project.yml."""

import subprocess
import sys

import yaml

from medicare_claims.config import load_config
from medicare_claims.model import sql_params
from tests.conftest import REPO


def test_generated_models_match_sql() -> None:
    result = subprocess.run([sys.executable, "scripts/gen_dbt_models.py", "--check"], cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_every_legacy_table_has_a_dbt_model_and_a_grain_test() -> None:
    models = {p.stem for p in (REPO / "dbt" / "models").rglob("*.sql")}
    schema = yaml.safe_load((REPO / "dbt" / "models" / "schema.yml").read_text())
    tested = {m["name"] for m in schema["models"]}
    inventory = (REPO / "docs" / "table_inventory.md").read_text()
    for line in inventory.splitlines():
        if line.startswith("| `"):
            table = line.split("`")[1]
            assert table in models, table
            assert table in tested, table


def test_dbt_vars_default_to_the_sample_profile() -> None:
    project = yaml.safe_load((REPO / "dbt" / "dbt_project.yml").read_text())
    assert project["vars"] == sql_params(load_config(root=REPO))


def test_blocking_reconciliation_categories_are_singular_tests() -> None:
    tests = {p.stem for p in (REPO / "dbt" / "tests").glob("*.sql")}
    for category in ("dates", "eligibility", "fact_to_fact", "fact_to_mart", "foreign_keys", "header_line", "keys",
                     "nulls", "raw_to_staging", "staging_to_fact"):
        assert f"assert_reconciliation_{category}" in tests
