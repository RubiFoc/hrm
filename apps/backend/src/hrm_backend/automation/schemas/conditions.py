"""Condition tree schema used by automation rules."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

JsonPrimitive = str | int | float | bool | None


class EqCondition(BaseModel):
    """Field equality condition."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["eq"]
    field: str = Field(min_length=1, max_length=128)
    value: JsonPrimitive


class NeqCondition(BaseModel):
    """Field inequality condition."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["neq"]
    field: str = Field(min_length=1, max_length=128)
    value: JsonPrimitive


class InCondition(BaseModel):
    """Membership condition for primitive lists."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["in"]
    field: str = Field(min_length=1, max_length=128)
    value: list[JsonPrimitive] = Field(min_length=1)


class ContainsCondition(BaseModel):
    """Substring condition for string fields."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["contains"]
    field: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=256)


class ExistsCondition(BaseModel):
    """Existence condition (field present and not null)."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["exists"]
    field: str = Field(min_length=1, max_length=128)


class AndCondition(BaseModel):
    """Conjunction condition."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["and"]
    conditions: list[AutomationCondition] = Field(min_length=1)


class OrCondition(BaseModel):
    """Disjunction condition."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["or"]
    conditions: list[AutomationCondition] = Field(min_length=1)


class NotCondition(BaseModel):
    """Negation condition."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["not"]
    condition: AutomationCondition


AutomationCondition = Annotated[
    EqCondition
    | NeqCondition
    | InCondition
    | ContainsCondition
    | ExistsCondition
    | AndCondition
    | OrCondition
    | NotCondition,
    Field(discriminator="op"),
]
