-- 07 Provider performance and review flags. Flags mean "review", never fraud or poor quality.
-- Parameters: $peer_min_providers, $min_claims, $iqr_multiplier.

create or replace table mart_provider_performance as
with facility as (
    -- Peers are compared within the same setting: inpatient hospitals and outpatient facilities have
    -- very different payment per claim, so a pooled peer group would flag most of one type.
    select case setting when 'inpatient' then 'facility_inpatient' else 'facility_outpatient' end as provider_type,
           facility_id as provider_id, claim_year as year,
           count(*) as claims, count(distinct beneficiary_id) as beneficiaries,
           sum(payment_amount)::decimal(16, 2) as payment_amount
    from fact_claim_header
    where is_analytic and setting in ('inpatient', 'outpatient') and facility_id is not null
    group by setting, facility_id, claim_year
), professional as (
    select 'npi' as provider_type, l.performing_npi as provider_id, h.claim_year as year,
           count(distinct l.claim_key) as claims, count(distinct l.beneficiary_id) as beneficiaries,
           sum(l.line_nch_pmt_amt)::decimal(16, 2) as payment_amount
    from fact_claim_line l join fact_claim_header h using (claim_key)
    where h.is_analytic and l.setting = 'carrier' and l.performing_npi is not null
    group by 1, 2, 3
), unioned as (
    select * from facility union all select * from professional
), stats as (
    select *,
           payment_amount / nullif(claims, 0) as payment_per_claim,
           count(*) over w as peer_count,
           quantile_cont(payment_amount / nullif(claims, 0), 0.25) over w as payment_per_claim_q1,
           quantile_cont(payment_amount / nullif(claims, 0), 0.75) over w as payment_per_claim_q3,
           quantile_cont(claims, 0.25) over w as claims_q1,
           quantile_cont(claims, 0.75) over w as claims_q3
    from unioned
    window w as (partition by provider_type, year)
), flagged as (
    select *,
           -- A fence exists only when peers vary (IQR above zero); a zero IQR would flag everyone above the median.
           (peer_count >= $peer_min_providers and claims >= $min_claims
            and payment_per_claim_q3 > payment_per_claim_q1
            and payment_per_claim > payment_per_claim_q3 + $iqr_multiplier * (payment_per_claim_q3 - payment_per_claim_q1)
           ) as flag_high_payment_per_claim,
           (peer_count >= $peer_min_providers and claims >= $min_claims
            and claims_q3 > claims_q1
            and claims > claims_q3 + $iqr_multiplier * (claims_q3 - claims_q1)) as flag_high_claim_volume
    from stats
)
select p.provider_key, f.provider_type, f.provider_id, f.year, f.claims, f.beneficiaries, f.payment_amount,
       f.payment_per_claim, f.peer_count, f.payment_per_claim_q1, f.payment_per_claim_q3, f.claims_q1, f.claims_q3,
       f.flag_high_payment_per_claim, f.flag_high_claim_volume,
       (f.flag_high_payment_per_claim or f.flag_high_claim_volume) as review_flag,
       list_filter([case when f.flag_high_payment_per_claim then 'HIGH_PAYMENT_PER_CLAIM' end,
                    case when f.flag_high_claim_volume then 'HIGH_CLAIM_VOLUME' end], x -> x is not null) as reason_codes
from flagged f
left join dim_provider p on p.provider_type = case when f.provider_type like 'facility%' then 'facility' else f.provider_type end
                        and p.provider_id = f.provider_id;
