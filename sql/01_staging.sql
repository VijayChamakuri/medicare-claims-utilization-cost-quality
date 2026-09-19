-- 01 Staging. Types raw text, normalizes codes, and drops exact duplicate rows.
-- Parameters: none. Macros below are mirrored in src/medicare_claims/codes.py and tested for parity.

create or replace macro norm_code(x) as nullif(upper(replace(replace(trim(x), '.', ''), ' ', '')), '');
create or replace macro to_date8(x) as try_strptime(x, '%Y%m%d')::date;
create or replace macro to_amt(x) as try_cast(x as decimal(14, 2));
create or replace macro icd9_valid(c) as (
    c is not null and (regexp_full_match(c, '[0-9]{3}[0-9]{0,2}')
                       or regexp_full_match(c, 'V[0-9]{2}[0-9]{0,2}')
                       or regexp_full_match(c, 'E[0-9]{3}[0-9]?')));
create or replace macro hcpcs_valid(c) as (c is not null and regexp_full_match(c, '[0-9A-Z][0-9]{3}[0-9A-Z]'));
create or replace macro hcpcs_group(c) as (
    case
        when not coalesce(hcpcs_valid(c), false) then 'Invalid or missing'
        when regexp_full_match(c, '[0-9]{4}[FT]') then 'CPT category II and III'
        when regexp_full_match(c, '[0-9]{5}') then
            case when c::integer between 99201 and 99499 then 'Evaluation and management'
                 when c::integer between 100 and 1999 then 'Anesthesia'
                 when c::integer between 10021 and 69990 then 'Surgery'
                 when c::integer between 70010 and 79999 then 'Radiology'
                 when c::integer between 80047 and 89398 then 'Pathology and laboratory'
                 when c::integer between 90281 and 99199 or c::integer between 99500 and 99607 then 'Medicine'
                 else 'Unclassified' end
        when regexp_full_match(c, '[0-9].*') then 'Unclassified'
        else case substr(c, 1, 1)
            when 'A' then 'Transportation, medical and surgical supplies'
            when 'B' then 'Enteral and parenteral therapy'
            when 'C' then 'Outpatient PPS temporary codes'
            when 'D' then 'Dental'
            when 'E' then 'Durable medical equipment'
            when 'G' then 'Temporary procedures and professional services'
            when 'H' then 'Behavioral health and substance abuse'
            when 'J' then 'Drugs administered other than oral'
            when 'K' then 'Temporary durable medical equipment'
            when 'L' then 'Orthotic and prosthetic procedures'
            when 'M' then 'Other medical services'
            when 'P' then 'Pathology and laboratory'
            when 'Q' then 'Temporary codes'
            when 'R' then 'Diagnostic radiology'
            when 'S' then 'Private payer temporary codes'
            when 'T' then 'State Medicaid temporary codes'
            when 'V' then 'Vision and hearing'
            else 'Unclassified' end
    end);

create or replace table stg_beneficiary_year as
select
    "DESYNPUF_ID" as beneficiary_id,
    bene_year,
    to_date8("BENE_BIRTH_DT") as birth_date,
    to_date8("BENE_DEATH_DT") as death_date,
    "BENE_SEX_IDENT_CD" as sex_code,
    "BENE_RACE_CD" as race_code,
    "BENE_ESRD_IND" as esrd_code,
    "SP_STATE_CODE" as state_code,
    "BENE_COUNTY_CD" as county_code,
    try_cast("BENE_HI_CVRAGE_TOT_MONS" as integer) as hi_coverage_months,
    try_cast("BENE_SMI_CVRAGE_TOT_MONS" as integer) as smi_coverage_months,
    try_cast("BENE_HMO_CVRAGE_TOT_MONS" as integer) as hmo_coverage_months,
    try_cast("PLAN_CVRG_MOS_NUM" as integer) as plan_coverage_months,
    ("SP_ALZHDMTA" = '1') as sp_alzhdmta,
    ("SP_CHF" = '1') as sp_chf,
    ("SP_CHRNKIDN" = '1') as sp_chrnkidn,
    ("SP_CNCR" = '1') as sp_cncr,
    ("SP_COPD" = '1') as sp_copd,
    ("SP_DEPRESSN" = '1') as sp_depressn,
    ("SP_DIABETES" = '1') as sp_diabetes,
    ("SP_ISCHMCHT" = '1') as sp_ischmcht,
    ("SP_OSTEOPRS" = '1') as sp_osteoprs,
    ("SP_RA_OA" = '1') as sp_ra_oa,
    ("SP_STRKETIA" = '1') as sp_strketia,
    to_amt("MEDREIMB_IP") as medreimb_ip,
    to_amt("BENRES_IP") as benres_ip,
    to_amt("PPPYMT_IP") as pppymt_ip,
    to_amt("MEDREIMB_OP") as medreimb_op,
    to_amt("BENRES_OP") as benres_op,
    to_amt("PPPYMT_OP") as pppymt_op,
    to_amt("MEDREIMB_CAR") as medreimb_car,
    to_amt("BENRES_CAR") as benres_car,
    to_amt("PPPYMT_CAR") as pppymt_car
from raw_beneficiary
qualify row_number() over (partition by "DESYNPUF_ID", bene_year order by source_file) = 1;

