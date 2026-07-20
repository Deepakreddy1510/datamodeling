# Generation Quality Report

Status: **passed_with_warnings**

## Errors

- None

## Warnings

- Inferred fact table(s) not found by name or close equivalent: fact_delivery, fact_transaction

## Summary

- Model intent: `analytical_data_warehouse`
- Required layers: `['raw_load', 'staging', 'dimension', 'fact', 'reporting']`
- DDL present: True
- Load tables present: True
- Staging tables present: True
- Dimension tables present: True
- Fact tables present: True
- Reporting views present: True

## Checks

| Check | Passed / Value |
|---|---:|
| model_type | analytical_data_warehouse |
| required_layers | ['raw_load', 'staging', 'dimension', 'fact', 'reporting'] |
| dimension_tables_present | True |
| fact_tables_present | True |
| load_tables_present | True |
| staging_tables_present | True |
| reporting_views_present | True |
| ddl_present | True |
| ai_additions_present | True |
