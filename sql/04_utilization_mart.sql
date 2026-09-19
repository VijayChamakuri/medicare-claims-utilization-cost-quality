-- 04 Utilization marts. Parameters: $ed_codes.
-- Member-month rule: a beneficiary-year contributes min(Part A coverage months, months alive) member months,
-- placed from January. CMS gives a count of coverage months, not which months (see docs/limitations.md).

create or replace table mart_member_month as
select f.beneficiary_id, f.year, t.m as month, make_date(f.year, t.m, 1) as month_start,
       (t.m <= f.member_months) as eligible
from fact_beneficiary_year f, unnest(range(1, 13)) as t(m);

create or replace table mart_utilization_monthly as
with members as (
    select month_start, count(*) filter (where eligible) as members from mart_member_month group by 1
), claims as (
    select setting, month_start, count(*) as claims, count(distinct beneficiary_id) as unique_beneficiaries
    from fact_claim_header where is_analytic group by 1, 2
), admits as (
    select admit_month as month_start, count(*) as admissions from fact_inpatient_stay group by 1
), ed_claims as (
    select distinct claim_key from fact_claim_line
    where setting = 'outpatient' and list_contains($ed_codes, procedure_code)
), ed as (
    select h.month_start, count(*) as ed_proxy_visits
    from fact_claim_header h join ed_claims e using (claim_key)
    where h.setting = 'outpatient' and h.is_analytic group by 1
), lines as (
    select h.month_start, count(*) as carrier_service_lines
    from fact_claim_line l join fact_claim_header h using (claim_key)
    where h.setting = 'carrier' and h.is_analytic group by 1
)
select
    m.month_start,
    s.care_setting as setting,
    m.members,
    coalesce(c.claims, 0) as claims,
    coalesce(c.unique_beneficiaries, 0) as unique_beneficiaries,
    case when s.care_setting = 'inpatient' then coalesce(a.admissions, 0) end as admissions,
    case when s.care_setting = 'outpatient' then coalesce(e.ed_proxy_visits, 0) end as ed_proxy_visits,
    case when s.care_setting = 'outpatient' then coalesce(c.claims, 0) end as outpatient_visits,
    case when s.care_setting = 'carrier' then coalesce(l.carrier_service_lines, 0) end as carrier_service_lines,
    case when m.members > 0 then coalesce(c.claims, 0) * 1000.0 / m.members end as claims_per_1000_members
from members m
cross join dim_care_setting s
left join claims c on c.month_start = m.month_start and c.setting = s.care_setting
left join admits a on a.month_start = m.month_start
left join ed e on e.month_start = m.month_start
left join lines l on l.month_start = m.month_start
where m.month_start is not null;

create or replace table mart_utilization_annual as
with members as (
    select year, sum(member_months) as member_months, count(*) as beneficiaries from fact_beneficiary_year group by 1
), claims as (
    select setting, claim_year as year, count(*) as claims, count(distinct beneficiary_id) as unique_beneficiaries
    from fact_claim_header where is_analytic group by 1, 2
), admits as (
    select admit_year as year, count(*) as admissions, sum(length_of_stay_days) as total_length_of_stay_days
    from fact_inpatient_stay group by 1
), ed_claims as (
    select distinct claim_key from fact_claim_line
    where setting = 'outpatient' and list_contains($ed_codes, procedure_code)
), ed as (
    select h.claim_year as year, count(*) as ed_proxy_visits
    from fact_claim_header h join ed_claims e using (claim_key)
    where h.setting = 'outpatient' and h.is_analytic group by 1
), lines as (
    select h.claim_year as year, count(*) as carrier_service_lines
    from fact_claim_line l join fact_claim_header h using (claim_key)
    where h.setting = 'carrier' and h.is_analytic group by 1
)
select
    m.year,
    s.care_setting as setting,
    m.beneficiaries,
    m.member_months,
    m.member_months / 12.0 as member_years,
    coalesce(c.claims, 0) as claims,
    coalesce(c.unique_beneficiaries, 0) as unique_beneficiaries,
    case when s.care_setting = 'inpatient' then coalesce(a.admissions, 0) end as admissions,
    case when s.care_setting = 'inpatient' then coalesce(a.total_length_of_stay_days, 0) end as total_length_of_stay_days,
    case when s.care_setting = 'outpatient' then coalesce(e.ed_proxy_visits, 0) end as ed_proxy_visits,
    case when s.care_setting = 'outpatient' then coalesce(c.claims, 0) end as outpatient_visits,
    case when s.care_setting = 'carrier' then coalesce(l.carrier_service_lines, 0) end as carrier_service_lines
from members m
cross join dim_care_setting s
left join claims c on c.year = m.year and c.setting = s.care_setting
left join admits a on a.year = m.year
left join ed e on e.year = m.year
left join lines l on l.year = m.year;
