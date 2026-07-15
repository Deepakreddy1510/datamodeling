from datetime import date, datetime, time
from decimal import Decimal

from phase2.ddl_parser import parse_ddl
from phase2.synthetic_data_generator import SyntheticDataError, generate_synthetic_data
from phase2.validator import validate_generated_data


def test_generate_data_preserves_pk_and_fk_consistency():
    model = parse_ddl("""
CREATE TABLE customer (customer_id integer PRIMARY KEY, customer_name text NOT NULL);
CREATE TABLE sales_order (
  order_id integer PRIMARY KEY,
  customer_id integer REFERENCES customer(customer_id),
  order_date date NOT NULL
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    assert len(data["customer"]) == 100
    assert len(data["sales_order"]) == 100
    assert validate_generated_data(model, data, 100)["status"] == "passed"


def test_varchar_max_lengths_are_respected_for_fallback_values():
    model = parse_ddl("""
CREATE TABLE web_values (
  id integer PRIMARY KEY,
  email varchar(30),
  source_file_name varchar(30),
  campaign_theme varchar(30),
  customer_segment character varying(20),
  status varchar(30)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    row = data["web_values"][0]
    for column in model.tables[0].columns:
        value = row[column.name]
        if isinstance(value, str) and column.max_length:
            assert len(value) <= column.max_length
    assert "@" in row["email"]
    assert row["status"] in {"New", "Active", "Pending", "Completed", "Inactive"}


def test_phase2_generates_analytical_data_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE dim_customer (
  customer_id varchar(20) PRIMARY KEY,
  customer_name varchar(50) NOT NULL,
  customer_segment varchar(20) CHECK (customer_segment IN ('New', 'Premium'))
);
CREATE TABLE fact_sales (
  sales_key integer PRIMARY KEY,
  customer_id varchar(20) REFERENCES dim_customer(customer_id),
  quantity integer CHECK (quantity BETWEEN 1 AND 10),
  order_total_amount numeric(8,2)
);
""")
    data = generate_synthetic_data(model, rows_per_table=25, seed=1)
    assert data["dim_customer"][0]["customer_id"].startswith("CUST-")
    assert {row["customer_segment"] for row in data["dim_customer"]} <= {"New", "Premium"}
    parent_ids = {row["customer_id"] for row in data["dim_customer"]}
    assert {row["customer_id"] for row in data["fact_sales"]} <= parent_ids
    assert validate_generated_data(model, data, 25)["status"] in {"passed", "passed_with_warnings"}


def test_business_key_inference_generates_readable_ids_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE business_keys (
  customer_id varchar(30) PRIMARY KEY,
  product_id varchar(30),
  store_id varchar(30),
  order_id varchar(40),
  payment_id varchar(30),
  delivery_id varchar(30)
);
""")
    data = generate_synthetic_data(model, rows_per_table=1, seed=1)
    row = data["business_keys"][0]
    assert row["customer_id"] == "CUST-000001"
    assert row["product_id"] == "PROD-000001"
    assert row["store_id"] == "STORE-000001"
    assert row["order_id"] == "ORDER-20260706-000001"
    assert row["payment_id"] == "PAYMENT-000001"
    assert row["delivery_id"] == "DELIVERY-000001"


def test_composite_unique_constraints_are_repaired_from_ddl_only():
    model = parse_ddl("""
CREATE TABLE dim_location (
  location_key integer PRIMARY KEY,
  city varchar(40),
  region varchar(40),
  country varchar(40),
  UNIQUE (city, region, country)
);
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    tuples = {(row["city"], row["region"], row["country"]) for row in data["dim_location"]}
    assert len(tuples) == 100
    assert validate_generated_data(model, data, 100)["status"] in {"passed", "passed_with_warnings"}


def test_generation_supports_common_postgres_types_and_json():
    model = parse_ddl("""
CREATE TABLE typed_values (
  id integer PRIMARY KEY,
  text_value text NOT NULL,
  varchar_value varchar(20) NOT NULL,
  int_value integer NOT NULL,
  bigint_value bigint NOT NULL,
  amount numeric(12,2) CHECK (amount >= 0),
  active boolean NOT NULL,
  event_date date NOT NULL,
  event_time time NOT NULL,
  event_timestamp timestamp NOT NULL,
  event_timestamptz timestamptz NOT NULL,
  row_uuid uuid NOT NULL,
  payload json NOT NULL,
  payload_b jsonb NOT NULL
);
""")
    data = generate_synthetic_data(model, rows_per_table=5, seed=1)
    row = data["typed_values"][0]
    assert isinstance(row["text_value"], str)
    assert isinstance(row["varchar_value"], str)
    assert isinstance(row["int_value"], int)
    assert isinstance(row["bigint_value"], int)
    assert isinstance(row["amount"], Decimal)
    assert isinstance(row["active"], bool)
    assert isinstance(row["event_date"], date)
    assert isinstance(row["event_time"], time)
    assert isinstance(row["event_timestamp"], datetime)
    assert isinstance(row["event_timestamptz"], datetime)
    assert isinstance(row["row_uuid"], str)
    assert isinstance(row["payload"], dict)
    assert isinstance(row["payload_b"], dict)
    assert validate_generated_data(model, data, 5)["status"] == "passed"


def test_primary_key_uniqueness_for_multiple_pk_shapes():
    model = parse_ddl("""
CREATE TABLE integer_pk (id integer PRIMARY KEY, value text);
CREATE TABLE text_pk (customer_id varchar(30) PRIMARY KEY, value text);
CREATE TABLE uuid_pk (id uuid PRIMARY KEY, value text);
CREATE TABLE composite_pk (part_a varchar(20), part_b integer, value text, PRIMARY KEY (part_a, part_b));
""")
    data = generate_synthetic_data(model, rows_per_table=100, seed=1)
    for table in model.tables:
        tuples = {tuple(row[col] for col in table.primary_key) for row in data[table.name]}
        assert len(tuples) == 100
    assert validate_generated_data(model, data, 100)["status"] in {"passed", "passed_with_warnings"}


def test_fk_inside_unique_constraint_remains_valid():
    model = parse_ddl("""
CREATE TABLE parent_product (product_id varchar(20) PRIMARY KEY);
CREATE TABLE order_line (
  line_id integer PRIMARY KEY,
  order_id varchar(20),
  product_id varchar(20) REFERENCES parent_product(product_id),
  UNIQUE (order_id, product_id)
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=1)
    parent_ids = {row["product_id"] for row in data["parent_product"]}
    assert {row["product_id"] for row in data["order_line"]} <= parent_ids
    assert validate_generated_data(model, data, 20)["status"] in {"passed", "passed_with_warnings"}


def test_unique_check_in_capacity_failure_is_clear():
    model = parse_ddl("""
CREATE TABLE constrained_unique (
  id integer PRIMARY KEY,
  status varchar(10) UNIQUE CHECK (status IN ('A', 'B'))
);
""")
    try:
        generate_synthetic_data(model, rows_per_table=100, seed=1)
    except SyntheticDataError as exc:
        assert "DDL constraint capacity exceeded" in str(exc)
    else:
        raise AssertionError("Expected capacity failure for UNIQUE CHECK IN with only two values")


def test_generic_calculations_from_column_names():
    model = parse_ddl("""
CREATE TABLE fact_line (
  line_id integer PRIMARY KEY,
  quantity integer CHECK (quantity > 0),
  unit_price numeric(8,2) CHECK (unit_price > 0),
  line_total_amount numeric(10,2),
  promised_delivery_time timestamp,
  actual_delivery_time timestamp,
  delivery_delay_minutes integer,
  is_delayed boolean
);
""")
    data = generate_synthetic_data(model, rows_per_table=10, seed=1)
    for row in data["fact_line"]:
        assert row["line_total_amount"] == row["quantity"] * row["unit_price"]
        assert row["delivery_delay_minutes"] >= 0
        assert row["is_delayed"] == (row["delivery_delay_minutes"] > 0)
    assert validate_generated_data(model, data, 10)["status"] == "passed"


def test_generic_semantic_generation_uses_reference_data_and_no_placeholders_for_football_style():
    model = parse_ddl("""
CREATE TABLE load_player_raw (
  player_id varchar(30) PRIMARY KEY,
  player_name varchar(80) NOT NULL,
  position varchar(30),
  jersey_number integer,
  date_of_birth date,
  nationality varchar(50),
  active_status boolean
);
""")
    business_input = {"reference_data": {"player_positions": ["Goalkeeper", "Defender", "Midfielder", "Forward"]}}
    data = generate_synthetic_data(model, rows_per_table=8, seed=2, business_input=business_input)
    positions = {row["position"] for row in data["load_player_raw"]}
    assert positions <= set(business_input["reference_data"]["player_positions"])
    for row in data["load_player_raw"]:
        assert row["player_name"] != "Player 001"
        assert " " in row["player_name"]
        assert isinstance(row["date_of_birth"], date)
        assert isinstance(row["jersey_number"], int)
        assert isinstance(row["active_status"], bool)
        assert not row["nationality"].endswith(" 001")
    validation = validate_generated_data(model, data, 8, business_input=business_input)
    assert validation["status"] == "passed"


def test_generic_reference_data_payment_status_and_customer_email_consistency_across_layers():
    model = parse_ddl("""
CREATE TABLE load_customer_raw (customer_id varchar(30) PRIMARY KEY, customer_name varchar(80), email varchar(120), city varchar(50));
CREATE TABLE stg_customer (customer_id varchar(30) PRIMARY KEY, customer_name varchar(80), email varchar(120), city varchar(50));
CREATE TABLE dim_customer (customer_id varchar(30) PRIMARY KEY, customer_name varchar(80), email varchar(120), city varchar(50));
CREATE TABLE fact_payment (
  payment_id integer PRIMARY KEY,
  customer_id varchar(30) REFERENCES dim_customer(customer_id),
  payment_status varchar(30),
  payment_amount numeric(10,2)
);
""")
    business_input = {"reference_data": {"payment_statuses": ["Successful", "Failed", "Pending", "Refunded"]}}
    data = generate_synthetic_data(model, rows_per_table=5, seed=3, business_input=business_input)
    assert {row["payment_status"] for row in data["fact_payment"]} <= set(business_input["reference_data"]["payment_statuses"])
    customer_rows = len(data["load_customer_raw"])
    assert customer_rows < len(data["fact_payment"])
    assert len(data["stg_customer"]) == len(data["dim_customer"]) == customer_rows
    for i in range(customer_rows):
        raw = data["load_customer_raw"][i]
        stg = data["stg_customer"][i]
        dim = data["dim_customer"][i]
        assert raw["customer_name"] == stg["customer_name"] == dim["customer_name"]
        assert raw["email"] == stg["email"] == dim["email"]
        first, last = raw["customer_name"].split()[0].lower(), raw["customer_name"].split()[-1].lower()
        assert first in raw["email"] and last in raw["email"]
    assert validate_generated_data(model, data, data["__expected_rows__"], business_input=business_input)["status"] == "passed"


def test_generic_semantic_styles_service_healthcare_banking_have_valid_types_and_fks():
    model = parse_ddl("""
CREATE TABLE dim_requester (requester_id varchar(30) PRIMARY KEY, requester_name varchar(80), email varchar(100));
CREATE TABLE fact_ticket (ticket_id integer PRIMARY KEY, requester_id varchar(30) REFERENCES dim_requester(requester_id), ticket_priority varchar(20), created_at timestamp, resolved_flag boolean);
CREATE TABLE dim_patient (patient_id varchar(30) PRIMARY KEY, patient_name varchar(80), date_of_birth date);
CREATE TABLE fact_appointment (appointment_id integer PRIMARY KEY, patient_id varchar(30) REFERENCES dim_patient(patient_id), appointment_status varchar(20), appointment_date date);
CREATE TABLE fact_transaction (transaction_id integer PRIMARY KEY, transaction_type varchar(20), transaction_amount numeric(12,2), transaction_date date, active_status boolean);
""")
    business_input = {"reference_data": {"ticket_priorities": ["Low", "Medium", "High"], "appointment_statuses": ["Scheduled", "Completed"], "transaction_types": ["Deposit", "Withdrawal"]}}
    data = generate_synthetic_data(model, rows_per_table=6, seed=4, business_input=business_input)
    assert {row["ticket_priority"] for row in data["fact_ticket"]} <= {"Low", "Medium", "High"}
    assert {row["appointment_status"] for row in data["fact_appointment"]} <= {"Scheduled", "Completed"}
    assert {row["transaction_type"] for row in data["fact_transaction"]} <= {"Deposit", "Withdrawal"}
    for row in data["fact_transaction"]:
        assert isinstance(row["transaction_amount"], Decimal)
        assert isinstance(row["transaction_date"], date)
        assert isinstance(row["active_status"], bool)
    assert validate_generated_data(model, data, 6, business_input=business_input)["status"] == "passed"


def test_check_in_constraints_override_reference_data_for_text_enums_generically():
    model = parse_ddl("""
CREATE TABLE enum_values (
  id integer PRIMARY KEY,
  status varchar(20) CHECK (status IN ('DDL_A','DDL_B')),
  platform_type text CHECK (platform_type IN ('Web','Mobile','Partner')),
  ticket_category varchar(20) CHECK (ticket_category IN ('Standard','Premium'))
);
""")
    business_input = {"reference_data": {"statuses": ["Yaml A", "Yaml B"], "platform_types": ["Yaml Platform"]}}
    data = generate_synthetic_data(model, rows_per_table=6, seed=5, business_input=business_input)
    assert {row["status"] for row in data["enum_values"]} <= {"DDL_A", "DDL_B"}
    assert {row["platform_type"] for row in data["enum_values"]} <= {"Web", "Mobile", "Partner"}
    assert {row["ticket_category"] for row in data["enum_values"]} <= {"Standard", "Premium"}
    assert set(data["__stats__"]["check_in_value_sources"]) == {
        "enum_values.platform_type",
        "enum_values.status",
        "enum_values.ticket_category",
    }
    assert validate_generated_data(model, data, 6, business_input=business_input)["status"] == "passed"


def test_football_style_check_in_columns_are_generated_from_ddl_allowed_values():
    model = parse_ddl("""
CREATE TABLE stg_team (
  team_id integer PRIMARY KEY,
  confederation varchar(20) CHECK (confederation IN ('AFC','CAF','CONCACAF','CONMEBOL','OFC','UEFA'))
);
CREATE TABLE stg_player (
  player_id integer PRIMARY KEY,
  position varchar(20) CHECK (position IN ('Goalkeeper','Defender','Midfielder','Forward')),
  preferred_foot varchar(10) CHECK (preferred_foot IN ('Left','Right','Both'))
);
CREATE TABLE stg_match (
  match_id integer PRIMARY KEY,
  match_stage varchar(30) CHECK (match_stage IN ('Group Stage','Round of 16','Quarter Final','Semi Final','Third Place Playoff','Final')),
  match_status varchar(20) CHECK (match_status IN ('Scheduled','In Progress','Completed','Postponed','Cancelled'))
);
CREATE TABLE stg_match_event (
  event_id integer PRIMARY KEY,
  event_type varchar(20) CHECK (event_type IN ('Goal','Assist','Yellow Card','Red Card','Substitution','Penalty','Own Goal','Save')),
  event_outcome varchar(20) CHECK (event_outcome IN ('Successful','Unsuccessful','Awarded','Missed','Completed'))
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=6, business_input={"reference_data": {"positions": ["Yaml Position"]}})
    assert {row["confederation"] for row in data["stg_team"]} <= {'AFC','CAF','CONCACAF','CONMEBOL','OFC','UEFA'}
    assert {row["position"] for row in data["stg_player"]} <= {'Goalkeeper','Defender','Midfielder','Forward'}
    assert {row["preferred_foot"] for row in data["stg_player"]} <= {'Left','Right','Both'}
    assert {row["match_stage"] for row in data["stg_match"]} <= {'Group Stage','Round of 16','Quarter Final','Semi Final','Third Place Playoff','Final'}
    assert {row["match_status"] for row in data["stg_match"]} <= {'Scheduled','In Progress','Completed','Postponed','Cancelled'}
    assert {row["event_type"] for row in data["stg_match_event"]} <= {'Goal','Assist','Yellow Card','Red Card','Substitution','Penalty','Own Goal','Save'}
    assert {row["event_outcome"] for row in data["stg_match_event"]} <= {'Successful','Unsuccessful','Awarded','Missed','Completed'}
    assert validate_generated_data(model, data, 20)["status"] == "passed"


def test_finalize_generated_value_enforces_ddl_types_and_varchar_length_for_bad_candidates():
    model = parse_ddl("""
CREATE TABLE guard_values (
  id integer PRIMARY KEY,
  int_value integer,
  big_value bigint,
  amount numeric(10,2),
  event_date date,
  event_timestamp timestamp,
  active_status boolean,
  short_label varchar(10)
);
""")
    table = model.tables[0]
    from phase2.synthetic_data_generator import finalize_generated_value
    stats = {"truncated_values": 0}
    bad = "Synthetic Global Football Value 001"
    row = {}
    for column in table.columns:
        if column.name == "id":
            continue
        row[column.name] = finalize_generated_value(table, column, bad, 1, row, stats)
    assert isinstance(row["int_value"], int)
    assert isinstance(row["big_value"], int)
    assert isinstance(row["amount"], Decimal)
    assert isinstance(row["event_date"], date) and not isinstance(row["event_date"], datetime)
    assert isinstance(row["event_timestamp"], datetime)
    assert isinstance(row["active_status"], bool)
    assert len(row["short_label"]) <= 10


def test_entity_reuse_is_finalized_against_target_ddl_type():
    model = parse_ddl("""
CREATE TABLE load_metric_raw (metric_id integer PRIMARY KEY, metric_value text, metric_date text, metric_amount text);
CREATE TABLE stg_metric (metric_id integer PRIMARY KEY, metric_value integer, metric_date date, metric_amount numeric(8,2));
""")
    data = generate_synthetic_data(model, rows_per_table=3, seed=7)
    for row in data["stg_metric"]:
        assert isinstance(row["metric_value"], int)
        assert isinstance(row["metric_date"], date) and not isinstance(row["metric_date"], datetime)
        assert isinstance(row["metric_amount"], Decimal)
    assert set(data["__stats__"]["incompatible_reuse_corrections"]) >= {"stg_metric.metric_value", "stg_metric.metric_date", "stg_metric.metric_amount"}
    assert validate_generated_data(model, data, 3)["status"] == "passed"


def test_between_and_positive_constraints_are_enforced_by_final_guard():
    model = parse_ddl("""
CREATE TABLE constrained_numbers (
  id integer PRIMARY KEY,
  jersey_number integer CHECK (jersey_number BETWEEN 1 AND 99),
  minutes_played integer CHECK (minutes_played BETWEEN 0 AND 120),
  nonnegative_amount numeric(10,2) CHECK (nonnegative_amount >= 0),
  positive_amount numeric(10,2) CHECK (positive_amount > 0)
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=8)
    for row in data["constrained_numbers"]:
        assert 1 <= row["jersey_number"] <= 99
        assert 0 <= row["minutes_played"] <= 120
        assert row["nonnegative_amount"] >= 0
        assert row["positive_amount"] > 0
    assert validate_generated_data(model, data, 20)["status"] == "passed"


def test_football_style_typed_columns_pass_validation_without_text_leaks():
    model = parse_ddl("""
CREATE TABLE typed_sports_regression (
  id integer PRIMARY KEY,
  season_year integer CHECK (season_year BETWEEN 2024 AND 2026),
  start_date date,
  end_date date,
  team_rank integer CHECK (team_rank > 0),
  jersey_number integer CHECK (jersey_number BETWEEN 1 AND 99),
  date_of_birth date,
  match_date date,
  home_score integer CHECK (home_score >= 0),
  away_score integer CHECK (away_score >= 0),
  attendance_count integer CHECK (attendance_count >= 0),
  match_revenue numeric(14,2) CHECK (match_revenue >= 0),
  minutes_played integer CHECK (minutes_played BETWEEN 0 AND 120),
  event_time_minute integer CHECK (event_time_minute BETWEEN 0 AND 120),
  tickets_sold integer CHECK (tickets_sold >= 0),
  ticket_price numeric(10,2) CHECK (ticket_price >= 0),
  sale_amount numeric(14,2) CHECK (sale_amount >= 0),
  sale_date date,
  viewers_count bigint CHECK (viewers_count > 0),
  broadcast_revenue numeric(14,2) CHECK (broadcast_revenue > 0),
  contract_amount numeric(14,2) CHECK (contract_amount > 0),
  confederation varchar(20) CHECK (confederation IN ('AFC','CAF','CONCACAF','CONMEBOL','OFC','UEFA')),
  position varchar(30) CHECK (position IN ('Goalkeeper','Defender','Midfielder','Forward')),
  preferred_foot varchar(10) CHECK (preferred_foot IN ('Left','Right','Both')),
  match_stage varchar(50) CHECK (match_stage IN ('Group Stage','Round of 16','Quarter Final','Semi Final','Third Place Playoff','Final')),
  match_status varchar(30) CHECK (match_status IN ('Scheduled','In Progress','Completed','Postponed','Cancelled')),
  event_type varchar(30) CHECK (event_type IN ('Goal','Assist','Yellow Card','Red Card','Substitution','Penalty','Own Goal','Save')),
  event_outcome varchar(30) CHECK (event_outcome IN ('Successful','Unsuccessful','Awarded','Missed','Completed'))
);
""")
    data = generate_synthetic_data(model, rows_per_table=20, seed=9)
    for row in data["typed_sports_regression"]:
        assert isinstance(row["season_year"], int) and 2024 <= row["season_year"] <= 2026
        assert isinstance(row["start_date"], date) and isinstance(row["end_date"], date)
        assert isinstance(row["jersey_number"], int) and 1 <= row["jersey_number"] <= 99
        assert isinstance(row["date_of_birth"], date)
        assert isinstance(row["match_date"], date)
        assert isinstance(row["home_score"], int) and row["home_score"] >= 0
        assert isinstance(row["away_score"], int) and row["away_score"] >= 0
        assert isinstance(row["sale_amount"], Decimal)
        assert row["confederation"] in {'AFC','CAF','CONCACAF','CONMEBOL','OFC','UEFA'}
        assert row["position"] in {'Goalkeeper','Defender','Midfielder','Forward'}
        assert row["preferred_foot"] in {'Left','Right','Both'}
        for value in row.values():
            if isinstance(value, str):
                assert not value.startswith("Synthetic Global Football")
    assert validate_generated_data(model, data, 20)["status"] == "passed"


def test_python_engine_aligns_generic_raw_json_payloads_to_staging():
    model = parse_ddl("""
CREATE TABLE load_account_raw (
  load_id bigint PRIMARY KEY,
  source_payload jsonb NOT NULL,
  source_system text,
  loaded_at timestamp
);
CREATE TABLE stg_account (
  account_id varchar(30) PRIMARY KEY,
  account_name varchar(80) NOT NULL,
  status varchar(20)
);
CREATE TABLE dim_account (
  account_key integer PRIMARY KEY,
  account_id varchar(30) UNIQUE,
  account_name varchar(80),
  status varchar(20)
);
CREATE TABLE fact_activity (
  activity_key integer PRIMARY KEY,
  account_key integer REFERENCES dim_account(account_key),
  activity_count integer
);
""")
    data = generate_synthetic_data(model, rows_per_table=10, seed=11)
    assert len(data["load_account_raw"]) == len(data["stg_account"])
    for raw, staging in zip(data["load_account_raw"], data["stg_account"]):
        assert raw["source_payload"]["account_id"] == staging["account_id"]
        assert raw["source_payload"]["account_name"] == staging["account_name"]
        assert raw["source_payload"]["status"] == staging["status"]
    assert data["__stats__"]["raw_payload_alignment_events"] == ["load_account_raw -> stg_account"]
