# Calculated fields and parameters

Use these exactly so results match `expected_kpis.csv`. All extracts already hold counts and amounts; rates are computed here so they re-aggregate correctly when filters change.

## Parameters

| Parameter | Type | Default | Use |
|---|---|---|---|
| `Top N` | Integer | 10 | Rows shown in the provider review list |
| `IQR multiplier` | Float, range 0.5 to 5, step 0.1 | 3.0 | Provider outlier fence: Q3 + multiplier x IQR |
| `Min claims` | Integer | 30 | Providers below this are never flagged |
| `Selected year` | Integer, list of 2008, 2009, 2010 | 2009 | Executive overview |

## Rates (aggregate, never average a row-level rate)

```text
Claims per 1,000 member-years   = SUM([claims]) / (SUM([member_months]) / 12) * 1000     // annual_by_setting uses member_years:
                                = SUM([claims]) / SUM([member_years]) * 1000
Admissions per 1,000 MY         = SUM([admissions]) / SUM([member_years]) * 1000
ED proxy per 1,000 MY           = SUM([ed_proxy_visits]) / SUM([member_years]) * 1000
Paid per claim                  = SUM([payment_amount]) / SUM([claims])
Paid per beneficiary            = SUM([payment_amount]) / SUM([beneficiaries])
Readmission proxy               = SUM([readmitted_stays]) / SUM([eligible_index_stays])
Share of paid amount            = SUM([payment_amount]) / TOTAL(SUM([payment_amount]))
Share of claims                 = SUM([claims]) / TOTAL(SUM([claims]))
```

In `annual_by_setting`, `beneficiaries` and `member_years` repeat on each setting row. Use `MAX([member_years])` (or `ATTR`) when summing across settings so the denominator is not counted three times:

```text
Claims per 1,000 MY (all settings) = SUM([claims]) / MAX([member_years]) * 1000
```

## Provider review (facility extract)

```text
Fence (payment per claim)  = [payment_per_claim_q3] + [IQR multiplier] * ([payment_per_claim_q3] - [payment_per_claim_q1])
Fence (claims)             = [claims_q3] + [IQR multiplier] * ([claims_q3] - [claims_q1])
Review flag (parameterized) =
    [peer_count] >= 20 AND [claims] >= [Min claims]
    AND ( ([payment_per_claim_q3] > [payment_per_claim_q1] AND [payment_per_claim] > [Fence (payment per claim)])
       OR ([claims_q3] > [claims_q1] AND [claims] > [Fence (claims)]) )
Review reason              = IF [payment_per_claim] > [Fence (payment per claim)] THEN "HIGH_PAYMENT_PER_CLAIM" END
```

A flag is a prompt to review, never a finding about fraud, quality or performance.

## Tooltip text (numerator, denominator, caveat)

```text
<Rate name>: <rate>
Numerator: <SUM numerator> | Denominator: <SUM denominator>
Synthetic CMS claims. Proxy measure, not certified.
```
