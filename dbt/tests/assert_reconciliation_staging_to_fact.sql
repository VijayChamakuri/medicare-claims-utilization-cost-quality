-- Blocking reconciliation checks in category 'staging_to_fact' (sql/08_reconciliation.sql). Any returned row fails the build.
select check_name, expected, actual, difference, tolerance, detail
from {{ ref('reconciliation_results') }}
where category = 'staging_to_fact' and blocking and not passed
