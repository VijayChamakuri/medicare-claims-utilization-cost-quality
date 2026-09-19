# Interview guide

## The 90-second version

"I built an analytics pipeline on the CMS DE-SynPUF synthetic Medicare claims: about 5.6 million inpatient, outpatient and carrier claims. I loaded them into DuckDB, modeled a star schema in SQL, and defined utilization, payment and quality-monitoring metrics with a written dictionary. The part I care about is validation: I hand-derived a small fixture and assert every headline number exactly, I reconcile raw to staging to marts in SQL, and I recompute the KPIs independently in pandas without any shared SQL. On the full sample all 42 of those checks agree. The outputs are an Excel operations workbook with live formulas, an offline dashboard, an executive summary and a Tableau data package. Because the data is synthetic, every result is a pipeline demonstration, not a finding about real Medicare, and I say that on every artifact."

## What I would say when asked

**Is this real data?** No. CMS synthetic public use files, built for development and training. They cannot estimate real rates, provider performance, savings or prevalence.

**Did you find a real payment or quality problem?** No, and I would not claim one. I found data-model issues: claims can have two segments, so the claim key needs the beneficiary and claim ID; CMS pads unused carrier line slots with 0.00, which inflated line counts about thirteen-fold until I caught it in reconciliation; and the beneficiary summary payments do not tie to claim payments.

**How do you know your numbers are right?** Three layers: exact assertions against a fixture I derived by hand, SQL reconciliation from raw to marts, and an independent pandas recomputation from the raw CSVs. The tests also tamper with the warehouse and confirm the checks fail.

**Is the readmission rate a HEDIS measure?** No. It is a measure-inspired 30-day all-cause proxy with explicit index and exclusion logic and no planned-readmission or discharge-status data.

**Is the risk tier CMS-HCC?** No. It is a transparent points score from prior-year chronic condition flags, admissions and paid amount. It is a starting list for review, not a validated model.

**Do the provider flags identify fraud?** No. They are review prompts that compare a provider with same-type peers. On this data volume flags mostly track facility size.

**Did you build a Tableau dashboard?** No. The reproducible dashboard is an offline HTML page, plus an Excel workbook. I prepared a Tableau data and build package, but there is no workbook until it is built and checked in Tableau.

**Did you use Epic, Clarity or Caboodle?** No. This is public synthetic claims data.

**Is it HIPAA compliant?** Synthetic data avoids PHI exposure; that is not the same as compliance. The governance document lists what a real deployment would need.

**What would you do next with real data?** Add discharge status and planned-readmission flags, validate the tiers, apply cell suppression, and put the pipeline behind access controls and audit logging.
