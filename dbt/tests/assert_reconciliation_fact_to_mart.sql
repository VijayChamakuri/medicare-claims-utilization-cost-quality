-- Blocking reconciliation checks in category 'fact_to_mart' (sql/08_reconciliation.sql). Any returned row fails the build.
select check_name, expected, actual, difference, tolerance, detail
from {{ ref('reconciliation_results') }}
where category = 'fact_to_mart' and blocking and not passed
