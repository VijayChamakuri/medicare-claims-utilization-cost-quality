-- Policy (docs/code_mapping_and_limits.md): negative CMS payment amounts are adjustments. They stay in totals,
-- are counted per month, and never have a null amount. The monthly mart's negative-claim count must match.
with header as (
    select month_start, setting, count(*) filter (where payment_amount < 0) as negative_claims
    from {{ ref('fact_claim_header') }} where is_analytic group by 1, 2
)
select h.month_start, h.setting, h.negative_claims, m.negative_payment_claims
from header h join {{ ref('mart_payment_monthly') }} m using (month_start, setting)
where h.negative_claims <> m.negative_payment_claims
union all
select month_start, setting, null, null from {{ ref('fact_claim_header') }}
where is_analytic and payment_amount is null
