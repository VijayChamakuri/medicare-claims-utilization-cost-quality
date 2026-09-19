"""Data-quality measurements behind reports/data_quality_report.md."""

from __future__ import annotations

from typing import Any

import duckdb

from medicare_claims.metrics import compute_data_quality


def code_quality(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    def one(sql: str) -> Any:
        row = con.execute(sql).fetchone()
        return None if row is None else row[0]

    total = int(one("select count(*) from fact_claim_diagnosis"))
    return {
        "diagnosis_rows": total,
        "diagnosis_invalid_format": int(one("select count(*) from fact_claim_diagnosis f join dim_diagnosis d on d.diagnosis_code = f.diagnosis_code where not d.format_valid")),
        "diagnosis_unmapped_valid": int(one("select count(*) from fact_claim_diagnosis f join dim_diagnosis d on d.diagnosis_code = f.diagnosis_code where d.format_valid and not d.is_mapped")),
        "distinct_diagnosis_codes": int(one("select count(*) from dim_diagnosis")),
        "distinct_procedure_codes": int(one("select count(*) from dim_procedure")),
        "procedure_invalid_format": int(one("select count(*) from dim_procedure where not format_valid")),
        "claims_missing_primary_dx": {s: int(n) for s, n in con.execute(
            "select setting, count(*) from fact_claim_header where is_analytic and primary_dx is null group by 1").fetchall()},
        "claims_by_setting": {s: int(n) for s, n in con.execute(
            "select setting, count(*) from fact_claim_header where is_analytic group by 1").fetchall()},
        "stays_source_utilization_day_mismatch": int(one(
            "select count(*) from fact_inpatient_stay where claim_count = 1 and source_utilization_days is not null "
            "and source_utilization_days <> length_of_stay_days")),
        "stays_with_source_utilization_days": int(one(
            "select count(*) from fact_inpatient_stay where claim_count = 1 and source_utilization_days is not null")),
        "zero_payment_claims": int(one("select count(*) from fact_claim_header where is_analytic and payment_amount = 0")),
        "orphan_claims": int(one("select count(*) from fact_claim_header h where not exists "
                                 "(select 1 from dim_beneficiary b where b.beneficiary_id = h.beneficiary_id)")),
        "claims_after_death": int(one(
            "select count(*) from fact_claim_header h join dim_beneficiary b using (beneficiary_id) "
            "where h.is_analytic and b.death_date is not null and h.service_date > b.death_date")),
    }


def all_quality(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {"counts": compute_data_quality(con), "codes": code_quality(con)}
