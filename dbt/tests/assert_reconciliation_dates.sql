-- Blocking reconciliation checks in category 'dates' (sql/08_reconciliation.sql). Any returned row fails the build.
select check_name, expected, actual, difference, tolerance, detail
from {{ ref('reconciliation_results') }}
where category = 'dates' and blocking and not passed
