"""The committed README: numbers only in generated blocks, and the blocks match reports/headline_kpis.json."""

import re

import pytest

from medicare_claims.config import load_config
from medicare_claims.reports import BLOCKS, MARK, check_readme
from tests.conftest import REPO

README = (REPO / "README.md").read_text(encoding="utf-8")


def test_every_generated_block_is_present() -> None:
    assert set(BLOCKS) <= {m.group("name") for m in MARK.finditer(README)}


def test_no_statistics_are_hard_coded_outside_generated_blocks() -> None:
    prose = MARK.sub("", README)
    prose = re.sub(r"```.*?```", "", prose, flags=re.S)
    prose = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", prose)
    prose = re.sub(r"\]\([^)]*\)", "]", prose)
    prose = prose.replace("5 percent", "").replace("5%", "")  # the DE-SynPUF sampling fraction is a fact of the source
    assert re.findall(r"\$\d[\d,.]*\s?[MBK]\b", prose) == []
    assert re.findall(r"\b\d{1,3}\.\d\s?%", prose) == []


@pytest.mark.skipif(not (REPO / "reports" / "headline_kpis.json").exists(), reason="reports not generated")
def test_generated_blocks_match_the_committed_headline_numbers() -> None:
    assert check_readme(load_config(root=REPO)) == []
