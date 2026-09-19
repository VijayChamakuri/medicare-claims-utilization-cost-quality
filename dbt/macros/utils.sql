{% macro duckdb_varchar_list(values) -%}
  [{% for v in values %}'{{ v }}'{% if not loop.last %}, {% endif %}{% endfor %}]::varchar[]
{%- endmacro %}

{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ target.schema }}
{%- endmacro %}
