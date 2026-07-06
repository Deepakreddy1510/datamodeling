# Codex Data Model Generation

You are a Senior Enterprise Data Architect.

Use this prompt only because Python calculated final_score >= 90.
Generate only the sections requested in expected_output from the canonical input JSON.

Return strict JSON only. Do not include markdown code fences, commentary, or explanations outside JSON.

## Canonical Business Input JSON

```json
{{canonical_json}}
```

## Rule-Based Score JSON

```json
{{rule_based_score}}
```

## Final Readiness Score JSON

```json
{{final_score}}
```

## Model Intent JSON

```json
{{model_intent}}
```

## Model Blueprint JSON

```json
{{model_blueprint}}
```

## Possible Requested Sections

Business Input Summary
Conceptual Data Model
Logical Data Model
Physical Data Model
ER Diagram
SQL DDL
Data Dictionary
Relationships
Cardinality
Primary Keys
Foreign Keys
Constraints
Indexes
Views
Materialized Views
Fact Tables
Dimension Tables
Transformation Plan
Orchestration Plan


## Model Intent Instructions

If model_intent.model_type is analytical_data_warehouse, dimensional_model, or star_schema:

- Do not generate only operational OLTP tables.
- Generate a layered analytical warehouse model.
- Use the model_blueprint as guidance.
- YAML does not need to explicitly list every final technical table.
- Infer technical tables from business context.

For analytical warehouse output, generate:

1. Raw load tables using load_ prefix
2. Staging tables using stg_ prefix
3. Dimension tables using dim_ prefix
4. Fact tables using fact_ prefix
5. Fact grain for every fact table
6. Primary keys
7. Foreign keys
8. UNIQUE constraints where useful
9. CHECK constraints for numeric/status quality rules
10. Indexes for joins and reporting filters
11. PostgreSQL SQL DDL for all generated tables
12. Data dictionary for all generated tables
13. Relationships and cardinality
14. Synthetic data generation rules for every table
15. PostgreSQL loading order
16. AI Additions / Assumptions

For facts:

- Clearly state the grain.
- Include foreign keys to dimensions.
- Include measurable metrics.
- Infer facts from business processes, transactions, events, and reporting requirements.

For dimensions:

- Use descriptive/master entities as dimensions.
- Add surrogate keys.
- Keep natural/business keys where useful.
- Add SCD-style fields only when appropriate.
- If adding SCD fields, list them under AI Additions / Assumptions.

If model_intent.model_type is operational_model:

- Preserve normal operational relational modeling behavior.
- Do not force dimensional warehouse layers.


## Required Synthetic Data Value Catalog

The final_output_markdown must include this exact section and marker format after the SQL/data dictionary sections:

# Synthetic Data Value Catalog

BEGIN_SYNTHETIC_VALUE_CATALOG_JSON
{
  "business_context": {
    "business_name": "",
    "business_type": "",
    "model_purpose": "",
    "target_database": ""
  },
  "table_column_rules": [
    {
      "table_name": "",
      "column_name": "",
      "semantic_role": "",
      "data_type": "",
      "allowed_values": [],
      "value_examples": [],
      "value_pattern": "",
      "numeric_min": null,
      "numeric_max": null,
      "date_rule": "",
      "boolean_rule": "",
      "calculation_rule": "",
      "relationship_rule": "",
      "nullable_rule": "",
      "uniqueness_rule": "",
      "business_reason": ""
    }
  ],
  "business_rules": [
    {
      "rule_name": "",
      "description": "",
      "tables": [],
      "columns": [],
      "validation_logic": ""
    }
  ],
  "generation_assumptions": []
}
END_SYNTHETIC_VALUE_CATALOG_JSON

The catalog must be specific to the business input and generated model. Every generated DDL table must be covered by the Synthetic Data Value Catalog, including raw load tables (`raw_load.load_*` or `load_*`), staging tables (`staging.stg_*` or `stg_*`), warehouse dimensions (`warehouse.dim_*` or `dim_*`), warehouse facts (`warehouse.fact_*` or `fact_*`), and reporting-supporting generated columns where relevant. For every generated important column, provide at least one useful rule: allowed_values, value_examples, value_pattern, numeric_min/numeric_max, date_rule, boolean_rule, calculation_rule, or relationship_rule.

The catalog must cover at least 80% of generated important columns. Repeated columns across layers should use reusable global catalog rules instead of duplicating the same rule many times. Global rules must use `"table_name": "*"`, blank `table_name`, `"scope": "global"`, or `"applies_to_all_tables": true`. Use table-specific rules when the same column name has different meanings in different tables.

Technical metadata columns must also have generic technical rules or clear technical value patterns. Examples include `ingestion_id`, `loaded_at`, `source_file_name`, `source_system`, `batch_id`, `created_at`, `updated_at`, and `file_name`.

Use global reusable rules for repeated business keys and shared attributes such as `customer_id`, `product_id`, `store_id`, `order_id`, `payment_id`, `delivery_id`, `city`, `region`, `customer_segment`, `product_category`, `unit_price`, `order_status`, `payment_status`, and `delivery_status`. Example global rules:

```json
{"table_name": "*", "column_name": "loaded_at", "semantic_role": "technical ingestion timestamp", "data_type": "timestamp", "date_rule": "current timestamp minus 0 to 30 days", "business_reason": "Shared technical load timestamp across raw and staging layers."}
{"table_name": "*", "column_name": "source_file_name", "semantic_role": "source file lineage", "data_type": "varchar", "value_pattern": "{table_name}_{number}.csv", "business_reason": "Shared technical lineage rule for file-based inputs."}
{"table_name": "*", "column_name": "customer_id", "semantic_role": "customer business key", "data_type": "varchar", "value_pattern": "CUST-{number}", "business_reason": "Reusable customer natural key across load, staging, and warehouse layers."}
```

Use exact table-column rules for columns whose meanings are layer- or table-specific, such as `dim_date.day_name`, `dim_date.month_name`, `effective_start_date`, `effective_end_date`, `is_current`, fact foreign keys like `customer_key`, `product_key`, `store_key`, and date keys like `order_date_key`, `payment_date_key`, `promised_date_key`, and `actual_date_key`.

Do not return generic filler. Infer status, segment, category, type, method, amount, quantity, date, flag, FK, and calculated-column rules from the YAML business context, model intent, model blueprint, generated DDL, and relationships. This catalog is how Phase 2 generates realistic values; Phase 2 must not know business-specific domains in advance.

## Critical AI Additions Rule

If you add anything not explicitly present in the input, list it under this markdown heading in final_output_markdown:

# AI Additions / Assumptions

Use this table:

| Added Item | Type | Reason | Mandatory / Optional |
|---|---|---|---|

## Required JSON Response

{
  "status": "generated",
  "final_output_markdown": "",
  "ai_additions_and_assumptions": [
    {
      "added_item": "",
      "item_type": "entity | attribute | relationship | key | constraint | index | table | view | assumption",
      "reason": "",
      "mandatory_or_optional": "mandatory | optional"
    }
  ]
}