-- Institutional claims are staged per segment. CMS allows up to two segments per claim (codebook
-- variable SEGMENT), so the claim key is beneficiary plus CLM_ID and segments are merged later.
create or replace table stg_ip_all as
select
    "DESYNPUF_ID" as beneficiary_id,
    "CLM_ID" as claim_id,
    coalesce("SEGMENT", '1') as segment,
    to_date8("CLM_FROM_DT") as from_date,
    to_date8("CLM_THRU_DT") as thru_date,
    "PRVDR_NUM" as facility_id,
    to_amt("CLM_PMT_AMT") as clm_pmt_amt,
    to_amt("NCH_PRMRY_PYR_CLM_PD_AMT") as nch_prmry_pyr_clm_pd_amt,
    "AT_PHYSN_NPI" as attending_npi,
    "OP_PHYSN_NPI" as operating_npi,
    "OT_PHYSN_NPI" as other_npi,
    to_date8("CLM_ADMSN_DT") as admit_date,
    to_date8("NCH_BENE_DSCHRG_DT") as discharge_date,
    try_cast("CLM_UTLZTN_DAY_CNT" as integer) as source_utilization_days,
    "CLM_DRG_CD" as drg_code,
    norm_code("ADMTNG_ICD9_DGNS_CD") as admitting_dx,
    norm_code("ICD9_DGNS_CD_1") as dx_1, norm_code("ICD9_DGNS_CD_2") as dx_2,
    norm_code("ICD9_DGNS_CD_3") as dx_3, norm_code("ICD9_DGNS_CD_4") as dx_4,
    norm_code("ICD9_DGNS_CD_5") as dx_5, norm_code("ICD9_DGNS_CD_6") as dx_6,
    norm_code("ICD9_DGNS_CD_7") as dx_7, norm_code("ICD9_DGNS_CD_8") as dx_8,
    norm_code("ICD9_DGNS_CD_9") as dx_9, norm_code("ICD9_DGNS_CD_10") as dx_10,
    source_file,
    row_number() over (partition by "DESYNPUF_ID", "CLM_ID", coalesce("SEGMENT", '1')
                       order by source_file) as dup_rank
from raw_inpatient;
create or replace view stg_ip as select * exclude (dup_rank) from stg_ip_all where dup_rank = 1;

create or replace table stg_op_all as
select
    "DESYNPUF_ID" as beneficiary_id,
    "CLM_ID" as claim_id,
    coalesce("SEGMENT", '1') as segment,
    to_date8("CLM_FROM_DT") as from_date,
    to_date8("CLM_THRU_DT") as thru_date,
    "PRVDR_NUM" as facility_id,
    to_amt("CLM_PMT_AMT") as clm_pmt_amt,
    to_amt("NCH_PRMRY_PYR_CLM_PD_AMT") as nch_prmry_pyr_clm_pd_amt,
    "AT_PHYSN_NPI" as attending_npi,
    "OP_PHYSN_NPI" as operating_npi,
    "OT_PHYSN_NPI" as other_npi,
    norm_code("ADMTNG_ICD9_DGNS_CD") as admitting_dx,
    norm_code("ICD9_DGNS_CD_1") as dx_1, norm_code("ICD9_DGNS_CD_2") as dx_2,
    norm_code("ICD9_DGNS_CD_3") as dx_3, norm_code("ICD9_DGNS_CD_4") as dx_4,
    norm_code("ICD9_DGNS_CD_5") as dx_5, norm_code("ICD9_DGNS_CD_6") as dx_6,
    norm_code("ICD9_DGNS_CD_7") as dx_7, norm_code("ICD9_DGNS_CD_8") as dx_8,
    norm_code("ICD9_DGNS_CD_9") as dx_9, norm_code("ICD9_DGNS_CD_10") as dx_10,
    source_file,
    row_number() over (partition by "DESYNPUF_ID", "CLM_ID", coalesce("SEGMENT", '1')
                       order by source_file) as dup_rank
from raw_outpatient;
create or replace view stg_op as select * exclude (dup_rank) from stg_op_all where dup_rank = 1;

-- Carrier claim header fields only (dates and diagnoses). Line detail is unpivoted in 01b.
create or replace table stg_carrier_claim_all as
select
    "DESYNPUF_ID" as beneficiary_id,
    "CLM_ID" as claim_id,
    to_date8("CLM_FROM_DT") as from_date,
    to_date8("CLM_THRU_DT") as thru_date,
    norm_code("ICD9_DGNS_CD_1") as dx_1, norm_code("ICD9_DGNS_CD_2") as dx_2,
    norm_code("ICD9_DGNS_CD_3") as dx_3, norm_code("ICD9_DGNS_CD_4") as dx_4,
    norm_code("ICD9_DGNS_CD_5") as dx_5, norm_code("ICD9_DGNS_CD_6") as dx_6,
    norm_code("ICD9_DGNS_CD_7") as dx_7, norm_code("ICD9_DGNS_CD_8") as dx_8,
    source_file,
    row_number() over (partition by "DESYNPUF_ID", "CLM_ID" order by source_file) as dup_rank
from raw_carrier;
create or replace view stg_carrier_claim as select * exclude (dup_rank) from stg_carrier_claim_all where dup_rank = 1;
