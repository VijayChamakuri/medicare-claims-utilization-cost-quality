# Hand-calculated fixture

Twelve synthetic beneficiaries, three years, three settings. `expected_kpis.json` holds every value asserted in `tests/test_fixture_kpis.py`, derived by hand from the CSVs in `raw/` and never from pipeline output. Regenerate the CSVs with `python tests/fixtures/build_fixture.py`.

## Rules used in the derivation

- **Claim** = beneficiary + `CLM_ID` within a setting. `SEGMENT` rows are merged (payments add, dates from the segment that has them). An exact duplicate row is dropped.
- **Analytic claim** = valid dates (`from <= thru`, and for inpatient `admit <= discharge`) and `from` date inside 2008-01-01..2010-12-31. Others stay in the facts with a flag and are reported as exclusions.
- **Year** = year of the claim `from` date (inpatient admission year for admissions).
- **Member months** for a beneficiary-year = `min(BENE_HI_CVRAGE_TOT_MONS, months alive in the year)`, placed from January.
- **Admission** = one continuous inpatient stay. A claim whose admit date is on or before the discharge date of the beneficiary's previous stay continues that stay.
- **Readmission proxy**: index stay is eligible if dates are valid, the beneficiary did not die between admit and discharge, and discharge is on or before 2010-12-01 (30 days before the study end). Readmitted if another stay begins after the index discharge date and within 30 days.
- **ED proxy** = outpatient claim carrying HCPCS 99281 to 99285.
- **Top 5 percent** = `ceil(0.05 * beneficiaries)` highest payers in the year (one person for every year here).

## Member months

| Year | Beneficiary rows | Member months |
|---|---|---|
| 2008 | 12 | 10 people x 12 = 120, B05 has 6, B12 has 6 (death 2008-06-15, six months alive) = 132 |
| 2009 | 11 | 10 x 12 = 120, B11 has 3 (death 2009-03-10) = 123 |
| 2010 | 10 | 10 x 12 = 120 |

## Inpatient stays

| Stay | Beneficiary | Admit to discharge | LOS | Payment | Note |
|---|---|---|---|---|---|
| I01 | B01 | 2008-02-01 to 02-05 | 4 | 10,000 | index, readmitted by I02 (15 days) |
| I02 | B01 | 2008-02-20 to 02-25 | 5 | 8,000 | 45 days to I03, so not readmitted |
| I03 | B01 | 2008-04-10 to 04-12 | 2 | 5,000 | |
| I04 + I05 | B02 | 2008-05-01 to 05-10 | 9 | 12,000 + 9,000 | I05 admits on I04's discharge day: one continuous stay |
| I06 (twice) + I07 | B03 | 2008-11-15 to 11-20; 12-10 to 12-15 | 5, 5 | 7,500; 6,000 | duplicate row dropped; I06 readmitted by I07 (20 days) |
| I17 | B05 | 2008-03-15 to 03-18 | 3 | 3,500 | primary dx 99999 is well-formed but unmapped (condition ID `unmapped_valid`) |
| I11 | B12 | 2008-06-10 to 06-15 | 5 | 15,000 | died 2008-06-15: excluded from the readmission index |
| I08, I09 | B04 | 2009-01-10 to 01-13; 02-20 to 02-21 | 3, 1 | 4,000; 500 | 38 days apart, so not a readmission |
| I10 | B06 | 2009-06-01 to 06-03 | 2 | -2,000 | payment adjustment, no primary dx |
| I12 | B11 | 2009-02-25 to 03-01 | 4 | 9,500 | lower-case `v5789` normalizes to V5789 |
| I15 (2 segments) | B09 | 2009-09-01 to 09-04 | 3 | 6,000 + 2,000 | one claim, malformed dx `ABC12` |
| I18 | B10 | 2009-10-05 to 10-08 | 3 | 60,000 | high-payment provider F9 |
| I13 | B07 | 2010-12-10 to 12-15 | 5 | 6,500 | discharge after 2010-12-01: no follow-up window |
| I14 | B08 | admit 2009-07-10, discharge 2009-07-05 | n/a | 3,000 | impossible dates: excluded |
| I16 | B10 | 2007-12-20 to 12-30 | n/a | 4,500 | before the study window: excluded |

