-- 05 Payment marts. Payment fields keep their CMS meaning: CLM_PMT_AMT (inpatient, outpatient) and
-- LINE_NCH_PMT_AMT_1..13 (carrier) are Medicare trust fund payments. Parameters: $top_share_percent.

create or replace table mart_payment_monthly as
select month_start, setting, payment_source_field,
       count(*) as claims,
       sum(payment_amount)::decimal(16, 2) as payment_amount,
       count(*) filter (where payment_amount < 0) as negative_payment_claims,
       count(*) filter (where payment_amount = 0) as zero_payment_claims
from fact_claim_header
where is_analytic
group by month_start, setting, payment_source_field;

create or replace table mart_payment_annual as
select claim_year as year, setting, payment_source_field,
       count(*) as claims,
       sum(payment_amount)::decimal(16, 2) as payment_amount,
       count(distinct beneficiary_id) as paid_beneficiaries
from fact_claim_header
where is_analytic
group by claim_year, setting, payment_source_field;

create or replace table mart_beneficiary_year_summary as
select f.beneficiary_id, f.year, f.member_months, f.chronic_condition_count,
       coalesce(c.claims, 0) as claims,
       coalesce(c.payment, 0)::decimal(16, 2) as payment_amount,
       coalesce(a.admissions, 0) as admissions
from fact_beneficiary_year f
left join (select beneficiary_id, claim_year as year, count(*) as claims, sum(payment_amount) as payment
           from fact_claim_header where is_analytic group by 1, 2) c
       on c.beneficiary_id = f.beneficiary_id and c.year = f.year
left join (select beneficiary_id, admit_year as year, count(*) as admissions
           from fact_inpatient_stay group by 1, 2) a
       on a.beneficiary_id = f.beneficiary_id and a.year = f.year;

-- Payment concentration: share of paid amount held by the top N percent of beneficiaries in a year.
-- The top group is ceil(N% of beneficiaries) people ranked by paid amount, ties broken by ID.
create or replace table mart_payment_concentration as
with ranked as (
    select year, beneficiary_id, payment_amount,
           row_number() over (partition by year order by payment_amount desc, beneficiary_id) as rnk,
           count(*) over (partition by year) as n
    from mart_beneficiary_year_summary
)
select
    year,
    max(n) as beneficiaries,
    ceil(max(n) * $top_share_percent / 100.0)::integer as top_count,
    coalesce(sum(payment_amount) filter (where rnk <= ceil(n * $top_share_percent / 100.0)), 0)::decimal(16, 2) as top_payment,
    sum(payment_amount)::decimal(16, 2) as total_payment,
    case when sum(payment_amount) <> 0
         then sum(payment_amount) filter (where rnk <= ceil(n * $top_share_percent / 100.0)) / sum(payment_amount) end as top_share,
    arg_min(beneficiary_id, rnk) as top_beneficiary_id
from ranked
group by year;

-- Demographic summary for filters. Age is age at the end of the calendar year, from the synthetic birth date.
create or replace table mart_demographic_summary as
select s.year, b.sex, b.race,
       case when s.year - extract(year from b.birth_date) < 65 then 'Under 65'
            when s.year - extract(year from b.birth_date) < 75 then '65-74'
            when s.year - extract(year from b.birth_date) < 85 then '75-84'
            else '85 and over' end as age_band,
       count(*) as beneficiaries,
       sum(s.member_months) as member_months,
       sum(s.claims) as claims,
       sum(s.payment_amount)::decimal(16, 2) as payment_amount,
       sum(s.admissions) as admissions
from mart_beneficiary_year_summary s
join dim_beneficiary b using (beneficiary_id)
group by 1, 2, 3, 4;
