-- 06 Quality and operations monitoring. These are measure-inspired proxies, not certified measures.
-- Parameters: $study_end, $readmission_days, $comorb_low_max, $comorb_medium_max, $adm_one, $adm_two_plus,
-- $paid_medium_min, $paid_high_min, $tier_low_max, $tier_medium_max.

-- Utilization risk tier: transparent points from prior-year information only.
create or replace table mart_member_risk as
with prior as (
    select f.beneficiary_id, f.year,
           p.beneficiary_id is not null as has_prior_year,
           coalesce(p.chronic_condition_count, 0) as prior_chronic_conditions,
           coalesce(s.admissions, 0) as prior_admissions,
           coalesce(s.payment_amount, 0) as prior_paid_amount
    from fact_beneficiary_year f
    left join fact_beneficiary_year p on p.beneficiary_id = f.beneficiary_id and p.year = f.year - 1
    left join mart_beneficiary_year_summary s on s.beneficiary_id = f.beneficiary_id and s.year = f.year - 1
), scored as (
    select *,
           case when prior_chronic_conditions <= $comorb_low_max then 0
                when prior_chronic_conditions <= $comorb_medium_max then 1 else 2 end as comorbidity_points,
           case when prior_admissions = 0 then 0 when prior_admissions = 1 then $adm_one else $adm_two_plus end as admission_points,
           case when prior_paid_amount >= $paid_high_min then 2
                when prior_paid_amount >= $paid_medium_min then 1 else 0 end as paid_points
    from prior
)
select beneficiary_id, year, has_prior_year, prior_chronic_conditions, prior_admissions, prior_paid_amount,
       comorbidity_points, admission_points, paid_points,
       comorbidity_points + admission_points + paid_points as risk_score,
       case when not has_prior_year then 'not_assessed'
            when comorbidity_points + admission_points + paid_points <= $tier_low_max then 'low'
            when comorbidity_points + admission_points + paid_points <= $tier_medium_max then 'medium'
            else 'high' end as utilization_risk_tier
from scored;

-- 30-day all-cause readmission proxy. Index stay: valid dates, beneficiary did not die between admit and
-- discharge, and a full follow-up window before the study ends. Readmission: another stay beginning after
-- the index discharge date and within the window. No planned-readmission exclusion is possible (no such field).
create or replace table mart_readmission_index as
with base as (
    select s.stay_key, s.beneficiary_id, s.admit_date, s.discharge_date,
           extract(year from s.discharge_date)::integer as discharge_year,
           coalesce(b.death_date between s.admit_date and s.discharge_date, false) as died_in_stay,
           (s.discharge_date > $study_end::date - $readmission_days::integer) as insufficient_followup,
           (select count(*) from fact_inpatient_stay n
             where n.beneficiary_id = s.beneficiary_id and n.admit_date > s.discharge_date
               and n.admit_date <= s.discharge_date + $readmission_days::integer) as readmissions_in_window
    from fact_inpatient_stay s
    join dim_beneficiary b using (beneficiary_id)
)
select *,
       (not died_in_stay and not insufficient_followup) as eligible_index,
       (not died_in_stay and not insufficient_followup and readmissions_in_window > 0) as readmitted
from base;

create or replace table mart_quality_monitoring as
select r.discharge_year as year,
       coalesce(m.utilization_risk_tier, 'not_assessed') as utilization_risk_tier,
       count(*) filter (where r.eligible_index) as eligible_index_stays,
       count(*) filter (where r.readmitted) as readmitted_stays,
       case when count(*) filter (where r.eligible_index) > 0
            then (count(*) filter (where r.readmitted))::double / (count(*) filter (where r.eligible_index)) end as readmission_rate,
       count(*) filter (where r.died_in_stay) as excluded_died_in_stay,
       count(*) filter (where r.insufficient_followup and not r.died_in_stay) as excluded_insufficient_followup,
       count(*) as stays_considered
from mart_readmission_index r
left join mart_member_risk m on m.beneficiary_id = r.beneficiary_id and m.year = r.discharge_year
group by r.discharge_year, coalesce(m.utilization_risk_tier, 'not_assessed');

create or replace table mart_condition_summary as
select 'primary_diagnosis_ccs' as condition_type, h.claim_year as year, h.setting,
       coalesce(d.ccs_category::varchar, 'unmapped') as condition_id,
       case when h.primary_dx is null then 'Missing primary diagnosis'
            when d.ccs_category is not null then d.ccs_category_name
            when h.primary_dx_valid then 'Unmapped (valid format, not in CCS 2015)'
            else 'Invalid code format' end as condition_name,
       count(*) as claims,
       count(distinct h.beneficiary_id) as beneficiaries,
       sum(h.payment_amount)::decimal(16, 2) as payment_amount,
       null::bigint as denominator_beneficiaries
from fact_claim_header h
left join dim_diagnosis d on d.diagnosis_code = h.primary_dx
where h.is_analytic
group by 1, 2, 3, 4, 5
union all
select 'chronic_condition_flag', year, 'all', condition, upper(replace(condition, 'sp_', '')) as label,
       0, count(*) filter (where flag), null, count(*)
from (unpivot (select beneficiary_id, year, sp_alzhdmta, sp_chf, sp_chrnkidn, sp_cncr, sp_copd, sp_depressn,
                      sp_diabetes, sp_ischmcht, sp_osteoprs, sp_ra_oa, sp_strketia from fact_beneficiary_year)
      on sp_alzhdmta, sp_chf, sp_chrnkidn, sp_cncr, sp_copd, sp_depressn, sp_diabetes, sp_ischmcht,
         sp_osteoprs, sp_ra_oa, sp_strketia into name condition value flag)
group by year, condition;
