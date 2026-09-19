-- Blocking reconciliation checks in category 'foreign_keys' (sql/08_reconciliation.sql). Any returned row fails the build.
select check_name, expected, actual, difference, tolerance, detail
from {{ ref('reconciliation_results') }}
where category = 'foreign_keys' and blocking and not passed
