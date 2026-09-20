"""The Tableau package: extracts, packaged workbook, manifest, expected KPIs and the Hyper tie-out."""

import re
import xml.dom.minidom
import zipfile

import pandas as pd
import pytest
import yaml

from medicare_claims.metrics import compute_kpis
from medicare_claims.tableau import DISALLOWED, WORKBOOK_FILE, build_package, extracts
from tests.conftest import REPO


@pytest.fixture(scope="module")
def package(warehouse, config, tmp_path_factory):
    return build_package(warehouse, config, tmp_path_factory.mktemp("tableau"))


@pytest.fixture(scope="module")
def twb(package) -> str:
    with zipfile.ZipFile(package / "workbook" / WORKBOOK_FILE) as z:
        name = next(n for n in z.namelist() if n.endswith(".twb"))
        return z.read(name).decode("utf-8")


def test_workbook_is_well_formed_xml_with_five_dashboards(twb) -> None:
    doc = xml.dom.minidom.parseString(twb)
    dashboards = [d.getAttribute("name") for d in doc.getElementsByTagName("dashboard")]
    assert dashboards == ["Executive Overview", "Utilization & Payment", "Provider Operations", "Quality & Cohorts",
                          "Data Quality & Definitions"]
    sheets = [w.getAttribute("name") for w in doc.getElementsByTagName("worksheet")]
    assert len(sheets) == len(set(sheets))


def test_manifest_references_only_what_the_workbook_contains(package, twb) -> None:
    manifest = yaml.safe_load((package / "workbook_manifest.yml").read_text())
    with zipfile.ZipFile(package / "workbook" / WORKBOOK_FILE) as z:
        members = set(z.namelist())
    for ds in manifest["data_sources"]:
        assert ds["extract"] in members, ds
        assert f"dbname={xml_attr(ds['extract'])}" in twb
        assert (package / "data" / ds["csv"].split("/")[-1]).exists()
    for sheet in manifest["worksheets"]:
        assert f"<worksheet name={xml_attr(sheet)}>" in twb, sheet
    for dash in manifest["dashboards"]:
        for sheet in dash["worksheets"]:
            assert sheet in manifest["worksheets"], sheet
    for action in manifest["actions"]:
        assert action["source"] in manifest["worksheets"] and set(action["targets"]) <= set(manifest["worksheets"])


def xml_attr(value: str) -> str:
    from xml.sax.saxutils import quoteattr

    return quoteattr(value)


def test_manifest_check_fails_when_a_sheet_is_missing(package, twb) -> None:
    manifest = yaml.safe_load((package / "workbook_manifest.yml").read_text())
    manifest["worksheets"].append("Sheet that does not exist")
    assert not all(f"<worksheet name={xml_attr(s)}>" in twb for s in manifest["worksheets"])


def test_every_dashboard_carries_the_synthetic_notice_source_and_refresh(twb) -> None:
    for block in re.findall(r"<dashboard name=.*?</dashboard>", twb, flags=re.S):
        assert "not real patient or provider performance" in block
        assert "Source: CMS 2008-2010 DE-SynPUF sample 1" in block
        assert "Fixture data" in block or "Data retrieved" in block
        assert "maxwidth='1366'" in block and "maxheight='768'" in block


def test_proxy_and_review_disclaimers_are_on_their_dashboards(twb) -> None:
    quality = re.search(r'<dashboard name="Quality &amp; Cohorts">.*?</dashboard>', twb, flags=re.S).group(0)
    assert "Not HEDIS, not CMS-HCC, not a clinical outcome measure" in quality
    provider = re.search(r'<dashboard name="Provider Operations">.*?</dashboard>', twb, flags=re.S).group(0)
    assert "not a finding about fraud or quality" in provider


def test_no_published_extract_contains_a_beneficiary_or_claim_identifier(warehouse, config, package) -> None:
    for path in (package / "data").glob("*.csv"):
        columns = {c.lower() for c in pd.read_csv(path, nrows=1).columns}
        assert not (columns & DISALLOWED), path.name


def test_extract_guard_rejects_a_beneficiary_identifier(warehouse, config, monkeypatch) -> None:
    import medicare_claims.tableau as tab

    original = tab.datasets

    def leaky(con, cfg):
        out = original(con, cfg)
        out["kpi_annual"] = out["kpi_annual"].assign(beneficiary_id="X")
        return out

    monkeypatch.setattr(tab, "datasets", leaky)
    with pytest.raises(ValueError, match="beneficiary"):
        extracts(warehouse, config)


def test_expected_kpis_tie_to_the_marts(warehouse, package) -> None:
    kpis = compute_kpis(warehouse)
    expected = pd.read_csv(package / "expected_kpis.csv")
    paid = expected[expected["field"] == "payment_total"].set_index("year")["expected_value"]
    for year, value in kpis["payment_total"].items():
        assert paid.loc[int(year)] == pytest.approx(value, abs=0.005)


def test_hyper_tieout_passes_for_every_kpi(package) -> None:
    evidence = pd.read_csv(package / "validation_evidence.csv")
    assert len(evidence) == len(pd.read_csv(package / "expected_kpis.csv"))
    assert evidence["passed"].all(), evidence[~evidence["passed"]]


def test_tieout_detects_drift(package) -> None:
    from medicare_claims.tableau import hyper_tieout

    expected = pd.read_csv(package / "expected_kpis.csv")
    expected.loc[expected.index[0], "expected_value"] += 1
    result = hyper_tieout(package / "workbook" / WORKBOOK_FILE, expected)
    assert not result["passed"].all()


def test_payment_metrics_are_never_called_cost(twb) -> None:
    for text in re.findall(r'(?:caption|name)="([^"]*)"', twb) + re.findall(r"<run[^>]*>([^<]*)</run>", twb):
        if re.search(r"\bcost\b", text, flags=re.I):
            assert re.search(r"not cost|never .*cost", text, flags=re.I), text


def test_committed_package_matches_the_contract() -> None:
    manifest = yaml.safe_load((REPO / "tableau" / "workbook_manifest.yml").read_text())
    assert manifest["file"] == f"tableau/workbook/{WORKBOOK_FILE}"
    assert (REPO / manifest["file"]).exists()
    evidence = pd.read_csv(REPO / "tableau" / "validation_evidence.csv")
    assert evidence["passed"].all()
