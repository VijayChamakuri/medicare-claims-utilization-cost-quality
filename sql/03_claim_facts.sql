-- 03 Claim facts. Parameters: $study_start, $study_end.
-- Grain: fact_claim_header is one row per claim (beneficiary + CLM_ID within a setting, segments merged).

create or replace table fact_claim_header as
with ip as (
    select 'inpatient' as setting, beneficiary_id, claim_id,
           min(from_date) as from_date, max(thru_date) as thru_date,
           min(admit_date) as admit_date, max(discharge_date) as discharge_date,
           coalesce(sum(clm_pmt_amt), 0)::decimal(14, 2) as payment_amount,
           count(*) as segment_count, null::integer as line_count,
           arg_min(facility_id, segment) filter (where facility_id is not null) as facility_id,
           arg_min(dx_1, segment) filter (where dx_1 is not null) as primary_dx,
           max(source_utilization_days) as source_utilization_days
    from stg_ip group by beneficiary_id, claim_id
), op as (
    select 'outpatient' as setting, beneficiary_id, claim_id,
           min(from_date) as from_date, max(thru_date) as thru_date,
           null::date as admit_date, null::date as discharge_date,
           coalesce(sum(clm_pmt_amt), 0)::decimal(14, 2) as payment_amount,
           count(*) as segment_count, null::integer as line_count,
           arg_min(facility_id, segment) filter (where facility_id is not null) as facility_id,
           arg_min(dx_1, segment) filter (where dx_1 is not null) as primary_dx,
           null::integer as source_utilization_days
    from stg_op group by beneficiary_id, claim_id
), ca as (
    select 'carrier' as setting, c.beneficiary_id, c.claim_id, c.from_date, c.thru_date,
           null::date as admit_date, null::date as discharge_date,
           coalesce(l.payment, 0)::decimal(14, 2) as payment_amount,
           1 as segment_count, coalesce(l.line_count, 0)::integer as line_count,
           null::varchar as facility_id, c.dx_1 as primary_dx, null::integer as source_utilization_days
    from stg_carrier_claim c
    left join (select beneficiary_id, claim_id, sum(line_nch_pmt_amt) as payment, count(*) as line_count
               from stg_carrier_line group by 1, 2) l using (beneficiary_id, claim_id)
), unioned as (
    select * from ip union all select * from op union all select * from ca
), flagged as (
    select
        setting || ':' || beneficiary_id || ':' || claim_id as claim_key,
        *,
        case setting when 'carrier' then 'LINE_NCH_PMT_AMT_1..13 (sum of lines)'
                     else 'CLM_PMT_AMT (sum of segments)' end as payment_source_field,
        (from_date is not null and thru_date is not null and from_date <= thru_date
         and (setting <> 'inpatient'
              or (admit_date is not null and discharge_date is not null and admit_date <= discharge_date))) as date_valid,
        -- Inpatient claims are dated by admission so claims and stays always fall in the same period.
        case when setting = 'inpatient' then coalesce(admit_date, from_date) else from_date end as service_date,
        primary_dx is not null as has_primary_dx,
        icd9_valid(primary_dx) as primary_dx_valid
    from unioned
), dated as (
    select *,
           coalesce(service_date between $study_start::date and $study_end::date, false) as in_study_window
    from flagged
)
select *,
       (date_valid and in_study_window) as is_analytic,
       extract(year from service_date)::integer as claim_year,
       date_trunc('month', service_date)::date as month_start
from dated;

create or replace table fact_claim_diagnosis as
select setting || ':' || beneficiary_id || ':' || claim_id as claim_key, setting, beneficiary_id, claim_id,
       code as diagnosis_code, min(pos) as first_position
from stg_dx_long
group by setting, beneficiary_id, claim_id, code;

create or replace table fact_claim_line as
select 'carrier:' || beneficiary_id || ':' || claim_id as claim_key, 'carrier' as setting, beneficiary_id, claim_id,
       line_num, hcpcs as procedure_code, npi as performing_npi, tax_num, line_dx as line_diagnosis_code,
       line_nch_pmt_amt, line_bene_ptb_ddctbl_amt, line_bene_prmry_pyr_pd_amt, line_coinsrnc_amt,
       line_alowd_chrg_amt, line_prcsg_ind_cd
