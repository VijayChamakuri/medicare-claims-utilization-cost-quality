"""One command per stage on the fixture profile, through the same CLI a user runs."""

import shutil

import pandas as pd
import pytest

from medicare_claims import reports
from medicare_claims.cli import main
from tests.conftest import REPO


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    root = tmp_path_factory.mktemp("proj")
    for folder in ("sql", "config", "reference", "dashboard", "tableau", "docs"):
        shutil.copytree(REPO / folder, root / folder, dirs_exist_ok=True, ignore=shutil.ignore_patterns("data", "screenshots", "index.html"))
    shutil.copytree(REPO / "tests" / "fixtures" / "raw", root / "tests" / "fixtures" / "raw")
    # keep the review thresholds used in the hand derivation
    cfg = root / "config" / "project.yml"
    cfg.write_text(cfg.read_text().replace("peer_min_providers: 20", "peer_min_providers: 4").replace("min_claims: 30", "min_claims: 1")
                   .replace("iqr_multiplier: 3.0", "iqr_multiplier: 1.5"))
    (root / "build" / "fixture").mkdir(parents=True)
    (root / "build" / "fixture" / "README.md").write_text("<!-- BEGIN generated:results -->\nold\n<!-- END generated:results -->\n"
                                    "<!-- BEGIN generated:kpis -->\nold\n<!-- END generated:kpis -->\n")
    base = ["--root", str(root), "--profile", "fixture"]
    for command in (["build"], ["validate"], ["export"], ["excel"], ["reports"], ["tableau"], ["dashboard"], ["readme"]):
        assert main(base + command) == 0
    return root, base


def test_every_stage_wrote_its_artifact(project) -> None:
    root, _ = project
    out = root / "build" / "fixture"
    for path in ("exports/kpi_annual.csv", "excel/claims_operations_review.xlsx", "reports/executive_summary.md",
                 "reports/data_quality_report.md", "reports/provider_action_list.csv", "reports/headline_kpis.json",
                 "tableau/data/annual_by_setting.csv", "tableau/expected_kpis.csv", "tableau/field_dictionary.md", "dashboard/index.html",
                 "docs/table_inventory.md", "docs/metric_dictionary.md"):
        assert (out / path).stat().st_size > 100, path
    assert not (root / "reports").exists() and not (root / "exports").exists()  # fixture output stays in build/fixture
    assert (root / "data" / "warehouse" / "fixture.duckdb").exists()


def test_exports_are_aggregates_only_and_match_hand_values(project) -> None:
    root, _ = project
    annual = pd.read_csv(root / "build" / "fixture" / "exports" / "kpi_annual.csv").set_index("year")
    assert annual.loc[2009, "claims"] == 14 and annual.loc[2009, "payment_total"] == pytest.approx(81385.0)
    assert annual.loc[2008, "readmission_eligible_index"] == 7
    for csv in (root / "build" / "fixture" / "exports").glob("*.csv"):
        assert "beneficiary_id" not in pd.read_csv(csv, nrows=0).columns, csv.name


def test_tableau_expected_kpis_match_the_hand_derivation(project) -> None:
    root, _ = project
    exp = pd.read_csv(root / "build" / "fixture" / "tableau" / "expected_kpis.csv")
    got = exp[(exp.year == 2009) & (exp.field == "payment_total")]["expected_value"].iloc[0]
    assert got == pytest.approx(81385.0)
    assert set(exp.field) >= {"claims", "readmission_rate", "top_5pct_payment_share"}


def test_executive_summary_states_the_synthetic_caveat_and_no_savings(project) -> None:
    root, _ = project
    text = (root / "build" / "fixture" / "reports" / "executive_summary.md").read_text()
    assert "not real patient or provider performance" in text and "No savings, impact or outcome is claimed" in text
    action = pd.read_csv(root / "build" / "fixture" / "reports" / "provider_action_list.csv")
    assert set(action["provider_id"]) == {"F9", "N2"} and action["note"].str.contains("SYNTHETIC").all()


def test_provider_action_list_carries_reason_codes(project) -> None:
    root, _ = project
    action = pd.read_csv(root / "build" / "fixture" / "reports" / "provider_action_list.csv").set_index("provider_id")
    assert action.loc["F9", "reason_codes"] == "HIGH_PAYMENT_PER_CLAIM"
    assert action.loc["N2", "reason_codes"] == "HIGH_CLAIM_VOLUME"


def test_readme_blocks_are_generated_and_drift_is_detected(project, capsys) -> None:
    root, base = project
    assert main(base + ["readme", "--check"]) == 0
    from medicare_claims.config import load_config

    config = load_config(root=root, profile="fixture")
    assert reports.check_readme(config) == []
    readme = root / "build" / "fixture" / "README.md"
    readme.write_text(readme.read_text().replace("Payment is concentrated", "Payment is diffuse"))
    assert len(reports.check_readme(config)) == 1
    with pytest.raises(SystemExit):
        main(base + ["readme", "--check"])
    assert "out of sync" in capsys.readouterr().out
