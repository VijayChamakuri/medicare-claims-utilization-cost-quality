-- 02 Dimensions. Parameters: $study_start, $study_end, $ed_codes.
-- ref_ccs_dx (AHRQ CCS 2015, ICD-9-CM) is loaded by src/medicare_claims/model.py before this file runs.

create or replace table dim_date as
select
    d::date as date_key,
    extract(year from d)::integer as year,
    extract(month from d)::integer as month,
    extract(quarter from d)::integer as quarter,
    strftime(d, '%Y-%m') as year_month,
    date_trunc('month', d)::date as month_start,
    (d::date between $study_start::date and $study_end::date) as in_study_window
from generate_series(date '2007-01-01', $study_end::date, interval 1 day) as t(d);

create or replace table dim_beneficiary as
select
    row_number() over (order by beneficiary_id) as beneficiary_key,
    beneficiary_id,
    min(birth_date) as birth_date,
    max(death_date) as death_date,
    (max(death_date) is not null) as deceased,
    arg_max(sex_code, bene_year) as sex_code,
    case arg_max(sex_code, bene_year) when '1' then 'Male' when '2' then 'Female' else 'Unknown' end as sex,
    arg_max(race_code, bene_year) as race_code,
    case arg_max(race_code, bene_year) when '1' then 'White' when '2' then 'Black'
         when '3' then 'Other' when '5' then 'Hispanic' else 'Unknown' end as race,
    arg_max(state_code, bene_year) as state_code,
    bool_or(esrd_code = 'Y') as ever_esrd,
    min(bene_year) as first_year,
    max(bene_year) as last_year
from stg_beneficiary_year
group by beneficiary_id;

create or replace table dim_care_setting as
select * from (values
    ('inpatient', 'Inpatient (institutional, hospital stays)', 'CMS inpatient claims file', 1),
    ('outpatient', 'Outpatient (institutional, hospital outpatient)', 'CMS outpatient claims file', 2),
    ('carrier', 'Carrier (professional, physician and supplier)', 'CMS carrier claims file', 3)
) as t(care_setting, description, source_file_type, sort_order);

create or replace table dim_provider as
with ids as (
    select 'facility' as provider_type, facility_id as provider_id, 'inpatient_facility' as source_role
      from stg_ip where facility_id is not null
    union all select 'facility', facility_id, 'outpatient_facility' from stg_op where facility_id is not null
    union all select 'npi', attending_npi, 'inpatient_attending' from stg_ip where attending_npi is not null
    union all select 'npi', operating_npi, 'inpatient_operating' from stg_ip where operating_npi is not null
    union all select 'npi', other_npi, 'inpatient_other' from stg_ip where other_npi is not null
    union all select 'npi', attending_npi, 'outpatient_attending' from stg_op where attending_npi is not null
    union all select 'npi', operating_npi, 'outpatient_operating' from stg_op where operating_npi is not null
    union all select 'npi', other_npi, 'outpatient_other' from stg_op where other_npi is not null
    union all select 'npi', npi, 'carrier_performing' from stg_carrier_line where npi is not null
)
select
    row_number() over (order by provider_type, provider_id) as provider_key,
    provider_type,
    provider_id,
    list_sort(list_distinct(list(source_role))) as source_roles
from ids
group by provider_type, provider_id;

create or replace table dim_diagnosis as
with codes as (select code, count(*) as occurrences from stg_dx_long group by code)
select
    row_number() over (order by c.code) as diagnosis_key,
    c.code as diagnosis_code,
    'ICD-9-CM' as code_system,
    icd9_valid(c.code) as format_valid,
    m.ccs_category,
    case when m.ccs_category is not null then m.ccs_category_name
         when icd9_valid(c.code) then 'Unmapped (valid format, not in CCS 2015)'
         else 'Invalid code format' end as ccs_category_name,
    (m.ccs_category is not null) as is_mapped,
    c.occurrences
from codes c
left join ref_ccs_dx m on m.icd9_code = c.code;

create or replace table dim_procedure as
with codes as (
    select code from stg_hcpcs_long
    union select hcpcs from stg_carrier_line where hcpcs is not null
)
select
    row_number() over (order by code) as procedure_key,
    code as procedure_code,
    'HCPCS' as code_system,
    hcpcs_valid(code) as format_valid,
    hcpcs_group(code) as procedure_group,
    list_contains($ed_codes, code) as is_ed_proxy_code
from codes;
