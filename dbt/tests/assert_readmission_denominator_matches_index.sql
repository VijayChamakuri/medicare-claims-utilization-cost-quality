-- The quality mart's eligible index stays and readmitted stays must equal a recount from the index table.
with mart as (
    select year, sum(eligible_index_stays) as eligible, sum(readmitted_stays) as readmitted
    from {{ ref('mart_quality_monitoring') }} group by year
), recount as (
    select discharge_year as year, count(*) filter (where eligible_index) as eligible,
           count(*) filter (where eligible_index and readmitted) as readmitted
    from {{ ref('mart_readmission_index') }} group by discharge_year
)
select coalesce(m.year, r.year) as year, m.eligible, r.eligible as recount_eligible, m.readmitted, r.readmitted as recount_readmitted
from mart m full join recount r on m.year = r.year
where coalesce(m.eligible, 0) <> coalesce(r.eligible, 0) or coalesce(m.readmitted, 0) <> coalesce(r.readmitted, 0)
