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
