# Code mapping and limits

> CMS synthetic claims - not real patient or provider performance.

## ICD-9 era

2008 to 2010 claims use **ICD-9-CM**, not ICD-10. Nothing here applies ICD-10 logic.

## Diagnosis grouping

Condition groups use the **AHRQ HCUP Clinical Classifications Software (CCS) for ICD-9-CM, single level, 2015**, the final ICD-9-CM release ([source](https://hcup-us.ahrq.gov/toolssoftware/ccs/ccs.jsp)).

- Source zip `Single_Level_CCS_2015.zip`, SHA-256 `a1e31709cc4fa7d67fc254a7421ec9686030098af9225d5f7ba73ae28deaa283`, pinned in `config/project.yml` and checked on download.
- The compact mapping `reference/ccs_icd9_dx_2015.csv` is derived from `$dxref 2015.csv` and the category names in `AppendixASingleDX.txt`. Its hash is recorded in `data/data_manifest.json`.
- Codes are normalized (trim, drop dots and spaces, upper-case) before joining. Raw text stays unchanged in the `raw_*` tables.
- Categories 2601 to 2621 (E-code categories) have only abbreviated names in the source and use them.

Handling:

| Case | Result |
|---|---|
| Well-formed and in CCS | Category number and name |
| Well-formed but not in CCS 2015 (for example `99999`) | "Unmapped (valid format, not in CCS 2015)" |
| Malformed (for example `ABC12`) | "Invalid code format" |
| Missing | "Missing primary diagnosis" |
| Lower-case, dotted or padded (`v5789`, `250.00`, `4280 `) | Normalized, then mapped |

Nothing is inferred beyond the CCS definition, and mappings are never guessed for unmapped codes.

## Procedure grouping

HCPCS codes are grouped by **CPT section ranges** (evaluation and management 99201 to 99499, anesthesia 00100 to 01999, surgery 10021 to 69990, radiology 70010 to 79999, pathology and laboratory 80047 to 89398, medicine 90281 to 99199 and 99500 to 99607) and the **HCPCS Level II first letter** families in CMS "HCPCS Level II Coding Procedures". Only the section structure is used; descriptors are not reproduced. This is a coarse grouping, not BETOS. ICD-9 procedure codes are not loaded.

## ED visit proxy

Outpatient claims carrying **HCPCS 99281 to 99285** (emergency department evaluation and management). DE-SynPUF has no revenue center codes and no place of service, so this is a code-based proxy and will miss ED visits billed without these codes and count other uses of them. The code list is in `config/project.yml` and tested.

## Not implemented, deliberately

- **Avoidable-utilization proxy.** It needs a cited ambulatory-care-sensitive definition with code lists; none is included.
- **Follow-up or repeat-visit proxy.** No cited definition is applied to this data.
- **CMS-HCC, RAF, HEDIS.** The utilization risk tier is a transparent portfolio stratification and does not use any official model, coefficients or hierarchies.