Admissions: 2008 = 3 (B01) + 1 (B02) + 2 (B03) + 1 (B05) + 1 (B12) = 8; 2009 = 2 + 1 + 1 + 1 + 1 = 6; 2010 = 1. Total 15.
Inpatient payment: 2008 = 10+8+5+12+9+7.5+6+15+3.5 = 76.0 thousand; 2009 = 4 + 0.5 - 2 + 9.5 + 8 + 60 = 80.0 thousand; 2010 = 6.5 thousand.
Length of stay: 2008 = 4+5+2+9+5+5+3+5 = 38 over 8; 2009 = 3+1+2+4+3+3 = 16 over 6; 2010 = 5 over 1.

## Readmission proxy

2008 index stays: I01 (readmitted), I02, I03, B02 stay, I06 (readmitted), I07, I17 = 7 eligible, 2 readmitted; I11 excluded (died). 2009: I08, I09, I10, I12, I15, I18 = 6 eligible, 0 readmitted. 2010: I13 excluded (no follow-up window). Total 13 eligible, 2 readmitted (15.4%).

## Outpatient and carrier

Outpatient analytic claims: 2008 = O01 600, O02 400, O05 150, O10 250 (four claims, 1,400); 2009 = O03 350, O04 200, O07 -50, O09 500, O12 (100 + 25 second segment) = five claims, 1,125; 2010 = O06 300, O08 0 = two claims, 300. O11 (2007) is excluded. ED proxy: O01, O02 (2008); O03, O09 (2009).
Carrier claims: 2008 = C01 (60+15+5 = 80, 3 lines), C02 (100+40 = 140, 2 lines), C05 (25, 1 line) = 245; 2009 = C03 90 (1 line; its second slot is a padded 0.00 entry with no code or NPI and is not a line), C04 (20+30+40+10 = 100, 4), C07 70 (1) = 260; 2010 = C06 (55+45 = 100, 2 lines).

## Concentration and risk tiers

Top payer: 2008 B01 = 23,000 (IP) + 600 + 80 = 23,680 of 77,645; 2009 B10 = 60,000 + 70 = 60,070 of 81,385; 2010 B07 = 6,500 of 6,900.

Risk tier score = comorbidity points (prior-year chronic flags: 0-1 -> 0, 2-3 -> 1, 4+ -> 2) + prior-year admissions points (0 -> 0, 1 -> 2, 2+ -> 3) + prior-year paid points (< 1,000 -> 0, 1,000 to < 5,000 -> 1, 5,000+ -> 2). Score 0-1 low, 2-3 medium, 4+ high. 2008 has no prior year, so it is not assessed.
2009 (prior = 2008): B01 = 1 + 3 + 2 = 6 high; B02 = 0 + 2 + 2 = 4 high; B03 = 0 + 3 + 2 = 5 high; B05 = 0 + 2 + 1 = 3 medium; the other seven score 0 low.
2010 (prior = 2009): B04 = 1 (COPD, CHF) + 3 + 1 (4,800) = 5 high; B06 = 2 (four flags) + 2 + 0 (-2,000) = 4 high; B09 = 0 + 2 + 2 = 4 high; B10 = 0 + 2 + 2 = 4 high; the other six low.

## Provider review flags (fixture thresholds: at least 4 peers, at least 1 claim, IQR multiplier 1.5; facilities are compared within their setting)

Inpatient facilities (F1, F2, F3, F9) and outpatient facilities (F5, F6) are separate peer groups. 2009 inpatient payment per claim: F2 -2,000; F3 2,250; F1 8,750; F9 60,000. Sorted, Q1 sits at position 0.75 = -2,000 + 0.75 x 4,250 = 1,187.5 and Q3 at position 2.25 = 8,750 + 0.25 x 51,250 = 21,562.5, so IQR = 20,375 and the fence is 21,562.5 + 1.5 x 20,375 = 52,125. Only F9 (60,000) is flagged. 2008 has three inpatient facilities and 2009 has two outpatient facilities (fewer than four peers), and 2010 has one of each, so nothing else is flagged.

Professional (carrier line NPI) peers use distinct claims per NPI. 2008 has four NPIs: N1 = 1 claim (C01), N2 = 2 claims (C01, C02), N3 = 1 (C02), N4 = 1 (C05). Sorted claim counts 1, 1, 1, 2 give Q1 = 1, Q3 = 1 + 0.25 x (2 - 1) = 1.25, IQR = 0.25, fence = 1.25 + 0.375 = 1.625, so N2 is flagged HIGH_CLAIM_VOLUME. Payment per claim is 75, 52.5, 40, 25 (fence 90.9), so nothing is flagged for payment. 2009 has three NPIs (fewer than four peers) and 2010 has one, so neither year flags.
