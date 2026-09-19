"""Code normalization and cited groupings.

The SQL macros in ``sql/01_staging.sql`` implement the same rules; ``tests/test_codes.py`` checks
the two agree. 2008-2010 claims use ICD-9-CM, and CCS 2015 is the final ICD-9-CM release.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ICD9_PATTERNS = (
    re.compile(r"[0-9]{3}[0-9]{0,2}"),
    re.compile(r"V[0-9]{2}[0-9]{0,2}"),
    re.compile(r"E[0-9]{3}[0-9]?"),
)
HCPCS_PATTERN = re.compile(r"[0-9A-Z][0-9]{3}[0-9A-Z]")

# HCPCS Level II first-letter families, as described in CMS "HCPCS Level II Coding Procedures".
LEVEL2_GROUPS = {
    "A": "Transportation, medical and surgical supplies",
    "B": "Enteral and parenteral therapy",
    "C": "Outpatient PPS temporary codes",
    "D": "Dental",
    "E": "Durable medical equipment",
    "G": "Temporary procedures and professional services",
    "H": "Behavioral health and substance abuse",
    "J": "Drugs administered other than oral",
    "K": "Temporary durable medical equipment",
    "L": "Orthotic and prosthetic procedures",
    "M": "Other medical services",
    "P": "Pathology and laboratory",
    "Q": "Temporary codes",
    "R": "Diagnostic radiology",
    "S": "Private payer temporary codes",
    "T": "State Medicaid temporary codes",
    "V": "Vision and hearing",
}
# CPT section ranges (structure only, no descriptors).
CPT_SECTIONS = (
    (99201, 99499, "Evaluation and management"),
    (100, 1999, "Anesthesia"),
    (10021, 69990, "Surgery"),
    (70010, 79999, "Radiology"),
    (80047, 89398, "Pathology and laboratory"),
    (90281, 99199, "Medicine"),
    (99500, 99607, "Medicine"),
)


def normalize_code(raw: str | None) -> str | None:
    """Trim, drop dots and spaces, upper-case. Empty becomes None."""
    if raw is None:
        return None
    value = raw.strip().replace(".", "").replace(" ", "").upper()
    return value or None


def is_valid_icd9(code: str | None) -> bool:
    return code is not None and any(p.fullmatch(code) for p in ICD9_PATTERNS)


def is_valid_hcpcs(code: str | None) -> bool:
    return code is not None and HCPCS_PATTERN.fullmatch(code) is not None


def hcpcs_group(code: str | None) -> str:
    if code is None or not is_valid_hcpcs(code):
        return "Invalid or missing"
    if code[-1] in "FT" and code[:4].isdigit():
        return "CPT category II and III"
    if code[0].isdigit():
        number = int(code[:5]) if code.isdigit() else None
        if number is None:
            return "Unclassified"
        for low, high, name in CPT_SECTIONS:
            if low <= number <= high:
                return name
        return "Unclassified"
    return LEVEL2_GROUPS.get(code[0], "Unclassified")


def load_ccs(path: Path) -> dict[str, tuple[int, str]]:
    """AHRQ CCS single-level ICD-9-CM diagnosis map: normalized code to (category, name)."""
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["icd9_code"]: (int(row["ccs_category"]), row["ccs_category_name"])
                for row in csv.DictReader(handle)}
