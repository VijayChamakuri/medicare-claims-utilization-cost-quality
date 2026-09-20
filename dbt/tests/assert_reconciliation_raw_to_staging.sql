-- Blocking reconciliation checks in category 'raw_to_staging' (sql/08_reconciliation.sql). Any returned row fails the build.
select check_name, expected, actual, difference, tolerance, detail
from {{ ref('reconciliation_results') }}
where category = 'raw_to_staging' and blocking and not passed
