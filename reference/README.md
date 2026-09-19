# Reference data

`ccs_icd9_dx_2015.csv`: ICD-9-CM diagnosis code to AHRQ CCS single-level category (15,072 codes, 283 categories).

- Source: AHRQ HCUP Clinical Classifications Software (CCS) for ICD-9-CM, 2015 release (the final ICD-9-CM version): https://hcup-us.ahrq.gov/toolssoftware/ccs/ccs.jsp
- Upstream archive: `Single_Level_CCS_2015.zip`, SHA-256 `a1e31709cc4fa7d67fc254a7421ec9686030098af9225d5f7ba73ae28deaa283` (pinned in `config/project.yml`, verified by `medicare-claims download`).
- Derived from `$dxref 2015.csv` (codes and categories) and `AppendixASingleDX.txt` (full category names). Codes are stored without dots, upper-case.
- Hash of this compact file: recorded in `data/data_manifest.json`.
