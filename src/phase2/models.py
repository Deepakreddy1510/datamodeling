from dataclasses import dataclass, field


@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    references_table: str | None = None
    references_column: str | None = None
    max_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    default: str | None = None


@dataclass
class ForeignKey:
    child_table: str
    child_columns: list[str]
    parent_table: str
    parent_columns: list[str]


@dataclass
class UniqueConstraint:
    columns: list[str]
    name: str | None = None


@dataclass
class CheckConstraint:
    expression: str
    column: str | None = None
    operator: str | None = None
    values: list[str] = field(default_factory=list)
    min_value: str | None = None
    max_value: str | None = None
    name: str | None = None
    supported: bool = False


@dataclass
class Table:
    name: str
    schema: str | None = None
    columns: list[Column] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    foreign_keys: list[ForeignKey] = field(default_factory=list)
    unique_constraints: list[UniqueConstraint] = field(default_factory=list)
    check_constraints: list[CheckConstraint] = field(default_factory=list)
    ignored_constraints: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def full_name(self):
        return f"{self.schema}.{self.name}" if self.schema else self.name

    def column_names(self):
        return [column.name for column in self.columns]


@dataclass
class DDLModel:
    schemas: list[str] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def table_map(self):
        mapping = {}
        for table in self.tables:
            mapping[table.name.lower()] = table
            mapping[table.full_name.lower()] = table
        return mapping
