{% test source_not_empty(model) %}
-- Fails when a source table is empty: an empty load means the download or ingest step failed.
select 1 as empty_source where (select count(*) from {{ model }}) = 0
{% endtest %}
