# Data

Raw CMS files are not committed. Run `medicare-claims download` to fetch them into `data/raw/`; it verifies each file and writes [`data_manifest.json`](data_manifest.json).

`data_manifest.json` records, for every file: source URL, retrieval date, byte size, SHA-256 and archive members. It also records the codebook and FAQ PDFs (their hashes identify the documentation version), the AHRQ CCS reference, and the overview and collection pages.

Sources (official):

- [CMS DE-SynPUF overview](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-claims-synthetic-public-use-files/cms-2008-2010-data-entrepreneurs-synthetic-public-use-file-de-synpuf)
- [Data.CMS.gov collection](https://data.cms.gov/collection/synthetic-medicare-enrollment-fee-for-service-claims-and-prescription-drug-event)
- [Codebook](https://www.cms.gov/files/document/de-10-codebook.pdf-0) and [FAQ](https://www.cms.gov/files/document/de-10-frequently-asked-questions.pdf)

CMS links the 2010 beneficiary file for sample 1 as `de1_0_2010_beneficiary_summary_file_sample_20.zip`. The CSV inside is `DE1_0_2010_Beneficiary_Summary_File_Sample_1.csv`, and all of its beneficiary IDs appear in the 2008 sample 1 file.

`data/sample/` is reserved for a small documented extract; the tests use the hand-built fixture in `tests/fixtures/` instead.