from stg_carrier_line
union all
select setting || ':' || beneficiary_id || ':' || claim_id, setting, beneficiary_id, claim_id,
       (coalesce(try_cast(segment as integer), 1) - 1) * 45 + line_num, code, null, null, null,
       null::decimal(14, 2), null::decimal(14, 2), null::decimal(14, 2), null::decimal(14, 2),
       null::decimal(14, 2), null
from (select distinct * from stg_hcpcs_long);

-- One row per continuous inpatient stay. A claim whose admit date is on or before the discharge date
-- of the beneficiary's earlier stay continues that stay (a transfer or continuation), not a new admission.
create or replace table fact_inpatient_stay as
with claims as (
    select claim_key, beneficiary_id, claim_id, admit_date, discharge_date, payment_amount, facility_id,
           primary_dx, source_utilization_days
    from fact_claim_header where setting = 'inpatient' and is_analytic
), ordered as (
    select *, max(discharge_date) over (
        partition by beneficiary_id order by admit_date, claim_id
        rows between unbounded preceding and 1 preceding) as prior_max_discharge
    from claims
), numbered as (
    select *, sum(case when prior_max_discharge is null or admit_date > prior_max_discharge then 1 else 0 end)
        over (partition by beneficiary_id order by admit_date, claim_id rows unbounded preceding) as stay_seq
    from ordered
)
select
    beneficiary_id || ':' || stay_seq as stay_key,
    beneficiary_id,
    stay_seq,
    min(admit_date) as admit_date,
    max(discharge_date) as discharge_date,
    date_diff('day', min(admit_date), max(discharge_date)) as length_of_stay_days,
    count(*) as claim_count,
    sum(payment_amount)::decimal(14, 2) as payment_amount,
    arg_min(facility_id, admit_date) as admitting_facility_id,
    arg_min(primary_dx, admit_date) as primary_dx,
    max(source_utilization_days) as source_utilization_days,
    extract(year from min(admit_date))::integer as admit_year,
    date_trunc('month', min(admit_date))::date as admit_month
from numbered
group by beneficiary_id, stay_seq;

create or replace table fact_beneficiary_year as
select
    b.beneficiary_id,
    b.bene_year as year,
    b.hi_coverage_months, b.smi_coverage_months, b.hmo_coverage_months, b.plan_coverage_months,
    b.sp_alzhdmta, b.sp_chf, b.sp_chrnkidn, b.sp_cncr, b.sp_copd, b.sp_depressn, b.sp_diabetes,
    b.sp_ischmcht, b.sp_osteoprs, b.sp_ra_oa, b.sp_strketia,
    (coalesce(b.sp_alzhdmta, false)::integer + coalesce(b.sp_chf, false)::integer + coalesce(b.sp_chrnkidn, false)::integer
     + coalesce(b.sp_cncr, false)::integer + coalesce(b.sp_copd, false)::integer + coalesce(b.sp_depressn, false)::integer
     + coalesce(b.sp_diabetes, false)::integer + coalesce(b.sp_ischmcht, false)::integer
     + coalesce(b.sp_osteoprs, false)::integer + coalesce(b.sp_ra_oa, false)::integer
     + coalesce(b.sp_strketia, false)::integer) as chronic_condition_count,
    b.medreimb_ip, b.benres_ip, b.pppymt_ip, b.medreimb_op, b.benres_op, b.pppymt_op,
    b.medreimb_car, b.benres_car, b.pppymt_car,
    case when d.death_date is null or extract(year from d.death_date) > b.bene_year then 12
         when extract(year from d.death_date) < b.bene_year then 0
         else extract(month from d.death_date)::integer end as months_alive,
    greatest(0, least(coalesce(b.hi_coverage_months, 0),
        case when d.death_date is null or extract(year from d.death_date) > b.bene_year then 12
             when extract(year from d.death_date) < b.bene_year then 0
             else extract(month from d.death_date)::integer end)) as member_months
from stg_beneficiary_year b
join dim_beneficiary d using (beneficiary_id);
