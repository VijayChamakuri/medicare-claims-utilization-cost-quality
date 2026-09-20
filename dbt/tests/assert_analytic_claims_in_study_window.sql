-- Analytic claims must have valid dates inside the study window; anything else is excluded upstream.
select claim_key, service_date
from {{ ref('fact_claim_header') }}
where is_analytic and (not date_valid or not in_study_window
      or service_date < '{{ var("study_start") }}'::date or service_date > '{{ var("study_end") }}'::date)
